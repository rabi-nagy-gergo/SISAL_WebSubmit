import asyncio
import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from src.services.api_utils import R_PLOT_SCRIPT_PATH, get_session_paths

router = APIRouter()


# ==========================================
# R Plotting
# ==========================================
@router.post("/api/run_plots/{session_id}")
async def run_plots(session_id: str, request: Request):
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

    # Run the R plotting script
    async def generate_response():
        async with request.app.state.script_semaphore:
            # Starting subprocess asynchronously
            process = await asyncio.create_subprocess_exec(
                "Rscript",
                R_PLOT_SCRIPT_PATH,
                filename,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Continuously reading standard output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode("utf-8").strip()
                if line_str:
                    try:
                        msg = json.loads(line_str)
                        if msg.get("priority") == "Status message":
                            yield (
                                json.dumps(
                                    {
                                        "type": "progress",
                                        "percentage": msg.get("percentage"),
                                        "section": msg.get("section"),
                                        "message": msg.get("description"),
                                    }
                                )
                                + "\n"
                            )
                    except json.JSONDecodeError:
                        pass

            # Capture stderr for error reporting before waiting on the process
            stderr_bytes = await process.stderr.read()
            await process.wait()

            if process.returncode != 0:
                stderr_text = (
                    stderr_bytes.decode("utf-8", errors="replace")
                    if stderr_bytes
                    else ""
                )
                yield (
                    json.dumps(
                        {
                            "type": "complete",
                            "status": "error",
                            "message": "R plotting script failed.",
                            "stderr": stderr_text[-3000:] if stderr_text else "",
                        }
                    )
                    + "\n"
                )
                return

            plot_files = sorted(
                f
                for f in os.listdir(paths["output"])
                if f.startswith("plot_") and f.endswith(".png")
            )
            yield (
                json.dumps(
                    {"type": "complete", "status": "success", "plots": plot_files}
                )
                + "\n"
            )

    # Disable proxy buffering to ensure real-time streaming of NDJSON
    headers = {
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }

    # Using StreamingResponse with NDJSON format
    return StreamingResponse(generate_response(), media_type="application/x-ndjson", headers = headers)


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
