import os
import subprocess
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.services.api_utils import R_PLOT_SCRIPT_PATH, get_session_paths

router = APIRouter()


# ==========================================
# R Plotting
# ==========================================
@router.post("/api/run_plots/{session_id}")
async def run_plots(session_id: str):
    paths = get_session_paths(session_id)
    if not os.path.exists(paths["base"]):
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    files = os.listdir(paths["input"])
    if not files:
        raise HTTPException(status_code=400, detail="No file found in session.")
    filename = files[0]

    env = os.environ.copy()
    env["SISAL_INPUT_DIR"] = os.path.abspath(paths["input"])
    env["SISAL_OUTPUT_DIR"] = os.path.abspath(paths["output"])

    try:
        result = subprocess.run(
            ["Rscript", R_PLOT_SCRIPT_PATH, filename],
            capture_output=True,
            text=True,
            env=env,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to execute R plotting script: {str(e)}"
        )

    if result.returncode != 0:
        return {
            "status": "error",
            "message": "R plotting script failed.",
            "stderr": result.stderr[-3000:] if result.stderr else "",
        }

    plot_files = sorted(
        f
        for f in os.listdir(paths["output"])
        if f.startswith("plot_") and f.endswith(".png")
    )
    return {"status": "success", "plots": plot_files}


@router.get("/api/plots/{session_id}")
async def list_plots(session_id: str):
    paths = get_session_paths(session_id)
    if not os.path.exists(paths["output"]):
        raise HTTPException(status_code=404, detail="Session not found.")

    plot_files = sorted(
        f
        for f in os.listdir(paths["output"])
        if f.startswith("plot_") and f.endswith(".png")
    )
    return {"plots": plot_files}


@router.get("/api/plots/{session_id}/{filename}")
async def get_plot_image(session_id: str, filename: str):
    paths = get_session_paths(session_id)
    if not os.path.exists(paths["output"]):
        raise HTTPException(status_code=404, detail="Session not found.")

    if not filename.endswith(".png") or not filename.startswith("plot_"):
        raise HTTPException(status_code=400, detail="Invalid plot filename.")

    plot_path = os.path.join(paths["output"], filename)
    if not os.path.isfile(plot_path):
        raise HTTPException(status_code=404, detail="Plot not found.")

    return FileResponse(plot_path, media_type="image/png")
