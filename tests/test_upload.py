import json
from unittest.mock import patch

# ==========================================
# SUITE 1: API Response Validation
# Tests focusing on the HTTP status and JSON response body
# ==========================================


def test_upload_excel_file_returns_success(client, tmp_path):
    """Tests that uploading an Excel file returns an HTTP 200 success status."""
    file_content = b"dummy excel binary content"
    filename = "test_data.xlsx"

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={
                "file": (
                    filename,
                    file_content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"


def test_upload_excel_file_returns_session_data(client, tmp_path):
    """Tests that the API response contains the correct filename and a generated session_id."""
    file_content = b"dummy excel binary content"
    filename = "test_data.xlsx"

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={
                "file": (
                    filename,
                    file_content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        data = response.json()
        assert data["filename"] == filename
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0


def test_upload_non_excel_file_returns_success(client, tmp_path):
    """
    Tests that non-Excel files are currently accepted by the endpoint.
    This serves as a baseline before strict .xlsx validation is implemented.
    """
    file_content = b"just some plain text"
    filename = "not_an_excel.txt"

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload", files={"file": (filename, file_content, "text/plain")}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"


# ==========================================
# SUITE 2: Filesystem State Validation
# Tests focusing on directory creation and file saving
# ==========================================


def test_upload_creates_session_directories(client, tmp_path):
    """Tests that the endpoint creates the required 'input' and 'output' folders for the session."""
    filename = "test_data.xlsx"

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={
                "file": (
                    filename,
                    b"content",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        session_id = response.json()["session_id"]
        session_dir = tmp_path / session_id

        assert session_dir.is_dir()
        assert (session_dir / "input").is_dir()
        assert (session_dir / "output").is_dir()


def test_upload_saves_file_to_input_dir(client, tmp_path):
    """Tests that the uploaded file is physically saved into the 'input' directory."""
    file_content = b"specific file content"
    filename = "test_data.xlsx"

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={
                "file": (
                    filename,
                    file_content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        session_id = response.json()["session_id"]
        saved_file_path = tmp_path / session_id / "input" / filename

        assert saved_file_path.is_file()
        assert saved_file_path.read_bytes() == file_content


# ==========================================
# SUITE 3: Metadata Generation Validation
# Tests focusing on the metadata creation and content
# ==========================================


def test_upload_creates_metadata_file(client, tmp_path):
    """Tests that a metadata.json file is generated inside the session directory."""
    filename = "test_data.xlsx"

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={
                "file": (
                    filename,
                    b"content",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        session_id = response.json()["session_id"]
        metadata_path = tmp_path / session_id / "metadata.json"

        assert metadata_path.is_file()


def test_upload_metadata_contains_correct_initial_state(client, tmp_path):
    """Tests that the generated metadata.json contains the expected initial keys and values."""
    filename = "test_data.xlsx"

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={
                "file": (
                    filename,
                    b"content",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        session_id = response.json()["session_id"]
        metadata_path = tmp_path / session_id / "metadata.json"

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        assert metadata["saved"] is False
        assert "expires_at" in metadata
        assert isinstance(metadata["expires_at"], float)
