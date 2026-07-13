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
    """
    Creates a valid session directory structure with a dummy input file.
    Returns the generated session_id.
    """
    session_id = "test-plots-1234"
    base_dir = tmp_path / session_id
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"

    os.makedirs(input_dir)
    os.makedirs(output_dir)

    # Create a dummy input file
    test_file = input_dir / "speleothem_data.xlsx"
    test_file.write_text("dummy excel content")

    return session_id


# ==========================================
# SUITE 1: Run Plots - Pre-execution Validations
# ==========================================


def test_run_plots_session_not_found(client, tmp_path):
    """Tests that triggering plots for a non-existent session returns 404."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post("/api/run_plots/invalid-session-id")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


def test_run_plots_no_input_file(client, tmp_path):
    """Tests that execution fails with 400 if the session has no uploaded files."""
    session_id = "empty-session"
    os.makedirs(tmp_path / session_id / "input")
    os.makedirs(tmp_path / session_id / "output")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/run_plots/{session_id}")

        assert response.status_code == 400
        assert "No file found" in response.json()["detail"]


# ==========================================
# SUITE 2: Run Plots - Subprocess Execution
# ==========================================


@patch("src.pages.plots.asyncio.create_subprocess_exec")
def test_run_plots_successful_execution(mock_exec, client, tmp_path, mock_session):
    """Tests successful R script execution and proper detection of generated plots."""
    # Setup: Mock subprocess to return success code
    mock_process = AsyncMock()
    mock_process.stdout = MockStreamReader(
        [
            b'{"priority": "Status message", "percentage": 50, "section": "Plotting", "description": "Generating maps..."}\n'
        ]
    )
    mock_process.stderr.read = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock()
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    # Setup: Pre-create mock plot images in the output directory
    (tmp_path / mock_session / "output" / "plot_01_age.png").write_bytes(b"img1")
    (tmp_path / mock_session / "output" / "plot_02_depth.png").write_bytes(b"img2")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/run_plots/{mock_session}")

        assert response.status_code == 200
        lines = [line for line in response.text.split("\n") if line.strip()]
        data = json.loads(lines[-1])

        assert data["status"] == "success"
        assert len(data["plots"]) == 2
        assert "plot_01_age.png" in data["plots"]


@patch("src.pages.plots.asyncio.create_subprocess_exec")
def test_run_plots_json_decode_error_handled(mock_exec, client, tmp_path, mock_session):
    """Tests that non-JSON output from the subprocess does not crash the stream (JSONDecodeError is handled gracefully)."""
    # Setup: Mock subprocess with mixed JSON and plain text output
    mock_process = AsyncMock()
    mock_process.stdout = MockStreamReader(
        [
            b"Loading required package: ggplot2\n",  # Invalid JSON, should trigger JSONDecodeError and be ignored
            b'{"priority": "Status message", "percentage": 50, "section": "Plotting", "description": "Generating maps..."}\n',
            b'[1] "Warning: non-finite values removed"\n',  # Invalid JSON
        ]
    )
    mock_process.stderr.read = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock()
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    # Setup: Pre-create mock plot images
    (tmp_path / mock_session / "output" / "plot_01_age.png").write_bytes(b"img1")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/run_plots/{mock_session}")

        assert response.status_code == 200
        lines = [line for line in response.text.split("\n") if line.strip()]

        # The plain text lines should be silently ignored (JSONDecodeError caught),
        # so we only expect 2 JSON responses: the valid progress line and the complete line.
        assert len(lines) == 2

        progress_data = json.loads(lines[0])
        assert progress_data["type"] == "progress"
        assert progress_data["percentage"] == 50

        complete_data = json.loads(lines[1])
        assert complete_data["type"] == "complete"
        assert complete_data["status"] == "success"


@patch("src.pages.plots.asyncio.create_subprocess_exec")
def test_run_plots_script_failure(mock_exec, client, tmp_path, mock_session):
    """Tests that a non-zero return code from R script is handled gracefully."""
    # Setup: Mock subprocess to return an error code and stderr
    mock_process = AsyncMock()
    mock_process.stdout = MockStreamReader([])
    mock_process.stderr.read = AsyncMock(
        return_value=b"Error in ggplot2: missing aesthetics"
    )
    mock_process.wait = AsyncMock()
    mock_process.returncode = 1
    mock_exec.return_value = mock_process

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(f"/api/run_plots/{mock_session}")

        assert response.status_code == 200
        lines = [line for line in response.text.split("\n") if line.strip()]
        data = json.loads(lines[-1])

        assert data["status"] == "error"
        assert "R plotting script failed" in data["message"]
        assert "missing aesthetics" in data["stderr"]


@patch("src.pages.plots.asyncio.create_subprocess_exec")
def test_run_plots_subprocess_exception(mock_exec, client, tmp_path, mock_session):
    """Tests that unhandled Python exceptions during subprocess call return 500."""
    # Setup: Force an exception
    mock_exec.side_effect = Exception("Rscript command not found")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        with pytest.raises(Exception):
            client.post(f"/api/run_plots/{mock_session}")


# ==========================================
# SUITE 3: List Plots Endpoint
# ==========================================


def test_list_plots_success(client, tmp_path, mock_session):
    """Tests that the endpoint correctly lists all plot_*.png files."""
    # Setup: Create mixed files in output directory
    output_dir = tmp_path / mock_session / "output"
    (output_dir / "plot_1.png").write_bytes(b"img")
    (output_dir / "plot_2.png").write_bytes(b"img")
    (output_dir / "QC_log.txt").write_bytes(b"ignore me")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/plots/{mock_session}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["plots"]) == 2
        assert "plot_1.png" in data["plots"]
        assert "QC_log.txt" not in data["plots"]


def test_list_plots_session_not_found(client, tmp_path):
    """Tests listing plots for an invalid session."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get("/api/plots/invalid-session")
        assert response.status_code == 404


# ==========================================
# SUITE 4: Get Plot Image Endpoint
# ==========================================


def test_get_plot_image_success(client, tmp_path, mock_session):
    """Tests successfully downloading a specific plot image."""
    image_content = b"fake png content"
    filename = "plot_result.png"
    (tmp_path / mock_session / "output" / filename).write_bytes(image_content)

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/plots/{mock_session}/{filename}")

        assert response.status_code == 200
        assert response.content == image_content
        assert response.headers["content-type"] == "image/png"


def test_get_plot_image_session_not_found(client, tmp_path):
    """Tests that requesting an image for a non-existent session returns 404."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        # Requesting a structurally valid filename but from a non-existent session
        response = client.get("/api/plots/invalid-session/plot_dummy.png")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


def test_get_plot_image_invalid_filename(client, tmp_path, mock_session):
    """Tests that filenames not starting with 'plot_' or not ending with '.png' are rejected."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        # Test wrong prefix
        resp1 = client.get(f"/api/plots/{mock_session}/map_image.png")
        assert resp1.status_code == 400

        # Test wrong extension
        resp2 = client.get(f"/api/plots/{mock_session}/plot_result.pdf")
        assert resp2.status_code == 400


def test_get_plot_image_not_found(client, tmp_path, mock_session):
    """Tests requesting a valid filename that doesn't exist on disk."""
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.get(f"/api/plots/{mock_session}/plot_missing.png")
        assert response.status_code == 404
