import re
from datetime import datetime


def extract_tags(text: str) -> list:
    tags = re.findall(r"@(\w+)", text)
    return list(dict.fromkeys(tags))  # deduplicated, order preserved


def word_count(text: str) -> int:
    return len(text.split()) if text.strip() else 0


def make_entry_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso


def preview(text: str, length: int = 60) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    first = lines[0] if lines else ""
    return first[:length] + ("..." if len(first) > length else "")
