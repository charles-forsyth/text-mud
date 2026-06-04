import random
from typing import Any, List, Optional, Tuple
from aetheria.entity import Player, Companion, Enemy
from aetheria.models import Spell, Consumable
from aetheria.ai_engine import generate_combat_banter


def calculate_evasion(entity: Any) -> float:
    """Calculates evasion probability based on Level, Class, and passive stat parameters."""
    base_evasion = 0.05  # 5% base dodge rate

    # Rogues and agility-based heroes gain an inherent +10% evasion boost
    class_bonus = 0.10 if getattr(entity, "char_class", "") == "Rogue" else 0.00

    level_scaling = (entity.level * 0.01) / (1.0 + entity.level * 0.01)
    return min(
        0.50, base_evasion + class_bonus + level_scaling
    )  # Cap maximum dodge at 50%


class CombatManager:
    def __init__(self, player: Player, party: List[Companion], enemy: Enemy):
        self.player = player
        self.party = [c for c in party if c.is_alive]
        self.enemy = enemy
        self.is_active = True
        self.fled = False
        self.round_log: List[str] = []
        self.defending: List[str] = []  # Names of entities defending this turn

    def get_battle_status(self) -> dict:
        """Returns structured information about the current combat status."""
        return {
            "player": {
                "name": self.player.name,
                "hp": self.player.hp,
                "max_hp": self.player.max_hp,
                "mana": self.player.mana,
                "max_mana": self.player.max_mana,
            },
            "party": [
                {
                    "name": c.name,
                    "hp": c.hp,
                    "max_hp": c.max_hp,
                    "mana": c.mana,
                    "max_mana": c.max_mana,
                    "class": c.char_class,
                }
                for c in self.party
            ],
            "enemy": {
                "name": self.enemy.name,
                "hp": self.enemy.hp,
                "max_hp": self.enemy.max_hp,
                "level": self.enemy.level,
            },
        }

    def execute_round(
        self,
        player_action: str,  # "attack", "spell", "item", "defend"
        spell: Optional[Spell] = None,
        consumable: Optional[Consumable] = None,
    ) -> List[str]:
        """Runs a complete combat round where player, companions, and enemy all act."""
        self.round_log = []
        self.defending = []

        # 1. Establish Turn Order (Initiative: Player & Companions go first, then Enemy)
        participants: List[Tuple[str, Any]] = [("player", self.player)]
        for companion in self.party:
            if companion.is_alive:
                participants.append(("companion", companion))

        # 2. Process Ally Turns
        for role, entity in participants:
            if not self.enemy.is_alive:
                break

            if role == "player":
                self._process_player_turn(player_action, spell, consumable)
            elif role == "companion":
                self._process_companion_auto_turn(entity)

        # 3. Process Enemy Turn
        if self.enemy.is_alive:
            self._process_enemy_turn()

        # 4. Check Post-Combat Status (Victory / Defeat)
        if not self.enemy.is_alive:
            self._process_victory()
        elif not self.player.is_alive:
            self._process_defeat()

        return self.round_log

    def attempt_flee(self) -> bool:
        """Attempts to escape from the battle. Success rate is 60%."""
        success = random.random() < 0.60
        if success:
            self.is_active = False
            self.fled = True
        return success

    def _process_player_turn(
        self, action: str, spell: Optional[Spell], consumable: Optional[Consumable]
    ):
        if action == "defend":
            self.defending.append(self.player.name)
            self.round_log.append(
                f"[yellow]{self.player.name} raises their guard, preparing to defend.[/yellow]"
            )
            return

        if action == "item" and consumable:
            summary = consumable.use(self.player)
            self.player.inventory.remove(consumable)
            self.round_log.append(f"[green]{summary}[/green]")
            return

        if action == "spell" and spell:
            if self.player.spend_mana(spell.mana_cost):
                if spell.damage > 0:
                    damage = spell.damage + int(self.player.attack * 0.5)
                    inflicted = self.enemy.take_damage(
                        damage, attacker_level=self.player.level
                    )
                    self.round_log.append(
                        f"🌟 {self.player.name} casts [bold cyan]{spell.name}[/bold cyan] at the {self.enemy.name}! "
                        f"Deals [bold red]{inflicted}[/bold red] magical damage! "
                        f"({self.enemy.name} HP: {self.enemy.hp}/{self.enemy.max_hp})"
                    )
                if spell.healing > 0:
                    self.player.heal(spell.healing)
                    self.round_log.append(
                        f"💖 {self.player.name} casts [bold green]{spell.name}[/bold green] on themselves, "
                        f"healing for [bold green]{spell.healing}[/bold green] HP."
                    )
            else:
                self.round_log.append(
                    f"[red]Not enough Mana to cast {spell.name}![/red]"
                )
            return

        # Default Basic Attack
        evasion_rate = calculate_evasion(self.enemy)
        if random.random() < evasion_rate:
            self.round_log.append(
                f"💨 {self.enemy.name} swiftly dodges the incoming blow from {self.player.name}!"
            )
            return

        damage = self.player.attack
        is_crit = random.random() < (
            0.25 if getattr(self.player, "char_class", "") == "Rogue" else 0.15
        )
        if is_crit:
            damage = int(damage * 1.5)

        inflicted = self.enemy.take_damage(damage, attacker_level=self.player.level)
        crit_str = "[bold red]CRITICAL HIT![/bold red] " if is_crit else ""
        self.round_log.append(
            f"⚔️ {crit_str}{self.player.name} strikes the {self.enemy.name}! "
            f"Deals [bold red]{inflicted}[/bold red] physical damage! "
            f"({self.enemy.name} HP: {self.enemy.hp}/{self.enemy.max_hp})"
        )

    def _process_companion_auto_turn(self, companion: Companion):
        """Simplistic AI rules for companions in party combat."""
        # 1. Healing check: If companion or player is low HP, and companion has Heal
        target = self.player if self.player.hp < self.player.max_hp * 0.4 else companion
        heal_spells = [s for s in companion.spells if s.healing > 0]

        if (
            (target.hp < target.max_hp * 0.5)
            and heal_spells
            and companion.mana >= heal_spells[0].mana_cost
        ):
            spell = heal_spells[0]
            companion.spend_mana(spell.mana_cost)
            target.heal(spell.healing)
            self.round_log.append(
                f"✨ {companion.name} casts [bold green]{spell.name}[/bold green] on {target.name}, "
                f"healing for [bold green]{spell.healing}[/bold green] HP."
            )
            # Dynamic Banter on healing
            banter = generate_combat_banter(
                companion.name, companion.personality, "critical_hit", self.enemy.name
            )
            if banter:
                self.round_log.append(f'[dim]{companion.name}: "{banter}"[/dim]')
            return

        # 2. Attack check: Cast damage spell if mana is plenty
        dmg_spells = [s for s in companion.spells if s.damage > 0]
        if (
            dmg_spells
            and companion.mana >= dmg_spells[0].mana_cost
            and random.random() < 0.60
        ):
            spell = dmg_spells[0]
            companion.spend_mana(spell.mana_cost)
            damage = spell.damage + int(companion.attack * 0.3)
            inflicted = self.enemy.take_damage(damage, attacker_level=companion.level)
            self.round_log.append(
                f"🔥 {companion.name} casts [bold cyan]{spell.name}[/bold cyan]! "
                f"Deals [bold red]{inflicted}[/bold red] magical damage! "
                f"({self.enemy.name} HP: {self.enemy.hp}/{self.enemy.max_hp})"
            )
            return

        # Default basic attack
        evasion_rate = calculate_evasion(self.enemy)
        if random.random() < evasion_rate:
            self.round_log.append(
                f"💨 {self.enemy.name} swiftly dodges the incoming blow from {companion.name}!"
            )
            return

        damage = companion.attack
        is_crit = random.random() < (
            0.25 if getattr(companion, "char_class", "") == "Rogue" else 0.10
        )
        if is_crit:
            damage = int(damage * 1.5)
        inflicted = self.enemy.take_damage(damage, attacker_level=companion.level)
        crit_str = "[bold red]CRITICAL HIT![/bold red] " if is_crit else ""
        self.round_log.append(
            f"⚔️ {companion.name} attacks! {crit_str}Deals [bold red]{inflicted}[/bold red] damage! "
            f"({self.enemy.name} HP: {self.enemy.hp}/{self.enemy.max_hp})"
        )

        # Trigger Attack Banter
        if is_crit:
            banter = generate_combat_banter(
                companion.name, companion.personality, "critical_hit", self.enemy.name
            )
            if banter:
                self.round_log.append(f'[dim]{companion.name}: "{banter}"[/dim]')
        elif random.random() < 0.30:
            banter = generate_combat_banter(
                companion.name, companion.personality, "ally_hit", self.enemy.name
            )
            if banter:
                self.round_log.append(f'[dim]{companion.name}: "{banter}"[/dim]')

    def _process_enemy_turn(self):
        # Choose a target (Player gets targeted 60% of the time, companions 40%)
        target: Any = self.player
        if self.party and random.random() < 0.40:
            target = random.choice([c for c in self.party if c.is_alive])

        # Boss vs Enemy actions
        action = self.enemy.choose_action()
        damage = action["damage"]

        if "announcement" in action:
            self.round_log.append(action["announcement"])

        # Check evasion for incoming enemy attacks
        evasion_rate = calculate_evasion(target)
        if random.random() < evasion_rate:
            self.round_log.append(
                f"💨 {target.name} swiftly dodges the incoming blow '{action['name']}' from {self.enemy.name}!"
            )
            return

        # Defense calculation
        is_defending = target.name in self.defending
        mitigated_damage = damage
        if is_defending:
            mitigated_damage = int(damage * 0.5)

        inflicted = target.take_damage(
            mitigated_damage, attacker_level=self.enemy.level
        )
        def_str = " (Defending!)" if is_defending else ""

        self.round_log.append(
            f"💀 {self.enemy.name} uses [bold red]{action['name']}[/bold red] on {target.name}! "
            f"Deals [bold red]{inflicted}[/bold red] damage{def_str}! "
            f"({target.name} HP: {target.hp}/{target.max_hp})"
        )

        # Companion cry out if hurt
        if (
            isinstance(target, Companion)
            and inflicted > target.max_hp * 0.25
            and target.is_alive
        ):
            banter = generate_combat_banter(
                target.name, target.personality, "ally_hurt", self.enemy.name
            )
            if banter:
                self.round_log.append(f'[dim]{target.name}: "{banter}"[/dim]')

    def _process_victory(self):
        self.is_active = False
        self.round_log.append(
            f"\n🎉 [bold green]VICTORY![/bold green] Defeated the {self.enemy.name}!"
        )

        # Gold and XP Rewards
        xp_gained = self.enemy.xp_value
        gold_gained = self.enemy.gold

        self.player.gold += gold_gained
        self.round_log.append(
            f"💰 Looted [bold yellow]{gold_gained}[/bold yellow] Gold."
        )

        # Gain Player XP
        self.round_log.append(f"✨ Gained [bold cyan]{xp_gained}[/bold cyan] XP.")
        lvl_announcements = self.player.gain_xp(xp_gained)
        for ann in lvl_announcements:
            self.round_log.append(ann)

        # Gain Companions Level synchronization
        for companion in self.party:
            if companion.level < self.player.level:
                companion.level_up()
                self.round_log.append(
                    f"🌟 {companion.name} leveled up to Level {companion.level}!"
                )

    def _process_defeat(self):
        self.is_active = False
        self.round_log.append(
            "\n💀 [bold red]DEFEAT![/bold red] You have fallen in battle..."
        )
