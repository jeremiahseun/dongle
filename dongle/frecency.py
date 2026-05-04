"""
Frecency tracking: combines visit frequency and recency to rank directories.
Inspired by Mozilla's frecency algorithm and the `z` shell tool.
"""
import json
import time
from pathlib import Path

from dongle.config import FRECENCY_FILE

_MAX_ENTRIES = 1000


def _load() -> dict:
    if not FRECENCY_FILE.exists():
        return {}
    try:
        return json.loads(FRECENCY_FILE.read_text())
    except Exception:
        return {}


def _save(data: dict):
    try:
        FRECENCY_FILE.write_text(json.dumps(data))
    except Exception:
        pass


def record_visit(path: str):
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


def get_frecency_scores() -> dict:
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
    scores = {}
    for path, info in data.items():
        visits = info.get("visits", 1)
        age = now - info.get("last_visit", 0)

        if age < 3_600:
            weight = 4
        elif age < 86_400:
            weight = 2
        elif age < 604_800:
            weight = 1
        else:
            weight = 0.5

        scores[path] = int(visits * weight)

    return scores


def get_recent_dirs(n: int = 10) -> list:
    """Return up to n most recently visited directories."""
    data = _load()
    if not data:
        return []
    entries = sorted(data.items(), key=lambda x: x[1]["last_visit"], reverse=True)
    return [path for path, _ in entries[:n]]
