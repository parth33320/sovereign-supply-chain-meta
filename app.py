import streamlit as st
import sqlite3
import json
import uuid
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

DEMO_MODE = os.environ.get("DEMO_MODE") == "1"

_api_key = os.environ.get("META_API_KEY")
if not _api_key:
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
<div id="ssc-loader" style="
    position:fixed;inset:0;background:#0d1117;
    display:flex;flex-direction:column;
    align-items:center;justify-content:center;
    z-index:999999;transition:opacity 0.4s ease;">
  <div style="font-size:1.4rem;color:#58a6ff;
      font-weight:600;font-family:sans-serif;">
    Sovereign Supply Chain
  </div>
  <div style="color:#8b949e;font-size:0.85rem;
      margin-top:8px;font-family:sans-serif;">
    Initializing AI agents...
  </div>
</div>
<script>
  window.addEventListener('load', function() {
    setTimeout(function() {
      var el = document.getElementById('ssc-loader');
      if (el) { el.style.opacity='0';
        setTimeout(function(){el.remove();},400); }
    }, 800);
  });
</script>
""", unsafe_allow_html=True)


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
st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)

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

def show_user_error(message: str, suggestion: str):
    """
    Renders a styled HTML card with a ⚠️ icon, plain-English error headline, and a 'What to do next:' line.
    Replaces raw st.error calls across the application.
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
    if not ADMIN_SECRET:
        return False
    params = st.query_params
    token = params.get("admin_token", "")
    return token == ADMIN_SECRET

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

# Navigation Rail (Left Sidebar) - Admin only appears when admin_token is valid
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

    modules = ["Orchestrator", "Warehouse", "Documents"]
    if is_authorized_admin:
        modules.append("Admin")
        if st.session_state.active_nav_module not in modules or st.session_state.get("_admin_default_set") is None:
            st.session_state.active_nav_module = "Admin"
            st.session_state._admin_default_set = True
    elif st.session_state.active_nav_module == "Admin":
        st.session_state.active_nav_module = "Orchestrator"

    current_idx = modules.index(st.session_state.active_nav_module) if st.session_state.active_nav_module in modules else 0
    selected_module = st.radio(
        "Navigation",
        modules,
        index=current_idx,
        label_visibility="collapsed",
        key="main_nav_radio"
    )
    switch_module(selected_module)
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

    st.markdown("<div style='margin-top: auto; padding-top: 2rem;'></div>", unsafe_allow_html=True)
    st.caption("Environment: Meta Foundation Cloud\nv1.6.0-enterprise")

# Global Top Header Bar
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

                st.session_state.pending_plan = drafted_plan
        except Exception as e:
            st.error(friendly_error(e))


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
                st.error(friendly_error(e))

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

    fuzzy_err = check_missing_item_and_suggest(to_submit, tenant_id)
    if fuzzy_err:
        show_user_error(fuzzy_err[0], fuzzy_err[1])
    elif not check_prompt_injection(to_submit):
        st.session_state.waf_count += 1
        st.session_state.waf_history.append({"timestamp": time.strftime("%H:%M:%S"), "count": 1})
        show_toast("Request blocked. See suggestions below.", "warning")
        st.session_state["prefill_prompt"] = ""
        st.session_state.prefilled_prompt = ""
        st.session_state.show_guardrail_help = True
    else:
        if not check_rate_limit(tenant_id):
            st.warning("⏳ Please wait a few seconds before sending another request.")
            st.stop()

        st.session_state.chat_history.append({"role": "user", "content": to_submit})
        request_id = str(uuid.uuid4())
        dispatched_prompt = to_submit
        if st.session_state.get("shelf_context") and st.session_state["shelf_context"].get("summary"):
            summary_text = st.session_state["shelf_context"]["summary"]
            dispatched_prompt = f"[VISUAL SHELF ANALYSIS: {summary_text}]\n{to_submit}"

        st.session_state.pending_prompt = dispatched_prompt
        if DEMO_MODE:
            resp_plan = (
                f"Orchestrator Analysis for '{to_submit}':\n"
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
        else:
            execute_agent_synchronous(dispatched_prompt, tenant_id, request_id)
        st.rerun()


# Fix 4: Breadcrumb at top of main content area
module_name = st.session_state.get("active_module", selected_module)
st.markdown(f"""
<div style="font-size:0.75rem;color:#8b949e;
    margin-bottom:16px;font-family:sans-serif;">
  🏭 Sovereign Supply Chain
  <span style="margin:0 6px;color:#30363d;">›</span>
  <span style="color:#e6edf3;">{module_name}</span>
</div>
""", unsafe_allow_html=True)

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
        st.error(friendly_error(e))
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
                    st.success(f"Addition request for '{add_name}' submitted for approval!")
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
                    st.success(f"Update request for '{edit_name}' submitted for approval!")
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
                st.warning("Submitting this request will stage item removal pending manager sign-off.")
                del_submit = st.form_submit_button("Submit Deletion Request", type="primary")
                if del_submit:
                    execute_mutation(
                        """
                        INSERT INTO admin_requests (tenant_id, action, item_id, item_name, quantity, transit_time, spot_rate, supplier_id, status)
                        VALUES (?, 'DELETE', ?, ?, ?, ?, ?, ?, 'PENDING')
                        """,
                        [tenant_id, del_item['id'], del_item['item_name'], del_item['quantity'], del_item['transit_time'], del_item['spot_rate'], del_item['supplier_id']]
                    )
                    st.success(f"Deletion request for '{del_item['item_name']}' submitted for approval!")
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
        st.error(friendly_error(e))
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
                        st.success(f"Request #{req_id} ({action}) approved and applied to database!")
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
                        st.warning(f"Request #{req_id} ({action}) rejected.")
                        st.rerun()

# -----------------------------------------------------------------------------
# Module 1: Orchestrator
# -----------------------------------------------------------------------------
elif selected_module == "Orchestrator":
    # Friendly Status Banner (exactly one banner shown)
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

    if is_paused:
        col_main, col_hitl = st.columns([2, 1])
    else:
        col_main = st.container()
        col_hitl = None

    if col_hitl is not None:
        with col_hitl:
            po_num = pending_po.get("po_number", pending_po.get("id", "PO-2025-001")) if pending_po else "PO-2025-001"
            supp = pending_po.get("supplier", "Supplier B") if pending_po else "Supplier B"
            qty = pending_po.get("quantity", pending_po.get("restock_quantity", 500)) if pending_po else 500
            price_val = pending_po.get("price_per_unit", pending_po.get("unit_price", 10.0)) if pending_po else 10.0
            amt = f"${qty * price_val:,.2f}" if isinstance(qty, (int, float)) and isinstance(price_val, (int, float)) else "$5,000.00"
            summary_txt = pending_plan_content if pending_plan_content else "Emergency Restock Order for Microcontrollers"

            # Fix 7: HITL Card Visual Elevation
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #e3b341;border-left:4px solid #e3b341;border-radius:8px;padding:20px;margin:16px 0;">
                <div style="font-size:0.75rem;color:#e3b341;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-bottom:12px;">
                    ⏸ AWAITING YOUR APPROVAL
                </div>
                <div style="color:#e6edf3;font-size:0.9rem;margin-bottom:16px;">
                    {summary_txt}
                </div>
                <div style="color:#8b949e;font-size:0.8rem;">
                    PO {po_num} · {supp} · {amt}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if pending_po:
                sku = pending_po.get("sku", "N/A")
                lead_time = pending_po.get("lead_time_days", "N/A")

                st.markdown(
                    f"""
                    <div style="background: #161f30; border: 1px solid #232b3e; border-radius: 6px; padding: 0.85rem; margin-bottom: 0.85rem;">
                        <div style="font-size: 0.78rem; font-weight: 700; color: #3b82f6; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">
                            📦 Purchase Order Summary
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.84rem;">
                            <div><span style="color: #94a3b8;">Supplier:</span> <strong style="color: #f8fafc;">{supp}</strong></div>
                            <div><span style="color: #94a3b8;">SKU:</span> <strong style="color: #f8fafc;">{sku}</strong></div>
                            <div><span style="color: #94a3b8;">Quantity:</span> <strong style="color: #f8fafc;">{qty:,} units</strong></div>
                            <div><span style="color: #94a3b8;">Price / Unit:</span> <strong style="color: #34d399;">${price_val:,.2f}</strong></div>
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
                if st.button("✅ Approve", type="primary", key="hitl_approve_btn", use_container_width=True):
                    # Fix 8: Success State After Approve
                    st.markdown("""
                    <div style="background:#0d1117;border:1px solid #3fb950;border-left:4px solid #3fb950;border-radius:8px;padding:20px;margin:16px 0;text-align:center;">
                        <div style="font-size:1.4rem;margin-bottom:8px;">✅</div>
                        <div style="color:#3fb950;font-weight:600;font-size:0.95rem;">Plan Approved</div>
                        <div style="color:#8b949e;font-size:0.8rem;margin-top:4px;">
                            Executing with AI agents...
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    show_toast("Plan approved", "success")
                    log_dpo(
                        st.session_state.get('pending_prompt', ''),
                        st.session_state.get('demo_pending_plan', st.session_state.get('pending_plan', '')),
                        ""
                    )
                    st.session_state["hitl_approved"] = True
                    if DEMO_MODE:
                        st.session_state.demo_paused_for_hitl = False
                        st.session_state.chat_history.append({"role": "assistant", "content": "Plan Approved and Executed."})
                        st.rerun()
                    else:
                        graph.update_state(config, {"status": "approved"})
                        for event in graph.stream(None, config):
                            pass
                        st.session_state.chat_history.append({"role": "assistant", "content": "Plan Approved and Executed."})
                        st.rerun()

            with col_rej:
                if st.button("✗ Reject", key="hitl_reject_btn", use_container_width=True):
                    log_dpo(
                        st.session_state.get('pending_prompt', ''),
                        "",
                        st.session_state.get('demo_pending_plan', st.session_state.get('pending_plan', ''))
                    )
                    show_toast("Plan rejected", "warning")
                    if DEMO_MODE:
                        st.session_state.demo_paused_for_hitl = False
                        st.session_state.chat_history.append({"role": "assistant", "content": "Plan Rejected."})
                        show_user_error(
                            message="The proposed logistics plan was rejected by the operator.",
                            suggestion="Submit a revised command specifying different quantity or supplier requirements."
                        )
                        st.rerun()
                    else:
                        graph.update_state(config, {"status": "rejected"})
                        for event in graph.stream(None, config):
                            pass
                        st.session_state.chat_history.append({"role": "assistant", "content": "Plan Rejected."})
                        show_user_error(
                            message="The proposed logistics plan was rejected by the operator.",
                            suggestion="Submit a revised command specifying different quantity or supplier requirements."
                        )
                        st.rerun()

    # Main Conversation Area
    with col_main:
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("""
                <div class="ssc-card" style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:24px;margin-bottom:16px;">
                  <div style="font-size:1.15rem;font-weight:700;color:#f8fafc;margin-bottom:8px;">
                    👋 Welcome to Sovereign Supply Chain
                  </div>
                  <div style="color:#8b949e;font-size:0.875rem;margin-bottom:16px;">
                    Try one of these to get started:
                  </div>
                </div>
                """, unsafe_allow_html=True)
                col_onb1, col_onb2, col_onb3 = st.columns(3)
                with col_onb1:
                    if st.button("🔴 Check Widget-A stockout", use_container_width=True, key="onb_btn_1"):
                        st.session_state["prefill_prompt"] = "Check Widget-A stockout"
                        st.session_state.prefilled_prompt = "Check Widget-A stockout"
                        st.session_state.auto_submit_prompt = "Check Widget-A stockout"
                        st.rerun()
                with col_onb2:
                    if st.button("📦 Reorder Semiconductors", use_container_width=True, key="onb_btn_2"):
                        st.session_state["prefill_prompt"] = "Reorder Semiconductors"
                        st.session_state.prefilled_prompt = "Reorder Semiconductors"
                        st.session_state.auto_submit_prompt = "Reorder Semiconductors"
                        st.rerun()
                with col_onb3:
                    if st.button("🤝 Negotiate with Supplier B", use_container_width=True, key="onb_btn_3"):
                        st.session_state["prefill_prompt"] = "Negotiate with Supplier B"
                        st.session_state.prefilled_prompt = "Negotiate with Supplier B"
                        st.session_state.auto_submit_prompt = "Negotiate with Supplier B"
                        st.rerun()
                st.markdown("""
                <div style="color:#8b949e;font-size:0.85rem;margin-top:12px;margin-bottom:16px;">
                  Or type your own warehouse command ↓
                </div>
                """, unsafe_allow_html=True)
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        if st.session_state.get("prefilled_prompt"):
            st.info(f"📋 **Draft Logistics Instruction from Document:**\n\n_{st.session_state.prefilled_prompt}_")
            if st.button("Send Instruction to Orchestrator", key="send_prefilled_instruction_btn", type="primary"):
                st.session_state.auto_submit_prompt = st.session_state.prefilled_prompt
                st.session_state.prefilled_prompt = ""
                st.rerun()

        # Collapsible Example Inputs Expander (20 Voice Commands)
        voice_examples = [x for x in GOLD_INPUTS if x.get("type") == "voice"]
        if voice_examples:
            with st.expander("📋 Example Inputs (20 Voice Commands)", expanded=False):
                st.caption("Click **Use** next to any command to auto-populate and immediately dispatch it to the Orchestrator.")
                for i, ex in enumerate(voice_examples):
                    c_txt, c_btn = st.columns([5, 1])
                    with c_txt:
                        st.markdown(f"**{i+1}.** _{ex.get('input')}_")
                        st.caption(f"Expected: {ex.get('expected_outcome')}")
                    with c_btn:
                        if st.button("Use", key=f"use_voice_ex_{i}", use_container_width=True):
                            st.session_state.auto_submit_prompt = ex.get("input")
                            st.rerun()

        # Operational Voice Command Input
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
                            st.session_state.auto_submit_prompt = transcript
                            st.rerun()
                    else:
                        err_intent = voice_result.get("intent", "Audio input unclear")
                        if "META_API_KEY" in err_intent or "ValueError" in err_intent:
                            show_user_error(
                                message="⚠️ Voice transcription requires a META_API_KEY. Add it to your Render environment variables.",
                                suggestion="Add META_API_KEY to your environment variables or .env file, or type your instruction directly in the chat box."
                            )
                        else:
                            show_user_error(
                                message=f"We had trouble processing your voice audio: {err_intent}.",
                                suggestion="Ensure your microphone is connected, speak clearly within 3 feet, or type your instruction directly in the chat box."
                            )

        # Fix 11: Guardrail Help Card
        if st.session_state.get("show_guardrail_help"):
            st.markdown("""
            <div class="ssc-card" style="border-color:#e3b341;border:1px solid #e3b341;border-radius:8px;padding:16px;margin:16px 0;background:#161b22;">
              <div class="ssc-section-header" style="color:#e3b341;font-weight:600;font-size:0.8rem;letter-spacing:0.08em;margin-bottom:8px;">
                ⚡ WHAT TO TRY INSTEAD
              </div>
              <div style="color:#8b949e;font-size:0.85rem;line-height:1.8;">
                ✓ "Check stock levels for Semiconductors"<br>
                ✓ "Reorder 500 units of Widget-A"<br>
                ✓ "Emergency stockout on Microcontrollers"<br>
                <a href="#" style="color:#58a6ff;font-size:0.8rem;">
                  See all 20 example inputs ↓
                </a>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Fix 5: Agent Progress Indicator
        task_status = st.session_state.get("task_status", "IDLE")
        render_agent_progress(task_status)

        # Text Logistics Command Input
        prompt = st.chat_input("Enter logistics instruction...")
        if prompt:
            st.session_state.auto_submit_prompt = prompt
            st.session_state["dispatch_ts"] = time.time()
            st.rerun()


# -----------------------------------------------------------------------------
# Module 2: Warehouse Vision
# -----------------------------------------------------------------------------
elif selected_module == "Warehouse":
    st.markdown("### 📦 Warehouse Vision & Inventory Segmentation")
    st.markdown("Automated stock segmentation powered by Meta SAM 3.1. Upload shelf imagery to detect low-stock or empty SKU bins.")

    # Collapsible Example Inputs for Shelf Images
    shelf_examples = [x for x in GOLD_INPUTS if x.get("type") == "shelf"]
    if shelf_examples:
        with st.expander("📋 Example Inputs (20 Shelf Inspection Scenarios)", expanded=False):
            st.caption("Click **Use** to inject the visual scenario directly into the active shelf context.")
            for i, ex in enumerate(shelf_examples):
                c_txt, c_btn = st.columns([5, 1])
                with c_txt:
                    st.markdown(f"**{i+1}.** {ex.get('input')}")
                    st.caption(f"Expected: {ex.get('expected_outcome')}")
                with c_btn:
                    if st.button("Use", key=f"use_shelf_ex_{i}", use_container_width=True):
                        is_empty = "empty" in ex.get('input').lower() or "vacant" in ex.get('input').lower() or "devoid" in ex.get('input').lower()
                        fill_lvl = 0.0 if is_empty else 0.75
                        status = "empty" if is_empty else "ok"
                        st.session_state.shelf_context = {
                            "summary": ex.get("input"),
                            "items": [{"item": "Inspected SKU", "fill_level": fill_lvl, "status": status}]
                        }
                        st.success("Shelf scenario applied to active visual context!")
                        st.rerun()

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
                show_user_error(
                    message="The uploaded shelf photo exceeds the 1MB file size limit.",
                    suggestion="Please compress the image or take a lower resolution photo before uploading."
                )
            else:
                image_bytes = uploaded_image.read()
                image_id = hash(image_bytes)
                if st.session_state.get("last_uploaded_image_id") != image_id:
                    st.session_state.last_uploaded_image_id = image_id
                    with st.spinner("Analyzing shelf image with SAM 3.1..."):
                        try:
                            analysis = analyze_shelf_image(image_bytes)
                            st.session_state.shelf_context = analysis
                            st.rerun()
                        except Exception as e:
                            st.error(friendly_error(e))

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
            st.info("No active shelf image analyzed. Upload an image or select an example scenario above.")


# -----------------------------------------------------------------------------
# Module 3: Documents
# -----------------------------------------------------------------------------
elif selected_module == "Documents":
    st.markdown("### 📄 Document & Invoice Extraction")
    st.markdown("Automated structured data extraction powered by Meta muse-image-1.0. Upload invoices, bills of lading, and freight manifests.")

    # Collapsible Example Inputs for Invoice Line Items
    invoice_examples = [x for x in GOLD_INPUTS if x.get("type") == "invoice"]
    if invoice_examples:
        with st.expander("📋 Example Inputs (20 Invoice Line Items)", expanded=False):
            st.caption("Click **Use** to immediately populate and stage the extracted logistics data.")
            for i, ex in enumerate(invoice_examples):
                c_txt, c_btn = st.columns([5, 1])
                with c_txt:
                    st.markdown(f"**{i+1}.** {ex.get('input')}")
                    st.caption(f"Expected: {ex.get('expected_outcome')}")
                with c_btn:
                    if st.button("Use", key=f"use_inv_ex_{i}", use_container_width=True):
                        st.session_state.extracted_document = {
                            "supplier": "FastFreight Logistics",
                            "items": [{"description": ex.get("input")[:50], "quantity": 100, "unit_price": 45.0}],
                            "dates": ["2026-11-05"],
                            "raw_summary": ex.get("input")
                        }
                        st.session_state.prefilled_prompt = f"Process incoming shipment from FastFreight Logistics: receive 100x items based on '{ex.get('input')[:60]}' into inventory."
                        st.success("Invoice example loaded into structured extraction view!")
                        st.rerun()

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
                show_user_error(
                    message="The uploaded document exceeds the 2MB size limit.",
                    suggestion="Please scan the document at 200 DPI or compress the PDF/image before uploading."
                )
            else:
                doc_bytes = uploaded_doc.read()
                doc_id = hash(doc_bytes)
                if st.session_state.get("last_uploaded_doc_id") != doc_id:
                    st.session_state.last_uploaded_doc_id = doc_id
                    with st.spinner("Extracting document data with muse-image-1.0..."):
                        try:
                            extraction = extract_document_data(doc_bytes)
                            st.session_state.extracted_document = extraction
                            st.session_state.prefilled_prompt = format_logistics_instruction(extraction)
                            st.rerun()
                        except Exception as e:
                            st.error(friendly_error(e))

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
            st.info("No document uploaded. Upload a document or select an example invoice line item above.")


# -----------------------------------------------------------------------------
