# Haunted Castle MUD: Aetheria

A modern, AI-enabled, text-based RPG set in the mythical realm of Aetheria. It features dynamic quests, rich town hubs, tavern recruitment pools, procedurally generated dialogue via Gemini, tactical combat, and dungeon boss fights.

## Goal
Journey through Eldergrove, solve the local goblin pestilence, find the **Golden Key** in the **Great Hall**, defeat Lord Malakor, and escape through the **Front Gate**.

---

## Brand-New Features: Play with Less Typing!

### 1. ⚡ Quick Actions Grid
Every turn, the interface automatically detects your surroundings and constructs a beautiful **Quick Actions Panel** of custom numbered actions. Instead of typing out full commands, you can simply type the matching single or double-digit number!
- **Movement**: `1` might go North, `2` goes South.
- **Interactives**: `3` might recruit Lyra, `4` might talk to Barnaby.
- **Combat & Loot**: Quickly select combat spells, physical strikes, or items to pick up directly using numeric indexes.

### 2. 🎛️ Interactive Prompts
Typing action verbs without any parameters will automatically trigger an interactive visual sub-menu:
- Type `take` or `t`: Displays a numbered list of all items on the floor and asks you which one to pick up.
- Type `use` or `u`: Displays your consumables and lets you select one by number or name.
- Type `equip` or `eq`: Displays your armament and equipment and lets you select gear to don.
- Type `talk` or `tk`: Lists characters present and asks you who to talk to.
- Type `recruit` or `rec`: Inside the tavern, lists all available companions to recruit into your active party.

---

## How to Run

Launch the game inside the virtual environment:
```bash
uv run python3 mud_game.py
```

## How to Play (Classical Mode)
- **Move**: `n`, `s`, `e`, `w` (or `go north`, etc.)
- **Look**: `look` or `l`
- **Talk to NPC**: `talk [npc_name] about [topic]` (e.g. `talk barnaby about quest`)
- **Take Item**: `take [item_name]`
- **Check Inventory**: `inventory` or `i`
- **Check Party HUD**: `party` or `p`
- **Check Quests Log**: `quests` or `q`
- **Save Game**: `save`
- **Load Game**: `load`
- **Quit**: `quit` or `exit`

---

## Tests
Run our complete and thorough test suite with:
```bash
uv run pytest
```
