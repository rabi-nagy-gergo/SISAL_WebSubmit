import os
import json
import shutil
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.services.api_utils import (
    SESSIONS_DIR,
    SESSION_TIMEOUT_HOURS,
    SAVED_SESSION_TIMEOUT_HOURS,
)
from src.pages import upload, validation, plots, download


# ==========================================
# Background process: Garbage Collector
# ==========================================
async def garbage_collector():
    """
    At every hour this function checks sessions directory
    and deletes expired sessions, based on session UUID.
    """
    while True:
        if os.path.exists(SESSIONS_DIR):
            now = datetime.now().timestamp()
            for session_id in os.listdir(SESSIONS_DIR):
                session_path = os.path.join(SESSIONS_DIR, session_id)
                metadata_path = os.path.join(session_path, "metadata.json")

                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)

                        # If current time exceeds the expiry time, delete the session.
                        if now > metadata.get("expires_at", 0):
                            shutil.rmtree(session_path, ignore_errors=True)
                            print(
                                f"[Garbage Collector] Expired session deleted: {session_id}"
                            )
                    except Exception as e:
                        print(
                            f"[Garbage Collector] An error occurred while checking session {session_id}: {e}"
                        )

        # Runs at every hour.
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On server startup: Create session directory and start garbage collector.
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    gc_task = asyncio.create_task(garbage_collector())
    yield
    # On server shutdown: Shut down garbage collector.
    gc_task.cancel()


# ==========================================
# FastAPI Initialization
# ==========================================
app = FastAPI(title="SISAL AutoQC API", lifespan=lifespan)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registering separated routers
app.include_router(upload.router)
app.include_router(validation.router)
app.include_router(plots.router)
app.include_router(download.router)


@app.get("/api/config")
async def get_config():
    return {
        "session_timeout_hours": SESSION_TIMEOUT_HOURS,
        "saved_session_timeout_hours": SAVED_SESSION_TIMEOUT_HOURS,
    }


# Mount frontend code to root directory
app.mount("/", StaticFiles(directory="web", html=True), name="web")
