import json
import os
import shutil
import logging
from typing import Dict, List, Tuple, Any, Optional
from aetheria.config import SAVE_FILE_NAME, SAVE_SCHEMA_VERSION
from aetheria.entity import Player, Companion
from aetheria.world import Room
from aetheria.quests import Quest


# ==================== SCHEMA MIGRATION PIPELINE ====================


def migrate_v1_to_v2(state: dict) -> dict:
    """Upgrades version 1 saves by introducing dynamic NPC affinity states and completed quest hashes."""
    logging.info("Migrating save file from Schema Version 1 to 2...")

    # 1. Add default completed_quests list if missing
    if "player" in state and "completed_quests" not in state["player"]:
        state["player"]["completed_quests"] = []

    # 2. Add default affinity (0) and relationship_flags to all saved NPCs
    if "rooms" in state:
        for room_data in state["rooms"].values():
            for npc_data in room_data.get("npcs", []):
                if "affinity" not in npc_data:
                    npc_data["affinity"] = 0
                if "relationship_flags" not in npc_data:
                    npc_data["relationship_flags"] = []

    # 3. Add default tavern_companions array if missing
    if "tavern_companions" not in state:
        state["tavern_companions"] = []

    state["schema_version"] = 2
    return state


def migrate_v2_to_v3(state: dict) -> dict:
    """Upgrades version 2 saves by introducing clock cycles, weather variables, and skill trees."""
    logging.info("Migrating save file from Schema Version 2 to 3...")

    # Initialize clock defaults
    if "world_clock" not in state:
        state["world_clock"] = {
            "current_index": 1,  # Day
            "movement_ticks": 0,
        }

    # Initialize weather defaults
    if "weather_engine" not in state:
        state["weather_engine"] = {"current_state_key": "clear", "turns_remaining": 15}

    # Initialize player talent defaults
    if "player" in state:
        if "skill_points" not in state["player"]:
            state["player"]["skill_points"] = 0
        if "talent_tree" not in state["player"]:
            char_class = state["player"].get("char_class", "Warrior")
            state["player"]["talent_tree"] = {
                "class_name": char_class,
                "nodes": {},
                "allocated_points": 0,
            }
        if "ailments" not in state["player"]:
            state["player"]["ailments"] = []

    state["schema_version"] = 3
    return state


# Mapping of source schema versions to their corresponding migration upgrade functions
MIGRATION_REGISTRY: Dict[int, Any] = {
    1: migrate_v1_to_v2,
    2: migrate_v2_to_v3,
}


def run_state_migrations(state: dict) -> dict:
    """Sequentially applies all required migrations to bring historical saves up to the latest spec."""
    saved_version = state.get(
        "schema_version", 1
    )  # Default old unversioned files to version 1

    while saved_version < SAVE_SCHEMA_VERSION:
        migration_fn = MIGRATION_REGISTRY.get(saved_version)
        if not migration_fn:
            logging.warning(
                f"No schema migration path found for version {saved_version}!"
            )
            break
        state = migration_fn(state)
        saved_version = state.get("schema_version", saved_version + 1)

    return state


# ==================== SAVING & LOADING CORE ENGINE ====================


def save_game(
    player: Player,
    party: List[Companion],
    world: Dict[str, Room],
    quests: Dict[str, Quest],
    current_room_name: str,
    tavern_companions: List[Companion],
    world_clock: Any = None,
    weather_engine: Any = None,
) -> bool:
    """Saves the entire game state atomically using a transaction-safe temporary file and creates a backup."""
    world_clock_data = None
    if world_clock is not None:
        world_clock_data = {
            "current_index": getattr(world_clock, "current_index", 1),
            "movement_ticks": getattr(world_clock, "movement_ticks", 0),
        }

    weather_engine_data = None
    if weather_engine is not None:
        state_key = "clear"
        current_state = getattr(weather_engine, "current_state", None)
        if current_state:
            for k, v in getattr(weather_engine, "STATES", {}).items():
                if v == current_state:
                    state_key = k
                    break
        weather_engine_data = {
            "current_state_key": state_key,
            "turns_remaining": getattr(weather_engine, "turns_remaining", 15),
        }

    state = {
        "schema_version": SAVE_SCHEMA_VERSION,
        "player": player.to_dict(),
        "party": [c.to_dict() for c in party],
        "tavern_companions": [c.to_dict() for c in tavern_companions],
        "current_room": current_room_name,
        "quests": {qid: q.to_dict() for qid, q in quests.items()},
        "rooms": {rname: r.to_dict() for rname, r in world.items()},
        "world_clock": world_clock_data,
        "weather_engine": weather_engine_data,
    }

    # Backup rotation
    if os.path.exists(SAVE_FILE_NAME):
        try:
            shutil.copy2(SAVE_FILE_NAME, f"{SAVE_FILE_NAME}.bak")
        except Exception as e:
            logging.error(f"Failed to create double-buffered backup: {e}")

    tmp_file = f"{SAVE_FILE_NAME}.tmp"
    try:
        with open(tmp_file, "w") as f:
            json.dump(state, f, indent=4)
        os.replace(tmp_file, SAVE_FILE_NAME)
        return True
    except Exception as e:
        logging.error(f"Atomic file save failed: {e}")
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass
        return False


class LoadGameResult(tuple):
    """Custom tuple subclass to allow unpacking exactly 7 values for backward compatibility, while exposing extra attributes."""

    def __new__(
        cls,
        player: Player,
        party: List[Companion],
        world: Dict[str, Room],
        quests: Dict[str, Quest],
        room_name: str,
        tavern: List[Companion],
        was_recovered: bool,
        clock_data: Optional[Dict[str, Any]] = None,
        weather_data: Optional[Dict[str, Any]] = None,
    ):
        inst = super().__new__(
            cls, (player, party, world, quests, room_name, tavern, was_recovered)
        )
        inst.clock_data = clock_data
        inst.weather_data = weather_data
        return inst


def load_game(
    default_world: Dict[str, Room], default_quests: Dict[str, Quest]
) -> Tuple[
    Player,
    List[Companion],
    Dict[str, Room],
    Dict[str, Quest],
    str,
    List[Companion],
    bool,
]:
    """Loads, migrates, and safely deserializes the entire game state with validation."""
    state = None
    was_recovered = False

    try:
        if not os.path.exists(SAVE_FILE_NAME):
            raise FileNotFoundError("Primary save file not found.")

        with open(SAVE_FILE_NAME, "r") as f:
            state = json.load(f)
    except Exception as primary_err:
        # Attempt backup recovery
        bak_file = f"{SAVE_FILE_NAME}.bak"
        if os.path.exists(bak_file):
            try:
                with open(bak_file, "r") as f:
                    state = json.load(f)
                was_recovered = True
            except Exception as bak_err:
                raise RuntimeError(
                    f"Primary load failed ({primary_err}) and backup is corrupt: {bak_err}"
                )
        else:
            raise RuntimeError(
                f"Primary load failed ({primary_err}) and no backup (.bak) exists."
            )

    # Apply Migrations to upgrade old JSON schemas cleanly
    state = run_state_migrations(state)

    # Perform deserializations
    loaded_player = Player.from_dict(state["player"])
    loaded_party = [Companion.from_dict(c) for c in state["party"]]
    loaded_tavern = [Companion.from_dict(c) for c in state.get("tavern_companions", [])]
    loaded_room_name = state["current_room"]

    # Restore Quests
    loaded_quests: Dict[str, Quest] = {}
    for qid, q_data in state["quests"].items():
        loaded_quests[qid] = Quest.from_dict(q_data)

    # Restore Rooms (acting as Identity Map to preserve referential integrity)
    loaded_world: Dict[str, Room] = {}
    for rname, r_data in state["rooms"].items():
        loaded_world[rname] = Room.from_dict(r_data)

    # Re-establish exit graph connections dynamically!
    for room in loaded_world.values():
        saved_exits = getattr(room, "_saved_exits_map", {})
        if saved_exits:
            for direction, target_name in saved_exits.items():
                if target_name in loaded_world:
                    room.add_exit(direction, loaded_world[target_name])
        else:
            if room.name in default_world:
                for direction, target_room_default in default_world[
                    room.name
                ].exits.items():
                    if target_room_default.name in loaded_world:
                        room.add_exit(direction, loaded_world[target_room_default.name])

    # Re-link Player current_room reference
    if loaded_room_name in loaded_world:
        loaded_player.current_room = loaded_world[loaded_room_name]
    else:
        loaded_player.current_room = loaded_world["Eldergrove Center"]
        loaded_room_name = "Eldergrove Center"

    clock_data = state.get("world_clock")
    weather_data = state.get("weather_engine")

    return LoadGameResult(
        loaded_player,
        loaded_party,
        loaded_world,
        loaded_quests,
        loaded_room_name,
        loaded_tavern,
        was_recovered,
        clock_data,
        weather_data,
    )
