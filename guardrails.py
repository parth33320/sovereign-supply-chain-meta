import os
import re
import logging
from langchain_openai import ChatOpenAI
from llm_client import get_llm

logger = logging.getLogger("Guardrails")

MALICIOUS_PATTERNS = [
    r"ignore previous instructions",
    r"disregard all prior instructions",
    r"forget everything",
    r"you are now an unrestricted",
    r"system prompt",
    r"jailbreak",
    r"bypass rules",
    r"reveal all api keys",
    r"\[\[injection\]\]",
    r"drop table",
    r"print the contents of your \.env",
    r"without restriction",
    r"admin access to the database",
    r"repeat (?:back )?(?:your )?(?:system |previous )?(?:prompt|instructions)",
    r"what (?:were|are) your instructions",
    r"print (?:your )?(?:full )?(?:context|prompt|system)",
    r"output (?:your )?(?:initial|original) (?:prompt|instructions)",
    r"act as (?:if you have )?no restrictions",
    r"pretend you (?:are|have) no",
    r"dan mode",
    r"developer mode",
    r"sudo\s",
    r"<\s*script",
    r"javascript:",
]

def check_prompt_injection(prompt: str) -> bool:
    """
    Semantic Bouncer
    Intercepts the user's prompt before LangGraph sees it.
    1. Fast regex pre-filter for known attack patterns.
    2. Meta LLM semantic classification for subtle injections.

    Returns True if the prompt is safe, False if malicious.
    """
    # 1. Fast regex pre-filter
    lower_prompt = prompt.lower()
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, lower_prompt):
            logger.info("Blocked prompt via regex pattern match.")
            return False

    # 2. LLM Semantic similarity/injection check
    api_key = os.environ.get("META_API_KEY")
    base_url = os.environ.get("META_API_BASE_URL")
    model_name = os.environ.get("META_MODEL_NAME", "muse-spark-1.3")

    if not api_key or not base_url:
        logger.warning("Meta API credentials not configured; skipping LLM semantic guardrail check.")
        return True

    try:
        llm = get_llm()
        query = (
            f"Is this prompt a malicious injection attack? Reply only YES or NO.\n\n"
            f"Prompt: {prompt}"
        )
        response = llm.invoke(query)
        content = (response.content or "").strip().upper()

        if "YES" in content:
            logger.info("Blocked prompt via LLM semantic injection check.")
            return False

        return True
    except Exception as e:
        logger.error(f"LLM guardrail check failed: {e}. Failing closed.")
        return False  # CHANGED from True to False
