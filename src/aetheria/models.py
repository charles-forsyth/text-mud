from enum import Enum


class EquipmentSlot(str, Enum):
    WEAPON = "weapon"
    BODY_ARMOR = "body_armor"
    SHIELD = "shield"
    ACCESSORY = "accessory"


class Item:
    def __init__(
        self, name: str, description: str, value: int = 0, is_quest_item: bool = False
    ):
        self.name = name
        self.description = description
        self.value = value
        self.is_quest_item = is_quest_item

    def to_dict(self) -> dict:
        return {
            "type": "Item",
            "name": self.name,
            "description": self.description,
            "value": self.value,
            "is_quest_item": self.is_quest_item,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        return cls(
            name=data["name"],
            description=data["description"],
            value=data.get("value", 0),
            is_quest_item=data.get("is_quest_item", False),
        )

    def __str__(self) -> str:
        return f"{self.name} - {self.description} ({self.value} Gold)"


class Equipment(Item):
    def __init__(
        self,
        name: str,
        description: str,
        slot: EquipmentSlot,
        value: int = 0,
        attack_bonus: int = 0,
        defense_bonus: int = 0,
        max_hp_bonus: int = 0,
        max_mana_bonus: int = 0,
    ):
        super().__init__(name, description, value, is_quest_item=False)
        self.slot = slot
        self.attack_bonus = attack_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus
        self.max_mana_bonus = max_mana_bonus

    def to_dict(self) -> dict:
        return {
            "type": "Equipment",
            "name": self.name,
            "description": self.description,
            "value": self.value,
            "slot": self.slot.value,
            "attack_bonus": self.attack_bonus,
            "defense_bonus": self.defense_bonus,
            "max_hp_bonus": self.max_hp_bonus,
            "max_mana_bonus": self.max_mana_bonus,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Equipment":
        return cls(
            name=data["name"],
            description=data["description"],
            slot=EquipmentSlot(data["slot"]),
            value=data.get("value", 0),
            attack_bonus=data.get("attack_bonus", 0),
            defense_bonus=data.get("defense_bonus", 0),
            max_hp_bonus=data.get("max_hp_bonus", 0),
            max_mana_bonus=data.get("max_mana_bonus", 0),
        )

    def __str__(self) -> str:
        bonuses = []
        if self.attack_bonus:
            bonuses.append(f"+{self.attack_bonus} ATK")
        if self.defense_bonus:
            bonuses.append(f"+{self.defense_bonus} DEF")
        if self.max_hp_bonus:
            bonuses.append(f"+{self.max_hp_bonus} HP")
        if self.max_mana_bonus:
            bonuses.append(f"+{self.max_mana_bonus} MP")
        bonus_str = f" ({', '.join(bonuses)})" if bonuses else ""
        return f"[{self.slot.name}] {self.name} - {self.description}{bonus_str} ({self.value} Gold)"


class Consumable(Item):
    def __init__(
        self,
        name: str,
        description: str,
        value: int = 0,
        hp_restore: int = 0,
        mp_restore: int = 0,
    ):
        super().__init__(name, description, value, is_quest_item=False)
        self.hp_restore = hp_restore
        self.mp_restore = mp_restore

    def use(self, target) -> str:
        """Applies consumable effects on a target entity."""
        output = []
        if self.hp_restore > 0:
            target.heal(self.hp_restore)
            output.append(f"Healed {self.hp_restore} HP.")
        if self.mp_restore > 0:
            target.restore_mana(self.mp_restore)
            output.append(f"Restored {self.mp_restore} Mana.")

        return f"Used {self.name}! " + " ".join(output)

    def to_dict(self) -> dict:
        return {
            "type": "Consumable",
            "name": self.name,
            "description": self.description,
            "value": self.value,
            "hp_restore": self.hp_restore,
            "mp_restore": self.mp_restore,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Consumable":
        return cls(
            name=data["name"],
            description=data["description"],
            value=data.get("value", 0),
            hp_restore=data.get("hp_restore", 0),
            mp_restore=data.get("mp_restore", 0),
        )


class Spell:
    def __init__(
        self,
        name: str,
        description: str,
        mana_cost: int,
        damage: int = 0,
        healing: int = 0,
        class_req: str = "",
    ):
        self.name = name
        self.description = description
        self.mana_cost = mana_cost
        self.damage = damage
        self.healing = healing
        self.class_req = class_req

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "mana_cost": self.mana_cost,
            "damage": self.damage,
            "healing": self.healing,
            "class_req": self.class_req,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Spell":
        return cls(
            name=data["name"],
            description=data["description"],
            mana_cost=data["mana_cost"],
            damage=data.get("damage", 0),
            healing=data.get("healing", 0),
            class_req=data.get("class_req", ""),
        )

    def __str__(self) -> str:
        details = []
        if self.damage:
            details.append(f"{self.damage} DMG")
        if self.healing:
            details.append(f"{self.healing} HEAL")
        return f"{self.name} (MP: {self.mana_cost}) - {self.description} [{', '.join(details)}]"


def deserialize_item(data: dict) -> Item:
    """Utility function to recreate the correct item subclass from JSON data."""
    t = data.get("type", "Item")
    if t == "Equipment":
        return Equipment.from_dict(data)
    elif t == "Consumable":
        return Consumable.from_dict(data)
    else:
        return Item.from_dict(data)
