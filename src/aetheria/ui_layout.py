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

        # Body Row split: Left (Room narrative + Quests + Exits) and Right (Maps + Party Stats)
        layout["body"].split_row(
            Layout(name="exploration", ratio=55),
            Layout(name="stats_and_maps", ratio=45),
        )

        # Right side split: Top (Maps/Minimap) and Bottom (Party stats)
        layout["body"]["stats_and_maps"].split_column(
            Layout(name="map_views", ratio=40),
            Layout(name="party_hud", ratio=60),
        )

        # Footer Row split: Left (Scrolling Activity Log) and Right (Quick Actions + Suggestions Hub)
        layout["footer"].split_row(
            Layout(name="activity_log", ratio=55),
            Layout(name="quick_actions", ratio=45),
        )

        layout["body"]["exploration"].update(room_panel)
        layout["body"]["stats_and_maps"]["map_views"].update(minimap_panel)
        layout["body"]["stats_and_maps"]["party_hud"].update(party_panel)
        layout["footer"]["activity_log"].update(log_panel)
        layout["footer"]["quick_actions"].update(quick_actions_panel)

    return layout
