# DEPRECATED: Streamlit UI replaced by React frontend
# Kept for reference only. Do not run in production.
# Production entry point: backend/main.py (FastAPI)
import sys
if "--streamlit" not in sys.argv:
    print("WARNING: app.py is deprecated.")
    print("Run: cd backend && uvicorn main:app --port 8000")

import streamlit as st
import sqlite3
import json
import uuid
import hashlib
import time
import os
import re
import difflib
from typing import Optional, Tuple
import pandas as pd
from dotenv import load_dotenv

from guardrails import check_prompt_injection
from voice_handler import process_voice_input
from warehouse_vision import analyze_shelf_image
from document_vision import extract_document_data, format_logistics_instruction
from demand_forecaster import forecast_sku_stockouts
from graph import get_graph_with_postgres, log_dpo
from langchain_core.messages import HumanMessage, AIMessage
from db import execute_query, execute_mutation, get_db_connection

# Load environment variables
load_dotenv()

DEMO_MODE = os.environ.get("DEMO_MODE", "1") == "1"

_api_key = os.environ.get("META_API_KEY")
if not DEMO_MODE and not _api_key:
    st.set_page_config(page_title="Setup Required",
                       page_icon="🔑", layout="centered")
    st.markdown("""
    <div style="max-width:500px; margin:4rem auto;
    background:#131926; border:1px solid #ef4444;
    border-radius:8px; padding:2rem; text-align:center;">
      <div style="font-size:2rem;">🔑</div>
      <h2 style="color:#f8fafc;">API Key Required</h2>
      <p style="color:#94a3b8;">
        Add your Meta AI API key to get started.
      </p>
      <code style="background:#0b0f17; color:#3b82f6;
      padding:0.5rem 1rem; border-radius:4px; display:block;
      margin:1rem 0;">META_API_KEY=your_key_here</code>
      <p style="color:#64748b; font-size:0.85rem;">
        Get your key at
        <a href="https://dev.meta.ai/api-keys"
        style="color:#3b82f6;">dev.meta.ai/api-keys</a>
      </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Page Configuration
st.set_page_config(
    page_title="Sovereign Supply Chain",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<!-- ssc-loader removed -->
""", unsafe_allow_html=True)


st.markdown("""
<style>
header[data-testid="stHeader"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# SaaS Design System CSS (Dark Slate + Linear/Vercel/ServiceNow aesthetic)
APP_CSS = """
<style>
/* Claude-style combined input bar */
.combined-input-row {
    display: flex;
    align-items: center;
    background: #111622;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 6px 12px;
    margin-top: 10px;
    margin-bottom: 12px;
}
.combined-input-row:focus-within {
    border-color: #58a6ff;
    box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2);
}

/* Base Theme Overrides */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #e6edf3;
}

@keyframes pulse-amber {
  0% { box-shadow: 0 0 0 0 rgba(227, 179, 65, 0.4); border-color: rgba(227, 179, 65, 0.6); }
  70% { box-shadow: 0 0 0 10px rgba(227, 179, 65, 0); border-color: rgba(227, 179, 65, 1); }
  100% { box-shadow: 0 0 0 0 rgba(227, 179, 65, 0); border-color: rgba(227, 179, 65, 0.6); }
}
.hitl-panel-pulsing {
  animation: pulse-amber 2s infinite ease-in-out;
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

/* Header Bar */
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

/* Cards & Panels */
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

/* Styled User Error Card */
.user-error-card {
    background: #1f1215;
    border: 1px solid #ef4444;
    border-left: 5px solid #ef4444;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin: 0.85rem 0 1.25rem 0;
}

.user-error-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #fca5a5;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
}

.user-error-message {
    font-size: 0.88rem;
    color: #fecaca;
    line-height: 1.45;
    margin-bottom: 0.55rem;
}

.user-error-suggestion {
    font-size: 0.82rem;
    color: #94a3b8;
    background: #111622;
    border: 1px solid #232b3e;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    line-height: 1.4;
}

.user-error-suggestion strong {
    color: #38bdf8;
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
/* Fix 4: Active radio navigation state */
div[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: #21262d !important;
    border-left: 3px solid #58a6ff !important;
    border-radius: 0 6px 6px 0 !important;
    color: #58a6ff !important;
    padding-left: 12px !important;
}

/* Fix 13: Streamlit widget style normalization */
.stSelectbox > div > div {
    background:#161b22 !important;
    border:1px solid #30363d !important;
    border-radius:6px !important;
    color:#e6edf3 !important;
}
.stFileUploader > div {
    background:#161b22 !important;
    border:1px dashed #30363d !important;
    border-radius:8px !important;
}
.stFileUploader label {
    color:#8b949e !important;
    font-size:0.85rem !important;
}
.stRadio > div {
    gap:4px !important;
}
.stRadio label {
    color:#8b949e !important;
    font-size:0.9rem !important;
    padding:8px 12px !important;
    border-radius:6px !important;
    cursor:pointer !important;
    transition:background 0.15s !important;
}
.stRadio label:hover {
    background:#21262d !important;
    color:#e6edf3 !important;
}
.stChatInput textarea {
    background:#161b22 !important;
    border:1px solid #30363d !important;
    border-radius:8px !important;
    color:#e6edf3 !important;
    font-size:0.9rem !important;
}
.stChatInput textarea:focus {
    border-color:#58a6ff !important;
    box-shadow:0 0 0 2px rgba(88,166,255,0.15) !important;
}
.stSpinner > div {
    border-top-color:#58a6ff !important;
}
.streamlit-expanderHeader {
    background:#161b22 !important;
    border:1px solid #30363d !important;
    border-radius:6px !important;
    color:#8b949e !important;
    font-size:0.85rem !important;
}


.alert-banner.success {
    background-color: #0f2e24;
    border-color: #10b981;
    color: #34d399;
}
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)

st.markdown("""
<script>
  var lastScroll = 0;
  window.addEventListener('scroll',
    function(){ lastScroll = window.scrollY; });
  var observer = new MutationObserver(function(){
    if(lastScroll > 0){
      window.scrollTo(0, lastScroll);
    }
  });
  observer.observe(document.body,
    {childList:true, subtree:true});
</script>
""", unsafe_allow_html=True)


def show_toast(message: str, kind: str = "success", duration: int = 3):
    colors = {
        "success": ("#3fb950", "✅"),
        "error":   ("#f85149", "⚠️"),
        "info":    ("#58a6ff", "ℹ️"),
        "warning": ("#e3b341", "⚡"),
    }
    color, icon = colors.get(kind, colors["info"])
    st.markdown(f"""
    <div id="ssc-toast" style="
        position:fixed;bottom:24px;right:24px;
        background:#161b22;border:1px solid {color};
        border-left:4px solid {color};
        border-radius:8px;padding:12px 20px;
        font-family:sans-serif;font-size:0.875rem;
        color:#e6edf3;z-index:99999;
        box-shadow:0 4px 12px rgba(0,0,0,0.4);
        animation:slideIn 0.3s ease;">
      {icon} {message}
    </div>
    <style>
      @keyframes slideIn {{
        from {{transform:translateX(100px);opacity:0;}}
        to  {{transform:translateX(0);opacity:1;}}
      }}
    </style>
    <script>
      setTimeout(function(){{
        var t=document.getElementById('ssc-toast');
        if(t){{t.style.opacity='0';
          t.style.transition='opacity 0.3s';
          setTimeout(function(){{t.remove();}},{duration*1000});}}
      }},{duration*1000});
    </script>
    """, unsafe_allow_html=True)


PERSISTENT_KEYS = [
    "messages", "chat_history", "thread_id", "task_id",
    "shelf_context", "hitl_approved", "dispatch_ts"
]


def switch_module(new_module: str):
    current = st.session_state.get("active_module")
    if current != new_module:
        if current == "Warehouse":
            st.session_state.pop("shelf_upload_result", None)
        elif current == "Invoice":
            st.session_state.pop("invoice_result", None)
        st.session_state["active_module"] = new_module


AGENT_STEPS = [
    "Checking disruption radar",
    "Fetching inventory",
    "Analyzing demand",
    "Drafting plan",
    "Awaiting your approval"
]


def render_agent_progress(task_status: str):
    if task_status in ("PENDING", "STARTED"):
        elapsed = time.time() - st.session_state.get("dispatch_ts", time.time())
        step_idx = min(int(elapsed / 3), len(AGENT_STEPS) - 1)
        progress_pct = (step_idx + 1) / len(AGENT_STEPS)

        st.markdown(f"""
        <div class="ssc-card" style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin:16px 0;">
          <div class="ssc-section-header" style="font-size:0.75rem;color:#58a6ff;font-weight:600;letter-spacing:0.08em;margin-bottom:8px;">AI AGENTS WORKING</div>
          <div style="color:#e6edf3;font-size:0.9rem;margin-bottom:12px;">
            ⚡ {AGENT_STEPS[step_idx]}...
          </div>
          <div style="background:#21262d;border-radius:4px;height:6px;">
            <div style="background:#58a6ff;border-radius:4px;height:6px;
              width:{int(progress_pct*100)}%;
              transition:width 0.5s ease;">
            </div>
          </div>
          <div style="color:#8b949e;font-size:0.75rem;margin-top:8px;">
            Step {step_idx+1} of {len(AGENT_STEPS)}
          </div>
        </div>
        """, unsafe_allow_html=True)



FRIENDLY_ERRORS = {
    "connection": "⚠️ Cannot reach the database right now. Try again in 30 seconds.",
    "timeout": "⚠️ The AI model took too long to respond. Please retry your request.",
    "guardrail": "⚠️ Your request was blocked by security filters. See Example Inputs below for accepted phrasing.",
    "upload": "⚠️ File could not be processed. Ensure it is a clear PNG/JPG/WEBP under 1MB.",
    "default": "⚠️ Something went wrong. Please retry or contact your system administrator."
}

def friendly_error(e: Exception) -> str:
    msg = str(e).lower()
    if "connect" in msg or "database" in msg:
        return FRIENDLY_ERRORS["connection"]
    if "timeout" in msg or "timed out" in msg:
        return FRIENDLY_ERRORS["timeout"]
    if "guardrail" in msg or "blocked" in msg:
        return FRIENDLY_ERRORS["guardrail"]
    if "upload" in msg or "image" in msg:
        return FRIENDLY_ERRORS["upload"]
    return FRIENDLY_ERRORS["default"]

RATE_LIMIT_SECONDS = 10

def check_rate_limit(tenant_id: str) -> bool:
    key = f"last_dispatch_{tenant_id}"
    last = st.session_state.get(key, 0)
    if time.time() - last < RATE_LIMIT_SECONDS:
        return False
    st.session_state[key] = time.time()
    return True

def log_activity(source: str, msg: str, icon: str = "⚡", model: Optional[str] = None):
    """Append entry to real-time Activity Log (capped at 100)."""
    if 'activity_log' not in st.session_state:
        st.session_state.activity_log = []
    ts = time.strftime("%H:%M:%S")
    entry = {"ts": ts, "source": source, "msg": str(msg)[:80], "icon": icon}
    if model:
        entry["model"] = model
    st.session_state.activity_log.append(entry)
    if len(st.session_state.activity_log) > 100:
        st.session_state.activity_log = st.session_state.activity_log[-100:]

def append_activity_log(icon: str, source: str, message: str, level: str = "info"):
    """Append an event entry to st.session_state.activity_log."""
    log_activity(source=source, msg=message, icon=icon)

def render_activity_log(disabled: bool = False):
    """Render fixed height docked activity log panel at bottom of main column."""
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    is_expanded = st.session_state.get("activity_log_expanded", False)
    header_col, btn1_col, btn2_col = st.columns([7, 1.6, 1.4])
    with header_col:
        st.markdown(f"**Activity Log ({len(st.session_state.get('activity_log', []))})**")
    with btn1_col:
        toggle_label = "Hide Log" if is_expanded else "Show Log"
        if st.button(toggle_label, key="toggle_activity_log_btn", use_container_width=True):
            st.session_state.activity_log_expanded = not is_expanded
            st.rerun()
    with btn2_col:
        if st.button("Clear", key="clear_activity_log_btn", disabled=disabled, use_container_width=True):
            st.session_state.activity_log = []
            st.rerun()

    if is_expanded:
        log_entries = st.session_state.get("activity_log", [])
        lines = []
        for e in reversed(log_entries):
            ts = e.get("ts", "")
            icon = e.get("icon", "•")
            src = e.get("source", "system")
            msg = e.get("msg", "")[:80]
            mdl = f" [{e['model']}]" if e.get("model") else ""
            lines.append(f"<div style='font-family:monospace;font-size:0.8rem;padding:2px 0;color:#94a3b8;'>{ts} {icon} <strong>{src}</strong>{mdl}: {msg}</div>")
        content_html = "".join(lines) if lines else "<div style='color:#64748b;font-size:0.8rem;'>No recent activity.</div>"
        st.markdown(
            f"""
            <div style="height: 180px; overflow-y: auto; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; margin-bottom: 1rem;">
                {content_html}
            </div>
            """,
            unsafe_allow_html=True
        )

def show_user_error(message: str, suggestion: str):
    """
    Renders a styled HTML card with a ⚠️ icon, plain-English error headline, and a 'What to do next:' line.
    Replaces raw error popup calls across the application.
    """
    card_html = f"""
    <div class="user-error-card">
        <div class="user-error-title">
            <span>⚠️ Action Needed</span>
        </div>
        <div class="user-error-message">
            {message}
        </div>
        <div class="user-error-suggestion">
            <strong>What to do next:</strong> {suggestion}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def suggest_similar_item(item_name: str, tenant_id: str) -> Optional[str]:
    """
    Finds the closest matching inventory item name for tenant_id using difflib.get_close_matches
    against inventory item names fetched from the database with cutoff=0.5.
    """
    try:
        rows = execute_query("SELECT item_name FROM inventory WHERE tenant_id = ?", [tenant_id])
        item_names = [r["item_name"] for r in rows]
    except Exception:
        return None

    if not item_names:
        return None

    mapping = {name.lower(): name for name in item_names}
    # Direct case-insensitive match
    if item_name.lower() in mapping:
        return mapping[item_name.lower()]

    matches = difflib.get_close_matches(item_name.lower(), mapping.keys(), n=1, cutoff=0.5)
    if matches:
        return mapping[matches[0]]
    return None


def check_missing_item_and_suggest(user_input: str, tenant_id: str) -> Optional[Tuple[str, str]]:
    """
    Checks if an item name mentioned in the user prompt is absent from inventory,
    and returns an error message and suggestion with the closest match if found.
    """
    try:
        rows = execute_query("SELECT item_name FROM inventory WHERE tenant_id = ?", [tenant_id])
        item_names = [r["item_name"] for r in rows]
    except Exception:
        return None

    words = re.findall(r"[A-Za-z0-9\-]+", user_input)
    lower_inventory = {name.lower(): name for name in item_names}

    for word in words:
        if len(word) >= 4 and word.lower() not in lower_inventory:
            closest_match = suggest_similar_item(word, tenant_id)
            if closest_match:
                return (
                    f"Item not found: We couldn't find '{word}' in your inventory.",
                    f"Did you mean '{closest_match}'? Try saying or typing '{closest_match}' again, or request adding '{word}' in the Admin panel."
                )
    return None


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
if 'auto_submit_prompt' not in st.session_state:
    st.session_state.auto_submit_prompt = None
if 'demo_paused_for_hitl' not in st.session_state:
    st.session_state.demo_paused_for_hitl = False
if 'demo_a2a_transcript' not in st.session_state:
    st.session_state.demo_a2a_transcript = []
if 'demo_pending_po' not in st.session_state:
    st.session_state.demo_pending_po = None
if 'demo_pending_plan' not in st.session_state:
    st.session_state.demo_pending_plan = ""
BUILD_ID = os.environ.get("RENDER_GIT_COMMIT", "dev")[:8]
if 'activity_log' not in st.session_state or st.session_state.get("build_id") != BUILD_ID:
    st.session_state.activity_log = [
        {"ts": time.strftime("%H:%M:%S"), "icon": "⚡", "source": "system", "msg": f"System ready (build {BUILD_ID})"}
    ]
    st.session_state.build_id = BUILD_ID
if 'activity_log_expanded' not in st.session_state:
    st.session_state.activity_log_expanded = False

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

# Check intentional developer mode (?dev=1 or DEV_MODE=1)
is_dev_mode = (
    st.query_params.get("dev") == "1"
    or os.environ.get("DEV_MODE") == "1"
)

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")

def is_admin_authenticated() -> bool:
    if not ADMIN_SECRET or len(ADMIN_SECRET) <= 8:
        return False
    params = st.query_params
    token = params.get("admin_token", "")
    return bool(token and token == ADMIN_SECRET)

is_authorized_admin = is_admin_authenticated()
is_admin_mode = is_authorized_admin

if ("admin_token" in st.query_params or st.query_params.get("admin") == "1") and not is_authorized_admin:
    show_user_error(
        "Unauthorized access.",
        "Provide a valid ?admin_token=<token> to access the Admin panel."
    )
    st.stop()

if 'active_nav_module' not in st.session_state:
    st.session_state.active_nav_module = "Admin" if is_authorized_admin else "Orchestrator"

# Navigation Rail (Left Sidebar) - Minimalist Single-Page Layout
with st.sidebar:
    st.markdown("🛡️ **Sovereign**")
    selected_module = "Admin" if is_authorized_admin else "Orchestrator"
    st.session_state.active_nav_module = selected_module

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    # Developer Tools Section: visible only in intentional developer mode
    if is_dev_mode:
        with st.expander("🛠️ Developer Tools", expanded=False):
            dev_subviews = ["Diagnostics & WAF", "Analytics Dashboard"]
            selected_dev_view = st.radio("Developer Views", dev_subviews, key="dev_subview_radio")
            st.session_state.active_dev_subview = selected_dev_view
    else:
        st.session_state.active_dev_subview = None

# Pure Module Title Header (no Sovereign Supply Chain button, default tenant, no Operational badge)
tenant_id = os.environ.get("DEFAULT_TENANT_ID", "Tenant_" + "A")

st.markdown(
    f"""
    <div style="padding-top: 0.2rem; padding-bottom: 0.8rem;">
        <h1 style="font-size: 1.6rem; font-weight: 700; color: #f8fafc; margin: 0; padding: 0; letter-spacing: -0.02em;">
            {selected_module}
        </h1>
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

                for m in final_messages:
                    if isinstance(m, AIMessage):
                        if not any(chat["content"] == m.content for chat in st.session_state.chat_history):
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": m.content,
                                "ts": time.strftime("%H:%M:%S")
                            })
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

                st.session_state.pending_plan = drafted_plan
        except Exception as e:
            show_user_error(friendly_error(e), "Try submitting your command again in a moment.")


# Load gold standard inputs once for example collapsibles
try:
    with open("demo/gold_standard_inputs.json", "r") as f:
        GOLD_INPUTS = json.load(f)
except Exception:
    GOLD_INPUTS = []


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
# Developer Tools Display
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
                logs = execute_query("SELECT id, query, tenant_id FROM mcp_sql_logs ORDER BY id DESC LIMIT 5")
                if not logs:
                    st.info("No SQL queries executed yet.")
                for log in logs:
                    st.code(f"[{log.get('tenant_id')}] {log.get('query')}")
            except Exception as e:
                show_user_error(friendly_error(e), "Try submitting your command again in a moment.")

    elif subview == "Analytics Dashboard":
        try:
            from portfolio import (
                create_initiative,
                get_wsjf_ranked_backlog,
                get_evms_snapshot,
                get_connection as get_portfolio_connection,
            )
        except Exception:
            pass

        st.subheader("Analytics Dashboard")
        with st.expander("Disruption Alert History", expanded=True):
            if not st.session_state.disruption_history:
                st.info("No disruption alerts recorded yet.")
            else:
                for alert in reversed(st.session_state.disruption_history):
                    sev = alert.get("severity", "low").upper()
                    summary = alert.get("summary", "No details")
                    ts = alert.get("timestamp", "")
                    st.markdown(f"**[{ts}] ({sev})**: {summary}")

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


# Check if auto_submit_prompt was triggered (e.g. from Example Inputs button)
if st.session_state.get("auto_submit_prompt"):
    to_submit = st.session_state.auto_submit_prompt
    st.session_state.auto_submit_prompt = None

    if not check_prompt_injection(to_submit):
        st.session_state.waf_count += 1
        st.session_state.waf_history.append({"timestamp": time.strftime("%H:%M:%S"), "count": 1})
        log_activity("guardrails", "Prompt injection blocked: malicious pattern", icon="❌")
        block_msg = "⚠️ That input was blocked by safety guardrails.\n\nTry:\n• Check stock levels for Widget-A\n• Reorder 500 Microcontrollers\n• Emergency restock Semiconductors"
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": block_msg,
            "ts": time.strftime("%H:%M:%S")
        })
        st.session_state["prefill_prompt"] = ""
        st.session_state.prefilled_prompt = ""
    elif check_missing_item_and_suggest(to_submit, tenant_id):
        fuzzy_err = check_missing_item_and_suggest(to_submit, tenant_id)
        show_user_error(fuzzy_err[0], fuzzy_err[1])
        st.session_state.waf_count += 1
        st.session_state.waf_history.append({"timestamp": time.strftime("%H:%M:%S"), "count": 1})
        show_toast("Request blocked. See suggestions below.", "warning")
        st.session_state["prefill_prompt"] = ""
        st.session_state.prefilled_prompt = ""
        st.session_state.show_guardrail_help = True
    else:
        if not check_rate_limit(tenant_id):
            show_user_error("Rate limit reached.", "Please wait a few seconds before sending another request.")
            st.stop()

        st.session_state.chat_history.append({
            "role": "user",
            "content": to_submit,
            "ts": time.strftime("%H:%M:%S")
        })
        request_id = str(uuid.uuid4())
        dispatched_prompt = to_submit
        if st.session_state.get("shelf_context") and st.session_state["shelf_context"].get("summary"):
            summary_text = st.session_state["shelf_context"]["summary"]
            dispatched_prompt = f"[VISUAL SHELF ANALYSIS: {summary_text}]\n{to_submit}"

        st.session_state.pending_prompt = dispatched_prompt
        if DEMO_MODE:
            # Determine what item the demo should focus on
            shelf_ctx = st.session_state.get("shelf_context")

            # Priority 1: shelf image was uploaded — use lowest-stock item
            if shelf_ctx and shelf_ctx.get("items"):
                items = shelf_ctx["items"]
                # Find emptiest item
                worst = min(items, key=lambda x: x.get("fill_pct", 100))
                demo_sku = worst.get("sku", "Widget-A")
                demo_item_name = worst.get("name", "Widget-A")
            # Priority 2: parse item from text input
            elif to_submit:
                # Extract item name from common patterns
                import re
                m = re.search(
                    r"(?:restock|reorder|stock|check)\s+(?:\d+\s+)?(?:units?\s+of\s+)?([A-Za-z0-9\-\s]+?)(?:\s*$|\s*—|\s*,|\s*\.)",
                    to_submit, re.IGNORECASE
                )
                demo_item_name = m.group(1).strip() if m else "Widget-A"
                demo_sku = "SKU-" + demo_item_name.upper().replace(" ", "-")
            else:
                demo_item_name = "Widget-A"
                demo_sku = "SKU-WIDGET-A"

            # Look up item in live inventory to get real reorder quantity
            try:
                inv_rows = execute_query(
                    "SELECT item_name, quantity FROM inventory WHERE tenant_id = ? AND LOWER(item_name) LIKE ?",
                    [tenant_id, f"%{demo_item_name.lower()[:8]}%"]
                )
                if inv_rows:
                    matched = inv_rows[0]
                    demo_item_name = matched["item_name"]
                    current_qty = matched["quantity"]
                else:
                    current_qty = 0
            except Exception:
                current_qty = 0

            reorder_qty = max(500, (1000 - current_qty))
            demo_po = {
                "po_id": f"PO-{uuid.uuid4().hex[:6].upper()}",
                "items": [{"sku": demo_sku, "qty": reorder_qty}],
                "restock_quantity": reorder_qty,
                "price_per_unit": 14.20,
                "lead_time_days": 4,
                "supplier": "Global Electronics Supplier AI",
                "item_name": demo_item_name,
            }

            qty = demo_po["restock_quantity"]
            price = demo_po["price_per_unit"]
            total = qty * price
            lead = demo_po["lead_time_days"]
            supplier = demo_po["supplier"]
            po_id = demo_po["po_id"]
            item_name = demo_po["item_name"]

            append_activity_log("✅", "disruption-radar", "Disruption radar scan complete")
            append_activity_log("✅", "inventory", f"Stockout confirmed: {item_name}")
            append_activity_log("⚡", "a2a", f"Negotiated ${price}/unit with {supplier}")
            append_activity_log("⏸️", "hitl", f"Paused for operator approval: {po_id}")

            po_bubble = (
                f"Stockout detected for **{item_name}**. Negotiated **${price}/unit** with {supplier}. "
                f"Approval required.\n\n"
                f"⚡ **{po_id}** · {qty} units · ${price}/unit · **${total:,.2f}** · {lead} days"
            )
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": po_bubble,
                "ts": time.strftime("%H:%M:%S")
            })
            st.session_state.demo_pending_plan = po_bubble
            st.session_state.demo_pending_po = demo_po
            st.session_state.demo_paused_for_hitl = True
        else:
            execute_agent_synchronous(dispatched_prompt, tenant_id, request_id)
        st.rerun()




# Fix 12: Disruption alert as elevated banner
if st.session_state.disruption_history:
    disruption_alert = st.session_state.disruption_history[-1]
    if disruption_alert and disruption_alert.get("alert"):
        sev = disruption_alert.get("severity", "low").lower()
        if sev in ("high", "medium"):
            color = "#f85149" if sev == "high" else "#e3b341"
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid {color};
                border-left:4px solid {color};border-radius:8px;
                padding:12px 16px;margin-bottom:16px;
                display:flex;align-items:center;gap:12px;">
              <span style="color:{color};font-size:1rem;">⚠️</span>
              <div>
                <span style="color:{color};font-weight:600;
                    font-size:0.8rem;text-transform:uppercase;">
                  {sev.upper()} DISRUPTION ALERT
                </span>
                <span style="color:#8b949e;font-size:0.85rem;
                    margin-left:12px;">
                  {disruption_alert.get('summary','')}
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Module 0: Manager Admin Panel (accessible directly via ?admin_token=<UUID>)
# -----------------------------------------------------------------------------
if is_admin_mode:
    st.markdown(f"### ⚙️ Manager Admin Panel — Inventory Governance ({tenant_id})")
    st.markdown("Authorized managers can stage catalog modifications (Add, Edit, Delete). Changes enter the pending approvals queue and require sign-off before committing to the database.")

    # 1. Active Tenant Inventory Display
    st.markdown("#### Current Catalog Inventory")
    try:
        inventory_rows = execute_query(
            "SELECT id, item_name, quantity, transit_time, spot_rate, supplier_id FROM inventory WHERE tenant_id = ? ORDER BY id ASC",
            [tenant_id]
        )
        if inventory_rows:
            inv_df = pd.DataFrame(inventory_rows)
            st.dataframe(inv_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No inventory records found for {tenant_id}.")
    except Exception as e:
        show_user_error(friendly_error(e), "Try submitting your command again in a moment.")
        inventory_rows = []

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # 2. Add / Edit / Delete Inventory Actions
    tab_add, tab_edit, tab_del = st.tabs(["➕ Add New Item", "✏️ Edit Existing Item", "🗑️ Delete Item"])

    with tab_add:
        with st.form("admin_add_item_form"):
            st.markdown("**Request Addition of New Inventory Item**")
            add_name = st.text_input("Item / SKU Name", placeholder="e.g. Titanium Fasteners")
            c1, c2 = st.columns(2)
            with c1:
                add_qty = st.number_input("Quantity", min_value=0, value=1000, step=50)
                add_transit = st.number_input("Transit Time (days)", min_value=1, value=7, step=1)
            with c2:
                add_rate = st.number_input("Spot Rate ($)", min_value=0.0, value=250.0, step=10.0)
                add_supp = st.text_input("Supplier ID", value="SUP_NEW_01")

            add_submit = st.form_submit_button("Submit for Approval", type="primary")
            if add_submit:
                if not add_name.strip():
                    show_user_error("Item Name cannot be blank.", "Please enter a descriptive SKU or item name.")
                else:
                    execute_mutation(
                        """
                        INSERT INTO admin_requests (tenant_id, action, item_name, quantity, transit_time, spot_rate, supplier_id, status)
                        VALUES (?, 'ADD', ?, ?, ?, ?, ?, 'PENDING')
                        """,
                        [tenant_id, add_name.strip(), add_qty, add_transit, add_rate, add_supp.strip()]
                    )
                    append_activity_log("✅", "admin", f"Addition request for {add_name} submitted")
                    st.rerun()

    with tab_edit:
        if inventory_rows:
            item_options = {f"#{r['id']}: {r['item_name']}": r for r in inventory_rows}
            selected_edit_label = st.selectbox("Select Item to Edit", list(item_options.keys()))
            chosen_item = item_options[selected_edit_label]

            with st.form("admin_edit_item_form"):
                st.markdown(f"**Request Update for Item #{chosen_item['id']} ({chosen_item['item_name']})**")
                edit_name = st.text_input("Updated Item Name", value=chosen_item['item_name'])
                c1, c2 = st.columns(2)
                with c1:
                    edit_qty = st.number_input("Updated Quantity", min_value=0, value=int(chosen_item['quantity']), step=50)
                    edit_transit = st.number_input("Updated Transit Time (days)", min_value=1, value=int(chosen_item['transit_time']), step=1)
                with c2:
                    edit_rate = st.number_input("Updated Spot Rate ($)", min_value=0.0, value=float(chosen_item['spot_rate']), step=10.0)
                    edit_supp = st.text_input("Updated Supplier ID", value=chosen_item['supplier_id'])

                edit_submit = st.form_submit_button("Submit Update Request", type="primary")
                if edit_submit:
                    execute_mutation(
                        """
                        INSERT INTO admin_requests (tenant_id, action, item_id, item_name, quantity, transit_time, spot_rate, supplier_id, status)
                        VALUES (?, 'EDIT', ?, ?, ?, ?, ?, ?, 'PENDING')
                        """,
                        [tenant_id, chosen_item['id'], edit_name.strip(), edit_qty, edit_transit, edit_rate, edit_supp.strip()]
                    )
                    append_activity_log("✅", "admin", f"Update request for {edit_name} submitted")
                    st.rerun()
        else:
            st.info("No items available to edit.")

    with tab_del:
        if inventory_rows:
            item_del_options = {f"#{r['id']}: {r['item_name']} (Qty: {r['quantity']})": r for r in inventory_rows}
            selected_del_label = st.selectbox("Select Item to Delete", list(item_del_options.keys()))
            del_item = item_del_options[selected_del_label]

            with st.form("admin_del_item_form"):
                st.markdown(f"**Confirm Request to Delete Item #{del_item['id']} ({del_item['item_name']})**")
                st.caption("Submitting this request will stage item removal pending manager sign-off.")
                del_submit = st.form_submit_button("Submit Deletion Request", type="primary")
                if del_submit:
                    execute_mutation(
                        """
                        INSERT INTO admin_requests (tenant_id, action, item_id, item_name, quantity, transit_time, spot_rate, supplier_id, status)
                        VALUES (?, 'DELETE', ?, ?, ?, ?, ?, ?, 'PENDING')
                        """,
                        [tenant_id, del_item['id'], del_item['item_name'], del_item['quantity'], del_item['transit_time'], del_item['spot_rate'], del_item['supplier_id']]
                    )
                    append_activity_log("✅", "admin", f"Deletion request for {del_item['item_name']} submitted")
                    st.rerun()
        else:
            st.info("No items available to delete.")

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    st.divider()

    # 3. Pending Approvals Section
    st.markdown("#### ⏳ Pending Approvals Queue")
    try:
        pending_requests = execute_query(
            """
            SELECT id, tenant_id, action, item_id, item_name, quantity, transit_time, spot_rate, supplier_id, status, created_at
            FROM admin_requests
            WHERE tenant_id = ? AND status = 'PENDING'
            ORDER BY id ASC
            """,
            [tenant_id]
        )
    except Exception as e:
        show_user_error(friendly_error(e), "Try submitting your command again in a moment.")
        pending_requests = []

    if not pending_requests:
        st.info(f"No pending approval requests for {tenant_id}.")
    else:
        for req in pending_requests:
            req_id = req["id"]
            action = req["action"]
            item_name = req["item_name"]
            item_id = req["item_id"]
            qty = req["quantity"]
            transit = req["transit_time"]
            rate = req["spot_rate"]
            supp = req["supplier_id"]

            with st.container():
                st.markdown(
                    f"""
                    <div style="background: #161f30; border: 1px solid #232b3e; border-radius: 6px; padding: 0.85rem; margin-bottom: 0.5rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                            <strong>Request #{req_id}: {action} {item_name}</strong>
                            <span style="font-size: 0.75rem; background: #3b82f6; color: #ffffff; padding: 2px 6px; border-radius: 4px;">{action}</span>
                        </div>
                        <div style="font-size: 0.82rem; color: #94a3b8;">
                            Qty: <strong style="color: #f8fafc;">{qty}</strong> |
                            Transit: <strong style="color: #f8fafc;">{transit}d</strong> |
                            Rate: <strong style="color: #34d399;">${rate}</strong> |
                            Supplier: <strong style="color: #f8fafc;">{supp}</strong>
                            {f' | Target Item #{item_id}' if item_id else ''}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                c_app, c_rej, _ = st.columns([1, 1, 4])
                with c_app:
                    if st.button("Approve", key=f"app_req_{req_id}", type="primary"):
                        if action == "ADD":
                            execute_mutation(
                                "INSERT INTO inventory (tenant_id, item_name, quantity, transit_time, spot_rate, supplier_id) VALUES (?, ?, ?, ?, ?, ?)",
                                [tenant_id, item_name, qty, transit, rate, supp]
                            )
                        elif action == "EDIT" and item_id:
                            execute_mutation(
                                "UPDATE inventory SET item_name=?, quantity=?, transit_time=?, spot_rate=?, supplier_id=? WHERE id=? AND tenant_id=?",
                                [item_name, qty, transit, rate, supp, item_id, tenant_id]
                            )
                        elif action == "DELETE" and item_id:
                            execute_mutation(
                                "DELETE FROM inventory WHERE id=? AND tenant_id=?",
                                [item_id, tenant_id]
                            )

                        execute_mutation(
                            "UPDATE admin_requests SET status = 'APPROVED' WHERE id = ?",
                            [req_id]
                        )
                        log_dpo(
                            prompt=f"Admin {action} request for {item_name}",
                            chosen=f"Approved {action} request #{req_id} for {item_name} (Qty: {qty}, Rate: ${rate})",
                            rejected="Rejected"
                        )
                        append_activity_log("✅", "admin", f"Request #{req_id} approved")
                        st.rerun()

                with c_rej:
                    if st.button("Reject", key=f"rej_req_{req_id}"):
                        execute_mutation(
                            "UPDATE admin_requests SET status = 'REJECTED' WHERE id = ?",
                            [req_id]
                        )
                        log_dpo(
                            prompt=f"Admin {action} request for {item_name}",
                            chosen="",
                            rejected=f"Rejected {action} request #{req_id} for {item_name}"
                        )
                        append_activity_log("❌", "admin", f"Request #{req_id} rejected")
                        st.rerun()

# -----------------------------------------------------------------------------
# Module 1: Orchestrator
# -----------------------------------------------------------------------------
elif selected_module == "Orchestrator":
    # Initialize UI state
    if "chat_hidden" not in st.session_state:
        st.session_state.chat_hidden = False
    if "help_shown" not in st.session_state:
        st.session_state.help_shown = False
    if "active_input_mode" not in st.session_state:
        st.session_state.active_input_mode = None
    if "pending_image_choice" not in st.session_state:
        st.session_state.pending_image_choice = None
    if "last_processed_audio_hash" not in st.session_state:
        st.session_state.last_processed_audio_hash = None

    # Status Banner
    postgres_uri = os.environ.get("POSTGRES_DB_URI", "").strip()
    if DEMO_MODE:
        st.markdown(
            """
            <div class="alert-banner info">
                🎭 <strong>Demo Mode:</strong> AI responses are simulated. Set DEMO_MODE=0 and POSTGRES_DB_URI for live Meta AI calls.
            </div>
            """,
            unsafe_allow_html=True
        )
    elif not postgres_uri:
        st.markdown(
            """
            <div class="alert-banner warning">
                ⚠️ <strong>No database configured.</strong> Using local SQLite fallback. Add POSTGRES_DB_URI for persistent state across sessions.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class="alert-banner success">
                ✅ <strong>Live Mode:</strong> Connected to Meta AI and PostgreSQL.
            </div>
            """,
            unsafe_allow_html=True
        )

    # Disruption Alert Banner
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

    # Determine HITL status and pending PO
    hitl_status = "idle"
    pending_po = None
    pending_plan_content = ""

    if DEMO_MODE:
        if st.session_state.get("demo_paused_for_hitl"):
            hitl_status = "pending"
            pending_po = st.session_state.get("demo_pending_po")
            pending_plan_content = st.session_state.get("demo_pending_plan", "")
    elif os.environ.get("POSTGRES_DB_URI"):
        try:
            graph = get_graph_with_postgres()
            current_state = graph.get_state(config)
            if current_state.next == ('human_review',):
                hitl_status = "pending"
                pending_po = current_state.values.get("pending_po") if hasattr(current_state, "values") else None
                pending_plan_content = current_state.values.get("drafted_plan", "") if hasattr(current_state, "values") else ""
        except Exception:
            pass

    is_paused = (hitl_status == "pending")

    def get_action_slot_rank():
        """Single source of truth for Action Slot priority hierarchy."""
        if hitl_status == "pending":
            if st.session_state.get("help_shown"):
                st.session_state.help_shown = False
            return 1
        if st.session_state.get("pending_image_choice"):
            return 2
        if st.session_state.get("prefilled_prompt"):
            return 3
        if st.session_state.get("help_shown"):
            return 4
        return None

    action_rank = get_action_slot_rank()

    # Chat Header Controls: [Hide/Show Chat] and [Clear]
    col_chat_tgl, col_chat_clr, _ = st.columns([0.15, 0.12, 0.73])
    with col_chat_tgl:
        chat_btn_label = "Show Chat" if st.session_state.chat_hidden else "Hide Chat"
        if st.button(chat_btn_label, key="toggle_chat_btn"):
            st.session_state.chat_hidden = not st.session_state.chat_hidden
            st.rerun()

    with col_chat_clr:
        if st.button("Clear", key="clear_chat_btn", disabled=is_paused):
            st.session_state.chat_history = []
            st.session_state.help_shown = False
            st.session_state.prefilled_prompt = ""
            st.session_state.pending_image_choice = None
            st.session_state.shelf_context = None
            st.session_state.extracted_document = None
            append_activity_log("🧹", "orchestrator", "Conversation cleared")
            st.rerun()

    # Chat Area
    if st.session_state.chat_hidden:
        if hitl_status == "pending" and pending_po:
            po_id = pending_po.get("po_id") if "po_id" in pending_po else pending_po.get("id")
            if not po_id:
                append_activity_log("❌", "hitl", "PO data missing po_id key")
            lead_time = pending_po.get("lead_time_days") if "lead_time_days" in pending_po else pending_po.get("lead_time", 4)
            qty = pending_po.get("quantity") if "quantity" in pending_po else pending_po.get("restock_quantity", 500)
            price = pending_po.get("price_per_unit") if "price_per_unit" in pending_po else pending_po.get("unit_price", 14.20)
            amt_str = f"${qty * price:,.2f}" if isinstance(qty, (int, float)) and isinstance(price, (int, float)) else "$35,500.00"

            st.caption("💬 Chat hidden · click **[Show Chat]** to expand")
            st.markdown(f"**⚡ {po_id or 'PO-9402'} · {amt_str} · {lead_time} days** · awaiting operator approval")
        else:
            st.caption("💬 Chat hidden · click **[Show Chat]** to expand")
    else:
        chat_box = st.container(height=400, border=False)
        with chat_box:
            if not st.session_state.chat_history:
                with st.chat_message("assistant"):
                    st.write("🤖 How can I assist with your supply chain today?")
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    ts = msg.get("ts", "")
                    if ts:
                        st.caption(ts)
                    st.write(msg["content"])

            # Native Drawers inside chat container boundary
            if st.session_state.active_input_mode == "file":
                col_d_lbl, col_d_x = st.columns([0.85, 0.15])
                with col_d_lbl:
                    st.caption("📎 **Upload Logistics File (WAV, PNG, JPG, PDF)** — Limit 2MB")
                with col_d_x:
                    if st.button("✕ Close", key="close_file_drawer_btn", use_container_width=True):
                        st.session_state.active_input_mode = None
                        st.rerun()

                uploaded_file = st.file_uploader(
                    "Upload Logistics File",
                    type=["wav", "mp3", "png", "jpg", "jpeg", "pdf"],
                    key="unified_file_uploader",
                    label_visibility="collapsed"
                )

                if uploaded_file is not None:
                    try:
                        fbytes = uploaded_file.read()
                        fname = uploaded_file.name.lower()
                        if len(fbytes) > 2_000_000:
                            show_user_error("File size exceeds 2MB limit.", "Upload a smaller document or compressed image.")
                        elif fname.endswith((".wav", ".mp3")):
                            with st.spinner("Transcribing audio via Meta ASR..."):
                                res = process_voice_input(fbytes)
                                if res.get("status") == "ok" and res.get("transcription"):
                                    st.session_state.auto_submit_prompt = res["transcription"].strip()
                                else:
                                    show_user_error("Audio transcription failed.", "Speak clearly or type command.")
                        elif fname.endswith(".pdf"):
                            with st.spinner("Extracting logistics document..."):
                                doc_data = extract_document_data(fbytes)
                                st.session_state.extracted_document = doc_data
                                st.session_state.prefilled_prompt = f"Process document: {doc_data.get('raw_summary', 'Inbound shipping manifest')}"
                        else:
                            # Ambiguous image: Trigger Disambiguation Rank 2
                            st.session_state.pending_image_choice = {
                                "bytes": fbytes,
                                "name": uploaded_file.name
                            }
                    except Exception as e:
                        append_activity_log("❌", "upload", f"Upload error: {str(e)[:40]}")
                        show_user_error("File could not be processed.", "Please ensure the file is valid and under 2MB.")
                    finally:
                        if not st.session_state.get("pending_image_choice"):
                            st.session_state.active_input_mode = None
                        st.rerun()

            elif st.session_state.active_input_mode == "voice":
                col_v_lbl, col_v_x = st.columns([0.85, 0.15])
                with col_v_lbl:
                    st.caption("🎙️ **Voice Logistics Command**")
                with col_v_x:
                    if st.button("✕ Close", key="close_voice_drawer_btn", use_container_width=True):
                        st.session_state.active_input_mode = None
                        st.rerun()

                voice_audio = st.audio_input("Record voice instruction", key="voice_audio_input", label_visibility="collapsed")
                if voice_audio is not None and hasattr(voice_audio, "read"):
                    try:
                        voice_audio.seek(0)
                        audio_bytes = voice_audio.read()
                        if audio_bytes:
                            audio_hash = hashlib.md5(audio_bytes).hexdigest()
                            if st.session_state.get("last_processed_audio_hash") != audio_hash:
                                st.session_state.last_processed_audio_hash = audio_hash
                                with st.spinner("Transcribing voice command..."):
                                    v_res = process_voice_input(audio_bytes)
                                    if v_res.get("status") == "ok" and v_res.get("transcription"):
                                        st.session_state.auto_submit_prompt = v_res["transcription"].strip()
                                        st.session_state.active_input_mode = None
                                        st.rerun()
                                    else:
                                        show_user_error("Audio transcription unclear.", "Ensure microphone is active and speak clearly.")
                    except Exception as e:
                        append_activity_log("❌", "voice", f"Voice error: {str(e)[:40]}")
                        show_user_error("Voice processing error.", "Please type your instruction in the command bar.")
                    finally:
                        st.session_state.active_input_mode = None

    # ACTION SLOT - Ranked Priority Slot between Chat and Input Bar
    if action_rank == 1 and pending_po:
        # Rank 1: HITL Operator Approval
        po_id = pending_po.get("po_id") if "po_id" in pending_po else pending_po.get("id")
        lead_time = pending_po.get("lead_time_days") if "lead_time_days" in pending_po else pending_po.get("lead_time", 4)
        c_app, c_rej = st.columns([0.5, 0.5])
        with c_app:
            if st.button("✅ APPROVE", key="action_slot_approve_btn", type="primary", use_container_width=True):
                st.session_state["hitl_approved"] = True
                log_dpo(
                    st.session_state.get('pending_prompt', ''),
                    st.session_state.get('demo_pending_plan', st.session_state.get('pending_plan', '')),
                    ""
                )
                conf_msg = f"🤖 ✅ Purchase Order {po_id or 'PO-9402'} approved and dispatched. Carrier route initiated with ETA {lead_time} days."
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": conf_msg,
                    "ts": time.strftime("%H:%M:%S")
                })
                append_activity_log("⚡", "orchestrator", f"{po_id or 'PO-9402'} approved by operator")
                if DEMO_MODE:
                    if st.session_state.get("demo_pending_po"):
                        po = st.session_state.demo_pending_po
                        item = po.get("item_name", "")
                        qty = po.get("restock_quantity", 500)
                        if item:
                            try:
                                execute_mutation(
                                    "UPDATE inventory SET quantity = quantity + ? WHERE tenant_id = ? AND LOWER(item_name) LIKE ?",
                                    [qty, tenant_id, f"%{item.lower()[:8]}%"]
                                )
                            except Exception:
                                pass
                    st.session_state.demo_paused_for_hitl = False
                    st.session_state.demo_pending_po = None
                else:
                    graph.update_state(config, {"status": "approved"})
                    for event in graph.stream(None, config):
                        pass
                st.rerun()

        with c_rej:
            if st.button("❌ REJECT", key="action_slot_reject_btn", use_container_width=True):
                log_dpo(
                    st.session_state.get('pending_prompt', ''),
                    "",
                    st.session_state.get('demo_pending_plan', st.session_state.get('pending_plan', ''))
                )
                rej_msg = f"🤖 ❌ Purchase Order {po_id or 'PO-9402'} rejected by operator."
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": rej_msg,
                    "ts": time.strftime("%H:%M:%S")
                })
                append_activity_log("❌", "orchestrator", f"{po_id or 'PO-9402'} rejected by operator")
                if DEMO_MODE:
                    st.session_state.demo_paused_for_hitl = False
                    st.session_state.demo_pending_po = None
                else:
                    graph.update_state(config, {"status": "rejected"})
                    for event in graph.stream(None, config):
                        pass
                st.rerun()

    elif action_rank == 2 and st.session_state.get("pending_image_choice"):
        # Rank 2: Image Disambiguation
        img_info = st.session_state.pending_image_choice
        c_dis_sh, c_dis_doc, c_dis_cancel = st.columns([0.4, 0.4, 0.2])
        with c_dis_sh:
            if st.button("Analyze as Warehouse Shelf (SAM 3.1)", key="dis_shelf_btn", use_container_width=True):
                with st.spinner("Analyzing shelf with Meta SAM 3.1..."):
                    analysis = analyze_shelf_image(img_info["bytes"])
                    st.session_state.shelf_context = analysis
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"🤖 **Warehouse Shelf Analyzed:** {analysis.get('summary', 'Low stock detected.')}",
                        "ts": time.strftime("%H:%M:%S")
                    })
                    st.session_state.pending_image_choice = None
                    st.session_state.active_input_mode = None
                    st.rerun()

        with c_dis_doc:
            if st.button("Extract as Shipping Document (Muse)", key="dis_doc_btn", use_container_width=True):
                with st.spinner("Extracting with Meta muse-image-1.0..."):
                    doc_data = extract_document_data(img_info["bytes"])
                    st.session_state.extracted_document = doc_data
                    st.session_state.prefilled_prompt = f"Process document: {doc_data.get('raw_summary', 'Inbound shipping invoice')}"
                    st.session_state.pending_image_choice = None
                    st.session_state.active_input_mode = None
                    st.rerun()

        with c_dis_cancel:
            if st.button("✕ Cancel", key="dis_cancel_btn", use_container_width=True):
                st.session_state.pending_image_choice = None
                st.session_state.active_input_mode = None
                st.rerun()

    elif action_rank == 3 and st.session_state.get("prefilled_prompt"):
        # Rank 3: Document Prefill Action Button
        p_text = st.session_state.prefilled_prompt
        col_pf_btn, col_pf_cls = st.columns([0.85, 0.15])
        with col_pf_btn:
            if st.button(f"📋 Send Draft Instruction: {p_text[:45]}...", key="action_send_prefill_btn", type="primary", use_container_width=True):
                st.session_state.auto_submit_prompt = p_text
                st.session_state.prefilled_prompt = ""
                st.rerun()
        with col_pf_cls:
            if st.button("✕ Dismiss", key="action_dismiss_prefill_btn", use_container_width=True):
                st.session_state.prefilled_prompt = ""
                st.rerun()

    elif action_rank == 4 and st.session_state.get("help_shown"):
        # Rank 4: Help Downloads (3 downloads in Row 1, Full-Width Dismiss in Row 2)
        from pathlib import Path
        assets_dir = Path(__file__).resolve().parent / "demo-assets"
        sample_voice = assets_dir / "sample_voice_command.wav"
        sample_shelf = assets_dir / "sample_shelf.jpg"
        sample_invoice = assets_dir / "sample_invoice.png"

        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            if sample_voice.exists():
                st.download_button(
                    "⬇️ Audio (.wav)",
                    sample_voice.read_bytes(),
                    file_name="sample_voice_command.wav",
                    mime="audio/wav",
                    key="dl_audio_action_btn",
                    use_container_width=True
                )
        with col_h2:
            if sample_shelf.exists():
                st.download_button(
                    "⬇️ Shelf (.jpg)",
                    sample_shelf.read_bytes(),
                    file_name="sample_shelf.jpg",
                    mime="image/jpeg",
                    key="dl_shelf_action_btn",
                    use_container_width=True
                )
        with col_h3:
            if sample_invoice.exists():
                st.download_button(
                    "⬇️ Invoice (.png)",
                    sample_invoice.read_bytes(),
                    file_name="sample_invoice.png",
                    mime="image/png",
                    key="dl_invoice_action_btn",
                    use_container_width=True
                )

        if st.button("✕ Dismiss Help", key="dismiss_help_btn", use_container_width=True):
            st.session_state.help_shown = False
            append_activity_log("ℹ️", "help", "Help dismissed")
            st.rerun()

    # COMBINED INPUT BAR - Fixed 5-Column Grid [0.05, 0.05, 0.05, 0.75, 0.1]
    st.markdown('<div class="combined-input-row">', unsafe_allow_html=True)
    col_q, col_clip, col_mic, col_txt, col_send = st.columns([0.05, 0.05, 0.05, 0.75, 0.1])

    with col_q:
        if st.button("?", key="btn_help_trigger", disabled=is_paused, use_container_width=True):
            if not st.session_state.get("help_shown"):
                st.session_state.help_shown = True
                help_text = (
                    "🤖 **Autonomous Supply Chain Orchestrator**\n\n"
                    "Type instructions, upload logistics files, or speak.\n\n"
                    "```\nCheck stock levels for Widget-A\n```\n"
                    "```\nReorder 500 Microcontrollers\n```\n"
                    "```\nEmergency restock Semiconductors\n```"
                )
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": help_text,
                    "ts": time.strftime("%H:%M:%S")
                })
                append_activity_log("ℹ️", "help", "Help guide displayed")
                st.rerun()

    with col_clip:
        if st.button("📎", key="btn_file_trigger", disabled=is_paused, use_container_width=True):
            if st.session_state.get("help_shown"):
                st.session_state.help_shown = False
                append_activity_log("ℹ️", "help", "Help dismissed on file drawer open")
            st.session_state.active_input_mode = "file" if st.session_state.active_input_mode != "file" else None
            st.rerun()

    with col_mic:
        if st.button("🎙️", key="btn_voice_trigger", disabled=is_paused, use_container_width=True):
            if st.session_state.get("help_shown"):
                st.session_state.help_shown = False
                append_activity_log("ℹ️", "help", "Help dismissed on voice drawer open")
            st.session_state.active_input_mode = "voice" if st.session_state.active_input_mode != "voice" else None
            st.rerun()

    with col_txt:
        input_placeholder = "Awaiting PO decision..." if is_paused else "Type a command..."
        cmd_text = st.text_input(
            "Command Input",
            placeholder=input_placeholder,
            key="combined_cmd_input_field",
            disabled=is_paused,
            label_visibility="collapsed"
        )

    with col_send:
        # Conditionally render ➔ only when cmd_text has content, not paused, and voice drawer inactive
        if cmd_text and not is_paused and st.session_state.active_input_mode != "voice":
            if st.button("➔", key="combined_cmd_submit_btn", type="primary", use_container_width=True):
                st.session_state.auto_submit_prompt = cmd_text
                st.session_state["dispatch_ts"] = time.time()
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Activity Log
    render_activity_log(disabled=is_paused)
