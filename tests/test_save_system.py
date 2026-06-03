import unittest
import os
from aetheria.config import SAVE_FILE_NAME
from aetheria.entity import Player, Companion
from aetheria.world import build_default_world
from aetheria.quests import get_default_quests
from aetheria.save_system import save_game, load_game


class TestAetheriaSaveSystem(unittest.TestCase):
    def setUp(self):
        self.world = build_default_world()
        self.quests = get_default_quests()
        self.player = Player(name="SaveHero", char_class="Mage", gold=250)
        self.player.current_room = self.world["Eldergrove Center"]
        self.companion = Companion(
            name="Lyra", char_class="Mage", personality="Dry wit"
        )

        # Clean up existing save file if any
        if os.path.exists(SAVE_FILE_NAME):
            os.remove(SAVE_FILE_NAME)

    def tearDown(self):
        # Clean up save file
        if os.path.exists(SAVE_FILE_NAME):
            os.remove(SAVE_FILE_NAME)

    def test_save_and_load_transactional_integrity(self):
        # 1. Modify initial states
        self.player.gold = 500
        self.player.gain_xp(120)  # Should level up to Level 2

        # Lock Eldergrove Center (for testing, normally unlocked)
        self.world["Eldergrove Center"].locked = True

        # Activate a quest
        self.player.active_quests.append("q_eldergrove_goblins")
        self.quests["q_eldergrove_goblins"].status = "active"
        self.quests["q_eldergrove_goblins"].count_current = 1

        # 2. Execute Save
        success = save_game(
            player=self.player,
            party=[self.companion],
            world=self.world,
            quests=self.quests,
            current_room_name="Eldergrove Center",
            tavern_companions=[],
        )
        self.assertTrue(success)
        self.assertTrue(os.path.exists(SAVE_FILE_NAME))

        # 3. Load back using pure transaction deserializer
        default_w = build_default_world()
        default_q = get_default_quests()

        (
            p_loaded,
            party_loaded,
            world_loaded,
            quests_loaded,
            room_name_loaded,
            tav_loaded,
        ) = load_game(default_w, default_q)

        # 4. Verify identical states
        self.assertEqual(p_loaded.name, "SaveHero")
        self.assertEqual(p_loaded.gold, 500)
        self.assertEqual(p_loaded.level, 2)
        self.assertEqual(room_name_loaded, "Eldergrove Center")

        # Verify party companion state
        self.assertEqual(len(party_loaded), 1)
        self.assertEqual(party_loaded[0].name, "Lyra")
        self.assertEqual(party_loaded[0].char_class, "Mage")

        # Verify quest log progress
        self.assertIn("q_eldergrove_goblins", p_loaded.active_quests)
        self.assertEqual(quests_loaded["q_eldergrove_goblins"].status, "active")
        self.assertEqual(quests_loaded["q_eldergrove_goblins"].count_current, 1)

        # Verify world room properties
        self.assertTrue(world_loaded["Eldergrove Center"].locked)


if __name__ == "__main__":
    unittest.main()
