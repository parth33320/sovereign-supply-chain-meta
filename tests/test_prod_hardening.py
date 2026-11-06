import time
from unittest.mock import patch
import pytest


def test_no_sql_interpolation():
    with open("mcp_server.py", "r") as f:
        source = f.read()
    assert 'f"SELECT' not in source
    assert "f'SELECT" not in source


def test_dpo_log_writes_to_db():
    from graph import log_dpo
    from db import execute_query, execute_mutation

    # Ensure table exists
    execute_mutation("CREATE TABLE IF NOT EXISTS dpo_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT, chosen TEXT, rejected TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

    prompt_val = f"test prompt {time.time()}"
    log_dpo(prompt_val, "good", "bad")
    rows = execute_query("SELECT * FROM dpo_logs WHERE prompt = ?", [prompt_val])
    assert len(rows) == 1
    assert rows[0]["chosen"] == "good"
    assert rows[0]["rejected"] == "bad"


def test_disruption_radar_timeout():
    import disruption_radar
    from disruption_radar import fetch_disruption_alert, DEFAULT_FALLBACK, clear_disruption_cache
    clear_disruption_cache()

    def slow_fetch(url, limit=5):
        time.sleep(15)
        return ["fake headline"]

    start = time.time()
    with patch.object(disruption_radar, "_fetch_feed_headlines", side_effect=slow_fetch):
        result = fetch_disruption_alert()
    elapsed = time.time() - start

    assert elapsed < 12, f"Expected fetch_disruption_alert to complete in < 12s, took {elapsed}s"
    assert result == DEFAULT_FALLBACK


def test_friendly_error_connection():
    from app import friendly_error
    result = friendly_error(Exception("connection refused"))
    assert "database" in result.lower() or "reach" in result.lower()


def test_health_endpoint():
    # Render single-port health check path configured in render.yaml is /_stcore/health
    with open("render.yaml", "r") as f:
        content = f.read()
    assert "/_stcore/health" in content