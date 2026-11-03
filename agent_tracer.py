import os
import sqlite3
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

DB_PATH = "agent_traces.db"

@dataclass
class AgentTrace:
    trace_id: str       # uuid4
    timestamp: str      # ISO format
    agent_name: str     # "global_oracle" | "forecast_demand" | "a2a_negotiate" | etc
    tenant_id: str
    input_summary: str  # first 200 chars of input
    output_summary: str # first 200 chars of output
    decision: str       # "PROCEED" | "ESCALATE" | "REJECT"
    saving_usd: float   # 0.0 if unknown
    latency_ms: int
    model_used: str     # from META_MODEL_NAME env var

def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_tracer_db():
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_traces (
                trace_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                input_summary TEXT NOT NULL,
                output_summary TEXT NOT NULL,
                decision TEXT NOT NULL,
                saving_usd REAL NOT NULL DEFAULT 0.0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                model_used TEXT NOT NULL
            )
        """)
        conn.commit()

def record_trace(
    agent_name: str,
    tenant_id: str,
    input_text: Any,
    output_text: Any,
    decision: str = "PROCEED",
    saving_usd: float = 0.0,
    latency_ms: int = 0
) -> AgentTrace:
    init_tracer_db()
    trace_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    model_used = os.environ.get("META_MODEL_NAME", "muse-spark-1.3")

    input_summary = str(input_text)[:200]
    output_summary = str(output_text)[:200]

    trace = AgentTrace(
        trace_id=trace_id,
        timestamp=timestamp,
        agent_name=agent_name,
        tenant_id=tenant_id,
        input_summary=input_summary,
        output_summary=output_summary,
        decision=decision,
        saving_usd=float(saving_usd or 0.0),
        latency_ms=int(latency_ms or 0),
        model_used=model_used
    )

    with _get_db() as conn:
        conn.execute("""
            INSERT INTO agent_traces (
                trace_id, timestamp, agent_name, tenant_id,
                input_summary, output_summary, decision,
                saving_usd, latency_ms, model_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace.trace_id,
            trace.timestamp,
            trace.agent_name,
            trace.tenant_id,
            trace.input_summary,
            trace.output_summary,
            trace.decision,
            trace.saving_usd,
            trace.latency_ms,
            trace.model_used
        ))
        conn.commit()

    return trace

def get_traces(tenant_id: Optional[str] = None, limit: int = 50) -> List[AgentTrace]:
    init_tracer_db()
    with _get_db() as conn:
        if tenant_id:
            cursor = conn.execute("""
                SELECT * FROM agent_traces
                WHERE tenant_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (tenant_id, limit))
        else:
            cursor = conn.execute("""
                SELECT * FROM agent_traces
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()

    traces = []
    for row in rows:
        traces.append(AgentTrace(
            trace_id=row["trace_id"],
            timestamp=row["timestamp"],
            agent_name=row["agent_name"],
            tenant_id=row["tenant_id"],
            input_summary=row["input_summary"],
            output_summary=row["output_summary"],
            decision=row["decision"],
            saving_usd=row["saving_usd"],
            latency_ms=row["latency_ms"],
            model_used=row["model_used"]
        ))
    return traces

def get_agent_stats(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    init_tracer_db()
    with _get_db() as conn:
        if tenant_id:
            cursor = conn.execute("""
                SELECT agent_name, decision, saving_usd, latency_ms
                FROM agent_traces
                WHERE tenant_id = ?
            """, (tenant_id,))
        else:
            cursor = conn.execute("""
                SELECT agent_name, decision, saving_usd, latency_ms
                FROM agent_traces
            """)
        rows = cursor.fetchall()

    total_actions = len(rows)
    total_savings_usd = sum(row["saving_usd"] for row in rows)
    avg_latency_ms = (sum(row["latency_ms"] for row in rows) / total_actions) if total_actions > 0 else 0.0

    decisions = {"PROCEED": 0, "ESCALATE": 0, "REJECT": 0}
    by_agent: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        dec = row["decision"]
        if dec in decisions:
            decisions[dec] += 1
        else:
            decisions[dec] = 1

        agent = row["agent_name"]
        if agent not in by_agent:
            by_agent[agent] = {"count": 0, "savings": 0.0}
        by_agent[agent]["count"] += 1
        by_agent[agent]["savings"] += row["saving_usd"]

    return {
        "total_actions": total_actions,
        "total_savings_usd": round(total_savings_usd, 2),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "decisions": decisions,
        "by_agent": by_agent
    }

def seed_demo_traces():
    """
    DEMO_MODE: pre-seed agent_traces.db with 20 realistic trace records across
    the 7 node types showing a mix of PROCEED/ESCALATE decisions and $savings.
    """
    init_tracer_db()
    with _get_db() as conn:
        conn.execute("DELETE FROM agent_traces")
        conn.commit()

    sample_nodes = [
        # (agent_name, input_text, output_text, decision, saving_usd, latency_ms)
        ("global_oracle", "Disruption scan maritime RSS feed", "Red Sea shipping lane congestion alert synthesized", "PROCEED", 1250.00, 340),
        ("forecast_demand", "SKU-STEEL-BEAMS 30-day forecast", "Predicted stockout in 3 days with high confidence", "ESCALATE", 3400.00, 520),
        ("fetch_inventory", "Query SAP mock inventory for Tenant_A", "Found 5 inventory items, 1 item stocked out (qty=0)", "PROCEED", 0.0, 110),
        ("a2a_negotiate", "Buyer RFQ for 500 units SKU-STEEL-BEAMS", "Supplier quote received: $42.50/unit, 3 days lead time", "PROCEED", 2150.00, 890),
        ("draft_po", "Create PO from Supplier Agent quote", "Drafted PO-948201 with supplier Apex Logistics", "PROCEED", 0.0, 95),
        ("draft_plan", "Reallocate emergency stock from Hub-West to Hub-East", "Plan generated: optimal carrier dispatch with ETA 24h", "PROCEED", 4800.00, 610),
        ("execute_plan", "Dispatch approved reallocation plan", "Reallocation manifest dispatched to WMS execution layer", "PROCEED", 0.0, 230),

        ("global_oracle", "Rotterdam port strike monitoring", "Terminal delays expected +48 hours", "ESCALATE", 850.00, 290),
        ("forecast_demand", "SKU-COPPER-WIRE inventory exhaustion rate", "Adequate safety stock available, 45 days remaining", "PROCEED", 0.0, 480),
        ("fetch_inventory", "Check regional DC inventory levels", "Stock query returned 10 items in Tenant_A warehouse", "PROCEED", 0.0, 125),
        ("a2a_negotiate", "Supplier price negotiation for bulk Lithium Batteries", "Counter-offer rejected by supplier AI due to tariff surcharge", "REJECT", 0.0, 1150),
        ("draft_plan", "Alternate intermodal rail routing via Chicago", "Intermodal route scheduled: cost reduction $1,900", "PROCEED", 1900.00, 540),
        ("draft_po", "Draft expedited PO for Copper Wire replacement", "Purchase order drafted: PO-102938 for 2,000 lbs", "PROCEED", 0.0, 80),
        ("execute_plan", "Execute expedited freight booking", "Carrier confirmation received: Waybill #US-882910", "PROCEED", 600.00, 210),

        ("global_oracle", "Panama canal transit slot availability", "Draft restrictions causing 4-day transit delays", "ESCALATE", 2200.00, 310),
        ("forecast_demand", "Semiconductors lead-time variance model", "Lead time spiked from 14 to 28 days", "ESCALATE", 5100.00, 600),
        ("fetch_inventory", "Periodic stock audit for Tenant_A", "All stock levels synchronized with SAP core", "PROCEED", 0.0, 105),
        ("a2a_negotiate", "RFQ for replacement semiconductor microcontrollers", "Supplier AI accepted terms with 5% volume discount", "PROCEED", 3100.00, 920),
        ("draft_plan", "Air cargo charter versus ocean container reallocation", "Air cargo selected for critical production line continuity", "PROCEED", 7500.00, 580),
        ("execute_plan", "Finalize charter flight contract and manifest", "Charter flight cargo space confirmed and locked", "PROCEED", 1200.00, 190)
    ]

    for item in sample_nodes:
        record_trace(
            agent_name=item[0],
            tenant_id="Tenant_A",
            input_text=item[1],
            output_text=item[2],
            decision=item[3],
            saving_usd=item[4],
            latency_ms=item[5]
        )
