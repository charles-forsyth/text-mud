import unittest
from unittest.mock import MagicMock, patch
from aetheria.tts import TTSManager, DEFAULT_FEMALE_VOICE, DEFAULT_MALE_VOICE


class TestTTSManager(unittest.TestCase):
    def setUp(self):
        # Reset the Singleton instance for testing purposes
        TTSManager._instance = None
        self.tts = TTSManager()

    def test_singleton_behavior(self):
        another_tts = TTSManager()
        self.assertIs(self.tts, another_tts)

    def test_voice_toggling(self):
        self.assertFalse(self.tts.voice_enabled)
        self.tts.voice_enabled = True
        self.assertTrue(self.tts.voice_enabled)

    def test_strip_rich_tags(self):
        text_with_tags = "[bold red]Hello[/bold red] [dim]World[/dim]!"
        clean_text = self.tts._strip_rich_tags(text_with_tags)
        self.assertEqual(clean_text, "Hello World!")

    def test_select_voice_exact_and_heuristics(self):
        # Exact speaker name lookup (case-insensitive)
        self.assertEqual(
            self.tts.select_voice("Tavernkeeper Barnaby"), "en-US-Chirp3-HD-Algieba"
        )
        self.assertEqual(self.tts.select_voice("Thorin"), "en-US-Chirp3-HD-Fenrir")
        self.assertEqual(self.tts.select_voice("Althea"), "en-US-Chirp3-HD-Autonoe")
        self.assertEqual(self.tts.select_voice("Elena"), "en-US-Chirp3-HD-Gacrux")
        self.assertEqual(self.tts.select_voice("Lyra"), "en-US-Chirp3-HD-Achernar")
        self.assertEqual(self.tts.select_voice("Garrick"), "en-US-Chirp3-HD-Charon")

        # Heuristic lookup
        self.assertEqual(
            self.tts.select_voice("A proud priestess"), DEFAULT_FEMALE_VOICE
        )
        self.assertEqual(self.tts.select_voice("Some male warrior"), DEFAULT_MALE_VOICE)
        self.assertEqual(
            self.tts.select_voice("Unknown generic person"), DEFAULT_FEMALE_VOICE
        )

    @patch("aetheria.tts.texttospeech.TextToSpeechClient")
    @patch("aetheria.tts.pygame.mixer")
    def test_synthesize_and_play_flow(self, mock_pygame_mixer, mock_tts_client_class):
        # Mock Google Cloud TTS response
        mock_client = MagicMock()
        mock_tts_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.audio_content = b"fake_mp3_data"
        mock_client.synthesize_speech.return_value = mock_response

        # Mock pygame.mixer behavior
        mock_pygame_mixer.get_init.return_value = True

        self.tts._client = mock_client
        self.tts.voice_enabled = True

        # Speak should run in a thread, so we'll test the helper worker directly for predictability
        with (
            patch("tempfile.NamedTemporaryFile") as mock_temp_file,
            patch("os.path.exists") as mock_exists,
            patch("os.remove") as mock_remove,
        ):
            # Setup temp file mocking
            mock_temp_instance = MagicMock()
            mock_temp_instance.name = "fake_temp_path.mp3"
            mock_temp_file.return_value.__enter__.return_value = mock_temp_instance

            import os

            original_exists = os.path.exists

            def selective_exists(path):
                if path == "previous_temp_file.mp3":
                    return True
                if "fake_temp_path.mp3" in str(path):
                    return True
                if ".tts_cache" in str(path):
                    return False
                return original_exists(path)

            mock_exists.side_effect = selective_exists

            # Set previous file to test deletion cleanup
            self.tts._current_temp_file = "previous_temp_file.mp3"

            # Trigger synthesis and playback worker directly
            self.tts._synthesize_and_play("Hello there", "Narrator")

            # Verify synthesizer client was called with correct parameters
            mock_client.synthesize_speech.assert_called_once()
            _, kwargs = mock_client.synthesize_speech.call_args
            self.assertEqual(
                kwargs["voice"].name, "en-US-Chirp3-HD-Enceladus"
            )  # Narrator voice

            # Verify pygame loaded and played the file
            mock_pygame_mixer.music.load.assert_called_once_with("fake_temp_path.mp3")
            mock_pygame_mixer.music.play.assert_called_once()

            # Verify previous file was cleaned up and deleted
            mock_remove.assert_called_once_with("previous_temp_file.mp3")


if __name__ == "__main__":
    unittest.main()
