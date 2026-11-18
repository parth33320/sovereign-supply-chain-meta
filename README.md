# 🏭 Sovereign Supply Chain XR Walk

[![Live WebXR Demo](https://shields.io)](https://onrender.com)
[![Python](https://shields.io)](https://python.org)
[![Powered by Meta AI](https://shields.io)](https://meta.ai)

A **hands-first Meta Quest mixed reality supply chain copilot** powered by **Meta Muse (`muse-spark-1.3`)**, **WebXR**, **Three.js**, and **FastAPI**. Warehouse operators step into passthrough, view a digital-twin inventory rack anchored to their real-world floor, trigger multi-agent A2A supplier negotiations with a bare-hand pinch, drag floating spatial cards like native Quest OS windows, approve Purchase Orders, and settle supplier invoices—zero paired controllers required.

---

## 🚀 Live WebXR Demo (Zero Setup)

> **[👉 https://onrender.com](https://onrender.com)](https://sovereign-supply-chain-meta.onrender.com/vr)**

1. Open the link in **Meta Quest Browser** (or desktop Chrome with the **Immersive Web Emulator** extension).
2. Tap **🏭 Enter XR Walk** — the 3D shelf auto-anchors `1.35m` in front of you at floor level (`y=0`) within comfortable seated reach.
3. **Pinch** the pulsing red **Widget-A (`0 units`)** bin to launch autonomous multi-agent supplier negotiation.
4. **Pinch-and-drag** the top grab bars (`≡`) on either the **A2A Negotiation Log** or **Purchase Order Approval** card to reposition them anywhere in your room.
5. Pinch **✅ Approve PO** → **🧾 Validate Invoice** (or Widget-A) → **💳 Verify & Pay** to restock `Widget-A` to **500 units** (green), or pinch **🔄 Reset Demo** to replay.

*(Note: Meta's Model API firewall blocks requests from shared cloud hosting IPs such as Render, so the hosted demo automatically runs in deterministic simulated Muse mode. Follow the 3-step quickstart below to run locally with your own `META_API_KEY` and live `muse-spark-1.3`.)*

---

## ⚡ Local Quickstart (Live Meta Muse `muse-spark-1.3`)

### 1. Clone & Configure `.env`
```bash
git clone https://github.com
cd sovereign-supply-chain-meta
cp .env.example .env
```
Open `.env` and paste your Meta Developer API key:
```env
META_API_KEY=your_meta_api_key_here
META_API_BASE_URL=https://meta.ai/v1
META_MODEL_NAME=muse-spark-1.3
```

### 2. Install Dependencies & Start the Server
```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
*(On Windows, you can also double-click `run.bat`.)*

### 3. Open in Browser or Meta Quest Headset
- **Desktop Chrome (with WebXR Emulator & Voice Commands):** Open `http://localhost:8000/vr`. Both **🎤 Voice** (`"restock"`, `"approve PO"`, `"pay invoice"`) and hand-pinch controls are active.
- **Meta Quest 2 / 3 Headset (USB):** Connect via USB and run `adb reverse tcp:8000 tcp:8000`, then open `http://localhost:8000/vr` in Meta Quest Browser.
- **Meta Quest 2 / 3 Headset (Wireless Wi-Fi):** Run `cloudflared tunnel --url http://localhost:8000` and open the generated `https://<subdomain>://` URL in Meta Quest Browser.

---

## ✨ Key Features & Architecture

- **100% Hands-First WebXR Interaction (`frontend/vr/index.html`):**
  - **Far-Field Ray Pinch (`selectstart` / `selectend`):** Dual hand rays with a snapping cursor dot and 900ms debounce to prevent double-pinch jitter.
  - **Quest OS-Style Draggable Panels:** Dedicated top grab handles (`createGrabHandleMesh`) let operators independently pinch-and-drag the **Purchase Order** card and **A2A Negotiation Log** card in 3D space while keeping them oriented toward the user.
  - **Optional Near-Field Index-Finger Touch:** Tracks 25 `XRHand` joints per hand for direct fingertip proximity taps.
  - **Seated & FoV-Aware Ergonomics:** Auto-anchors at floor height (`y=0`, `1.35m` distance) with dynamically wrapped, auto-expanding 3D canvas panels so text never overflows.
  - **Quest Browser Smart UI:** Detects standalone `OculusBrowser` on Android to hide the unsupported Web Speech mic button, center **🔄 Reset Demo**, and display pure hands-first prompts.
- **FastAPI + Meta Muse Backend (`backend/routers/vr.py`):**
  - `POST /api/vr/negotiate` — Runs multi-supplier RFQ evaluation (`Apex Logistics`, `Global Parts Co`, `FastShip Inc`) using `muse-spark-1.3` with automatic fallback.
  - `POST /api/vr/interpret-voice` — Classifies spoken warehouse commands (`restock`, `approve_po`, `reject_po`, `show_invoice`, `pay_invoice`) via `muse-spark-1.3`.
  - `POST /api/vr/invoice-scan/demo` & `POST /api/vr/invoice-pay/demo` — Verifies invoice totals against the approved PO and commits the restock (`+500 units`) to SQLite (`mock_sap.db`).
  - `POST /api/vr/reset-demo` & `GET /api/vr/muse-status` — Restores initial database state and reports live Meta Muse connectivity.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `META_API_KEY` | Yes (for live AI) | none | Meta Model API key from `dev.meta.ai` |
| `META_API_BASE_URL` | No | `https://meta.ai/v1` | Meta Model API base URL |
| `META_MODEL_NAME` | No | `muse-spark-1.3` | Model used for A2A negotiation & voice intent |
| `DEMO_MODE` | No | `0` | Set to `1` to force deterministic offline/cloud demo mode |

---

## Running Tests

```bash
DEMO_MODE=1 PYTHONPATH=. pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py tests/test_s22_backend.py -q
```

Once deployed, visit your Render URL:
[https://sovereign-supply-chain-meta.onrender.com](https://sovereign-supply-chain-meta.onrender.com)
