import pytest
from unittest.mock import patch, MagicMock
from app import show_user_error, suggest_similar_item, check_missing_item_and_suggest


def test_suggest_similar_item_direct_match():
    # Direct match (case-insensitive) should find item in Tenant_A
    result = suggest_similar_item("Semiconductors", "Tenant_A")
    assert result == "Semiconductors"
    result_lower = suggest_similar_item("semiconductors", "Tenant_A")
    assert result_lower == "Semiconductors"


def test_suggest_similar_item_fuzzy_match():
    # 'semiconductor' (singular) should fuzzy match 'Semiconductors'
    match = suggest_similar_item("semiconductor", "Tenant_A")
    assert match == "Semiconductors"

    # 'actuator' should fuzzy match 'Hydraulic Actuators'
    match_act = suggest_similar_item("actuator", "Tenant_A")
    assert match_act == "Hydraulic Actuators"

    # 'multimeter' should fuzzy match 'Digital Multimeters'
    match_multi = suggest_similar_item("multimeter", "Tenant_A")
    assert match_multi == "Digital Multimeters"


def test_suggest_similar_item_cutoff_0_5():
    # 'copper wire' -> 'Copper Wire Spools' with cutoff=0.5
    match = suggest_similar_item("copper wire", "Tenant_A")
    assert match == "Copper Wire Spools"


def test_suggest_similar_item_tenant_isolation():
    # 'denim fabric' is in Tenant_B, not Tenant_A
    match_b = suggest_similar_item("denim fabric", "Tenant_B")
    assert match_b == "Raw Indigo Denim Fabric"

    match_a = suggest_similar_item("denim fabric", "Tenant_A")
    assert match_a is None or "denim" not in match_a.lower()


def test_check_missing_item_and_suggest():
    res = check_missing_item_and_suggest("Please check on semiconductor stock immediately", "Tenant_A")
    assert res is not None
    err_msg, suggestion = res
    assert "Item not found" in err_msg or "couldn't find" in err_msg
    assert "Semiconductors" in suggestion


def test_show_user_error_renders_card():
    with patch("streamlit.markdown") as mock_markdown:
        show_user_error("Test Error Message", "Test Suggestion")
        mock_markdown.assert_called_once()
        rendered_html = mock_markdown.call_args[0][0]
        assert "user-error-card" in rendered_html
        assert "⚠️ Action Needed" in rendered_html
        assert "Test Error Message" in rendered_html
        assert "What to do next:" in rendered_html
        assert "Test Suggestion" in rendered_html
