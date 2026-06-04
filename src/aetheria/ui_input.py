# src/aetheria/ui_input.py
import sys
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from typing import List, Optional, Callable, Any

try:
    import tty
    import termios

    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False


def get_input_suggestions_panel(current_input: str, valid_exits: List[str]) -> Panel:
    """
    Generates an autocomplete and syntax helper panel matching input prefixes.
    Guides keyboard interactions on active directions and action targets.
    """
    cleaned = current_input.strip().lower()
    suggestion_text = Text()

    if not cleaned:
        suggestion_text.append(
            "💡 Hotkeys: [1-9] Quick Action | [n/s/e/w] Move | [look] Inspect | [i] Bag",
            style="dim white",
        )
    elif cleaned == "go" or cleaned.startswith("go "):
        directions = ", ".join(
            f"[bold green]{dir_}[/bold green]" for dir_ in valid_exits
        )
        suggestion_text.append("🚪 Travel Paths: ", style="white")
        suggestion_text.append(directions)
        suggestion_text.append(
            "\n💡 Examples: 'go north', 'go south' or simply type shorthand 'n' / 's'",
            style="dim yellow",
        )
    elif cleaned.startswith("t") or cleaned.startswith("take"):
        suggestion_text.append(
            "📦 Usage: take <item_name> | Examples: 'take health potion', 'take bronze sword'",
            style="yellow",
        )
    elif cleaned.startswith("talk") or cleaned.startswith("tk"):
        suggestion_text.append(
            "👤 Usage: talk to <npc_name> about <topic> | Topic Ideas: 'quest', 'rumor', 'help'",
            style="cyan",
        )
    elif cleaned.startswith("u") or cleaned.startswith("use"):
        suggestion_text.append(
            "🧪 Usage: use <consumable_name> | Examples: 'use health potion', 'use mana elixir'",
            style="magenta",
        )
    else:
        # Default fallback match
        suggestion_text.append(
            f"🔍 Custom Command: '{cleaned}' (Hit enter to submit action)",
            style="dim italic green",
        )

    return Panel(
        suggestion_text,
        title="[bold yellow]💡 Command Synthesizer Help[/bold yellow]",
        border_style="yellow",
        box=ROUNDED,
        padding=(0, 1),
    )


def read_single_character() -> Optional[str]:
    """Reads a single keystroke from stdin in raw non-blocking mode."""
    if not HAS_TERMIOS or not sys.stdin.isatty():
        # Fallback if stdin is not a TTY (e.g. in tests)
        return sys.stdin.read(1)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def interactive_prompt(
    valid_exits: List[str],
    prompt_text: str = "> ",
    on_change: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Interactive, character-by-character non-blocking text reader.
    Updates the autocomplete HUD dynamically above the input row.
    """

    if not HAS_TERMIOS or not sys.stdin.isatty():
        # Fallback to standard input if not a real interactive TTY
        if on_change:
            on_change("")
        else:
            sys.stdout.write(prompt_text)
            sys.stdout.flush()
        return sys.stdin.readline().strip()

    current_buffer: List[str] = []

    if on_change:
        on_change("")
    else:
        sys.stdout.write(prompt_text)
        sys.stdout.flush()

    while True:
        char = read_single_character()
        if not char:
            continue

        # Carriage Return or Newline (handles enter key)
        if char in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            break
        # Backspace / Delete
        elif char in ("\x7f", "\x08"):
            if current_buffer:
                current_buffer.pop()
                if on_change:
                    on_change("".join(current_buffer))
                else:
                    # Erase last character visually
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
        # Escape sequences (Arrow keys, functional inputs etc.)
        elif char == "\x1b":
            # Consume escape sequence characters
            read_single_character()
            read_single_character()
            continue
        # Standard printable characters
        elif ord(char) >= 32:
            current_buffer.append(char)
            if on_change:
                on_change("".join(current_buffer))
            else:
                sys.stdout.write(char)
                sys.stdout.flush()

    return "".join(current_buffer)


def get_combat_suggestions_panel(current_input: str, player: Any, enemy: Any) -> Panel:
    """
    Generates an autocomplete and combat command helper panel matching current input.
    Guides the player on spell casting and item usage live!
    """

    cleaned = current_input.strip().lower()
    suggestion_text = Text()

    if not cleaned:
        suggestion_text.append(
            "⚔️ Actions: 1. [bold green]Attack[/bold green] | 2. [bold cyan]Spell[/bold cyan] | 3. [bold yellow]Item[/bold yellow] | 4. [bold magenta]Defend[/bold yellow] | 5. [bold red]Flee[/bold red]",
            style="white",
        )
        suggestion_text.append(
            "\n💡 Shorthand: '1' or 'atk', '2' or 'spell', '3' or 'item', '4' or 'def', '5' or 'flee'",
            style="dim yellow",
        )
    elif (
        cleaned == "2"
        or cleaned == "spell"
        or cleaned.startswith("spell ")
        or cleaned.startswith("cast ")
        or cleaned.startswith("cast")
    ):
        # List player spells
        spells_str = ", ".join(
            f"[bold cyan]{s.name}[/bold cyan] ({s.mana_cost} MP)" for s in player.spells
        )
        suggestion_text.append("🪄 Available Spells:\n", style="white")
        suggestion_text.append(
            spells_str if spells_str else "[dim red]No spells available[/dim red]"
        )
        suggestion_text.append(
            "\n💡 Usage: 'spell <name>' or cast by choosing option 2 and typing the name/number.",
            style="dim yellow",
        )
    elif (
        cleaned == "3"
        or cleaned == "item"
        or cleaned.startswith("item ")
        or cleaned.startswith("use ")
        or cleaned.startswith("use")
    ):
        # List player consumables
        from aetheria.models import Consumable

        consumables = [
            item for item in player.inventory if isinstance(item, Consumable)
        ]
        items_str = ", ".join(
            f"[bold yellow]{c.name}[/bold yellow]" for c in consumables
        )
        suggestion_text.append("🧪 Backpack Consumables:\n", style="white")
        suggestion_text.append(
            items_str
            if items_str
            else "[dim red]No healing consumables available[/dim red]"
        )
        suggestion_text.append(
            "\n💡 Usage: 'item <name>' or 'use <name>' to consume a potion.",
            style="dim yellow",
        )
    elif cleaned == "1" or cleaned == "attack" or cleaned == "atk":
        suggestion_text.append(
            f"⚔️ Strike: basic weapon swing at [bold red]{enemy.name}[/bold red]!",
            style="green",
        )
    elif cleaned == "4" or cleaned == "defend" or cleaned == "def":
        suggestion_text.append(
            "🛡️ Guard: Prepare to block attacks, reducing damage taken by 50%!",
            style="magenta",
        )
    elif cleaned == "5" or cleaned == "flee":
        suggestion_text.append(
            "🏃 Escape: Attempt to flee the battlefield! Success rate is 60%.",
            style="red",
        )
    else:
        suggestion_text.append(
            f"🔍 Custom Command: '{cleaned}' (Hit enter to submit combat choice)",
            style="dim italic green",
        )

    return Panel(
        suggestion_text,
        title="[bold red]💡 Combat Strategy Guide[/bold red]",
        border_style="red",
        box=ROUNDED,
        padding=(0, 1),
    )
