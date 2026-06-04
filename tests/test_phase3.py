import unittest

from aetheria.entity import Player, Companion, Enemy
from aetheria.world import Room
from aetheria.weather import WeatherEngine, EnvironmentalHazard
from aetheria.navigation import LivingWorldClock, ScheduledNPC, find_shortest_path
from aetheria.loot import generate_random_loot, LootGenerator
from aetheria.ailments import StatusEffect, resolve_elemental_combos
from aetheria.models import Equipment, EquipmentSlot


class TestAetheriaPhase3(unittest.TestCase):
    def setUp(self):
        # Build a small dummy room grid for BFS navigation and hazard testing
        self.room_a = Room("Room A", "A quiet starting room.")
        self.room_b = Room("Room B", "A windy corridor.")
        self.room_c = Room("Room C", "A scorching lava room.")

        self.room_a.add_exit("north", self.room_b)
        self.room_b.add_exit("south", self.room_a)
        self.room_b.add_exit("east", self.room_c)
        self.room_c.add_exit("west", self.room_b)

        # Build standard testing player and entities
        self.player = Player(name="TestHero", char_class="Warrior", gold=100)
        self.player.current_room = self.room_a

        self.enemy = Enemy(
            name="Testing Goblin",
            description="A green pest.",
            hp=50,
            max_hp=50,
            attack=8,
            defense=3,
            level=2,
            xp_value=25,
            gold_value=12,
        )

    def test_weather_engine_and_hazards(self):
        # 1. Weather Engine Cycles
        engine = WeatherEngine()
        self.assertEqual(engine.current_state.name, "Clear Skies")
        self.assertTrue(engine.turns_remaining > 0)

        # Force weather change
        engine.turns_remaining = 1
        announcement = engine.tick()
        self.assertIsNotNone(announcement)
        self.assertTrue(engine.turns_remaining >= 12)

        # 2. Environmental Hazards
        hazard = EnvironmentalHazard(
            hazard_type="fire",
            damage_per_tick=15,
            description="Lava bursts out!",
            mitigation_item="Flame Ring",
        )

        # Hazard tick without mitigation
        self.player.hp = 100
        self.player._max_hp = 100
        log_no_mit = hazard.resolve_tick(self.player)
        self.assertIn("lava bursts out", log_no_mit.lower())
        self.assertEqual(self.player.hp, 85)

        # Hazard tick with mitigation
        # Add the mitigation item to the player's inventory
        ring = Equipment(
            name="Flame Ring",
            description="Mitigates fire damage.",
            slot=EquipmentSlot.ACCESSORY,
            value=100,
        )
        self.player.inventory.append(ring)
        log_with_mit = hazard.resolve_tick(self.player)
        self.assertIn("flame ring protects you", log_with_mit.lower())
        self.assertEqual(self.player.hp, 85)  # Health should not change

    def test_navigation_and_npc_schedules(self):
        # 1. Shortest Path (BFS)
        path = find_shortest_path(self.room_a, self.room_c)
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 3)
        self.assertEqual(path[0].name, "Room A")
        self.assertEqual(path[1].name, "Room B")
        self.assertEqual(path[2].name, "Room C")

        # 2. Living World Clock
        clock = LivingWorldClock()
        self.assertEqual(clock.current_time, "Day")
        # Tick movement 8 times to advance segment
        for _ in range(7):
            self.assertIsNone(clock.tick_movement())
        announcement = clock.tick_movement()
        self.assertIsNotNone(announcement)
        self.assertEqual(clock.current_time, "Dusk")

        # 3. Scheduled NPC Roaming
        npc = Companion(
            name="Merchant John", char_class="Warrior", personality="Shrewd"
        )
        self.room_a.npcs.append(npc)
        npc.current_room = self.room_a

        schedule = {
            "Dawn": "Room A",
            "Day": "Room C",
            "Dusk": "Room B",
            "Night": "Room A",
        }
        scheduled_npc = ScheduledNPC(npc, schedule)

        world_map = {
            "Room A": self.room_a,
            "Room B": self.room_b,
            "Room C": self.room_c,
        }

        # John moves from Room A -> Room B (step 1 towards Room C during 'Day')
        move_log = scheduled_npc.update_location("Day", world_map)
        self.assertIsNotNone(move_log)
        self.assertIn("Merchant John", move_log)
        self.assertNotIn(npc, self.room_a.npcs)
        self.assertIn(npc, self.room_b.npcs)
        self.assertEqual(npc.current_room.name, "Room B")

        # Next step: John moves from Room B -> Room C (step 2)
        move_log2 = scheduled_npc.update_location("Day", world_map)
        self.assertIsNotNone(move_log2)
        self.assertIn("Merchant John", move_log2)
        self.assertNotIn(npc, self.room_b.npcs)
        self.assertIn(npc, self.room_c.npcs)
        self.assertEqual(npc.current_room.name, "Room C")

        # Already at destination: John should not move
        move_log3 = scheduled_npc.update_location("Day", world_map)
        self.assertIsNone(move_log3)

    def test_talent_trees_allocation_and_multipliers(self):
        tree = self.player.talent_tree
        self.assertEqual(tree.class_name, "Warrior")

        # Initial checks
        self.player.skill_points = 0
        self.assertFalse(tree.can_allocate("iron_skin", self.player.skill_points))

        # Add points (needs 4 to max iron_skin and allocate shield_slam)
        self.player.skill_points = 4
        self.assertTrue(tree.can_allocate("iron_skin", self.player.skill_points))

        # Check prerequisite lock
        self.assertFalse(tree.can_allocate("shield_slam", self.player.skill_points))

        # Allocate Iron Skin (Rank 1)
        success = tree.allocate("iron_skin", self.player)
        self.assertTrue(success)
        self.assertEqual(self.player.skill_points, 3)
        self.assertEqual(tree.nodes["iron_skin"].current_rank, 1)

        # Prerequisites still not met (needs rank 3 max)
        self.assertFalse(tree.can_allocate("shield_slam", self.player.skill_points))

        # Allocate Iron Skin (Rank 2)
        success = tree.allocate("iron_skin", self.player)
        self.assertTrue(success)

        # Allocate Iron Skin (Rank 3)
        success = tree.allocate("iron_skin", self.player)
        self.assertTrue(success)
        self.assertEqual(tree.nodes["iron_skin"].current_rank, 3)

        # Check cumulative defense modifier (3 * 10% = 30%)
        def_multiplier = tree.get_cumulative_multiplier("defense_multiplier")
        self.assertAlmostEqual(def_multiplier, 0.30)

        # Verify dynamic player attack/defense multiplier impact
        base_def = self.player._defense
        expected_def = int(base_def * 1.30)
        self.assertEqual(self.player.defense, expected_def)

        # Prerequisites met: can allocate Shield Slam
        self.assertTrue(tree.can_allocate("shield_slam", self.player.skill_points))

    def test_procedural_loot_generation(self):
        # Generate random loot for area level 5
        loot_item = generate_random_loot(level=5)
        self.assertIsNotNone(loot_item)
        self.assertIn(
            loot_item.slot,
            [
                EquipmentSlot.WEAPON,
                EquipmentSlot.BODY_ARMOR,
                EquipmentSlot.SHIELD,
                EquipmentSlot.ACCESSORY,
            ],
        )

        # Rarity grades must match valid markup styles
        self.assertTrue(
            any(
                word in loot_item.name
                for word in ["white", "royal_blue", "violet", "gold", "bold"]
            )
        )

        # Check stats multipliers applied based on affixes
        base_sword = Equipment(
            name="Iron Broadsword",
            description="A blunt iron sword.",
            slot=EquipmentSlot.WEAPON,
            value=30,
            attack_bonus=10,
        )

        rare_sword = LootGenerator.generate_loot(base_sword, level=4)
        self.assertTrue(rare_sword.value > base_sword.value)
        self.assertTrue(rare_sword.attack_bonus >= base_sword.attack_bonus)

    def test_status_ailments_and_elemental_combos(self):
        # 1. Ailment container state ticks
        self.assertEqual(len(self.enemy.ailments.active_effects), 0)

        # Apply Burn
        burn_effect = StatusEffect("Burn", duration=3, dot_damage=10)
        apply_msg = self.enemy.ailments.apply_effect(burn_effect)
        self.assertIn("burn", apply_msg.lower())
        self.assertEqual(len(self.enemy.ailments.active_effects), 1)

        # Ticking down Burn (deals dot_damage)
        self.enemy.hp = 50
        tick_logs = self.enemy.ailments.resolve_ticks()
        self.assertEqual(len(tick_logs), 1)
        self.assertIn("burn", tick_logs[0].lower())
        self.assertEqual(self.enemy.hp, 40)
        self.assertEqual(self.enemy.ailments.active_effects["Burn"].duration, 2)

        # 2. Elemental Turn Combos
        # Setup 'Wet' status on the enemy
        self.enemy.ailments.active_effects.clear()
        self.enemy.ailments.apply_effect(StatusEffect("Wet", duration=3))

        # Cast Lightning Spell on Wet enemy -> Conductive Overload combo!
        combo_res = resolve_elemental_combos(self.player, self.enemy, "lightning")
        self.assertIsNotNone(combo_res)
        bonus_dmg, combo_announcement = combo_res
        self.assertEqual(bonus_dmg, 30)  # Conductive Overload base damage is 30
        self.assertIn("conductive overload", combo_announcement.lower())

        # Combo should clear Wet negative status
        self.assertEqual(len(self.enemy.ailments.active_effects), 0)

        # Setup 'Frozen' status on the enemy
        self.enemy.ailments.apply_effect(StatusEffect("Frozen", duration=2))
        # Deliver a physical attack to Frozen enemy -> Shatter combo!
        combo_res_shatter = resolve_elemental_combos(
            self.player, self.enemy, "physical"
        )
        self.assertIsNotNone(combo_res_shatter)
        bonus_dmg_shatter, combo_announcement_shatter = combo_res_shatter
        self.assertEqual(bonus_dmg_shatter, 35)  # Shatter base damage is 35
        self.assertIn("shatter", combo_announcement_shatter.lower())
        self.assertEqual(len(self.enemy.ailments.active_effects), 0)


if __name__ == "__main__":
    unittest.main()
