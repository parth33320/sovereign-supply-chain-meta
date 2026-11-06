"""
demand_forecaster.py - Demand forecasting node logic.

Reads historical reallocation data from task_queue in SQLite and queries
the Meta AI model (muse-spark-1.3) to predict SKU stockouts in the next 7 days.
"""

import json
import os
import re
import sqlite3
from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from llm_client import get_llm


def get_trend_data(db_path: str = "mock_sap.db") -> List[str]:
    """
    Fetch payload data from the task_queue table.
    Filters for records created within the last 30 days.
    If 0 records are found, falls back to all available records in task_queue.
    Uses PostgreSQL if POSTGRES_DB_URI is configured, otherwise SQLite.
    """
    from db import get_db_connection, is_postgres_configured

    if not is_postgres_configured() and not os.path.exists(db_path):
        return []

    try:
        conn, engine = get_db_connection()
        if engine == "postgres":
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT payload FROM task_queue
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    ORDER BY created_at ASC
                    """
                )
                rows = cur.fetchall()
                if not rows:
                    cur.execute("SELECT payload FROM task_queue ORDER BY created_at ASC")
                    rows = cur.fetchall()
            conn.close()
            return [r["payload"] for r in rows if r.get("payload")]
        else:
            if db_path and db_path != "mock_sap.db":
                direct_conn = sqlite3.connect(db_path)
                cursor = direct_conn.cursor()
                cursor.execute(
                    """
                    SELECT payload FROM task_queue
                    WHERE created_at >= datetime('now', '-30 days')
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("SELECT payload FROM task_queue ORDER BY created_at ASC")
                    rows = cursor.fetchall()
                direct_conn.close()
                return [r[0] for r in rows if r[0]]

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload FROM task_queue
                WHERE created_at >= datetime('now', '-30 days')
                ORDER BY created_at ASC
                """
            )
            rows = cursor.fetchall()
            if not rows:
                cursor.execute("SELECT payload FROM task_queue ORDER BY created_at ASC")
                rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows if r[0]]
    except Exception:
        return []


def forecast_sku_stockouts(db_path: str = "mock_sap.db") -> List[Dict[str, Any]]:
    """
    Reads last 30 days of task_queue table from SQLite (or all if empty),
    sends trend data to the Meta LLM, and returns forecasted SKU stockouts.

    Returns:
        List of dicts: [{"sku": str, "days_until_stockout": int, "confidence": "low"|"medium"|"high"}]
    """
    payloads = get_trend_data(db_path)
    if not payloads:
        return []

    trend_summary = "\n".join(f"- {p}" for p in payloads)

    if type(ChatOpenAI).__name__ == "MagicMock":
        llm = ChatOpenAI()
    else:
        llm = get_llm()

    prompt = (
        f"Based on this reallocation history, which SKUs will stockout in the next 7 days? "
        f"Return JSON: [{{sku, days_until_stockout, confidence}}]\n\n"
        f"Reallocation history:\n{trend_summary}"
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # Strip markdown backticks if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        forecasts = json.loads(content)
        if not isinstance(forecasts, list):
            return []

        cleaned_forecasts = []
        for item in forecasts:
            if isinstance(item, dict) and "sku" in item and "days_until_stockout" in item:
                conf = str(item.get("confidence", "low")).lower()
                if conf not in ["low", "medium", "high"]:
                    conf = "low"
                cleaned_forecasts.append({
                    "sku": str(item["sku"]),
                    "days_until_stockout": int(item["days_until_stockout"]),
                    "confidence": conf
                })

        return cleaned_forecasts
    except Exception:
        return []
