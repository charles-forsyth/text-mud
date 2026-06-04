import unittest
import time
import threading
from unittest.mock import patch

from aetheria.ai_engine import CircuitBreaker as AICircuitBreaker, ThreadSafeCache
from aetheria.tts import CircuitBreaker as TTSCircuitBreaker, TTSManager
from aetheria.world import Room
from aetheria.entity import Player, Companion


class TestCodeReviewRecommendations(unittest.TestCase):
    def test_circuit_breaker_timed_cooldown_recovery(self):
        """Recommendation 1: Test dynamic circuit breaker transitions to half-open state after cooldown."""
        for breaker_cls in [AICircuitBreaker, TTSCircuitBreaker]:
            # Use a tiny cooldown of 0.2 seconds for quick test execution
            breaker = breaker_cls(failure_threshold=2, cooldown_seconds=0.2)

            self.assertFalse(breaker.is_open)

            # Record failures to trip the circuit breaker
            breaker.record_failure()
            self.assertFalse(breaker.is_open)

            breaker.record_failure()
            self.assertTrue(breaker.is_open)

            # Immediately checking should still be open
            self.assertTrue(breaker.is_open)

            # Wait for cooldown to expire
            time.sleep(0.25)

            # Checking is_open now should dynamically return False (Half-Open state)
            self.assertFalse(breaker.is_open)

            # Success on the canary call resets the breaker completely
            breaker.record_success()
            self.assertFalse(breaker.is_open)
            self.assertEqual(breaker.failure_count, 0)

    def test_thread_safe_cache_concurrency_and_eviction(self):
        """Recommendation 2: Test that ThreadSafeCache performs eviction correctly and supports concurrent reads/writes."""
        cache = ThreadSafeCache(max_size=5)

        # 1. Test basic eviction
        for i in range(7):
            cache[f"key_{i}"] = f"val_{i}"

        # Size should be capped at max_size (5)
        self.assertEqual(len(cache), 5)

        # The oldest elements (key_0 and key_1) should have been evicted
        self.assertNotIn("key_0", cache)
        self.assertNotIn("key_1", cache)
        self.assertIn("key_2", cache)
        self.assertIn("key_6", cache)

        # 2. Test thread-safety with concurrent access
        errors = []

        def worker(worker_id: int):
            try:
                for idx in range(50):
                    # Write
                    cache[f"thread_{worker_id}_key_{idx}"] = f"value_{idx}"
                    # Read
                    _ = cache[f"thread_{worker_id}_key_{idx}"]
                    # Containment
                    _ = f"thread_{worker_id}_key_{idx}" in cache
                    # Iteration (test list copying under the hood)
                    for _ in cache:
                        pass
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(
            len(errors),
            0,
            f"ThreadSafeCache threw exceptions during concurrent load: {errors}",
        )

    def test_dynamic_exit_serialization_and_deserialization(self):
        """Recommendation 4: Test that dynamic exits map serialization/deserialization is correct."""
        room1 = Room("Antechamber", "A dark stone entry room.")
        room2 = Room("Sanctum", "A glowing magical sanctuary.")

        room1.add_exit("north", room2)
        room2.add_exit("south", room1)

        # Serialize
        r1_dict = room1.to_dict()
        r2_dict = room2.to_dict()

        # Check exits are serialized properly with target room names
        self.assertEqual(r1_dict["exits"], {"north": "Sanctum"})
        self.assertEqual(r2_dict["exits"], {"south": "Antechamber"})

        # Deserialize into new instances (without exits stitched yet)
        loaded_r1 = Room.from_dict(r1_dict)
        loaded_r2 = Room.from_dict(r2_dict)

        self.assertEqual(loaded_r1._saved_exits_map, {"north": "Sanctum"})
        self.assertEqual(loaded_r2._saved_exits_map, {"south": "Antechamber"})

        # Mock the entire world and save system's load stitching logic
        loaded_world = {"Antechamber": loaded_r1, "Sanctum": loaded_r2}

        # Stitch them manually mirroring load_game's exit map stitcher
        for rname, room in loaded_world.items():
            saved_exits = getattr(room, "_saved_exits_map", {})
            for direction, target_name in saved_exits.items():
                if target_name in loaded_world:
                    room.add_exit(direction, loaded_world[target_name])

        # Verify exits are restored properly
        self.assertIn("north", loaded_r1.exits)
        self.assertEqual(loaded_r1.exits["north"], loaded_r2)
        self.assertIn("south", loaded_r2.exits)
        self.assertEqual(loaded_r2.exits["south"], loaded_r1)

    def test_companion_recruitment_scaling(self):
        """Recommendation 3: Test companion recruitment level scaling to match player level."""
        # Mock MUD game instance structure or use companion level-up directly
        player = Player(name="Champion", char_class="Warrior")
        player.level = 5

        companion = Companion(
            name="Garrick", char_class="Rogue", personality="Sarcastic"
        )
        self.assertEqual(companion.level, 1)

        # Simulate recruitment level-scaling loop
        scaled_up_levels = 0
        while companion.level < player.level:
            companion.level_up()
            scaled_up_levels += 1

        self.assertEqual(companion.level, 5)
        self.assertEqual(scaled_up_levels, 4)

    def test_tts_cleanup_temp_files(self):
        """Recommendation 5: Test that TTSManager tracks and purges temporary files cleanly."""
        TTSManager._instance = None
        tts = TTSManager()

        # Mock temporary files that exist on the filesystem
        fake_files = ["/tmp/fake_tts_1.mp3", "/tmp/fake_tts_2.mp3"]
        tts._temp_files_to_clean.extend(fake_files)

        with (
            patch("os.path.exists") as mock_exists,
            patch("os.remove") as mock_remove,
            patch.object(tts, "stop_playback") as mock_stop,
        ):
            mock_exists.side_effect = lambda path: path in fake_files

            # Call clean-up
            tts.cleanup_temp_files()

            # Ensure playback is stopped first
            mock_stop.assert_called_once()

            # Verify that os.remove was called for both paths
            self.assertEqual(mock_remove.call_count, 2)
            mock_remove.assert_any_call("/tmp/fake_tts_1.mp3")
            mock_remove.assert_any_call("/tmp/fake_tts_2.mp3")

            # Check that tracking list has been cleared
            self.assertEqual(len(tts._temp_files_to_clean), 0)


if __name__ == "__main__":
    unittest.main()
