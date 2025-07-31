from pathlib import Path
from typing import Optional, Dict

from app.utils.filename_parser import parse_filename as parse_filename_advanced, FilenameInfo


def parse_filename(filename: str) -> Optional[Dict[str, str]]:
    """Parse a filename using the advanced parser and convert to dict format.

    Uses the unified parser from filename_parser.py for consistency.
    """
    result = parse_filename_advanced(filename)
    if result is None:
        return None

    return {
        "principal": result.principal,
        "agent": result.agent,
        "doctype": result.doctype,
        "number": result.number,
        "date": result.date,
    }


def get_drive_path(filename: str) -> list[str]:
    """Return hierarchical path segments based on filename.
    Pattern: <principal>/<principal>_<agent>/<doctype>_<number>_<date>.
    If parsing fails → ["unsorted"]."""
    info = parse_filename(filename)
    if info is None:
        return ["unsorted"]

    return [
        info["principal"],
        f"{info['principal']}_{info['agent']}",
        f"{info['doctype']}_{info['number']}_{info['date']}",
    ]


def determine_path(filename: str) -> str:
    """Return full relative path (with '/'). Falls back to stem if unparsable."""
    info = parse_filename(filename)
    if info is None:
        return f"unsorted/{Path(filename).stem}"

    return f"{info['principal']}/{info['principal']}_{info['agent']}/{info['doctype']}_{info['number']}_{info['date']}"
