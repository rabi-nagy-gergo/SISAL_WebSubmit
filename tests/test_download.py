import json
import os
import zipfile
from unittest.mock import patch

import pytest

# ==========================================
# Fixture for Session Setup
# ==========================================


@pytest.fixture
def mock_session(tmp_path):
    """
    Creates a valid session directory structure with dummy input and output files
    to fully test the zip filtering and log formatting logic.
    Returns the generated session_id.
    """
    session_id = "test-download-1234"
    base_dir = tmp_path / session_id
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"

    os.makedirs(input_dir)
    os.makedirs(output_dir)

    # Create input files
    (input_dir / "data.xlsx").write_text("dummy excel data")
    (input_dir / "ignore_me.txt").write_text("this should not be in zip")

    # Create output files
    # 1. Valid files that match the strict prefix/extension rules
    (output_dir / "QC_passed_SISAL_workbook_test.xlsx").write_bytes(
        b"dummy valid excel"
    )
    (output_dir / "QC_agemodel_hiatus_test.pdf").write_bytes(b"dummy valid pdf")
    (output_dir / "map_site.png").write_bytes(b"dummy valid map png")

    # 2. Invalid files that should be ignored despite being in the output directory
    (output_dir / "plot_1.pdf").write_bytes(b"dummy wrong prefix pdf")
    (output_dir / "plot_1.png").write_bytes(b"dummy wrong prefix png")

    # Create a dummy QC log with valid JSON, invalid JSON, and Status messages
    log_content = (
        '{"priority": "Status message", "description": "Running AutoQC..."}\n'
        "this is just a random text line, not valid JSON\n"
        '{"priority": "Warning", "workbook_location": "Sample data", "description": "Missing gaps."}\n'
        '{"priority": "Informative", "description": "Site is at Lat 43.0, Lon -4.8"}\n'
    )
    (output_dir / "QC_log_data.txt").write_text(log_content)

    # Create an initial metadata file
    initial_metadata = {"saved": False, "expires_at": 1000000000.0}
    with open(base_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(initial_metadata, f)

    return session_id


@pytest.fixture
def empty_mock_session(tmp_path):
    """
    Creates a session where the output directory is completely empty.
    """
    session_id = "test-empty-5678"
    base_dir = tmp_path / session_id
    os.makedirs(base_dir / "input")
    os.makedirs(base_dir / "output")
    return session_id


# ==========================================
# SUITE 1: Download Results Endpoint
# Tests generating, filtering, formatting and serving the ZIP archive
# ==========================================


def test_download_results_success(client, tmp_path, mock_session):
    """Tests that a valid session successfully generates and returns a ZIP file."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/download/{mock_session}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "SISAL_QC_Results" in response.headers["content-disposition"]

        # Verify that the zip file was physically created in the session root
        zip_file_path = tmp_path / mock_session / f"SISAL_QC_Results_{mock_session}.zip"
        assert zip_file_path.is_file()


def test_download_results_zip_contents(client, tmp_path, mock_session):
    """Tests that the ZIP archive contains the correct filtered files (Excel, PDF, map PNG, and Report) and excludes others."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        client.get(f"/api/download/{mock_session}")
        zip_file_path = tmp_path / mock_session / f"SISAL_QC_Results_{mock_session}.zip"

        # Open the generated ZIP file and verify its contents
        with zipfile.ZipFile(zip_file_path, "r") as zipf:
            file_names = zipf.namelist()

            # These should be included based on our filtering logic
            assert "QC_passed_SISAL_workbook_test.xlsx" in file_names
            assert "QC_agemodel_hiatus_test.pdf" in file_names
            assert "map_site.png" in file_names
            assert "QC_log_data.txt" in file_names

            # These should be explicitly excluded
            assert "data.xlsx" not in file_names  # In input folder
            assert "ignore_me.txt" not in file_names  # In input folder
            assert "plot_1.pdf" not in file_names  # Wrong prefix
            assert "plot_1.png" not in file_names  # Wrong prefix


def test_download_results_report_formatting(client, tmp_path, mock_session):
    """Tests that the QC log is correctly parsed from JSON and formatted into readable text inside the ZIP."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        client.get(f"/api/download/{mock_session}")
        zip_file_path = tmp_path / mock_session / f"SISAL_QC_Results_{mock_session}.zip"

        with zipfile.ZipFile(zip_file_path, "r") as zipf:
            report_content = zipf.read("QC_log_data.txt").decode("utf-8")

            # The status messages and invalid JSON lines should be ignored
            assert "Running AutoQC..." not in report_content
            assert "random text line" not in report_content

            # Valid JSON lines should be formatted properly
            assert "SISAL AutoQC Validation Report" in report_content
            assert "WARNING: [Sample data] Missing gaps." in report_content
            assert "INFORMATIVE: Site is at Lat 43.0, Lon -4.8" in report_content


def test_download_results_session_not_found(client, tmp_path):
    """Tests that requesting a download for a non-existent session returns 404."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get("/api/download/invalid-session-id")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


def test_download_results_no_output_files(client, tmp_path, empty_mock_session):
    """Tests that an empty output directory returns a 400 Bad Request."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/download/{empty_mock_session}")

        assert response.status_code == 400
        assert "No output files available" in response.json()["detail"]


# ==========================================
# SUITE 2: Save Session Endpoint
# Tests extending session expiry and updating metadata
# ==========================================


def test_save_session_success(client, tmp_path, mock_session):
    """Tests that saving a session updates the metadata.json file correctly."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/session/{mock_session}/save")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify the filesystem changes
        metadata_path = tmp_path / mock_session / "metadata.json"
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        assert metadata["saved"] is True
        # Ensure the expiration time was pushed into the future
        assert metadata["expires_at"] > 1000000000.0


def test_save_session_not_found(client, tmp_path):
    """Tests that trying to save a non-existent session returns 404."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post("/api/session/invalid-session-id/save")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


# ==========================================
# SUITE 3: Discard Session Endpoint
# Tests complete deletion of the session directory
# ==========================================


def test_discard_session_success(client, tmp_path, mock_session):
    """Tests that discarding a session physically deletes its directory structure."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        session_dir = tmp_path / mock_session
        assert session_dir.is_dir()

        response = client.post(f"/api/session/{mock_session}/discard")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify the session directory is completely gone
        assert not session_dir.exists()


def test_discard_session_already_deleted(client, tmp_path):
    """
    Tests that discarding a session that doesn't exist anymore
    still returns success without crashing (idempotent behavior).
    """
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post("/api/session/already-gone-session/discard")

        assert response.status_code == 200
        assert response.json()["status"] == "success"
