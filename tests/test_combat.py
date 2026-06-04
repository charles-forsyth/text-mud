import unittest
from aetheria.entity import Player, Companion, Enemy
from aetheria.models import Consumable
from aetheria.combat import CombatManager


class TestAetheriaCombat(unittest.TestCase):
    def setUp(self):
        # Create Player and Companion
        self.player = Player(
            name="Hero",
            char_class="Warrior",
            hp=100,
            max_hp=100,
            mana=20,
            max_mana=20,
            attack=15,
            defense=5,
        )
        self.companion = Companion(
            name="Lyra",
            char_class="Mage",
            personality="Sarcastic elven mage",
            hp=80,
            max_hp=80,
            mana=30,
            max_mana=30,
            attack=10,
            defense=3,
        )
        self.enemy = Enemy(
            name="Goblin",
            description="Nasty green goblin.",
            hp=40,
            max_hp=45,
            attack=12,
            defense=3,
            level=2,
            xp_value=50,
            gold_value=10,
        )

    def test_entity_damage_mitigation(self):
        # Enemy base attack is 12, Player defense is 5
        # With hyperbolic curve and attacker_level=1, DR = 5 / (5 + 15) = 0.25
        # Inflicted damage = round(12 * 0.75) = 9
        inflicted = self.player.take_damage(12)
        self.assertEqual(inflicted, 9)
        self.assertEqual(self.player.hp, 91)

    def test_entity_healing(self):
        self.player.hp = 75
        self.player.heal(20)
        self.assertEqual(self.player.hp, 95)
        self.player.heal(100)  # Should cap at max_hp (100)
        self.assertEqual(self.player.hp, 100)

    def test_spells_list_initialization(self):
        # Warrior spells should include Slash and Shield Wall
        spell_names = [spell.name for spell in self.player.spells]
        self.assertIn("Slash", spell_names)
        self.assertIn("Shield Wall", spell_names)

    def test_consumable_usage(self):
        potion = Consumable(
            "Test Potion", "Restores HP and MP", value=10, hp_restore=15, mp_restore=10
        )
        self.player.hp = 75
        self.player.spend_mana(5)  # mp becomes 15

        self.player.inventory.append(potion)
        summary = potion.use(self.player)
        self.player.inventory.remove(potion)

        self.assertIn("Healed 15 HP", summary)
        self.assertIn("Restored 10 Mana", summary)
        self.assertEqual(self.player.hp, 90)
        self.assertEqual(self.player.mana, 20)

    def test_combat_manager_victory(self):
        # Setup Combat
        manager = CombatManager(self.player, [self.companion], self.enemy)

        # Rig enemy HP to low to trigger victory in one turn
        self.enemy.hp = 5

        # Execute basic attack round
        logs = manager.execute_round("attack")

        self.assertFalse(self.enemy.is_alive)
        self.assertFalse(manager.is_active)
        # Check loot distributions in logs
        self.assertTrue(
            any("Looted" in line and "10" in line and "Gold" in line for line in logs)
        )
        self.assertTrue(
            any("Gained" in line and "50" in line and "XP" in line for line in logs)
        )

    def test_xp_and_level_up(self):
        # Player level 1 starts with 0 XP. 100 XP to next level
        announcements = self.player.gain_xp(110)
        self.assertEqual(self.player.level, 2)
        self.assertEqual(self.player.xp, 10)  # Carried over
        self.assertTrue(any("LEVEL UP" in line for line in announcements))
        # Base max HP should have increased
        self.assertGreater(self.player.max_hp, 100)


if __name__ == "__main__":
    unittest.main()
