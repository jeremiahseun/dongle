"""
Frecency & Bookmarks tracking: combines visit frequency, recency, and user pins
to rank directories. Also handles pruning deleted directories.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Set

from dongle.config import FRECENCY_FILE, BOOKMARKS_FILE

_MAX_ENTRIES = 1000


def _load(file_path: Path = None) -> dict:
    target = file_path or FRECENCY_FILE
    if not target.exists():
        return {}
    try:
        return json.loads(target.read_text())
    except Exception:
        return {}


def _save(data: dict, file_path: Path = None) -> None:
    target = file_path or FRECENCY_FILE
    try:
        target.write_text(json.dumps(data))
    except Exception:
        pass


def record_visit(path: str) -> None:
    """Increment visit count and update last-visited timestamp for path."""
    data = _load()
    now = time.time()
    entry = data.get(path)
    if entry:
        entry["visits"] += 1
        entry["last_visit"] = now
    else:
        data[path] = {"visits": 1, "last_visit": now}

    # Keep only the most recently visited entries
    if len(data) > _MAX_ENTRIES:
        trimmed = sorted(data.items(), key=lambda x: x[1]["last_visit"], reverse=True)
        data = dict(trimmed[:_MAX_ENTRIES])

    _save(data)


def get_frecency_scores() -> Dict[str, int]:
    """
    Return {path: score} for all tracked directories.

    Recency weights:
      < 1 hour  → ×4
      < 1 day   → ×2
      < 1 week  → ×1
      older     → ×0.5
    """
    data = _load()
    if not data:
        return {}

    now = time.time()
    scores: Dict[str, int] = {}
    for path, info in data.items():
        visits = info.get("visits", 1)
        age = now - info.get("last_visit", 0)

        if age < 3_600:
            weight = 4.0
        elif age < 86_400:
            weight = 2.0
        elif age < 604_800:
            weight = 1.0
        else:
            weight = 0.5

        scores[path] = int(visits * weight)

    return scores


def get_recent_dirs(n: int = 10) -> List[str]:
    """Return up to n most recently visited existing directories."""
    data = _load()
    if not data:
        return []
    entries = sorted(data.items(), key=lambda x: x[1]["last_visit"], reverse=True)
    return [path for path, _ in entries[:n]]


def prune_frecency() -> int:
    """Remove non-existent directories from frecency and bookmarks. Returns count removed."""
    data = _load()
    removed = 0
    if data:
        cleaned = {p: info for p, info in data.items() if os.path.isdir(p)}
        removed += len(data) - len(cleaned)
        if len(cleaned) != len(data):
            _save(cleaned)

    bookmarks = get_bookmarks()
    if bookmarks:
        cleaned_bm = [p for p in bookmarks if os.path.isdir(p)]
        if len(cleaned_bm) != len(bookmarks):
            removed += len(bookmarks) - len(cleaned_bm)
            _save_bookmarks(cleaned_bm)

    return removed


# ── Bookmarks / Pinned Directories ─────────────────────────────

def get_bookmarks() -> List[str]:
    """Return list of bookmarked absolute directory paths."""
    if not BOOKMARKS_FILE.exists():
        return []
    try:
        data = json.loads(BOOKMARKS_FILE.read_text())
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_bookmarks(bookmarks: List[str]) -> None:
    try:
        BOOKMARKS_FILE.write_text(json.dumps(bookmarks))
    except Exception:
        pass


def toggle_bookmark(path: str) -> bool:
    """Toggle bookmark status for an absolute path. Returns True if now bookmarked."""
    abs_path = os.path.abspath(path)
    bookmarks = get_bookmarks()
    if abs_path in bookmarks:
        bookmarks.remove(abs_path)
        _save_bookmarks(bookmarks)
        return False
    else:
        bookmarks.insert(0, abs_path)
        _save_bookmarks(bookmarks)
        return True


def get_bookmark_set() -> Set[str]:
    """Return a set of bookmarked absolute paths for O(1) lookup."""
    return set(get_bookmarks())
