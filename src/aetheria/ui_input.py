# src/aetheria/ui_input.py
import sys
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from typing import List, Optional

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


def interactive_prompt(valid_exits: List[str], prompt_text: str = "> ") -> str:
    """
    Interactive, character-by-character non-blocking text reader.
    Updates the autocomplete HUD dynamically above the input row.
    """
    if not HAS_TERMIOS or not sys.stdin.isatty():
        # Fallback to standard input if not a real interactive TTY
        sys.stdout.write(prompt_text)
        sys.stdout.flush()
        return sys.stdin.readline().strip()

    current_buffer: List[str] = []
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
            sys.stdout.write(char)
            sys.stdout.flush()

    return "".join(current_buffer)
