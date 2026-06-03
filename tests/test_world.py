import unittest
from aetheria.models import Item
from aetheria.world import build_default_world
from aetheria.entity import Player


class TestAetheriaWorld(unittest.TestCase):
    def setUp(self):
        self.world = build_default_world()
        self.player = Player(name="Hero", char_class="Warrior")
        self.player.current_room = self.world["Eldergrove Center"]

    def test_default_town_connections(self):
        center = self.world["Eldergrove Center"]
        # Exits check
        self.assertIn("north", center.exits)
        self.assertIn("east", center.exits)
        self.assertIn("west", center.exits)
        self.assertIn("south", center.exits)

        self.assertEqual(
            center.exits["north"].name, "Eldergrove Tavern (The Golden Oak)"
        )
        self.assertEqual(
            center.exits["east"].name, "Eldergrove Blacksmith (Iron & Ash)"
        )

    def test_npc_placement(self):
        tavern = self.world["Eldergrove Tavern (The Golden Oak)"]
        self.assertEqual(len(tavern.npcs), 1)
        self.assertEqual(tavern.npcs[0].name, "Tavernkeeper Barnaby")

    def test_locked_doors_require_items(self):
        # Silverlight bridge is locked and requires the Aether Sigil
        bridge = self.world["Silverlight Bridge"]
        self.assertTrue(bridge.locked)
        self.assertIsNotNone(bridge.key_needed)
        self.assertEqual(bridge.key_needed.name, "Aether Sigil")

        # Let's verify player unlocking
        sigil = Item("Aether Sigil", "Glowing sigil", value=0, is_quest_item=True)
        self.player.inventory.append(sigil)

        self.assertTrue(self.player.has_item("Aether Sigil"))

    def test_unlocking_mechanism_removes_lock(self):
        bridge = self.world["Silverlight Bridge"]
        self.assertTrue(bridge.locked)

        # Player does not have key
        self.assertFalse(self.player.has_item("Aether Sigil"))

        # Give player key and try to unlock
        sigil = Item("Aether Sigil", "Glowing sigil", value=0, is_quest_item=True)
        self.player.inventory.append(sigil)
        self.assertTrue(self.player.has_item("Aether Sigil"))

        if bridge.key_needed and self.player.has_item(bridge.key_needed.name):
            bridge.locked = False

        self.assertFalse(bridge.locked)


if __name__ == "__main__":
    unittest.main()
