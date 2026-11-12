"""Main FastAPI application for Sovereign Supply Chain Orchestrator."""

import sys, os
# Resolve repo root whether running from repo root or inside backend/
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.routers import chat, upload, voice, hitl, activity, inventory, manager, whatif
import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database schema and sample data on startup."""
    init_db.init_db()
    yield

app = FastAPI(title="Sovereign Supply Chain", lifespan=lifespan)

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"])

app.include_router(chat.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(hitl.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(manager.router, prefix="/api")
app.include_router(whatif.router, prefix="/api")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "demo_mode": os.environ.get("DEMO_MODE") == "1",
        "manager_password": os.environ.get("MANAGER_PASSWORD", "sovereign"),
        "frontend_dist": os.path.exists(os.path.join(repo_root, "frontend", "dist")),
    }

# Serve React build — static assets served directly, SPA fallback for all other routes
frontend_dist = os.path.join(repo_root, "frontend", "dist")
print(f"[startup] repo_root={repo_root} frontend_dist={frontend_dist} exists={os.path.exists(frontend_dist)}")

if os.path.exists(frontend_dist):
    # /assets/* and other static files served directly
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Serve favicon and other root-level static files
    for static_file in ("favicon.svg", "icons.svg"):
        static_path = os.path.join(frontend_dist, static_file)
        if os.path.exists(static_path):
            @app.get(f"/{static_file}")
            async def _serve_static(p=static_path):
                return FileResponse(p)

    # SPA catch-all: serve index.html for any unmatched path
    index_html = os.path.join(frontend_dist, "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA — handles client-side routing."""
        # Check if file exists (e.g. /favicon.svg, /assets/*)
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(index_html)
else:
    print(f"[startup] WARNING: frontend/dist not found at {frontend_dist} — UI will not be served")

    @app.get("/")
    async def no_frontend():
        return JSONResponse({"error": "Frontend not built", "hint": "Run: cd frontend && npm run build"})
