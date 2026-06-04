from collections import deque
from typing import Dict, List, Optional, Any


def find_shortest_path(start_room: Any, target_room: Any) -> Optional[List[Any]]:
    """Uses Breadth-First Search (BFS) to find the shortest exit sequence toward a destination room."""
    if start_room.name == target_room.name:
        return [start_room]

    queue = deque([[start_room]])
    visited = {start_room.name}

    while queue:
        path = queue.popleft()
        current_node = path[-1]

        for neighbor in current_node.exits.values():
            if neighbor and neighbor.name not in visited:
                new_path = list(path) + [neighbor]
                if neighbor.name == target_room.name:
                    return new_path
                visited.add(neighbor.name)
                queue.append(new_path)

    return None


class LivingWorldClock:
    """Ticking world clock cycles across Dawn, Day, Dusk, and Night based on movements."""

    TIMES = ["Dawn", "Day", "Dusk", "Night"]

    def __init__(self):
        self.current_index = 1  # Start at Day
        self.movement_ticks = 0

    def tick_movement(self) -> Optional[str]:
        """Advances time on player movement. Returns announcement on state transition."""
        self.movement_ticks += 1
        if self.movement_ticks >= 8:  # Shifting state every 8 room moves
            self.movement_ticks = 0
            self.current_index = (self.current_index + 1) % len(self.TIMES)
            return f"\n[bold gold1]⏳ Time of day has shifted: The world enters {self.TIMES[self.current_index]}...[/bold gold1]"
        return None

    @property
    def current_time(self) -> str:
        return self.TIMES[self.current_index]


class ScheduledNPC:
    """Wraps an NPC instance with pathfinding navigation schedules."""

    def __init__(self, npc_instance: Any, schedule: Dict[str, str]):
        self.npc = npc_instance
        self.schedule = schedule  # e.g., {"Dawn": "Eldergrove Center", "Night": "Eldergrove Tavern (The Golden Oak)"}

    def update_location(
        self, current_time: str, world_map: Dict[str, Any]
    ) -> Optional[str]:
        """Calculates the NPC schedule and steps them one room closer toward their target room."""
        target_room_name = self.schedule.get(current_time)
        if not target_room_name:
            return None

        current_room = getattr(self.npc, "current_room", None)
        if not current_room:
            # Try to find which room currently holds this NPC in the world_map
            for rname, room in world_map.items():
                if self.npc in room.npcs:
                    current_room = room
                    self.npc.current_room = room
                    break

        if not current_room or current_room.name == target_room_name:
            return None

        target_room = world_map.get(target_room_name)
        if not target_room:
            return None

        path = find_shortest_path(current_room, target_room)
        if path and len(path) > 1:
            next_room = path[1]

            # Relocate NPC containers safely
            if self.npc in current_room.npcs:
                current_room.npcs.remove(self.npc)
            next_room.npcs.append(self.npc)
            self.npc.current_room = next_room

            return f"👤 [bold cyan]{self.npc.name}[/bold cyan] traveled towards the [bold green]{next_room.name}[/bold green]."
        return None
