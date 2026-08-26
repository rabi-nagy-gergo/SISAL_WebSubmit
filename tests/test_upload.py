import json
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.pages.upload import verify_turnstile_token

# ==========================================
# SUITE 1: API Response Validation
# ==========================================


@patch("src.pages.upload.verify_turnstile_token", return_value=True)
def test_upload_excel_file_returns_success(mock_verify, client, tmp_path):
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
            data={"captcha_token": "dummy_token"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"


@patch("src.pages.upload.verify_turnstile_token", return_value=True)
def test_upload_excel_file_returns_session_data(mock_verify, client, tmp_path):
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
            data={"captcha_token": "dummy_token"},
        )

        data = response.json()
        assert data["filename"] == filename
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0


@patch("src.pages.upload.verify_turnstile_token", return_value=True)
def test_upload_non_excel_file_returns_success(mock_verify, client, tmp_path):
    file_content = b"just some plain text"
    filename = "not_an_excel.txt"

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={"file": (filename, file_content, "text/plain")},
            data={"captcha_token": "dummy_token"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"


# ==========================================
# SUITE 2: Filesystem State Validation
# ==========================================


@patch("src.pages.upload.verify_turnstile_token", return_value=True)
def test_upload_creates_session_directories(mock_verify, client, tmp_path):
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
            data={"captcha_token": "dummy_token"},
        )

        session_id = response.json()["session_id"]
        session_dir = tmp_path / session_id

        assert session_dir.is_dir()
        assert (session_dir / "input").is_dir()
        assert (session_dir / "output").is_dir()


@patch("src.pages.upload.verify_turnstile_token", return_value=True)
def test_upload_saves_file_to_input_dir(mock_verify, client, tmp_path):
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
            data={"captcha_token": "dummy_token"},
        )

        session_id = response.json()["session_id"]
        saved_file_path = tmp_path / session_id / "input" / filename

        assert saved_file_path.is_file()
        assert saved_file_path.read_bytes() == file_content


# ==========================================
# SUITE 3: Metadata Generation Validation
# ==========================================


@patch("src.pages.upload.verify_turnstile_token", return_value=True)
def test_upload_creates_metadata_file(mock_verify, client, tmp_path):
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
            data={"captcha_token": "dummy_token"},
        )

        session_id = response.json()["session_id"]
        metadata_path = tmp_path / session_id / "metadata.json"

        assert metadata_path.is_file()


@patch("src.pages.upload.verify_turnstile_token", return_value=True)
def test_upload_metadata_contains_correct_initial_state(mock_verify, client, tmp_path):
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
            data={"captcha_token": "dummy_token"},
        )

        session_id = response.json()["session_id"]
        metadata_path = tmp_path / session_id / "metadata.json"

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        assert metadata["saved"] is False
        assert "expires_at" in metadata
        assert isinstance(metadata["expires_at"], float)


# ==========================================
# SUITE 4: Captcha Requirement Endpoint Tests
# ==========================================


def test_requires_captcha_invalid_json_metadata(client, tmp_path):
    session_id = "test-corrupted-session"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True)

    metadata_file = session_dir / "metadata.json"
    metadata_file.write_text("{this_is_not_a_valid_json_format:", encoding="utf-8")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        client.cookies = {"sisal_session_id": session_id}

        response = client.get("/api/upload/requires-captcha")

        assert response.status_code == 200
        assert response.json() == {"requires_captcha": True}


def test_requires_captcha_no_cookie(client):
    response = client.get("/api/upload/requires-captcha")
    assert response.status_code == 200
    assert response.json() == {"requires_captcha": True}


def test_requires_captcha_valid_cookie(client, tmp_path):
    session_id = "test-session-123"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True)

    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
    with open(session_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump({"expires_at": expires}, f)

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        client.cookies = {"sisal_session_id": session_id}

        response = client.get("/api/upload/requires-captcha")

        assert response.status_code == 200
        assert response.json() == {"requires_captcha": False}


def test_requires_captcha_expired_cookie(client, tmp_path):
    session_id = "test-session-123"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True)

    expires = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
    with open(session_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump({"expires_at": expires}, f)

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        client.cookies = {"sisal_session_id": session_id}

        response = client.get("/api/upload/requires-captcha")

        assert response.status_code == 200
        assert response.json() == {"requires_captcha": True}


# ==========================================
# SUITE 5: Validation and Edge Cases (Limits, invalid tokens)
# ==========================================


@patch("src.pages.upload.get_sessions_dir_size")
def test_upload_storage_limit_reached(mock_get_size, client):
    # 1025 MB exceeds the default 1024.0 MB quota
    mock_get_size.return_value = 1025 * 1024 * 1024

    response = client.post(
        "/api/upload",
        files={
            "file": (
                "test.xlsx",
                b"data",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 507
    assert "limit reached" in response.json()["detail"]


def test_upload_missing_captcha_token(client, tmp_path):
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={
                "file": (
                    "test.xlsx",
                    b"data",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert response.status_code == 400
        assert "CAPTCHA verification is required" in response.json()["detail"]


@patch("src.pages.upload.verify_turnstile_token", return_value=False)
def test_upload_invalid_captcha_token(mock_verify, client, tmp_path):
    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        response = client.post(
            "/api/upload",
            files={
                "file": (
                    "test.xlsx",
                    b"data",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"captcha_token": "bad_token"},
        )

        assert response.status_code == 400
        assert "Invalid CAPTCHA" in response.json()["detail"]


@patch("src.pages.upload.verify_turnstile_token", return_value=True)
def test_upload_invalid_json_metadata_prevents_reuse(mock_verify, client, tmp_path):
    session_id = "corrupted-session-123"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True)

    metadata_file = session_dir / "metadata.json"
    metadata_file.write_text("{this_json_is_not_valid:", encoding="utf-8")

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        client.cookies = {"sisal_session_id": session_id}

        response = client.post(
            "/api/upload",
            files={
                "file": (
                    "test.xlsx",
                    b"data",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"captcha_token": "dummy_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        assert data["session_id"] != session_id
        assert len(data["session_id"]) > 0


# ==========================================
# SUITE 6: Session Reuse Validation
# ==========================================


def test_upload_with_valid_session_cookie_reuses_session(client, tmp_path):
    session_id = "reuse-session-123"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True)
    (session_dir / "input").mkdir()
    (session_dir / "output").mkdir()

    # Create a dummy old file to ensure the folder gets cleared
    old_file = session_dir / "input" / "old_file.txt"
    old_file.write_text("old data")

    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
    with open(session_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump({"expires_at": expires}, f)

    with patch("src.services.api_utils.SESSIONS_DIR", str(tmp_path)):
        client.cookies = {"sisal_session_id": session_id}

        response = client.post(
            "/api/upload",
            files={
                "file": (
                    "new_test.xlsx",
                    b"new data",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

        # Verify old folder was cleared and new file exists
        assert not old_file.exists()
        assert (session_dir / "input" / "new_test.xlsx").exists()


# ==========================================
# SUITE 7: Turnstile Token Verification Internal Logic
# ==========================================


@patch("src.pages.upload.urllib.request.urlopen")
def test_verify_turnstile_token_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"success": true}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    assert verify_turnstile_token("dummy_token") is True


@patch("src.pages.upload.urllib.request.urlopen")
def test_verify_turnstile_token_failure(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = (
        b'{"success": false, "error-codes": ["invalid-input-response"]}'
    )
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    assert verify_turnstile_token("dummy_token") is False


@patch(
    "src.pages.upload.urllib.request.urlopen", side_effect=urllib.error.URLError(...)
)
def test_verify_turnstile_token_network_exception(mock_urlopen):
    assert verify_turnstile_token("dummy_token") is False
