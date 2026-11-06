import os
import time
import sqlite3
import logging

logger = logging.getLogger(__name__)

def check_system_health() -> dict:
    """
    Runs startup health checks and returns status dict.
    Call once at app startup.
    """
    health = {
        "api_key": False,
        "database": False,
        "demo_mode": False,
        "warnings": []
    }

    # Check API key
    api_key = os.environ.get("META_API_KEY", "")
    health["api_key"] = bool(api_key and len(api_key) > 10)

    # Check database
    try:
        if os.environ.get("POSTGRES_DB_URI"):
            health["database"] = True
            health["db_type"] = "PostgreSQL"
        else:
            conn = sqlite3.connect("mock_sap.db", timeout=5)
            conn.execute("SELECT 1")
            conn.close()
            health["database"] = True
            health["db_type"] = "SQLite"
            health["warnings"].append(
                "Using SQLite — state won't persist across restarts"
            )
    except Exception as e:
        health["database"] = False
        health["warnings"].append(f"Database unavailable: {e}")

    # Check demo mode
    health["demo_mode"] = os.environ.get("DEMO_MODE") == "1"

    return health
