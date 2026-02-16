# Design Document: Save/Load System for Haunted Castle MUD

## Overview
This document outlines the design for adding a robust Save/Load system to the Haunted Castle MUD. This system will allow players to persist their game state and resume play at a later time, ensuring a seamless experience in the Haunted Castle world.

## Mission
Add a robust Save/Load system to the Haunted Castle MUD. Players should be able to save their progress (HP, inventory, current room) to a `savegame.json` file and load it upon starting or via a `load` command. The Gatekeeper will audit the security of the file loading logic to prevent vulnerabilities.

## Requirements

### 1. Persistence
- **State to save**:
    - `player.hp` (integer): Current health points of the player.
    - `player.current_room.name` (string): The unique name of the room where the player is currently located.
    - `player.inventory` (list of strings): A list of names of items currently held by the player.
- **File format**: JSON.
- **Filename**: `savegame.json` (stored in the project root).

### 2. User Interface
- **New Command: `save`**
    - Saves the current state to `savegame.json`.
    - Feedback: "Game saved successfully to savegame.json."
- **New Command: `load`**
    - Loads the state from `savegame.json`.
    - Feedback: "Game loaded successfully." or error handling.
- **Startup Loading**:
    - On launch, if `savegame.json` exists, prompt: "A saved game was found. Would you like to load it? (yes/no)".

### 3. Architecture Changes

#### Data Schema (`savegame.json`)
```json
{
  "version": "1.0",
  "player": {
    "hp": 100,
    "current_room": "Entrance Hall",
    "inventory": ["Rusty Sword", "Health Potion"]
  }
}
```

#### `Game` Class Enhancements
- `Game.items_registry`: A dictionary to store all available `Item` templates/instances for easy lookup during loading.
- `Game.save_game(filename: str = "savegame.json") -> bool`:
    - Serializes `self.player.hp`, `self.player.current_room.name`, and `[item.name for item in self.player.inventory]`.
- `Game.load_game(filename: str = "savegame.json") -> bool`:
    - Reads JSON, validates, and updates `self.player`.
    - Uses `self.world` to find the `Room` object.
    - Uses `self.items_registry` to find `Item` objects for the inventory.

## Architectural Decision Records (ADRs)

### ADR 1: Use of JSON for Save Files
- **Status**: Accepted
- **Decision**: Use JSON for its readability and ease of use with Python's `json` module.

### ADR 2: Entity Lookups via Registries
- **Status**: Accepted
- **Decision**: Save names of rooms and items as strings. Maintain `world` (rooms) and `items_registry` (items) in the `Game` class to resolve these names back to objects during loading.

### ADR 3: Fail-Safe Loading
- **Status**: Accepted
- **Decision**: Implement strict validation. If a save file is corrupted or contains invalid entities, the load operation will abort with an error message, leaving the current game state untouched.

## Security Considerations (Gatekeeper Audit)
- **Path Traversal**: Restrict file operations to the current directory.
- **Data Validation**: Ensure `hp` is an integer and within `[0, max_hp]`.
- **Existence Checks**: Verify room and item names exist in the game registries before assignment.
- **Error Handling**: Gracefully handle `FileNotFoundError` and `json.JSONDecodeError`.

## Implementation Plan
1. **Registry Setup**: Populate `items_registry` in `Game.setup_world`.
2. **Serialization**: Implement `Game.save_game`.
3. **Deserialization**: Implement `Game.load_game` with validation.
4. **Integration**: Add `save`/`load` commands and startup prompt.
5. **Verification**: Write tests for all save/load scenarios.
