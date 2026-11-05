import os
import re
import json
import time
import logging
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Dict, Any, List
import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from llm_client import get_llm

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://www.freightwaves.com/news/feed",
    "https://feeds.feedburner.com/SupplyChainBrain",
]

DEFAULT_FALLBACK = {
    "alert": False,
    "severity": "low",
    "summary": "No disruption data available.",
}

_disruption_cache = {"result": None, "ts": 0.0}
CACHE_TTL_SECONDS = 300  # 5 minutes

def fetch_disruption_alert() -> Dict[str, Any]:
    now = time.time()
    if _disruption_cache["result"] and (now - _disruption_cache["ts"]) < CACHE_TTL_SECONDS:
        return _disruption_cache["result"]
    result = _fetch_disruption_alert_uncached()
    _disruption_cache["result"] = result
    _disruption_cache["ts"] = now
    return result

def clear_disruption_cache():
    global _disruption_cache
    _disruption_cache["result"] = None
    _disruption_cache["ts"] = 0.0


def _fetch_feed_headlines(url: str, limit: int = 5) -> List[str]:
    """
    Fetches an RSS feed and extracts up to `limit` headlines and descriptions.
    """
    headers = {
        "User-Agent": "DisruptionRadar/1.0 (SupplyChainBot)"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    items = root.findall(".//item")
    headlines = []
    for item in items[:limit]:
        title = item.findtext("title") or ""
        description = item.findtext("description") or ""
        clean_desc = re.sub(r"<[^>]+>", "", description).strip()
        headline = f"Title: {title.strip()}"
        if clean_desc:
            headline += f" | Summary: {clean_desc[:200]}"
        headlines.append(headline)

    return headlines


def _clean_json_text(text: str) -> str:
    """
    Strips markdown code fences (e.g. ```json ... ```) and leading/trailing whitespace.
    """
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


def _fetch_disruption_alert_uncached() -> Dict[str, Any]:
    """
    Fetches supply chain RSS feeds, queries the Meta LLM for disruptions,
    and returns a structured alert dictionary:
    {"alert": bool, "severity": "low"|"medium"|"high", "summary": str}
    Total cap: 8 seconds max for all RSS fetches combined.
    """
    headlines: List[str] = []
    ex = ThreadPoolExecutor(max_workers=2)
    try:
        deadline = time.time() + 8
        futures = [ex.submit(_fetch_feed_headlines, url, 5) for url in RSS_FEEDS]
        for f in futures:
            remaining = max(0, deadline - time.time())
            try:
                headlines.extend(f.result(timeout=min(remaining, 8)))
            except Exception:
                pass
    except Exception:
        return dict(DEFAULT_FALLBACK)
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    if not headlines:
        return dict(DEFAULT_FALLBACK)

    try:
        system_prompt = """You are an expert supply chain risk analyst.
Analyze the following recent headlines from supply chain and freight news feeds to determine if there are significant ongoing disruptions (e.g., strikes, port closures, severe weather, canal blockages, capacity shortages, geopolitical blockades).

Headlines:
{headlines}

Instructions:
1. Return ONLY raw JSON (no explanations, no markdown formatting outside JSON).
2. The JSON object must have exactly these keys:
   - "alert": boolean (true if a significant disruption is actively threatening or occurring; false otherwise)
   - "severity": string ("low", "medium", or "high")
   - "summary": string (a concise summary of the active disruption or "No active disruptions detected.")
"""
        prompt_template = ChatPromptTemplate.from_template(system_prompt)
        prompt_messages = prompt_template.format_messages(headlines="\n".join(headlines))

        llm = get_llm()

        response = llm.invoke(prompt_messages)
        if hasattr(response, "content"):
            raw_content = response.content
        else:
            raw_content = str(response)

        cleaned_json = _clean_json_text(str(raw_content))
        parsed = json.loads(cleaned_json)

        # Validate expected keys and types
        if not isinstance(parsed, dict) or "alert" not in parsed or "severity" not in parsed or "summary" not in parsed:
            return dict(DEFAULT_FALLBACK)

        severity = str(parsed["severity"]).lower()
        if severity not in ["low", "medium", "high"]:
            severity = "low"

        return {
            "alert": bool(parsed["alert"]),
            "severity": severity,
            "summary": str(parsed["summary"]),
        }

    except Exception as e:
        logger.error(f"Failed to fetch disruption alert: {e}")
        return dict(DEFAULT_FALLBACK)
