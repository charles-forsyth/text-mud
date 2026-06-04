import os
import tempfile
import threading
import pygame
from typing import Optional
from google.cloud import texttospeech
from google.api_core import exceptions

# Voice mappings for characters
SPEAKER_VOICE_MAP = {
    "barnaby": "en-US-Chirp3-HD-Algieba",  # Jolly, stout dwarf (MALE)
    "thorin": "en-US-Chirp3-HD-Fenrir",  # Stern elf blacksmith (MALE)
    "althea": "en-US-Chirp3-HD-Autonoe",  # Gentle priestess (FEMALE)
    "elena": "en-US-Chirp3-HD-Gacrux",  # Sharp-eyed scale-mail elf (FEMALE)
    "lyra": "en-US-Chirp3-HD-Achernar",  # Sarcastic elven spell-weaver (FEMALE)
    "garrick": "en-US-Chirp3-HD-Charon",  # Battle-weary stoic warrior (MALE)
    "narrator": "en-US-Chirp3-HD-Enceladus",  # Deep, rich narrator (MALE)
}

# Default fallbacks
DEFAULT_FEMALE_VOICE = "en-US-Chirp3-HD-Zephyr"
DEFAULT_MALE_VOICE = "en-US-Chirp3-HD-Enceladus"


class TTSManager:
    """Manages text-to-speech synthesis and non-blocking playback for Aetheria MUD."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TTSManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.voice_enabled = False
        self._current_temp_file: Optional[str] = None
        self._play_thread: Optional[threading.Thread] = None
        self._initialized = True
        self._client: Optional[texttospeech.TextToSpeechClient] = None

    def initialize_client(self) -> bool:
        """Initializes the TTS client if not already done."""
        if self._client is not None:
            return True
        try:
            self._client = texttospeech.TextToSpeechClient()
            return True
        except Exception:
            # Silently fail initialization to preserve robust gameplay
            return False

    def select_voice(self, speaker_name: str) -> str:
        """Selects an appropriate voice for the speaker name."""
        name_lower = speaker_name.lower()
        # Direct lookup
        for key, voice in SPEAKER_VOICE_MAP.items():
            if key in name_lower:
                return voice

        # Heuristics based on name or title
        female_clues = [
            "priestess",
            "elena",
            "lady",
            "queen",
            "sister",
            "woman",
            "lyra",
            "she",
            "her",
            "female",
            "girl",
            "maid",
            "princess",
            "mage",
            "spell-weaver",
        ]
        male_clues = [
            "blacksmith",
            "tavernkeeper",
            "garrick",
            "king",
            "brother",
            "man",
            "lord",
            "sir",
            "he",
            "him",
            "male",
            "warrior",
            "soldier",
            "knight",
            "boy",
            "guy",
            "dwarf",
        ]

        if any(clue in name_lower for clue in female_clues):
            return DEFAULT_FEMALE_VOICE
        if any(clue in name_lower for clue in male_clues):
            return DEFAULT_MALE_VOICE

        # Alternating or default
        return DEFAULT_FEMALE_VOICE

    def stop_playback(self):
        """Stops any current audio playback and unloads the file."""
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass

    def speak(self, text: str, speaker_name: str):
        """Synthesizes and plays the text as speech in a non-blocking background thread."""
        if not self.voice_enabled:
            return

        # Clean text of any rich tags (e.g. [bold red] etc.) before synthesis
        clean_text = self._strip_rich_tags(text)
        if not clean_text:
            return

        # Run synthesis and playback in a separate thread to prevent game freezes
        thread = threading.Thread(
            target=self._synthesize_and_play,
            args=(clean_text, speaker_name),
            daemon=True,
        )
        thread.start()

    def _strip_rich_tags(self, text: str) -> str:
        """Strips Rich library tags like [bold red]...[/bold red] from text."""
        import re

        # Strip BBCode-like tags
        return re.sub(r"\[\/?[a-zA-Z0-9_\s#=,.-]+\]", "", text)

    def _synthesize_and_play(self, text: str, speaker_name: str):
        """Worker function that handles synthesis and playback."""
        if not self.initialize_client():
            return

        voice_name = self.select_voice(speaker_name)

        try:
            # 1. Synthesis
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice_params = texttospeech.VoiceSelectionParams(
                language_code="en-US", name=voice_name
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            response = self._client.synthesize_speech(  # type: ignore
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )

            # 2. Stop any active playback
            self.stop_playback()

            # 3. Write response to a new temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(response.audio_content)
                temp_path = temp_file.name

            # 4. Play using pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            # 5. Track file path to delete it later
            old_file = self._current_temp_file
            self._current_temp_file = temp_path

            # Attempt to delete the previous file
            if old_file and os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except Exception:
                    pass

        except exceptions.GoogleAPICallError:
            # Handle Google Cloud API errors gracefully
            pass
        except Exception:
            # Handle any other exceptions (pygame initialization or file locks) gracefully
            pass
