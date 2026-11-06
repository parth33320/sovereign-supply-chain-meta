import re
import html
import logging

logger = logging.getLogger(__name__)

MAX_PROMPT_LENGTH = 2000
MAX_FILE_SIZE_BYTES = 2_000_000
BLOCKED_PATTERNS = [
    r"<script.*?>.*?</script>",
    r"javascript:",
    r"data:text/html",
    r"vbscript:",
    r"onload\s*=",
    r"onerror\s*=",
]

IMAGE_MAGIC_BYTES = [
    b'\xff\xd8\xff',        # JPEG
    b'\x89PNG\r\n\x1a\n',   # PNG
    b'RIFF',                # WEBP
]

def sanitize_text_input(text: str) -> str:
    """Strip HTML tags and escape special chars from user input."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Escape remaining HTML entities
    text = html.escape(text)
    # Truncate to max length
    return text[:MAX_PROMPT_LENGTH]

def check_xss_patterns(text: str) -> bool:
    """Returns True if text is safe, False if XSS detected."""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            logger.warning(f"XSS pattern detected: {pattern}")
            return False
    return True

def validate_file_upload(file_bytes: bytes,
                          max_size: int = MAX_FILE_SIZE_BYTES,
                          allowed_magic: list = None) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Checks size and magic bytes.
    """
    if len(file_bytes) > max_size:
        return False, f"File too large: {len(file_bytes)//1024}KB > {max_size//1024}KB"

    if allowed_magic:
        if not any(file_bytes.startswith(m) for m in allowed_magic):
            return False, "Invalid file format"

    return True, ""
