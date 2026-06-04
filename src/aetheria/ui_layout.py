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
    header_title: str = "✨ Aetheria Terminal Console ✨",
) -> Layout:
    """
    Assembles a beautiful, non-scrolling full-screen dashboard layout grid.
    Apportions coordinate real-estate cleanly to prevent terminal overflows.
    """
    # 1. Initialize root layout
    layout = Layout()

    # 2. Split into Header, Body, and Footer
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=3),
        Layout(name="footer", ratio=2),
    )

    # 3. Split Body into Left (Room details) and Right (Maps)
    layout["body"].split_row(
        Layout(name="room_details", ratio=65), Layout(name="map_views", ratio=35)
    )

    # 4. Split Footer into Left (Party HUD) and Right (Activity Logs)
    layout["footer"].split_row(
        Layout(name="party_hud", ratio=45), Layout(name="activity_log", ratio=55)
    )

    # 5. Populate Header Content
    layout["header"].update(
        Panel(
            Text(header_title, style="bold gold1", justify="center"),
            border_style="gold1",
            box=DOUBLE,
        )
    )

    # 6. Populate Grid Containers
    layout["body"]["room_details"].update(room_panel)
    layout["body"]["map_views"].update(minimap_panel)
    layout["footer"]["party_hud"].update(party_panel)
    layout["footer"]["activity_log"].update(log_panel)

    return layout
