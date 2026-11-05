import os
import pytest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")


def read_app_source():
    with open(APP_PATH, "r", encoding="utf-8") as f:
        return f.read()


def test_page_config_no_mvp():
    source = read_app_source()
    assert "MVP" not in source
    assert 'page_title="Sovereign Supply Chain"' in source


def test_loader_overlay_present():
    source = read_app_source()
    assert "ssc-loader" in source


def test_onboarding_card_present():
    source = read_app_source()
    assert "Welcome to Sovereign" in source
    assert "prefill_prompt" in source


def test_toast_function_exists():
    from app import show_toast
    assert callable(show_toast)


def test_persistent_keys_not_cleared_on_switch():
    source = read_app_source()
    assert "PERSISTENT_KEYS" in source
    assert "messages" in source


def test_disruption_banner_uses_severity_color():
    source = read_app_source()
    assert "#f85149" in source
    assert "#e3b341" in source


def test_guardrail_block_clears_input():
    source = read_app_source()
    assert 'prefill_prompt"] = ""' in source


def test_progress_bar_steps_defined():
    source = read_app_source()
    assert "AGENT_STEPS" in source
    assert "dispatch_ts" in source


def test_chat_input_css_overridden():
    source = read_app_source()
    assert ".stChatInput" in source
    assert "#58a6ff" in source


def test_hitl_card_yellow_border():
    source = read_app_source()
    assert "#e3b341" in source
    assert "AWAITING YOUR APPROVAL" in source
