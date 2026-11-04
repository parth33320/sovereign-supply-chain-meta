import os
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

DB_PATH = os.environ.get("PORTFOLIO_DB_PATH", "portfolio.db")

@dataclass
class Initiative:
    id: str           # e.g. "Q4-COST"
    title: str        # "Cut procurement costs 20%"
    owner: str        # "CEO"
    target_saving_usd: float
    deadline: str     # "2024-12-31"
    status: str       # "active|complete|at_risk"

@dataclass
class WorkItem:
    id: str
    initiative_id: str
    title: str
    wsjf_score: float   # (Business Value + Time Criticality + Risk) / Job Size
    story_points: int
    status: str         # "backlog|in_progress|done"
    actual_saving_usd: float = 0.0
    agent_actions: list[str] = field(default_factory=list)
    target_saving_usd: float = 0.0

def calculate_wsjf(business_value: float, time_criticality: float, risk: float, job_size: float) -> float:
    """
    Calculate Weighted Shortest Job First (WSJF) score.
    Formula: (Business Value + Time Criticality + Risk) / Job Size
    """
    if job_size == 0:
        return 0.0
    return float((business_value + time_criticality + risk) / job_size)

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or os.environ.get("PORTFOLIO_DB_PATH", DB_PATH)
    conn = sqlite3.connect(path, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_portfolio_db(db_path: Optional[str] = None):
    """
    Initialize SQLite tables for initiatives, work items, and agent actions.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS initiatives (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            owner TEXT NOT NULL,
            target_saving_usd REAL NOT NULL,
            deadline TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_items (
            id TEXT PRIMARY KEY,
            initiative_id TEXT NOT NULL,
            title TEXT NOT NULL,
            wsjf_score REAL NOT NULL,
            story_points INTEGER NOT NULL,
            status TEXT NOT NULL,
            actual_saving_usd REAL DEFAULT 0.0,
            target_saving_usd REAL DEFAULT 0.0,
            agent_actions TEXT DEFAULT '[]',
            FOREIGN KEY (initiative_id) REFERENCES initiatives (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_item_id TEXT NOT NULL,
            action_description TEXT NOT NULL,
            saving_usd REAL DEFAULT 0.0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (work_item_id) REFERENCES work_items (id)
        )
    """)

    conn.commit()

    # Pre-seed if DEMO_MODE or if table is empty in DEMO_MODE
    demo_mode = os.environ.get("DEMO_MODE") == "1"
    cursor.execute("SELECT COUNT(*) FROM initiatives")
    init_count = cursor.fetchone()[0]

    if demo_mode and init_count == 0:
        seed_demo_data(conn)

    conn.close()

def seed_demo_data(conn: sqlite3.Connection):
    cursor = conn.cursor()
    # Initiative: "Q4-COST — Cut procurement costs 20% — target $50,000"
    init_id = "Q4-COST"
    cursor.execute("""
        INSERT OR REPLACE INTO initiatives (id, title, owner, target_saving_usd, deadline, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (init_id, "Q4-COST — Cut procurement costs 20%", "CEO", 50000.0, "2024-12-31", "active"))

    # Work items (WSJF ranked):
    # 1. Demand Forecast Widget-A   WSJF=12.5  status=done   saved=$8,000
    # 2. Supplier Negotiation PO-99 WSJF=11.0  status=done   saved=$4,200
    # 3. Disruption Buffer Stock    WSJF=8.5   status=in_progress saved=$0
    # 4. Carrier Rate Audit         WSJF=6.0   status=backlog saved=$0
    demo_items = [
        ("WI-101", init_id, "Demand Forecast Widget-A", 12.5, 5, "done", 8000.0, 15000.0, json.dumps(["Demand forecasting automated"])),
        ("WI-102", init_id, "Supplier Negotiation PO-99", 11.0, 4, "done", 4200.0, 15000.0, json.dumps(["Supplier quote renegotiated"])),
        ("WI-103", init_id, "Disruption Buffer Stock", 8.5, 6, "in_progress", 0.0, 10000.0, json.dumps([])),
        ("WI-104", init_id, "Carrier Rate Audit", 6.0, 3, "backlog", 0.0, 10000.0, json.dumps([])),
    ]

    for item_id, i_id, title, wsjf, sp, status, saved, target_saved, actions in demo_items:
        cursor.execute("""
            INSERT OR REPLACE INTO work_items (id, initiative_id, title, wsjf_score, story_points, status, actual_saving_usd, target_saving_usd, agent_actions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, i_id, title, wsjf, sp, status, saved, target_saved, actions))

    conn.commit()

def create_initiative(title: str, target_saving_usd: float, deadline: str, owner: str = "CEO", status: str = "active", initiative_id: Optional[str] = None) -> Initiative:
    conn = get_connection()
    cursor = conn.cursor()
    if not initiative_id:
        initiative_id = f"INIT-{uuid.uuid4().hex[:6].upper()}"
    cursor.execute("""
        INSERT OR REPLACE INTO initiatives (id, title, owner, target_saving_usd, deadline, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (initiative_id, title, owner, float(target_saving_usd), deadline, status))
    conn.commit()
    conn.close()
    return Initiative(
        id=initiative_id,
        title=title,
        owner=owner,
        target_saving_usd=float(target_saving_usd),
        deadline=deadline,
        status=status
    )

def add_work_item(
    initiative_id: str,
    title: str,
    business_value: float,
    time_criticality: float,
    risk: float,
    job_size: float,
    story_points: int = 3,
    status: str = "backlog",
    target_saving_usd: float = 0.0,
    work_item_id: Optional[str] = None
) -> WorkItem:
    conn = get_connection()
    cursor = conn.cursor()
    if not work_item_id:
        work_item_id = f"WI-{uuid.uuid4().hex[:6].upper()}"

    wsjf_score = calculate_wsjf(business_value, time_criticality, risk, job_size)

    # If target_saving_usd is 0, infer proportional from initiative target or default
    if target_saving_usd == 0.0:
        cursor.execute("SELECT target_saving_usd FROM initiatives WHERE id = ?", (initiative_id,))
        row = cursor.fetchone()
        if row and row["target_saving_usd"]:
            target_saving_usd = row["target_saving_usd"] / 4.0
        else:
            target_saving_usd = 10000.0

    cursor.execute("""
        INSERT OR REPLACE INTO work_items (id, initiative_id, title, wsjf_score, story_points, status, actual_saving_usd, target_saving_usd, agent_actions)
        VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, '[]')
    """, (work_item_id, initiative_id, title, wsjf_score, int(story_points), status, float(target_saving_usd)))
    conn.commit()
    conn.close()

    return WorkItem(
        id=work_item_id,
        initiative_id=initiative_id,
        title=title,
        wsjf_score=wsjf_score,
        story_points=int(story_points),
        status=status,
        actual_saving_usd=0.0,
        agent_actions=[],
        target_saving_usd=float(target_saving_usd)
    )

def get_wsjf_ranked_backlog(initiative_id: Optional[str] = None) -> List[WorkItem]:
    conn = get_connection()
    cursor = conn.cursor()
    if initiative_id:
        cursor.execute("""
            SELECT * FROM work_items
            WHERE initiative_id = ?
            ORDER BY wsjf_score DESC
        """, (initiative_id,))
    else:
        cursor.execute("""
            SELECT * FROM work_items
            ORDER BY wsjf_score DESC
        """)
    rows = cursor.fetchall()
    conn.close()

    items = []
    for r in rows:
        try:
            actions = json.loads(r["agent_actions"]) if r["agent_actions"] else []
        except Exception:
            actions = []
        items.append(
            WorkItem(
                id=r["id"],
                initiative_id=r["initiative_id"],
                title=r["title"],
                wsjf_score=float(r["wsjf_score"]),
                story_points=int(r["story_points"]),
                status=r["status"],
                actual_saving_usd=float(r["actual_saving_usd"]),
                agent_actions=actions,
                target_saving_usd=float(r["target_saving_usd"])
            )
        )
    return items

def record_agent_action(work_item_id: str, action_description: str, saving_usd: float = 0.0):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO agent_actions (work_item_id, action_description, saving_usd)
        VALUES (?, ?, ?)
    """, (work_item_id, action_description, float(saving_usd)))

    # Fetch current item
    cursor.execute("SELECT actual_saving_usd, agent_actions FROM work_items WHERE id = ?", (work_item_id,))
    row = cursor.fetchone()
    if row:
        curr_saved = float(row["actual_saving_usd"] or 0.0) + float(saving_usd)
        try:
            actions = json.loads(row["agent_actions"]) if row["agent_actions"] else []
        except Exception:
            actions = []
        actions.append(action_description)

        cursor.execute("""
            UPDATE work_items
            SET actual_saving_usd = ?, agent_actions = ?
            WHERE id = ?
        """, (curr_saved, json.dumps(actions), work_item_id))

    conn.commit()
    conn.close()

def get_evms_snapshot(initiative_id: str) -> Dict[str, float]:
    """
    Returns: {
      "planned_value": float,      # sum of all work items' target savings
      "earned_value": float,       # sum of DONE work items' actual savings
      "actual_cost": float,        # hours_spent * $150/hr (use story_points * 2hrs)
      "schedule_variance": float,  # EV - PV
      "cost_variance": float,      # EV - AC
      "spi": float,                # EV / PV (Schedule Performance Index)
      "cpi": float                 # EV / AC (Cost Performance Index)
    }
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM work_items WHERE initiative_id = ?", (initiative_id,))
    items = cursor.fetchall()

    cursor.execute("SELECT target_saving_usd FROM initiatives WHERE id = ?", (initiative_id,))
    init_row = cursor.fetchone()
    init_target = float(init_row["target_saving_usd"]) if init_row else 0.0

    conn.close()

    total_target_savings = sum(float(r["target_saving_usd"] or 0.0) for r in items)
    planned_value = total_target_savings if total_target_savings > 0 else init_target

    earned_value = sum(
        float(r["actual_saving_usd"] or 0.0)
        for r in items
        if str(r["status"]).lower() == "done"
    )

    # Actual cost: hours_spent * $150/hr (use story_points * 2hrs)
    # Story points of in-progress or done items or all items worked
    # For EVMS, actual cost is actual work spent: story_points * 2 hours * $150/hr
    total_sp = sum(int(r["story_points"] or 0) for r in items if str(r["status"]).lower() in ["done", "in_progress"])
    if total_sp == 0 and items:
        total_sp = sum(int(r["story_points"] or 0) for r in items)

    actual_cost = float(total_sp * 2 * 150) # hours_spent * $150/hr

    schedule_variance = earned_value - planned_value
    cost_variance = earned_value - actual_cost

    spi = (earned_value / planned_value) if planned_value > 0 else 1.0
    cpi = (earned_value / actual_cost) if actual_cost > 0 else 1.0

    return {
        "planned_value": planned_value,
        "earned_value": earned_value,
        "actual_cost": actual_cost,
        "schedule_variance": schedule_variance,
        "cost_variance": cost_variance,
        "spi": round(spi, 3),
        "cpi": round(cpi, 3)
    }

# Initialize on import
init_portfolio_db()
