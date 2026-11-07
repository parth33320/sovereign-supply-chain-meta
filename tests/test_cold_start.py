"""
test_cold_start.py - Verify cold-start performance and keyless boots under DEMO_MODE=1.
"""
import time
import os
from pathlib import Path
import streamlit.testing.v1 as st_test

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_app_cold_start_under_15s():
    """Verify app imports and runs in under 15 seconds without freezing or halting."""
    old_env = os.environ.get("DEMO_MODE")
    os.environ["DEMO_MODE"] = "1"
    start_time = time.time()
    try:
        app_path = REPO_ROOT / "app.py"
        at = st_test.AppTest.from_file(str(app_path), default_timeout=15)
        at.run()
        elapsed = time.time() - start_time
        assert elapsed < 15.0, f"App took {elapsed:.2f}s to cold start, exceeding 15s budget"
        # Confirm app booted into main content rather than stopping at Setup Required
        assert not any("API Key Required" in m.value for m in at.markdown), "Halted on API Key Required"
        assert len(at.text_input) > 0, "Combined text input was not rendered"
    finally:
        if old_env is None:
            os.environ.pop("DEMO_MODE", None)
        else:
            os.environ["DEMO_MODE"] = old_env
