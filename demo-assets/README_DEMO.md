# Sovereign Supply Chain Orchestrator — Demo Walkthrough

This directory contains the demo media assets and step-by-step instructions to reproduce the autonomous multi-agent supply chain demo flow.

## QUICKSTART (5 minutes):
1. Clone repo
2. Create .env file with: META_API_KEY=your_key_here and DEMO_MODE=1
3. pip install -r requirements.txt
4. python init_db.py
5. streamlit run app.py
6. Go to Warehouse tab, upload demo-assets/sample_shelf.jpg
7. Go to Documents tab, upload demo-assets/sample_invoice.png
8. Go to Orchestrator tab, click mic and say:
   "Emergency. Widget-A is running out. Get me the best price now."
   OR type it in the text box
9. Click Approve on the panel that appears on the right

## FOR LIVE META AI (no demo mode):
1. Remove DEMO_MODE from .env
2. Add POSTGRES_DB_URI=your_postgres_url to .env
3. Same steps above — now uses real muse-spark-1.3

---

## Demo Assets Included:
- `sample_shelf.jpg`: Warehouse shelf inspection image showing 3 tiers of shelving with one shelf nearly empty labeled "Widget-A 12%".
- `sample_invoice.png`: Shipping invoice from Supplier Apex Logistics for Item Widget-A (Qty: 500, Unit Price: $8.20, Date: 2026-11-04).
- `sample_voice_command.wav`: Silent 3-second WAV placeholder. Note: Users should record their own voice saying *"Emergency. Widget-A is running out. Get me the best price now."* or use the mic button directly in the app.
