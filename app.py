import streamlit as st
import sqlite3
import json
import uuid
import time
from dotenv import load_dotenv
from guardrails import check_prompt_injection
from voice_handler import process_voice_input
from warehouse_vision import analyze_shelf_image

# Load environment variables
load_dotenv()
from graph import get_graph_with_postgres, log_dpo
from worker import process_agent_task
from celery.result import AsyncResult
from generate_synthetic_load import generate_load
from langchain_core.messages import HumanMessage, AIMessage

# Initialization
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'waf_count' not in st.session_state:
    st.session_state.waf_count = 0
if 'shelf_context' not in st.session_state:
    st.session_state.shelf_context = None

config = {"configurable": {"thread_id": st.session_state.thread_id}}

st.set_page_config(page_title="Sovereign Supply Chain Orchestrator", layout="wide")

# Header
st.title("Sovereign Supply Chain Orchestrator (MVP)")
tenant_id = st.selectbox("Select Active Tenant (Multi-Tenant Isolation)", ["Tenant_A", "Tenant_B"])

# Sidebar
with st.sidebar:
    st.header("Warehouse Vision")
    uploaded_image = st.file_uploader("Upload Shelf Image", type=["png", "jpg", "jpeg", "webp"], key="shelf_image_uploader")
    if uploaded_image is not None:
        if uploaded_image.size > 1_000_000:
            st.error("File too large. Please upload under 1MB.")
            st.stop()

        image_bytes = uploaded_image.read()
        image_id = hash(image_bytes)
        if st.session_state.get("last_uploaded_image_id") != image_id:
            st.session_state.last_uploaded_image_id = image_id
            with st.spinner("Analyzing shelf image with SAM 3.1..."):
                analysis = analyze_shelf_image(image_bytes)
                st.session_state.shelf_context = analysis

    if st.session_state.get("shelf_context"):
        ctx = st.session_state.shelf_context
        st.subheader("Shelf Analysis")
        st.write(f"**Summary:** {ctx.get('summary', '')}")
        items = ctx.get("items", [])
        if items:
            for itm in items:
                fill_pct = int(itm.get("fill_level", 0.0) * 100)
                st.write(f"- **{itm.get('item')}**: {fill_pct}% fill ({itm.get('status', 'ok')})")
        if st.button("Clear Shelf Context", key="clear_shelf_context_btn"):
            st.session_state.shelf_context = None
            st.session_state.last_uploaded_image_id = None
            st.rerun()

    st.divider()

    st.header("Security & Diagnostics")
    st.metric(label="WAF Rate-Limit Count", value=st.session_state.waf_count)

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

# Main Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Orchestrator Chat")

    # Display chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Voice Input (placed above text chat input)
    voice_audio = st.audio_input("Record voice instruction", key="voice_audio_input")
    if voice_audio is not None:
        # Check if this audio has already been processed to avoid infinite reruns
        audio_bytes = voice_audio.read()
        audio_id = hash(audio_bytes)
        if st.session_state.get("last_processed_audio_id") != audio_id:
            st.session_state.last_processed_audio_id = audio_id
            with st.spinner("Processing voice input..."):
                voice_result = process_voice_input(audio_bytes)
                if voice_result.get("status") == "ok":
                    transcript = voice_result.get("transcription", "").strip()
                    if transcript:
                        # Auto-submit transcript into orchestrator pipeline
                        if not check_prompt_injection(transcript):
                            st.session_state.waf_count += 1
                            st.error("SECURITY ALERT: Malicious prompt detected and blocked by Semantic Bouncer.")
                        else:
                            st.session_state.chat_history.append({"role": "user", "content": transcript})
                            request_id = str(uuid.uuid4())
                            dispatched_prompt = transcript
                            if st.session_state.get("shelf_context") and st.session_state["shelf_context"].get("summary"):
                                summary_text = st.session_state["shelf_context"]["summary"]
                                dispatched_prompt = f"[VISUAL SHELF ANALYSIS: {summary_text}]\n{transcript}"

                            state = {
                                "messages": [HumanMessage(content=dispatched_prompt)],
                                "tenant_id": tenant_id,
                                "request_id": request_id,
                                "status": "init"
                            }
                            task = process_agent_task.delay(tenant_id, request_id, dispatched_prompt)
                            st.session_state.pending_task_id = task.id
                            st.session_state.pending_request_id = request_id
                            st.session_state.pending_prompt = dispatched_prompt
                            st.rerun()
                else:
                    st.error(f"Voice processing error: {voice_result.get('intent', 'Unknown error')}")

    # Chat Input
    prompt = st.chat_input("Enter logistics instruction...")
    if prompt:
        # Semantic Bouncer
        if not check_prompt_injection(prompt):
            st.session_state.waf_count += 1
            st.error("SECURITY ALERT: Malicious prompt detected and blocked by Semantic Bouncer.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processing via LangGraph Orchestrator..."):
                    request_id = str(uuid.uuid4())

                    dispatched_prompt = prompt
                    if st.session_state.get("shelf_context") and st.session_state["shelf_context"].get("summary"):
                        summary_text = st.session_state["shelf_context"]["summary"]
                        dispatched_prompt = f"[VISUAL SHELF ANALYSIS: {summary_text}]\n{prompt}"

                    state = {
                        "messages": [HumanMessage(content=dispatched_prompt)],
                        "tenant_id": tenant_id,
                        "request_id": request_id,
                        "status": "init"
                    }

                    # Dispatch task to Celery
                    task = process_agent_task.delay(tenant_id, request_id, dispatched_prompt)
                    st.session_state.pending_task_id = task.id
                    st.session_state.pending_request_id = request_id
                    st.session_state.pending_prompt = dispatched_prompt
                    st.rerun()


# Polling mechanism for Celery task
if 'pending_task_id' in st.session_state:
    task_id = st.session_state.pending_task_id
    task = AsyncResult(task_id)

    if task.state == 'PENDING' or task.state == 'STARTED':
        with st.spinner("Processing via LangGraph Orchestrator..."):
            time.sleep(2)
            st.rerun()
    elif task.state == 'SUCCESS' or task.status == 'PAUSED_FOR_REVIEW':
        # Task finished or paused, we can read from Postgres
        st.success("Execution completed or paused.")
        graph = get_graph_with_postgres()
        config = {"configurable": {"thread_id": st.session_state.pending_request_id}}
        current_state = graph.get_state(config)

        if current_state and hasattr(current_state, 'values'):
            final_messages = current_state.values.get("messages", [])
            drafted_plan = current_state.values.get("drafted_plan", "")

            for m in final_messages:
                if isinstance(m, AIMessage):
                    if not any(chat["content"] == m.content for chat in st.session_state.chat_history):
                        st.session_state.chat_history.append({"role": "assistant", "content": m.content})

            st.session_state.pending_plan = drafted_plan

        del st.session_state.pending_task_id
        st.rerun()
    elif task.state == 'FAILURE':
        st.error(f"Task failed: {task.info}")
        del st.session_state.pending_task_id
        st.rerun()

with col2:
    st.subheader("Controls")

    # Action Row: HITL
    st.write("Human-in-the-Loop Checkpoint")
    graph = get_graph_with_postgres()
    current_state = graph.get_state(config)

    if current_state.next == ('human_review',):
        st.warning("Execution Paused. Plan awaits approval.")

        # --- Sprint-3 A2A visualisation ---
        pending_po = current_state.values.get("pending_po")
        if pending_po:
            st.subheader("A2A Negotiation Transcript")
            for exchange in current_state.values.get("a2a_transcript", []):
                st.json(exchange)
            st.subheader("Draft Purchase Order")
            st.json(pending_po)
        # -----------------------------------

        col_approve, col_reject = st.columns(2)
        with col_approve:
            if st.button("Approve", type="primary"):
                # Log DPO
                log_dpo(st.session_state.get('pending_prompt', ''), st.session_state.get('pending_plan', ''), "")

                # Resume execution
                graph.update_state(config, {"status": "approved"})
                for event in graph.stream(None, config):
                    pass
                st.success("Plan Approved and Executed.")
                st.session_state.chat_history.append({"role": "assistant", "content": "Plan Approved and Executed."})
                st.rerun()

        with col_reject:
            if st.button("Reject"):
                # Log DPO
                log_dpo(st.session_state.get('pending_prompt', ''), "", st.session_state.get('pending_plan', ''))

                graph.update_state(config, {"status": "rejected"})
                for event in graph.stream(None, config):
                    pass
                st.error("Plan Rejected.")
                st.session_state.chat_history.append({"role": "assistant", "content": "Plan Rejected."})
                st.rerun()
    else:
        st.info("No plans pending approval.")

    st.divider()

    # A2A Negotiate
    if st.button("A2A Negotiate"):
        with st.spinner("Initiating Agent-to-Agent Handshake..."):
            time.sleep(1) # Simulate millisecond handshake visually
            st.success("Handshake complete: SYNC_ACK with Vendor AI.")

    # Chaos Test
    if st.button("Trigger Chaos Load Test"):
        with st.spinner("Injecting 1,000 edge cases..."):
            generate_load()
            st.success("1,000 synthetic edge-case rows injected into database.")
            st.rerun()
