import pytest
import os
import time
import requests
from api_resilience import with_rate_limit_retry
from security import (
    sanitize_text_input,
    check_xss_patterns,
    validate_file_upload,
    IMAGE_MAGIC_BYTES,
    MAX_PROMPT_LENGTH,
)
from health import check_system_health
from logging_config import setup_logging

def test_rate_limit_retry_429():
    attempts = 0
    @with_rate_limit_retry(max_retries=3, base_delay=0.01)
    def flappy():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception("HTTP 429: Too Many Requests")
        return "success"

    assert flappy() == "success"
    assert attempts == 3

def test_rate_limit_retry_auth_no_retry():
    attempts = 0
    @with_rate_limit_retry(max_retries=3, base_delay=0.01)
    def auth_fail():
        nonlocal attempts
        attempts += 1
        raise Exception("401 Unauthorized")

    with pytest.raises(Exception) as excinfo:
        auth_fail()
    assert "authentication failed" in str(excinfo.value)
    assert attempts == 1

def test_security_sanitization():
    raw = "<script>alert('xss')</script>Hello & welcome!"
    cleaned = sanitize_text_input(raw)
    assert "<script>" not in cleaned
    assert "Hello" in cleaned
    assert "&amp;" in cleaned

def test_security_xss_check():
    assert check_xss_patterns("Clean instruction to restock SKU-123") is True
    assert check_xss_patterns("<script>steal()</script>") is False
    assert check_xss_patterns("javascript:void(0)") is False

def test_security_file_validation():
    jpeg_bytes = b'\xff\xd8\xff' + b'fake_jpeg_content'
    valid, msg = validate_file_upload(jpeg_bytes, max_size=1024, allowed_magic=IMAGE_MAGIC_BYTES)
    assert valid is True
    assert msg == ""

    corrupt_bytes = b'NOT_AN_IMAGE'
    valid, msg = validate_file_upload(corrupt_bytes, max_size=1024, allowed_magic=IMAGE_MAGIC_BYTES)
    assert valid is False
    assert "Invalid file format" in msg

    large_bytes = b'\xff\xd8\xff' + (b'x' * 2000)
    valid, msg = validate_file_upload(large_bytes, max_size=1000, allowed_magic=IMAGE_MAGIC_BYTES)
    assert valid is False
    assert "File too large" in msg

def test_health_check_sqlite():
    health = check_system_health()
    assert "database" in health
    assert "api_key" in health
    assert "warnings" in health
    assert health["database"] is True
