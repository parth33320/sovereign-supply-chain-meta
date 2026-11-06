from api_resilience import with_rate_limit_retry
"""
Warehouse Vision Module (S10)
=============================
Provides warehouse shelf image analysis, item segmentation, and fill-level estimation
powered by Meta API models (SAM 3.1 with fallback to muse-spark-1.3).

Inputs and Outputs:
- Input: image_bytes (bytes)
- Output: dict
    {
        "items": [
            {
                "item": str,
                "fill_level": float, # 0.0 to 1.0
                "status": "low" | "ok" | "empty"
            }
        ],
        "summary": str
    }
"""

import base64
import json
import logging
import os
import re
from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def _parse_llm_response(content: str) -> Dict[str, Any]:
    """
    Parses LLM response content into structured shelf analysis output.
    """
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "items" in data and "summary" in data:
            # Validate and normalize item formats
            normalized_items = []
            for item in data.get("items", []):
                item_name = str(item.get("item", "Unknown Item"))
                try:
                    fill_level = float(item.get("fill_level", 0.0))
                except (ValueError, TypeError):
                    fill_level = 0.0

                status = str(item.get("status", "ok")).lower()
                if status not in ("low", "ok", "empty"):
                    if fill_level <= 0.05:
                        status = "empty"
                    elif fill_level < 0.3:
                        status = "low"
                    else:
                        status = "ok"

                normalized_items.append({
                    "item": item_name,
                    "fill_level": fill_level,
                    "status": status
                })

            return {
                "items": normalized_items,
                "summary": str(data.get("summary", ""))
            }
    except Exception as e:
        logger.warning(f"Could not parse structured JSON from vision model: {e}. Raw content: {content}")

    # Fallback structure if JSON parsing fails
    return {
        "items": [],
        "summary": content.strip()
    }


@with_rate_limit_retry(max_retries=3, base_delay=2)
def analyze_shelf_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Analyzes a warehouse shelf image using SAM 3.1 via Meta API.
    If the sam-3.1 model fails (e.g., 404 or unsupported), falls back to muse-spark-1.3.

    Inputs:
        image_bytes (bytes): Raw bytes of the shelf image.

    Outputs:
        Dict[str, Any]:
            {
                "items": [{"item": str, "fill_level": float, "status": "low"|"ok"|"empty"}],
                "summary": str
            }

    Raises:
        ValueError: If image_bytes is empty or invalid.
    """
    if not image_bytes or not isinstance(image_bytes, (bytes, bytearray)):
        raise ValueError("Invalid or empty image bytes provided for shelf analysis.")

    api_key = os.environ.get("META_API_KEY")
    base_url = os.environ.get("META_API_BASE_URL", "https://api.meta.ai/v1")

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{base64_image}"

    prompt_text = (
        "You are an expert warehouse inventory computer vision model analyzing a shelf image.\n"
        "Identify and segment all detected items/products on the shelf.\n"
        "For each detected item, determine:\n"
        "1. 'item': item name or category\n"
        "2. 'fill_level': estimated capacity fill percentage as a float between 0.0 and 1.0\n"
        "3. 'status': 'low' (fill_level < 0.3), 'ok' (fill_level >= 0.3), or 'empty' (fill_level == 0.0)\n\n"
        "Provide a concise summary string describing overall shelf state.\n"
        "Respond ONLY with valid JSON in this exact structure:\n"
        "{\n"
        '  "items": [\n'
        '    {"item": "Item Name", "fill_level": 0.5, "status": "ok"}\n'
        "  ],\n"
        '  "summary": "Brief summary of shelf fill and detected items"\n'
        "}"
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": data_url}
            }
        ]
    )

    # First attempt: SAM 3.1
    try:
        llm = ChatOpenAI(
            model="sam-3.1",
            api_key=api_key,
            base_url=base_url,
            temperature=0
        )
        response = llm.invoke([message])
        return _parse_llm_response(response.content)
    except Exception as exc:
        logger.warning(f"SAM 3.1 model call failed ({exc}). Falling back to muse-spark-1.3.")

    # Fallback attempt: muse-spark-1.3
    try:
        fallback_model = os.environ.get("META_MODEL_NAME", "muse-spark-1.3")
        llm_fallback = ChatOpenAI(
            model=fallback_model,
            api_key=api_key,
            base_url=base_url,
            temperature=0
        )
        response = llm_fallback.invoke([message])
        return _parse_llm_response(response.content)
    except Exception as exc:
        logger.error(f"Fallback vision model call failed: {exc}")
        return {
            "items": [],
            "summary": f"Vision analysis error: {str(exc)}"
        }
