import random
from typing import Dict
from aetheria.models import Equipment


class ItemAffix:
    """Represents a prefix or suffix that alters item stats, names, and value multipliers."""

    def __init__(self, name: str, value_multiplier: float, stat_boosts: Dict[str, int]):
        self.name = name
        self.value_multiplier = value_multiplier
        self.stat_boosts = stat_boosts  # e.g., {"attack": 5, "max_hp": 15}


class LootGenerator:
    """Procedurally generates gear with balanced prefixes, suffixes, and colorized rarities."""

    PREFIXES = [
        ItemAffix("Savage", 1.35, {"attack": 5}),
        ItemAffix("Gleaming", 1.20, {"max_mana": 15}),
        ItemAffix("Stalwart", 1.25, {"defense": 4}),
        ItemAffix("Spectral", 1.40, {"attack": 3, "max_mana": 10}),
    ]

    SUFFIXES = [
        ItemAffix("of the Falcon", 1.20, {"defense": 2}),
        ItemAffix("of Smoldering Ember", 1.40, {"attack": 6}),
        ItemAffix("of Fortitude", 1.30, {"max_hp": 20}),
        ItemAffix("of the Phoenix", 1.50, {"max_hp": 15, "attack": 4}),
    ]

    RARITIES = {
        "Common": "white",
        "Rare": "bold royal_blue1",
        "Epic": "bold dark_violet",
        "Legendary": "bold gold1",
    }

    @classmethod
    def generate_loot(cls, base_equip: Equipment, level: int = 1) -> Equipment:
        """Applies prefix, suffix, value, and rarity calculations to customize equipment properties."""
        roll = random.random()

        prefix = None
        suffix = None
        rarity = "Common"

        if roll > 0.95:
            rarity = "Legendary"
            prefix = random.choice(cls.PREFIXES)
            suffix = random.choice(cls.SUFFIXES)
        elif roll > 0.80:
            rarity = "Epic"
            if random.random() < 0.5:
                prefix = random.choice(cls.PREFIXES)
            else:
                suffix = random.choice(cls.SUFFIXES)
        elif roll > 0.50:
            rarity = "Rare"
            suffix = random.choice(cls.SUFFIXES)

        # Assemble new procedural display name
        parts = []
        if prefix:
            parts.append(prefix.name)
        parts.append(base_equip.name)
        if suffix:
            parts.append(suffix.name)

        full_name = " ".join(parts)
        color = cls.RARITIES[rarity]

        # We preserve color formatting tags inside the rich-enabled MUD terminal
        colored_name = f"[{color}]{full_name}[/{color}]"

        # Apply scaling stats based on drop level and rolled affixes
        multiplier = 1.0 + (level - 1) * 0.10
        scaled_atk = int(base_equip.attack_bonus * multiplier)
        scaled_def = int(base_equip.defense_bonus * multiplier)
        scaled_hp = int(base_equip.max_hp_bonus * multiplier)
        scaled_mana = int(base_equip.max_mana_bonus * multiplier)
        scaled_val = int(base_equip.value * multiplier)

        if prefix:
            scaled_atk += prefix.stat_boosts.get("attack", 0)
            scaled_def += prefix.stat_boosts.get("defense", 0)
            scaled_hp += prefix.stat_boosts.get("max_hp", 0)
            scaled_mana += prefix.stat_boosts.get("max_mana", 0)
            scaled_val = int(scaled_val * prefix.value_multiplier)

        if suffix:
            scaled_atk += suffix.stat_boosts.get("attack", 0)
            scaled_def += suffix.stat_boosts.get("defense", 0)
            scaled_hp += suffix.stat_boosts.get("max_hp", 0)
            scaled_mana += suffix.stat_boosts.get("max_mana", 0)
            scaled_val = int(scaled_val * suffix.value_multiplier)

        # Create a newly populated customized Equipment instance
        custom_equip = Equipment(
            name=colored_name,
            description=f"Rarity: {rarity} | Level {level} Armament",
            slot=base_equip.slot,
            value=scaled_val,
            attack_bonus=scaled_atk,
            defense_bonus=scaled_def,
            max_hp_bonus=scaled_hp,
            max_mana_bonus=scaled_mana,
        )
        return custom_equip


def generate_random_loot(level: int = 1) -> Equipment:
    """Selects a random base equipment piece and generates custom prefixed/suffixed loot."""
    from aetheria.models import EquipmentSlot, Equipment

    pool = [
        Equipment(
            "Iron Sword",
            "A sturdy blade made of refined iron.",
            EquipmentSlot.WEAPON,
            value=30,
            attack_bonus=6,
        ),
        Equipment(
            "Steel Greatsword",
            "A heavy steel blade that requires two hands.",
            EquipmentSlot.WEAPON,
            value=50,
            attack_bonus=10,
        ),
        Equipment(
            "Oak Wand",
            "A simple wand tuned to focus arcane energy.",
            EquipmentSlot.WEAPON,
            value=25,
            attack_bonus=3,
            max_mana_bonus=15,
        ),
        Equipment(
            "Leather Jerkin",
            "Light leather armor providing decent protection.",
            EquipmentSlot.BODY_ARMOR,
            value=25,
            defense_bonus=3,
        ),
        Equipment(
            "Steel Plate",
            "Heavy plate armor crafted for front-line vanguard.",
            EquipmentSlot.BODY_ARMOR,
            value=60,
            defense_bonus=8,
            max_hp_bonus=20,
        ),
        Equipment(
            "Wooden Shield",
            "A simple round shield made of reinforced oak.",
            EquipmentSlot.SHIELD,
            value=20,
            defense_bonus=3,
        ),
        Equipment(
            "Steel Aegis",
            "A heavy steel tower shield of resolute protection.",
            EquipmentSlot.SHIELD,
            value=45,
            defense_bonus=6,
            max_hp_bonus=10,
        ),
        Equipment(
            "Silver Ring",
            "A polished silver ring radiating a faint glow.",
            EquipmentSlot.ACCESSORY,
            value=25,
            max_mana_bonus=10,
        ),
        Equipment(
            "Amulet of Life",
            "An ancient amulet pulsing with warm vitality.",
            EquipmentSlot.ACCESSORY,
            value=40,
            max_hp_bonus=15,
        ),
    ]
    base = random.choice(pool)
    return LootGenerator.generate_loot(base, level)
