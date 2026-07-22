import json
import os
from unittest.mock import AsyncMock, patch

import pytest


class MockStreamReader:
    def __init__(self, lines):
        self.lines = lines
        self.idx = 0

    async def readline(self):
        if self.idx < len(self.lines):
            val = self.lines[self.idx]
            self.idx += 1
            return val
        return b""


# ==========================================
# Fixture for Session Setup
# ==========================================


@pytest.fixture
def mock_session(tmp_path):
    session_id = "test-val-1234"
    base_dir = tmp_path / session_id
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"

    os.makedirs(input_dir)
    os.makedirs(output_dir)

    test_file = input_dir / "test_workbook.xlsx"
    test_file.write_text("dummy content")

    return session_id


# ==========================================
# SUITE 1: Validation - Pre-execution Errors
# ==========================================


def test_validate_session_not_found(client, tmp_path):
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post("/api/validate/invalid-session-id")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


def test_validate_no_input_file(client, tmp_path):
    session_id = "empty-session"
    os.makedirs(tmp_path / session_id / "input")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{session_id}")

        assert response.status_code == 400
        assert "No file found" in response.json()["detail"]


# ==========================================
# SUITE 2: Validation - Subprocess Execution Success
# ==========================================


@patch("src.pages.validation.asyncio.create_subprocess_exec")
def test_validate_successful_execution(mock_exec, client, tmp_path, mock_session):
    mock_process = AsyncMock()
    mock_process.stdout = MockStreamReader(
        [
            b'{"priority": "Status message", "percentage": 10, "section": "Init", "description": "Starting"}\n'
        ]
    )
    mock_process.wait = AsyncMock()
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    log_content = '{"priority": "Informative", "description": "All good"}'
    log_path = tmp_path / mock_session / "output" / "QC_log_test_workbook.txt"
    log_path.write_text(log_content)

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{mock_session}")

        assert response.status_code == 200

        lines = [line for line in response.text.split("\n") if line.strip()]
        assert len(lines) == 2

        progress_data = json.loads(lines[0])
        assert progress_data["type"] == "progress"
        assert progress_data["percentage"] == 10

        complete_data = json.loads(lines[1])
        assert complete_data["type"] == "complete"
        assert complete_data["status"] == "success"
        assert complete_data["report"]["total_fatal"] == 0


@patch("src.pages.validation.asyncio.create_subprocess_exec")
def test_validate_log_with_invalid_json(mock_exec, client, tmp_path, mock_session):
    """Tests that a JSONDecodeError during stdout stream parsing is handled gracefully."""
    mock_process = AsyncMock()

    mock_process.stdout = MockStreamReader(
        [
            b'{"priority": "Status message", "percentage": 10, "section": "Init", "description": "Starting"}\n',
            b"Warning: This is standard text output, not a valid JSON string!\n",
            b'{"priority": "Status message", "percentage": 20, "section": "Init", "description": "Continuing"}\n',
        ]
    )
    mock_process.wait = AsyncMock()
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    log_content = '{"priority": "Informative", "description": "All good"}\n{invalid_json_here: missing_quotes}'
    log_path = tmp_path / mock_session / "output" / "QC_log_test_workbook.txt"
    log_path.write_text(log_content)

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{mock_session}")

        assert response.status_code == 200

        lines = [line for line in response.text.split("\n") if line.strip()]
        complete_data = json.loads(lines[-1])

        assert complete_data["type"] == "complete"
        assert complete_data["status"] == "success"
        assert complete_data["report"]["total_fatal"] == 0


@patch("src.pages.validation.asyncio.create_subprocess_exec")
def test_validate_subprocess_exception_handled(
    mock_exec, client, tmp_path, mock_session
):
    mock_exec.side_effect = Exception("System out of memory")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        with pytest.raises(Exception):
            client.post(f"/api/validate/{mock_session}")


# ==========================================
# SUITE 3: Validation - Subprocess Failures
# ==========================================


@patch("src.pages.validation.asyncio.create_subprocess_exec")
def test_validate_fatal_error_from_returncode(
    mock_exec, client, tmp_path, mock_session
):
    mock_process = AsyncMock()
    mock_process.stdout = MockStreamReader([])
    mock_process.wait = AsyncMock()
    mock_process.returncode = 1
    mock_exec.return_value = mock_process

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{mock_session}")

        assert response.status_code == 200

        lines = [line for line in response.text.split("\n") if line.strip()]
        complete_data = json.loads(lines[-1])
        assert complete_data["type"] == "complete"
        assert complete_data["status"] == "error"


@patch("src.pages.validation.asyncio.create_subprocess_exec")
def test_validate_fatal_error_from_log(mock_exec, client, tmp_path, mock_session):
    mock_process = AsyncMock()
    mock_process.stdout = MockStreamReader([])
    mock_process.wait = AsyncMock()
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    log_content = '{"priority": "Fatal", "description": "Critical workbook corruption"}'
    log_path = tmp_path / mock_session / "output" / "QC_log_test_workbook.txt"
    log_path.write_text(log_content)

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/validate/{mock_session}")

        assert response.status_code == 200

        lines = [line for line in response.text.split("\n") if line.strip()]
        complete_data = json.loads(lines[-1])
        assert complete_data["type"] == "complete"
        assert complete_data["status"] == "error"
        assert complete_data["report"]["total_fatal"] == 1


# ==========================================
# SUITE 4: Serve Map Endpoint
# ==========================================


def test_get_map_session_not_found(client, tmp_path):
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get("/api/map/invalid-session")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


def test_get_map_file_not_found(client, tmp_path, mock_session):
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/map/{mock_session}")

        assert response.status_code == 404
        assert "Map not found" in response.json()["detail"]


def test_get_map_success(client, tmp_path, mock_session):
    map_content = b"fake png image binary data"
    map_path = tmp_path / mock_session / "output" / "map_test_workbook.png"
    map_path.write_bytes(map_content)

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/map/{mock_session}")

        assert response.status_code == 200
        assert response.content == map_content
        assert response.headers["content-type"] == "image/png"
