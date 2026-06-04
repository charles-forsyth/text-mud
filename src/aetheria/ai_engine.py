import google.generativeai as genai
import time
import threading
from typing import Optional, List, Tuple
from aetheria.config import GEMINI_API_KEY, DEFAULT_AI_MODEL

# Configure the Gemini API client
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        _api_ready = True
    else:
        _api_ready = False
except Exception:
    _api_ready = False


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


_gemini_breaker = CircuitBreaker()


class ThreadSafeCache:
    """A thread-safe dictionary cache wrapper that handles eviction thread-safely."""

    def __init__(self, max_size: int = 100):
        self._cache: dict = {}
        self._lock = threading.RLock()
        self.max_size = max_size

    def __contains__(self, key) -> bool:
        with self._lock:
            return key in self._cache

    def __getitem__(self, key):
        with self._lock:
            return self._cache[key]

    def __setitem__(self, key, value):
        with self._lock:
            if len(self._cache) >= self.max_size and key not in self._cache:
                # Evict oldest entry (insertion ordered dict in 3.7+)
                first_key = next(iter(self._cache))
                self._cache.pop(first_key, None)
            self._cache[key] = value

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def __iter__(self):
        with self._lock:
            # Return list of keys to prevent dictionary mutation errors during iteration
            return iter(list(self._cache.keys()))

    def __delitem__(self, key):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()


# In-memory cache for generated room descriptions
_ROOM_DESC_CACHE = ThreadSafeCache()


def call_gemini(prompt: str, temperature: float = 0.7) -> str:
    """Helper to safely make calls to Google Gemini with a procedural fallback."""
    if not _api_ready or _gemini_breaker.is_open:
        return ""
    try:
        model = genai.GenerativeModel(DEFAULT_AI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=300,
            ),
        )
        _gemini_breaker.record_success()
        return response.text.strip()
    except Exception as e:
        _gemini_breaker.record_failure()
        # Fast trip breaker on authorization/invalid key errors
        err_msg = str(e).lower()
        if any(
            term in err_msg
            for term in ["api_key", "invalid", "permission", "400", "403"]
        ):
            _gemini_breaker.is_open = True
        return ""


def generate_npc_dialogue(
    npc_name: str,
    persona: str,
    topic: str,
    player_name: str,
    quest_context: str,
    player_class: str = "Adventurer",
    player_level: int = 1,
    player_hp: int = 100,
    player_max_hp: int = 100,
    party_members: Optional[List[Tuple[str, str]]] = None,
    inventory_items: Optional[List[str]] = None,
    dialogue_history: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """Generates context-aware, in-character NPC responses using Gemini Pro with full awareness of companions, inventory, and history."""

    history_str = ""
    if dialogue_history:
        history_str = "\nRecent Conversation History:\n" + "\n".join(
            f"{speaker}: {text}" for speaker, text in dialogue_history
        )

    party_str = "None"
    if party_members:
        party_str = ", ".join(
            f"{name} ({char_class})" for name, char_class in party_members
        )

    inv_str = "None"
    if inventory_items:
        inv_str = ", ".join(inventory_items)

    prompt = f"""
You are {npc_name}, an NPC in a dark, rich, atmospheric text-based fantasy RPG game set in Aetheria.
Your persona/background: {persona}

A player is speaking to you.
Player Details:
- Name: {player_name}
- Class: {player_class} (Level {player_level})
- HP: {player_hp}/{player_max_hp}
- Inventory: {inv_str}

Active Companions traveling in the Player's Party:
{party_str}

Current Quest Context in the World:
{quest_context}
{history_str}

The player says/asks about: "{topic}"

Provide an immersive, atmospheric, in-character response. Keep it concise (1 to 4 sentences). 
Speak directly in your unique voice. Do NOT include any meta-text, meta-tags, or markdown headers. Just your raw dialogue.
If any companions are present, you are welcome to address them specifically (e.g. Lyra or Garrick) if appropriate or mention their class.
"""
    response = call_gemini(prompt, temperature=0.8)
    if response:
        return response

    # High-quality procedural fallback if Gemini is offline
    topic_lower = topic.lower()
    if "quest" in topic_lower or "help" in topic_lower:
        return f"{npc_name} sighs. 'There is much work to be done. Check the town quest board, adventurer.'"
    elif "hello" in topic_lower or "hi" in topic_lower:
        return f"{npc_name} nods in greeting. 'A fine day to you, traveler. What brings you to these parts?'"
    else:
        return f"{npc_name} looks at you thoughtfully. 'I do not know much about \"{topic}\", but these are dark times. Stay safe.'"


def generate_companion_banter(
    companion_name: str,
    personality: str,
    room_name: str,
    room_description: str,
    hp: int,
    max_hp: int,
    other_companions: Optional[List[str]] = None,
    player_name: str = "player",
    quest_context: str = "",
) -> str:
    """Generates exploration banter for active party companions, fully aware of other party members and quests."""
    others_str = ", ".join(other_companions) if other_companions else "None"

    prompt = f"""
You are {companion_name}, a recruitable companion traveling in the player's party in a text RPG set in Aetheria.
Your personality and class details: {personality}
Your current health: {hp}/{max_hp} HP

You have just entered a room named '{room_name}'.
Room Description: "{room_description}"

Party Companions traveling with you:
- Player: {player_name}
- Other Companions: {others_str}

Current Quest Context:
{quest_context}

Provide a brief, witty, or descriptive reaction or comment in-character about this room. 
Keep it under 2 sentences. Do NOT include any meta-text, quotes around your entire response, or action descriptions (like '*sighs*'). Just your raw spoken dialogue.
"""
    response = call_gemini(prompt, temperature=0.9)
    if response:
        return response

    # Procedural fallback
    p_lower = personality.lower()
    if "sarcastic" in p_lower or "mage" in p_lower:
        return '"Splendid. Another dark corner of the world. My robes are going to be ruined here."'
    elif "weary" in p_lower or "shield" in p_lower or "warrior" in p_lower:
        return '"Watch your step, friend. This place smells like an ambush waiting to happen."'
    else:
        return "\"An interesting spot. Let's make sure we find whatever's hidden here and move on.\""


def generate_combat_banter(
    companion_name: str,
    personality: str,
    event_type: str,  # "ally_hit", "ally_hurt", "enemy_killed", "critical_hit"
    enemy_name: str,
) -> str:
    """Generates short combat lines for companions during intense battles."""
    prompts = {
        "ally_hit": f"React to striking the {enemy_name} successfully.",
        "ally_hurt": f"React to the player or yourself getting severely hurt by {enemy_name}.",
        "enemy_killed": f"React to defeating the {enemy_name}.",
        "critical_hit": f"React to landing a massive critical hit on {enemy_name}!",
    }
    action = prompts.get(event_type, f"React to combat with {enemy_name}.")

    prompt = f"""
You are {companion_name}, fighting alongside the player in a tactical text-based turn combat RPG.
Your personality/class: {personality}

Action: {action}

Provide a very short, punchy, in-character combat exclamation (1 sentence or phrase).
Do NOT include action descriptions like '*swings sword*'. Just the spoken text.
"""
    response = call_gemini(prompt, temperature=0.8)
    if response:
        return response

    # Procedural fallback
    p_lower = personality.lower()
    if "sarcastic" in p_lower:
        if event_type == "enemy_killed":
            return '"And nothing of value was lost."'
        elif event_type == "ally_hurt":
            return '"Ouch! Can we stick to the plan where they don\'t hit us?"'
        else:
            return '"Take that!"'
    else:
        if event_type == "enemy_killed":
            return '"Victory is ours! Focus on the next target."'
        elif event_type == "ally_hurt":
            return '"Hold the line! We can survive this!"'
        else:
            return '"For honor and steel!"'


def generate_dynamic_room_description(
    room_name: str,
    base_description: str,
    is_town: bool,
    items: List[str],
    npcs: List[Tuple[str, str]],  # (name, persona)
    enemy_name: Optional[str],
    enemy_hp_info: Optional[str],
    player_name: str,
    player_class: str,
    party_members: List[Tuple[str, str]],  # (name, class/personality)
    quest_context: str,
) -> str:
    """Generates a highly immersive, cohesive, and context-aware description of the room based on present entities."""

    # 1. Create a stable, hashable cache key from the inputs
    cache_key = (
        room_name,
        base_description,
        is_town,
        tuple(sorted(items)),
        tuple(sorted(npcs)),
        enemy_name,
        enemy_hp_info,
        player_name,
        player_class,
        tuple(sorted(party_members)),
        quest_context,
    )

    # 2. Check the in-memory cache
    if cache_key in _ROOM_DESC_CACHE:
        return _ROOM_DESC_CACHE[cache_key]

    party_str = "None"
    if party_members:
        party_str = ", ".join(f"{name} ({desc})" for name, desc in party_members)

    npcs_str = "None"
    if npcs:
        npcs_str = ", ".join(f"{name} (Persona: {persona})" for name, persona in npcs)

    items_str = "None"
    if items:
        items_str = ", ".join(items)

    enemy_str = "None"
    if enemy_name:
        enemy_str = f"{enemy_name} {enemy_hp_info if enemy_hp_info else ''}"

    prompt = f"""
You are the narrator of a dark, immersive, atmospheric text-based fantasy RPG game set in the realm of Aetheria.
Generate a rich, sensory, and context-aware description of the current room.

Room Name: {room_name}
Base Room Description: "{base_description}"
Is it a Town Hub? {"Yes" if is_town else "No (Hostile Area)"}

Entities and Objects currently present in the room:
- Items on the floor: {items_str}
- NPCs present: {npcs_str}
- Enemies/Monsters lurking: {enemy_str}

The Player's Party details:
- Player: {player_name} ({player_class})
- Active Companions: {party_str}

Current Quest Context in the World:
{quest_context}

Write a beautiful, cohesive, atmospheric descriptive paragraph (2 to 4 sentences) for this room.
Incorporate the presence of any NPCs, enemies, loot, or companions organically into the narrative. 
For example, mention how companions react to the atmosphere, how local characters fit into the scene, or how a looming foe watches you.
Do NOT repeat the name of the room. Keep it highly immersive and under 100 words. Do NOT include any meta-text, markdown tags, or headers.
"""
    response = call_gemini(prompt, temperature=0.7)
    if response:
        # Cache the response to prevent repeated API calls
        # Evict oldest entry if cache exceeds 100 elements to prevent leaks
        if len(_ROOM_DESC_CACHE) >= 100:
            # Delete first key (since dict is ordered by insertion in Python 3.7+)
            first_key = next(iter(_ROOM_DESC_CACHE))
            del _ROOM_DESC_CACHE[first_key]
        _ROOM_DESC_CACHE[cache_key] = response
        return response

    # Clean procedural fallback
    fallback_parts = [base_description]
    if party_members:
        names = [name for name, _ in party_members]
        if len(names) == 1:
            fallback_parts.append(f"{names[0]} stands beside you, looking around.")
        else:
            fallback_parts.append(
                f"Your companions, {', '.join(names[:-1])} and {names[-1]}, watch your surroundings closely."
            )
    if npcs:
        npc_names = [name for name, _ in npcs]
        fallback_parts.append(f"You spot {', '.join(npc_names)} standing nearby.")
    if enemy_name:
        fallback_parts.append(f"A hostile {enemy_name} glares at you from the shadows.")

    fallback_desc = " ".join(fallback_parts)
    # Cache the fallback too to prevent repeated failures trying to hit the API
    if len(_ROOM_DESC_CACHE) >= 100:
        first_key = next(iter(_ROOM_DESC_CACHE))
        del _ROOM_DESC_CACHE[first_key]
    _ROOM_DESC_CACHE[cache_key] = fallback_desc
    return fallback_desc
