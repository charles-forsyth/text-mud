# src/aetheria/ui_meters.py
from rich.text import Text


def render_stat_progress_bar(
    label: str,
    current: int,
    max_val: int,
    width: int = 15,
    bar_char: str = "█",
    empty_char: str = "░",
    color_scheme: str = "default",
    suffix: str = "",
) -> Text:
    """
    Constructs a stylized horizontal graphical progress meter.
    Color transitions smoothly based on ratio status threshold tiers.
    """
    # Safety bounds
    current = max(0, min(current, max_val))
    if max_val <= 0:
        ratio = 0.0
    else:
        ratio = current / max_val

    # Determine bar segment lengths
    filled_length = int(round(ratio * width))
    empty_length = width - filled_length

    # Determine visual colors
    if color_scheme == "mana":
        color = "cyan"
    elif color_scheme == "xp":
        color = "purple"
    else:
        # Dynamic health indicators
        if ratio > 0.50:
            color = "green"
        elif ratio > 0.25:
            color = "yellow"
        else:
            color = "bold red"

    # Assemble text buffer
    bar_part = bar_char * filled_length
    empty_part = empty_char * empty_length

    meter_text = Text()
    meter_text.append(f"{label:<4} [", style="dim white")
    meter_text.append(bar_part, style=color)
    meter_text.append(empty_part, style="dim grey37")
    meter_text.append("] ", style="dim white")
    meter_text.append(f"{current}/{max_val}", style=f"bold {color}")
    if suffix:
        meter_text.append(suffix)

    return meter_text
