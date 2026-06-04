# tests/test_premium_ui.py
import unittest
from unittest.mock import patch
from rich.panel import Panel
from rich.layout import Layout

from aetheria.ui_meters import render_stat_progress_bar
from aetheria.ui_log import ScrollingActivityLog, parse_string_to_log_event
from aetheria.ui_effects import render_dynamic_impact_panel
from aetheria.ui_layout import generate_main_dashboard_layout
from aetheria.ui_input import get_input_suggestions_panel, interactive_prompt


class TestPremiumUIUX(unittest.TestCase):
    def test_stat_progress_bars_color_thresholds(self):
        """Verify that graphical meters transition colors based on status ratio thresholds."""
        # > 50% should be green
        green_bar = render_stat_progress_bar("HP", 80, 100, width=10)
        self.assertTrue(any("green" in str(s.style) for s in green_bar.spans))

        # XP bar color scheme (purple)
        xp_bar = render_stat_progress_bar("XP", 10, 100, width=10, color_scheme="xp")
        self.assertTrue(any("purple" in str(s.style) for s in xp_bar.spans))

        # Mana bar color scheme (cyan)
        mana_bar = render_stat_progress_bar(
            "MP", 50, 100, width=10, color_scheme="mana"
        )
        self.assertTrue(any("cyan" in str(s.style) for s in mana_bar.spans))

    def test_semantic_structured_activity_log_parsing(self):
        """Verify parsing of raw string logs into themed, icon-highlighted GameLogEvents."""
        combat_msg = "Archmage Malakor deals 25 physical damage."
        evt = parse_string_to_log_event(combat_msg)
        self.assertEqual(evt.category, "combat_damage")
        rich_text = evt.format_to_rich()
        self.assertIn("⚔️", rich_text.plain)

        loot_msg = "You found a Gold Key inside the chest."
        evt2 = parse_string_to_log_event(loot_msg)
        self.assertEqual(evt2.category, "loot")
        rich_text2 = evt2.format_to_rich()
        self.assertIn("🎁", rich_text2.plain)

        dialog_msg = "Barnaby says: Safe travels, hero!"
        evt3 = parse_string_to_log_event(dialog_msg)
        self.assertEqual(evt3.category, "dialogue")
        rich_text3 = evt3.format_to_rich()
        self.assertIn("👤", rich_text3.plain)

    def test_scrolling_activity_log_buffering(self):
        """Verify that ScrollingActivityLog respects sizing bounds and rolls correctly."""
        log = ScrollingActivityLog(max_size=3)
        log.append("system", "Event 1")
        log.append("system", "Event 2")
        log.append("system", "Event 3")
        log.append("system", "Event 4")

        self.assertEqual(len(log.buffer), 3)
        self.assertEqual(log.buffer[0].message, "Event 2")
        self.assertEqual(log.buffer[2].message, "Event 4")

        lines = log.get_display_lines(limit=2)
        self.assertEqual(len(lines), 2)

    def test_dynamic_impact_panel_box_transformations(self):
        """Verify that panels transition to high-alert double-bordered red borders on heavy hit impacts."""
        panel_normal = render_dynamic_impact_panel(
            "Content", "Title", is_impacted=False
        )
        self.assertEqual(panel_normal.border_style, "dim slate_blue1")

        panel_town = render_dynamic_impact_panel(
            "Content", "Title", is_impacted=False, is_town=True
        )
        self.assertEqual(panel_town.border_style, "dim green")

        panel_impacted = render_dynamic_impact_panel(
            "Content", "Title", is_impacted=True
        )
        self.assertEqual(panel_impacted.border_style, "bold red")
        # Double box border should be used
        from rich.box import DOUBLE

        self.assertEqual(panel_impacted.box, DOUBLE)

    def test_full_screen_dashboard_layout_grid(self):
        """Verify dashboard assembler split rows and columns correctly without overlaps."""
        room_panel = Panel("Room Content")
        minimap_panel = Panel("Minimap Content")
        party_panel = Panel("Party Status Content")
        log_panel = Panel("Activity Log Content")

        layout = generate_main_dashboard_layout(
            room_panel, minimap_panel, party_panel, log_panel
        )
        self.assertIsInstance(layout, Layout)
        self.assertIsNotNone(layout["header"])
        self.assertIsNotNone(layout["body"])
        self.assertIsNotNone(layout["footer"])

    def test_reimagined_dashboard_layout_grid_with_quick_actions(self):
        """Verify that passing quick_actions_panel splits the layout according to the reimagined dashboard."""
        room_panel = Panel("Room Content")
        minimap_panel = Panel("Minimap Content")
        party_panel = Panel("Party Status Content")
        log_panel = Panel("Activity Log Content")
        quick_actions_panel = Panel("Quick Actions Content")

        layout = generate_main_dashboard_layout(
            room_panel,
            minimap_panel,
            party_panel,
            log_panel,
            quick_actions_panel=quick_actions_panel,
        )
        self.assertIsInstance(layout, Layout)
        self.assertIsNotNone(layout["header"])
        self.assertIsNotNone(layout["body"])
        self.assertIsNotNone(layout["footer"])

        # Verify specific sub-layouts exist in the reimagined layout
        self.assertIsNotNone(layout["body"]["left_column"])
        self.assertIsNotNone(layout["body"]["left_column"]["exploration"])
        self.assertIsNotNone(layout["body"]["left_column"]["activity_log"])
        self.assertIsNotNone(layout["body"]["right_column"])
        self.assertIsNotNone(layout["body"]["right_column"]["map_views"])
        self.assertIsNotNone(layout["body"]["right_column"]["party_hud"])
        self.assertIsNotNone(layout["footer"])

    def test_smart_command_input_suggestions_hud(self):
        """Verify autocomplete HUD guides player inputs dynamically."""
        panel_empty = get_input_suggestions_panel("", ["north", "south"])
        self.assertIn("💡 Hotkeys:", panel_empty.renderable.plain)

        panel_go = get_input_suggestions_panel("go", ["north", "south"])
        self.assertIn("🚪 Travel Paths:", panel_go.renderable.plain)
        self.assertIn("north", panel_go.renderable.plain)

        panel_take = get_input_suggestions_panel("take", [])
        self.assertIn("📦 Usage: take", panel_take.renderable.plain)

    @patch("sys.stdin.isatty", return_value=False)
    @patch("sys.stdin.readline", return_value="go north\n")
    def test_interactive_prompt_tty_fallback(self, mock_readline, mock_isatty):
        """Verify prompt falls back gracefully to standard readline when not in TTY environment."""
        result = interactive_prompt(["north", "south"], prompt_text="> ")
        self.assertEqual(result, "go north")
        mock_readline.assert_called_once()

    def test_layout_capture_prevention(self):
        """Verify that layout lines and box borders are detected as layout lines to prevent pollution."""
        from mud_game import is_layout_line

        # Border lines should be classified as layout lines
        self.assertTrue(
            is_layout_line("│                                             │")
        )
        self.assertTrue(
            is_layout_line("┌───────────────────────────────────────────────┐")
        )
        self.assertTrue(is_layout_line("HP   [████████████] 90/90"))
        self.assertTrue(is_layout_line("XP   [░░░░░░░░░░░░] 0/100"))

        # Normal narrative lines should NOT be classified as layout lines
        self.assertFalse(is_layout_line("You travel north to the Eldergrove Tavern."))
        self.assertFalse(
            is_layout_line("The tavernkeeper Barnaby says: Hello traveller!")
        )

    @patch("mud_game.build_default_world")
    @patch("mud_game.get_default_quests")
    def test_game_controller_capture_rendering_bypass(self, mock_quests, mock_world):
        """Verify that GameController bypasses render_current_room during command capture."""
        from mud_game import GameController
        from unittest.mock import MagicMock

        controller = GameController()
        controller.player = MagicMock()
        controller.player.current_room = MagicMock()
        controller.player.current_room.items = []
        controller.player.current_room.npcs = []
        controller.player.current_room.enemy = None

        # When is_capturing is True, calling render_current_room should call render_room_panel
        # When is_capturing is False, calling render_current_room should return immediately
        with patch("mud_game.render_room_panel") as mock_render:
            controller.is_capturing = True
            controller.render_current_room()
            mock_render.assert_not_called()

            controller.is_capturing = False
            # Mock generate_dynamic_room_description
            with patch(
                "mud_game.generate_dynamic_room_description", return_value="Desc"
            ):
                controller.render_current_room()
                mock_render.assert_called_once()
