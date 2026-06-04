# src/aetheria/ui_layout.py
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.box import DOUBLE
from typing import Any


def generate_main_dashboard_layout(
    room_panel: Panel,
    minimap_panel: Any,
    party_panel: Panel,
    log_panel: Panel,
    quick_actions_panel: Any = None,
    header_title: str = "✨ Aetheria Terminal Console ✨",
) -> Layout:
    """
    Assembles a beautiful, non-scrolling full-screen dashboard layout grid.
    Apportions coordinate real-estate cleanly to prevent terminal overflows.
    """
    layout = Layout()

    if quick_actions_panel is None:
        # ORIGINAL LAYOUT FOR TEST COMPATIBILITY
        # Split into Header, Body, and Footer
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=3),
            Layout(name="footer", ratio=2),
        )

        # Split Body into Left (Room details) and Right (Maps)
        layout["body"].split_row(
            Layout(name="room_details", ratio=50),
            Layout(name="map_views", ratio=50, minimum_size=58),
        )

        # Split Footer into Left (Party HUD) and Right (Activity Logs)
        layout["footer"].split_row(
            Layout(name="party_hud", ratio=45), Layout(name="activity_log", ratio=55)
        )

        # Populate Header Content
        layout["header"].update(
            Panel(
                Text(header_title, style="bold gold1", justify="center"),
                border_style="gold1",
                box=DOUBLE,
            )
        )

        # Populate Grid Containers
        layout["body"]["room_details"].update(room_panel)
        layout["body"]["map_views"].update(minimap_panel)
        layout["footer"]["party_hud"].update(party_panel)
        layout["footer"]["activity_log"].update(log_panel)

    else:
        # REIMAGINED SIMPLE & ANIMATED INTEGRATED LAYOUT
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=14),
            Layout(name="footer", size=7),
        )

        # Header Panel
        layout["header"].update(
            Panel(
                Text(header_title, style="bold gold1", justify="center"),
                border_style="gold1",
                box=DOUBLE,
            )
        )

        # Body Row split: Left Column (Narrative + Log) and Right Column (Maps + Party Vitals)
        layout["body"].split_row(
            Layout(name="left_column", ratio=55),
            Layout(name="right_column", ratio=45),
        )

        # Left Column: Top (Exploration narrative) and Bottom (Recent Activity Log)
        layout["body"]["left_column"].split_column(
            Layout(name="exploration", ratio=65),
            Layout(name="activity_log", ratio=35),
        )

        # Right Column: Top (Maps/Minimap) and Bottom (Party Vitals HUD)
        layout["body"]["right_column"].split_column(
            Layout(name="map_views", ratio=40),
            Layout(name="party_hud", ratio=60),
        )

        # Update renderables
        layout["body"]["left_column"]["exploration"].update(room_panel)
        layout["body"]["left_column"]["activity_log"].update(log_panel)
        layout["body"]["right_column"]["map_views"].update(minimap_panel)
        layout["body"]["right_column"]["party_hud"].update(party_panel)
        layout["footer"].update(quick_actions_panel)

    return layout


def generate_combat_dashboard_layout(
    party_panel: Panel,
    enemy_panel: Panel,
    log_panel: Panel,
    combat_actions_panel: Any,
    header_title: str = "⚔️ Aetheria Tactical Combat ⚔️",
) -> Layout:
    """
    Assembles a beautiful, non-scrolling combat dashboard.
    Maintains symmetric height splits to guarantee a perfect 24-line terminal layout.
    """
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=14),
        Layout(name="footer", size=7),
    )

    # Populate Header Content
    layout["header"].update(
        Panel(
            Text(header_title, style="bold red", justify="center"),
            border_style="red",
            box=DOUBLE,
        )
    )

    # Split Body into Left (Party status & HP) and Right (Enemy stats & status)
    layout["body"].split_row(
        Layout(name="party_status", ratio=50),
        Layout(name="enemy_status", ratio=50),
    )

    # Split Footer into Left (Combat round log) and Right (Interactive Action Panel)
    layout["footer"].split_row(
        Layout(name="combat_log", ratio=55),
        Layout(name="combat_actions", ratio=45),
    )

    # Assign renderables
    layout["body"]["party_status"].update(party_panel)
    layout["body"]["enemy_status"].update(enemy_panel)
    layout["footer"]["combat_log"].update(log_panel)
    layout["footer"]["combat_actions"].update(combat_actions_panel)

    return layout
