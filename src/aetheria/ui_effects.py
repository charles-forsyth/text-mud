# src/aetheria/ui_effects.py
import sys
import time
from rich.panel import Panel


def trigger_screen_damage_flash() -> None:
    """
    Injects ANSI screen-flash command codes to turn the terminal background red.
    Fades back to black instantaneously to simulate taking physical combat damage.
    """
    # 1. Fill screen background red (\033[41m), clear (\033[2J)
    sys.stdout.write("\033[41m\033[2J")
    sys.stdout.flush()
    time.sleep(0.08)

    # 2. Reset standard colors (\033[0m), clear again
    sys.stdout.write("\033[0m\033[2J")
    sys.stdout.flush()


def render_dynamic_impact_panel(
    content: str, title: str, is_impacted: bool = False, is_town: bool = False
) -> Panel:
    """
    Renders standard content panels. Undergoes dynamic styling transitions
    if taking immediate heavy combat damage or critical hits.
    """
    if is_impacted:
        # High impact alert: heavy DOUBLE border, burning red style
        from rich.box import DOUBLE

        return Panel(
            content,
            title=f"[bold blink red]🔥 {title} 🔥[/bold blink red]",
            border_style="bold red",
            box=DOUBLE,
            padding=(1, 2),
        )
    else:
        # Standard exploration styling
        from rich.box import ROUNDED

        border_style = "dim green" if is_town else "dim slate_blue1"

        return Panel(
            content, title=title, border_style=border_style, box=ROUNDED, padding=(1, 2)
        )
