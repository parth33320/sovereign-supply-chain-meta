"""Main FastAPI application for Sovereign Supply Chain Orchestrator."""

import sys, os
# Resolve repo root whether running from repo root or inside backend/
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.routers import chat, upload, voice, hitl, activity, inventory, manager
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

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "demo_mode": os.environ.get("DEMO_MODE") == "1",
        "manager_password": os.environ.get("MANAGER_PASSWORD", "sovereign")
    }

# Serve React build — must be LAST
frontend_dist = os.path.join(repo_root, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True),
              name="static")
