# Sovereign Supply Chain Orchestrator

[![Live Demo](https://img.shields.io/badge/Demo-Live%20on%20Render-brightgreen)](https://sovereign-supply-chain-meta.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Powered by Meta AI](https://img.shields.io/badge/Meta%20AI-Muse%20%26%20SAM-purple.svg)](https://api.meta.ai)

An enterprise-grade, multi-agent supply chain orchestration platform powered by Meta foundation models. The system proactively detects logistics disruptions, executes autonomous multi-agent negotiations for stocked-out inventory, supports voice-driven warehouse commands, and enforces strict zero-trust semantic guardrails with human-in-the-loop (HITL) governance.

---

### Pre-existing
Pre-existing: LangGraph supply chain skeleton with SQLite, Celery workers, and basic HITL flow.

---

## Live Demo
The live application is deployed and hosted on Render:
- **Live Demo URL**: [https://sovereign-supply-chain-meta.onrender.com](https://sovereign-supply-chain-meta.onrender.com)

---

## Architecture Diagram

The end-to-end architecture integrates Streamlit, LangGraph orchestration, PostgreSQL state checkpointing, asynchronous Celery workers, MCP inventory services, and Meta AI foundation models.

```mermaid
flowchart TD
    subgraph Client ["User Interfaces & Ingestion"]
        UI["Streamlit Command Center (app.py)"]
        VoiceInput["Voice Command Audio Input"]
        DocInput["Invoice / BOL Document Upload"]
        VisionInput["Warehouse Shelf Camera Feed"]
    end

    subgraph MetaModels ["Meta Foundation Models"]
        M_Voice["muse-voice-transcribe-1.0<br/>(Speech-to-Text Transcription)"]
        M_Spark["muse-spark-1.3<br/>(Reasoning, Guardrails, Oracle, A2A)"]
        M_Image["muse-image-1.0<br/>(Document / BOL Data Extraction)"]
        M_SAM["sam-3.1<br/>(Warehouse Visual Stock Segmentation)"]
    end

    subgraph Security ["Security & Guardrail Layer"]
        Guard["Semantic Bouncer (guardrails.py)<br/>Regex Filter + Meta LLM Classification"]
    end

    subgraph Orchestration ["LangGraph State Machine (graph.py)"]
        Entry(["State Entry"])
        Oracle["Global Oracle Node<br/>(Disruption Radar RSS Feed)"]
        MCPFetch["Fetch Inventory Node<br/>(Tenacity Retry & Backoff)"]
        RouteIntent{"Route Intent Decision"}
        A2ANegotiate["A2A Negotiate Node<br/>(Buyer Agent RFQ + Supplier Agent Quote)"]
        DraftPO["Draft Purchase Order Node"]
        DraftPlan["Draft Logistics Plan Node"]
        HITL["Human Review Node (Interrupt Before)"]
        Execute["Execute Plan Node"]
        EndNode(["End State"])
    end

    subgraph DataInfra ["Data & Infrastructure Services"]
        PG[("PostgreSQL Checkpointer (Render DB)")]
        Redis[("Redis Message Broker")]
        CeleryWorker["Celery Worker (worker.py)"]
        MCPServer["FastMCP Server (mock_sap.db)"]
    end

    %% Ingestion flows
    VoiceInput -->|"Audio bytes"| M_Voice
    M_Voice -->|"Transcribed text"| UI
    DocInput -->|"Document image"| M_Image
    M_Image -->|"Structured JSON"| UI
    VisionInput -->|"Shelf image"| M_SAM
    M_SAM -->|"Low-stock / Empty SKU mask"| UI

    %% User prompt & Guardrails
    UI -->|"User prompt / Intent"| Guard
    Guard -.->|"Classify prompt injection"| M_Spark
    Guard -->|"Safe prompt"| Entry

    %% Graph Execution
    Entry --> Oracle
    Oracle -.->|"Summarize RSS headlines"| M_Spark
    Oracle --> MCPFetch
    MCPFetch <-->|"MCP Tool / SQL Query"| MCPServer
    MCPFetch --> RouteIntent

    %% Branching logic
    RouteIntent -->|"Stockout detected (qty == 0)"| A2ANegotiate
    RouteIntent -->|"Normal rebalance / query"| DraftPlan

    A2ANegotiate -.->|"Buyer persona RFQ generation"| M_Spark
    A2ANegotiate -.->|"Supplier persona Quote generation"| M_Spark
    A2ANegotiate --> DraftPO
    DraftPO --> HITL

    DraftPlan -.->|"Draft reallocation plan"| M_Spark
    DraftPlan --> HITL

    %% HITL and Execution
    HITL -->|"User Approval via UI"| Execute
    Execute --> EndNode

    %% Persistence & Workers
    Orchestration <-->|"State Checkpoints & Memory"| PG
    UI -->|"Dispatch async task"| Redis
    Redis --> CeleryWorker
    CeleryWorker -->|"Run graph with thread_id"| Orchestration
```

---

## What We Built This Week

Across sprints S1 through S14, we transformed the baseline skeleton into an intelligent, resilient, multi-modal supply chain control tower:

- **S1: Meta API Integration (muse-spark-1.3 swap)** — Swapped standard completion endpoints to Meta's `muse-spark-1.3` using standard OpenAI-compatible interface protocols (`META_API_KEY`, `META_API_BASE_URL`, `META_MODEL_NAME`).
- **S2: PostgreSQL Checkpointer + Render DB** — Built durable multi-turn state persistence for LangGraph using PostgreSQL (`PostgresSaver` via `psycopg-pool`) backed by Render managed databases with connection pooling and SSL mode.
- **S3: Live Disruption Radar (RSS + muse-spark-1.3)** — Ingested real-time maritime and freight RSS feeds (FreightWaves, SupplyChainBrain) and synthesized dynamic disruption alerts with severity scoring.
- **S4: Voice Command Input (muse-voice-transcribe-1.0)** — Integrated audio ingestion pipeline using Meta's `muse-voice-transcribe-1.0` model to transcribe spoken warehouse operations commands into text.
- **S5: Semantic Injection Guardrails (muse-spark-1.3)** — Designed a zero-trust "Semantic Bouncer" (`guardrails.py`) combining fast regex filtering and Meta LLM semantic classification to neutralize prompt injection attacks.
- **S6: Disruption Radar wired into Global Oracle node** — Wired live disruption feeds directly into the LangGraph entry node (`global_oracle`) to inject actionable disruption alerts into state before planning.
- **S7: Voice UI wired into Streamlit** — Added a dedicated voice recording interface in Streamlit (`st.audio_input`) positioned directly above chat, enabling seamless automatic submission of transcribed voice commands.
- **S8: Guardrails integration tests** — Established regression and chaos test suites validating adversarial prompt injection blocks and UI warning notifications.
- **S9: Multi-Agent A2A Negotiation (Buyer + Supplier personas)** — Built autonomous agent-to-agent negotiation (`a2a_negotiate`) using two distinct Meta model personas: a Buyer Agent generating structured RFQs and a Supplier Agent returning JSON restock quotes.
- **S10: SAM 3.1 Warehouse Shelf Vision** — Visual perception integration using Meta SAM 3.1 for segmenting warehouse shelving imagery to detect low-stock and empty SKU positions.
- **S11: Muse Image Invoice/Document Extraction** — Document extraction engine powered by Meta `muse-image-1.0` to parse bills of lading, freight receipts, and packing slips into structured schema.
- **S12: Demand Forecasting node (proactive stockout prediction)** — Integrated predictive intelligence into the decision graph to project inventory exhaustion horizons and trigger proactive restock cycles.
- **S13: Analytics Dashboard Panel** — Deployed real-time diagnostic telemetry in Streamlit: MCP query audit logs, WAF rate-limiting counters, and negotiation transcript views.
- **S14: Automated Demo Video (Playwright + gTTS + moviepy)** — Developed automated end-to-end browser walkthroughs and synthetic voiceover generation to record verifiable demo runs.

---

## Meta Models Used

This platform standardizes entirely on Meta AI foundation models:

| Model | Purpose & Architectural Role |
|---|---|
| **`muse-spark-1.3`** | Core reasoning, semantic guardrail classification, live disruption radar synthesis, logistics reallocation planning, and multi-agent A2A negotiation (Buyer & Supplier personas). Default model across all LLM nodes. |
| **`muse-voice-transcribe-1.0`** | Speech-to-text audio transcription engine for verbal logistics queries and hands-free warehouse commands via `voice_handler.py`. |
| **`muse-image-1.0`** | Multimodal document processing model that extracts structured data from shipping invoices, bills of lading, and freight manifests. |
| **`sam-3.1`** | Segment Anything Model 3.1 used for warehouse computer vision; segments shelf imagery to visually identify low-stock positions and empty SKU bins. |

---

## User Guide (Non-Technical)

A simple, everyday guide for warehouse supervisors, logistics staff, and procurement specialists.

### Orchestrator Chat & Voice Commands
- Select **Orchestrator** in the left sidebar navigation rail.
- Pick your active company profile using the **Active Tenant** dropdown at the top (`Tenant_A` or `Tenant_B`).
- Type your logistics question or instructions in the bottom chat bar, or click the microphone button to record a voice instruction.
- **Example Prompts**:
  - *"Check stock levels for Semiconductors and flag any stockouts."*
  - *"Reallocate 500 units of Copper Wire Spools from Warehouse East to West."*
  - *"Emergency stockout on Microcontrollers, initiate immediate supplier restock negotiation."*
- You can also click **📋 Example Inputs (20 Voice Commands)** and hit **Use** on any preset scenario to test commands immediately.
- When the AI generates a purchase order or reallocation plan, review the details in the review card and click **Approve** or **Reject**.

### Warehouse Shelf Inspection
- Select **Warehouse** in the left sidebar.
- Click **Upload Shelf Image** to upload a photo of your storage shelves (PNG, JPG, or WEBP under 1MB).
- The visual inspection tool identifies rack occupancy and flags low-stock or empty SKU bins.
- The inspection summary is saved to your session and automatically attached to your next Orchestrator chat message.
- To test without taking photos, expand **📋 Example Inputs (20 Shelf Inspection Scenarios)** and click **Use** next to any pre-loaded scenario.

### Uploading Documents and Invoices
- Select **Documents** in the left sidebar.
- Click **Upload Invoice or Shipping Document** to submit a packing slip, bill of lading, or supplier invoice (under 2MB).
- The system extracts supplier name, invoice dates, quantities, and line item costs into a readable table.
- A draft logistics instruction is automatically written for you. Click **Open in Orchestrator** to review and dispatch it into the supply chain flow.
- You can also test with **📋 Example Inputs (20 Invoice Line Items)** by clicking **Use** on any line item.

### What to Do When Blocked by Guardrails
- If a warning card titled **⚠️ Action Needed** appears stating that your instruction was blocked by security guardrails:
  - Do not try to override system settings, ask for passwords, or run technical code commands.
  - Keep your requests strictly focused on everyday warehouse operations: checking stock, requesting restocks, or moving inventory.
  - Review the sample queries in `demo/gold_standard_inputs.json` (or expand the **Example Inputs** list in the chat) to see gold standard phrasing that is always accepted.
  - If a specific item name was mistyped, look at the suggestion note (for example: *"Did you mean 'Semiconductors'?"*) and try re-submitting with the suggested spelling.

### Requesting Manager Approval for New Inventory
- If you need to add, edit, or remove catalog items, open the manager portal by adding `?admin_token=<ADMIN_SECRET>` to your browser URL.
- In the sidebar, select the **Admin** panel.
- Go to the **➕ Add New Item** tab, type the SKU name, starting quantity, transit time in days, spot price, and supplier code.
- Click **Submit for Approval**.
- The request appears in the **Pending Approvals Queue**. A manager can review the item details and click **Approve** to commit the item to the database, or **Reject** to decline it.

---

## Setup & Deployment Instructions

### Prerequisites
- Python 3.12+
- Docker & Docker Compose (optional for local Redis/Postgres)
- Meta AI API Credentials (`META_API_KEY`, `META_API_BASE_URL`)

### 1. Environment Configuration
Clone the repository and copy the environment template:
```bash
cp .env.example .env
```

Configure the following variables in `.env`:
```env
META_API_KEY=your_meta_api_key_here
META_API_BASE_URL=https://api.meta.ai/v1
META_MODEL_NAME=muse-spark-1.3

# PostgreSQL LangGraph Checkpointer (optional for local fallback; required in production)
POSTGRES_DB_URI=postgresql://postgres:postgres@localhost:5432/postgres

# Celery Redis Broker/Backend
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 2. Local Infrastructure (Docker)
Start PostgreSQL and Redis locally for state checkpointer and task queues:
```bash
# Start Redis for Celery Broker/Backend
docker run -d -p 6379:6379 --name local-redis redis:alpine

# Start PostgreSQL for LangGraph Checkpointer
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres --name local-postgres postgres:alpine
```

### 3. Install Dependencies & Initialize Database
```bash
pip install -r requirements.txt
python init_db.py
```

### 4. Run the Celery Worker
```bash
celery -A worker worker --loglevel=info
```

### 5. Run the Streamlit Application
```bash
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```
Open your browser to `http://localhost:8501`.

---

## Deploying to Render

The application is containerized and ready for 1-click or Git deployment on Render.

1. **Create a Managed PostgreSQL Database** on Render:
   - Copy the External/Internal Connection String.
   - Set `sslmode=require` in the connection URL.
2. **Create a Redis Instance** on Render (or use external managed Redis).
3. **Deploy Web Service**:
   - Environment: **Docker** (using the root `Dockerfile`).
   - Add Environment Variables:
     - `META_API_KEY`: Your Meta AI API key.
     - `META_API_BASE_URL`: `https://api.meta.ai/v1`
     - `META_MODEL_NAME`: `muse-spark-1.3`
     - `POSTGRES_DB_URI`: Render PostgreSQL internal connection string.
     - `CELERY_BROKER_URL`: Render Redis internal connection string.
     - `CELERY_RESULT_BACKEND`: Render Redis internal connection string.
4. **Deploy Background Worker** (Optional for asynchronous tasks):
   - Command: `celery -A worker worker --loglevel=info`

Once deployed, visit your Render URL:
[https://sovereign-supply-chain-meta.onrender.com](https://sovereign-supply-chain-meta.onrender.com)
