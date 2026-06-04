from typing import Any, Dict, List, Optional
from aetheria.models import Item, Equipment, EquipmentSlot, Spell, deserialize_item
from aetheria.talents import SkillTree, get_tree_for_class
from aetheria.ailments import AilmentContainer


class Entity:
    def __init__(
        self,
        name: str,
        description: str,
        hp: int = 100,
        max_hp: int = 100,
        mana: int = 20,
        max_mana: int = 20,
        attack: int = 10,
        defense: int = 5,
        level: int = 1,
        gold: int = 0,
    ):
        self.name = name
        self.description = description
        self.level = level
        self._hp = hp
        self._max_hp = max_hp
        self._mana = mana
        self._max_mana = max_mana
        self._attack = attack
        self._defense = defense
        self.gold = gold
        self.spells: List[Spell] = []
        self.ailments = AilmentContainer(self)

    @property
    def max_hp(self) -> int:
        return self._max_hp

    @property
    def max_mana(self) -> int:
        return self._max_mana

    @property
    def attack(self) -> int:
        return self._attack

    @property
    def defense(self) -> int:
        return self._defense

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, val: int):
        self._hp = max(0, min(self.max_hp, val))

    @property
    def mana(self) -> int:
        return self._mana

    @mana.setter
    def mana(self, val: int):
        self._mana = max(0, min(self.max_mana, val))

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int, attacker_level: int = 1) -> int:
        """
        Inflicts non-linear mitigated damage using a hyperbolic diminishing returns curve.
        Guarantees defense scales safely and never permanently locks combat at 1 damage.
        """
        # Tuning constant: higher values increase defense requirements to achieve 50% DR
        k_scale = 15.0

        # Scale defense requirements dynamically based on attacker tier to prevent over-level trivialization
        scaled_denominator = self.defense + (k_scale * max(1, attacker_level))

        # Prevent divide-by-zero if defense is zero
        if scaled_denominator > 0:
            damage_reduction = self.defense / scaled_denominator
        else:
            damage_reduction = 0.0

        # Apply damage reduction (capped at 85% maximum reduction to prevent absolute immunity)
        damage_reduction = min(0.85, damage_reduction)

        mitigated = int(round(amount * (1.0 - damage_reduction)))
        actual_damage = max(1, mitigated)

        self.hp -= actual_damage
        return actual_damage

    def heal(self, amount: int):
        """Restores health, capping at max_hp."""
        self.hp += amount

    def restore_mana(self, amount: int):
        """Restores mana, capping at max_mana."""
        self.mana += amount

    def spend_mana(self, amount: int) -> bool:
        """Attempts to spend mana. Returns True if successful, False otherwise."""
        if self.mana >= amount:
            self.mana -= amount
            return True
        return False


class Player(Entity):
    def __init__(
        self,
        name: str,
        char_class: str,
        hp: int = 100,
        max_hp: int = 100,
        mana: int = 30,
        max_mana: int = 30,
        attack: int = 12,
        defense: int = 6,
        level: int = 1,
        xp: int = 0,
        gold: int = 50,
    ):
        super().__init__(
            name,
            "The chosen adventurer.",
            hp,
            max_hp,
            mana,
            max_mana,
            attack,
            defense,
            level,
            gold,
        )
        self.char_class = char_class.capitalize()
        self.xp = xp
        self.inventory: List[Item] = []
        self.equipment: Dict[EquipmentSlot, Optional[Equipment]] = {
            EquipmentSlot.WEAPON: None,
            EquipmentSlot.BODY_ARMOR: None,
            EquipmentSlot.SHIELD: None,
            EquipmentSlot.ACCESSORY: None,
        }
        self.active_quests: List[str] = []  # Quest IDs
        self.completed_quests: List[str] = []
        self.current_room: Any = None
        self.skill_points = 0
        self.talent_tree = get_tree_for_class(self.char_class)
        self._init_class_spells()

    def _init_class_spells(self):
        """Grants starting spell lists according to character class."""
        self.spells = []
        if self.char_class == "Warrior":
            self.spells.append(
                Spell("Slash", "A sweeping sword swing.", mana_cost=5, damage=22)
            )
            self.spells.append(
                Spell(
                    "Shield Wall",
                    "A defensive posture that bolsters iron grit.",
                    mana_cost=10,
                    healing=15,
                )
            )
        elif self.char_class == "Mage":
            self.spells.append(
                Spell(
                    "Fireball",
                    "A bolt of raging mystical flame.",
                    mana_cost=10,
                    damage=35,
                )
            )
            self.spells.append(
                Spell(
                    "Mana Shield",
                    "Uses magic to heal minor wounds.",
                    mana_cost=8,
                    healing=18,
                )
            )
        elif self.char_class == "Rogue":
            self.spells.append(
                Spell(
                    "Backstab",
                    "A strike aimed directly at weak spots.",
                    mana_cost=6,
                    damage=26,
                )
            )
            self.spells.append(
                Spell(
                    "Poison Strike", "Applies corrosive venom.", mana_cost=8, damage=30
                )
            )
        elif self.char_class == "Cleric":
            self.spells.append(
                Spell("Smite", "Holy light burns the enemy.", mana_cost=7, damage=20)
            )
            self.spells.append(
                Spell("Heal", "Divine grace heals wounds.", mana_cost=8, healing=25)
            )

    def unlock_spell_from_tree(self, spell_name: str):
        """Unlocks a special high-tier spell unlocked via the Talent Tree."""
        spell_templates = {
            "Shield Slam": Spell(
                "Shield Slam",
                "Slam your shield, dealing massive physical damage.",
                mana_cost=8,
                damage=35,
                class_req="Warrior",
            ),
            "Meteor": Spell(
                "Meteor",
                "A colossal meteor strikes from above, dealing catastrophic damage.",
                mana_cost=15,
                damage=55,
                class_req="Mage",
            ),
            "Assassinate": Spell(
                "Assassinate",
                "Deliver a fatal blow from the shadows.",
                mana_cost=10,
                damage=48,
                class_req="Rogue",
            ),
            "Resurrect": Spell(
                "Resurrect",
                "Holy light restores massive vitality.",
                mana_cost=12,
                healing=50,
                class_req="Cleric",
            ),
        }
        if spell_name in spell_templates:
            if not any(s.name == spell_name for s in self.spells):
                self.spells.append(spell_templates[spell_name])

    @property
    def max_hp(self) -> int:
        bonus = sum(eq.max_hp_bonus for eq in self.equipment.values() if eq is not None)
        mult = 1.0 + self.talent_tree.get_cumulative_multiplier("max_hp_multiplier")
        return int((self._max_hp + bonus) * mult)

    @property
    def max_mana(self) -> int:
        bonus = sum(
            eq.max_mana_bonus for eq in self.equipment.values() if eq is not None
        )
        mult = 1.0 + self.talent_tree.get_cumulative_multiplier("max_mana_multiplier")
        return int((self._max_mana + bonus) * mult)

    @property
    def attack(self) -> int:
        bonus = sum(eq.attack_bonus for eq in self.equipment.values() if eq is not None)
        mult = 1.0 + self.talent_tree.get_cumulative_multiplier("attack_multiplier")
        return int((self._attack + bonus) * mult)

    @property
    def defense(self) -> int:
        bonus = sum(
            eq.defense_bonus for eq in self.equipment.values() if eq is not None
        )
        mult = 1.0 + self.talent_tree.get_cumulative_multiplier("defense_multiplier")
        return int((self._defense + bonus) * mult)

    @property
    def evasion(self) -> float:
        """Returns the accumulated evasion percentage from talents."""
        return self.talent_tree.get_cumulative_multiplier("evasion_multiplier")

    def equip(self, item: Equipment) -> Optional[Equipment]:
        """Equips an item, returning the previously equipped item in that slot, if any."""
        old_eq = self.equipment[item.slot]
        self.equipment[item.slot] = item
        if old_eq:
            self.inventory.append(old_eq)
        if item in self.inventory:
            self.inventory.remove(item)
        return old_eq

    def unequip(self, slot: EquipmentSlot) -> bool:
        """Unequips an item, placing it back in the inventory."""
        eq = self.equipment[slot]
        if eq:
            self.inventory.append(eq)
            self.equipment[slot] = None
            return True
        return False

    def gain_xp(self, amount: int) -> List[str]:
        """Adds XP and triggers level ups. Returns a list of log announcements."""
        self.xp += amount
        announcements = []
        next_level_req = self.xp_to_next_level()
        while self.xp >= next_level_req:
            self.xp -= next_level_req
            self.level += 1
            self.skill_points += 2
            # Scale Base Stats
            hp_gain = 15 if self.char_class == "Warrior" else 10
            mp_gain = 5 if self.char_class == "Mage" else 3
            atk_gain = 3 if self.char_class in ["Warrior", "Rogue"] else 2
            def_gain = 2 if self.char_class in ["Warrior", "Cleric"] else 1

            self._max_hp += hp_gain
            self._max_mana += mp_gain
            self._attack += atk_gain
            self._defense += def_gain

            self.hp = self.max_hp
            self.mana = self.max_mana
            announcements.append(
                f"[bold green]LEVEL UP![/bold green] You reached Level {self.level}! "
                f"(+{hp_gain} HP, +{mp_gain} MP, +{atk_gain} ATK, +{def_gain} DEF, +2 Skill Points)"
            )
            next_level_req = self.xp_to_next_level()
        return announcements

    def xp_to_next_level(self) -> int:
        return 100 + (self.level - 1) * 50

    def has_item(self, item_name: str) -> bool:
        """Checks if the player has an item with the given name in their inventory."""
        return any(item.name.lower() == item_name.lower() for item in self.inventory)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "char_class": self.char_class,
            "level": self.level,
            "xp": self.xp,
            "gold": self.gold,
            "hp": self.hp,
            "max_hp": self._max_hp,
            "mana": self.mana,
            "max_mana": self._max_mana,
            "attack": self._attack,
            "defense": self._defense,
            "inventory": [item.to_dict() for item in self.inventory],
            "equipment": {
                slot.value: (eq.to_dict() if eq else None)
                for slot, eq in self.equipment.items()
            },
            "active_quests": self.active_quests,
            "completed_quests": self.completed_quests,
            "skill_points": self.skill_points,
            "talent_tree": self.talent_tree.to_dict(),
            "ailments": self.ailments.to_list(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        player = cls(
            name=data["name"],
            char_class=data["char_class"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            mana=data["mana"],
            max_mana=data["max_mana"],
            attack=data["attack"],
            defense=data["defense"],
            level=data["level"],
            xp=data["xp"],
            gold=data["gold"],
        )
        player.inventory = [deserialize_item(i) for i in data.get("inventory", [])]

        # Equipment Restore
        eq_data = data.get("equipment", {})
        for slot_str, item_dict in eq_data.items():
            slot = EquipmentSlot(slot_str)
            if item_dict:
                player.equipment[slot] = Equipment.from_dict(item_dict)

        player.active_quests = data.get("active_quests", [])
        player.completed_quests = data.get("completed_quests", [])
        player.skill_points = data.get("skill_points", 0)
        if "talent_tree" in data:
            player.talent_tree = SkillTree.from_dict(data["talent_tree"])
        if "ailments" in data:
            player.ailments.load_from_list(data["ailments"])
        return player


class Companion(Entity):
    def __init__(
        self,
        name: str,
        char_class: str,
        personality: str,
        hp: int = 90,
        max_hp: int = 90,
        mana: int = 20,
        max_mana: int = 20,
        attack: int = 10,
        defense: int = 4,
        level: int = 1,
    ):
        super().__init__(
            name,
            f"A recruitable {char_class}.",
            hp,
            max_hp,
            mana,
            max_mana,
            attack,
            defense,
            level,
            gold=0,
        )
        self.char_class = char_class.capitalize()
        self.personality = personality
        self._init_companion_spells()

    def _init_companion_spells(self):
        self.spells = []
        if self.char_class == "Mage":
            self.spells.append(
                Spell("Spark", "Spark of electricity.", mana_cost=4, damage=18)
            )
            self.spells.append(
                Spell("Fireball", "Raging fireball.", mana_cost=10, damage=35)
            )
        elif self.char_class == "Cleric":
            self.spells.append(
                Spell("Heal", "Restorative warmth.", mana_cost=8, healing=22)
            )
            self.spells.append(
                Spell("Holy Bolt", "Holy blast.", mana_cost=6, damage=16)
            )
        elif self.char_class == "Warrior":
            self.spells.append(
                Spell("Cleave", "Heavily strikes the enemy.", mana_cost=5, damage=20)
            )
        elif self.char_class == "Rogue":
            self.spells.append(
                Spell("Quick Strike", "Stabs with precision.", mana_cost=5, damage=22)
            )

    def level_up(self):
        """Levels up the companion to match player tier."""
        self.level += 1
        hp_gain = 12 if self.char_class == "Warrior" else 8
        mp_gain = 4 if self.char_class == "Mage" else 2
        atk_gain = 2
        def_gain = 2 if self.char_class == "Warrior" else 1

        self._max_hp += hp_gain
        self._max_mana += mp_gain
        self._attack += atk_gain
        self._defense += def_gain

        self.hp = self.max_hp
        self.mana = self.max_mana

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "char_class": self.char_class,
            "personality": self.personality,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self._max_hp,
            "mana": self.mana,
            "max_mana": self._max_mana,
            "attack": self._attack,
            "defense": self._defense,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Companion":
        companion = cls(
            name=data["name"],
            char_class=data["char_class"],
            personality=data["personality"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            mana=data["mana"],
            max_mana=data["max_mana"],
            attack=data["attack"],
            defense=data["defense"],
            level=data["level"],
        )
        return companion


class Enemy(Entity):
    def __init__(
        self,
        name: str,
        description: str,
        hp: int,
        max_hp: int,
        attack: int,
        defense: int,
        level: int,
        xp_value: int,
        gold_value: int,
    ):
        super().__init__(
            name,
            description,
            hp,
            max_hp,
            mana=0,
            max_mana=0,
            attack=attack,
            defense=defense,
            level=level,
            gold=gold_value,
        )
        self.xp_value = xp_value

    def choose_action(self) -> dict:
        """Returns the enemy's attack stats for the current turn."""
        return {"name": "Basic Attack", "damage": self.attack, "is_spell": False}

    def to_dict(self) -> dict:
        return {
            "type": "Enemy",
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "attack": self.attack,
            "defense": self.defense,
            "xp_value": self.xp_value,
            "gold_value": self.gold,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Enemy":
        return cls(
            name=data["name"],
            description=data["description"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            attack=data["attack"],
            defense=data["defense"],
            level=data["level"],
            xp_value=data["xp_value"],
            gold_value=data["gold_value"],
        )


class Boss(Enemy):
    def __init__(
        self,
        name: str,
        description: str,
        hp: int,
        max_hp: int,
        attack: int,
        defense: int,
        level: int,
        xp_value: int,
        gold_value: int,
        phases: int = 1,
    ):
        super().__init__(
            name, description, hp, max_hp, attack, defense, level, xp_value, gold_value
        )
        self.max_phases = phases
        self.current_phase = 1

    def choose_action(self) -> dict:
        """Advanced Boss action choosing based on phases or HP levels."""
        hp_pct = self.hp / self.max_hp
        if hp_pct < 0.3 and self.current_phase == 1 and self.max_phases > 1:
            # Phase 2 Trigger
            self.current_phase = 2
            self._attack += 5
            self._defense += 2
            return {
                "name": "[bold red]Aether Rage[/bold red] (Phase 2 Form!)",
                "damage": self.attack + 10,
                "is_spell": True,
                "announcement": f"{self.name} unleashes a blinding roar, expanding in size and overflowing with pure shadow magic!",
            }

        if hp_pct < 0.5:
            return {
                "name": "Crushing Slam",
                "damage": int(self.attack * 1.4),
                "is_spell": False,
            }
        else:
            return {
                "name": "Cleave strike",
                "damage": self.attack,
                "is_spell": False,
            }

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["type"] = "Boss"
        data["phases"] = self.max_phases
        data["current_phase"] = self.current_phase
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Boss":
        boss = cls(
            name=data["name"],
            description=data["description"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            attack=data["attack"],
            defense=data["defense"],
            level=data["level"],
            xp_value=data["xp_value"],
            gold_value=data["gold_value"],
            phases=data.get("phases", 1),
        )
        boss.current_phase = data.get("current_phase", 1)
        return boss


def deserialize_enemy(data: dict) -> Optional[Enemy]:
    if not data:
        return None
    t = data.get("type", "Enemy")
    if t == "Boss":
        return Boss.from_dict(data)
    else:
        return Enemy.from_dict(data)
