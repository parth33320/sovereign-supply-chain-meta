# Test Report: Sovereign Supply Chain Orchestrator

## 1. Sprint Results Summary (S1–S14, Security, E2E)

| Sprint | Suite / Target | Result | Detail / Reason |
|---|---|---|---|
| **S1** | `test_meta_smoke.py` | **SKIP** | Live `muse-spark-1.3` call skipped in sandbox (credentials configured on live Render web service). |
| **S2** | `test_postgres_smoke.py` | **SKIP** | PostgreSQL checkpointer live test skipped in sandbox (Render `supply-chain-db` URI set on Render). |
| **S3** | `test_disruption_radar.py` | **PASS** | RSS ingestion and LLM alert synthesis passed (live Meta API call skipped in sandbox). |
| **S4** | `test_voice_handler.py` | **PASS** | Audio transcription parsing and intent extraction passed. |
| **S5** | `test_guardrails.py` | **PASS** | Semantic Bouncer regex filtering and safe prompt passthrough verified. |
| **S6** | `test_global_oracle_integration.py` | **PASS** | Global Oracle correctly injects disruption alerts into state with `[GLOBAL ORACLE ALERT]`. |
| **S7** | `test_voice_ui_e2e.py` | **PASS** | `st.audio_input` widget verified, transcription auto-submits, Playwright E2E passed with video. |
| **S8** | `test_guardrails_ui.py` | **PASS** | Malicious prompt increments `waf_count` by 1; benign prompt does not. |
| **S9** | `test_a2a_negotiate.py` | **PASS** | A2A negotiation buyer RFQ and supplier quote pipeline verified (live call skipped in sandbox). |
| **S10** | `test_warehouse_vision.py` | **PASS** | Shelf segmentation parsing and UI tests passed. |
| **S11** | `test_document_vision.py` | **PASS** | Invoice/document extraction parsing and UI upload tests passed. |
| **S12** | `test_demand_forecaster.py` | **PASS** | Stockout prediction engine and graph forecast demand node verified. |
| **S13** | `test_analytics_dashboard.py` | **PASS** | Playwright E2E verified all 4 dashboard expanders in sidebar with video recorded. |
| **S14** | `test_demo_pipeline.py` | **PASS** | gTTS audio generation, timestamps.json schema validation, and MP4 pipeline passed. |
| **Security** | `test_security_adversarial.py` | **PASS** | All 10 prompt injection attacks return `False`; all 5 benign supply chain prompts return `True`. |
| **Scenario** | `test_e2e_full_scenario.py` | **PASS** | Full 7-step decision loop for Tenant_A verified from graph entry to approved task completion. |

---

## 2. Render Services Status

- **Web Service (`sovereign-supply-chain-meta`)**:
  - **Status**: Exists (Docker runtime, deployed on Render).
  - **Start Command**: `streamlit run app.py --server.port=8501 --server.address=0.0.0.0`
- **Worker Service (`sovereign-supply-chain-worker`)**:
  - **Status**: Previously MISSING; declared in `render.yaml`.
  - **Start Command**: `celery -A worker worker --loglevel=info`
  - **Runtime**: Docker (using repository `Dockerfile`).
- **Redis Service (`supply-chain-redis`)**:
  - **Status**: Declared in `render.yaml` with internal connection wiring.
  - **Internal URL**: `redis://red-dblo6d9srm7s73f7uf7g:6379` (used for `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`).
- **Database (`supply-chain-db`)**:
  - **Status**: PostgreSQL 18 managed database provisioned on Render.

---

## 3. Environment Variables Audit

- **Configured on Live Render**:
  - `META_API_KEY`: Set in Render dashboard.
  - `META_API_BASE_URL`: `https://api.meta.ai/v1`
  - `META_MODEL_NAME`: `muse-spark-1.3`
  - `POSTGRES_DB_URI`: Render internal PostgreSQL URI (`sslmode=require`).
  - `CELERY_BROKER_URL`: `redis://red-dblo6d9srm7s73f7uf7g:6379`
  - `CELERY_RESULT_BACKEND`: `redis://red-dblo6d9srm7s73f7uf7g:6379`
- **Sandbox Environment Status**:
  - Unset in isolated sandbox runner (expected as confirmed by user). Tests requiring live external endpoints gracefully skip using `@pytest.mark.skipif(not os.environ.get("META_API_KEY"))` and `@pytest.mark.skipif(not os.environ.get("POSTGRES_DB_URI"))`.

---

## 4. Meta API Calls & Error Details

- **Live Sandbox Meta API Calls**:
  - Unset API key skipped gracefully with standard pytest skip markers. No unexpected 4xx/5xx failures occurred.
- **Guardrails Determinism**:
  - All 10 adversarial attacks are handled deterministically via expanded regex filtering in `guardrails.py`, ensuring protection even during network or LLM latency.

---

## 5. Playwright UI Test Artifacts

- **Voice UI E2E (`tests/test_voice_ui_e2e.py`)**:
  - Verifies `st.audio_input` above chat, automatic submission, and headless Chromium execution.
  - Temporary video recorded under: `tmp_path / "videos/*.webm"`
  - Screenshot verified under: `tmp_path / "voice_ui_screenshot.png"`
- **Analytics Dashboard UI E2E (`tests/test_analytics_dashboard.py`)**:
  - Verifies all 4 expanders:
    1. "WAF Events Over Time"
    2. "PO History Table"
    3. "Disruption Alert History"
    4. "Forecast Predictions"
  - Temporary video recorded under: `tmp_path / "videos/*.webm"`
- **Document Vision UI E2E (`tests/test_document_vision_ui.py`)**:
  - Verifies document upload tab and chat pre-population.
  - Video recorded under: `tmp_path / "videos/*.webm"`
- **Warehouse Vision UI E2E (`tests/test_warehouse_vision_ui.py`)**:
  - Verifies shelf image uploader and context display.
  - Video recorded under: `tmp_path / "videos/*.webm"`
