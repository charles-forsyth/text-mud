import google.generativeai as genai
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


def call_gemini(prompt: str, temperature: float = 0.7) -> str:
    """Helper to safely make calls to Google Gemini with a procedural fallback."""
    if not _api_ready:
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
        return response.text.strip()
    except Exception:
        # Graceful fallback to indicate that the API might be throttled/offline
        return ""


def generate_npc_dialogue(
    npc_name: str, persona: str, topic: str, player_name: str, quest_context: str
) -> str:
    """Generates context-aware, in-character NPC responses using Gemini 3.1 Pro."""
    prompt = f"""
You are {npc_name}, an NPC in a dark, atmospheric text-based fantasy RPG game.
Your persona/background: {persona}

A player named '{player_name}' is speaking to you.
They want to talk to you about: "{topic}"
Current quest context in the world: {quest_context}

Provide a immersive, atmospheric, in-character response. Keep it concise (1 to 4 sentences). 
Speak directly in your unique voice. Do NOT include any meta-text, meta-tags, or markdown headers. Just your raw dialogue.
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
) -> str:
    """Generates exploration banter for active party companions."""
    prompt = f"""
You are {companion_name}, a recruitable companion traveling in the player's party in a text RPG.
Your personality and class details: {personality}
Your current health: {hp}/{max_hp} HP

You have just entered a room named '{room_name}'.
Room Description: "{room_description}"

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
