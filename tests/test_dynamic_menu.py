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

    def test_shorthand_npc_dialogue_parsing(self):
        # Place player in the tavern
        self.game.player.current_room = self.game.world[
            "Eldergrove Tavern (The Golden Oak)"
        ]

        # Mock generate_npc_dialogue to see what is passed
        from unittest.mock import patch

        with patch("mud_game.generate_npc_dialogue") as mock_generate:
            mock_generate.return_value = "Mocked Response"

            # Test 1: Classical "talk Tavernkeeper Barnaby about quest"
            self.game.talk_to_npc("Tavernkeeper Barnaby about quest")
            mock_generate.assert_called_with(
                npc_name="Tavernkeeper Barnaby",
                persona=self.game.player.current_room.npcs[0].persona,
                topic="quest",
                player_name="TestHero",
                player_class="Warrior",
                player_level=1,
                player_hp=100,
                player_max_hp=100,
                party_members=[],
                inventory_items=[],
                quest_context="No major events.",
                dialogue_history=[],
                affinity=0,
                relationship_flags=[],
            )

            # Test 2: Shorthand "Tavernkeeper Barnaby quest" (no "about" keyword)
            self.game.talk_to_npc("Tavernkeeper Barnaby quest")
            mock_generate.assert_called_with(
                npc_name="Tavernkeeper Barnaby",
                persona=self.game.player.current_room.npcs[0].persona,
                topic="quest",
                player_name="TestHero",
                player_class="Warrior",
                player_level=1,
                player_hp=100,
                player_max_hp=100,
                party_members=[],
                inventory_items=[],
                quest_context="Forest Cleanse",
                dialogue_history=[
                    ("TestHero", "quest"),
                    ("Tavernkeeper Barnaby", "Mocked Response"),
                ],
                affinity=0,
                relationship_flags=[],
            )

            # Test 3: Shorthand with just partial name "Barnaby hello"
            self.game.talk_to_npc("Barnaby hello")
            mock_generate.assert_called_with(
                npc_name="Tavernkeeper Barnaby",
                persona=self.game.player.current_room.npcs[0].persona,
                topic="hello",
                player_name="TestHero",
                player_class="Warrior",
                player_level=1,
                player_hp=100,
                player_max_hp=100,
                party_members=[],
                inventory_items=[],
                quest_context="Forest Cleanse",
                dialogue_history=[
                    ("TestHero", "quest"),
                    ("Tavernkeeper Barnaby", "Mocked Response"),
                    ("TestHero", "quest"),
                    ("Tavernkeeper Barnaby", "Mocked Response"),
                ],
                affinity=0,
                relationship_flags=[],
            )


if __name__ == "__main__":
    unittest.main()
