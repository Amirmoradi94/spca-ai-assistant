"""Event system for pipeline coordination."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine


class EventType(Enum):
    """Types of events in the pipeline."""
    SCRAPE_STARTED = "scrape_started"
    SCRAPE_COMPLETED = "scrape_completed"
    SCRAPE_FAILED = "scrape_failed"
    ANIMAL_DISCOVERED = "animal_discovered"
    ANIMAL_UPDATED = "animal_updated"
    ANIMAL_ADOPTED = "animal_adopted"
    CONTENT_SAVED = "content_saved"
    SYNC_REQUIRED = "sync_required"
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"


@dataclass
class Event:
    """An event in the pipeline."""
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return f"Event({self.type.value}, data={self.data})"


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventEmitter:
    """Central event bus for pipeline coordination."""

    def __init__(self):
        self._listeners: dict[EventType, list[EventHandler]] = {}
        self._global_listeners: list[EventHandler] = []

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a listener for a specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)

    def on_any(self, handler: EventHandler) -> None:
        """Register a listener for all events."""
        self._global_listeners.append(handler)

    def off(self, event_type: EventType, handler: EventHandler) -> None:
        """Remove a listener for a specific event type."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(handler)
            except ValueError:
                pass

    def off_any(self, handler: EventHandler) -> None:
        """Remove a global listener."""
        try:
            self._global_listeners.remove(handler)
        except ValueError:
            pass

    async def emit(self, event: Event) -> None:
        """Emit an event to all registered listeners."""
        tasks = []

        # Specific listeners
        if event.type in self._listeners:
            for handler in self._listeners[event.type]:
                tasks.append(asyncio.create_task(self._safe_call(handler, event)))

        # Global listeners
        for handler in self._global_listeners:
            tasks.append(asyncio.create_task(self._safe_call(handler, event)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        """Safely call a handler, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            # Log but don't propagate
            import logging
            logging.getLogger(__name__).error(
                f"Error in event handler for {event.type}: {e}"
            )

    def clear(self) -> None:
        """Clear all listeners."""
        self._listeners.clear()
        self._global_listeners.clear()


# Global event emitter singleton
_event_emitter: EventEmitter | None = None


def get_event_emitter() -> EventEmitter:
    """Get the global event emitter."""
    global _event_emitter
    if _event_emitter is None:
        _event_emitter = EventEmitter()
    return _event_emitter


async def emit_event(event_type: EventType, data: dict[str, Any] | None = None) -> None:
    """Convenience function to emit an event."""
    emitter = get_event_emitter()
    event = Event(type=event_type, data=data or {})
    await emitter.emit(event)
