#!/usr/bin/env python3
"""
Dongle - Fast directory navigation with live search.
Press / at your terminal prompt to activate.
"""

import os
import sys
from typing import Optional
import json
import time
import threading
import argparse
from pathlib import Path
try:
    import pathspec
except ImportError:
    pathspec = None

import asyncio
import selectors

if sys.platform == 'darwin':
    class SelectEventLoop(asyncio.SelectorEventLoop):
        def __init__(self):
            super().__init__(selectors.SelectSelector())
    class SelectEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
        def new_event_loop(self):
            return SelectEventLoop()
    asyncio.set_event_loop_policy(SelectEventLoopPolicy())

try:
    from prompt_toolkit import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer, Float
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.layout.dimension import D
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.layout.menus import CompletionsMenu
    from prompt_toolkit.output.defaults import create_output
except ImportError:
    print("Installing dependencies...", file=sys.stderr)
    os.system(f"{sys.executable} -m pip install prompt_toolkit --quiet")
    from prompt_toolkit import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer, Float
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.layout.dimension import D
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.output.defaults import create_output

CACHE_FILE = Path.home() / ".dongle_cache.json"
CACHE_TTL = 300  # 5 minutes

# ──────────────────────────────────────────────
# Directory Scanner
# ──────────────────────────────────────────────

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

def find_project_root(start_path: str) -> str:
    """Walk upwards to find the root of the current project."""
    current = os.path.abspath(start_path)
    while True:
        try:
            entries = os.listdir(current)
            if any(marker in entries for marker in ROOT_MARKERS):
                return current
        except PermissionError:
            pass
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # If no project root found, check if user explicitly constrained search scope
    search_dir = os.environ.get("DONGLE_SEARCH_DIR")
    if search_dir:
        expanded = os.path.expanduser(search_dir)
        if os.path.isdir(expanded):
            return expanded

    return os.path.abspath(start_path)

def load_ignore_spec(root: str):
    """Load .gitignore and .dongleignore into a pathspec."""
    if pathspec is None:
        return None

    lines = []
    for ignore_file in [".gitignore", ".dongleignore"]:
        p = os.path.join(root, ignore_file)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    lines.extend(f.readlines())
            except Exception:
                pass

    if not lines:
        return None

    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, lines)


def scan_paths(root: str, max_depth: int = 6, max_dirs: int = 15000, is_workspace: bool = False) -> list[str]:
    """Walk directory tree and collect all paths.
    If is_workspace is True, it quickly scans 2 levels deep across multiple root folders.
    """
    if not is_workspace and max_depth == 6:
        home = os.path.expanduser("~")
        if os.path.abspath(root) in (home, "/"):
            max_depth = 2

    root = os.path.abspath(root)
    paths = []

    # In workspace mode, we might get a comma-separated list of roots
    roots = []
    if is_workspace:
        ws_env = os.environ.get("DONGLE_WORKSPACES", "")
        if ws_env:
            roots = [os.path.abspath(os.path.expanduser(p.strip())) for p in ws_env.split(",") if p.strip()]

    if not roots:
        roots = [root]

    spec = None
    if not is_workspace:
        spec = load_ignore_spec(root)

    def walk(current: str, depth: int, current_root: str):
        if depth > max_depth or len(paths) >= max_dirs:
            return
        try:
            entries = os.scandir(current)
        except PermissionError:
            return

        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue

            # Skip hidden and default bad dirs
            if entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue

            rel = os.path.relpath(entry.path, current_root)

            # Check pathspec
            if spec and spec.match_file(rel + "/"):
                continue

            # In workspace mode, we prepend the root basename to distinguish projects
            if is_workspace:
                display_path = os.path.join(os.path.basename(current_root), rel)
                # Store tuple of (display_path, absolute_path) for workspaces
                paths.append((display_path, entry.path))
            else:
                paths.append(rel)

            walk(entry.path, depth + 1, current_root)

    if not is_workspace:
        paths.append(".")

    for r in roots:
        if os.path.exists(r):
            # Limit depth heavily for workspace mode to avoid crawling the whole user disk
            scan_depth = 3 if is_workspace else max_depth
            walk(r, 1, r)

    return paths


def load_cache(root: str):
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        if data.get("root") != root:
            return None
        if time.time() - data.get("ts", 0) > CACHE_TTL:
            return None
        return data["paths"]
    except Exception:
        return None


def save_cache(root: str, paths: list[str]):
    try:
        CACHE_FILE.write_text(json.dumps({"root": root, "paths": paths, "ts": time.time()}))
    except Exception:
        pass


def get_paths(root: str, is_workspace: bool = False) -> list:
    # Use a different cache key for workspace mode
    cache_key = "WORKSPACE:" + root if is_workspace else root
    cached = load_cache(cache_key)
    if cached is not None:
        return cached

    sys.stderr.write("\r\033[K  \033[36m⠋\033[0m Scanning directories... ")
    sys.stderr.flush()

    paths = scan_paths(root, is_workspace=is_workspace)
    save_cache(cache_key, paths)

    sys.stderr.write("\r\033[K")
    sys.stderr.flush()
    return paths


# ──────────────────────────────────────────────
# Fuzzy Matching
# ──────────────────────────────────────────────

def fuzzy_score(query: str, path: str) -> int:
    """Score a path against a query. Higher = better match."""
    if not query:
        return 1
    q = query.lower()
    p = path.lower()

    # Exact substring
    if q in p:
        # Prefer matches at the end (filename)
        idx = p.rfind(q)
        return 1000 - idx

    # All chars present in order
    qi = 0
    score = 0
    bonus = 0
    for ci, ch in enumerate(p):
        if qi < len(q) and ch == q[qi]:
            bonus += 10 if ci > 0 and p[ci-1] in "/_ -." else 1
            score += bonus
            qi += 1
        else:
            bonus = 0
    if qi == len(q):
        return score
    return -1  # no match


def search(query: str, paths: list[str], limit: int = 12, root: str = "", cwd: str = "") -> list[tuple[int, str]]:
    """Return scored, sorted results. Paths inside cwd get a massive boost."""
    results = []

    cwd_prefix = ""
    if cwd and root and cwd.startswith(root):
        rel = os.path.relpath(cwd, root)
        if rel and rel != ".":
            cwd_prefix = rel + os.sep

    abs_cwd = cwd + os.sep if cwd else ""

    for r in paths:
        # Check if r is a tuple/list from workspace mode (display_path, absolute_path)
        if isinstance(r, (tuple, list)):
            display_path, abs_path = r
            search_str = display_path
            is_inside_cwd = abs_path.startswith(abs_cwd) if abs_cwd else False
        else:
            search_str = r
            is_inside_cwd = search_str.startswith(cwd_prefix) if cwd_prefix else False

        s = fuzzy_score(query, search_str)
        if s > 0:
            if is_inside_cwd:
                s += 100000
            results.append((s, r))
    results.sort(key=lambda x: -x[0])
    return results[:limit]

VERSION = "0.2.8"

def check_for_updates():
    """Check GitHub for a newer release. Returns True if update available."""
    try:
        import urllib.request
        url = "https://api.github.com/repos/jeremiahseun/dongle/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "Dongle"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            data = json.loads(response.read().decode())
            latest = data.get("tag_name", "").lstrip("v")
            local_v = tuple(int(x) for x in VERSION.split(".") if x.isdigit())
            remote_v = tuple(int(x) for x in latest.split(".") if x.isdigit())
            if remote_v > local_v:
                return True
    except Exception:
        pass
    return False


# ──────────────────────────────────────────────
# TUI Application
# ──────────────────────────────────────────────

def run_picker(root: str, paths: Optional[list[str]], is_workspace: bool = False, cwd: str = "") -> Optional[str]:
    """Show interactive search UI. Returns selected path or None."""
    is_scanning = [paths is None]
    paths = paths or []

    selected = [None]
    max_results = 8
    results = [paths[:max_results] if paths else []]
    cursor = [0]

    kb = KeyBindings()

    @kb.add("enter")
    def accept(event):
        if results[0]:
            selected[0] = results[0][cursor[0]]
        event.app.exit()

    @kb.add("escape")
    @kb.add("c-c")
    @kb.add("c-g")
    def cancel(event):
        event.app.exit()

    @kb.add("up")
    @kb.add("c-p")
    def move_up(event):
        if cursor[0] > 0:
            cursor[0] -= 1
        refresh_results(search_buf.text)

    @kb.add("down")
    @kb.add("c-n")
    def move_down(event):
        if cursor[0] < len(results[0]) - 1:
            cursor[0] += 1
        refresh_results(search_buf.text)

    @kb.add("tab")
    def move_down_tab(event):
        if cursor[0] < len(results[0]) - 1:
            cursor[0] += 1
        refresh_results(search_buf.text)

    @kb.add("s-tab")
    def move_up_stab(event):
        if cursor[0] > 0:
            cursor[0] -= 1
        refresh_results(search_buf.text)

    def refresh_results(text):
        if text:
            scored = search(text, paths, limit=max_results, root=root, cwd=cwd)
            results[0] = [p for _, p in scored]
        else:
            results[0] = paths[:max_results]
        cursor[0] = min(cursor[0], max(0, len(results[0]) - 1))
        result_control.text = render_results

    def on_text_change(buf):
        cursor[0] = 0
        refresh_results(buf.text)

    def render_results():
        lines = []
        for i, item in enumerate(results[0]):
            is_selected = i == cursor[0]

            # Extract paths correctly depending on workspace mode tuple/list
            if isinstance(item, (tuple, list)):
                path, _ = item
            else:
                path = item

            parts = path.split(os.sep)
            # highlight last segment
            if len(parts) > 1:
                prefix = os.sep.join(parts[:-1]) + os.sep
                last = parts[-1]
            else:
                prefix = ""
                last = path

            if is_selected:
                lines.append(("class:selected", f"  ❯ {prefix}"))
                lines.append(("class:selected-highlight", f"{last}\n"))
            else:
                lines.append(("class:path-prefix", f"    {prefix}"))
                lines.append(("class:path-name", f"{last}\n"))

        if not results[0]:
            if is_scanning[0]:
                lines.append(("class:no-results", f"  Scanning {root} ...\n"))
            else:
                lines.append(("class:no-results", "  No results found\n"))
            drawn = 1
        else:
            drawn = len(results[0])

        # Pad so the window NEVER shrinks/jumps — always exactly max_results lines
        for _ in range(max_results - drawn):
            lines.append(("", "\n"))

        return lines

    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()

    has_update = [False]
    def bg_update_check():
        if check_for_updates():
            has_update[0] = True
            try:
                loop.call_soon_threadsafe(lambda: app.invalidate())
            except Exception:
                pass

    threading.Thread(target=bg_update_check, daemon=True).start()

    def bg_scan():
        cache_key = "WORKSPACE:" + root if is_workspace else root
        new_paths = scan_paths(root, is_workspace=is_workspace)
        save_cache(cache_key, new_paths)
        paths.clear()
        paths.extend(new_paths)
        is_scanning[0] = False

        # Thread-safe UI update
        def update_ui():
            refresh_results(search_buf.text)
            app.invalidate()

        loop.call_soon_threadsafe(update_ui)

    search_buf = Buffer(name="search", on_text_changed=lambda buf: on_text_change(buf))
    result_control = FormattedTextControl(text=render_results, focusable=False)

    root_display = root.replace(str(Path.home()), "~")
    def get_header():
        update_text = '  <style fg="#ffaa00">🚀 Update available: run `dongle update`</style>' if has_update[0] else ''
        return HTML(
            f'<b style="color: #5f87ff">  Dongle</b>'
            f'<style fg="#666">  in {root_display}</style>{update_text}\n'
            f'<style fg="#444">  ↑↓ navigate  Enter select  Esc cancel</style>'
        )

    header = FormattedTextControl(text=get_header)

    search_prompt = FormattedTextControl(HTML('<b style="color: #5fff87">  / </b>'))

    layout = Layout(
        HSplit([
            Window(content=header, height=2),
            Window(height=1, char=" "),  # padding between header and search
            VSplit([
                Window(content=search_prompt, width=4, height=1),
                Window(content=BufferControl(buffer=search_buf), height=1),
            ]),
            Window(height=1, char="─", style="class:divider"),
            Window(content=result_control, height=max_results + 1, wrap_lines=False),
        ])
    )

    style = Style.from_dict({
        "selected":           "bg:#1e3a5f #ffffff bold",
        "selected-highlight": "bg:#1e3a5f #5fff87 bold",
        "path-prefix":        "#555555",
        "path-name":          "#ffffff",
        "no-results":         "#ff5555 italic",
        "divider":            "#333333",
    })

    # Open /dev/tty directly so the picker works inside $() command substitution
    # where stdin/stdout are redirected away from the terminal
    tty_fd = os.open('/dev/tty', os.O_RDWR)
    tty_file_in = os.fdopen(tty_fd, 'rt', encoding='utf-8', closefd=False)
    tty_file_out = os.fdopen(tty_fd, 'wt', encoding='utf-8', closefd=False)

    from prompt_toolkit.input.vt100 import Vt100Input
    from prompt_toolkit.output.vt100 import Vt100_Output

    import shutil
    from prompt_toolkit.data_structures import Size
    def get_size() -> Size:
        sz = shutil.get_terminal_size((80, 24))
        return Size(rows=sz.lines, columns=sz.columns)

    tty_input = Vt100Input(tty_file_in)
    tty_output = Vt100_Output(tty_file_out, get_size)

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
        color_depth=None,
        input=tty_input,
        output=tty_output,
    )

    if is_scanning[0]:
        threading.Thread(target=bg_scan, daemon=True).start()

    try:
        app.run()
    finally:
        tty_file_in.close()
        tty_file_out.close()
        os.close(tty_fd)

    return selected[0]


# ──────────────────────────────────────────────
# Entry Points
# ──────────────────────────────────────────────

def cmd_pick():
    """Interactive picker — prints chosen path to stdout."""
    parser = argparse.ArgumentParser(description="Dongle interactive picker")
    parser.add_argument("root", nargs="?", default=None, help="Root directory to search")
    parser.add_argument("--rescan", action="store_true", help="Force rescan ignoring cache")
    parser.add_argument("--workspace", action="store_true", help="Search across all workspaces")
    args = parser.parse_args()

    # If no explicit root given, try to find the project root upwards!
    if args.root is None:
        root = find_project_root(os.getcwd())
    else:
        root = os.path.abspath(args.root)

    cache_key = "WORKSPACE:" + root if args.workspace else root
    if args.rescan:
        paths = None
    else:
        paths = load_cache(cache_key)

    chosen = run_picker(root, paths, is_workspace=args.workspace, cwd=os.getcwd())
    if chosen:
        # If workspace mode, chosen is a tuple/list (display_path, absolute_path)
        if isinstance(chosen, (tuple, list)):
            print(chosen[1])
        else:
            full = os.path.join(root, chosen) if chosen != "." else root
            print(full)
    else:
        sys.exit(1)


def cmd_scan():
    """Pre-scan and cache paths for a directory."""
    parser = argparse.ArgumentParser(description="Dongle scanner")
    parser.add_argument("root", nargs="?", default=None)
    parser.add_argument("--workspace", action="store_true", help="Scan across all workspaces")
    args = parser.parse_args()

    if args.root is None:
        root = find_project_root(os.getcwd())
    else:
        root = os.path.abspath(args.root)

    cache_file = CACHE_FILE if not args.workspace else Path.home() / ".dongle_workspace_cache.json"
    if cache_file.exists():
        cache_file.unlink()

    sys.stderr.write(f"Scanning {'workspaces' if args.workspace else root}...\n")
    paths = scan_paths(root, is_workspace=args.workspace)
    cache_key = "WORKSPACE:" + root if args.workspace else root
    save_cache(cache_key, paths)
    sys.stderr.write(f"Cached {len(paths)} paths\n")


def cmd_list():
    """List cached paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=os.getcwd())
    args = parser.parse_args()
    root = os.path.abspath(args.root)
    paths = get_paths(root)
    for p in paths:
        print(p)


if __name__ == "__main__":
    cmd_pick()
