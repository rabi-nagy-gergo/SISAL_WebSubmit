import zipfile
from typing import IO


def validate_excel_file_in_memory(file_obj: IO) -> tuple[bool, str]:
    """
    Performs in-memory structural validation on an uploaded Excel file.
    Checks for the ZIP magic number and basic XLSX internal structure
    without writing the file to disk.
    """
    try:
        # Magic number check
        file_obj.seek(0)
        magic_bytes = file_obj.read(4)
        if magic_bytes != b"PK\x03\x04":
            return (
                False,
                "Security check failed: File signature does not match an Excel/ZIP archive.",
            )

        # Structural smoke test
        file_obj.seek(0)
        try:
            with zipfile.ZipFile(file_obj, "r") as zf:
                namelist = zf.namelist()

                if "[Content_Types].xml" not in namelist:
                    return (
                        False,
                        "Security check failed: Missing [Content_Types].xml. Not a valid Excel file.",
                    )

                if not any(name.startswith("xl/") for name in namelist):
                    return (
                        False,
                        "Security check failed: Missing 'xl/' directory structure. Not a valid Excel file.",
                    )

        except zipfile.BadZipFile:
            return (
                False,
                "Security check failed: File is corrupted or not a valid archive.",
            )

        return True, ""

    finally:
        file_obj.seek(0)
