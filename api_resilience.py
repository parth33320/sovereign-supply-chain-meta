import time
import logging
import requests
from functools import wraps

logger = logging.getLogger(__name__)

def with_rate_limit_retry(max_retries=3, base_delay=2):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    err_str = str(e)
                    # Rate limit
                    if "429" in err_str or "rate" in err_str.lower():
                        wait = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limited. Waiting {wait}s "
                            f"(attempt {attempt+1}/{max_retries})"
                        )
                        time.sleep(wait)
                        continue
                    # Service unavailable
                    if "503" in err_str or "502" in err_str:
                        wait = base_delay * (attempt + 1)
                        logger.warning(
                            f"Service unavailable. Waiting {wait}s"
                        )
                        time.sleep(wait)
                        continue
                    # Auth error - don't retry
                    if "401" in err_str or "403" in err_str:
                        raise Exception(
                            "API authentication failed. "
                            "Check your META_API_KEY."
                        ) from e
                    # Other errors - raise immediately
                    raise
            raise Exception(
                f"API call failed after {max_retries} attempts. "
                "Meta AI may be temporarily unavailable."
            )
        return wrapper
    return decorator
