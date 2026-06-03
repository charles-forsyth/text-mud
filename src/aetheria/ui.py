from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.box import ROUNDED, DOUBLE
from typing import List
from aetheria.entity import Player, Companion, Enemy
from aetheria.world import Room
from aetheria.quests import Quest

# Instantiate global rich console
console = Console()


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
    table.add_row("save", "-", "Manually save current progress securely.")
    table.add_row("load", "-", "Restore previously saved character files.")
    table.add_row("exit / quit", "-", "Shut down current game.")

    console.print(table)


def render_room_panel(room: Room, party: List[Companion], player: Player):
    """Renders a beautiful visual layout of the player's current location."""
    header_style = "bold bright_green" if room.is_town else "bold deep_pink4"
    box_header = f"✨ {room.name}" if room.is_town else f"🌋 {room.name} (Hostile Area)"

    room_details = []
    room_details.append(f"[italic]{room.description}[/italic]\n")

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

    # Render Main Room Panel
    console.print(
        Panel(
            "\n".join(room_details),
            title=f"[{header_style}]{box_header}[/{header_style}]",
            box=ROUNDED,
            border_style="green" if room.is_town else "red",
            padding=(1, 2),
        )
    )

    # Render Side Mini-HUD
    render_mini_party_hud(player, party)


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


def render_combat_screen(
    player: Player, party: List[Companion], enemy: Enemy, round_log: List[str]
):
    """Displays structured layout for ongoing battles."""
    console.print("\n" + "=" * 80)
    console.print("[bold red]⚔️  BATTLE IN PROGRESS  ⚔️[/bold red]", justify="center")
    console.print("=" * 80)

    # Combat Table comparing health
    table = Table(box=ROUNDED, border_style="red", expand=True)
    table.add_column("Hero Party", style="bold green", justify="left")
    table.add_column("VS", style="bold yellow", justify="center")
    table.add_column("Dungeon Enemy", style="bold red", justify="right")

    # Build Hero block
    hero_lines = [
        f"[bold gold1]{player.name}[/bold gold1] [dim]({player.char_class})[/dim] - HP: [bold green]{player.hp}/{player.max_hp}[/bold green] | MP: [bold cyan]{player.mana}/{player.max_mana}[/bold cyan]"
    ]
    for comp in party:
        c_status = (
            "Dead"
            if not comp.is_alive
            else f"HP: {comp.hp}/{comp.max_hp} | MP: {comp.mana}/{comp.max_mana}"
        )
        hero_lines.append(
            f"[bold cyan]{comp.name}[/bold cyan] [dim]({comp.char_class})[/dim] - {c_status}"
        )

    hero_block = "\n".join(hero_lines)
    enemy_block = (
        f"[bold red]{enemy.name}[/bold red]\n"
        f"Level: {enemy.level}\n"
        f"HP: [bold red]{enemy.hp}/{enemy.max_hp}[/bold red]"
    )

    table.add_row(hero_block, "⚔️", enemy_block)
    console.print(table)

    # Round action logs
    if round_log:
        console.print(
            Panel(
                "\n".join(round_log),
                title="⚡ Combat Rounds Log",
                border_style="yellow",
                box=ROUNDED,
            )
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
