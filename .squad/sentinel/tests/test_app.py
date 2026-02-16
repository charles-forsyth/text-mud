import os
import json
import pytest
from unittest.mock import patch
import sys

# Add the project root to the path so we can import mud_game
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from mud_game import Game


@pytest.fixture
def game():
    """Fixture to create a game instance with initialized world."""
    g = Game()
    g.setup_world()
    return g


def test_save_game_creates_json(game, tmp_path):
    """Verify that save_game creates a valid JSON file with correct state."""
    save_file = tmp_path / "savegame.json"

    if not hasattr(game, "save_game"):
        pytest.skip("Game.save_game not yet implemented")

    # Modify state to something non-default
    game.player.hp = 75
    game.player.current_room = game.world["Kitchen"]

    # Manually populate inventory if items_registry exists
    if hasattr(game, "items_registry") and "Rusty Sword" in game.items_registry:
        game.player.inventory = [game.items_registry["Rusty Sword"]]

    # Execute save
    game.save_game(str(save_file))

    assert save_file.exists()

    with open(save_file, "r") as f:
        data = json.load(f)

    assert data.get("version") == "1.0"
    assert data.get("player", {}).get("hp") == 75
    assert data.get("player", {}).get("current_room") == "Kitchen"


def test_load_game_restores_state(game, tmp_path):
    """Verify that load_game correctly restores the player state."""
    save_file = tmp_path / "savegame.json"

    if not hasattr(game, "load_game"):
        pytest.skip("Game.load_game not yet implemented")

    save_data = {
        "version": "1.0",
        "player": {"hp": 42, "current_room": "Dungeon", "inventory": ["Golden Key"]},
    }

    with open(save_file, "w") as f:
        json.dump(save_data, f)

    # Execute load
    success = game.load_game(str(save_file))
    assert success is True

    assert game.player.hp == 42
    assert game.player.current_room.name == "Dungeon"


def test_load_game_validation_invalid_room(game, tmp_path):
    """Verify load_game fails gracefully when a room doesn't exist."""
    save_file = tmp_path / "savegame.json"

    if not hasattr(game, "load_game"):
        pytest.skip("Game.load_game not yet implemented")

    save_data = {
        "version": "1.0",
        "player": {"hp": 100, "current_room": "The Moon", "inventory": []},
    }
    with open(save_file, "w") as f:
        json.dump(save_data, f)

    success = game.load_game(str(save_file))
    assert success is False


def test_load_game_malformed_json(game, tmp_path):
    """Verify load_game handles corrupted JSON files."""
    save_file = tmp_path / "corrupted.json"

    if not hasattr(game, "load_game"):
        pytest.skip("Game.load_game not yet implemented")

    with open(save_file, "w") as f:
        f.write("{ this is not json }")

    success = game.load_game(str(save_file))
    assert success is False


def test_save_command_integration(game):
    """Verify that 'save' command is recognized and calls save_game."""
    if not hasattr(game, "save_game"):
        # We check if process_command handles it, even if save_game is missing
        # it should probably at least not crash or it should call the method
        pass

    with patch.object(game, "save_game", create=True, return_value=True) as mock_save:
        # Patching with create=True allows patching non-existent attributes
        game.process_command("save")
        # If it's implemented, it should have been called
        if not mock_save.called:
            pytest.fail(
                "Command 'save' did not trigger save_game (or is not implemented)"
            )


def test_load_command_integration(game):
    """Verify that 'load' command is recognized and calls load_game."""
    with patch.object(game, "load_game", create=True, return_value=True) as mock_load:
        game.process_command("load")
        if not mock_load.called:
            pytest.fail(
                "Command 'load' did not trigger load_game (or is not implemented)"
            )


def test_items_registry_exists(game):
    """Verify that Game has an items_registry attribute."""
    assert hasattr(game, "items_registry"), (
        "Game object missing items_registry attribute"
    )
    assert isinstance(game.items_registry, dict), (
        "items_registry should be a dictionary"
    )


def test_items_registry_populated(game):
    """Verify that items_registry is populated with items."""
    if not hasattr(game, "items_registry"):
        pytest.skip("items_registry not yet implemented")
    assert len(game.items_registry) > 0, "items_registry should not be empty"
    assert "Golden Key" in game.items_registry, "Golden Key missing from items_registry"
