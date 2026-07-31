import asyncio
import json
import os
import shutil
import zipfile
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.services.api_utils import SAVED_SESSION_TIMEOUT_HOURS, get_session_paths

router = APIRouter()


# ==========================================
# Helpers
# ==========================================


def generate_readable_report(raw_log_path: str) -> str:
    """Reads the raw JSON QC log and formats it into a human-readable text report."""
    with open(raw_log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    readable_lines = [
        "==========================================================\n",
        " SISAL AutoQC Validation Report\n",
        "==========================================================\n\n",
    ]

    for line in lines:
        line = line.strip()
        try:
            data = json.loads(line)
            if data.get("priority") not in ["Status", "Status message", None]:
                prio = data.get("priority").upper()
                loc = data.get("workbook_location")
                desc = data.get("description")

                loc_str = f"[{loc}] " if loc else ""
                readable_lines.append(f"{prio}: {loc_str}{desc}\n")
        except json.JSONDecodeError:
            pass

    return "".join(readable_lines)


# ==========================================
# Download results
# ==========================================


@router.get("/api/download/{session_id}")
async def download_results(session_id: str):
    paths = get_session_paths(session_id)
    if not os.path.exists(paths["base"]):
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    output_dir = paths["output"]

    if not os.path.exists(output_dir) or not os.listdir(output_dir):
        raise HTTPException(
            status_code=400, detail="No output files available to download."
        )

    zip_path = os.path.join(paths["base"], f"SISAL_QC_Results_{session_id}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add output files (QC passed excel, log file, PDF and map)
        if os.path.exists(output_dir):
            for f in os.listdir(output_dir):
                if (
                    (f.startswith("QC_passed_SISAL_workbook") and f.endswith(".xlsx"))
                    or (f.startswith("QC_agemodel_hiatus") and f.endswith(".pdf"))
                    or (f.startswith("map_") and f.endswith(".png"))
                ):
                    zipf.write(os.path.join(output_dir, f), arcname=f)

            # 3. Add generated human-readable report
            log_files = [
                f
                for f in os.listdir(output_dir)
                if f.startswith("QC_log_") and f.endswith(".txt")
            ]

            if log_files:
                original_log_filename = log_files[0]
                raw_log_path = os.path.join(output_dir, original_log_filename)

                readable_report = generate_readable_report(raw_log_path)
                zipf.writestr(original_log_filename, readable_report)

    return FileResponse(
        path=zip_path,
        filename="SISAL_QC_Results.zip",
        media_type="application/zip",
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
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=SAVED_SESSION_TIMEOUT_HOURS)
    ).timestamp()
    metadata = {"saved": True, "expires_at": expires_at}

    def _write_metadata():
        with open(paths["metadata"], "w", encoding="utf-8") as f:
            json.dump(metadata, f)

    await asyncio.to_thread(_write_metadata)

    return {"status": "success", "message": "Session saved."}


@router.post("/api/session/{session_id}/discard")
async def discard_session(session_id: str):
    paths = get_session_paths(session_id)
    if os.path.exists(paths["base"]):
        shutil.rmtree(paths["base"], ignore_errors=True)
    return {"status": "success", "message": "Session discarded and deleted."}
