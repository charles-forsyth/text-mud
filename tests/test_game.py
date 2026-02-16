import unittest
import sys
import os

# Add parent directory to sys.path to import mud_game
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mud_game import Game


class TestMUD(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.setup_world()

    def test_room_connections(self):
        # Entrance Hall exits
        entrance = self.game.world["Entrance Hall"]
        self.assertIn("north", entrance.exits)
        self.assertIn("east", entrance.exits)
        self.assertEqual(entrance.exits["north"].name, "Great Hall")
        self.assertEqual(entrance.exits["east"].name, "Kitchen")

        # Great Hall exits
        great_hall = self.game.world["Great Hall"]
        self.assertNotIn("east", great_hall.exits)
        self.assertEqual(great_hall.exits["west"].name, "Dungeon")

        # Kitchen exits
        kitchen = self.game.world["Kitchen"]
        self.assertIn("west", kitchen.exits)
        self.assertEqual(kitchen.exits["west"].name, "Entrance Hall")

    def test_take_item(self):
        # Move to Great Hall where Golden Key is
        self.game.player.move("north")
        great_hall = self.game.player.current_room

        # Verify Key is there
        key_present = any(item.name == "Golden Key" for item in great_hall.items)
        self.assertTrue(key_present)

        # Take the key
        self.game.player.take("Golden Key")

        # Verify Key is in inventory
        self.assertTrue(self.game.player.has_item("Golden Key"))
        # Verify Key is not in room
        self.assertFalse(any(item.name == "Golden Key" for item in great_hall.items))

    def test_health_system(self):
        self.assertEqual(self.game.player.hp, 100)

        self.game.player.take_damage(30)
        self.assertEqual(self.game.player.hp, 70)

        self.game.player.heal(20)
        self.assertEqual(self.game.player.hp, 90)

        self.game.player.heal(50)  # Should cap at 100
        self.assertEqual(self.game.player.hp, 100)

    def test_goblin_encounter(self):
        # Move to Great Hall then Dungeon
        self.game.player.move("north")

        # Mocking input for process_command if needed, but we can call move directly
        # However, the attack logic is in process_command.
        # So we should use process_command to trigger the attack.

        # Move to Dungeon
        self.game.process_command("go west")  # From Great Hall to Dungeon

        # Player is now in Dungeon with Goblin.
        # The attack happens AFTER the command is processed in the loop.
        # But wait, in my implementation:
        # if verb == "go": player.move()
        # ...
        # if player.current_room.enemy: enemy.attack()

        # So calling process_command('go west') should trigger the move AND the attack.
        dungeon = self.game.world["Dungeon"]
        self.assertEqual(self.game.player.current_room, dungeon)
        self.assertIsNotNone(dungeon.enemy)
        self.assertEqual(dungeon.enemy.name, "Goblin")

        # Check HP (Start 100 - 10 damage)
        self.assertEqual(self.game.player.hp, 90)

    def test_potion_usage(self):
        # Potion is in Kitchen (East of Entrance Hall)
        self.game.player.take_damage(50)  # HP = 50

        # Entrance Hall -> Kitchen
        self.game.process_command("go east")  # To Kitchen

        # Verify potion is there
        kitchen = self.game.world["Kitchen"]
        potion_present = any(item.name == "Health Potion" for item in kitchen.items)
        self.assertTrue(potion_present)

        # Take potion
        self.game.process_command("take health potion")
        self.assertTrue(self.game.player.has_item("Health Potion"))

        # Use potion
        self.game.process_command("use health potion")

        # HP should be 50 + 20 = 70
        self.assertEqual(self.game.player.hp, 70)

        # Potion should be gone from inventory
        self.assertFalse(self.game.player.has_item("Health Potion"))

    def test_win_condition_survival(self):
        # Get Key
        self.game.process_command("go north")  # Great Hall
        self.game.process_command("take golden key")

        # Go to Front Gate
        self.game.process_command("go south")  # Entrance Hall
        self.game.process_command(
            "go south"
        )  # Front Gate (Locked -> Unlocked with Key)

        # Wait, my logic for Locked door:
        # if next_room.locked:
        #   if has_key: unlock, enter.
        #   else: fail.

        # So 'go south' from Entrance Hall should move to Front Gate if we have key.
        self.assertEqual(self.game.player.current_room.name, "Front Gate")

        # Win condition checks hp > 0.
        # Since we haven't taken fatal damage, is_running should be False (Game Over - Win)
        # process_command handles the win check.

        # But wait, `is_running` is on the Game instance.
        self.assertFalse(self.game.is_running)

    def test_death(self):
        self.game.player.hp = 10
        # Go to Dungeon to die
        self.game.process_command("go north")
        self.game.process_command(
            "go west"
        )  # Dungeon -> Goblin attacks -> 10 dmg -> 0 HP

        self.assertEqual(self.game.player.hp, 0)
        self.assertFalse(self.game.is_running)


if __name__ == "__main__":
    unittest.main()
