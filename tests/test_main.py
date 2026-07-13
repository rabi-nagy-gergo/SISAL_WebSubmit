import asyncio
import json
import os
from unittest.mock import patch

import pytest

from src.main import app, garbage_collector

# ==========================================
# SUITE 1: API Config Endpoint
# Tests the configuration exposure endpoint
# ==========================================


def test_get_config_returns_expected_keys(client):
    """Tests that the config endpoint returns the required timeout settings."""
    response = client.get("/api/config")

    assert response.status_code == 200
    data = response.json()

    assert "session_timeout_hours" in data
    assert "saved_session_timeout_hours" in data
    assert isinstance(data["session_timeout_hours"], float)


# ==========================================
# SUITE 2: Garbage Collector Background Task
# Tests the automated cleanup of expired sessions
# ==========================================


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep")
async def test_garbage_collector_deletes_expired_sessions(mock_sleep, tmp_path):
    """
    Tests that the GC properly identifies and deletes expired sessions,
    while leaving valid sessions intact.
    """
    # Setup: Create mock SESSIONS_DIR
    sessions_dir = tmp_path / "sessions"
    os.makedirs(sessions_dir)

    # 1. Create an EXPIRED session (timestamp in the past)
    expired_id = "expired-session"
    os.makedirs(sessions_dir / expired_id)
    with open(sessions_dir / expired_id / "metadata.json", "w") as f:
        json.dump({"expires_at": 10000.0}, f)  # Old timestamp

    # 2. Create a VALID session (timestamp far in the future)
    valid_id = "valid-session"
    os.makedirs(sessions_dir / valid_id)
    future_time = asyncio.get_event_loop().time() + 9999999999.0
    with open(sessions_dir / valid_id / "metadata.json", "w") as f:
        json.dump({"expires_at": future_time}, f)

    # Setup: We must break the infinite "while True" loop in the GC.
    # We force asyncio.sleep to raise a CancelledError.
    mock_sleep.side_effect = asyncio.CancelledError

    with patch("src.main.SESSIONS_DIR", str(sessions_dir)):
        try:
            # Act: Run the garbage collector
            await garbage_collector()
        except asyncio.CancelledError:
            # Expected behavior to break the loop
            pass

    # Assert: The expired session should be deleted, valid should remain
    assert not (sessions_dir / expired_id).exists()
    assert (sessions_dir / valid_id).exists()


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep")
async def test_garbage_collector_ignores_missing_metadata(mock_sleep, tmp_path):
    """Tests that the GC doesn't crash if a session folder lacks metadata.json."""
    sessions_dir = tmp_path / "sessions"
    os.makedirs(sessions_dir)

    # Create a corrupted session folder without metadata.json
    corrupted_id = "corrupted-session"
    os.makedirs(sessions_dir / corrupted_id)

    mock_sleep.side_effect = asyncio.CancelledError

    with patch("src.main.SESSIONS_DIR", str(sessions_dir)):
        try:
            await garbage_collector()
        except asyncio.CancelledError:
            pass

    # Assert: Folder should still exist, GC should just skip it without crashing
    assert (sessions_dir / corrupted_id).exists()


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep")
async def test_garbage_collector_handles_corrupted_metadata_exception(
    mock_sleep, tmp_path
):
    """Tests that the GC catches and handles exceptions gracefully."""
    sessions_dir = tmp_path / "sessions"
    os.makedirs(sessions_dir)

    # Create a session folder with a corrupted metadata.json (Invalid JSON)
    corrupted_id = "invalid-json-session"
    os.makedirs(sessions_dir / corrupted_id)
    with open(
        sessions_dir / corrupted_id / "metadata.json", "w", encoding="utf-8"
    ) as f:
        f.write("{this is not valid json, it will raise JSONDecodeError}")

    mock_sleep.side_effect = asyncio.CancelledError

    with patch("src.main.SESSIONS_DIR", str(sessions_dir)):
        try:
            await garbage_collector()
        except asyncio.CancelledError:
            pass

    # Assert: The exception inside the 'try' block was caught,
    # the infinite loop didn't crash, and the folder is simply skipped.
    assert (sessions_dir / corrupted_id).exists()


# ==========================================
# SUITE 3: Lifespan Events (Startup/Shutdown)
# ==========================================


def test_lifespan_creates_sessions_directory(tmp_path):
    """
    Tests that starting the FastAPI application automatically creates
    the sessions directory if it does not exist.
    """
    # Point SESSIONS_DIR to a folder that DOES NOT exist yet
    test_sessions_dir = tmp_path / "new_empty_sessions_dir"

    with patch("src.main.SESSIONS_DIR", str(test_sessions_dir)):
        # Act: using the TestClient inside a 'with' block triggers the startup/shutdown events
        from fastapi.testclient import TestClient

        with TestClient(app):
            # Assert: The lifespan should have created the directory
            assert test_sessions_dir.is_dir()
