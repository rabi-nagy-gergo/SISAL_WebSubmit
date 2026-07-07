import os
import json

# Configurational constants
SESSIONS_DIR = os.getenv("SESSIONS_DIR", "sessions")
AUTOQC_SCRIPT_PATH = os.getenv("AUTOQC_SCRIPT_PATH", "src/services/wb_check_v15.py")
R_PLOT_SCRIPT_PATH = os.getenv("R_PLOT_SCRIPT_PATH", "src/services/run_plots.R")

# Session timeout constants
SESSION_TIMEOUT_HOURS = float(os.getenv("SESSION_TIMEOUT_HOURS", 2.0))
SAVED_SESSION_TIMEOUT_HOURS = float(os.getenv("SAVED_SESSION_TIMEOUT_HOURS", 168.0))


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
        "is_passed": False,
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
                "workbook_location": "",
            }

        priority = msg.get("priority", "Warning")
        normalized = {
            "priority": priority,
            "description": msg.get("description", ""),
            "script_location": msg.get("script_location", ""),
            "workbook_location": msg.get("workbook_location", ""),
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
        "metadata": os.path.join(base_path, "metadata.json"),
    }
