import os
import tempfile
import threading
import queue
import hashlib
import time
import pygame
from typing import Optional, Any
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


class CircuitBreaker:
    """Protects against persistent slow/offline network calls by tripping after consecutive failures.
    Supports automatic recovery via dynamic state transitions."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self._is_open = False
        self.last_state_change = 0.0

    @property
    def is_open(self) -> bool:
        if self._is_open:
            if time.time() - self.last_state_change >= self.cooldown_seconds:
                # Dynamically enters a half-open state by allowing a canary call
                return False
            return True
        return False

    @is_open.setter
    def is_open(self, value: bool):
        self._is_open = value
        self.last_state_change = time.time()

    def record_success(self):
        self.failure_count = 0
        self._is_open = False
        self.last_state_change = time.time()

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self._is_open = True
            self.last_state_change = time.time()


class TTSManager:
    """Manages thread-safe text-to-speech synthesis and cached non-blocking playback."""

    _instance: Optional["TTSManager"] = None
    _initialized: bool = False
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "TTSManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TTSManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.voice_enabled = False
        self._current_temp_file: Optional[str] = None
        self._initialized = True
        self._client: Optional[texttospeech.TextToSpeechClient] = None

        # Temp files tracking for process-exit deletion
        import atexit

        self._temp_files_to_clean: list[str] = []
        atexit.register(self.cleanup_temp_files)

        # Queue-based asynchronous worker system
        self._queue: queue.Queue = queue.Queue()
        self._latest_request_id = 0
        self._cache_dir = ".tts_cache"
        self._tts_breaker = CircuitBreaker()
        self._worker_thread: Optional[threading.Thread] = None

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

        # Generate a new request_id under lock
        with self._lock:
            self._latest_request_id += 1
            request_id = self._latest_request_id

        # Push the task to the queue
        self._queue.put(
            {
                "text": clean_text,
                "speaker_name": speaker_name,
                "request_id": request_id,
            }
        )

        # Ensure background worker is active
        self._start_worker_if_needed()

    def _start_worker_if_needed(self):
        """Lazily spawns the background worker thread."""
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    daemon=True,
                )
                self._worker_thread.start()

    def _worker_loop(self):
        """Background daemon processing speech tasks from the queue sequentially."""
        while True:
            try:
                task = self._queue.get()
                if task is None:
                    break

                request_id = task["request_id"]
                text = task["text"]
                speaker_name = task["speaker_name"]

                # Quick pre-check: skip task if a newer speech action has been requested
                with self._lock:
                    if request_id != self._latest_request_id:
                        self._queue.task_done()
                        continue

                self._synthesize_and_play(text, speaker_name, request_id)
                self._queue.task_done()
            except Exception:
                pass

    def _strip_rich_tags(self, text: str) -> str:
        """Strips Rich library tags like [bold red]...[/bold red] from text."""
        import re

        # Strip BBCode-like tags
        return re.sub(r"\[\/?[a-zA-Z0-9_\s#=,.-]+\]", "", text)

    def _synthesize_and_play(
        self, text: str, speaker_name: str, request_id: Optional[int] = None
    ):
        """Synthesizes speech (using local disk cache if available) and plays it back safely."""
        # Check if obsolete before doing work
        if request_id is not None:
            with self._lock:
                if request_id != self._latest_request_id:
                    return

        voice_name = self.select_voice(speaker_name)

        # 1. Attempt to resolve audio from disk cache
        cache_path = None
        audio_content = None
        if self._cache_dir:
            try:
                os.makedirs(self._cache_dir, exist_ok=True)
                h = hashlib.sha256(f"{voice_name}:{text}".encode("utf-8")).hexdigest()
                cache_path = os.path.join(self._cache_dir, f"{h}.mp3")
                if os.path.exists(cache_path):
                    with open(cache_path, "rb") as f:
                        audio_content = f.read()
            except Exception:
                pass

        # 2. Synthesize via API if not in cache and breaker is closed
        if not audio_content:
            if self._tts_breaker.is_open:
                return

            if not self.initialize_client():
                self._tts_breaker.record_failure()
                return

            try:
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
                audio_content = response.audio_content
                self._tts_breaker.record_success()

                # Save synthesized audio to disk cache
                if cache_path:
                    try:
                        with open(cache_path, "wb") as f:
                            f.write(audio_content)
                    except Exception:
                        pass
            except exceptions.GoogleAPICallError as e:
                self._tts_breaker.record_failure()
                # Fast trip breaker on authentication or permission issues
                if hasattr(e, "code") and e.code in (400, 403):
                    self._tts_breaker.is_open = True
                return
            except Exception:
                self._tts_breaker.record_failure()
                return

        # 3. Post-synthesis obsolete check
        if request_id is not None:
            with self._lock:
                if request_id != self._latest_request_id:
                    return

        # 4. Safe single-threaded Pygame playback
        try:
            self.stop_playback()

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_content)
                temp_path = temp_file.name

            # Track temp file for session cleanup
            self._temp_files_to_clean.append(temp_path)

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            old_file = self._current_temp_file
            self._current_temp_file = temp_path

            if old_file and os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except Exception:
                    pass
        except Exception:
            pass

    def cleanup_temp_files(self):
        """Purges all temporary audio files generated during this game session."""
        self.stop_playback()
        for filepath in self._temp_files_to_clean:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        self._temp_files_to_clean.clear()
