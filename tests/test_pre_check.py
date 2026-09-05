import io
import zipfile

from src.services.wb_pre_check import validate_excel_file_in_memory


def create_dummy_zip(files_to_add: dict) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for filename, content in files_to_add.items():
            zf.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer


def test_validate_excel_valid():
    file_obj = create_dummy_zip(
        {"[Content_Types].xml": b"dummy_content", "xl/workbook.xml": b"dummy_content"}
    )
    is_valid, msg = validate_excel_file_in_memory(file_obj)

    assert is_valid is True
    assert msg == ""


def test_validate_excel_invalid_magic_bytes():
    file_obj = io.BytesIO(b"This is just a plain text file, not a zip archive.")
    is_valid, msg = validate_excel_file_in_memory(file_obj)

    assert is_valid is False
    assert "File signature does not match" in msg


def test_validate_excel_missing_content_types():
    file_obj = create_dummy_zip({"xl/workbook.xml": b"dummy_content"})
    is_valid, msg = validate_excel_file_in_memory(file_obj)

    assert is_valid is False
    assert "Missing [Content_Types].xml" in msg


def test_validate_excel_missing_xl_dir():
    file_obj = create_dummy_zip({"[Content_Types].xml": b"dummy_content"})
    is_valid, msg = validate_excel_file_in_memory(file_obj)

    assert is_valid is False
    assert "Missing 'xl/' directory structure" in msg


def test_validate_excel_bad_zip_file():
    file_obj = io.BytesIO(b"PK\x03\x04" + b"some_corrupted_garbage_data_here")
    is_valid, msg = validate_excel_file_in_memory(file_obj)

    assert is_valid is False
    assert "File is corrupted or not a valid archive" in msg
