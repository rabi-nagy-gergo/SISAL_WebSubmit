import os
from unittest.mock import patch

from src.services.api_utils import (
    SESSIONS_DIR,
    get_session_paths,
    get_sessions_dir_size,
    parse_qc_log_to_json,
)

# ==========================================
# Tests for parse_qc_log_to_json
# ==========================================


def test_parse_qc_log_empty():
    """Tests that an empty log string results in zero counts and a passed status."""
    result = parse_qc_log_to_json("")

    assert result["total_warnings"] == 0
    assert result["total_errors"] == 0
    assert result["total_fatal"] == 0
    assert result["is_passed"] is True
    assert len(result["informative"]) == 0
    assert len(result["warnings"]) == 0
    assert len(result["errors"]) == 0
    assert len(result["fatals"]) == 0


def test_parse_qc_log_informative_only():
    """Tests that a log with only Informative messages passes the validation."""
    raw_log = '{"priority": "Informative", "description": "All checks passed", "script_location": "A", "workbook_location": "B"}'
    result = parse_qc_log_to_json(raw_log)

    assert result["total_warnings"] == 0
    assert result["total_errors"] == 0
    assert result["total_fatal"] == 0
    assert result["is_passed"] is True
    assert len(result["informative"]) == 1
    assert result["informative"][0]["description"] == "All checks passed"
    assert len(result["warnings"]) == 0


def test_parse_qc_log_mixed_priorities():
    """Tests that the parser correctly counts and groups different priority messages."""
    raw_log = """
    {"priority": "Informative", "description": "Started processing"}
    {"priority": "Warning", "description": "Missing optional column"}
    {"priority": "Error", "description": "Invalid date format"}
    {"priority": "Fatal", "description": "File corrupted"}
    """
    result = parse_qc_log_to_json(raw_log)

    # Counters should be exactly 1 for each error type
    assert result["total_warnings"] == 1
    assert result["total_errors"] == 1
    assert result["total_fatal"] == 1

    # Validation should fail if there are any errors or fatals
    assert result["is_passed"] is False

    assert len(result["informative"]) == 1

    assert len(result["warnings"]) == 1
    assert len(result["errors"]) == 1
    assert len(result["fatals"]) == 1


def test_parse_qc_log_invalid_json_fallback():
    """Tests handling of invalid JSON lines by treating them as Warnings."""
    raw_log = "This is an unexpected plain text error line."
    result = parse_qc_log_to_json(raw_log)

    assert result["total_warnings"] == 1
    assert result["total_errors"] == 0
    # Validation passes because warnings do not fail the submission
    assert result["is_passed"] is True

    assert len(result["warnings"]) == 1
    fallback_warning = result["warnings"][0]
    assert fallback_warning["priority"] == "Warning"
    assert (
        fallback_warning["description"]
        == "This is an unexpected plain text error line."
    )


def test_parse_qc_log_unknown_priority_fallback():
    """Tests that messages with an unrecognized priority are processed via the fallback branch (treated as Warnings)."""
    raw_log = (
        '{"priority": "UnknownLevel", "description": "Something unexpected occurred"}'
    )
    result = parse_qc_log_to_json(raw_log)

    assert result["total_warnings"] == 1
    assert result["total_errors"] == 0
    assert result["total_fatal"] == 0

    # Validation passes because fallback warnings do not fail the submission
    assert result["is_passed"] is True

    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["priority"] == "UnknownLevel"
    assert result["warnings"][0]["description"] == "Something unexpected occurred"


def test_parse_qc_log_empty_lines_ignored():
    """Tests that empty lines or whitespaces are properly skipped by the parser."""
    raw_log = "\n\n" + '{"priority": "Informative", "description": "Test"}' + "\n   \n"
    result = parse_qc_log_to_json(raw_log)

    assert len(result["informative"]) == 1
    assert result["is_passed"] is True


# ==========================================
# Tests for get_session_paths
# ==========================================


def test_get_session_paths_standard_uuid():
    """Tests directory path generation using a standard UUID string."""
    test_session_id = "test-uuid-1234-5678"
    paths = get_session_paths(test_session_id)

    expected_base = os.path.join(SESSIONS_DIR, test_session_id)

    assert paths["base"] == expected_base
    assert paths["input"] == os.path.join(expected_base, "input")
    assert paths["output"] == os.path.join(expected_base, "output")
    assert paths["metadata"] == os.path.join(expected_base, "metadata.json")


def test_get_session_paths_exact_keys():
    """Tests that exactly four specific keys are returned in the dictionary."""
    paths = get_session_paths("any-id")
    expected_keys = {"base", "input", "output", "metadata"}

    assert set(paths.keys()) == expected_keys


def test_get_session_paths_empty_string():
    """Tests path generation when an empty string is provided (edge case)."""
    paths = get_session_paths("")

    expected_base = os.path.join(SESSIONS_DIR, "")

    assert paths["base"] == expected_base
    assert paths["input"] == os.path.join(expected_base, "input")
    assert paths["output"] == os.path.join(expected_base, "output")


def test_get_session_paths_special_characters():
    """Tests path generation with special characters in the session ID."""
    test_session_id = "session_@_#_123"
    paths = get_session_paths(test_session_id)

    expected_base = os.path.join(SESSIONS_DIR, test_session_id)

    assert paths["base"] == expected_base
    assert paths["input"] == os.path.join(expected_base, "input")


# ==========================================
# Tests for get_sessions_dir_size
# ==========================================


def test_get_sessions_dir_size_non_existent(tmp_path):
    """Tests that a non-existent directory returns a size of 0."""
    fake_path = tmp_path / "does_not_exist"
    assert get_sessions_dir_size(str(fake_path)) == 0


def test_get_sessions_dir_size_empty_dir(tmp_path):
    """Tests that an empty directory returns a size of 0."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert get_sessions_dir_size(str(empty_dir)) == 0


def test_get_sessions_dir_size_with_files(tmp_path):
    """Tests that the function correctly sums the sizes of files in a directory tree."""
    root_dir = tmp_path / "test_dir"
    root_dir.mkdir()

    # Create file in root (10 bytes)
    file1 = root_dir / "file1.txt"
    file1.write_bytes(b"0123456789")

    # Create nested subfolder and file (20 bytes)
    sub_dir = root_dir / "sub"
    sub_dir.mkdir()
    file2 = sub_dir / "file2.txt"
    file2.write_bytes(b"01234567890123456789")

    # Total size should be 30 bytes
    assert get_sessions_dir_size(str(root_dir)) == 30


@patch("os.path.getsize")
def test_get_sessions_dir_size_oserror(mock_getsize, tmp_path):
    """Tests that OSError during size retrieval is caught and ignored."""
    root_dir = tmp_path / "test_dir_error"
    root_dir.mkdir()

    # Create two dummy files
    file1 = root_dir / "file1.txt"
    file1.write_bytes(b"dummy")
    file2 = root_dir / "file2.txt"
    file2.write_bytes(b"dummy")

    # Mock getsize to raise an OSError for file1, but return 20 bytes for file2
    def side_effect(path):
        if "file1.txt" in path:
            raise OSError("File deleted during calculation")
        return 20

    mock_getsize.side_effect = side_effect

    # The function should ignore file1's OSError and return only file2's size
    assert get_sessions_dir_size(str(root_dir)) == 20
