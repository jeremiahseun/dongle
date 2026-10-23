"""
Directory Preview & Action Execution Services.
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

_PREVIEW_CACHE: Dict[str, List[Tuple[str, str]]] = {}

_README_NAMES = ("README.md", "readme.md", "README.rst", "README.txt", "README")


def _read_git_branch(target: Path) -> str:
    """Fast, zero-subprocess git branch detection by inspecting .git/HEAD."""
    curr = target
    for _ in range(5):
        head_file = curr / ".git" / "HEAD"
        if head_file.is_file():
            try:
                content = head_file.read_text(errors="ignore").strip()
                if content.startswith("ref: refs/heads/"):
                    return content[len("ref: refs/heads/"):]
                return content[:7]
            except Exception:
                return ""
        parent = curr.parent
        if parent == curr:
            break
        curr = parent
    return ""


def get_directory_preview(full_path: str, max_lines: int = 14) -> List[Tuple[str, str]]:
    """
    Generate formatted text tuples `(style_class, text)` for the preview pane.
    Results are cached in memory per picker session for zero-latency navigation.
    """
    if not full_path:
        return [("class:hint", "  No directory selected.\n")]

    if full_path in _PREVIEW_CACHE:
        return _PREVIEW_CACHE[full_path]

    p = Path(full_path)
    if not p.is_dir():
        res = [("class:no-match", "  Directory does not exist.\n")]
        _PREVIEW_CACHE[full_path] = res
        return res

    lines: List[Tuple[str, str]] = []
    used_lines = 0

    # Header: directory basename + git branch if any
    name = p.name or str(p)
    branch = _read_git_branch(p)
    lines.append(("class:preview-title", f" 📁 {name}"))
    if branch:
        lines.append(("class:preview-git", f"  ({branch})"))
    lines.append(("", "\n"))
    used_lines += 1

    # Scan immediate children using os.scandir (very fast)
    subdirs: List[str] = []
    files: List[str] = []
    readme_path: Path = None

    try:
        with os.scandir(p) as it:
            for entry in it:
                ename = entry.name
                if ename in (".git", ".DS_Store", "__pycache__", "node_modules"):
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        subdirs.append(ename)
                    else:
                        files.append(ename)
                        if readme_path is None and ename in _README_NAMES:
                            readme_path = p / ename
                except OSError:
                    continue
    except OSError:
        lines.append(("class:no-match", "  Permission denied.\n"))
        _PREVIEW_CACHE[full_path] = lines
        return lines

    subdirs.sort(key=str.lower)
    files.sort(key=str.lower)

    lines.append((
        "class:preview-meta",
        f" {len(subdirs)} dirs, {len(files)} files\n"
    ))
    used_lines += 1

    # List top subdirectories and files
    max_entries = 6 if readme_path else (max_lines - used_lines - 1)
    shown = 0
    for d in subdirs:
        if shown >= max_entries:
            break
        lines.append(("class:preview-dir", f"  ▸ {d[:28]}/\n"))
        shown += 1
        used_lines += 1

    for f in files:
        if shown >= max_entries:
            break
        lines.append(("class:preview-file", f"  • {f[:28]}\n"))
        shown += 1
        used_lines += 1

    remaining = (len(subdirs) + len(files)) - shown
    if remaining > 0 and used_lines < max_lines:
        lines.append(("class:hint", f"  … +{remaining} more\n"))
        used_lines += 1

    # Add README snippet if space permits
    if readme_path and used_lines < max_lines - 1:
        try:
            raw_lines = readme_path.read_text(errors="ignore").splitlines()
            snippet = [ln.strip() for ln in raw_lines if ln.strip() and not ln.strip().startswith("![")]
            if snippet:
                lines.append(("class:preview-meta", " ─── README ───\n"))
                used_lines += 1
                for s_ln in snippet:
                    if used_lines >= max_lines:
                        break
                    clean = s_ln.lstrip("# ").strip()[:32]
                    if clean:
                        lines.append(("class:preview-readme", f" {clean}\n"))
                        used_lines += 1
        except Exception:
            pass

    _PREVIEW_CACHE[full_path] = lines
    return lines


def clear_preview_cache() -> None:
    _PREVIEW_CACHE.clear()


# ── Action Menu Execution ──────────────────────────────────────

ACTIONS = [
    ("cd", "Navigate (cd into directory)", "Enter"),
    ("vscode", "Open in Editor (Cursor / VS Code)", "e"),
    ("finder", "Reveal in File Manager (Finder)", "o"),
    ("copy", "Copy absolute path to clipboard", "y"),
    ("pin", "Pin / Unpin bookmark", "p"),
]


def execute_action(action_id: str, full_path: str) -> Tuple[bool, str]:
    """
    Execute a non-cd action on `full_path`.
    Returns `(should_exit_picker, status_message)`.
    """
    if action_id == "vscode":
        for editor in ("cursor", "code", "zed", "subl"):
            editor_bin = shutil.which(editor)
            if editor_bin:
                subprocess.Popen(
                    [editor_bin, full_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, f"Opened in {editor}: {full_path}"
        # Fallback on macOS: check /Applications
        for app_name in ("Cursor", "Visual Studio Code"):
            app_path = f"/Applications/{app_name}.app"
            if os.path.exists(app_path):
                subprocess.Popen(
                    ["open", "-a", app_name, full_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, f"Opened in {app_name}: {full_path}"
        return False, "No supported editor (cursor/code) found in PATH"

    elif action_id == "finder":
        opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
        if shutil.which(opener):
            subprocess.Popen(
                [opener, full_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, f"Opened in file manager: {full_path}"
        return False, f"File manager command '{opener}' not found"

    elif action_id == "copy":
        try:
            if shutil.which("pbcopy"):
                p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                p.communicate(input=full_path.encode("utf-8"))
                return True, f"Copied to clipboard: {full_path}"
            elif shutil.which("xclip"):
                p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                p.communicate(input=full_path.encode("utf-8"))
                return True, f"Copied to clipboard: {full_path}"
        except Exception:
            pass
        return False, "Clipboard utility (pbcopy/xclip) not available"

    return False, ""
