# Design Document: Haunted Castle MUD

## Overview
A single-player text-based adventure game set in a haunted castle. The player explores rooms, collects items, fights enemies, and attempts to escape.

## Goals
-   Find the **Golden Key** in the **Great Hall**.
-   Survive the **Goblin** in the **Dungeon**.
-   Unlock and exit through the **Front Gate**.

## Architecture

### Classes

1.  **`Item`**
    -   `name`: str
    -   `description`: str

2.  **`Enemy`**
    -   `name`: str
    -   `description`: str
    -   `damage`: int
    -   Method: `attack(player)`

3.  **`Room`**
    -   `name`: str
    -   `description`: str
    -   `exits`: dict (direction -> Room)
    -   `items`: list[Item]
    -   `enemy`: Enemy (optional)
    -   `locked`: bool (default False)
    -   `key_needed`: Item (optional)

    -   Methods:
        -   `add_exit(direction, room)`
        -   `add_item(item)`
        -   `remove_item(item)`
        -   `set_enemy(enemy)`
        -   `get_exit(direction)`

4.  **`Player`**
    -   `current_room`: Room
    -   `inventory`: list[Item]
    -   `hp`: int (starts at 100)
    -   `max_hp`: int (100)

    -   Methods:
        -   `move(direction)`
        -   `look()`
        -   `take(item_name)`
        -   `use(item_name)`
        -   `inventory_list()`
        -   `has_item(item_name)`
        -   `take_damage(amount)`
        -   `heal(amount)`

5.  **`Game`**
    -   `player`: Player
    -   `is_running`: bool

    -   Methods:
        -   `setup_world()`: Creates rooms, items, and enemies.
        -   `play()`: Main game loop.
        -   `process_command(command)`: Handles user input, enemy attacks, and win/loss conditions.

## Game Loop
1.  Initialize `Game`.
2.  Call `setup_world()`.
3.  Print welcome message.
4.  Loop while `is_running`:
    -   Get user input.
    -   `process_command(input)`.
    -   If player in room with enemy, enemy attacks.
    -   Check if Player HP <= 0 (Game Over).
    -   Check win condition (Player at Front Gate with Golden Key AND HP > 0).

## World Map
-   **Entrance Hall**: Starting point. Exits: North (Great Hall), East (Kitchen).
-   **Great Hall**: Contains **Golden Key**. Exits: South (Entrance Hall), West (Dungeon).
-   **Kitchen**: Contains **Rusty Sword** and **Health Potion**. Exits: West (Entrance Hall).
-   **Dungeon**: Contains **Goblin** (Enemy). Exits: East (Great Hall).
-   **Front Gate**: Locked. Requires **Golden Key**. Exits: North (Escape/Win).

## Commands
-   `go [direction]` (n, s, e, w)
-   `look`
-   `take [item]`
-   `use [item]` (e.g., `use health potion`)
-   `inventory` (or `i`)
-   `quit` (or `q`)
