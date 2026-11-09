"""Dependencies and in-memory activity log for Sovereign Supply Chain."""

_activity_log: list = []

def get_activity_log() -> list:
    """Returns the shared activity log."""
    return _activity_log

def clear_activity_log():
    """Clears the shared activity log."""
    global _activity_log
    _activity_log = []
