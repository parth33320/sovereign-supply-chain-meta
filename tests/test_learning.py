import os
import pytest
from unittest.mock import patch

def test_learning_stats(tmp_path):
    test_db = str(tmp_path / "test_dpo.db")
    with patch("learning_log.DB_PATH", test_db):
        from learning_log import log_dpo_feedback, get_learning_stats
        log_dpo_feedback("prompt 1", "response 1", feedback=1, tenant_id="tenant_1", intent="reallocation")
        log_dpo_feedback("prompt 2", "response 2", feedback=1, tenant_id="tenant_1", intent="reallocation")
        log_dpo_feedback("prompt 3", "response 3", feedback=-1, tenant_id="tenant_1", intent="stockout")

        stats = get_learning_stats("tenant_1")
        assert stats["total_feedback"] == 3
        assert stats["positive"] == 2
        assert stats["negative"] == 1
        # Assert approval_rate == positive/total
        assert stats["approval_rate"] == pytest.approx(2 / 3, 0.01)
        assert "reallocation" in stats["top_improved_intents"]

def test_weekly_trend(tmp_path):
    test_db = str(tmp_path / "test_dpo.db")
    with patch("learning_log.DB_PATH", test_db):
        from learning_log import log_dpo_feedback, get_learning_stats
        log_dpo_feedback("prompt 1", "response 1", feedback=1, tenant_id="tenant_1", intent="procurement")
        stats = get_learning_stats("tenant_1")
        weekly_trend = stats["weekly_trend"]
        # Assert len(weekly_trend) >= 1
        assert len(weekly_trend) >= 1
        assert "week" in weekly_trend[0]
        assert "rate" in weekly_trend[0]
        assert isinstance(weekly_trend[0]["rate"], float)

def test_demo_mode_seed_learning(tmp_path):
    test_db = str(tmp_path / "test_demo_dpo.db")
    with patch("learning_log.DB_PATH", test_db):
        from learning_log import seed_demo_feedback, get_learning_stats
        seed_demo_feedback()
        stats = get_learning_stats()
        assert stats["total_feedback"] == 15
        assert stats["positive"] == 12
        assert stats["negative"] == 3
        assert stats["approval_rate"] == pytest.approx(0.80, 0.01)
