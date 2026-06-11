import os
import pytest
from src.services.api_utils import parse_qc_log_to_json, get_session_paths, SESSIONS_DIR

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
    assert len(result["informative_messages"]) == 0
    assert len(result["warnings"]) == 0

def test_parse_qc_log_informative_only():
    """Tests that a log with only Informative messages passes the validation."""
    raw_log = '{"priority": "Informative", "description": "All checks passed", "script_location": "A", "workbook_location": "B"}'
    result = parse_qc_log_to_json(raw_log)
    
    assert result["total_warnings"] == 0
    assert result["total_errors"] == 0
    assert result["total_fatal"] == 0
    assert result["is_passed"] is True
    assert len(result["informative_messages"]) == 1
    assert result["informative_messages"][0]["description"] == "All checks passed"
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
    
    # Validation should fail if there are any warnings, errors, or fatals
    assert result["is_passed"] is False
    
    # 1 Informative message expected
    assert len(result["informative_messages"]) == 1
    
    # The 'warnings' list acts as a catch-all for anything not Informative
    assert len(result["warnings"]) == 3

def test_parse_qc_log_invalid_json_fallback():
    """Tests handling of invalid JSON lines by treating them as Warnings."""
    raw_log = "This is an unexpected plain text error line."
    result = parse_qc_log_to_json(raw_log)
    
    assert result["total_warnings"] == 1
    assert result["total_errors"] == 0
    assert result["is_passed"] is False
    
    assert len(result["warnings"]) == 1
    fallback_warning = result["warnings"][0]
    assert fallback_warning["priority"] == "Warning"
    assert fallback_warning["description"] == "This is an unexpected plain text error line."

def test_parse_qc_log_empty_lines_ignored():
    """Tests that empty lines or whitespaces are properly skipped by the parser."""
    raw_log = "\n\n" + '{"priority": "Informative", "description": "Test"}' + "\n   \n"
    result = parse_qc_log_to_json(raw_log)
    
    assert len(result["informative_messages"]) == 1
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