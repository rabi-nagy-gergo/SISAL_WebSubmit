import asyncio
import json
import os
import shutil
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.pages import download, plots, upload, validation
from src.services.api_utils import (
    ROOT_PATH,
    SAVED_SESSION_TIMEOUT_HOURS,
    SESSION_TIMEOUT_HOURS,
    SESSIONS_DIR,
    UPLOAD_MAX_SIZE_MB,
)


# Helper to read files sychronously
def read_metadata_sync(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
            now = time.time()
            for session_id in os.listdir(SESSIONS_DIR):
                session_path = os.path.join(SESSIONS_DIR, session_id)
                metadata_path = os.path.join(session_path, "metadata.json")

                if os.path.exists(metadata_path):
                    try:
                        metadata = await asyncio.to_thread(
                            read_metadata_sync, metadata_path
                        )

                        # If current time exceeds the expiry time, delete the session.
                        if now > metadata.get("expires_at", 0):
                            await asyncio.to_thread(
                                shutil.rmtree, session_path, ignore_errors=True
                            )
                            print(
                                f"[Garbage Collector] Expired session deleted: {session_id}"
                            )
                    except (OSError, json.JSONDecodeError) as e:
                        print(
                            f"[Garbage Collector] Failed to process session {session_id}: {type(e).__name__} - {e}"
                        )

        # Runs at every hour.
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # CPU-based semaphore initialization
    cpu_count = os.cpu_count() or 2
    max_concurrent = max(1, cpu_count - 1)
    app.state.script_semaphore = asyncio.Semaphore(max_concurrent)

    # On server startup: Create session directory and start garbage collector.
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    gc_task = asyncio.create_task(garbage_collector())
    yield

    # On server shutdown: Shut down garbage collector.
    gc_task.cancel()


# ==========================================
# FastAPI Initialization
# ==========================================


app = FastAPI(title="SISAL AutoQC API", lifespan=lifespan, root_path=ROOT_PATH)


@app.middleware("http")
async def override_proxy_prefix(request: Request, call_next):
    request.scope["root_path"] = ROOT_PATH
    return await call_next(request)


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
        "upload_max_size_mb": UPLOAD_MAX_SIZE_MB,
    }


# ==========================================
# Web / Jinja2 Templates
# ==========================================


templates = Jinja2Templates(directory="web")


@app.get("/", response_class=HTMLResponse)
@app.get("/{page}.html", response_class=HTMLResponse)
async def serve_pages(request: Request, page: str = "index"):
    valid_pages = [
        "index",
        "stepper",
        "upload",
        "validate",
        "plots",
        "download",
        "about",
    ]

    if page not in valid_pages:
        raise HTTPException(status_code=404, detail="Page not found")

    return templates.TemplateResponse(
        request=request,
        name=f"{page}.html",
        context={"request": request, "root_path": ROOT_PATH},
    )


app.mount("/", StaticFiles(directory="web"), name="web_static")
