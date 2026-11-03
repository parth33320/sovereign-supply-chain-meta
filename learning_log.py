import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

DB_PATH = "dpo_log.db"

def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_learning_db():
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dpo_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                chosen_response TEXT NOT NULL,
                rejected_response TEXT NOT NULL,
                intent TEXT NOT NULL,
                feedback INTEGER NOT NULL
            )
        """)
        conn.commit()

def log_dpo_feedback(
    prompt: str,
    response: str,
    feedback: int = 1,
    tenant_id: str = "default",
    intent: str = "general",
    rejected_response: str = ""
):
    """
    Records a DPO feedback interaction.
    feedback: 1 for positive (thumbs up), -1 for negative (thumbs down)
    """
    init_learning_db()
    timestamp = datetime.now(timezone.utc).isoformat()
    chosen_resp = response if feedback > 0 else ""
    rejected_resp = response if feedback < 0 else rejected_response

    with _get_db() as conn:
        conn.execute("""
            INSERT INTO dpo_records (
                timestamp, tenant_id, prompt, chosen_response,
                rejected_response, intent, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            tenant_id,
            prompt,
            chosen_resp,
            rejected_resp,
            intent,
            1 if feedback > 0 else -1
        ))
        conn.commit()

def get_learning_stats(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns: {
      "total_feedback": int,
      "positive": int,
      "negative": int,
      "approval_rate": float,   # positive / total
      "weekly_trend": list[dict] # [{week: "2024-W45", rate: 0.82}, ...]
      "top_improved_intents": list[str]  # intents with most positive feedback
    }
    """
    init_learning_db()
    with _get_db() as conn:
        if tenant_id:
            cursor = conn.execute("""
                SELECT timestamp, intent, feedback
                FROM dpo_records
                WHERE tenant_id = ?
                ORDER BY timestamp ASC
            """, (tenant_id,))
        else:
            cursor = conn.execute("""
                SELECT timestamp, intent, feedback
                FROM dpo_records
                ORDER BY timestamp ASC
            """)
        rows = cursor.fetchall()

    total_feedback = len(rows)
    positive = sum(1 for r in rows if r["feedback"] > 0)
    negative = sum(1 for r in rows if r["feedback"] < 0)
    approval_rate = (positive / total_feedback) if total_feedback > 0 else 0.0

    # Calculate weekly trend
    weeks: Dict[str, Dict[str, int]] = {}
    intent_positives: Dict[str, int] = {}

    for r in rows:
        ts_str = r["timestamp"]
        try:
            # Parse ISO string
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            week_key = dt.strftime("%Y-W%W")
        except Exception:
            week_key = datetime.now(timezone.utc).strftime("%Y-W%W")

        if week_key not in weeks:
            weeks[week_key] = {"positive": 0, "total": 0}
        weeks[week_key]["total"] += 1
        if r["feedback"] > 0:
            weeks[week_key]["positive"] += 1

        # Track intent improvements
        intent = r["intent"]
        if r["feedback"] > 0:
            intent_positives[intent] = intent_positives.get(intent, 0) + 1

    weekly_trend = []
    for wk in sorted(weeks.keys()):
        w_total = weeks[wk]["total"]
        w_pos = weeks[wk]["positive"]
        rate = round(w_pos / w_total, 2) if w_total > 0 else 0.0
        weekly_trend.append({"week": wk, "rate": rate})

    if not weekly_trend:
        # Fallback if no records or no week
        cur_week = datetime.now(timezone.utc).strftime("%Y-W%W")
        weekly_trend.append({"week": cur_week, "rate": round(approval_rate, 2)})

    # Sort intents by positive count descending
    top_improved_intents = [
        item[0] for item in sorted(intent_positives.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "total_feedback": total_feedback,
        "positive": positive,
        "negative": negative,
        "approval_rate": round(approval_rate, 2),
        "weekly_trend": weekly_trend,
        "top_improved_intents": top_improved_intents
    }

def seed_demo_feedback():
    """
    Pre-seed dpo_log.db with 15 feedback records (12 positive, 3 negative) showing
    80% approval rate.
    """
    init_learning_db()
    with _get_db() as conn:
        conn.execute("DELETE FROM dpo_records")
        conn.commit()

    # Create 15 records across recent weeks
    # 12 positive, 3 negative = 80% approval rate
    samples = [
        ("Reallocate 500 units Copper Wire to Chicago", "Carrier route plan created with 24h transit time.", 1, "Tenant_A", "reallocation", "2025-02-03T10:00:00+00:00"),
        ("Check Rotterdam strike impact", "Disruption analysis: 48h delay on Antwerp route.", 1, "Tenant_A", "disruption_radar", "2025-02-04T11:00:00+00:00"),
        ("Order 200 microcontrollers", "PO-99210 drafted for Apex Micro.", 1, "Tenant_A", "procurement", "2025-02-05T09:30:00+00:00"),
        ("Optimize air freight routing", "Selected chartered 747 cargo flight.", -1, "Tenant_A", "route_optimization", "2025-02-06T14:15:00+00:00"),

        ("Demand forecast for Lithium Batteries", "Stockout predicted in 8 days. Safety buffer suggested.", 1, "Tenant_A", "forecasting", "2025-02-10T08:00:00+00:00"),
        ("Restock Steel Plates 10k tons", "Supplier RFQ sent to US Steel.", 1, "Tenant_A", "procurement", "2025-02-11T12:00:00+00:00"),
        ("Expedite shipment #US-882", "Driver dispatched with hot-shot trailer.", 1, "Tenant_A", "reallocation", "2025-02-12T16:45:00+00:00"),
        ("Find alternate supplier for resin", "Proposed supplier rejected due to unverified ISO cert.", -1, "Tenant_A", "supplier_evaluation", "2025-02-13T17:20:00+00:00"),

        ("Draft multi-hub transfer", "Balanced inventory across West and East hubs.", 1, "Tenant_A", "reallocation", "2025-02-17T09:00:00+00:00"),
        ("Query SAP mock database", "Inventory status fetched in 85ms.", 1, "Tenant_A", "inventory_query", "2025-02-18T10:10:00+00:00"),
        ("A2A Restock negotiation", "Supplier agreed to $42.50 per unit.", 1, "Tenant_A", "a2a_negotiate", "2025-02-19T11:30:00+00:00"),
        ("Analyze shelf camera feed", "SKU-PLASTIC-CASING identified as 20% empty.", 1, "Tenant_A", "warehouse_vision", "2025-02-20T13:40:00+00:00"),

        ("Generate synthetic warehouse load", "Load injected at 15 req/sec.", 1, "Tenant_A", "load_testing", "2025-02-24T09:00:00+00:00"),
        ("Emergency container repositioning", "Plan suggested rail route that was blocked.", -1, "Tenant_A", "route_optimization", "2025-02-25T15:00:00+00:00"),
        ("Voice dispatch warehouse forklift", "Voice command transcribed: move pallet 4B.", 1, "Tenant_A", "voice_dispatch", "2025-02-26T16:00:00+00:00"),
    ]

    with _get_db() as conn:
        for p, resp, fb, ten, intent, ts in samples:
            chosen = resp if fb > 0 else ""
            rejected = resp if fb < 0 else ""
            conn.execute("""
                INSERT INTO dpo_records (
                    timestamp, tenant_id, prompt, chosen_response,
                    rejected_response, intent, feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ts, ten, p, chosen, rejected, intent, fb))
        conn.commit()
