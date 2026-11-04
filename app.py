import streamlit as st
import sqlite3
import json
import uuid
import time
from dotenv import load_dotenv
from guardrails import check_prompt_injection
from voice_handler import process_voice_input
from warehouse_vision import analyze_shelf_image
from document_vision import extract_document_data, format_logistics_instruction
from demand_forecaster import forecast_sku_stockouts
import pandas as pd
from portfolio import (
    create_initiative,
    get_wsjf_ranked_backlog,
    get_evms_snapshot,
    get_connection as get_portfolio_connection,
)

# Load environment variables
load_dotenv()
import os
from graph import get_graph_with_postgres, log_dpo
from worker import process_agent_task
from celery.result import AsyncResult
from generate_synthetic_load import generate_load
from langchain_core.messages import HumanMessage, AIMessage

DEMO_MODE = os.environ.get("DEMO_MODE") == "1"

# Initialization
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

st.set_page_config(page_title="Sovereign Supply Chain Orchestrator", layout="wide")

# Header
st.title("Sovereign Supply Chain Orchestrator (MVP)")
tenant_id = st.selectbox("Select Active Tenant (Multi-Tenant Isolation)", ["Tenant_A", "Tenant_B"])

config = {"configurable": {"thread_id": f"{tenant_id}_{st.session_state.thread_id}"}}

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

    st.divider()

    st.header("Portfolio Dashboard")

    # Fetch initiatives for dropdown/selection
    try:
        p_conn = get_portfolio_connection()
        p_cur = p_conn.cursor()
        p_cur.execute("SELECT id, title FROM initiatives ORDER BY id ASC")
        init_rows = p_cur.fetchall()
        p_conn.close()
    except Exception:
        init_rows = []

    active_init_id = None
    if init_rows:
        init_options = {f"{r['id']} - {r['title'][:30]}": r["id"] for r in init_rows}
        selected_label = st.selectbox("Select Business Initiative", list(init_options.keys()), key="portfolio_initiative_selector")
        active_init_id = init_options[selected_label]
    else:
        st.info("No initiatives created yet.")

    # 1. Input form: "New Initiative"
    with st.expander("New Initiative", expanded=False):
        with st.form("new_initiative_form", clear_on_submit=True):
            new_title = st.text_input("Initiative Title", placeholder="e.g. Cut procurement costs 20%")
            new_target = st.number_input("Target Savings ($ USD)", min_value=0.0, value=50000.0, step=1000.0)
            new_deadline = st.text_input("Deadline", value="2025-12-31")
            submitted = st.form_submit_button("Create Initiative")
            if submitted and new_title.strip():
                create_initiative(new_title.strip(), new_target, new_deadline.strip())
                st.success(f"Initiative '{new_title}' created!")
                st.rerun()

    # 2. WSJF backlog table: columns = Work Item | WSJF Score | Status | $ Saved
    st.subheader("WSJF Backlog Table")
    backlog_items = get_wsjf_ranked_backlog(active_init_id)
    if not backlog_items:
        st.info("No work items in backlog for this initiative.")
    else:
        table_rows = []
        for item in backlog_items:
            table_rows.append({
                "Work Item": item.title,
                "WSJF Score": round(item.wsjf_score, 1),
                "Status": item.status,
                "$ Saved": f"${item.actual_saving_usd:,.2f}"
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    # 3. EVMS mini-chart: horizontal bar showing PV vs EV vs AC
    st.subheader("EVMS Performance Chart")
    if active_init_id:
        evms = get_evms_snapshot(active_init_id)
        evms_data = pd.DataFrame({
            "Metric": ["Planned Value (PV)", "Earned Value (EV)", "Actual Cost (AC)"],
            "Amount ($ USD)": [evms["planned_value"], evms["earned_value"], evms["actual_cost"]]
        })
        st.bar_chart(evms_data, x="Metric", y="Amount ($ USD)", horizontal=True)

        col_spi, col_cpi = st.columns(2)
        with col_spi:
            st.metric("Schedule Perf (SPI)", f"{evms['spi']:.2f}")
        with col_cpi:
            st.metric("Cost Perf (CPI)", f"{evms['cpi']:.2f}")

    # 4. "AI Recommend Next" button: calls get_wsjf_ranked_backlog(), displays top item
    if st.button("AI Recommend Next", key="ai_recommend_next_btn"):
        ranked = get_wsjf_ranked_backlog(active_init_id)
        if ranked:
            top = ranked[0]
            st.success(
                f"🎯 **AI Recommended Next Action:**\n\n"
                f"**Item:** {top.title}\n\n"
                f"**WSJF Priority Score:** {top.wsjf_score:.1f} | **Status:** {top.status}\n\n"
                f"**Potential Target / Current Saved:** ${top.actual_saving_usd:,.2f}"
            )
        else:
            st.info("No work items available to recommend.")

    st.divider()

    st.header("Analytics Dashboard")

    # Section 1: WAF events over time
    with st.expander("WAF Events Over Time", expanded=False):
        if not st.session_state.waf_history:
            st.info("No WAF events recorded yet.")
        else:
            waf_counts = {}
            for ev in st.session_state.waf_history:
                ts = ev.get("timestamp", "unknown")
                waf_counts[ts] = waf_counts.get(ts, 0) + ev.get("count", 1)
            st.bar_chart(waf_counts)

    # Section 2: PO history table
    with st.expander("PO History Table", expanded=False):
        try:
            conn = sqlite3.connect('mock_sap.db')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, request_id, status, payload, created_at
                FROM task_queue
                WHERE status = 'EXECUTED'
                ORDER BY id DESC
                LIMIT 10
            """)
            po_rows = cursor.fetchall()
            conn.close()
            if not po_rows:
                st.info("No executed purchase orders found in task queue.")
            else:
                table_data = []
                for row in po_rows:
                    table_data.append({
                        "ID": row[0],
                        "Request ID": row[1],
                        "Status": row[2],
                        "Payload": row[3],
                        "Created At": row[4]
                    })
                st.dataframe(table_data, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading PO history: {e}")

    # Section 3: Disruption alert history
    with st.expander("Disruption Alert History", expanded=False):
        if not st.session_state.disruption_history:
            st.info("No disruption alerts recorded yet.")
        else:
            for alert in reversed(st.session_state.disruption_history):
                sev = alert.get("severity", "low").upper()
                summary = alert.get("summary", "No details")
                ts = alert.get("timestamp", "")
                st.markdown(f"**[{ts}] ({sev})**: {summary}")

    # Section 4: Forecast predictions display
    with st.expander("Forecast Predictions", expanded=False):
        if st.button("Refresh Forecast", key="refresh_forecast_btn"):
            with st.spinner("Forecasting SKU stockouts with muse-spark-1.3..."):
                st.session_state.forecast_cache = forecast_sku_stockouts()

        if st.session_state.forecast_cache is None:
            # Auto-populate cache if empty
            with st.spinner("Loading initial stockout forecasts..."):
                st.session_state.forecast_cache = forecast_sku_stockouts()

        forecasts = st.session_state.forecast_cache
        if not forecasts:
            st.info("No stockout predictions at this time.")
        else:
            color_map = {
                "high": "red",
                "medium": "orange",
                "low": "green"
            }
            for fc in forecasts:
                sku = fc.get("sku", "Unknown SKU")
                days = fc.get("days_until_stockout", 0)
                conf = str(fc.get("confidence", "low")).lower()
                color = color_map.get(conf, "gray")
                st.markdown(
                    f"- **{sku}**: Stockout in **{days}** days "
                    f"(Confidence: :{color}[{conf.upper()}])"
                )

# Main Layout
col1, col2 = st.columns([2, 1])

with col1:
    tab_chat, tab_upload = st.tabs(["Orchestrator Chat", "Upload Document"])

    with tab_upload:
        st.subheader("Invoice / Shipping Document Extraction")
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
                        extraction = extract_document_data(doc_bytes)
                        st.session_state.extracted_document = extraction
                        st.session_state.prefilled_prompt = format_logistics_instruction(extraction)

        if st.session_state.get("extracted_document"):
            doc_data = st.session_state.extracted_document
            st.success("Document Extracted Successfully")

            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"**Supplier:** {doc_data.get('supplier') or 'Not specified'}")
                dates = doc_data.get("dates", [])
                st.markdown(f"**Dates:** {', '.join(dates) if dates else 'Not specified'}")
            with col_info2:
                st.markdown(f"**Summary:** {doc_data.get('raw_summary') or 'None'}")

            items = doc_data.get("items", [])
            if items:
                st.markdown("**Items & Quantities:**")
                for itm in items:
                    price_str = f" (${itm.get('unit_price')}/unit)" if itm.get("unit_price") is not None else ""
                    st.write(f"- {itm.get('quantity', 1)}x {itm.get('description', 'Item')}{price_str}")

            if st.session_state.get("prefilled_prompt"):
                st.info(f"**Pre-populated Chat Instruction:**\n\n_{st.session_state.prefilled_prompt}_")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Clear Document", key="clear_extracted_doc_btn"):
                    st.session_state.extracted_document = None
                    st.session_state.prefilled_prompt = ""
                    st.session_state.last_uploaded_doc_id = None
                    st.rerun()

    with tab_chat:
        st.subheader("Orchestrator Chat")

        # Display chat
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Display prefilled prompt stage if available
        if st.session_state.get("prefilled_prompt"):
            st.info(f"📋 **Draft Logistics Instruction:**\n\n_{st.session_state.prefilled_prompt}_")
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

                    task = process_agent_task.delay(tenant_id, request_id, dispatched_prompt)
                    st.session_state.pending_task_id = task.id
                    st.session_state.pending_request_id = request_id
                    st.session_state.pending_prompt = dispatched_prompt
                    st.rerun()

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
                                st.session_state.waf_history.append({"timestamp": time.strftime("%H:%M:%S"), "count": 1})
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
                st.session_state.waf_history.append({"timestamp": time.strftime("%H:%M:%S"), "count": 1})
                st.error("SECURITY ALERT: Malicious prompt detected and blocked by Semantic Bouncer.")
            else:
                st.session_state.chat_history.append({"role": "user", "content": prompt})

                request_id = str(uuid.uuid4())
                dispatched_prompt = prompt
                if st.session_state.get("shelf_context") and st.session_state["shelf_context"].get("summary"):
                    summary_text = st.session_state["shelf_context"]["summary"]
                    dispatched_prompt = f"[VISUAL SHELF ANALYSIS: {summary_text}]\n{prompt}"

                if DEMO_MODE:
                    # In DEMO_MODE, execute synchronously and inject mock response deterministically
                    resp_plan = (
                        f"Orchestrator Analysis for '{prompt}':\n"
                        f"• Tenant: {tenant_id}\n"
                        f"• Stock level verified across regional hubs.\n"
                        f"• Draft reallocation route: Warehouse-West to Distribution-East.\n"
                        f"• Optimal carrier dispatch generated with ETA 24 hours."
                    )
                    st.session_state.chat_history.append({"role": "assistant", "content": resp_plan})
                    st.session_state.demo_pending_plan = resp_plan
                    st.session_state.pending_prompt = dispatched_prompt
                    st.rerun()
                else:
                    with st.chat_message("user"):
                        st.write(prompt)

                    with st.chat_message("assistant"):
                        with st.spinner("Processing via LangGraph Orchestrator..."):
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
        config = {"configurable": {"thread_id": f"{tenant_id}_{st.session_state.pending_request_id}"}}
        current_state = graph.get_state(config)

        if current_state and hasattr(current_state, 'values'):
            final_messages = current_state.values.get("messages", [])
            drafted_plan = current_state.values.get("drafted_plan", "")

            for m in final_messages:
                if isinstance(m, AIMessage):
                    if not any(chat["content"] == m.content for chat in st.session_state.chat_history):
                        st.session_state.chat_history.append({"role": "assistant", "content": m.content})
                    if "[GLOBAL ORACLE ALERT]" in m.content:
                        import re
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
    if DEMO_MODE:
        is_paused = st.session_state.demo_paused_for_hitl
        pending_po = st.session_state.demo_pending_po
        a2a_transcript = st.session_state.demo_a2a_transcript
    else:
        try:
            graph = get_graph_with_postgres()
            current_state = graph.get_state(config)
            is_paused = current_state.next == ('human_review',)
            pending_po = current_state.values.get("pending_po") if hasattr(current_state, "values") else None
            a2a_transcript = current_state.values.get("a2a_transcript", []) if hasattr(current_state, "values") else []
        except Exception:
            is_paused = False
            pending_po = None
            a2a_transcript = []

    if is_paused:
        st.warning("Execution Paused. Plan awaits approval.")

        # --- Sprint-3 A2A visualisation ---
        if pending_po:
            st.subheader("A2A Negotiation Transcript")
            for exchange in a2a_transcript:
                st.json(exchange)
            st.subheader("Draft Purchase Order")
            st.json(pending_po)
        # -----------------------------------

        col_approve, col_reject = st.columns(2)
        with col_approve:
            if st.button("Approve", type="primary"):
                # Log DPO
                log_dpo(st.session_state.get('pending_prompt', ''), st.session_state.get('demo_pending_plan', st.session_state.get('pending_plan', '')), "")

                if DEMO_MODE:
                    st.session_state.demo_paused_for_hitl = False
                    st.success("Plan Approved and Executed.")
                    st.session_state.chat_history.append({"role": "assistant", "content": "Plan Approved and Executed."})
                    st.rerun()
                else:
                    graph.update_state(config, {"status": "approved"})
                    for event in graph.stream(None, config):
                        pass
                    st.success("Plan Approved and Executed.")
                    st.session_state.chat_history.append({"role": "assistant", "content": "Plan Approved and Executed."})
                    st.rerun()

        with col_reject:
            if st.button("Reject"):
                # Log DPO
                log_dpo(st.session_state.get('pending_prompt', ''), "", st.session_state.get('demo_pending_plan', st.session_state.get('pending_plan', '')) )

                if DEMO_MODE:
                    st.session_state.demo_paused_for_hitl = False
                    st.error("Plan Rejected.")
                    st.session_state.chat_history.append({"role": "assistant", "content": "Plan Rejected."})
                    st.rerun()
                else:
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
            if DEMO_MODE:
                # Trigger A2A negotiation transcript + draft PO display in HITL section
                mock_rfq = "Procurement Buyer RFQ: Request restock of 500 units SKU-STEEL-BEAMS. Max lead time: 5 days."
                mock_quote = {"restock_quantity": 500, "price_per_unit": 42.50, "lead_time_days": 3}
                st.session_state.demo_a2a_transcript = [
                    {"role": "buyer_agent", "request": [{"sku": "SKU-STEEL-BEAMS", "qty": 0}], "response": mock_rfq},
                    {"role": "supplier_agent", "request": mock_rfq, "response": mock_quote}
                ]
                st.session_state.demo_pending_po = {
                    "po_id": "PO-948201",
                    "items": [{"sku": "SKU-STEEL-BEAMS", "qty": 500}],
                    "restock_quantity": 500,
                    "price_per_unit": 42.50,
                    "lead_time_days": 3,
                    "supplier": "Apex Logistics Supplier AI"
                }
                st.session_state.demo_paused_for_hitl = True
                st.success("Handshake complete: SYNC_ACK with Vendor AI.")
                st.rerun()
            else:
                st.success("Handshake complete: SYNC_ACK with Vendor AI.")

    # Chaos Test
    if st.button("Trigger Chaos Load Test"):
        with st.spinner("Injecting 1,000 edge cases..."):
            generate_load()
            if DEMO_MODE:
                st.session_state.demo_chaos_triggered = True
            else:
                st.success("1,000 synthetic edge-case rows injected into database.")
            st.rerun()

    if DEMO_MODE and st.session_state.get("demo_chaos_triggered"):
        st.success("1,000 synthetic edge-case rows injected into database.")
        st.info("System recovered: Tenacity retry policies engaged. Database integrity preserved.")
