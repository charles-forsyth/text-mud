import os

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    "AIzaSyDgnBTB9UI-qbtRVzuJIQiwV0g_wsin8iQ",  # Robust user fallback key
)
DEFAULT_AI_MODEL = "gemini-3.1-pro"  # User preferred model

# Save File Path
SAVE_FILE_NAME = "savegame_aetheria.json"
SAVE_SCHEMA_VERSION = 2


# Gameplay Settings
MAX_PARTY_SIZE = 4
BASE_RESPAWN_GOLD_PENALTY_PCT = 0.10  # 10% gold loss on death
