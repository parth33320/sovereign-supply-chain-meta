from api_resilience import with_rate_limit_retry
"""
Document Vision Module (S11)
============================
Provides shipping document and invoice analysis powered by Meta API models
(primary: muse-image-1.0, with fallback to META_MODEL_NAME / muse-spark-1.3).

Inputs and Outputs:
- Input: image_bytes (bytes)
- Output: dict
    {
        "supplier": str,
        "items": [
            {
                "description": str,
                "quantity": float | int,
                "unit_price": float | None
            }
        ],
        "dates": list[str],
        "raw_summary": str
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


def _parse_document_response(content: str) -> Dict[str, Any]:
    """
    Parses LLM response content into structured document extraction output.
    """
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            supplier = str(data.get("supplier", "")).strip()

            dates_raw = data.get("dates", [])
            dates = [str(d).strip() for d in dates_raw if d] if isinstance(dates_raw, list) else []

            normalized_items = []
            for item in data.get("items", []):
                if isinstance(item, dict):
                    desc = str(item.get("description") or item.get("item") or "Item").strip()
                    try:
                        qty = float(item.get("quantity", 1))
                        if qty.is_integer():
                            qty = int(qty)
                    except (ValueError, TypeError):
                        qty = 1

                    unit_price = item.get("unit_price")
                    if unit_price is not None:
                        try:
                            unit_price = float(unit_price)
                        except (ValueError, TypeError):
                            unit_price = None

                    normalized_items.append({
                        "description": desc,
                        "quantity": qty,
                        "unit_price": unit_price
                    })

            raw_summary = str(data.get("raw_summary") or data.get("summary") or "").strip()

            return {
                "supplier": supplier,
                "items": normalized_items,
                "dates": dates,
                "raw_summary": raw_summary
            }
    except Exception as e:
        logger.warning(f"Could not parse structured JSON from document vision model: {e}. Raw content: {content}")

    return {
        "supplier": "",
        "items": [],
        "dates": [],
        "raw_summary": content.strip()
    }


@with_rate_limit_retry(max_retries=3, base_delay=2)
def extract_document_data(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts structured fields (supplier, items, quantities, dates) from an invoice
    or shipping document image using muse-image-1.0 via Meta API.
    Falls back to META_MODEL_NAME (default muse-spark-1.3) if muse-image-1.0 is unavailable.

    Inputs:
        image_bytes (bytes): Raw bytes of the document image.

    Outputs:
        Dict[str, Any]:
            {
                "supplier": str,
                "items": [{"description": str, "quantity": int|float, "unit_price": float|None}],
                "dates": list[str],
                "raw_summary": str
            }

    Raises:
        ValueError: If image_bytes is empty or invalid.
    """
    if not image_bytes or not isinstance(image_bytes, (bytes, bytearray)):
        raise ValueError("Invalid or empty image bytes provided for document analysis.")

    api_key = os.environ.get("META_API_KEY")
    base_url = os.environ.get("META_API_BASE_URL", "https://api.meta.ai/v1")

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{base64_image}"

    prompt_text = (
        "You are an expert OCR and procurement document extraction model analyzing a shipping document or invoice.\n"
        "Extract the following key logistics information:\n"
        "1. 'supplier': Name of the vendor, supplier, or shipper.\n"
        "2. 'dates': All relevant dates mentioned (e.g. invoice date, shipping date, delivery date, due date) as a list of strings.\n"
        "3. 'items': List of items or products. Each item must contain:\n"
        "   - 'description': Name or description of the product/part\n"
        "   - 'quantity': Quantity ordered/shipped as a number\n"
        "   - 'unit_price': Unit price if present, or null\n"
        "4. 'raw_summary': A concise one or two sentence summary of the document.\n\n"
        "Respond ONLY with valid JSON in this exact structure:\n"
        "{\n"
        '  "supplier": "Vendor Name",\n'
        '  "dates": ["2025-05-10"],\n'
        '  "items": [\n'
        '    {"description": "Part Name", "quantity": 10, "unit_price": 5.0}\n'
        "  ],\n"
        '  "raw_summary": "Invoice for parts from Vendor"\n'
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

    # Primary attempt: muse-image-1.0
    try:
        llm = ChatOpenAI(
            model="muse-image-1.0",
            api_key=api_key,
            base_url=base_url,
            temperature=0
        )
        response = llm.invoke([message])
        return _parse_document_response(response.content)
    except Exception as exc:
        logger.warning(f"muse-image-1.0 model call failed ({exc}). Falling back to META_MODEL_NAME.")

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
        return _parse_document_response(response.content)
    except Exception as exc:
        logger.error(f"Fallback document vision model call failed: {exc}")
        return {
            "supplier": "",
            "items": [],
            "dates": [],
            "raw_summary": f"Document extraction error: {str(exc)}"
        }


def format_logistics_instruction(extracted: Dict[str, Any]) -> str:
    """
    Generates a pre-populated logistics chat instruction from extracted document data.
    """
    supplier = extracted.get("supplier", "").strip()
    items = extracted.get("items", [])
    dates = extracted.get("dates", [])

    items_part = ""
    if items:
        item_strs = [f"{itm.get('quantity', 1)}x {itm.get('description', 'items')}" for itm in items]
        items_part = ", ".join(item_strs)

    dates_part = ""
    if dates:
        dates_part = f" dated {', '.join(dates)}"

    supplier_part = f" from {supplier}" if supplier else ""

    if items_part:
        return f"Process incoming shipment{supplier_part}: receive {items_part}{dates_part} into inventory."
    elif supplier:
        return f"Process incoming shipment{supplier_part}{dates_part} into inventory."
    else:
        return "Process incoming shipment into inventory."
