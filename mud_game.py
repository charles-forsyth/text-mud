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
from aetheria.quests import get_default_quests, QuestObserver
from aetheria.events import EventDispatcher, EventType
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
    render_world_map,
    TerminalScreen,
    clear_and_home_screen,
    show_terminal_cursor,
    render_action_log,
    interactive_prompt,
)


def is_layout_line(line: str) -> bool:
    """Helper to detect if a line is part of a TUI panel or layout border to prevent capture pollution."""
    # Box Drawing range (0x2500 - 0x257F) and Block Elements range (0x2580 - 0x259F)
    for c in line:
        if 0x2500 <= ord(c) <= 0x259F:
            return True
    if "\033[" in line or "\x1b[" in line:
        return True
    return False


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

        # Thread-safe queue for sequential prewarming tasks
        import queue

        self._prewarm_queue = queue.Queue()
        self._prewarm_thread = None
        self._start_prewarm_worker_if_needed()

        self.quests_observer = QuestObserver(self)
        self.quests_observer.register_listeners()
        self.message_log: list[str] = []
        self.is_capturing = False

        # Initialize weather engine, clock, and scheduled NPCs for Phase 3
        from aetheria.weather import WeatherEngine
        from aetheria.navigation import LivingWorldClock, ScheduledNPC

        self.weather_engine = WeatherEngine()
        self.world_clock = LivingWorldClock()

        self.scheduled_npcs: list[ScheduledNPC] = []
        althea = None
        thorin = None
        for room in self.world.values():
            for npc in room.npcs:
                if npc.name == "Priestess Althea":
                    althea = npc
                elif npc.name == "Blacksmith Thorin":
                    thorin = npc

        if althea:
            self.scheduled_npcs.append(
                ScheduledNPC(
                    althea,
                    {
                        "Dawn": "Eldergrove Center",
                        "Day": "Eldergrove Temple (Aether Sanctuary)",
                        "Dusk": "Eldergrove Center",
                        "Night": "Eldergrove Tavern (The Golden Oak)",
                    },
                )
            )
        if thorin:
            self.scheduled_npcs.append(
                ScheduledNPC(
                    thorin,
                    {
                        "Dawn": "Eldergrove Blacksmith (Iron & Ash)",
                        "Day": "Eldergrove Blacksmith (Iron & Ash)",
                        "Dusk": "Eldergrove Center",
                        "Night": "Eldergrove Tavern (The Golden Oak)",
                    },
                )
            )

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

    def render_current_room(self, quick_actions=None, current_input=""):
        """Generates dynamic descriptive context and renders the beautiful room panel."""
        if self.is_capturing:
            return
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
            room,
            self.party,
            self.player,
            dynamic_description=dynamic_desc,
            world=self.world,
            weather_engine=self.weather_engine,
            world_clock=self.world_clock,
            message_log=self.message_log,
            quick_actions=quick_actions,
            current_input=current_input,
        )
        render_action_log(self.message_log)

        TTSManager().speak(dynamic_desc, "Narrator")

        # Predictive prewarming of adjacent rooms' descriptions in background threads
        self._prewarm_adjacent_rooms(room)

    def _start_prewarm_worker_if_needed(self):
        """Lazily spawns the background prewarm worker thread if needed."""
        import threading

        if self._prewarm_thread is None or not self._prewarm_thread.is_alive():
            self._prewarm_thread = threading.Thread(
                target=self._prewarm_worker_loop,
                daemon=True,
            )
            self._prewarm_thread.start()

    def _prewarm_worker_loop(self):
        """Background worker thread that sequentializes Gemini prewarming calls with throttling."""
        import time
        from aetheria.ai_engine import generate_dynamic_room_description

        while True:
            try:
                task = self._prewarm_queue.get()
                if task is None:
                    break
                generate_dynamic_room_description(**task)
                self._prewarm_queue.task_done()
                time.sleep(0.5)  # Safe throttling gap
            except Exception:
                pass

    def _prewarm_adjacent_rooms(self, current_room):
        """Identifies all adjacent rooms and queues sequential tasks to pre-generate their dynamic descriptions."""
        # Avoid prewarming if player is not fully initialized
        if not self.player:
            return

        # Ensure worker is alive
        self._start_prewarm_worker_if_needed()

        # Clear any pending prewarm tasks in queue to focus on the new room's exits
        while not self._prewarm_queue.empty():
            try:
                self._prewarm_queue.get_nowait()
                self._prewarm_queue.task_done()
            except Exception:
                break

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

            # Queue the prewarm task
            self._prewarm_queue.put(
                {
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
                }
            )

    def run(self):
        render_title_screen()
        self.character_creation()

        with TerminalScreen():
            # Initial look of starting room is done on the first loop tick
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
                    clear_and_home_screen()
                    self.quick_actions = self.get_current_quick_actions()

                    prompt_style = "\x1b[32m\x1b[1m> \x1b[0m"

                    def redraw_overworld(buffer_text: str):
                        clear_and_home_screen()
                        self.quick_actions = self.get_current_quick_actions()
                        self.render_current_room(
                            quick_actions=self.quick_actions, current_input=buffer_text
                        )
                        sys.stdout.write(prompt_style + buffer_text)
                        sys.stdout.flush()

                    show_terminal_cursor(True)
                    command = interactive_prompt(
                        valid_exits=list(self.player.current_room.exits.keys()),
                        prompt_text=prompt_style,
                        on_change=redraw_overworld,
                    )
                    show_terminal_cursor(False)

                    if self.is_heavy_command(command):
                        self.process_command(command)
                    else:
                        try:
                            self.is_capturing = True
                            with console.capture() as capture:
                                self.process_command(command)
                        finally:
                            self.is_capturing = False
                        captured_output = capture.get()
                        if captured_output.strip():
                            for line in captured_output.split("\n"):
                                line_stripped = line.strip()
                                if line_stripped:
                                    if not is_layout_line(line_stripped):
                                        self.message_log.append(line)
                except (KeyboardInterrupt, EOFError):
                    self.is_running = False

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

    def is_heavy_command(self, command_str: str) -> bool:
        parts = command_str.lower().split()
        if not parts:
            return False
        verb = parts[0]
        if verb.isdigit():
            idx = int(verb) - 1
            if hasattr(self, "quick_actions") and 0 <= idx < len(self.quick_actions):
                _, actual_command = self.quick_actions[idx]
                return self.is_heavy_command(actual_command)
        return verb in [
            "help",
            "h",
            "party",
            "p",
            "quests",
            "q",
            "inventory",
            "i",
            "map",
            "m",
            "talents",
            "t",
        ]

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
            clear_and_home_screen()
            render_help_menu()
            show_terminal_cursor(True)
            console.input(
                "\n[bold yellow]Press Enter to return to game...[/bold yellow]"
            )
            show_terminal_cursor(False)

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
            clear_and_home_screen()
            render_full_party_hud(self.player, self.party)
            show_terminal_cursor(True)
            console.input(
                "\n[bold yellow]Press Enter to return to game...[/bold yellow]"
            )
            show_terminal_cursor(False)

        elif verb in ["quests", "q"]:
            clear_and_home_screen()
            render_quests_log(list(self.quests.values()))
            show_terminal_cursor(True)
            console.input(
                "\n[bold yellow]Press Enter to return to game...[/bold yellow]"
            )
            show_terminal_cursor(False)

        elif verb in ["inventory", "i"]:
            clear_and_home_screen()
            render_inventory_list(self.player)
            show_terminal_cursor(True)
            console.input(
                "\n[bold yellow]Press Enter to return to game...[/bold yellow]"
            )
            show_terminal_cursor(False)

        elif verb in ["map", "m"]:
            clear_and_home_screen()
            render_world_map(self.player.current_room.name, self.world)
            show_terminal_cursor(True)
            console.input(
                "\n[bold yellow]Press Enter to return to game...[/bold yellow]"
            )
            show_terminal_cursor(False)

        elif verb in ["talents", "t"]:
            self.show_talents_screen()

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

    def show_talents_screen(self):
        """Renders an interactive, fullscreen double-buffered Talent point allocation menu."""
        from rich.panel import Panel
        from rich.table import Table

        while True:
            clear_and_home_screen()
            tree = self.player.talent_tree
            sp = self.player.skill_points

            table = Table(
                title=f"✨ [bold gold1]{self.player.name}'s {self.player.char_class} Talent Tree ({sp} SP Available)[/bold gold1]",
                expand=True,
            )
            table.add_column("ID", style="cyan", width=15)
            table.add_column("Talent Node Name", style="bold yellow")
            table.add_column("Description", style="white")
            table.add_column("Rank", style="green", justify="center")
            table.add_column("Prerequisites", style="magenta")
            table.add_column("Status", style="bold blue")

            for nid, node in tree.nodes.items():
                prereqs = (
                    ", ".join(node.prerequisites) if node.prerequisites else "None"
                )
                status = (
                    "[bold green]MAX[/bold green]"
                    if node.current_rank >= node.max_rank
                    else (
                        "[green]Available[/green]"
                        if tree.can_allocate(nid, sp)
                        else "[red]Locked[/red]"
                    )
                )
                table.add_row(
                    nid,
                    node.name,
                    node.description,
                    f"{node.current_rank}/{node.max_rank}",
                    prereqs,
                    status,
                )

            console.print(
                Panel(
                    table,
                    subtitle="Commands: 'allocate <id>' to invest SP | 'exit' to return",
                )
            )
            show_terminal_cursor(True)
            choice = console.input("\nChoose an option: ").strip().lower()
            show_terminal_cursor(False)

            if choice == "exit" or not choice:
                break

            if choice.startswith("allocate "):
                target_id = choice.split(" ", 1)[1].strip()
                if target_id in tree.nodes:
                    success = tree.allocate(target_id, self.player)
                    if success:
                        # Sync current hp/mana pools to new stat capacities
                        self.player.hp = min(self.player.hp, self.player.max_hp)
                        self.player.mana = min(self.player.mana, self.player.max_mana)
                        self.message_log.append(
                            f"[bold green]Allocated 1 SP to {tree.nodes[target_id].name}![/bold green]"
                        )
                    else:
                        self.message_log.append(
                            "[red]Cannot allocate point. Requirements not met or no SP remaining.[/red]"
                        )
                else:
                    self.message_log.append("[red]Invalid talent node ID.[/red]")

    def tick_world_simulation(self):
        """Safely ticks time-of-day clock and updates scheduled NPC coordinates."""
        # 1. Tick Clock
        clock_announcement = self.world_clock.tick_movement()
        if clock_announcement:
            self.message_log.append(clock_announcement)

        # 2. Advance NPC Schedules safely (preventing mutating list-size runtime errors)
        current_time = self.world_clock.current_time

        npcs_moved = []
        for s_npc in self.scheduled_npcs:
            log_line = s_npc.update_location(current_time, self.world)
            if log_line:
                npcs_moved.append(log_line)

        # Print movements to logs if the player is in the same source/destination room
        player_room_name = self.player.current_room.name
        for log in npcs_moved:
            if player_room_name in log:
                self.message_log.append(log)

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
                # Dispatch event if unlocking is related to fetch items
                EventDispatcher.dispatch(
                    EventType.ITEM_ACQUIRED, {"item_name": next_room.key_needed.name}
                )
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

        # 1. Tick Global Weather
        weather_announcement = self.weather_engine.tick()
        if weather_announcement:
            self.message_log.append(weather_announcement)

        # 2. Resolve Environmental Hazards in Next Room (if any)
        if next_room.hazard:
            hazard_log = next_room.hazard.resolve_tick(self.player)
            if hazard_log:
                self.message_log.append(hazard_log)
                if "[bold red]" in hazard_log:
                    TTSManager().speak(
                        "Warning: environmental hazard encountered.", "System"
                    )

        # 3. Tick world clock and scheduled NPCs
        self.tick_world_simulation()

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

        # Dispatch event for item acquired
        EventDispatcher.dispatch(
            EventType.ITEM_ACQUIRED, {"item_name": target_item.name}
        )

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
            affinity=getattr(npc, "affinity", 0),
            relationship_flags=getattr(npc, "relationship_flags", []),
        )

        # Parse sentiment shift and flag tags from response
        import re

        clean_dialogue = dialogue

        # 1. Parse sentiment shift tags: <sentiment_shift: +/-X>
        shift_match = re.search(r"<sentiment_shift:\s*([+-]?\d+)>", dialogue)
        if shift_match:
            try:
                shift_val = int(shift_match.group(1))
                npc.affinity = max(
                    -100, min(100, getattr(npc, "affinity", 0) + shift_val)
                )
                clean_dialogue = clean_dialogue.replace(shift_match.group(0), "")
            except ValueError:
                pass

        # 2. Parse relationship memory flag tags: <add_flag: flag_name>
        flag_match = re.search(r"<add_flag:\s*([a-zA-Z0-9_]+)>", dialogue)
        if flag_match:
            flag_val = flag_match.group(1)
            if not hasattr(npc, "relationship_flags") or npc.relationship_flags is None:
                npc.relationship_flags = []
            if flag_val not in npc.relationship_flags:
                npc.relationship_flags.append(flag_val)
            clean_dialogue = clean_dialogue.replace(flag_match.group(0), "")

        clean_dialogue = clean_dialogue.strip()

        # Dispatch event for spoken NPC
        EventDispatcher.dispatch(
            EventType.NPC_SPOKEN, {"npc_name": npc.name, "topic": topic_sub}
        )

        # Append this exchange to history (limit to last 5 turns / 10 lines)
        npc.dialogue_history.append((self.player.name, topic_sub))
        npc.dialogue_history.append((npc.name, clean_dialogue))
        if len(npc.dialogue_history) > 10:
            npc.dialogue_history = npc.dialogue_history[-10:]

        console.print(f"[bold cyan]{npc.name}[/bold cyan]: {clean_dialogue}")
        TTSManager().speak(clean_dialogue, npc.name)

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

        # Scale companion level to match player level
        scaled_up_levels = 0
        while companion.level < self.player.level:
            companion.level_up()
            scaled_up_levels += 1

        # Remove from Tavern pool, add to active Party
        self.tavern_companions.remove(companion)
        self.party.append(companion)
        console.print(
            f"\n🎉 [bold yellow]{companion.name} the {companion.char_class} has joined your party![/bold yellow]"
        )
        if scaled_up_levels > 0:
            console.print(
                f"🌟 [bold yellow]{companion.name}[/bold yellow] scaled up {scaled_up_levels} levels to match your experience (Level {companion.level})!"
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
            # 1. Ask for player action with live autocompletion
            prompt_str = "\x1b[33m\x1b[1mChoose combat action (1-5 or Name): \x1b[0m"

            def redraw_combat(buffer_text: str):
                clear_and_home_screen()
                render_combat_screen(
                    self.player,
                    self.party,
                    enemy,
                    round_log,
                    current_input=buffer_text,
                )
                sys.stdout.write(prompt_str + buffer_text)
                sys.stdout.flush()

            show_terminal_cursor(True)
            choice = (
                interactive_prompt(
                    valid_exits=[],
                    prompt_text=prompt_str,
                    on_change=redraw_combat,
                )
                .strip()
                .lower()
            )
            show_terminal_cursor(False)

            action = "attack"
            spell = None
            consumable = None

            if choice in ["2", "spell"]:
                # Cast Spells list
                if not self.player.spells:
                    round_log.append(
                        "[bold red]You have no active abilities/spells to cast![/bold red]"
                    )
                    continue

                prompt_spell = "\x1b[36m\x1b[1mSelect Spell (Number or Name): \x1b[0m"

                def redraw_spell_selection(buffer_text: str):
                    clear_and_home_screen()
                    render_combat_screen(
                        self.player,
                        self.party,
                        enemy,
                        round_log,
                        current_input="spell " + buffer_text,
                    )
                    sys.stdout.write(prompt_spell + buffer_text)
                    sys.stdout.flush()

                show_terminal_cursor(True)
                s_choice = interactive_prompt(
                    valid_exits=[],
                    prompt_text=prompt_spell,
                    on_change=redraw_spell_selection,
                ).strip()
                show_terminal_cursor(False)

                try:
                    s_idx = int(s_choice) - 1
                    if 0 <= s_idx < len(self.player.spells):
                        spell = self.player.spells[s_idx]
                        action = "spell"
                    else:
                        round_log.append("[bold red]Invalid index choice.[/bold red]")
                        continue
                except ValueError:
                    # Match by spell name
                    for s in self.player.spells:
                        if s.name.lower() == s_choice.lower():
                            spell = s
                            action = "spell"
                            break
                    if not spell:
                        round_log.append("[bold red]Spell not recognized.[/bold red]")
                        continue

            elif choice in ["3", "item"]:
                consumables = [
                    item
                    for item in self.player.inventory
                    if isinstance(item, Consumable)
                ]
                if not consumables:
                    round_log.append(
                        "[bold red]No healing potions or elixirs in your backpack.[/bold red]"
                    )
                    continue

                prompt_item = (
                    "\x1b[35m\x1b[1mSelect Consumable (Number or Name): \x1b[0m"
                )

                def redraw_item_selection(buffer_text: str):
                    clear_and_home_screen()
                    render_combat_screen(
                        self.player,
                        self.party,
                        enemy,
                        round_log,
                        current_input="item " + buffer_text,
                    )
                    sys.stdout.write(prompt_item + buffer_text)
                    sys.stdout.flush()

                show_terminal_cursor(True)
                c_choice = interactive_prompt(
                    valid_exits=[],
                    prompt_text=prompt_item,
                    on_change=redraw_item_selection,
                ).strip()
                show_terminal_cursor(False)

                try:
                    c_idx = int(c_choice) - 1
                    if 0 <= c_idx < len(consumables):
                        consumable = consumables[c_idx]
                        action = "item"
                    else:
                        round_log.append("[bold red]Invalid index choice.[/bold red]")
                        continue
                except ValueError:
                    for c in consumables:
                        if c.name.lower() == c_choice.lower():
                            consumable = c
                            action = "item"
                            break
                    if not consumable:
                        round_log.append("[bold red]Item not recognized.[/bold red]")
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
                EventDispatcher.dispatch(
                    EventType.ITEM_ACQUIRED, {"item_name": sigil.name}
                )

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
                EventDispatcher.dispatch(
                    EventType.ITEM_ACQUIRED, {"item_name": void_key.name}
                )

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

            # Dispatch event for enemy killed
            EventDispatcher.dispatch(EventType.ENEMY_KILLED, {"enemy_name": enemy.name})
            # Nullify enemy in room
            self.player.current_room.enemy = None

            show_terminal_cursor(True)
            console.input(
                "\n[bold yellow]Press Enter to return to exploration...[/bold yellow]"
            )
            show_terminal_cursor(False)

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
        show_terminal_cursor(True)
        console.input("\n[bold yellow]Press Enter to continue...[/bold yellow]")
        show_terminal_cursor(False)

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
            world_clock=self.world_clock,
            weather_engine=self.weather_engine,
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
            p, pt, w, q, rname, tav, was_recovered, clock_data, weather_data = (
                load_game(self.world, self.quests)
            )
            self.player = p
            self.party = pt
            self.world = w
            self.quests = q
            self.tavern_companions = tav

            if clock_data:
                self.world_clock.current_index = clock_data.get("current_index", 1)
                self.world_clock.movement_ticks = clock_data.get("movement_ticks", 0)
            if weather_data:
                state_key = weather_data.get("current_state_key", "clear")
                if state_key in self.weather_engine.STATES:
                    self.weather_engine.current_state = self.weather_engine.STATES[
                        state_key
                    ]
                self.weather_engine.turns_remaining = weather_data.get(
                    "turns_remaining", 15
                )

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
