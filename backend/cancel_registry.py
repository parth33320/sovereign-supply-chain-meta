"""
cancel_registry.py
Server-side graph cancellation registry managing threading.Events per thread_id.
"""

import threading
from typing import Dict

_cancelled: Dict[str, threading.Event] = {}
_lock = threading.Lock()


def register(thread_id: str) -> threading.Event:
    """Registers a new cancellation event for thread_id."""
    with _lock:
        event = threading.Event()
        _cancelled[thread_id] = event
        return event


def cancel(thread_id: str) -> None:
    """Signals cancellation for the given thread_id."""
    with _lock:
        event = _cancelled.get(thread_id)
        if event is not None:
            event.set()


def is_cancelled(thread_id: str) -> bool:
    """Checks whether cancellation was signaled for thread_id."""
    with _lock:
        event = _cancelled.get(thread_id)
        return event.is_set() if event is not None else False


def cleanup(thread_id: str) -> None:
    """Removes thread_id from cancellation registry."""
    with _lock:
        _cancelled.pop(thread_id, None)
