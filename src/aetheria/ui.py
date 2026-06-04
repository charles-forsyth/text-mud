from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.box import ROUNDED, DOUBLE
from typing import Any, List, Optional
from aetheria.entity import Player, Companion, Enemy
from aetheria.world import Room
from aetheria.quests import Quest

# Import premium UI/UX modular system
from aetheria.ui_meters import render_stat_progress_bar
from aetheria.ui_layout import (
    generate_main_dashboard_layout,
    generate_combat_dashboard_layout,
)
from aetheria.ui_log import parse_string_to_log_event, ScrollingActivityLog
from aetheria.ui_effects import render_dynamic_impact_panel
from aetheria.ui_input import (
    interactive_prompt as interactive_prompt,
    get_input_suggestions_panel as get_input_suggestions_panel,
    get_combat_suggestions_panel as get_combat_suggestions_panel,
)

import sys

# Instantiate global rich console
console = Console()

# Global state to prevent duplicate/redundant prints in sequential logging
DASHBOARD_RENDERED = False


class TerminalScreen:
    """
    A context manager that transitions the terminal into a full-screen alternate buffer.
    Prevents scroll history pollution and provides flicker-free double-buffered redraws.
    """

    def __enter__(self):
        # Enter alternate buffer (\033[?1049h), clear screen (\033[H\033[?25l)
        sys.stdout.write("\033[?1049h\033[H\033[?25l")
        sys.stdout.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore normal buffer (\033[?1049l), show cursor (\033[?25h)
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()


def clear_and_home_screen():
    """Clears the screen in-place and homes the cursor position without scrolling."""
    sys.stdout.write("\033[H\033[2J")
    sys.stdout.flush()


def show_terminal_cursor(visible: bool):
    """Enables or disables the cursor visibility."""
    if visible:
        sys.stdout.write("\033[?25h")
    else:
        sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def render_title_screen():
    """Renders a beautiful premium RPG splash header."""
    title_text = r"""
    _    _   _   _  _             _         __  __ _   _ ____  
   / \  | |_| |_| || | ___  _ __ (_) __ _  |  \/  | | | |  _ \ 
  / _ \ | __|  _  || |/ _ \| '__|| |/ _` | | |\/| | | | | | | |
 / ___ \| |_| | | || |  __/| |   | | (_| | | |  | | |_| | |_| |
/_/   \_\\__|_| |_||_|\\___||_|   |_|\\__,_| |_|  |_|\\___/|____/ 
    """
    console.print(
        Panel(
            Text(title_text, style="bold gold1", justify="center"),
            box=DOUBLE,
            subtitle="[bold cyan]An AI-Driven Text RPG Adventure v0.2.0[/bold cyan]",
            subtitle_align="center",
            border_style="purple",
            padding=(1, 2),
        )
    )


def render_help_menu():
    """Displays all modern text game console actions."""
    table = Table(
        title="📜 Aetheria Command Codex",
        border_style="cyan",
        box=ROUNDED,
        show_header=True,
    )
    table.add_column("Command", style="bold yellow", justify="left")
    table.add_column("Shorthand", style="italic green", justify="center")
    table.add_column("Description", style="white", justify="left")

    table.add_row(
        "go [direction]", "n / s / e / w", "Move north, south, east, or west."
    )
    table.add_row("look", "l", "Inspect current room, items, exits, and characters.")
    table.add_row("take [item]", "t [item]", "Pick up an item on the ground.")
    table.add_row("use [item]", "u [item]", "Drink a potion or consume an elixir.")
    table.add_row("equip [item]", "eq [item]", "Equip weapons, shields, or armor.")
    table.add_row(
        "talk to [npc] about [topic]",
        "talk [npc] [topic]",
        "Speak dynamic topics to NPC (Gemini AI powered).",
    )
    table.add_row(
        "recruit [companion]",
        "rec [companion]",
        "Hire a recruitable helper at the Tavern.",
    )
    table.add_row("party", "p", "View active party members, classes, and stats.")
    table.add_row("quests", "q", "Check active side-quests and objective progress.")
    table.add_row("inventory", "i", "Examine collected items and current gold.")
    table.add_row(
        "map", "m", "Show the visual world maps with your highlighted location."
    )
    table.add_row(
        "voice",
        "v",
        "Toggle AI speech voice narrations (Google Cloud TTS Chirp 3 HD) ON/OFF.",
    )
    table.add_row("save", "-", "Manually save current progress securely.")
    table.add_row("load", "-", "Restore previously saved character files.")
    table.add_row("exit / quit", "-", "Shut down current game.")

    console.print(table)


def get_minimap_panel(room: Room) -> Panel:
    """Renders a beautiful and compact ASCII exit compass map of the current room."""
    north = room.get_exit("north")
    south = room.get_exit("south")
    east = room.get_exit("east")
    west = room.get_exit("west")

    n_style = "[bold green]N[/bold green]" if north else "[dim grey37]░[/dim grey37]"
    s_style = "[bold green]S[/bold green]" if south else "[dim grey37]░[/dim grey37]"
    e_style = "[bold green]E[/bold green]" if east else "[dim grey37]░[/dim grey37]"
    w_style = "[bold green]W[/bold green]" if west else "[dim grey37]░[/dim grey37]"

    n_conn = "│" if north else " "
    s_conn = "│" if south else " "
    w_conn = "───" if west else "   "
    e_conn = "───" if east else "   "

    compass_text = Text()
    compass_text.append(f"       {n_style}       \n")
    compass_text.append(f"       {n_conn}       \n")
    compass_text.append(f" {w_style} {w_conn}★{e_conn} {e_style} \n")
    compass_text.append(f"       {s_conn}       \n")
    compass_text.append(f"       {s_style}       ")

    return Panel(
        compass_text,
        title="[bold yellow]🧭 Local Exit Map[/bold yellow]",
        border_style="yellow",
        box=ROUNDED,
        padding=(0, 2),
    )


def get_region_map_panel(room: Room, world: Optional[dict] = None) -> Optional[Panel]:
    """Returns a beautiful Rich Panel containing the ASCII map for the current region."""
    name = room.name

    # Region definitions
    region1_rooms = [
        "Eldergrove Center",
        "Eldergrove Tavern (The Golden Oak)",
        "Eldergrove Blacksmith (Iron & Ash)",
        "Eldergrove Temple (Aether Sanctuary)",
    ]
    region2_rooms = [
        "Whisperwood Entrance",
        "Goblin Outpost",
        "Whispering Glade",
        "Ancient Oak Cave",
    ]
    region3_rooms = [
        "Silverlight Bridge",
        "Silverlight Keep Square",
        "Silverlight Royal Armory",
        "Shadowspire Gates",
        "Shadowspire Courtyard",
        "Alchemical Laboratory",
        "Shadow Throne Room",
    ]

    is_in_r1 = name in region1_rooms
    is_in_r2 = name in region2_rooms
    is_in_r3 = name in region3_rooms

    if not (is_in_r1 or is_in_r2 or is_in_r3):
        return None

    # Determine locks
    bridge_locked = True
    throne_locked = True
    if world:
        if "Silverlight Bridge" in world:
            bridge_locked = world["Silverlight Bridge"].locked
        if "Shadow Throne Room" in world:
            throne_locked = world["Shadow Throne Room"].locked
    else:
        # Traverse exits to locate bridge or throne if possible
        visited = set()
        queue = [room]
        found_bridge = False
        found_throne = False
        while queue:
            curr = queue.pop(0)
            if curr.name in visited:
                continue
            visited.add(curr.name)
            if curr.name == "Silverlight Bridge":
                bridge_locked = curr.locked
                found_bridge = True
            if curr.name == "Shadow Throne Room":
                throne_locked = curr.locked
                found_throne = True
            if found_bridge and found_throne:
                break
            for adj in curr.exits.values():
                if adj and adj.name not in visited:
                    queue.append(adj)

    # Render regional maps
    if is_in_r1:
        map_content = draw_eldergrove_map(name)
        title = "🗺️  [bold cyan]Region I: Eldergrove Village[/bold cyan]"
        border_color = "cyan"
        subtitle = "[bold gold1]★ YOU ARE HERE[/bold gold1]"
    elif is_in_r2:
        map_content = draw_whisperwood_map(name)
        title = "🗺️  [bold green]Region II: Whisperwood Forest[/bold green]"
        border_color = "green"
        subtitle = "[bold gold1]★ YOU ARE HERE[/bold gold1]"
    else:
        map_content = draw_silverlight_shadowspire_map(
            name, bridge_locked, throne_locked
        )
        title = "🗺️  [bold purple]Region III: Silverlight Keep & Castle Shadowspire[/bold purple]"
        border_color = "purple"
        subtitle = "[bold gold1]★ YOU ARE HERE[/bold gold1]"

    return Panel(
        map_content.strip("\n"),
        title=title,
        subtitle=subtitle,
        subtitle_align="right",
        border_style=border_color,
        box=ROUNDED,
    )


_PREV_STATS: dict[str, int] = {}
_PREV_COMBAT_STATS: dict[str, int] = {}


def get_combined_actions_and_help_panel(
    actions: List[tuple], valid_exits: List[str], current_input: str = ""
) -> Panel:
    """
    Renders a unified compact panel of numbered quick actions and context suggestions.
    If the user has started typing, dynamically renders matching command suggestions!
    Fits perfectly in exactly 5 lines of vertical inner space (inside a size=7 footer layout).
    """
    if current_input.strip():
        cleaned = current_input.strip().lower()
        suggestion_text = Text()
        if cleaned == "go" or cleaned.startswith("go "):
            directions = ", ".join(
                f"[bold green]{dir_}[/bold green]" for dir_ in valid_exits
            )
            suggestion_text.append("🚪 Travel Paths: ", style="white")
            suggestion_text.append(directions)
            suggestion_text.append(
                "\n💡 Shorthand: 'n', 's', 'e', 'w'", style="dim yellow"
            )
        elif cleaned.startswith("t") or cleaned.startswith("take"):
            suggestion_text.append("📦 Usage: take <item_name>", style="yellow")
            suggestion_text.append(
                "\n💡 Example: 'take health potion'", style="dim yellow"
            )
        elif cleaned.startswith("talk") or cleaned.startswith("tk"):
            suggestion_text.append(
                "👤 Usage: talk to <npc_name> about <topic>", style="cyan"
            )
            suggestion_text.append(
                "\n💡 Example: 'talk to Barnaby about quest'", style="dim cyan"
            )
        elif cleaned.startswith("u") or cleaned.startswith("use"):
            suggestion_text.append("🧪 Usage: use <item_name>", style="magenta")
            suggestion_text.append(
                "\n💡 Example: 'use health potion'", style="dim magenta"
            )
        else:
            suggestion_text.append(
                f"🔍 Custom Command: '{cleaned}'", style="dim italic green"
            )
            suggestion_text.append(
                "\n💡 Press Enter to submit command.", style="dim grey37"
            )

        # Pad with newlines to match 4 lines height precisely to prevent layout shifting
        lines = len(suggestion_text.plain.split("\n"))
        for _ in range(lines, 4):
            suggestion_text.append("\n")

        exits_shorthand = (
            "/".join(e[0].lower() for e in valid_exits) if valid_exits else "none"
        )
        help_text = f"💡 [bold yellow]Hotkeys:[/bold yellow] [{exits_shorthand}] Move | [look] Inspect | [i] Bag"

        table = Table.grid(expand=True)
        table.add_column(ratio=100)
        table.add_row(suggestion_text)
        table.add_row(Text.from_markup(help_text, style="dim white"))

        return Panel(
            table,
            title="⚡ [bold yellow]Command Synthesizer Help[/bold yellow]",
            border_style="yellow",
            box=ROUNDED,
            padding=(0, 1),
        )

    grid = Table.grid(expand=True)
    grid.add_column(style="bold yellow", justify="left", width=4)
    grid.add_column(style="white", justify="left")

    # Pick top actions to show (up to 4 actions)
    displayed_actions = actions[:4] if actions else []
    for idx, (display_text, command) in enumerate(displayed_actions, 1):
        grid.add_row(f" {idx} ", display_text)

    # Fill remaining rows up to 4 to keep size constant
    for idx in range(len(displayed_actions), 4):
        grid.add_row("", "")

    # Divider and Hotkey suggestion line
    exits_shorthand = (
        "/".join(e[0].lower() for e in valid_exits) if valid_exits else "none"
    )
    help_text = f"💡 [bold yellow]Hotkeys:[/bold yellow] [{exits_shorthand}] Move | [look] Inspect | [i] Bag"

    table = Table.grid(expand=True)
    table.add_column(ratio=100)
    table.add_row(grid)
    table.add_row(Text.from_markup(help_text, style="dim white"))

    return Panel(
        table,
        title="⚡ [bold yellow]Quick Actions Hub[/bold yellow]",
        border_style="yellow",
        box=ROUNDED,
        padding=(0, 1),
    )


def _print_layout_frame(
    room: Room,
    party: List[Companion],
    player: Player,
    dynamic_description: Optional[str] = None,
    world: Optional[dict] = None,
    weather_engine: Optional[Any] = None,
    world_clock: Optional[Any] = None,
    message_log: Optional[List[str]] = None,
    is_impacted: bool = False,
    quick_actions: Optional[List[tuple]] = None,
    current_input: str = "",
):
    header_style = "bold bright_green" if room.is_town else "bold deep_pink4"
    box_header = f"✨ {room.name}" if room.is_town else f"🌋 {room.name} (Hostile Area)"

    room_details = []
    desc = dynamic_description if dynamic_description else room.description
    room_details.append(f"[italic]{desc}[/italic]\n")

    # Display Weather and Clock
    weather_clock_details = []
    if world_clock:
        weather_clock_details.append(
            f"⏳ [bold gold1]Time of Day:[/bold gold1] [bold yellow]{world_clock.current_time}[/bold yellow]"
        )
    if weather_engine:
        c_state = weather_engine.current_state
        weather_clock_details.append(
            f"🌦️ [bold gold1]Weather:[/bold gold1] [{c_state.visual_style}]{c_state.name}[/{c_state.visual_style}]"
        )
    if weather_clock_details:
        room_details.append(" | ".join(weather_clock_details) + "\n")

    # Display items
    if room.items:
        items_str = ", ".join(
            f"[bold yellow]{item.name}[/bold yellow]" for item in room.items
        )
        room_details.append(
            f"📦 [bold gold1]Loot on the floor:[/bold gold1] {items_str}"
        )
    else:
        room_details.append("[dim]No items lying around here.[/dim]")

    # Display NPCs
    if room.npcs:
        npcs_str = ", ".join(f"[bold cyan]{npc.name}[/bold cyan]" for npc in room.npcs)
        room_details.append(f"👤 [bold cyan]Characters present:[/bold cyan] {npcs_str}")

    # Display Enemy
    if room.enemy:
        enemy_status = (
            f"([red]{room.enemy.hp}/{room.enemy.max_hp} HP[/red])"
            if room.enemy.is_alive
            else "([bold dim]Defeated[/bold dim])"
        )
        room_details.append(
            f"💀 [bold red]Hostile entity detected:[/bold red] [bold yellow]{room.enemy.name}[/bold yellow] Level {room.enemy.level} {enemy_status}"
        )

    # Display Exits
    exits_str = ", ".join(
        f"[bold green]{direction}[/bold green]" for direction in room.exits.keys()
    )
    room_details.append(
        f"🚪 [bold green]Exits:[/bold green] {exits_str if exits_str else '[dim]None[/dim]'}"
    )

    if message_log is not None:
        # PREMIUM UI/UX TUI DASHBOARD RENDER PATH
        # 1. Build room panel with potential impact layout effect
        room_panel = render_dynamic_impact_panel(
            "\n".join(room_details), box_header, is_impacted=is_impacted
        )

        # 2. Get local map (minimap) panel
        minimap_panel = get_minimap_panel(room)

        # 3. Construct the party panel dynamically with graphical progress bars
        party_panel_content = Table.grid(expand=True)
        party_panel_content.add_column(ratio=50)
        party_panel_content.add_column(width=2)
        party_panel_content.add_column(ratio=50)

        # Player column
        p_hp_bar = render_stat_progress_bar("HP", player.hp, player.max_hp, width=12)
        p_mp_bar = render_stat_progress_bar(
            "MP", player.mana, player.max_mana, width=12, color_scheme="mana"
        )
        p_xp_bar = render_stat_progress_bar(
            "XP",
            player.xp,
            player.xp_to_next_level(),
            width=12,
            color_scheme="xp",
        )

        player_info = Text.assemble(
            Text(f"🌟 {player.name} ", style="bold gold1"),
            Text(f"({player.char_class}) Lvl {player.level}\n", style="italic white"),
            p_hp_bar,
            Text("  "),
            p_mp_bar,
            Text("  "),
            p_xp_bar,
            Text("\n"),
            Text(
                f"💰 Gold: {player.gold}  ⚔️ ATK: {player.attack}  🛡️ DEF: {player.defense}",
                style="bold yellow",
            ),
        )

        left_side = Panel(
            player_info,
            border_style="gold1",
            box=ROUNDED,
            title="[bold gold1]Hero[/bold gold1]",
        )

        companion_texts = []
        for c in party:
            c_status = (
                " [bold green]ALIVE[/bold green]"
                if c.is_alive
                else " [bold dim red]DEAD[/bold dim red]"
            )
            c_hp_bar = render_stat_progress_bar("HP", c.hp, c.max_hp, width=10)
            c_mp_bar = render_stat_progress_bar(
                "MP", c.mana, c.max_mana, width=10, color_scheme="mana"
            )
            comp_info = Text.assemble(
                Text(f"👥 {c.name} ", style="bold cyan"),
                Text(f"({c.char_class}) Lvl {c.level}", style="white"),
                Text(c_status),
                Text("\n"),
                c_hp_bar,
                Text("  "),
                c_mp_bar,
            )
            companion_texts.append(comp_info)

        if companion_texts:
            all_comp_text = Text()
            for idx, ct in enumerate(companion_texts):
                if idx > 0:
                    all_comp_text.append("\n")
                all_comp_text.append(ct)
            right_side = Panel(
                all_comp_text,
                border_style="cyan",
                box=ROUNDED,
                title="[bold cyan]Companions[/bold cyan]",
            )
        else:
            right_side = Panel(
                Text(
                    "[italic dim]No companions in party.[/italic dim]\nRecruit allies at the Eldergrove Tavern!",
                    justify="center",
                ),
                border_style="dim",
                box=ROUNDED,
                title="[dim]Companions[/dim]",
            )

        party_panel_content.add_row(left_side, "", right_side)

        party_panel = Panel(
            party_panel_content,
            title="[bold yellow]👥 Adventure Party Status[/bold yellow]",
            border_style="yellow",
            box=ROUNDED,
            expand=True,
        )

        # 4. Construct the structured log panel
        activity_log = ScrollingActivityLog()
        for line in message_log:
            event = parse_string_to_log_event(line)
            activity_log.append(event.category, event.message)

        # Limit to 5 lines for combined layout height budget of size=7 footer
        log_limit = 5 if quick_actions is not None else 10
        log_lines = activity_log.get_display_lines(limit=log_limit)
        log_text = Text()
        for idx, line_text in enumerate(log_lines):
            if idx > 0:
                log_text.append("\n")
            log_text.append(line_text)

        log_panel = Panel(
            log_text,
            title="⚡ [bold gold1]Recent Activity Log[/bold gold1]",
            border_style="gold1",
            box=ROUNDED,
            expand=True,
            padding=(0, 1),
        )

        # 5. Build combined suggestions panel
        quick_actions_panel = None
        if quick_actions is not None:
            quick_actions_panel = get_combined_actions_and_help_panel(
                quick_actions, list(room.exits.keys()), current_input=current_input
            )

        # 6. Assemble and print full screen dashboard layout
        layout = generate_main_dashboard_layout(
            room_panel=room_panel,
            minimap_panel=minimap_panel,
            party_panel=party_panel,
            log_panel=log_panel,
            quick_actions_panel=quick_actions_panel,
            header_title=f"✨ {room.name} ✨"
            if room.is_town
            else f"🌋 {room.name} (Hostile Area) 🌋",
        )

        region_map_panel = get_region_map_panel(room, world)
        if region_map_panel:
            if quick_actions_panel is None:
                layout["body"]["map_views"].update(region_map_panel)
            else:
                layout["body"]["stats_and_maps"]["map_views"].update(region_map_panel)

        console.print(layout)

        # Trigger dashboard bypass for sequential activity renderer
        global DASHBOARD_RENDERED
        DASHBOARD_RENDERED = True

    else:
        # ORIGINAL SEQUENTIAL FALLBACK (For backward compatibility & standard unit tests)
        region_map_panel = get_region_map_panel(room, world)
        if region_map_panel:
            console.print(region_map_panel)
            console.print()

        # Create side-by-side Table layout
        layout_table = Table.grid(expand=True)
        layout_table.add_column(ratio=65)
        layout_table.add_column(width=2)
        layout_table.add_column(ratio=35)

        room_panel = Panel(
            "\n".join(room_details),
            title=f"[{header_style}]{box_header}[/{header_style}]",
            box=ROUNDED,
            border_style="green" if room.is_town else "red",
            padding=(1, 2),
            expand=True,
        )

        minimap_panel = get_minimap_panel(room)

        layout_table.add_row(room_panel, "", minimap_panel)

        # Render Main Room side-by-side Panel
        console.print(layout_table)

        # Render Side Mini-HUD
        from aetheria.ui import render_mini_party_hud

        render_mini_party_hud(player, party)


def render_room_panel(
    room: Room,
    party: List[Companion],
    player: Player,
    dynamic_description: Optional[str] = None,
    world: Optional[dict] = None,
    weather_engine: Optional[Any] = None,
    world_clock: Optional[Any] = None,
    message_log: Optional[List[str]] = None,
    is_impacted: bool = False,
    quick_actions: Optional[List[tuple]] = None,
    current_input: str = "",
):
    """Renders visual layout of the player's current location with automatic, non-blocking stats animations."""
    global _PREV_STATS

    current_stats = {
        "player_hp": player.hp,
        "player_mana": player.mana,
        "player_xp": player.xp,
    }
    for comp in party:
        current_stats[f"comp_{comp.name}_hp"] = comp.hp
        current_stats[f"comp_{comp.name}_mana"] = comp.mana

    # Detect any changes
    has_changes = False
    if _PREV_STATS:
        for k, v in current_stats.items():
            if _PREV_STATS.get(k, v) != v:
                has_changes = True
                break

    import os
    import sys

    # Only run interactive animation if we are in a real TTY and not running pytest unit tests
    is_interactive = (
        sys.stdin.isatty()
        and sys.stdout.isatty()
        and "PYTEST_CURRENT_TEST" not in os.environ
    )

    if has_changes and is_interactive and message_log is not None:
        # Interpolate frame states
        frames = 5
        import time

        for frame in range(1, frames):
            t = frame / frames

            # Interpolate Player stats
            orig_p_hp, orig_p_mana, orig_p_xp = (
                player.hp,
                player.mana,
                player.xp,
            )
            cached_p_hp = _PREV_STATS.get("player_hp", player.hp)
            cached_p_mp = _PREV_STATS.get("player_mana", player.mana)
            cached_p_xp = _PREV_STATS.get("player_xp", player.xp)

            player.hp = int(cached_p_hp + t * (player.hp - cached_p_hp))
            player.mana = int(cached_p_mp + t * (player.mana - cached_p_mp))
            player.xp = int(cached_p_xp + t * (player.xp - cached_p_xp))

            # Interpolate Companion stats
            orig_comp_stats = []
            for comp in party:
                orig_hp, orig_mana = comp.hp, comp.mana
                orig_comp_stats.append((comp, orig_hp, orig_mana))

                cached_hp = _PREV_STATS.get(f"comp_{comp.name}_hp", comp.hp)
                cached_mana = _PREV_STATS.get(f"comp_{comp.name}_mana", comp.mana)

                comp.hp = int(cached_hp + t * (comp.hp - cached_hp))
                comp.mana = int(cached_mana + t * (comp.mana - cached_mana))

            # Redraw full screen
            clear_and_home_screen()
            _print_layout_frame(
                room,
                party,
                player,
                dynamic_description,
                world,
                weather_engine,
                world_clock,
                message_log,
                is_impacted,
                quick_actions,
                current_input=current_input,
            )

            # Restore original state immediately
            player.hp, player.mana, player.xp = orig_p_hp, orig_p_mana, orig_p_xp
            for comp, orig_hp, orig_mana in orig_comp_stats:
                comp.hp, comp.mana = orig_hp, orig_mana

            time.sleep(0.04)

    # Print final frame and update cache
    _PREV_STATS = current_stats
    clear_and_home_screen()
    _print_layout_frame(
        room,
        party,
        player,
        dynamic_description,
        world,
        weather_engine,
        world_clock,
        message_log,
        is_impacted,
        quick_actions,
        current_input=current_input,
    )


def render_mini_party_hud(player: Player, party: List[Companion]):
    """Renders a horizontal mini-HUD bar displaying status of player + companions."""
    hud_cols = []

    # Player HUD column
    p_text = (
        f"[bold gold1]{player.name}[/bold gold1] ({player.char_class})\n"
        f"HP: [bold green]{player.hp}/{player.max_hp}[/bold green]\n"
        f"MP: [bold cyan]{player.mana}/{player.max_mana}[/bold cyan]\n"
        f"LVL: [bold]{player.level}[/bold] | G: [bold yellow]{player.gold}[/bold yellow]"
    )
    hud_cols.append(Panel(p_text, border_style="gold1", box=ROUNDED))

    # Party Companions columns
    for companion in party:
        c_status = (
            "[bold green]ALIVE[/bold green]"
            if companion.is_alive
            else "[bold dim red]DEAD[/bold dim red]"
        )
        c_text = (
            f"[bold cyan]{companion.name}[/bold cyan] ({companion.char_class})\n"
            f"HP: [bold green]{companion.hp}/{companion.max_hp}[/bold green]\n"
            f"MP: [bold cyan]{companion.mana}/{companion.max_mana}[/bold cyan]\n"
            f"LVL: {companion.level} | {c_status}"
        )
        hud_cols.append(
            Panel(
                c_text,
                border_style="cyan" if companion.is_alive else "red",
                box=ROUNDED,
            )
        )

    console.print(Columns(hud_cols))


def _print_combat_dashboard_frame(
    player: Player,
    party: List[Companion],
    enemy: Enemy,
    round_log: List[str],
    current_input: str = "",
    is_player_impacted: bool = False,
    is_enemy_impacted: bool = False,
):
    """Assembles and prints the combat dashboard layout frame."""
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.box import ROUNDED, DOUBLE
    from aetheria.ui_meters import render_stat_progress_bar

    # 1. Build Party Status Panel
    party_table = Table.grid(expand=True)
    party_table.add_column()

    # Player HP, MP, XP
    p_hp_bar = render_stat_progress_bar("HP", player.hp, player.max_hp, width=15)
    p_mp_bar = render_stat_progress_bar(
        "MP", player.mana, player.max_mana, width=15, color_scheme="mana"
    )
    p_xp_bar = render_stat_progress_bar(
        "XP", player.xp, player.xp_to_next_level(), width=15, color_scheme="xp"
    )

    party_table.add_row(
        Text.assemble(
            Text("🌟 ", style="bold gold1"),
            Text(f"{player.name} ", style="bold gold1"),
            Text(f"({player.char_class}) Lvl {player.level}", style="white"),
        )
    )
    party_table.add_row(p_hp_bar)
    party_table.add_row(p_mp_bar)
    party_table.add_row(p_xp_bar)
    party_table.add_row("")

    # Companions
    for comp in party:
        c_status = (
            " [bold green]ALIVE[/bold green]"
            if comp.is_alive
            else " [bold dim red]DEAD[/bold dim red]"
        )
        c_hp_bar = render_stat_progress_bar("HP", comp.hp, comp.max_hp, width=12)
        c_mp_bar = render_stat_progress_bar(
            "MP", comp.mana, comp.max_mana, width=12, color_scheme="mana"
        )
        party_table.add_row(
            Text.assemble(
                Text("👥 ", style="cyan"),
                Text(f"{comp.name} ", style="bold cyan"),
                Text(f"({comp.char_class})", style="white"),
                Text(c_status),
            )
        )
        party_table.add_row(c_hp_bar)
        party_table.add_row(c_mp_bar)
        party_table.add_row("")

    party_panel = Panel(
        party_table,
        title="[bold yellow]👥 Hero Party[/bold yellow]",
        border_style="bold red" if is_player_impacted else "yellow",
        box=DOUBLE if is_player_impacted else ROUNDED,
        expand=True,
    )

    # 2. Build Enemy Status Panel
    enemy_table = Table.grid(expand=True)
    enemy_table.add_column()

    e_hp_bar = render_stat_progress_bar("HP", enemy.hp, enemy.max_hp, width=15)
    enemy_table.add_row(
        Text.assemble(
            Text("💀 ", style="bold red"),
            Text(f"{enemy.name} ", style="bold red"),
            Text(f"Lvl {enemy.level}", style="white"),
        )
    )
    enemy_table.add_row(e_hp_bar)

    # Add active status ailments to enemy if any
    if hasattr(enemy, "ailments") and enemy.ailments.active_effects:
        ailment_names = ", ".join(
            f"[bold {effect.element_style}]{effect.name}[/bold {effect.element_style}]"
            for effect in enemy.ailments.active_effects
        )
        enemy_table.add_row(Text.from_markup(f"\n⚠️ Ailments: {ailment_names}"))

    enemy_table.add_row(
        Text(
            "\n⚡ Boss Enemy" if enemy.level >= 5 else "\nDungeon Monster",
            style="italic dim red",
        )
    )

    enemy_panel = Panel(
        enemy_table,
        title="[bold red]💀 Target Enemy[/bold red]",
        border_style="bold red" if is_enemy_impacted else "red",
        box=DOUBLE if is_enemy_impacted else ROUNDED,
        expand=True,
    )

    # 3. Build Combat Log Panel
    display_lines = [line.strip() for line in round_log if line.strip()]
    # Keep the last 5 lines for combined layout height budget
    recent_lines = display_lines[-5:] if len(display_lines) > 5 else display_lines
    if not recent_lines:
        recent_lines = ["[dim]Choose an action to initiate battle![/dim]"]

    log_panel = Panel(
        Text("\n").join([Text.from_markup(line) for line in recent_lines]),
        title="⚡ [bold yellow]Combat Rounds Log[/bold yellow]",
        border_style="yellow",
        box=ROUNDED,
        expand=True,
        padding=(0, 1),
    )

    # 4. Build Suggestions Panel
    combat_actions_panel = get_combat_suggestions_panel(current_input, player, enemy)

    # 5. Assemble into full combat dashboard layout
    layout = generate_combat_dashboard_layout(
        party_panel=party_panel,
        enemy_panel=enemy_panel,
        log_panel=log_panel,
        combat_actions_panel=combat_actions_panel,
        header_title=f"⚔️ {player.name} vs {enemy.name} ⚔️",
    )

    console.print(layout)


def render_combat_screen(
    player: Player,
    party: List[Companion],
    enemy: Enemy,
    round_log: List[str],
    current_input: str = "",
    is_player_impacted: bool = False,
    is_enemy_impacted: bool = False,
):
    """Displays structured, animated layout for ongoing battles."""
    global _PREV_COMBAT_STATS

    current_stats = {
        "player_hp": player.hp,
        "player_mana": player.mana,
        "enemy_hp": enemy.hp,
    }
    for comp in party:
        current_stats[f"comp_{comp.name}_hp"] = comp.hp
        current_stats[f"comp_{comp.name}_mana"] = comp.mana

    # Detect stats changes
    has_changes = False
    if _PREV_COMBAT_STATS:
        for k, v in current_stats.items():
            if _PREV_COMBAT_STATS.get(k, v) != v:
                has_changes = True
                break

    import os
    import sys

    is_interactive = (
        sys.stdin.isatty()
        and sys.stdout.isatty()
        and "PYTEST_CURRENT_TEST" not in os.environ
    )

    if has_changes and is_interactive:
        # Interpolate frame states over 5 frames
        frames = 5
        import time

        for frame in range(1, frames):
            t = frame / frames

            # Backup original stats
            orig_p_hp, orig_p_mana = player.hp, player.mana
            orig_e_hp = enemy.hp

            cached_p_hp = _PREV_COMBAT_STATS.get("player_hp", player.hp)
            cached_p_mp = _PREV_COMBAT_STATS.get("player_mana", player.mana)
            cached_e_hp = _PREV_COMBAT_STATS.get("enemy_hp", enemy.hp)

            player.hp = int(cached_p_hp + t * (player.hp - cached_p_hp))
            player.mana = int(cached_p_mp + t * (player.mana - cached_p_mp))
            enemy.hp = int(cached_e_hp + t * (enemy.hp - cached_e_hp))

            orig_comp_stats = []
            for comp in party:
                orig_hp, orig_mana = comp.hp, comp.mana
                orig_comp_stats.append((comp, orig_hp, orig_mana))

                cached_hp = _PREV_COMBAT_STATS.get(f"comp_{comp.name}_hp", comp.hp)
                cached_mana = _PREV_COMBAT_STATS.get(
                    f"comp_{comp.name}_mana", comp.mana
                )

                comp.hp = int(cached_hp + t * (comp.hp - cached_hp))
                comp.mana = int(cached_mana + t * (comp.mana - cached_mana))

            # Redraw frame
            clear_and_home_screen()
            _print_combat_dashboard_frame(
                player=player,
                party=party,
                enemy=enemy,
                round_log=round_log,
                current_input=current_input,
                is_player_impacted=is_player_impacted,
                is_enemy_impacted=is_enemy_impacted,
            )

            # Restore original stats
            player.hp, player.mana = orig_p_hp, orig_p_mana
            enemy.hp = orig_e_hp
            for comp, orig_hp, orig_mana in orig_comp_stats:
                comp.hp, comp.mana = orig_hp, orig_mana

            time.sleep(0.04)

    # Save final cache and draw final frame
    _PREV_COMBAT_STATS = current_stats
    clear_and_home_screen()
    _print_combat_dashboard_frame(
        player=player,
        party=party,
        enemy=enemy,
        round_log=round_log,
        current_input=current_input,
        is_player_impacted=is_player_impacted,
        is_enemy_impacted=is_enemy_impacted,
    )


def render_full_party_hud(player: Player, party: List[Companion]):
    """Renders comprehensive character inspection grids."""
    table = Table(
        title="👥 Adventure Party Codex",
        box=ROUNDED,
        border_style="gold1",
        show_header=True,
    )
    table.add_column("Character", style="bold yellow")
    table.add_column("Class / Personality", style="italic")
    table.add_column("Level", justify="center")
    table.add_column("HP", justify="center", style="bold green")
    table.add_column("Mana", justify="center", style="bold cyan")
    table.add_column("Attack", justify="center")
    table.add_column("Defense", justify="center")

    # Add Player
    table.add_row(
        f"{player.name} (Hero)",
        player.char_class,
        str(player.level),
        f"{player.hp}/{player.max_hp}",
        f"{player.mana}/{player.max_mana}",
        str(player.attack),
        str(player.defense),
    )

    # Add Companions
    for c in party:
        c_p = f"{c.char_class} - {c.personality}"
        table.add_row(
            c.name,
            c_p,
            str(c.level),
            f"{c.hp}/{c.max_hp}",
            f"{c.mana}/{c.max_mana}",
            str(c.attack),
            str(c.defense),
        )

    console.print(table)


def render_inventory_list(player: Player):
    """Displays equipped armor, active weaponry, and unequipped backpack inventory."""
    # Render Equipment Slots Table
    eq_table = Table(
        title="🛡️ Equipped Armaments", box=ROUNDED, border_style="cyan", show_header=True
    )
    eq_table.add_column("Slot", style="bold yellow")
    eq_table.add_column("Item Name", style="bold cyan")
    eq_table.add_column("Bonuses / Attributes", style="white")

    for slot, item in player.equipment.items():
        slot_name = slot.value.replace("_", " ").title()
        if item:
            bonuses = []
            if item.attack_bonus:
                bonuses.append(f"+{item.attack_bonus} ATK")
            if item.defense_bonus:
                bonuses.append(f"+{item.defense_bonus} DEF")
            if item.max_hp_bonus:
                bonuses.append(f"+{item.max_hp_bonus} HP")
            if item.max_mana_bonus:
                bonuses.append(f"+{item.max_mana_bonus} MP")
            bonus_str = f" ({', '.join(bonuses)})" if bonuses else ""
            eq_table.add_row(slot_name, item.name, f"{item.description}{bonus_str}")
        else:
            eq_table.add_row(
                slot_name,
                "[dim italic]Empty[/dim italic]",
                "[dim]No passive stat bonuses[/dim]",
            )

    console.print(eq_table)

    # Render Bag Packs Table
    bag_table = Table(
        title="🎒 Adventure Backpack Bag",
        box=ROUNDED,
        border_style="gold1",
        show_header=True,
    )
    bag_table.add_column("Item Name", style="bold yellow")
    bag_table.add_column("Description", style="white")
    bag_table.add_column("Value", style="bold yellow", justify="center")

    for inv_item in player.inventory:
        bag_table.add_row(inv_item.name, inv_item.description, f"{inv_item.value} Gold")

    if not player.inventory:
        bag_table.add_row(
            "[dim italic]Empty Backpack[/dim italic]",
            "[dim]Pick up items using 'take [item]'[/dim]",
            "0",
        )

    console.print(bag_table)
    console.print(
        f"💰 [bold yellow]Purse balance:[/bold yellow] [bold yellow]{player.gold}[/bold yellow] Gold coin tokens | ✨ [bold cyan]XP Progression:[/bold cyan] [bold]{player.xp}/{player.xp_to_next_level()}[/bold] XP"
    )


def render_quests_log(quests: List[Quest]):
    """Renders active quest progress panels."""
    table = Table(
        title="📜 Quest Tracker Scroll",
        box=ROUNDED,
        border_style="purple",
        show_header=True,
    )
    table.add_column("Quest Title", style="bold cyan")
    table.add_column("Lore Task Description", style="white")
    table.add_column("Objective", style="bold yellow")
    table.add_column("Rewards", style="bold yellow")
    table.add_column("Status", justify="center")

    for q in quests:
        if q.status == "inactive":
            continue

        status_color = "green" if q.status == "completed" else "yellow"
        reward_str = f"{q.gold_reward} Gold, {q.xp_reward} XP"
        if q.item_reward:
            reward_str += f", {q.item_reward.name}"

        obj_str = ""
        if q.objective_type == "kill":
            obj_str = f"Slay {q.objective_target} ({q.count_current}/{q.count_needed})"
        elif q.objective_type == "fetch":
            obj_str = (
                f"Collect {q.objective_target} ({q.count_current}/{q.count_needed})"
            )
        elif q.objective_type == "talk":
            obj_str = f"Speak to {q.objective_target}"

        table.add_row(
            q.name,
            q.description,
            obj_str,
            reward_str,
            f"[bold {status_color}]{q.status.upper()}[/bold {status_color}]",
        )

    if not any(q.status != "inactive" for q in quests):
        table.add_row(
            "[dim italic]No Active Quests[/dim italic]",
            "[dim]Visit Barnaby or Althea at towns to find work.[/dim]",
            "-",
            "-",
            "-",
        )

    console.print(table)


def render_action_log(message_log: List[str]):
    """Renders a beautiful scrolling Action Log panel containing recent game history events."""
    global DASHBOARD_RENDERED
    if DASHBOARD_RENDERED:
        DASHBOARD_RENDERED = False
        return

    # Filter out empty lines
    clean_lines = [line.strip() for line in message_log if line.strip()]
    # Keep the last 10 lines to fit terminal nicely without overflowing
    display_lines = clean_lines[-10:] if len(clean_lines) > 10 else clean_lines

    # If the log is empty, display a placeholder to keep UI structured
    if not display_lines:
        display_lines = [
            "[dim]The winds of Aetheria whisper. No recent actions...[/dim]"
        ]

    log_content = "\n".join(display_lines)

    console.print(
        Panel(
            log_content,
            title="⚡ [bold gold1]Recent Activity Log[/bold gold1]",
            border_style="gold1",
            box=ROUNDED,
            expand=True,
            padding=(0, 1),
        )
    )


def render_quick_actions(actions: List[tuple]):
    """Renders a beautiful grid or table of numbered quick actions in columns."""
    table = Table(
        box=ROUNDED,
        border_style="yellow",
        show_header=False,
        expand=True,
    )

    # We can split actions into 2 columns to save vertical space
    num_cols = 2
    for _ in range(num_cols):
        table.add_column("Number", style="bold yellow", justify="right", width=4)
        table.add_column("Action", style="white", justify="left")

    # Chunk actions into rows
    rows = []
    current_row = []
    for idx, (display_text, _) in enumerate(actions, 1):
        current_row.extend([f"[bold yellow]{idx}[/bold yellow]", display_text])
        if len(current_row) == num_cols * 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        # Pad with empty cells
        while len(current_row) < num_cols * 2:
            current_row.extend(["", ""])
        rows.append(current_row)

    for row in rows:
        table.add_row(*row)

    console.print(
        Panel(
            table,
            title="⚡ [bold yellow]Quick Actions[/bold yellow] (Type number or type command)",
            border_style="yellow",
            box=ROUNDED,
        )
    )


def draw_eldergrove_map(current: str) -> str:
    # Nodes
    t_style = (
        "bold yellow"
        if current == "Eldergrove Tavern (The Golden Oak)"
        else "bold green"
    )
    t_marker = "★ " if current == "Eldergrove Tavern (The Golden Oak)" else "  "

    c_style = "bold yellow" if current == "Eldergrove Center" else "bold green"
    c_marker = "★ " if current == "Eldergrove Center" else "  "

    tp_style = (
        "bold yellow"
        if current == "Eldergrove Temple (Aether Sanctuary)"
        else "bold green"
    )
    tp_marker = "★ " if current == "Eldergrove Temple (Aether Sanctuary)" else "  "

    b_style = (
        "bold yellow"
        if current == "Eldergrove Blacksmith (Iron & Ash)"
        else "bold green"
    )
    b_marker = "★ " if current == "Eldergrove Blacksmith (Iron & Ash)" else "  "

    map_str = f"""
                 [{t_style}]{t_marker}Tavern (Golden Oak)[/{t_style}]
                                │
                                │
 [{tp_style}]{tp_marker}Temple (Sanctuary)[/{tp_style}] ── [{c_style}]{c_marker}Center (Square)[/{c_style}] ── [{b_style}]{b_marker}Blacksmith[/{b_style}]
                                │                             │
                                ▼                             ▼
                      (To Whisperwood)              (To Silverlight)
"""
    return map_str


def draw_whisperwood_map(current: str) -> str:
    ent_style = "bold yellow" if current == "Whisperwood Entrance" else "bold red"
    ent_marker = "★ " if current == "Whisperwood Entrance" else "  "

    gob_style = "bold yellow" if current == "Goblin Outpost" else "bold red"
    gob_marker = "★ " if current == "Goblin Outpost" else "  "

    gld_style = "bold yellow" if current == "Whispering Glade" else "bold red"
    gld_marker = "★ " if current == "Whispering Glade" else "  "

    cav_style = "bold yellow" if current == "Ancient Oak Cave" else "bold red"
    cav_marker = "★ " if current == "Ancient Oak Cave" else "  "

    map_str = f"""
                      (From Eldergrove)
                              │
                              ▼
                  [{ent_style}]{ent_marker}Whisperwood Entrance[/{ent_style}]
                              │
                              ▼
                  [{gob_style}]{gob_marker}Goblin Outpost[/{gob_style}] ── [{gld_style}]{gld_marker}Whispering Glade[/{gld_style}]
                              │                       (Glowing Herbs)
                              ▼
                  [{cav_style}]{cav_marker}Ancient Oak Cave[/{cav_style}]
                     (BOSS: Forest Ancient)
"""
    return map_str


def draw_silverlight_shadowspire_map(
    current: str, bridge_locked: bool, throne_locked: bool
) -> str:
    brg_lock_str = " [🔒]" if bridge_locked else ""
    thr_lock_str = " [🔒]" if throne_locked else ""

    brg_style = (
        "bold yellow"
        if current == "Silverlight Bridge"
        else ("bold red" if bridge_locked else "bold green")
    )
    brg_marker = "★ " if current == "Silverlight Bridge" else "  "

    sq_style = "bold yellow" if current == "Silverlight Keep Square" else "bold green"
    sq_marker = "★ " if current == "Silverlight Keep Square" else "  "

    arm_style = "bold yellow" if current == "Silverlight Royal Armory" else "bold green"
    arm_marker = "★ " if current == "Silverlight Royal Armory" else "  "

    gat_style = "bold yellow" if current == "Shadowspire Gates" else "bold red"
    gat_marker = "★ " if current == "Shadowspire Gates" else "  "

    crt_style = "bold yellow" if current == "Shadowspire Courtyard" else "bold red"
    crt_marker = "★ " if current == "Shadowspire Courtyard" else "  "

    lab_style = "bold yellow" if current == "Alchemical Laboratory" else "bold red"
    lab_marker = "★ " if current == "Alchemical Laboratory" else "  "

    thr_style = "bold yellow" if current == "Shadow Throne Room" else "bold red"
    thr_marker = "★ " if current == "Shadow Throne Room" else "  "

    map_str = f"""
                 (From Eldergrove)
                        │
                        ▼
             [{brg_style}]{brg_marker}Silverlight Bridge{brg_lock_str}[/{brg_style}]
                        │
                        ▼
             [{sq_style}]{sq_marker}Keep Square[/{sq_style}] ── [{arm_style}]{arm_marker}Royal Armory[/{arm_style}]
                        │
                        ▼
             [{gat_style}]{gat_marker}Shadowspire Gates[/{gat_style}]
                        │
                        ▼
             [{crt_style}]{crt_marker}Shadowspire Courtyard[/{crt_style}]
                        │
               ┌────────┴────────┐
               ▼                 ▼
     [{lab_style}]{lab_marker}Alchem. Lab[/{lab_style}]     [{thr_style}]{thr_marker}Throne Room{thr_lock_str}[/{thr_style}]
      (Void Horror)        (BOSS: Malakor)
"""
    return map_str


def render_world_map(player_room_name: str, world_rooms: dict):
    """Renders a beautiful premium map of all three regions of Aetheria."""
    region1_rooms = [
        "Eldergrove Center",
        "Eldergrove Tavern (The Golden Oak)",
        "Eldergrove Blacksmith (Iron & Ash)",
        "Eldergrove Temple (Aether Sanctuary)",
    ]
    region2_rooms = [
        "Whisperwood Entrance",
        "Goblin Outpost",
        "Whispering Glade",
        "Ancient Oak Cave",
    ]
    region3_rooms = [
        "Silverlight Bridge",
        "Silverlight Keep Square",
        "Silverlight Royal Armory",
        "Shadowspire Gates",
        "Shadowspire Courtyard",
        "Alchemical Laboratory",
        "Shadow Throne Room",
    ]

    is_in_r1 = player_room_name in region1_rooms
    is_in_r2 = player_room_name in region2_rooms
    is_in_r3 = player_room_name in region3_rooms

    bridge_locked = world_rooms["Silverlight Bridge"].locked
    throne_locked = world_rooms["Shadow Throne Room"].locked

    r1_border = "gold1" if is_in_r1 else "blue"
    r1_sub = (
        "[bold blink gold1]⭐ YOU ARE HERE[/bold blink gold1]"
        if is_in_r1
        else "[dim]Safe Haven[/dim]"
    )

    r2_border = "gold1" if is_in_r2 else "blue"
    r2_sub = (
        "[bold blink gold1]⭐ YOU ARE HERE[/bold blink gold1]"
        if is_in_r2
        else "[dim]Hostile Wilderness[/dim]"
    )

    r3_border = "gold1" if is_in_r3 else "blue"
    r3_sub = (
        "[bold blink gold1]⭐ YOU ARE HERE[/bold blink gold1]"
        if is_in_r3
        else "[dim]Imperial Citadel & Deep Void[/dim]"
    )

    # Draw ASCII maps
    r1_map = draw_eldergrove_map(player_room_name)
    r2_map = draw_whisperwood_map(player_room_name)
    r3_map = draw_silverlight_shadowspire_map(
        player_room_name, bridge_locked, throne_locked
    )

    # Print a beautiful header
    console.print()
    console.print(
        Panel(
            Text("🗺️  WORLD MAP OF AETHERIA  🗺️", style="bold gold1", justify="center"),
            border_style="gold1",
            box=DOUBLE,
        )
    )
    console.print()

    # Print Region 1 Panel
    console.print(
        Panel(
            r1_map.strip("\n"),
            title="[bold cyan]Region I: Eldergrove Village[/bold cyan]",
            subtitle=r1_sub,
            subtitle_align="right",
            border_style=r1_border,
            box=ROUNDED,
        )
    )
    console.print()

    # Print Region 2 Panel
    console.print(
        Panel(
            r2_map.strip("\n"),
            title="[bold green]Region II: Whisperwood Forest[/bold green]",
            subtitle=r2_sub,
            subtitle_align="right",
            border_style=r2_border,
            box=ROUNDED,
        )
    )
    console.print()

    # Print Region 3 Panel
    console.print(
        Panel(
            r3_map.strip("\n"),
            title="[bold purple]Region III: Silverlight Keep & Castle Shadowspire[/bold purple]",
            subtitle=r3_sub,
            subtitle_align="right",
            border_style=r3_border,
            box=ROUNDED,
        )
    )
    console.print()

    # Print Legend Panel
    legend_text = (
        "  [bold yellow]★[/bold yellow] : Your Current Location     "
        "  [bold green]Room Name[/bold green] : Town / Safe Area     "
        "  [bold red]Room Name[/bold red] : Danger / Dungeon Area\n"
        "  [🔒 LOCKED] : Requires Special Sigil / Key to access"
    )
    console.print(
        Panel(legend_text, title="ℹ️  Map Legend", border_style="cyan", box=ROUNDED)
    )
    console.print()
