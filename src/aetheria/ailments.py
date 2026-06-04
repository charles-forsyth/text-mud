from typing import Dict, List, Optional, Tuple, Any


class StatusEffect:
    """Represents an active status condition affecting combat performance."""

    def __init__(
        self,
        name: str,
        duration: int,
        dot_damage: int = 0,
        stat_modifiers: Optional[dict] = None,
    ):
        self.name = name
        self.duration = duration
        self.dot_damage = dot_damage
        self.stat_modifiers = stat_modifiers or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration": self.duration,
            "dot_damage": self.dot_damage,
            "stat_modifiers": self.stat_modifiers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StatusEffect":
        return cls(
            name=data["name"],
            duration=data["duration"],
            dot_damage=data.get("dot_damage", 0),
            stat_modifiers=data.get("stat_modifiers"),
        )


class AilmentContainer:
    """Tracks active ailments and resolves damage and duration decays."""

    def __init__(self, parent_entity: Any):
        self.parent = parent_entity
        self.active_effects: Dict[str, StatusEffect] = {}

    def apply_effect(self, effect: StatusEffect) -> str:
        """Afflicts or refreshes an effect, returning a descriptive string."""
        self.active_effects[effect.name] = effect
        return f"[bold red]💀 {self.parent.name} is afflicted by {effect.name} for {effect.duration} rounds![/bold red]"

    def resolve_ticks(self) -> List[str]:
        """Resolves tick damage and updates remaining durations."""
        logs = []
        for name in list(self.active_effects.keys()):
            effect = self.active_effects[name]

            # Process Damage over Time (DoT)
            if effect.dot_damage > 0:
                self.parent.hp -= effect.dot_damage
                logs.append(
                    f"🩸 [bold red]{self.parent.name}[/bold red] suffers {effect.dot_damage} "
                    f"damage from {effect.name}! ({self.parent.hp}/{self.parent.max_hp} HP)"
                )

            effect.duration -= 1
            if effect.duration <= 0:
                if name in self.active_effects:
                    del self.active_effects[name]
                logs.append(
                    f"[bold green]✨ {self.parent.name} has recovered from {name}.[/bold green]"
                )

        return logs

    def to_list(self) -> list[dict]:
        return [effect.to_dict() for effect in self.active_effects.values()]

    def load_from_list(self, data_list: list):
        self.active_effects.clear()
        for item in data_list:
            effect = StatusEffect.from_dict(item)
            self.active_effects[effect.name] = effect


def resolve_elemental_combos(
    attacker: Any, defender: Any, damage_type: str
) -> Optional[Tuple[int, str]]:
    """Evaluates active statuses and applied damage types to trigger elemental combos."""
    container = getattr(defender, "ailments", None)
    if not container:
        return None

    # 1. SHATTER: Heavy/Physical damage hitting a Frozen defender
    if "Frozen" in container.active_effects and damage_type == "physical":
        del container.active_effects["Frozen"]
        bonus_dmg = 35
        return (
            bonus_dmg,
            "❄️ [bold royal_blue1]SHATTER![/bold royal_blue1] Smashing frozen armor inflicts massive crushing criticals!",
        )

    # 2. VAPORIZE: Fire damage hitting a Wet defender
    if "Wet" in container.active_effects and damage_type == "fire":
        del container.active_effects["Wet"]
        bonus_dmg = 25
        return (
            bonus_dmg,
            "💨 [bold orange3]VAPORIZE![/bold orange3] Boiling vapor erupts, shredding defense and burning flesh!",
        )

    # 3. CONDUCTIVE OVERLOAD: Lightning hitting a Wet defender
    if "Wet" in container.active_effects and damage_type == "lightning":
        del container.active_effects["Wet"]
        bonus_dmg = 30
        return (
            bonus_dmg,
            "⚡ [bold yellow]CONDUCTIVE OVERLOAD![/bold yellow] Lightning arcs wildly, causing shocking kinetic explosions!",
        )

    return None
