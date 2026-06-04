from enum import Enum, auto
from typing import Any, Callable, Dict, List
import threading
import logging


class EventType(Enum):
    ENEMY_KILLED = auto()
    ITEM_ACQUIRED = auto()
    NPC_SPOKEN = auto()
    ROOM_EXPLORED = auto()
    GOLD_CHANGED = auto()
    PARTY_MEMBER_RECRUITED = auto()


class Event:
    """Immutable data container representing a discrete in-game event."""

    def __init__(self, event_type: EventType, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data


class EventDispatcher:
    """Thread-safe event publishing and subscription broker."""

    _listeners: Dict[EventType, List[Callable[[Event], None]]] = {}
    _lock = threading.RLock()

    @classmethod
    def subscribe(cls, event_type: EventType, callback: Callable[[Event], None]):
        """Registers a listener callback for a specific event type."""
        with cls._lock:
            if event_type not in cls._listeners:
                cls._listeners[event_type] = []
            if callback not in cls._listeners[event_type]:
                cls._listeners[event_type].append(callback)

    @classmethod
    def unsubscribe(cls, event_type: EventType, callback: Callable[[Event], None]):
        """Removes a listener callback from an event type."""
        with cls._lock:
            if event_type in cls._listeners:
                try:
                    cls._listeners[event_type].remove(callback)
                except ValueError:
                    pass

    @classmethod
    def dispatch(cls, event_type: EventType, data: Dict[str, Any]):
        """Dispatches an event to all active subscribers with safety guards."""
        event = Event(event_type, data)
        callbacks = []

        with cls._lock:
            if event_type in cls._listeners:
                # Copy list to allow subscribers to modify listeners during execution without race errors
                callbacks = list(cls._listeners[event_type])

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logging.error(
                    f"EventDispatcher: Subscriber {callback} crashed on event {event_type}: {e}"
                )
