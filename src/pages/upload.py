import os
import uuid
import json
import shutil
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File

from src.services.api_utils import SESSION_TIMEOUT_HOURS, get_session_paths

router = APIRouter()


# ==========================================
# File upload (Sisal .xlsx worksheet)
# ==========================================
@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    paths = get_session_paths(session_id)

    # Create directory structure for this session.
    os.makedirs(paths["input"], exist_ok=True)
    os.makedirs(paths["output"], exist_ok=True)

    # Saving file in input folder.
    file_path = os.path.join(paths["input"], file.filename)
    with open(file_path, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    # Creating metadata (Saved: false, set session expiry)
    expires_at = (datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)).timestamp()
    metadata = {"saved": False, "expires_at": expires_at}

    with open(paths["metadata"], "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    return {"status": "success", "session_id": session_id, "filename": file.filename}
