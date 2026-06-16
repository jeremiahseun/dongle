import os
import json
import time
from pathlib import Path

from dongle.config import SKIP_DIRS, ROOT_MARKERS, CACHE_FILE, get_cache_ttl, get_workspace_depth, get_max_depth, get_max_dirs


def find_project_root(start_dir: str) -> str:
    """Walk upward until a project root marker is found."""
    curr = Path(start_dir).resolve()
    for parent in [curr] + list(curr.parents):
        if any((parent / m).exists() for m in ROOT_MARKERS):
            return str(parent)
    return str(curr)


def load_ignore_spec(root: str):
    """Load .gitignore and .dongleignore patterns. pathspec is imported lazily."""
    from pathspec import PathSpec
    from pathspec.patterns import GitWildMatchPattern

    patterns = []
    for filename in (".gitignore", ".dongleignore"):
        p = Path(root) / filename
        if p.exists():
            patterns.extend(p.read_text().splitlines())
    return PathSpec.from_lines(GitWildMatchPattern, patterns)


def scan_paths(root: str, is_workspace: bool = False) -> list:
    """Recursively scan for subdirectories, respecting ignore rules and limits."""
    paths = []
    max_dirs = get_max_dirs()

    if is_workspace:
        workspace_raw = os.environ.get("DONGLE_WORKSPACES", "")
        workspace_dirs = [os.path.expanduser(d.strip()) for d in workspace_raw.split(",") if d.strip()]
        max_depth = get_workspace_depth()

        for ws_dir in workspace_dirs:
            ws_path = Path(ws_dir)
            if not ws_path.exists():
                continue

            # String slicing optimization for Path.relative_to
            ws_str = os.path.normpath(str(ws_path))
            ws_len = len(ws_str) + (1 if not ws_str.endswith(os.sep) else 0)
            dirname = os.path.dirname(ws_str)
            if not dirname:
                ws_parent_len = 0
            else:
                ws_parent_len = len(dirname) + (1 if not dirname.endswith(os.sep) else 0)

            for curr_root, dirs, _files in os.walk(ws_str, topdown=True):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

                # Fast relative path calculation
                if ws_parent_len == 0:
                    rel_root_str = "." if curr_root == "." else curr_root
                else:
                    rel_root_str = curr_root[ws_parent_len:]

                depth = 0 if curr_root == ws_str else curr_root[ws_len:].count(os.sep) + 1

                if depth <= max_depth:
                    paths.append((rel_root_str, curr_root))
                    if len(paths) >= max_dirs:
                        return paths
                else:
                    dirs[:] = []
    else:
        ignore_spec = load_ignore_spec(root)
        root_path = Path(root)
        max_depth = get_max_depth()

        # String slicing optimization for Path.relative_to
        root_str = os.path.normpath(str(root_path))
        root_len = len(root_str) + (1 if not root_str.endswith(os.sep) else 0)

        for curr_root, dirs, _files in os.walk(root_str, topdown=True):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            # Fast relative path calculation
            if curr_root == root_str:
                rel_str = "."
                depth = 0
            else:
                rel_str = curr_root[root_len:]
                depth = rel_str.count(os.sep) + 1

            # Stop recursing past max depth
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


def load_cache(cache_key: str, cache_file: Path = CACHE_FILE) -> list:
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


def save_cache(cache_key: str, paths: list, cache_file: Path = CACHE_FILE):
    """Persist paths to the cache file."""
    data = {}
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
        except Exception:
            pass
    data[cache_key] = {"timestamp": time.time(), "paths": paths}
    cache_file.write_text(json.dumps(data))


def get_paths(root: str) -> list:
    """Return paths for root, using cache when available."""
    paths = load_cache(root)
    if paths is None:
        paths = scan_paths(root)
        save_cache(root, paths)
    return paths
