import os
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.routers import vr

# Reset cache before each test
@pytest.fixture(autouse=True)
def reset_cache():
    vr._muse_cache = None
    yield
    vr._muse_cache = None

class TestMuseStatus:
    def test_no_key(self, monkeypatch):
        monkeypatch.delenv("META_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("DEMO_MODE", raising=False)
        # Need to reset module-level os.environ check
        with patch.dict(os.environ, {}, clear=True):
            vr._muse_cache = None
            # Direct import to get fresh module
            import importlib
            importlib.reload(vr)
            response = pytest.mark.asyncio(lambda: vr.muse_status())
            # For async, use asyncio
            import asyncio
            result = asyncio.run(vr.muse_status())
            assert result["muse_active"] is False
            assert result["state"] == "no_key"

    def test_demo_mode(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "1")
        import asyncio
        result = asyncio.run(vr.muse_status())
        assert result["muse_active"] is False
        assert result["state"] == "demo"

    def test_invalid_key(self, monkeypatch):
        monkeypatch.setenv("META_API_KEY", "invalid123")
        monkeypatch.delenv("DEMO_MODE", raising=False)
        import asyncio
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(side_effect=Exception("401 Unauthorized: Invalid API key"))
            mock_chat.return_value = mock_instance
            result = asyncio.run(vr.muse_status())
            assert result["muse_active"] is False
            assert result["state"] == "invalid_key"

    def test_unreachable(self, monkeypatch):
        monkeypatch.setenv("META_API_KEY", "validkey123")
        monkeypatch.delenv("DEMO_MODE", raising=False)
        import asyncio
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(side_effect=Exception("Connection timeout: Connection refused"))
            mock_chat.return_value = mock_instance
            result = asyncio.run(vr.muse_status())
            assert result["muse_active"] is False
            assert result["state"] == "unreachable"

    def test_live_success(self, monkeypatch):
        monkeypatch.setenv("META_API_KEY", "validkey123")
        monkeypatch.delenv("DEMO_MODE", raising=False)
        import asyncio
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_chat.return_value = mock_instance
            result = asyncio.run(vr.muse_status())
            assert result["muse_active"] is True
            assert result["state"] == "live"
            assert result["model"] == "muse-spark-1.3"

    def test_cache_behavior(self, monkeypatch):
        monkeypatch.setenv("META_API_KEY", "validkey123")
        monkeypatch.delenv("DEMO_MODE", raising=False)
        import asyncio
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_chat.return_value = mock_instance
            # First call
            result1 = asyncio.run(vr.muse_status())
            assert result1["state"] == "live"
            # Second call should use cache (ChatOpenAI constructor called only once)
            result2 = asyncio.run(vr.muse_status())
            assert result2["state"] == "live"
            assert mock_chat.call_count == 1

    def test_response_never_contains_key(self, monkeypatch):
        monkeypatch.setenv("META_API_KEY", "supersecretkey123")
        monkeypatch.delenv("DEMO_MODE", raising=False)
        import asyncio
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=MagicMock(content="pong"))
            mock_chat.return_value = mock_instance
            result = asyncio.run(vr.muse_status())
            # Ensure the key string doesn't appear anywhere in the response
            result_str = str(result)
            assert "supersecretkey123" not in result_str
            assert "META_API_KEY" not in result_str