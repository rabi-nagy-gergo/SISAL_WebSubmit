import os
import json
import shutil
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.services.api_utils import SAVED_SESSION_TIMEOUT_HOURS, get_session_paths

router = APIRouter()

# ==========================================
# Download results
# ==========================================
@router.get("/api/download/{session_id}")
async def download_results(session_id: str):
    paths = get_session_paths(session_id)
    if not os.path.exists(paths["base"]):
        raise HTTPException(status_code=404, detail="Session not found or expired.")
        
    output_dir = paths["output"]
    if not os.listdir(output_dir):
        raise HTTPException(status_code=400, detail="No output files available to download.")
        
    # Creating ZIP file in session's root.
    zip_path = os.path.join(paths["base"], f"SISAL_QC_Results_{session_id}")
    shutil.make_archive(zip_path, 'zip', output_dir)
    
    return FileResponse(
        path=f"{zip_path}.zip",
        filename="SISAL_QC_Results.zip",
        media_type="application/zip"
    )

# ==========================================
# Session handler endpoints (using cookies)
# ==========================================
@router.post("/api/session/{session_id}/save")
async def save_session(session_id: str):
    paths = get_session_paths(session_id)
    if not os.path.exists(paths["base"]):
        raise HTTPException(status_code=404, detail="Session not found or expired.")
        
    # Set session expiry.
    expires_at = (datetime.now() + timedelta(hours=SAVED_SESSION_TIMEOUT_HOURS)).timestamp()
    metadata = {
        "saved": True,
        "expires_at": expires_at
    }
    with open(paths["metadata"], "w", encoding="utf-8") as f:
        json.dump(metadata, f)
        
    return {"status": "success", "message": "Session saved."}

@router.post("/api/session/{session_id}/discard")
async def discard_session(session_id: str):
    paths = get_session_paths(session_id)
    if os.path.exists(paths["base"]):
        shutil.rmtree(paths["base"], ignore_errors=True)
    return {"status": "success", "message": "Session discarded and deleted."}