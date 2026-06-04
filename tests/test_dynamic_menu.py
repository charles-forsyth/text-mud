import unittest
from aetheria.entity import Player, Companion
from aetheria.models import Consumable, Equipment, EquipmentSlot
from mud_game import GameController


class TestDynamicMenu(unittest.TestCase):
    def setUp(self):
        self.game = GameController()
        # Initialize a player manually to bypass character creation
        self.game.player = Player(name="TestHero", char_class="Warrior")
        self.game.player.current_room = self.game.world["Eldergrove Center"]

    def test_item_actions_visibility(self):
        # 1. Initially player has empty inventory.
        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]

        # Use and Equip should not be visible.
        self.assertNotIn("🎒 Use/Consume Item", action_names)
        self.assertNotIn("🛡️ Equip Armaments", action_names)

        # 2. Add a Consumable to inventory.
        potion = Consumable("Health Potion", "Restores HP", value=10, hp_restore=20)
        self.game.player.inventory.append(potion)

        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]
        self.assertIn("🎒 Use/Consume Item", action_names)
        self.assertNotIn("🛡️ Equip Armaments", action_names)

        # 3. Add an Equipment to inventory.
        sword = Equipment(
            "Bronze Sword", "A sharp blade", slot=EquipmentSlot.WEAPON, attack_bonus=5
        )
        self.game.player.inventory.append(sword)

        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]
        self.assertIn("🎒 Use/Consume Item", action_names)
        self.assertIn("🛡️ Equip Armaments", action_names)

    def test_companion_recruitment_visibility(self):
        # Move player to tavern
        self.game.player.current_room = self.game.world[
            "Eldergrove Tavern (The Golden Oak)"
        ]

        # Initially player party is empty. Should see recruitment options.
        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]

        recruitable_names = [c.name for c in self.game.tavern_companions]
        for name in recruitable_names:
            self.assertTrue(any(name in action for action in action_names))

        # Fill up party to 3 companions (which is MAX_PARTY_SIZE - 1 = 3)
        self.game.party = [
            Companion("Lyra", "Mage", "Dry wit"),
            Companion("Garrick", "Warrior", "Stoic"),
            Companion("Elena", "Rogue", "Sly"),
        ]

        # Now party is full. Recruitment actions should be filtered out.
        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]
        for name in recruitable_names:
            self.assertFalse(any(name in action for action in action_names))

    def test_npc_quest_shortcuts_visibility(self):
        # Let's test Tavernkeeper Barnaby
        self.game.player.current_room = self.game.world[
            "Eldergrove Tavern (The Golden Oak)"
        ]

        # Initially, Tavernkeeper Barnaby's quest is inactive. Shortcut should be shown.
        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]
        self.assertTrue(
            any("Barnaby" in action and "(Quest)" in action for action in action_names)
        )

        # Change quest status to active. Player doesn't have updates yet.
        self.game.quests["q_eldergrove_goblins"].status = "active"
        self.game.player.active_quests.append("q_eldergrove_goblins")

        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]
        self.assertFalse(
            any("Barnaby" in action and "(Quest)" in action for action in action_names)
        )

        # Now meet the objectives. Shortcut should reappear for hand-in.
        self.game.quests["q_eldergrove_goblins"].count_current = 1  # objective met

        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]
        self.assertTrue(
            any("Barnaby" in action and "(Quest)" in action for action in action_names)
        )

        # Now complete/hand-in the quest. Shortcut should be hidden.
        self.game.quests["q_eldergrove_goblins"].status = "completed"
        self.game.player.active_quests.remove("q_eldergrove_goblins")
        self.game.player.completed_quests.append("q_eldergrove_goblins")

        actions = self.game.get_current_quick_actions()
        action_names = [a[0] for a in actions]
        self.assertFalse(
            any("Barnaby" in action and "(Quest)" in action for action in action_names)
        )


if __name__ == "__main__":
    unittest.main()
