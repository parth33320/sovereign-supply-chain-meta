import os
from langchain_openai import ChatOpenAI

import threading

_llm_instance = None
_llm_lock = threading.Lock()

def get_llm() -> ChatOpenAI:
    global _llm_instance
    if _llm_instance is None:
        with _llm_lock:
            if _llm_instance is None:
                api_key = os.environ.get("META_API_KEY") or os.environ.get("OPENAI_API_KEY") or "dummy_key"
                base_url = os.environ.get("META_API_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.meta.ai/v1"
                _llm_instance = ChatOpenAI(
                    model=os.environ.get("META_MODEL_NAME", "muse-spark-1.3"),
                    api_key=api_key,
                    base_url=base_url,
                    temperature=0,
                    request_timeout=30,
                    max_retries=2,
                )
    return _llm_instance
