import random
from typing import Dict, Optional, Any


class WeatherState:
    """Represents a global weather condition modifying exploration and combat stats."""

    def __init__(
        self,
        name: str,
        description: str,
        combat_modifiers: Dict[
            str, float
        ],  # e.g., {"fire_damage": 0.70, "lightning_damage": 1.25}
        evasion_modifier: float = 0.0,
        visual_style: str = "white",
    ):
        self.name = name
        self.description = description
        self.combat_modifiers = combat_modifiers
        self.evasion_modifier = evasion_modifier
        self.visual_style = visual_style


class WeatherEngine:
    """Simulates dynamic weather patterns and scales situational combat and environmental calculations."""

    STATES = {
        "clear": WeatherState(
            "Clear Skies",
            "The air is calm, and atmospheric conditions are crystal clear.",
            {},
            visual_style="bold gold1",
        ),
        "rain": WeatherState(
            "Torrential Rain",
            "Heavy rain pours from the heavens, drenching combatants and pooling on the ground.",
            {"fire_damage": 0.70, "lightning_damage": 1.30},
            visual_style="bold sky_blue1",
        ),
        "fog": WeatherState(
            "Dense Fog",
            "Thick fog rolls across the land, limiting visual range and creating shadows.",
            {},
            evasion_modifier=0.15,
            visual_style="bold grey50",
        ),
        "storm": WeatherState(
            "Aether Storm",
            "Violent magical rifts sweep the skies, surging mana lines and disrupting physical attacks.",
            {"spell_damage": 1.25, "mana_regen": 1.50, "physical_damage": 0.85},
            visual_style="bold purple",
        ),
    }

    def __init__(self):
        self.current_state = self.STATES["clear"]
        self.turns_remaining = random.randint(10, 20)

    def tick(self) -> Optional[str]:
        """Ticks down the weather duration. Switches state on expiration, returning announcement."""
        self.turns_remaining -= 1
        if self.turns_remaining <= 0:
            new_key = random.choice(list(self.STATES.keys()))
            self.current_state = self.STATES[new_key]
            self.turns_remaining = random.randint(12, 24)
            return (
                f"\n🌦️ [{self.current_state.visual_style}]The weather has shifted: "
                f"{self.current_state.name}![/{self.current_state.visual_style}]\n"
                f"[dim]{self.current_state.description}[/dim]"
            )
        return None


class EnvironmentalHazard:
    """Defines room-based environmental dangers that tick damage on player movement."""

    def __init__(
        self,
        hazard_type: str,
        damage_per_tick: int,
        description: str,
        mitigation_item: Optional[str] = None,
    ):
        self.hazard_type = hazard_type
        self.damage_per_tick = damage_per_tick
        self.description = description
        self.mitigation_item = mitigation_item

    def resolve_tick(self, player: Any) -> Optional[str]:
        """Applies damage if the player lacks protective mitigation gear."""
        if self.mitigation_item and player.has_item(self.mitigation_item):
            return f"[dim]🛡️ Your {self.mitigation_item} protects you from the {self.hazard_type}.[/dim]"

        player.hp = max(1, player.hp - self.damage_per_tick)
        return f"[bold red]⚠️ {self.description}! You take {self.damage_per_tick} environmental damage.[/bold red]"
