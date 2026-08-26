import asyncio
import json
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, File, Form, HTTPException, UploadFile

from src.services.api_utils import (
    SESSION_TIMEOUT_HOURS,
    SESSIONS_DIR,
    SESSIONS_MAX_SIZE_MB,
    TURNSTILE_SECRET_KEY,
    get_session_paths,
    get_sessions_dir_size,
)

router = APIRouter()


def verify_turnstile_token(token: str) -> bool:
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = urllib.parse.urlencode(
        {"secret": TURNSTILE_SECRET_KEY, "response": token}
    ).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return result.get("success", False)
    except urllib.error.URLError as e:
        print(f"[Captcha Error] Validation failed: {e}")
        return False


def _read_metadata_sync(path: str) -> dict:
    """Helper function to read metadata synchronously."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==========================================
# Captcha requirement check
# ==========================================
@router.get("/api/upload/requires-captcha")
async def check_captcha_requirement(
    cookie_session_id: Annotated[str | None, Cookie(alias="sisal_session_id")] = None,
):
    """
    Checks if the user has a valid, unexpired session.
    Returns true if a CAPTCHA is required (no valid session), false otherwise.
    """
    if cookie_session_id:
        temp_paths = get_session_paths(cookie_session_id)
        if os.path.exists(temp_paths["base"]) and os.path.exists(
            temp_paths["metadata"]
        ):
            try:
                meta = await asyncio.to_thread(
                    _read_metadata_sync, temp_paths["metadata"]
                )
                now = datetime.now(timezone.utc).timestamp()
                if now <= meta.get("expires_at", 0):
                    return {"requires_captcha": False}
            except (OSError, json.JSONDecodeError):
                pass

    return {"requires_captcha": True}


# ==========================================
# File upload (Sisal .xlsx worksheet)
# ==========================================
@router.post("/api/upload")
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    captcha_token: Annotated[str | None, Form()] = None,
    cookie_session_id: Annotated[str | None, Cookie(alias="sisal_session_id")] = None,
):
    current_size_bytes = await asyncio.to_thread(get_sessions_dir_size, SESSIONS_DIR)
    current_size_mb = current_size_bytes / (1024 * 1024)

    if current_size_mb >= SESSIONS_MAX_SIZE_MB:
        raise HTTPException(
            status_code=507,
            detail=(
                "Server storage limit reached. Please try again later or "
                "contact the site administrator."
            ),
        )

    session_id = None
    is_valid_session = False

    # Check if we can reuse the existing session
    if cookie_session_id:
        temp_paths = get_session_paths(cookie_session_id)
        if os.path.exists(temp_paths["base"]) and os.path.exists(
            temp_paths["metadata"]
        ):
            try:
                meta = await asyncio.to_thread(
                    _read_metadata_sync, temp_paths["metadata"]
                )
                now = datetime.now(timezone.utc).timestamp()
                if now <= meta.get("expires_at", 0):
                    session_id = cookie_session_id
                    is_valid_session = True
            except (OSError, json.JSONDecodeError):
                pass

    if not is_valid_session:
        if not captcha_token:
            raise HTTPException(
                status_code=400,
                detail="CAPTCHA verification is required for new uploads.",
            )

        is_human = await asyncio.to_thread(verify_turnstile_token, captcha_token)
        if not is_human:
            raise HTTPException(
                status_code=400, detail="Invalid CAPTCHA. Please try again."
            )

        session_id = str(uuid.uuid4())
        paths = get_session_paths(session_id)
    else:
        paths = get_session_paths(session_id)
        shutil.rmtree(paths["input"], ignore_errors=True)
        shutil.rmtree(paths["output"], ignore_errors=True)

    os.makedirs(paths["input"], exist_ok=True)
    os.makedirs(paths["output"], exist_ok=True)

    def _process_upload():
        file_path = os.path.join(paths["input"], file.filename)
        with open(file_path, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=SESSION_TIMEOUT_HOURS)
        ).timestamp()
        metadata = {"saved": False, "expires_at": expires_at}

        with open(paths["metadata"], "w", encoding="utf-8") as f:
            json.dump(metadata, f)

    await asyncio.to_thread(_process_upload)

    return {"status": "success", "session_id": session_id, "filename": file.filename}
