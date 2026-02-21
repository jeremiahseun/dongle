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

def scan_paths(root: str, max_depth: int = 6, max_dirs: int = 5000) -> list[str]:
    """Walk directory tree and collect all paths."""
    root = os.path.abspath(root)
    paths = []

    def walk(current: str, depth: int):
        if depth > max_depth or len(paths) >= max_dirs:
            return
        try:
            entries = os.scandir(current)
        except PermissionError:
            return
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            if entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue
            rel = os.path.relpath(entry.path, root)
            paths.append(rel)
            walk(entry.path, depth + 1)

    paths.append(".")
    walk(root, 1)
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


def get_paths(root: str) -> list[str]:
    cached = load_cache(root)
    if cached is not None:
        return cached

    sys.stderr.write("\r\033[K  \033[36m⠋\033[0m Scanning directories... ")
    sys.stderr.flush()

    paths = scan_paths(root)
    save_cache(root, paths)

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


def search(query: str, paths: list[str], limit: int = 12) -> list[tuple[int, str]]:
    """Return scored, sorted results."""
    results = []
    for p in paths:
        s = fuzzy_score(query, p)
        if s > 0:
            results.append((s, p))
    results.sort(key=lambda x: -x[0])
    return results[:limit]


# ──────────────────────────────────────────────
# TUI Application
# ──────────────────────────────────────────────

def run_picker(root: str, paths: list[str]) -> Optional[str]:
    """Show interactive search UI. Returns selected path or None."""
    selected = [None]
    results = [paths[:12]]
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
            scored = search(text, paths)
            results[0] = [p for _, p in scored]
        else:
            results[0] = paths[:12]
        cursor[0] = min(cursor[0], max(0, len(results[0]) - 1))
        result_control.text = render_results

    def on_text_change(buf):
        cursor[0] = 0
        refresh_results(buf.text)

    def render_results():
        lines = []
        for i, path in enumerate(results[0]):
            is_selected = i == cursor[0]
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
            lines.append(("class:no-results", "  No results found\n"))
        return lines

    search_buf = Buffer(name="search", on_text_changed=lambda buf: on_text_change(buf))
    result_control = FormattedTextControl(text=render_results, focusable=False)

    root_display = root.replace(str(Path.home()), "~")
    header = FormattedTextControl(HTML(
        f'<b style="color: #5f87ff">  Dongle</b>'
        f'<style fg="#666">  in {root_display}</style>\n'
        f'<style fg="#444">  ↑↓ navigate  Enter select  Esc cancel</style>'
    ))

    search_prompt = FormattedTextControl(HTML('<b style="color: #5fff87">  / </b>'))

    layout = Layout(
        HSplit([
            Window(content=header, height=2),
            VSplit([
                Window(content=search_prompt, width=4, height=1),
                Window(content=BufferControl(buffer=search_buf), height=1),
            ]),
            Window(height=1, char="─", style="class:divider"),
            Window(content=result_control, height=14),
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
    parser.add_argument("root", nargs="?", default=os.getcwd(), help="Root directory to search")
    parser.add_argument("--rescan", action="store_true", help="Force rescan ignoring cache")
    args = parser.parse_args()

    root = os.path.abspath(args.root)

    if args.rescan and CACHE_FILE.exists():
        CACHE_FILE.unlink()

    # Background scan indicator
    sys.stderr.write("\033[?25l")  # hide cursor briefly
    paths = get_paths(root)
    sys.stderr.write("\033[?25h")  # restore cursor

    chosen = run_picker(root, paths)
    if chosen:
        full = os.path.join(root, chosen) if chosen != "." else root
        print(full)
    else:
        sys.exit(1)


def cmd_scan():
    """Pre-scan and cache paths for a directory."""
    parser = argparse.ArgumentParser(description="Dongle scanner")
    parser.add_argument("root", nargs="?", default=os.getcwd())
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()

    sys.stderr.write(f"Scanning {root}...\n")
    paths = scan_paths(root)
    save_cache(root, paths)
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
