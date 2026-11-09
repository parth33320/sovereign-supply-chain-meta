# Tech Stack Migration — 2026-11-08

## What changed
Streamlit UI replaced by React+Vite+Tailwind frontend.
FastAPI backend wraps existing Python files.

## Why
Streamlit limitations: click-only tooltips, full page
rerender on every button, no floating input bar, sidebar
collapse not persisted, file upload auto-detect impossible,
voice format bugs, 10-30s perceived latency on Render
free tier due to full Python rerun per interaction.

## What stays unchanged
graph.py, guardrails.py, voice_handler.py,
warehouse_vision.py, document_vision.py,
demand_forecaster.py, db.py, init_db.py, portfolio.py

## Architecture
Single Render service. FastAPI on $PORT.
React build served as static files from frontend/dist/.
SSE for activity log. Spinner for LLM responses.
No auth. No WebSocket. No separate frontend service.

## Alternatives rejected
- Express+React: forces Node.js rewrite of Python backend
- Next.js: SSR overkill for single-page app
- Two Render services: double cold start on free tier
- Keeping Streamlit: fundamental UI limitations unresolvable
