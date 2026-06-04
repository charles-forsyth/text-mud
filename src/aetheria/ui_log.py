# src/aetheria/ui_log.py
from typing import List
from rich.text import Text


class GameLogEvent:
    """Represents a structured, semantic action event in the world."""

    CATEGORY_THEMES = {
        "combat_damage": {"prefix": "⚔️  [bold red]DAMAGE[/bold red]", "style": "red"},
        "combat_heal": {"prefix": "💖 [bold green]HEAL[/bold green]", "style": "green"},
        "loot": {"prefix": "🎁 [bold gold1]LOOT[/bold gold1]", "style": "gold1"},
        "quest": {"prefix": "📜 [bold purple]QUEST[/bold purple]", "style": "purple"},
        "dialogue": {"prefix": "👤 [bold cyan]SPEECH[/bold cyan]", "style": "cyan"},
        "system": {
            "prefix": "⚙️  [bold grey50]SYSTEM[/bold grey50]",
            "style": "dim white",
        },
        "weather": {"prefix": "🌦️  [bold blue]CLIMATE[/bold blue]", "style": "blue"},
    }

    def __init__(self, category: str, message: str):
        self.category = category
        self.message = message

    def format_to_rich(self) -> Text:
        """Converts raw structured values to elegant styled console spans."""
        theme = self.CATEGORY_THEMES.get(
            self.category, {"prefix": "•", "style": "white"}
        )
        prefix = Text.from_markup(theme["prefix"])
        prefix.pad_right(16)

        formatted = Text()
        formatted.append(prefix)
        formatted.append(f" {self.message}", style=theme["style"])
        return formatted


class ScrollingActivityLog:
    """Buffers and formats semantic system-events inside a rolling panel."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.buffer: List[GameLogEvent] = []

    def append(self, category: str, message: str):
        """Pushes a new event, keeping bounds locked within limit."""
        if len(self.buffer) >= self.max_size:
            self.buffer.pop(0)
        self.buffer.append(GameLogEvent(category, message))

    def get_display_lines(self, limit: int = 10) -> List[Text]:
        """Returns formatted text spans tailored for the bottom panel grid."""
        recent = self.buffer[-limit:] if len(self.buffer) > limit else self.buffer
        return [evt.format_to_rich() for evt in recent]


def parse_string_to_log_event(line: str) -> GameLogEvent:
    """Parses a raw message string into a structured GameLogEvent."""
    import re

    lower_line = line.lower()
    # Clean standard markup tags to read raw words for categorization
    clean_text = re.sub(r"\[\/?[^\]]+\]", "", lower_line)

    if (
        "damage" in clean_text
        or "hit" in clean_text
        or "slay" in clean_text
        or "slain" in clean_text
        or "defeat" in clean_text
        or "attack" in clean_text
        or "strike" in clean_text
        or "⚔️" in clean_text
        or "deals" in clean_text
    ):
        return GameLogEvent("combat_damage", line)
    elif (
        "heal" in clean_text
        or "potion" in clean_text
        or "cure" in clean_text
        or "regenerate" in clean_text
        or "💖" in clean_text
        or "restores" in clean_text
    ):
        return GameLogEvent("combat_heal", line)
    elif (
        "loot" in clean_text
        or "found" in clean_text
        or "take" in clean_text
        or "gold" in clean_text
        or "obtained" in clean_text
        or "received" in clean_text
        or "backpack" in clean_text
        or "bag" in clean_text
        or "obtained" in clean_text
    ):
        return GameLogEvent("loot", line)
    elif (
        "quest" in clean_text
        or "objective" in clean_text
        or "completed" in clean_text
        or "progress" in clean_text
    ):
        return GameLogEvent("quest", line)
    elif (
        "say" in clean_text
        or "talk" in clean_text
        or "whisper" in clean_text
        or "speak" in clean_text
        or ":" in clean_text
    ):
        return GameLogEvent("dialogue", line)
    elif (
        "weather" in clean_text
        or "rain" in clean_text
        or "storm" in clean_text
        or "wind" in clean_text
        or "sky" in clean_text
    ):
        return GameLogEvent("weather", line)
    else:
        return GameLogEvent("system", line)
