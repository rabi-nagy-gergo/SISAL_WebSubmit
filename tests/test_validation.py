import os
import pytest
from unittest.mock import patch, MagicMock

# ==========================================
# Fixture for Session Setup
# ==========================================

@pytest.fixture
def mock_session(tmp_path):
    """
    Creates a valid session directory structure with a dummy input file.
    Returns the generated session_id.
    """
    session_id = "test-val-1234"
    base_dir = tmp_path / session_id
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    
    os.makedirs(input_dir)
    os.makedirs(output_dir)
    
    # Create a dummy input file
    test_file = input_dir / "test_workbook.xlsx"
    test_file.write_text("dummy content")
    
    return session_id

# ==========================================
# SUITE 1: Validation - Pre-execution Errors
# Tests for missing sessions or empty input directories
# ==========================================

def test_validate_session_not_found(client, tmp_path):
    """Tests that validating a non-existent session returns 404."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post("/api/validate/invalid-session-id")
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

def test_validate_no_input_file(client, tmp_path):
    """Tests that validation fails with 400 if the session exists but has no files."""
    session_id = "empty-session"
    os.makedirs(tmp_path / session_id / "input")
    
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{session_id}")
        
        assert response.status_code == 400
        assert "No file found" in response.json()["detail"]


# ==========================================
# SUITE 2: Validation - Subprocess Execution Success
# Tests for successful script execution and log processing
# ==========================================

@patch("src.pages.validation.subprocess.run")
def test_validate_successful_execution(mock_run, client, tmp_path, mock_session):
    """Tests that a successful subprocess run returns a success status and parsed report."""
    mock_run.return_value = MagicMock(returncode=0)
    
    # Setup: Pre-create the expected QC log file in the output directory
    log_content = '{"priority": "Informative", "description": "All good"}'
    log_path = tmp_path / mock_session / "output" / "QC_log_test_workbook.txt"
    log_path.write_text(log_content)
    
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{mock_session}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["report"]["total_fatal"] == 0

@patch("src.pages.validation.subprocess.run")
def test_validate_subprocess_exception_handled(mock_run, client, tmp_path, mock_session):
    """Tests that if subprocess raises a Python exception, the API returns a 500 error."""
    mock_run.side_effect = Exception("System out of memory")
    
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{mock_session}")
        
        assert response.status_code == 500
        assert "Failed to execute validation script" in response.json()["detail"]


# ==========================================
# SUITE 3: Validation - Subprocess Failures
# Tests for script crashes or fatal errors in the log
# ==========================================

@patch("src.pages.validation.subprocess.run")
def test_validate_fatal_error_from_returncode(mock_run, client, tmp_path, mock_session):
    """Tests that a non-zero return code (crash) triggers a fatal_error response."""
    # Setup: Mock subprocess to return an error code
    mock_run.return_value = MagicMock(returncode=1)
    
    # Intentionally NOT creating a log file to test the fallback logic
    
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{mock_session}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fatal_error"
        # The API should have injected a fallback fatal warning
        assert data["report"]["total_fatal"] == 1

@patch("src.pages.validation.subprocess.run")
def test_validate_fatal_error_from_log(mock_run, client, tmp_path, mock_session):
    """Tests that a zero return code but a 'Fatal' log entry triggers a fatal_error response."""
    mock_run.return_value = MagicMock(returncode=0)
    
    # Setup: Log file containing a Fatal error
    log_content = '{"priority": "Fatal", "description": "Critical workbook corruption"}'
    log_path = tmp_path / mock_session / "output" / "QC_log_test_workbook.txt"
    log_path.write_text(log_content)
    
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{mock_session}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fatal_error"
        assert data["report"]["total_fatal"] == 1


# ==========================================
# SUITE 4: Serve Map Endpoint
# Tests for retrieving the generated .png map
# ==========================================

def test_get_map_session_not_found(client, tmp_path):
    """Tests that requesting a map for an invalid session returns 404."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get("/api/map/invalid-session")
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

def test_get_map_file_not_found(client, tmp_path, mock_session):
    """Tests that requesting a map when no map file exists returns 404."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/map/{mock_session}")
        
        assert response.status_code == 404
        assert "Map not found" in response.json()["detail"]

def test_get_map_success(client, tmp_path, mock_session):
    """Tests that an existing map file is successfully served to the client."""
    # Setup: Create a dummy map file in the output directory
    map_content = b"fake png image binary data"
    map_path = tmp_path / mock_session / "output" / "map_test_workbook.png"
    map_path.write_bytes(map_content)
    
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/map/{mock_session}")
        
        assert response.status_code == 200
        assert response.content == map_content
        assert response.headers["content-type"] == "image/png"