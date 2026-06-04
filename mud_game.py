import sys
import os
import random
from typing import Any

# Add 'src' directory to sys.path to enable package imports cleanly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from aetheria.config import (
    SAVE_FILE_NAME,
    MAX_PARTY_SIZE,
    BASE_RESPAWN_GOLD_PENALTY_PCT,
)
from aetheria.models import Item, Equipment, Consumable
from aetheria.entity import Player, Companion, Enemy
from aetheria.world import build_default_world
from aetheria.quests import get_default_quests
from aetheria.combat import CombatManager
from aetheria.save_system import save_game, load_game
from aetheria.tts import TTSManager
from aetheria.ai_engine import (
    generate_npc_dialogue,
    generate_companion_banter,
    generate_dynamic_room_description,
)
from aetheria.ui import (
    console,
    render_title_screen,
    render_help_menu,
    render_room_panel,
    render_combat_screen,
    render_full_party_hud,
    render_inventory_list,
    render_quests_log,
    render_quick_actions,
    render_world_map,
)


class GameController:
    DIRECTIONS = {
        "n": "north",
        "s": "south",
        "e": "east",
        "w": "west",
        "north": "north",
        "south": "south",
        "east": "east",
        "west": "west",
    }

    def __init__(self):
        self.world = build_default_world()
        self.quests = get_default_quests()
        self.player: Player = None  # type: ignore
        self.party: list[Companion] = []

        # Initial recruitable companions at the Golden Oak Tavern
        self.tavern_companions = [
            Companion(
                name="Lyra",
                char_class="Mage",
                personality="Lyra is a sarcastic, highly intelligent elven spell-weaver. She speaks with dry humor and dislikes physical labor, but handles flame spells perfectly.",
                hp=80,
                max_hp=80,
                mana=40,
                max_mana=40,
                attack=8,
                defense=3,
                level=1,
            ),
            Companion(
                name="Garrick",
                char_class="Warrior",
                personality="Garrick is a battle-weary, heavy-shield fighter who speaks in deep, stoic sentences. He values defensive positioning, iron grit, and protects teammates.",
                hp=110,
                max_hp=110,
                mana=10,
                max_mana=10,
                attack=12,
                defense=7,
                level=1,
            ),
        ]
        self.is_running = True
        self.quick_actions: list[tuple[str, str]] = []

    def get_current_quick_actions(self) -> list[tuple[str, str]]:
        actions: list[tuple[str, str]] = []
        room = self.player.current_room

        # 1. Exits / Movement
        for direction in room.exits.keys():
            dest = room.get_exit(direction)
            dest_name = dest.name if dest else "Unknown"
            actions.append(
                (
                    f"🚪 Go [bold green]{direction.capitalize()}[/bold green] [dim]({dest_name})[/dim]",
                    f"go {direction}",
                )
            )

        # 2. Items / Loot
        for item in room.items:
            actions.append(
                (
                    f"📦 Pick up [bold yellow]{item.name}[/bold yellow]",
                    f"take {item.name}",
                )
            )

        # 3. Talk to NPCs
        for npc in room.npcs:
            actions.append(
                (
                    f"👤 Talk to [bold cyan]{npc.name}[/bold cyan] [dim](Hello)[/dim]",
                    f"talk {npc.name} hello",
                )
            )
            # If they are quest givers, let's offer a Quest conversation shortcut
            npc_quest_map = {
                "Tavernkeeper Barnaby": "q_eldergrove_goblins",
                "Priestess Althea": "q_eldergrove_sigil",
                "Quartermaster Elena": "q_silverlight_malakor",
            }
            if npc.name in npc_quest_map:
                qid = npc_quest_map[npc.name]
                if qid in self.quests:
                    quest = self.quests[qid]
                    show_quest_shortcut = False
                    if (
                        quest.status == "inactive"
                        and qid not in self.player.completed_quests
                    ):
                        if npc.name == "Priestess Althea":
                            if "q_eldergrove_goblins" in self.player.completed_quests:
                                show_quest_shortcut = True
                        else:
                            show_quest_shortcut = True
                    elif quest.status == "active" and quest.is_objective_met:
                        show_quest_shortcut = True

                    if show_quest_shortcut:
                        actions.append(
                            (
                                f"📜 Talk to [bold cyan]{npc.name}[/bold cyan] [dim](Quest)[/dim]",
                                f"talk {npc.name} quest",
                            )
                        )

        # 4. Recruit Companions in Tavern
        if (
            room.name == "Eldergrove Tavern (The Golden Oak)"
            and len(self.party) < MAX_PARTY_SIZE - 1
        ):
            for comp in self.tavern_companions:
                actions.append(
                    (
                        f"🍻 Recruit [bold cyan]{comp.name}[/bold cyan] [dim]({comp.char_class})[/dim]",
                        f"recruit {comp.name}",
                    )
                )

        # 5. General Menu Actions
        if any(isinstance(i, Consumable) for i in self.player.inventory):
            actions.append(("🎒 Use/Consume Item", "use"))
        if any(isinstance(i, Equipment) for i in self.player.inventory):
            actions.append(("🛡️ Equip Armaments", "equip"))
        actions.append(("🎒 View Inventory", "inventory"))
        actions.append(("👥 View Party HUD", "party"))
        actions.append(("📜 View Quest Log", "quests"))
        actions.append(("🗺️ Show World Map", "map"))
        actions.append(("💾 Save Progress", "save"))
        actions.append(("❓ Help Menu", "help"))

        return actions

    def render_current_room(self):
        """Generates dynamic descriptive context and renders the beautiful room panel."""
        room = self.player.current_room

        # Assemble items
        items_list = [item.name for item in room.items]

        # Assemble npcs
        npcs_list = [(npc.name, npc.persona) for npc in room.npcs]

        # Assemble enemy info
        enemy_name = room.enemy.name if room.enemy else None
        enemy_hp_info = (
            f"({room.enemy.hp}/{room.enemy.max_hp} HP)"
            if (room.enemy and room.enemy.is_alive)
            else None
        )

        # Assemble party companions
        party_list = [(c.name, c.personality) for c in self.party]

        # Assemble quest context
        quest_context = "No active quests."
        active_ids = self.player.active_quests
        if active_ids:
            quest_context = ", ".join(
                f"{self.quests[qid].name} (Status: In Progress)"
                for qid in active_ids
                if qid in self.quests
            )

        # Generate the dynamic description via ai_engine
        dynamic_desc = generate_dynamic_room_description(
            room_name=room.name,
            base_description=room.description,
            is_town=room.is_town,
            items=items_list,
            npcs=npcs_list,
            enemy_name=enemy_name,
            enemy_hp_info=enemy_hp_info,
            player_name=self.player.name,
            player_class=self.player.char_class,
            party_members=party_list,
            quest_context=quest_context,
        )

        # Call the render function
        render_room_panel(
            room, self.party, self.player, dynamic_description=dynamic_desc
        )
        TTSManager().speak(dynamic_desc, "Narrator")

        # Predictive prewarming of adjacent rooms' descriptions in background threads
        self._prewarm_adjacent_rooms(room)

    def _prewarm_adjacent_rooms(self, current_room):
        """Identifies all adjacent rooms and spins up background daemon threads to pre-generate their dynamic descriptions."""
        import threading

        # Avoid prewarming if player is not fully initialized
        if not self.player:
            return

        for direction, adj_room in current_room.exits.items():
            if not adj_room:
                continue

            # Prepare arguments for the adjacent room description generator
            items_list = [item.name for item in adj_room.items]
            npcs_list = [(npc.name, npc.persona) for npc in adj_room.npcs]
            enemy_name = adj_room.enemy.name if adj_room.enemy else None
            enemy_hp_info = (
                f"({adj_room.enemy.hp}/{adj_room.enemy.max_hp} HP)"
                if (adj_room.enemy and adj_room.enemy.is_alive)
                else None
            )
            party_list = [(c.name, c.personality) for c in self.party]

            quest_context = "No active quests."
            active_ids = self.player.active_quests
            if active_ids:
                quest_context = ", ".join(
                    f"{self.quests[qid].name} (Status: In Progress)"
                    for qid in active_ids
                    if qid in self.quests
                )

            player_name = self.player.name
            player_class = self.player.char_class

            # Spin up a background thread to generate the dynamic description (populating the cache)
            t = threading.Thread(
                target=generate_dynamic_room_description,
                kwargs={
                    "room_name": adj_room.name,
                    "base_description": adj_room.description,
                    "is_town": adj_room.is_town,
                    "items": items_list,
                    "npcs": npcs_list,
                    "enemy_name": enemy_name,
                    "enemy_hp_info": enemy_hp_info,
                    "player_name": player_name,
                    "player_class": player_class,
                    "party_members": party_list,
                    "quest_context": quest_context,
                },
                daemon=True,
            )
            t.start()

    def run(self):
        render_title_screen()
        self.character_creation()

        console.print("\n[bold yellow]Welcome to Aetheria MUD, traveler![/bold yellow]")
        console.print(
            "Type [bold cyan]help[/bold cyan] or [bold cyan]l[/bold cyan] to see available commands."
        )

        # Inital look of starting room
        self.render_current_room()

        while self.is_running:
            # Check passive events: combat trigger first
            if (
                self.player.current_room.enemy
                and self.player.current_room.enemy.is_alive
            ):
                self.enter_combat(self.player.current_room.enemy)
                if not self.is_running:
                    break
                continue

            try:
                self.quick_actions = self.get_current_quick_actions()
                render_quick_actions(self.quick_actions)
                command = console.input("\n[bold green]>[/bold green] ")
                self.process_command(command)
            except (KeyboardInterrupt, EOFError):
                self.is_running = False
                console.print("\n[bold red]Goodbye, traveler![/bold red]")

    def character_creation(self):
        """Asks the player for details to initialize their character."""
        console.print("\n[bold purple]=== Character Creation ===[/bold purple]")
        name = ""
        while not name.strip():
            name = console.input("Enter your hero's name: ").strip()

        console.print("\nChoose your starting Class:")
        console.print(
            "1. [bold yellow]Warrior[/bold yellow] - High Health, strong melee skills (Slash, Shield Wall)."
        )
        console.print(
            "2. [bold cyan]Mage[/bold cyan] - Master of spells, low defense but massive spellpower (Fireball, Mana Shield)."
        )
        console.print(
            "3. [bold green]Rogue[/bold green] - Quick strike specialist, high crits (Backstab, Poison Strike)."
        )
        console.print(
            "4. [bold white]Cleric[/bold white] - Holy healer, balances defensive shields with holy magic (Smite, Heal)."
        )

        class_choice = ""
        while class_choice not in [
            "1",
            "2",
            "3",
            "4",
            "warrior",
            "mage",
            "rogue",
            "cleric",
        ]:
            class_choice = console.input("Select Class (1-4 or Name): ").strip().lower()

        char_class = "Warrior"
        if class_choice in ["2", "mage"]:
            char_class = "Mage"
            self.player = Player(
                name=name,
                char_class=char_class,
                hp=90,
                max_hp=90,
                mana=40,
                max_mana=40,
                attack=9,
                defense=4,
            )
        elif class_choice in ["3", "rogue"]:
            char_class = "Rogue"
            self.player = Player(
                name=name,
                char_class=char_class,
                hp=100,
                max_hp=100,
                mana=25,
                max_mana=25,
                attack=14,
                defense=5,
            )
        elif class_choice in ["4", "cleric"]:
            char_class = "Cleric"
            self.player = Player(
                name=name,
                char_class=char_class,
                hp=105,
                max_hp=105,
                mana=30,
                max_mana=30,
                attack=10,
                defense=6,
            )
        else:
            self.player = Player(
                name=name,
                char_class=char_class,
                hp=120,
                max_hp=120,
                mana=15,
                max_mana=15,
                attack=12,
                defense=8,
            )

        # Set player spawn location
        self.player.current_room = self.world["Eldergrove Center"]

    def process_command(self, command_str: str):
        parts = command_str.lower().split()
        if not parts:
            return

        verb = parts[0]
        noun = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Check if verb is a quick action number selection
        if verb.isdigit():
            idx = int(verb) - 1
            if hasattr(self, "quick_actions") and 0 <= idx < len(self.quick_actions):
                _, actual_command = self.quick_actions[idx]
                console.print(f"[dim]⚡ Executing: {actual_command}[/dim]")
                self.process_command(actual_command)
                return
            else:
                console.print("[red]Invalid quick action number.[/red]")
                return

        if verb in ["quit", "exit"]:
            self.is_running = False
            console.print("[bold red]Goodbye![/bold red]")
            return

        elif verb in ["help", "h"]:
            render_help_menu()

        elif verb in ["look", "l"]:
            self.render_current_room()

        elif verb in ["go"] or verb in self.DIRECTIONS:
            direction = (
                self.DIRECTIONS.get(verb, verb)
                if verb != "go"
                else self.DIRECTIONS.get(noun, noun)
            )
            self.move_player(direction)

        elif verb in ["take", "t"]:
            self.take_item(noun)

        elif verb in ["use", "u"]:
            self.use_item(noun)

        elif verb in ["equip", "eq"]:
            self.equip_item(noun)

        elif verb in ["talk", "tk"]:
            self.talk_to_npc(noun)

        elif verb in ["recruit", "rec"]:
            self.recruit_companion(noun)

        elif verb in ["party", "p"]:
            render_full_party_hud(self.player, self.party)

        elif verb in ["quests", "q"]:
            render_quests_log(list(self.quests.values()))

        elif verb in ["inventory", "i"]:
            render_inventory_list(self.player)

        elif verb in ["map", "m"]:
            render_world_map(self.player.current_room.name, self.world)

        elif verb == "save":
            self.handle_save()

        elif verb == "load":
            self.handle_load()

        elif verb in ["voice", "v"]:
            self.toggle_voice()

        else:
            console.print(
                "[red]I don't understand that command. Type 'help' to see options.[/red]"
            )

    def move_player(self, direction: str):
        if not direction or direction not in self.DIRECTIONS:
            console.print(
                "[red]Go where? Specify a valid direction (north, south, east, west).[/red]"
            )
            return

        current_room = self.player.current_room
        next_room = current_room.get_exit(direction)

        if not next_room:
            console.print("[red]You can't go that way.[/red]")
            return

        # Check Locked Doors
        if next_room.locked:
            if next_room.key_needed and self.player.has_item(next_room.key_needed.name):
                console.print(
                    f"[bold green]🔓 You unlock the {next_room.name} using the {next_room.key_needed.name}![/bold green]"
                )
                next_room.locked = False
                # Update quests if unlocking is related to fetch items
                self.update_quest_progress("fetch", next_room.key_needed.name)
            else:
                req_str = (
                    f"You need the {next_room.key_needed.name}."
                    if next_room.key_needed
                    else "It is firmly locked."
                )
                console.print(
                    f"[red]The gate to the {next_room.name} is locked. {req_str}[/red]"
                )
                return

        # Perform the move
        self.player.current_room = next_room
        console.print(
            f"\n[bold green]You travel {direction} to the {next_room.name}.[/bold green]"
        )

        # Display new location info
        self.render_current_room()

        # Trigger dynamic companion exploration banter (30% chance if party is populated)
        if self.party and random.random() < 0.35:
            speaker = random.choice([c for c in self.party if c.is_alive])
            banter = generate_companion_banter(
                speaker.name,
                speaker.personality,
                next_room.name,
                next_room.description,
                speaker.hp,
                speaker.max_hp,
            )
            if banter:
                console.print(f'\n💬 [bold cyan]{speaker.name}[/bold cyan]: "{banter}"')
                TTSManager().speak(banter, speaker.name)

    def take_item(self, item_name: str):
        room = self.player.current_room
        target_item: Any = None
        if not room.items:
            console.print("[red]There is nothing here to take.[/red]")
            return

        if not item_name:
            if len(room.items) == 1:
                target_item = room.items[0]
            else:
                console.print("\n[bold yellow]Items on the floor:[/bold yellow]")
                for idx, item in enumerate(room.items, 1):
                    console.print(
                        f"  {idx}. [bold yellow]{item.name}[/bold yellow] - {item.description}"
                    )
                choice = console.input(
                    "\nSelect item to pick up (Number or Name): "
                ).strip()
                if not choice:
                    return
                try:
                    i_idx = int(choice) - 1
                    if 0 <= i_idx < len(room.items):
                        target_item = room.items[i_idx]
                    else:
                        console.print("[red]Invalid selection.[/red]")
                        return
                except ValueError:
                    # Match by name
                    for item in room.items:
                        if item.name.lower() == choice.lower():
                            target_item = item
                            break
                    else:
                        console.print("[red]Item not found.[/red]")
                        return
        else:
            target_item = None
            for item in room.items:
                if item.name.lower() == item_name.lower():
                    target_item = item
                    break

            if not target_item:
                console.print("[red]Item not found in this room.[/red]")
                return

        room.items.remove(target_item)
        self.player.inventory.append(target_item)
        console.print(
            f"[bold yellow]🎒 Picked up: {target_item.name}[/bold yellow] - {target_item.description}"
        )

        # Check Quest Progress
        self.update_quest_progress("fetch", target_item.name)

    def use_item(self, item_name: str):
        target_item: Any = None
        if not item_name:
            consumables = [
                item for item in self.player.inventory if isinstance(item, Consumable)
            ]
            if not consumables:
                console.print("[red]No usable items in your inventory.[/red]")
                return
            console.print("\n[bold yellow]Available Usable Items:[/bold yellow]")
            for idx, c in enumerate(consumables, 1):
                console.print(
                    f"  {idx}. [bold yellow]{c.name}[/bold yellow] - {c.description}"
                )
            choice = console.input("\nSelect item to use (Number or Name): ").strip()
            if not choice:
                return
            try:
                c_idx = int(choice) - 1
                if 0 <= c_idx < len(consumables):
                    target_item = consumables[c_idx]
                else:
                    console.print("[red]Invalid selection.[/red]")
                    return
            except ValueError:
                # Match by name
                for c in consumables:
                    if c.name.lower() == choice.lower():
                        target_item = c
                        break
                else:
                    console.print("[red]Item not found.[/red]")
                    return
        else:
            # find by name
            target_item = None
            for item in self.player.inventory:
                if item.name.lower() == item_name.lower():
                    target_item = item
                    break
            if not target_item:
                console.print("[red]You don't have that item in your inventory.[/red]")
                return

        if isinstance(target_item, Consumable):
            summary = target_item.use(self.player)
            self.player.inventory.remove(target_item)
            console.print(f"[bold green]✨ {summary}[/bold green]")
        else:
            console.print("[red]That item cannot be consumed.[/red]")

    def equip_item(self, item_name: str):
        target_item: Any = None
        if not item_name:
            equipment_list = [
                item for item in self.player.inventory if isinstance(item, Equipment)
            ]
            if not equipment_list:
                console.print("[red]No equipable gear in your inventory.[/red]")
                return
            console.print("\n[bold yellow]Available Equipable Gear:[/bold yellow]")
            for idx, eq in enumerate(equipment_list, 1):
                console.print(
                    f"  {idx}. [bold cyan]{eq.name}[/bold cyan] [dim]({eq.slot.name})[/dim] - {eq.description}"
                )
            choice = console.input("\nSelect gear to equip (Number or Name): ").strip()
            if not choice:
                return
            try:
                eq_idx = int(choice) - 1
                if 0 <= eq_idx < len(equipment_list):
                    target_item = equipment_list[eq_idx]
                else:
                    console.print("[red]Invalid selection.[/red]")
                    return
            except ValueError:
                # Match by name
                for eq in equipment_list:
                    if eq.name.lower() == choice.lower():
                        target_item = eq
                        break
                else:
                    console.print("[red]Item not found.[/red]")
                    return
        else:
            target_item = None
            for item in self.player.inventory:
                if item.name.lower() == item_name.lower():
                    target_item = item
                    break
            if not target_item:
                console.print("[red]You don't have that item in your inventory.[/red]")
                return

        if isinstance(target_item, Equipment):
            old_eq = self.player.equip(target_item)
            console.print(
                f"[bold cyan]🛡️ Equipped: {target_item.name} in slot [{target_item.slot.name}][/bold cyan]"
            )
            if old_eq:
                console.print(
                    f"[dim]Returned {old_eq.name} back to inventory bag.[/dim]"
                )
        else:
            console.print("[red]That item cannot be equipped as armaments.[/red]")

    def talk_to_npc(self, target_arg: str):
        """AI Enabled dialogue extraction with Gemini Pro."""
        npc: Any = None
        topic_sub: Any = None
        room = self.player.current_room
        if not room.npcs:
            console.print("[red]There is no one here to talk to.[/red]")
            return

        # If target_arg is empty, select the npc
        if not target_arg:
            if len(room.npcs) == 1:
                npc = room.npcs[0]
                topic_sub = "hello"
            else:
                console.print("\n[bold yellow]People present:[/bold yellow]")
                for idx, n in enumerate(room.npcs, 1):
                    console.print(f"  {idx}. [bold cyan]{n.name}[/bold cyan]")
                choice = console.input(
                    "\nSelect person to talk to (Number or Name): "
                ).strip()
                if not choice:
                    return
                try:
                    n_idx = int(choice) - 1
                    if 0 <= n_idx < len(room.npcs):
                        npc = room.npcs[n_idx]
                        topic_sub = "hello"
                    else:
                        console.print("[red]Invalid selection.[/red]")
                        return
                except ValueError:
                    # Match by name
                    for n in room.npcs:
                        if (
                            n.name.lower().startswith(choice.lower())
                            or choice.lower() in n.name.lower()
                        ):
                            npc = n
                            topic_sub = "hello"
                            break
                    else:
                        console.print("[red]No such person here.[/red]")
                        return
        else:
            # We expect syntax:
            # 1. talk [npc] about [topic]
            # 2. talk [npc] [topic] (e.g., from quick actions: talk Tavernkeeper Barnaby quest)
            # Clean target string
            clean_arg = target_arg.replace("to ", "").strip()

            npc = None
            topic_sub = "hello"

            # A. If "about" is present, split on it case-insensitively
            if "about" in clean_arg.lower():
                import re

                parts = re.split(r"\babout\b", clean_arg, flags=re.IGNORECASE)
                npc_sub = parts[0].strip()
                topic_sub = parts[1].strip() if len(parts) > 1 else "hello"

                # Match NPC based on npc_sub
                for n in room.npcs:
                    if (
                        n.name.lower().startswith(npc_sub.lower())
                        or npc_sub.lower() in n.name.lower()
                    ):
                        npc = n
                        break
            else:
                # B. No "about" keyword (e.g. "talk Tavernkeeper Barnaby quest" or "talk Barnaby hello")
                # Sort NPCs by name length descending to match longer names first
                sorted_npcs = sorted(room.npcs, key=lambda x: len(x.name), reverse=True)

                # 1. Try exact or full prefix match on NPC name
                for n in sorted_npcs:
                    n_name_l = n.name.lower()
                    c_arg_l = clean_arg.lower()
                    if c_arg_l == n_name_l:
                        npc = n
                        topic_sub = "hello"
                        break
                    elif c_arg_l.startswith(n_name_l + " "):
                        npc = n
                        topic_sub = clean_arg[len(n.name) :].strip()
                        break

                # 2. Try matching by sub-words of the NPC name (e.g. "Barnaby" in "Barnaby quest")
                if not npc:
                    for n in sorted_npcs:
                        npc_words = [
                            w.strip()
                            for w in n.name.lower().split()
                            if len(w.strip()) > 1
                        ]
                        for word in npc_words:
                            if clean_arg.lower() == word:
                                npc = n
                                topic_sub = "hello"
                                break
                            elif clean_arg.lower().startswith(word + " "):
                                npc = n
                                topic_sub = clean_arg[len(word) :].strip()
                                break
                        if npc:
                            break

                # 3. Fallback: Entire clean_arg matches or is substring of NPC name
                if not npc:
                    for n in room.npcs:
                        if (
                            n.name.lower().startswith(clean_arg.lower())
                            or clean_arg.lower() in n.name.lower()
                        ):
                            npc = n
                            topic_sub = "hello"
                            break

            if not npc:
                console.print(
                    "[red]Who are you trying to speak to? No such character is present here.[/red]"
                )
                return

        # Fetch active quest information for contextual dialogue
        quest_context = "No major events."
        active_ids = self.player.active_quests
        if active_ids:
            quest_context = ", ".join(
                self.quests[qid].name for qid in active_ids if qid in self.quests
            )

        console.print(
            f'\n💬 [bold green]You ask {npc.name} about: "{topic_sub}"...[/bold green]'
        )

        # Build detailed player context and companion list
        party_members = [(c.name, c.char_class) for c in self.party]
        inventory_items = [item.name for item in self.player.inventory]

        # Pull history from npc
        if not hasattr(npc, "dialogue_history"):
            npc.dialogue_history = []

        # Trigger Gemini generated response with procedural fallback
        dialogue = generate_npc_dialogue(
            npc_name=npc.name,
            persona=npc.persona,
            topic=topic_sub,
            player_name=self.player.name,
            player_class=self.player.char_class,
            player_level=self.player.level,
            player_hp=self.player.hp,
            player_max_hp=self.player.max_hp,
            party_members=party_members,
            inventory_items=inventory_items,
            quest_context=quest_context,
            dialogue_history=list(npc.dialogue_history),
        )

        # Append this exchange to history (limit to last 5 turns / 10 lines)
        npc.dialogue_history.append((self.player.name, topic_sub))
        npc.dialogue_history.append((npc.name, dialogue))
        if len(npc.dialogue_history) > 10:
            npc.dialogue_history = npc.dialogue_history[-10:]

        console.print(f"[bold cyan]{npc.name}[/bold cyan]: {dialogue}")
        TTSManager().speak(dialogue, npc.name)

        # Quest Triggering and Complete checks (Special interactive NPCs)
        if npc.name == "Tavernkeeper Barnaby" and "quest" in topic_sub.lower():
            self.trigger_quest_acceptance("q_eldergrove_goblins")

        elif npc.name == "Priestess Althea" and "quest" in topic_sub.lower():
            # Priestess rewards and triggers Forest Ancient main boss quest
            if "q_eldergrove_goblins" in self.player.completed_quests:
                self.trigger_quest_acceptance("q_eldergrove_sigil")
            else:
                console.print(
                    f"[bold cyan]{npc.name}[/bold cyan]: 'Help Barnaby with his goblin problem first, traveler, then I shall outline your true trial.'"
                )

        elif npc.name == "Quartermaster Elena" and "quest" in topic_sub.lower():
            # Quartermaster Elena gives final boss quest
            self.trigger_quest_acceptance("q_silverlight_malakor")

        # Handle quest completion payouts if speaking to specific quest givers
        self.check_quest_hand_in(npc.name)

    def recruit_companion(self, name_arg: str):
        companion: Any = None
        room = self.player.current_room
        if room.name != "Eldergrove Tavern (The Golden Oak)":
            console.print(
                "[red]Companions can only be recruited inside the Eldergrove Tavern.[/red]"
            )
            return

        if len(self.party) >= MAX_PARTY_SIZE - 1:
            console.print(
                "[red]Your adventure party is already full (Max 4 members).[/red]"
            )
            return

        if not self.tavern_companions:
            console.print("[red]No recruitable companions remain here.[/red]")
            return

        if not name_arg:
            console.print(
                "\n[bold yellow]Recruitable Companions present:[/bold yellow]"
            )
            for idx, comp in enumerate(self.tavern_companions, 1):
                console.print(
                    f"  {idx}. [bold cyan]{comp.name}[/bold cyan] ({comp.char_class}) - {comp.personality}"
                )
            choice = console.input(
                "\nSelect companion to recruit (Number or Name): "
            ).strip()
            if not choice:
                return
            try:
                c_idx = int(choice) - 1
                if 0 <= c_idx < len(self.tavern_companions):
                    companion = self.tavern_companions[c_idx]
                else:
                    console.print("[red]Invalid selection.[/red]")
                    return
            except ValueError:
                # Match by name
                for comp in self.tavern_companions:
                    if comp.name.lower() == choice.lower():
                        companion = comp
                        break
                else:
                    console.print("[red]No such companion present here.[/red]")
                    return
        else:
            companion = None
            for comp in self.tavern_companions:
                if comp.name.lower() == name_arg.lower():
                    companion = comp
                    break

            if not companion:
                print_msg = f"[red]No companion named '{name_arg}' is currently here waiting to be hired.[/red]"
                console.print(print_msg)
                return

        # Remove from Tavern pool, add to active Party
        self.tavern_companions.remove(companion)
        self.party.append(companion)
        console.print(
            f"\n🎉 [bold yellow]{companion.name} the {companion.char_class} has joined your party![/bold yellow]"
        )
        console.print(
            f'💬 [bold cyan]{companion.name}[/bold cyan]: "Greetings. I am ready to explore the depths. Lead the way."'
        )
        TTSManager().speak(
            "Greetings. I am ready to explore the depths. Lead the way.", companion.name
        )

    def enter_combat(self, enemy: Enemy):
        combat = CombatManager(self.player, self.party, enemy)
        round_log = [
            f"A wild [bold red]{enemy.name}[/bold red] blocking the way jumps out to attack!"
        ]

        while combat.is_active:
            render_combat_screen(self.player, self.party, enemy, round_log)

            # 1. Ask for player action
            console.print(
                "\n[bold yellow]Actions:[/bold yellow] [bold white]1. Attack | 2. Spell | 3. Item | 4. Defend | 5. Flee[/bold white]"
            )
            choice = (
                console.input("Choose combat action (1-5 or Name): ").strip().lower()
            )

            action = "attack"
            spell = None
            consumable = None

            if choice in ["2", "spell"]:
                # Cast Spells list
                if not self.player.spells:
                    console.print(
                        "[red]You have no active abilities/spells to cast![/red]"
                    )
                    continue

                console.print("\nAvailable Spells:")
                for idx, s in enumerate(self.player.spells, 1):
                    console.print(f"{idx}. {s}")

                s_choice = console.input("Select Spell (Number or Name): ").strip()
                try:
                    s_idx = int(s_choice) - 1
                    if 0 <= s_idx < len(self.player.spells):
                        spell = self.player.spells[s_idx]
                        action = "spell"
                    else:
                        console.print("[red]Invalid index choice.[/red]")
                        continue
                except ValueError:
                    # Match by spell name
                    for s in self.player.spells:
                        if s.name.lower() == s_choice.lower():
                            spell = s
                            action = "spell"
                            break
                    if not spell:
                        console.print("[red]Spell not recognized.[/red]")
                        continue

            elif choice in ["3", "item"]:
                consumables = [
                    item
                    for item in self.player.inventory
                    if isinstance(item, Consumable)
                ]
                if not consumables:
                    console.print(
                        "[red]No healing potions or elixirs in your backpack.[/red]"
                    )
                    continue

                console.print("\nConsumables:")
                for idx, c in enumerate(consumables, 1):
                    console.print(f"{idx}. {c.name} - {c.description}")

                c_choice = console.input("Select Consumable (Number or Name): ").strip()
                try:
                    c_idx = int(c_choice) - 1
                    if 0 <= c_idx < len(consumables):
                        consumable = consumables[c_idx]
                        action = "item"
                    else:
                        console.print("[red]Invalid index choice.[/red]")
                        continue
                except ValueError:
                    for c in consumables:
                        if c.name.lower() == c_choice.lower():
                            consumable = c
                            action = "item"
                            break
                    if not consumable:
                        console.print("[red]Item not recognized.[/red]")
                        continue

            elif choice in ["4", "defend"]:
                action = "defend"

            elif choice in ["5", "flee"]:
                if combat.attempt_flee():
                    console.print(
                        "[bold yellow]🏃 You managed to escape and flee the fight![/bold yellow]"
                    )
                    # Move player back to starting room (Eldergrove Center)
                    self.player.current_room = self.world["Eldergrove Center"]
                    return
                else:
                    console.print("[red]Flee failed! You couldn't get away![/red]")
                    action = "attack"

            # Execute Round
            round_log = combat.execute_round(action, spell, consumable)

            # Voice combat banter if enabled
            import re

            for log in round_log:
                match = re.search(r"\[dim\]([^:]+):\s*\"([^\"]+)\"\[/dim\]", log)
                if match:
                    speaker_name = match.group(1).strip()
                    banter_text = match.group(2).strip()
                    TTSManager().speak(banter_text, speaker_name)

        # Post Combat Cleanup
        if combat.fled:
            return

        if not enemy.is_alive:
            # Drop Special Quest Key Items
            if enemy.name == "The Forest Ancient":
                sigil = Item(
                    "Aether Sigil",
                    "A glowing crystal sigil left behind by the Forest Ancient.",
                    value=0,
                    is_quest_item=True,
                )
                self.player.inventory.append(sigil)
                console.print(
                    f"\n🌟 [bold yellow]Loot Found: {sigil.name}[/bold yellow] - dropped by the defeated boss!"
                )
                self.update_quest_progress("fetch", sigil.name)

            elif enemy.name == "Void Horror":
                void_key = Item(
                    "Void Key",
                    "A heavy dark metal key humming with void energy.",
                    value=0,
                    is_quest_item=True,
                )
                self.player.inventory.append(void_key)
                console.print(
                    f"\n🌟 [bold yellow]Loot Found: {void_key.name}[/bold yellow] - dropped by the horror!"
                )
                self.update_quest_progress("fetch", void_key.name)

            elif enemy.name == "Archmage Malakor":
                # Final Game Win trigger!
                console.print("\n" + "=" * 80)
                console.print(
                    "🏆 [bold gold1]CONGRATULATIONS! YOU HAVE SAVED AETHERIA![/bold gold1] 🏆",
                    justify="center",
                )
                console.print("=" * 80)
                victory_msg = (
                    "With a final mighty strike, Archmage Malakor is defeated! "
                    "The dark rift collapses, and sweet light returns to the lands."
                )
                console.print(victory_msg)
                celebration_msg = "You are celebrated as the Grand Hero of Eldergrove and Silverlight Keep!"
                console.print(celebration_msg)
                console.print("Thank you for playing Aetheria Text RPG!")
                TTSManager().speak(
                    f"{victory_msg} {celebration_msg} Thank you for playing Aetheria Text RPG!",
                    "Narrator",
                )
                self.is_running = False
                return

            # Check quest kill conditions
            self.update_quest_progress("kill", enemy.name)
            # Nullify enemy in room
            self.player.current_room.enemy = None

        elif not self.player.is_alive:
            self.handle_player_death()

    def handle_player_death(self):
        """Warp players safely to Eldergrove Temple upon death, charging gold fee."""
        console.print("\n" + "=" * 80)
        console.print("💀 [bold red]YOU HAVE DIED[/bold red] 💀", justify="center")
        console.print("=" * 80)

        gold_fee = int(self.player.gold * BASE_RESPAWN_GOLD_PENALTY_PCT)
        self.player.gold = max(0, self.player.gold - gold_fee)

        # Warp to Temple
        self.player.current_room = self.world["Eldergrove Temple (Aether Sanctuary)"]
        self.player.hp = self.player.max_hp
        self.player.mana = self.player.max_mana

        # Revive all companions with half HP
        for comp in self.party:
            comp.hp = int(comp.max_hp * 0.5)
            comp.mana = comp.max_mana

        death_msg = (
            "Priestess Althea channels the light of the Aether to restore your soul."
        )
        console.print(death_msg)
        revive_msg = f"You revive inside the sanctuary. Deducted [bold yellow]{gold_fee}[/bold yellow] Gold coin fee as tithing."
        console.print(revive_msg)
        TTSManager().speak(f"{death_msg} You revive inside the sanctuary.", "Narrator")
        self.render_current_room()

    def trigger_quest_acceptance(self, quest_id: str):
        if quest_id not in self.quests:
            return

        quest = self.quests[quest_id]
        if quest.status == "inactive" and quest_id not in self.player.completed_quests:
            quest.status = "active"
            self.player.active_quests.append(quest_id)
            console.print(
                f"\n📜 [bold yellow]Quest Accepted: {quest.name}[/bold yellow] - {quest.description}"
            )

            if quest.objective_type == "fetch":
                item_count = len(
                    [
                        item
                        for item in self.player.inventory
                        if item.name.lower() == quest.objective_target.lower()
                    ]
                )
                quest.count_current = min(quest.count_needed, item_count)

    def check_quest_hand_in(self, npc_name: str):
        # Determine who hands in which quests
        hand_in_map = {
            "Tavernkeeper Barnaby": "q_eldergrove_goblins",
            "Priestess Althea": "q_eldergrove_sigil",
            "Quartermaster Elena": "q_silverlight_malakor",
        }

        if npc_name not in hand_in_map:
            return

        qid = hand_in_map[npc_name]
        if qid not in self.player.active_quests:
            return

        quest = self.quests[qid]
        if quest.status == "active" and quest.is_objective_met:
            # Reward payout!
            quest.status = "completed"
            self.player.active_quests.remove(qid)
            self.player.completed_quests.append(qid)

            # Consume Quest Items if fetch objective
            if quest.objective_type == "fetch":
                # Find and remove from player inventory
                removed = 0
                for item in list(self.player.inventory):
                    if item.name.lower() == quest.objective_target.lower():
                        self.player.inventory.remove(item)
                        removed += 1
                        if removed >= quest.count_needed:
                            break

            self.player.gold += quest.gold_reward
            console.print(
                f"\n🎉 [bold green]QUEST COMPLETED: {quest.name}![/bold green]"
            )
            console.print(
                f"Received rewards: [bold yellow]{quest.gold_reward} Gold[/bold yellow] and [bold cyan]{quest.xp_reward} XP[/bold cyan]!"
            )

            lvl_announcements = self.player.gain_xp(quest.xp_reward)
            for ann in lvl_announcements:
                console.print(ann)

    def update_quest_progress(self, obj_type: str, target_name: str, amount: int = 1):
        for qid in self.player.active_quests:
            quest = self.quests[qid]
            changed = quest.update_progress(obj_type, target_name, amount)
            if changed:
                console.print(
                    f"[bold yellow]⚡ Quest Progress: {quest.name} ({quest.count_current}/{quest.count_needed})[/bold yellow]"
                )

    def handle_save(self):
        success = save_game(
            self.player,
            self.party,
            self.world,
            self.quests,
            self.player.current_room.name,
            self.tavern_companions,
        )
        if success:
            console.print(
                f"[bold green]💾 Game successfully saved to '{SAVE_FILE_NAME}'![/bold green]"
            )
        else:
            console.print(
                "[bold red]❌ Error: Unable to save game progress.[/bold red]"
            )

    def handle_load(self):
        try:
            p, pt, w, q, rname, tav, was_recovered = load_game(self.world, self.quests)
            self.player = p
            self.party = pt
            self.world = w
            self.quests = q
            self.tavern_companions = tav

            if was_recovered:
                console.print(
                    "[bold yellow]⚠️ WARNING: Primary save file was corrupted or missing! Game successfully recovered from automatic backup (.bak).[/bold yellow]"
                )
            else:
                console.print(
                    "[bold green]💾 Save game file successfully loaded![/bold green]"
                )
            self.render_current_room()
        except Exception as e:
            console.print(f"[bold red]❌ Error loading save game: {e}[/bold red]")

    def toggle_voice(self):
        tts = TTSManager()
        tts.voice_enabled = not tts.voice_enabled
        status = "ON" if tts.voice_enabled else "OFF"
        console.print(f"\n📢 [bold green]Voice settings toggled: {status}[/bold green]")
        if tts.voice_enabled:
            tts.speak(
                "Voice narration is now enabled. Welcome to Aetheria.", "Narrator"
            )
        else:
            tts.stop_playback()


if __name__ == "__main__":
    controller = GameController()
    controller.run()
