import os
import json
import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

from dongle.config import (
    SKIP_DIRS,
    ROOT_MARKERS,
    CACHE_FILE,
    WORKSPACE_CACHE_FILE,
    get_cache_ttl,
    get_workspace_depth,
    get_max_depth,
    get_max_dirs,
)


def find_project_root(start_dir: str) -> str:
    """Walk upward until a project root marker is found."""
    curr = Path(start_dir).resolve()
    for parent in [curr] + list(curr.parents):
        if any((parent / m).exists() for m in ROOT_MARKERS):
            return str(parent)
    fallback = os.environ.get("DONGLE_SEARCH_DIR", "").strip()
    if fallback:
        expanded = os.path.expanduser(fallback)
        if os.path.isdir(expanded):
            return os.path.abspath(expanded)
    return str(curr)


def get_workspace_cache_key() -> str:
    """Build a deterministic cache key for the configured workspace directories."""
    raw = os.environ.get("DONGLE_WORKSPACES", "").strip()
    if not raw:
        raw = os.environ.get("DONGLE_SEARCH_DIR", "").strip()
    dirs = [os.path.abspath(os.path.expanduser(d.strip())) for d in raw.split(",") if d.strip()]
    return "WORKSPACE:" + "|".join(dirs)


def load_ignore_spec(root: str):
    """Load .gitignore and .dongleignore patterns. pathspec is imported lazily."""
    from pathspec import PathSpec
    from pathspec.patterns import GitWildMatchPattern

    patterns = []
    for filename in (".gitignore", ".dongleignore"):
        p = Path(root) / filename
        if p.exists():
            try:
                patterns.extend(p.read_text(errors="ignore").splitlines())
            except Exception:
                pass
    return PathSpec.from_lines(GitWildMatchPattern, patterns)


def scan_paths(root: str, is_workspace: bool = False) -> list:
    """Recursively scan for subdirectories, respecting ignore rules and limits."""
    paths = []
    max_dirs = get_max_dirs()

    if is_workspace:
        workspace_raw = os.environ.get("DONGLE_WORKSPACES", "").strip()
        if not workspace_raw:
            workspace_raw = os.environ.get("DONGLE_SEARCH_DIR", "").strip()
        workspace_dirs = [os.path.expanduser(d.strip()) for d in workspace_raw.split(",") if d.strip()]
        if not workspace_dirs:
            # Fallback to parent of current project root so workspace search is still useful out of the box
            workspace_dirs = [str(Path(root).parent)]
        max_depth = get_workspace_depth()

        for ws_dir in workspace_dirs:
            ws_path = Path(ws_dir).resolve()
            if not ws_path.exists():
                continue

            # Optimized: Convert once to strings outside the hot loop
            ws_parent_str = str(ws_path.parent)
            ws_str = str(ws_path)

            for curr_root, dirs, _files in os.walk(ws_path, topdown=True):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

                # Optimized: os.path.relpath is ~3x faster than pathlib.Path().relative_to() in hot loops
                rel_to_ws = os.path.relpath(curr_root, ws_str)

                if rel_to_ws == ".":
                    depth = 0
                else:
                    depth = rel_to_ws.count(os.sep) + 1

                if depth <= max_depth:
                    rel_root_str = os.path.relpath(curr_root, ws_parent_str)
                    paths.append((rel_root_str, curr_root))
                    if len(paths) >= max_dirs:
                        return paths
                else:
                    dirs[:] = []
    else:
        ignore_spec = load_ignore_spec(root)
        root_path = Path(root).resolve()
        is_home = (root_path == Path.home().resolve())
        max_depth = min(get_max_depth(), 3) if is_home else get_max_depth()
        root_str = str(root_path)

        for curr_root, dirs, _files in os.walk(root_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

            # Optimized: os.path.relpath is ~3x faster than pathlib.Path().relative_to() in hot loops
            rel_str = os.path.relpath(curr_root, root_str)

            # Stop recursing past max depth
            if rel_str == ".":
                depth = 0
            else:
                depth = rel_str.count(os.sep) + 1

            if depth > max_depth:
                dirs[:] = []
                continue

            if rel_str == ".":
                paths.append(".")
            else:
                if not ignore_spec.match_file(rel_str):
                    paths.append(rel_str)
                else:
                    dirs[:] = []
                    continue

            if len(paths) >= max_dirs:
                return paths

    return paths


def load_cache(cache_key: str, cache_file: Path = CACHE_FILE) -> Optional[list]:
    """Return cached paths if they exist and are within the TTL."""
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text())
        entry = data.get(cache_key)
        if entry and time.time() - entry["timestamp"] < get_cache_ttl():
            return entry["paths"]
    except Exception:
        pass
    return None


def save_cache(cache_key: str, paths: list, cache_file: Path = CACHE_FILE) -> None:
    """Persist paths to the cache file."""
    data = {}
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
        except Exception:
            pass
    data[cache_key] = {"timestamp": time.time(), "paths": paths}
    try:
        cache_file.write_text(json.dumps(data))
    except Exception:
        pass


def get_paths(root: str, is_workspace: bool = False) -> list:
    """Return paths for root, using cache when available."""
    cache_key = get_workspace_cache_key() if is_workspace else root
    cache_file = WORKSPACE_CACHE_FILE if is_workspace else CACHE_FILE
    paths = load_cache(cache_key, cache_file)
    if paths is None:
        paths = scan_paths(root, is_workspace=is_workspace)
        save_cache(cache_key, paths, cache_file)
    return paths
