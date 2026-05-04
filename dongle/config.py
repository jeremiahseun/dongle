import os
from pathlib import Path

VERSION = "0.2.9"

CACHE_FILE = Path.home() / ".dongle_cache.json"
CACHE_TTL = 300  # 5 minutes

SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".cache",
    ".npm", ".yarn", "dist", "build", ".next", ".nuxt", "venv",
    ".venv", "env", ".env", ".tox", "target", "vendor", ".idea",
    ".vscode", "coverage", ".mypy_cache", ".pytest_cache",
}

ROOT_MARKERS = {
    ".git", ".svn", ".hg", "package.json", "pubspec.yaml", "pyproject.toml",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Makefile"
}

# Allow setting depth for workspace searches natively via config
def get_workspace_depth() -> int:
    try:
        return int(os.environ.get("DONGLE_WORKSPACE_DEPTH", "4"))
    except ValueError:
        return 4
