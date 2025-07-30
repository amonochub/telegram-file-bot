from pathlib import Path
import re
from typing import Optional, Dict


# Helper to parse filenames with pattern:
# <principal>_<agent>_<doctype parts>_<number>_<date>.<ext>
def parse_filename(filename: str) -> Optional[Dict[str, str]]:
    """Parse a filename of the pattern
    <principal>_<agent>_<doctype parts>_<number>_<date>.<ext>
    and return a dict with keys principal, agent, doctype, number, date.
    Returns None if pattern is not satisfied.
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    # Need at least 5 parts: principal, agent, doctype (≥1 part), number, date
    if len(parts) < 5:
        return None

    principal = parts[0]
    agent = parts[1]
    # doc_type may consist of several parts (keep original case/spaces with join)
    number = parts[-2]
    date = parts[-1]
    doctype_parts = parts[2:-2]
    doctype = " ".join(doctype_parts)

    # simple validations: number is digit-like, date has 6 or 8 digits
    if not number.isdigit():
        return None
    if not re.fullmatch(r"\d{6}|\d{8}", date):
        return None

    return {
        "principal": principal,
        "agent": agent,
        "doctype": doctype.lower(),  # normalize to lower-case for path
        "number": number,
        "date": date,
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
