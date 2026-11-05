import streamlit as st
import sqlite3
import json
import uuid
import time
import os
import re
import pandas as pd
from dotenv import load_dotenv

from guardrails import check_prompt_injection
from voice_handler import process_voice_input
from warehouse_vision import analyze_shelf_image
from document_vision import extract_document_data, format_logistics_instruction
from demand_forecaster import forecast_sku_stockouts
from portfolio import (
    create_initiative,
    get_wsjf_ranked_backlog,
    get_evms_snapshot,
    get_connection as get_portfolio_connection,
)
from graph import get_graph_with_postgres, log_dpo
from generate_synthetic_load import generate_load
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
load_dotenv()

DEMO_MODE = os.environ.get("DEMO_MODE") == "1"

# Page Configuration
st.set_page_config(
    page_title="Sovereign Supply Chain Orchestrator",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
header[data-testid="stHeader"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Enterprise SaaS Design System CSS (Dark Slate + Linear/Vercel/ServiceNow aesthetic)
ENTERPRISE_CSS = """
<style>
/* Base Theme Overrides */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #e6edf3;
}

/* Hide Streamlit Deploy Button */
.stDeployButton, [data-testid="stDeployButton"] {
    display: none !important;
}

/* App Background */
.stApp {
    background-color: #0b0f17;
}

/* Sidebar Navigation Rail */
[data-testid="stSidebar"] {
    background-color: #111622 !important;
    border-right: 1px solid #232b3e !important;
    padding-top: 1.5rem !important;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.6rem !important;
}

/* Custom Navigation Radio */
[data-testid="stSidebar"] .stRadio > div {
    gap: 0.35rem;
}

[data-testid="stSidebar"] .stRadio label {
    background: transparent;
    border: 1px solid transparent;
    padding: 0.55rem 0.85rem;
    border-radius: 6px;
    font-weight: 500;
    font-size: 0.88rem;
    cursor: pointer;
    transition: all 0.15s ease-in-out;
    color: #94a3b8 !important;
    display: flex;
    align-items: center;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background-color: #1a2234;
    color: #f1f5f9 !important;
}

/* Active Nav Selection */
[data-testid="stSidebar"] .stRadio label[data-checked="true"],
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background-color: #1e293b !important;
    border-color: #3b82f6 !important;
    color: #ffffff !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

/* Enterprise Header Bar */
.top-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.85rem 1.25rem;
    background: #111622;
    border: 1px solid #232b3e;
    border-radius: 8px;
    margin-bottom: 1.25rem;
}

.brand-title {
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: #0f2e24;
    border: 1px solid #10b981;
    color: #34d399;
    padding: 0.25rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.status-dot {
    width: 6px;
    height: 6px;
    background-color: #10b981;
    border-radius: 50%;
    box-shadow: 0 0 6px #10b981;
}

/* Enterprise Cards & Panels */
.control-card {
    background: #131926;
    border: 1px solid #232b3e;
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

.control-card-header {
    font-size: 0.95rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 0.5rem;
}

/* Button Standardizations */
button[kind="primary"], .stButton > button[kind="primary"] {
    background-color: #2563eb !important;
    border: 1px solid #3b82f6 !important;
    color: #ffffff !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    padding: 0.5rem 1.25rem !important;
    white-space: nowrap !important;
    min-height: 2.4rem !important;
    transition: background 0.15s ease !important;
}

button[kind="primary"]:hover {
    background-color: #1d4ed8 !important;
    border-color: #60a5fa !important;
}

button[kind="secondary"], .stButton > button:not([kind="primary"]) {
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    padding: 0.5rem 1.25rem !important;
    white-space: nowrap !important;
    min-height: 2.4rem !important;
}

button[kind="secondary"]:hover, .stButton > button:not([kind="primary"]):hover {
    background-color: #334155 !important;
    color: #ffffff !important;
}

/* Metric Cards */
[data-testid="stMetric"] {
    background-color: #161f30;
    border: 1px solid #26334d;
    padding: 0.85rem;
    border-radius: 6px;
}

[data-testid="stMetricLabel"] {
    font-size: 0.78rem;
    color: #94a3b8 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

[data-testid="stMetricValue"] {
    font-size: 1.4rem;
    font-weight: 700;
    color: #f8fafc !important;
}

/* Notification & Alert Banners */
.alert-banner {
    padding: 0.75rem 1rem;
    border-radius: 6px;
    margin-bottom: 1rem;
    font-size: 0.875rem;
    line-height: 1.4;
    border: 1px solid;
}

.alert-banner.critical {
    background-color: #381216;
    border-color: #ef4444;
    color: #fca5a5;
}

.alert-banner.warning {
    background-color: #35210c;
    border-color: #f59e0b;
    color: #fcd34d;
}

.alert-banner.info {
    background-color: #11253e;
    border-color: #3b82f6;
    color: #93c5fd;
}
</style>
"""
st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)

# State Initialization
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'waf_count' not in st.session_state:
    st.session_state.waf_count = 0
if 'waf_history' not in st.session_state:
    st.session_state.waf_history = []
if 'disruption_history' not in st.session_state:
    st.session_state.disruption_history = []
if 'forecast_cache' not in st.session_state:
    st.session_state.forecast_cache = None
if 'shelf_context' not in st.session_state:
    st.session_state.shelf_context = None
if 'extracted_document' not in st.session_state:
    st.session_state.extracted_document = None
if 'prefilled_prompt' not in st.session_state:
    st.session_state.prefilled_prompt = ""
if 'demo_paused_for_hitl' not in st.session_state:
    st.session_state.demo_paused_for_hitl = False
if 'demo_a2a_transcript' not in st.session_state:
    st.session_state.demo_a2a_transcript = []
if 'demo_pending_po' not in st.session_state:
    st.session_state.demo_pending_po = None
if 'demo_pending_plan' not in st.session_state:
    st.session_state.demo_pending_plan = ""

if DEMO_MODE and st.query_params.get("demo_hitl") == "1":
    st.session_state.demo_paused_for_hitl = True
    st.session_state.demo_pending_po = {
        "po_id": "PO-948201",
        "items": [{"sku": "SKU-STEEL-BEAMS", "qty": 500}],
        "restock_quantity": 500,
        "price_per_unit": 42.50,
        "lead_time_days": 3,
        "supplier": "Apex Logistics Supplier AI"
    }
    st.session_state.demo_a2a_transcript = [
        {"role": "buyer_agent", "request": [{"sku": "SKU-STEEL-BEAMS", "qty": 0}], "response": "Procurement Buyer RFQ: Request restock of 500 units SKU-STEEL-BEAMS. Max lead time: 5 days."},
        {"role": "supplier_agent", "request": "Procurement Buyer RFQ: Request restock of 500 units SKU-STEEL-BEAMS. Max lead time: 5 days.", "response": {"restock_quantity": 500, "price_per_unit": 42.50, "lead_time_days": 3}}
    ]
if 'active_nav_module' not in st.session_state:
    st.session_state.active_nav_module = "Orchestrator"
if 'blocked_unknown_item' not in st.session_state:
    st.session_state.blocked_unknown_item = None

# Check intentional developer mode (?dev=1 or DEV_MODE=1)
# User instruction: "Make it a collapsed Developer Tools item at the bottom of the navigation rail, visible only in intentional developer mode. Don't add an Operator/Developer toggle to the normal user interface."
is_dev_mode = (
    st.query_params.get("dev") == "1"
    or os.environ.get("DEV_MODE") == "1"
)

# Navigation Rail (Left Sidebar)
with st.sidebar:
    st.markdown(
        """
        <div style="padding-bottom: 0.75rem; border-bottom: 1px solid #232b3e; margin-bottom: 1rem;">
            <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em;">Platform</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin-top: 0.15rem;">Sovereign Tower</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Primary Navigation (Single-page navigation pattern with persistent, compact rail)
    modules = ["Orchestrator", "Warehouse", "Documents"]
    selected_module = st.radio(
        "Navigation",
        modules,
        index=modules.index(st.session_state.active_nav_module) if st.session_state.active_nav_module in modules else 0,
        label_visibility="collapsed",
        key="main_nav_radio"
    )
    st.session_state.active_nav_module = selected_module

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    # Developer Tools Section: visible only in intentional developer mode; collapsed area
    if is_dev_mode:
        with st.expander("🛠️ Developer Tools", expanded=False):
            dev_subviews = ["Diagnostics & WAF", "Analytics Dashboard"]
            selected_dev_view = st.radio("Developer Views", dev_subviews, key="dev_subview_radio")
            st.session_state.active_dev_subview = selected_dev_view
    else:
        st.session_state.active_dev_subview = None

    st.markdown("<div style='margin-top: auto; padding-top: 2rem;'></div>", unsafe_allow_html=True)
    st.caption("Environment: Meta Foundation Cloud\nv1.6.0-enterprise")

# Global Top Header Bar (Tenant Isolation & System Status)
header_col1, header_col2, header_col3 = st.columns([2, 1, 1])

with header_col1:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 0.75rem; padding-top: 0.35rem;">
            <div style="font-size: 1.35rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em;">
                🛡️ Sovereign Supply Chain
            </div>
            <div style="font-size: 0.85rem; color: #64748b; font-weight: 500;">
                / {st.session_state.active_nav_module}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with header_col2:
    tenant_id = st.selectbox(
        "Active Tenant",
        ["Tenant_A", "Tenant_B"],
        key="global_tenant_selector",
        label_visibility="collapsed"
    )

with header_col3:
    st.markdown(
        """
        <div style="text-align: right; padding-top: 0.35rem;">
            <span class="status-badge">
                <span class="status-dot"></span>
                Operational
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

config = {"configurable": {"thread_id": f"{tenant_id}_{st.session_state.thread_id}"}}
st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)


def execute_agent_synchronous(dispatched_prompt: str, tenant_id: str, request_id: str):
    """Invoke LangGraph synchronously and display response."""
    with st.spinner("Processing via LangGraph Orchestrator..."):
        try:
            graph = get_graph_with_postgres()
            state = {
                "messages": [HumanMessage(content=dispatched_prompt)],
                "tenant_id": tenant_id,
                "request_id": request_id,
                "status": "init"
            }
            result = graph.invoke(state, config)

            if result:
                final_messages = result.get("messages", [])
                drafted_plan = result.get("drafted_plan", "")
                status = result.get("status", "")
                unknown_item = result.get("unknown_item")

                for m in final_messages:
                    if isinstance(m, AIMessage):
                        if not any(chat["content"] == m.content for chat in st.session_state.chat_history):
                            st.session_state.chat_history.append({"role": "assistant", "content": m.content})
                        if "[GLOBAL ORACLE ALERT]" in m.content:
                            match = re.search(r"\[GLOBAL ORACLE ALERT\]\s*\((.*?)\):\s*(.*)", m.content)
                            if match:
                                severity = match.group(1).lower()
                                summary = match.group(2)
                                if not any(d.get("summary") == summary for d in st.session_state.disruption_history):
                                    st.session_state.disruption_history.append({
                                        "timestamp": time.strftime("%H:%M:%S"),
                                        "severity": severity,
                                        "summary": summary
                                    })

                if status == "item_not_found" and unknown_item:
                    st.session_state.blocked_unknown_item = {
                        "item": unknown_item,
                        "source": "Voice/Text Orchestrator Input"
                    }
                else:
                    st.session_state.pending_plan = drafted_plan
        except Exception as e:
            st.error(f"Execution error: {e}")


# Determine HITL State for contextual panel
if DEMO_MODE:
    is_paused = st.session_state.demo_paused_for_hitl
    pending_po = st.session_state.demo_pending_po
    a2a_transcript = st.session_state.demo_a2a_transcript
    pending_plan_content = st.session_state.demo_pending_plan
elif not os.environ.get("POSTGRES_DB_URI"):
    is_paused = False
    pending_po = None
    a2a_transcript = []
    pending_plan_content = ""
else:
    try:
        graph = get_graph_with_postgres()
        current_state = graph.get_state(config)
        is_paused = current_state.next == ('human_review',)
        pending_po = current_state.values.get("pending_po") if hasattr(current_state, "values") else None
        a2a_transcript = current_state.values.get("a2a_transcript", []) if hasattr(current_state, "values") else []
        pending_plan_content = current_state.values.get("drafted_plan", "") if hasattr(current_state, "values") else ""
    except Exception:
        is_paused = False
        pending_po = None
        a2a_transcript = []
        pending_plan_content = ""


# -----------------------------------------------------------------------------
# Developer Tools Display (When activated in Intentional Developer Mode)
# -----------------------------------------------------------------------------
if is_dev_mode and st.session_state.get("active_dev_subview"):
    subview = st.session_state.active_dev_subview
    st.markdown(f"### 🛠️ Developer Tools: {subview}")

    if subview == "Diagnostics & WAF":
        col_waf, col_sql = st.columns([1, 2])
        with col_waf:
            st.metric(label="WAF Rate-Limit Count", value=st.session_state.waf_count)
            if st.button("Reset WAF Counter", key="reset_waf_count_btn"):
                st.session_state.waf_count = 0
                st.session_state.waf_history = []
                st.rerun()

        with col_sql:
            st.subheader("MCP SQL Terminal Readout")
            try:
                conn = sqlite3.connect('mock_sap.db')
                cursor = conn.cursor()
                cursor.execute("SELECT id, query, tenant_id FROM mcp_sql_logs ORDER BY id DESC LIMIT 5")
                logs = cursor.fetchall()
                if not logs:
                    st.info("No SQL queries executed yet.")
                for log in logs:
                    st.code(f"[{log[2]}] {log[1]}")
                conn.close()
            except Exception as e:
                st.error(f"Error fetching SQL logs: {e}")

    elif subview == "Analytics Dashboard":
        st.subheader("Analytics Dashboard")

        # Section 1: Disruption alert history
        with st.expander("Disruption Alert History", expanded=True):
            if not st.session_state.disruption_history:
                st.info("No disruption alerts recorded yet.")
            else:
                for alert in reversed(st.session_state.disruption_history):
                    sev = alert.get("severity", "low").upper()
                    summary = alert.get("summary", "No details")
                    ts = alert.get("timestamp", "")
                    st.markdown(f"**[{ts}] ({sev})**: {summary}")

        # Section 2: Forecast predictions display
        with st.expander("Forecast Predictions", expanded=True):
            if st.button("Refresh Forecast", key="refresh_forecast_btn_dev"):
                with st.spinner("Forecasting SKU stockouts with muse-spark-1.3..."):
                    st.session_state.forecast_cache = forecast_sku_stockouts()

            forecasts = st.session_state.forecast_cache
            if not forecasts:
                st.info("No stockout predictions recorded. Click 'Refresh Forecast' to query model.")
            else:
                color_map = {"high": "red", "medium": "orange", "low": "green"}
                for fc in forecasts:
                    sku = fc.get("sku", "Unknown SKU")
                    days = fc.get("days_until_stockout", 0)
                    conf = str(fc.get("confidence", "low")).lower()
                    color = color_map.get(conf, "gray")
                    st.markdown(f"- **{sku}**: Stockout in **{days}** days (Confidence: :{color}[{conf.upper()}])")

    st.divider()


# -----------------------------------------------------------------------------
# Manager Approval HITL Panel (Triggered when input is blocked due to unknown item)
# -----------------------------------------------------------------------------
if st.session_state.get("blocked_unknown_item"):
    blocked_info = st.session_state.blocked_unknown_item
    unrecognized_item = blocked_info.get("item", "Unknown Item")
    source_info = blocked_info.get("source", "System Input")

    st.markdown(
        f"""
        <div class="control-card" style="border: 1px solid #f59e0b; background: #1c1917;">
            <div class="control-card-header" style="border-bottom: 1px solid #451a03; color: #fbbf24;">
                <span>⚠️ MANAGER APPROVAL REQUIRED — UNRECOGNIZED ITEM</span>
                <span style="font-size: 0.75rem; color: #f59e0b; background: #451a03; padding: 2px 8px; border-radius: 4px;">BLOCKED</span>
            </div>
            <div style="font-size: 0.9rem; margin-bottom: 0.75rem; color: #fef3c7;">
                An unrecognized item was detected from <strong>{source_info}</strong> and blocked by inventory governance:
            </div>
            <div style="background: #292524; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; border-left: 4px solid #f59e0b;">
                <span style="color: #94a3b8; font-size: 0.82rem; text-transform: uppercase;">Unrecognized Item / SKU:</span><br/>
                <strong style="font-size: 1.1rem; color: #f8fafc;">{unrecognized_item}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_mg_app, col_mg_cancel = st.columns([1, 1])
    with col_mg_app:
        if st.button("Request Manager Approval to Add", type="primary", key="manager_approval_add_btn", use_container_width=True):
            log_dpo(
                prompt=f"Manager approval request to add new inventory item: {unrecognized_item} (tenant: {tenant_id})",
                chosen="APPROVED",
                rejected="REJECTED"
            )
            st.session_state.blocked_unknown_item = None
            st.success(f"Manager approval requested to add item '{unrecognized_item}'. Logged successfully.")
            st.rerun()

    with col_mg_cancel:
        if st.button("Cancel", key="manager_approval_cancel_btn", use_container_width=True):
            st.session_state.blocked_unknown_item = None
            st.info("Manager approval request canceled.")
            st.rerun()

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Module 1: Orchestrator
# -----------------------------------------------------------------------------
if selected_module == "Orchestrator":
    # Check for active disruption banner from history
    if st.session_state.disruption_history:
        latest_alert = st.session_state.disruption_history[-1]
        sev = latest_alert.get("severity", "low").lower()
        banner_class = "critical" if sev == "high" else ("warning" if sev == "medium" else "info")
        st.markdown(
            f"""
            <div class="alert-banner {banner_class}">
                <strong>⚡ LOGISTICS DISRUPTION ALERT ({sev.upper()}):</strong> {latest_alert.get('summary', '')}
            </div>
            """,
            unsafe_allow_html=True
        )

    # Layout: Responsive split. If paused for HITL, show review panel (1/3) side-by-side on wide screens.
    if is_paused:
        col_main, col_hitl = st.columns([2, 1])
    else:
        col_main = st.container()
        col_hitl = None

    # Contextual HITL Review Panel (Only rendered when real approval is pending)
    if col_hitl is not None:
        with col_hitl:
            st.markdown(
                """
                <div class="control-card-header">
                    <span>⚠️ AWAITING HUMAN APPROVAL</span>
                    <span style="font-size: 0.75rem; color: #f59e0b; background: #35210c; padding: 2px 8px; border-radius: 4px;">PAUSED</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Real Draft Plan Details
            if pending_plan_content:
                st.markdown("**Proposed Logistics Plan:**")
                st.info(pending_plan_content)

            # Real A2A Negotiation and Draft PO
            if pending_po:
                # Human-readable summary card for Purchase Order
                supplier = pending_po.get("supplier", "Unknown Supplier")
                sku = pending_po.get("sku", "N/A")
                quantity = pending_po.get("quantity", pending_po.get("restock_quantity", 0))
                price = pending_po.get("price_per_unit", pending_po.get("unit_price", 0.0))
                lead_time = pending_po.get("lead_time_days", "N/A")

                st.markdown(
                    f"""
                    <div style="background: #161f30; border: 1px solid #232b3e; border-radius: 6px; padding: 0.85rem; margin-bottom: 0.85rem;">
                        <div style="font-size: 0.78rem; font-weight: 700; color: #3b82f6; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">
                            📦 Purchase Order Summary
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.84rem;">
                            <div><span style="color: #94a3b8;">Supplier:</span> <strong style="color: #f8fafc;">{supplier}</strong></div>
                            <div><span style="color: #94a3b8;">SKU:</span> <strong style="color: #f8fafc;">{sku}</strong></div>
                            <div><span style="color: #94a3b8;">Quantity:</span> <strong style="color: #f8fafc;">{quantity:,} units</strong></div>
                            <div><span style="color: #94a3b8;">Price / Unit:</span> <strong style="color: #34d399;">${price:,.2f}</strong></div>
                            <div><span style="color: #94a3b8;">Lead Time:</span> <strong style="color: #f8fafc;">{lead_time} days</strong></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            if a2a_transcript:
                with st.expander("📄 A2A Negotiation Transcript (JSON)", expanded=False):
                    for exchange in a2a_transcript:
                        st.json(exchange)

            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
            col_app, col_rej = st.columns(2)
            with col_app:
                if st.button("Approve", type="primary", key="hitl_approve_btn", use_container_width=True):
                    log_dpo(
                        st.session_state.get('pending_prompt', ''),
                        st.session_state.get('demo_pending_plan', st.session_state.get('pending_plan', '')),
                        ""
                    )
                    if DEMO_MODE:
                        st.session_state.demo_paused_for_hitl = False
                        st.session_state.chat_history.append({"role": "assistant", "content": "Plan Approved and Executed."})
                        st.success("Plan Approved and Executed.")
                        st.rerun()
                    else:
                        graph.update_state(config, {"status": "approved"})
                        for event in graph.stream(None, config):
                            pass
                        st.session_state.chat_history.append({"role": "assistant", "content": "Plan Approved and Executed."})
                        st.success("Plan Approved and Executed.")
                        st.rerun()

            with col_rej:
                if st.button("Reject", key="hitl_reject_btn", use_container_width=True):
                    log_dpo(
                        st.session_state.get('pending_prompt', ''),
                        "",
                        st.session_state.get('demo_pending_plan', st.session_state.get('pending_plan', ''))
                    )
                    if DEMO_MODE:
                        st.session_state.demo_paused_for_hitl = False
                        st.session_state.chat_history.append({"role": "assistant", "content": "Plan Rejected."})
                        st.error("Plan Rejected.")
                        st.rerun()
                    else:
                        graph.update_state(config, {"status": "rejected"})
                        for event in graph.stream(None, config):
                            pass
                        st.session_state.chat_history.append({"role": "assistant", "content": "Plan Rejected."})
                        st.error("Plan Rejected.")
                        st.rerun()

    # Main Conversation Area
    with col_main:
        # Display Conversation
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown(
                    """
                    <div style="text-align: center; padding: 3rem 1rem; color: #64748b; border: 1px dashed #232b3e; border-radius: 8px;">
                        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">💬</div>
                        <div style="font-weight: 600; color: #94a3b8;">Orchestrator Ready</div>
                        <div style="font-size: 0.85rem; margin-top: 0.25rem;">Dispatch voice or text logistics instructions to begin.</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        # Prefilled prompt from Document module if available
        if st.session_state.get("prefilled_prompt"):
            st.info(f"📋 **Draft Logistics Instruction from Document:**\n\n_{st.session_state.prefilled_prompt}_")
            if st.button("Send Instruction to Orchestrator", key="send_prefilled_instruction_btn", type="primary"):
                candidate_prompt = st.session_state.prefilled_prompt
                st.session_state.prefilled_prompt = ""
                if not check_prompt_injection(candidate_prompt):
                    st.session_state.waf_count += 1
                    st.session_state.waf_history.append({"timestamp": time.strftime("%H:%M:%S"), "count": 1})
                    st.error("SECURITY ALERT: Malicious prompt detected and blocked by Semantic Bouncer.")
                else:
                    st.session_state.chat_history.append({"role": "user", "content": candidate_prompt})
                    request_id = str(uuid.uuid4())
                    dispatched_prompt = candidate_prompt
                    if st.session_state.get("shelf_context") and st.session_state["shelf_context"].get("summary"):
                        summary_text = st.session_state["shelf_context"]["summary"]
                        dispatched_prompt = f"[VISUAL SHELF ANALYSIS: {summary_text}]\n{candidate_prompt}"

                    st.session_state.pending_prompt = dispatched_prompt
                    if DEMO_MODE:
                        resp_plan = (
                            f"Orchestrator Analysis for '{candidate_prompt}':\n"
                            f"• Tenant: {tenant_id}\n"
                            f"• Stock level verified across regional hubs.\n"
                            f"• Draft reallocation route: Warehouse-West to Distribution-East.\n"
                            f"• Optimal carrier dispatch generated with ETA 24 hours."
                        )
                        st.session_state.chat_history.append({"role": "assistant", "content": resp_plan})
                        st.session_state.demo_pending_plan = resp_plan
                    else:
                        execute_agent_synchronous(dispatched_prompt, tenant_id, request_id)
                    st.rerun()

        # Operational Voice Command Input (Placed directly above chat input)
        voice_audio = st.audio_input("Record voice instruction", key="voice_audio_input")
        if voice_audio is not None:
            audio_bytes = voice_audio.read()
            audio_id = hash(audio_bytes)
            if st.session_state.get("last_processed_audio_id") != audio_id:
                st.session_state.last_processed_audio_id = audio_id
                with st.spinner("Transcribing voice command with muse-voice-transcribe-1.0..."):
                    voice_result = process_voice_input(audio_bytes)
                    if voice_result.get("status") == "ok":
                        transcript = voice_result.get("transcription", "").strip()
                        if transcript:
                            if not check_prompt_injection(transcript):
                                st.session_state.waf_count += 1
                                st.session_state.waf_history.append({"timestamp": time.strftime("%H:%M:%S"), "count": 1})
                                st.error("SECURITY ALERT: Malicious prompt detected and blocked by Semantic Bouncer.")
                            else:
                                st.session_state.chat_history.append({"role": "user", "content": transcript})
                                request_id = str(uuid.uuid4())
                                dispatched_prompt = transcript
                                if st.session_state.get("shelf_context") and st.session_state["shelf_context"].get("summary"):
                                    summary_text = st.session_state["shelf_context"]["summary"]
                                    dispatched_prompt = f"[VISUAL SHELF ANALYSIS: {summary_text}]\n{transcript}"

                                st.session_state.pending_prompt = dispatched_prompt
                                if DEMO_MODE:
                                    from graph import extract_item_candidates
                                    from mcp_server import read_inventory
                                    inv_json = read_inventory(tenant_id)
                                    inv_items = json.loads(inv_json)
                                    valid_names = [itm.get("item_name", "").strip() for itm in inv_items if itm.get("item_name")]
                                    valid_names_lower = {name.lower(): name for name in valid_names}
                                    candidates = extract_item_candidates(transcript)
                                    unknown_found = None
                                    for c in candidates:
                                        c_lower = c.lower()
                                        if c_lower not in valid_names_lower and not any(c_lower in v or v in c_lower for v in valid_names_lower):
                                            unknown_found = c
                                            break

                                    if unknown_found:
                                        err_msg = f"Item '{unknown_found}' not found in inventory. Please retry or request manager approval to add new item"
                                        st.session_state.chat_history.append({"role": "assistant", "content": err_msg})
                                        st.session_state.blocked_unknown_item = {
                                            "item": unknown_found,
                                            "source": "Voice/Text Orchestrator Input"
                                        }
                                    else:
                                        resp_plan = (
                                            f"Orchestrator Analysis for '{transcript}':\n"
                                            f"• Tenant: {tenant_id}\n"
                                            f"• Stock level verified across regional hubs.\n"
                                            f"• Draft reallocation route: Warehouse-West to Distribution-East.\n"
                                            f"• Optimal carrier dispatch generated with ETA 24 hours."
                                        )
                                        st.session_state.chat_history.append({"role": "assistant", "content": resp_plan})
                                        st.session_state.demo_pending_plan = resp_plan
                                else:
                                    execute_agent_synchronous(dispatched_prompt, tenant_id, request_id)
                                st.rerun()
                    else:
                        st.error(f"Voice processing error: {voice_result.get('intent', 'Unknown error')}")

        # Text Logistics Command Input
        prompt = st.chat_input("Enter logistics instruction...")
        if prompt:
            if not check_prompt_injection(prompt):
                st.session_state.waf_count += 1
                st.session_state.waf_history.append({"timestamp": time.strftime("%H:%M:%S"), "count": 1})
                st.error("SECURITY ALERT: Malicious prompt detected and blocked by Semantic Bouncer.")
            else:
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                request_id = str(uuid.uuid4())
                dispatched_prompt = prompt
                if st.session_state.get("shelf_context") and st.session_state["shelf_context"].get("summary"):
                    summary_text = st.session_state["shelf_context"]["summary"]
                    dispatched_prompt = f"[VISUAL SHELF ANALYSIS: {summary_text}]\n{prompt}"

                st.session_state.pending_prompt = dispatched_prompt
                if DEMO_MODE:
                    from graph import extract_item_candidates
                    from mcp_server import read_inventory
                    inv_json = read_inventory(tenant_id)
                    inv_items = json.loads(inv_json)
                    valid_names = [itm.get("item_name", "").strip() for itm in inv_items if itm.get("item_name")]
                    valid_names_lower = {name.lower(): name for name in valid_names}
                    candidates = extract_item_candidates(prompt)
                    unknown_found = None
                    for c in candidates:
                        c_lower = c.lower()
                        if c_lower not in valid_names_lower and not any(c_lower in v or v in c_lower for v in valid_names_lower):
                            unknown_found = c
                            break

                    if unknown_found:
                        err_msg = f"Item '{unknown_found}' not found in inventory. Please retry or request manager approval to add new item"
                        st.session_state.chat_history.append({"role": "assistant", "content": err_msg})
                        st.session_state.blocked_unknown_item = {
                            "item": unknown_found,
                            "source": "Voice/Text Orchestrator Input"
                        }
                    else:
                        resp_plan = (
                            f"Orchestrator Analysis for '{prompt}':\n"
                            f"• Tenant: {tenant_id}\n"
                            f"• Stock level verified across regional hubs.\n"
                            f"• Draft reallocation route: Warehouse-West to Distribution-East.\n"
                            f"• Optimal carrier dispatch generated with ETA 24 hours."
                        )
                        st.session_state.chat_history.append({"role": "assistant", "content": resp_plan})
                        st.session_state.demo_pending_plan = resp_plan
                        st.session_state.demo_paused_for_hitl = True
                        st.session_state.demo_pending_po = {
                            "po_id": "PO-948201",
                            "items": [{"sku": "SKU-STEEL-BEAMS", "qty": 500}],
                            "restock_quantity": 500,
                            "price_per_unit": 42.50,
                            "lead_time_days": 3,
                            "supplier": "Apex Logistics Supplier AI"
                        }
                        st.session_state.pending_prompt = dispatched_prompt
                else:
                    execute_agent_synchronous(dispatched_prompt, tenant_id, request_id)
                st.rerun()



# -----------------------------------------------------------------------------
# Module 2: Warehouse Vision
# -----------------------------------------------------------------------------
elif selected_module == "Warehouse":
    st.markdown("### 📦 Warehouse Vision & Inventory Segmentation")
    st.markdown("Automated stock segmentation powered by Meta SAM 3.1. Upload shelf imagery to detect low-stock or empty SKU bins.")

    col_up, col_ctx = st.columns([1, 1])

    with col_up:
        st.markdown(
            """
            <div class="control-card-header">
                <span>UPLOAD SHELF CAMERA FEED</span>
                <span style="font-size: 0.75rem; color: #94a3b8;">MAX 1MB</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        uploaded_image = st.file_uploader(
            "Upload Shelf Image",
            type=["png", "jpg", "jpeg", "webp"],
            key="shelf_image_uploader"
        )
        if uploaded_image is not None:
            if uploaded_image.size > 1_000_000:
                st.error("File too large. Please upload under 1MB.")
            else:
                image_bytes = uploaded_image.read()
                image_id = hash(image_bytes)
                if st.session_state.get("last_uploaded_image_id") != image_id:
                    st.session_state.last_uploaded_image_id = image_id
                    with st.spinner("Analyzing shelf image with SAM 3.1..."):
                        analysis = analyze_shelf_image(image_bytes, tenant_id=tenant_id)
                        if "error" in analysis:
                            st.session_state.shelf_context = None
                            st.session_state.blocked_unknown_item = {
                                "item": analysis.get("unknown_item", "Unknown Item"),
                                "source": "Warehouse Shelf Vision"
                            }
                            st.error(analysis["error"])
                        else:
                            st.session_state.shelf_context = analysis
                            st.rerun()

    with col_ctx:
        st.markdown(
            """
            <div class="control-card-header">
                <span>ACTIVE VISUAL CONTEXT</span>
                <span style="font-size: 0.75rem; color: #34d399;">SAM 3.1 ACTIVE</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.session_state.get("shelf_context"):
            ctx = st.session_state.shelf_context
            st.markdown(f"**Analysis Summary:**\n\n{ctx.get('summary', 'No summary generated.')}")

            items = ctx.get("items", [])
            if items:
                table_items = []
                for itm in items:
                    fill_pct = int(itm.get("fill_level", 0.0) * 100)
                    table_items.append({
                        "Item SKU": itm.get("item"),
                        "Fill Level": f"{fill_pct}%",
                        "Status": itm.get("status", "ok").upper()
                    })
                st.dataframe(pd.DataFrame(table_items), use_container_width=True, hide_index=True)

            st.caption("Active context is automatically appended to subsequent Orchestrator instructions.")
            if st.button("Clear Shelf Context", key="clear_shelf_context_btn"):
                st.session_state.shelf_context = None
                st.session_state.last_uploaded_image_id = None
                st.rerun()
        else:
            st.info("No active shelf image analyzed. Upload an image to segment inventory.")


# -----------------------------------------------------------------------------
# Module 3: Documents
# -----------------------------------------------------------------------------
elif selected_module == "Documents":
    st.markdown("### 📄 Document & Invoice Extraction")
    st.markdown("Automated structured data extraction powered by Meta muse-image-1.0. Upload invoices, bills of lading, and freight manifests.")

    col_doc_up, col_doc_view = st.columns([1, 1])

    with col_doc_up:
        st.markdown(
            """
            <div class="control-card-header">
                <span>UPLOAD INVOICE / BOL DOCUMENT</span>
                <span style="font-size: 0.75rem; color: #94a3b8;">MAX 2MB</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        uploaded_doc = st.file_uploader(
            "Upload Invoice or Shipping Document",
            type=["png", "jpg", "jpeg", "webp"],
            key="document_image_uploader"
        )
        if uploaded_doc is not None:
            if uploaded_doc.size > 2_000_000:
                st.error("File too large. Please upload under 2MB.")
            else:
                doc_bytes = uploaded_doc.read()
                doc_id = hash(doc_bytes)
                if st.session_state.get("last_uploaded_doc_id") != doc_id:
                    st.session_state.last_uploaded_doc_id = doc_id
                    with st.spinner("Extracting document data with muse-image-1.0..."):
                        extraction = extract_document_data(doc_bytes, tenant_id=tenant_id)
                        if "error" in extraction:
                            st.session_state.extracted_document = None
                            st.session_state.prefilled_prompt = ""
                            st.session_state.blocked_unknown_item = {
                                "item": extraction.get("unknown_item", "Unknown Item"),
                                "source": "Document/Invoice Ingestion"
                            }
                            st.error(extraction["error"])
                        else:
                            st.session_state.extracted_document = extraction
                            st.session_state.prefilled_prompt = format_logistics_instruction(extraction)
                            st.rerun()

    with col_doc_view:
        st.markdown(
            """
            <div class="control-card-header">
                <span>STRUCTURED EXTRACTION</span>
                <span style="font-size: 0.75rem; color: #3b82f6;">MUSE-IMAGE-1.0</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.session_state.get("extracted_document"):
            doc_data = st.session_state.extracted_document
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(f"**Supplier:** {doc_data.get('supplier') or 'Not specified'}")
                dates = doc_data.get("dates", [])
                st.markdown(f"**Dates:** {', '.join(dates) if dates else 'Not specified'}")
            with col_d2:
                st.markdown(f"**Summary:** {doc_data.get('raw_summary') or 'None'}")

            items = doc_data.get("items", [])
            if items:
                st.markdown("**Line Items:**")
                doc_table = []
                for itm in items:
                    doc_table.append({
                        "Description": itm.get('description', 'Item'),
                        "Quantity": itm.get('quantity', 1),
                        "Unit Price": f"${itm.get('unit_price')}" if itm.get('unit_price') is not None else "N/A"
                    })
                st.dataframe(pd.DataFrame(doc_table), use_container_width=True, hide_index=True)

            if st.session_state.get("prefilled_prompt"):
                st.markdown("**Generated Logistics Instruction:**")
                st.info(st.session_state.prefilled_prompt)

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Clear Document", key="clear_extracted_doc_btn"):
                    st.session_state.extracted_document = None
                    st.session_state.prefilled_prompt = ""
                    st.session_state.last_uploaded_doc_id = None
                    st.rerun()
            with col_b2:
                if st.button("Open in Orchestrator", type="primary", key="open_in_orchestrator_btn"):
                    st.session_state.active_nav_module = "Orchestrator"
                    st.rerun()
        else:
            st.info("No document uploaded. Upload a document to extract structured logistics data.")
