import os
import json
import time
from pathlib import Path
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from dongle.config import SKIP_DIRS, ROOT_MARKERS, CACHE_FILE, get_workspace_depth

def find_project_root(start_dir: str) -> str:
    """Find the project root by looking upwards for markers."""
    curr = Path(start_dir).resolve()
    for parent in [curr] + list(curr.parents):
        if any((parent / marker).exists() for marker in ROOT_MARKERS):
            return str(parent)
    return str(curr)

def load_ignore_spec(root: str) -> PathSpec:
    """Load .gitignore and .dongleignore patterns."""
    patterns = []
    for filename in [".gitignore", ".dongleignore"]:
        p = Path(root) / filename
        if p.exists():
            patterns.extend(p.read_text().splitlines())
    return PathSpec.from_lines(GitWildMatchPattern, patterns)

def scan_paths(root: str, is_workspace: bool = False) -> list:
    """Recursively scan a directory for subdirectories, respecting ignores."""
    paths = []
    root_path = Path(root)
    
    if is_workspace:
        # Feature 2: Expand workspace depth
        # Workspace mode: Scan multiple directories from DONGLE_WORKSPACES
        workspace_raw = os.environ.get("DONGLE_WORKSPACES", "")
        workspace_dirs = [os.path.expanduser(d.strip()) for d in workspace_raw.split(",") if d.strip()]
        
        max_depth = get_workspace_depth()
        
        for ws_dir in workspace_dirs:
            ws_path = Path(ws_dir)
            if not ws_path.exists(): continue
            
            for curr_root, dirs, files in os.walk(ws_path, topdown=True):
                # Filter out skip dirs
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                
                rel_root = Path(curr_root).relative_to(ws_path.parent)
                
                # Only add if not too deep
                depth = len(Path(curr_root).relative_to(ws_path).parts)
                if depth <= max_depth:
                    paths.append((str(rel_root), curr_root))
                else:
                    dirs[:] = []  # Don't recurse deeper
    else:
        # Local mode: Scan from a single root
        ignore_spec = load_ignore_spec(root)
        
        for curr_root, dirs, files in os.walk(root_path, topdown=True):
            # Filter out skip dirs
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            
            # Apply ignore patterns
            rel_root = Path(curr_root).relative_to(root_path)
            if rel_root != Path("."):
                if ignore_spec.match_file(str(rel_root)):
                    dirs[:] = []
                    continue
                paths.append(str(rel_root))
            else:
                paths.append(".")
                
    return paths

def load_cache(cache_key: str, cache_file: Path = CACHE_FILE) -> list:
    """Load cached paths if they are not expired."""
    if not cache_file.exists():
        return None
        
    try:
        data = json.loads(cache_file.read_text())
        if cache_key in data:
            entry = data[cache_key]
            # Check TTL
            if time.time() - entry["timestamp"] < 300:
                return entry["paths"]
    except:
        pass
    return None

def save_cache(cache_key: str, paths: list, cache_file: Path = CACHE_FILE):
    """Save paths to cache."""
    data = {}
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
        except:
            pass
            
    data[cache_key] = {
        "timestamp": time.time(),
        "paths": paths
    }
    
    cache_file.write_text(json.dumps(data))

def get_paths(root: str) -> list:
    """High-level helper to get paths (with caching)."""
    cache_key = root
    paths = load_cache(cache_key)
    if paths is None:
        paths = scan_paths(root)
        save_cache(cache_key, paths)
    return paths
