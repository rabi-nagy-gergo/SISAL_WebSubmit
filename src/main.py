import os
import uuid
import json
import shutil
import asyncio
import subprocess
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Configurational constants
SESSIONS_DIR = os.getenv("SESSIONS_DIR", "sessions")
AUTOQC_SCRIPT_PATH = os.getenv("AUTOQC_SCRIPT_PATH", "src/wb_check_v15.py")

# Session timeout constants
SESSION_TIMEOUT_HOURS = float(os.getenv("SESSION_TIMEOUT_HOURS", 2.0))
SAVED_SESSION_TIMEOUT_HOURS = float(os.getenv("SAVED_SESSION_TIMEOUT_HOURS", 168.0))

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
                            print(f"[Garbage Collector] Expired session deleted: {session_id}")
                    except Exception as e:
                        print(f"[Garbage Collector] An error occurred while checking session {session_id}: {e}")
        
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

# ==========================================
# Helpers
# ==========================================
def parse_qc_log_to_json(raw_log: str) -> dict:
    parsed_data = {
        "informative_messages": [],
        "warnings": [],
        "total_warnings": 0,
        "total_errors": 0,
        "total_fatal": 0,
        "is_passed": False
    }

    for raw_line in raw_log.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            msg = {
                "priority": "Warning",
                "description": line,
                "script_location": "",
                "workbook_location": ""
            }

        priority = msg.get("priority", "Warning")
        normalized = {
            "priority": priority,
            "description": msg.get("description", ""),
            "script_location": msg.get("script_location", ""),
            "workbook_location": msg.get("workbook_location", "")
        }

        if priority == "Informative":
            parsed_data["informative_messages"].append(normalized)
        else:
            parsed_data["warnings"].append(normalized)
            if priority == "Fatal":
                parsed_data["total_fatal"] += 1
            elif priority == "Error":
                parsed_data["total_errors"] += 1
            else:
                parsed_data["total_warnings"] += 1

    parsed_data["is_passed"] = (
        parsed_data["total_warnings"] == 0
        and parsed_data["total_errors"] == 0
        and parsed_data["total_fatal"] == 0
    )
    return parsed_data

def get_session_paths(session_id: str):
    base_path = os.path.join(SESSIONS_DIR, session_id)
    return {
        "base": base_path,
        "input": os.path.join(base_path, "input"),
        "output": os.path.join(base_path, "output"),
        "metadata": os.path.join(base_path, "metadata.json")
    }

@app.get("/api/config")
async def get_config():
    return {
        "session_timeout_hours": SESSION_TIMEOUT_HOURS,
        "saved_session_timeout_hours": SAVED_SESSION_TIMEOUT_HOURS
    }

# ==========================================
# File upload (Sisal .xlsx worksheet)
# ==========================================
@app.post("/api/upload")
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
    metadata = {
        "saved": False,
        "expires_at": expires_at
    }

    with open(paths["metadata"], "w", encoding="utf-8") as f:
        json.dump(metadata, f)
        
    return {"status": "success", "session_id": session_id, "filename": file.filename}

# ==========================================
# AutoQC Validation
# ==========================================
@app.post("/api/validate/{session_id}")
async def validate_file(session_id: str):
    paths = get_session_paths(session_id)
    if not os.path.exists(paths["base"]):
        raise HTTPException(status_code=404, detail="Session not found or expired.")
        
    # Search for the uploaded file in input folder.
    files = os.listdir(paths["input"])
    if not files:
        raise HTTPException(status_code=400, detail="No file found in session.")
    filename = files[0]
    
    # Set up subprocess environment variables.
    env = os.environ.copy()
    env["SISAL_INPUT_DIR"] = os.path.abspath(paths["input"])
    env["SISAL_OUTPUT_DIR"] = os.path.abspath(paths["output"])
    
    # Run AutoQC script.
    try:
        result = subprocess.run(
            ["python", AUTOQC_SCRIPT_PATH, filename],
            capture_output=True,
            text=True,
            env=env
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute validation script: {str(e)}")
    
    # Process the structured QC log generated by AutoQC.
    log_path = os.path.join(paths["output"], "QC_log_" + os.path.splitext(filename)[0] + ".txt")
    raw_log = ""
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            raw_log = f.read()

    report = parse_qc_log_to_json(raw_log)
    
    if result.returncode != 0 or report["total_fatal"] > 0:
        if not report["warnings"]:
            report["warnings"].append({
                "priority": "Fatal",
                "description": "A fatal error occurred while running AutoQC, but no structured log entry was produced.",
                "script_location": "main.py",
                "workbook_location": ""
            })
            report["total_fatal"] = 1
        return {
            "status": "fatal_error",
            "message": "A fatal error occurred during workbook quality check.",
            "report": report
        }
        
    return {"status": "success", "report": report}

# ==========================================
# Serve Generated Map Image
# ==========================================
@app.get("/api/map/{session_id}")
async def get_map(session_id: str):
    paths = get_session_paths(session_id)
    if not os.path.exists(paths["output"]):
        raise HTTPException(status_code=404, detail="Session not found.")
        
    # Search for the generated png map
    for file in os.listdir(paths["output"]):
        if file.startswith("map_") and file.endswith(".png"):
            return FileResponse(os.path.join(paths["output"], file))
            
    raise HTTPException(status_code=404, detail="Map not found.")

# ==========================================
# Download results
# ==========================================
@app.get("/api/download/{session_id}")
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
@app.post("/api/session/{session_id}/save")
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

@app.post("/api/session/{session_id}/discard")
async def discard_session(session_id: str):
    paths = get_session_paths(session_id)
    if os.path.exists(paths["base"]):
        shutil.rmtree(paths["base"], ignore_errors=True)
    return {"status": "success", "message": "Session discarded and deleted."}

# Mount frontend code to root directory
app.mount("/", StaticFiles(directory="web", html=True), name="web")