import os
from pathlib import Path

VERSION = "0.3.0"

CACHE_FILE = Path.home() / ".dongle_cache.json"
FRECENCY_FILE = Path.home() / ".dongle_frecency.json"

SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".cache",
    ".npm", ".yarn", "dist", "build", ".next", ".nuxt", "venv",
    ".venv", "env", ".env", ".tox", "target", "vendor", ".idea",
    ".vscode", "coverage", ".mypy_cache", ".pytest_cache",
}

ROOT_MARKERS = {
    ".git", ".svn", ".hg", "package.json", "pubspec.yaml", "pyproject.toml",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Makefile",
}

# Extra dirs to skip, user-configurable
_extra = os.environ.get("DONGLE_SKIP_DIRS", "")
if _extra:
    SKIP_DIRS |= {d.strip() for d in _extra.split(",") if d.strip()}


def get_cache_ttl() -> int:
    try:
        return int(os.environ.get("DONGLE_CACHE_TTL", "300"))
    except ValueError:
        return 300


def get_max_depth() -> int:
    try:
        return int(os.environ.get("DONGLE_MAX_DEPTH", "6"))
    except ValueError:
        return 6


def get_workspace_depth() -> int:
    try:
        return int(os.environ.get("DONGLE_WORKSPACE_DEPTH", "4"))
    except ValueError:
        return 4


def get_max_dirs() -> int:
    try:
        return int(os.environ.get("DONGLE_MAX_DIRS", "5000"))
    except ValueError:
        return 5000
