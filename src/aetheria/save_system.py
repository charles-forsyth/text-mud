import json
import os
import shutil
from typing import Dict, List, Tuple
from aetheria.config import SAVE_FILE_NAME
from aetheria.entity import Player, Companion
from aetheria.world import Room
from aetheria.quests import Quest


def save_game(
    player: Player,
    party: List[Companion],
    world: Dict[str, Room],
    quests: Dict[str, Quest],
    current_room_name: str,
    tavern_companions: List[Companion],
) -> bool:
    """Saves the entire game state atomically using a transaction-safe temporary file and creates a backup."""
    state = {
        "player": player.to_dict(),
        "party": [c.to_dict() for c in party],
        "tavern_companions": [c.to_dict() for c in tavern_companions],
        "current_room": current_room_name,
        "quests": {qid: q.to_dict() for qid, q in quests.items()},
        "rooms": {rname: r.to_dict() for rname, r in world.items()},
    }

    # Create double-buffered backup of the last successful save
    if os.path.exists(SAVE_FILE_NAME):
        try:
            shutil.copy2(SAVE_FILE_NAME, f"{SAVE_FILE_NAME}.bak")
        except Exception:
            pass

    tmp_file = f"{SAVE_FILE_NAME}.tmp"
    try:
        # Write to temporary file first
        with open(tmp_file, "w") as f:
            json.dump(state, f, indent=4)

        # Atomic file rename (transaction-safe)
        os.replace(tmp_file, SAVE_FILE_NAME)
        return True
    except Exception:
        # Cleanup temp file on failure
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass
        return False


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
    """Loads and deserializes the entire game state. Performs validation to prevent corruption.
    Automatically recovers from SAVE_FILE_NAME.bak if primary save is corrupt or missing."""
    state = None
    was_recovered = False

    # 1. Try reading the primary save file
    try:
        if not os.path.exists(SAVE_FILE_NAME):
            raise FileNotFoundError("Primary save file does not exist.")

        with open(SAVE_FILE_NAME, "r") as f:
            state = json.load(f)

        # Verification of critical root nodes
        required_keys = ["player", "party", "current_room", "quests", "rooms"]
        for k in required_keys:
            if k not in state:
                raise KeyError(f"Corrupt save file: Missing root node '{k}'")
    except Exception as primary_err:
        # Primary failed, attempt automatic backup restoration
        bak_file = f"{SAVE_FILE_NAME}.bak"
        if os.path.exists(bak_file):
            try:
                with open(bak_file, "r") as f:
                    state = json.load(f)

                # Verification of critical root nodes on backup
                required_keys = ["player", "party", "current_room", "quests", "rooms"]
                for k in required_keys:
                    if k not in state:
                        raise KeyError(f"Corrupt backup file: Missing root node '{k}'")
                was_recovered = True
            except Exception as bak_err:
                raise RuntimeError(
                    f"Failed to load primary save ({primary_err}) and backup recovery failed: {bak_err}"
                )
        else:
            raise RuntimeError(
                f"Failed to load primary save ({primary_err}) and no backup file (.bak) was found."
            )

    # 2. Deserialization into NEW instances (Transaction Pattern)
    loaded_player = Player.from_dict(state["player"])
    loaded_party = [Companion.from_dict(c) for c in state["party"]]
    loaded_tavern = [Companion.from_dict(c) for c in state.get("tavern_companions", [])]
    loaded_room_name = state["current_room"]

    # Restore Quests
    loaded_quests: Dict[str, Quest] = {}
    for qid, q_data in state["quests"].items():
        loaded_quests[qid] = Quest.from_dict(q_data)

    # Restore Rooms dynamically
    loaded_world: Dict[str, Room] = {}
    for rname, r_data in state["rooms"].items():
        loaded_world[rname] = Room.from_dict(r_data)

    # Re-establish exit graph connections using the default world structure!
    # Because exit references were parsed by room name, we link rooms back together.
    for rname, room in loaded_world.items():
        if rname in default_world:
            for direction, target_room_default in default_world[rname].exits.items():
                if target_room_default.name in loaded_world:
                    # Link to the newly loaded room instance, preserving updated locks/items/enemies!
                    room.add_exit(direction, loaded_world[target_room_default.name])

    # Re-link Player current_room reference
    if loaded_room_name in loaded_world:
        loaded_player.current_room = loaded_world[loaded_room_name]
    else:
        # Fallback to Eldergrove Center if current room name is invalid
        loaded_player.current_room = loaded_world["Eldergrove Center"]
        loaded_room_name = "Eldergrove Center"

    return (
        loaded_player,
        loaded_party,
        loaded_world,
        loaded_quests,
        loaded_room_name,
        loaded_tavern,
        was_recovered,
    )
