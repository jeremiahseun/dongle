import sys
import os
import shutil
import subprocess
from pathlib import Path

# Only lightweight import at module level — init/version need nothing heavy
from dongle.config import VERSION, CACHE_FILE, WORKSPACE_CACHE_FILE

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def _get_shell_dir() -> Path:
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "dongle" / "shell"
    return Path(__file__).parent.resolve() / "shell"


def _read_shell_script(shell: str) -> str:
    shell_dir = _get_shell_dir()
    filenames = {"bash": "bash.sh", "zsh": "zsh.sh", "fish": "fish.fish"}
    if shell not in filenames:
        print(f"Unknown shell: {shell}. Supported: bash, zsh, fish", file=sys.stderr)
        sys.exit(1)
    script_path = shell_dir / filenames[shell]
    if not script_path.exists():
        print(f"Shell script not found: {script_path}", file=sys.stderr)
        sys.exit(1)
    return script_path.read_text()


def _find_pick_binary() -> Path:
    """Locate co-installed dongle-pick binary for both --onefile and --onedir bundles."""
    exe_dir = Path(sys.executable).resolve().parent
    candidates = [
        exe_dir / "dongle-pick",
        exe_dir.parent / "dongle-pick" / "dongle-pick",
        Path.home() / ".dongle" / "bin" / "dongle-pick",
        Path.home() / ".dongle" / "lib" / "dongle-pick" / "dongle-pick",
    ]
    for cand in candidates:
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand
    which_pick = shutil.which("dongle-pick")
    if which_pick:
        return Path(which_pick)
    return None


def cmd_pick():
    """Interactive picker — prints chosen path to stdout."""
    # In PyInstaller binary mode for the lightweight `dongle` binary (which excludes prompt_toolkit),
    # delegate to `dongle-pick`. Avoid infinite recursion if we ARE already inside `dongle-pick`.
    if hasattr(sys, '_MEIPASS') and Path(sys.executable).name == "dongle":
        pick_bin = _find_pick_binary()
        if pick_bin and pick_bin.resolve() != Path(sys.executable).resolve():
            os.execv(str(pick_bin), [str(pick_bin)] + sys.argv[1:])

    import argparse
    # Lazy: only loaded when actually picking
    from dongle.utils import patch_asyncio
    from dongle.scanner import find_project_root, load_cache, scan_paths, save_cache, get_workspace_cache_key
    from dongle.ui import run_picker

    patch_asyncio()

    parser = argparse.ArgumentParser(description="Dongle interactive picker")
    parser.add_argument("root", nargs="?", default=None)
    parser.add_argument("--rescan", action="store_true")
    parser.add_argument("--workspace", action="store_true")
    parser.add_argument("--query", type=str, default="")
    args = parser.parse_args()

    if args.root is None:
        root = find_project_root(os.getcwd())
    else:
        root = os.path.abspath(args.root)

    cache_key = get_workspace_cache_key() if args.workspace else root
    cache_file = WORKSPACE_CACHE_FILE if args.workspace else CACHE_FILE

    paths = None if args.rescan else load_cache(cache_key, cache_file)
    if paths is None:
        paths = scan_paths(root, is_workspace=args.workspace)
        save_cache(cache_key, paths, cache_file)

    chosen = run_picker(root, paths, is_workspace=args.workspace, cwd=os.getcwd(), initial_query=args.query)

    if chosen == "__UPDATE__":
        sys.stderr.write("\033[2J\033[H")
        sys.stderr.flush()
        os.system("dongle update >/dev/tty 2>&1 </dev/tty")
        sys.exit(0)
    elif chosen:
        from dongle.frecency import record_visit
        if isinstance(chosen, (tuple, list)):
            full_path = chosen[1]
        else:
            full_path = os.path.join(root, chosen) if chosen != "." else root
        record_visit(full_path)
        print(full_path)
    else:
        sys.exit(1)


def cmd_scan():
    """Pre-scan and cache paths for a directory."""
    import argparse
    from dongle.scanner import find_project_root, scan_paths, save_cache, get_workspace_cache_key

    parser = argparse.ArgumentParser(description="Dongle scanner")
    parser.add_argument("root", nargs="?", default=None)
    parser.add_argument("--workspace", action="store_true")
    args = parser.parse_args()

    if args.root is None:
        root = find_project_root(os.getcwd())
    else:
        root = os.path.abspath(args.root)

    cache_file = WORKSPACE_CACHE_FILE if args.workspace else CACHE_FILE
    cache_key = get_workspace_cache_key() if args.workspace else root

    sys.stderr.write(f"Scanning {'workspaces' if args.workspace else root}...\n")
    paths = scan_paths(root, is_workspace=args.workspace)
    save_cache(cache_key, paths, cache_file)
    sys.stderr.write(f"Cached {len(paths)} paths\n")


def cmd_list():
    """List cached paths."""
    import argparse
    from dongle.scanner import get_paths

    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=os.getcwd())
    parser.add_argument("--workspace", action="store_true")
    args = parser.parse_args()
    root = os.path.abspath(args.root)
    for p in get_paths(root, is_workspace=args.workspace):
        if isinstance(p, (tuple, list)):
            print(f"{p[0]}\t{p[1]}")
        else:
            print(p)


def cmd_root():
    """Print the project root for the current directory."""
    from dongle.scanner import find_project_root
    print(find_project_root(os.getcwd()))


def cmd_recent():
    """Print recently visited directories."""
    from dongle.frecency import get_recent_dirs, get_bookmark_set
    dirs = get_recent_dirs(20)
    bookmarks = get_bookmark_set()
    if not dirs and not bookmarks:
        print(f"{DIM}  No recent or pinned directories yet. Start navigating with dg or /{RESET}")
        return
    if bookmarks:
        print(f"\n{BOLD}  Pinned directories (★):{RESET}")
        for b in bookmarks:
            display = b.replace(str(Path.home()), "~")
            print(f"  {YELLOW}★{RESET}  {display}")
    if dirs:
        print(f"\n{BOLD}  Recent directories:{RESET}")
        for d in dirs:
            display = d.replace(str(Path.home()), "~")
            star = f"{YELLOW}★{RESET}" if d in bookmarks else f"{DIM}→{RESET}"
            print(f"  {star}  {display}")
    print()


def cmd_bookmarks():
    """Manage bookmarked / pinned directories."""
    from dongle.frecency import get_bookmarks, toggle_bookmark
    if len(sys.argv) >= 3:
        sub = sys.argv[2]
        target = os.path.abspath(sys.argv[3]) if len(sys.argv) >= 4 else os.getcwd()
        if sub in ("add", "pin", "toggle"):
            pinned = toggle_bookmark(target)
            status = f"{GREEN}★ Pinned{RESET}" if pinned else f"{YELLOW}☆ Unpinned{RESET}"
            print(f"  {status}: {target}")
            return
    bms = get_bookmarks()
    if not bms:
        print(f"{DIM}  No pinned directories yet. Press Ctrl+B inside the picker or run 'dongle pin'.{RESET}")
        return
    print(f"\n{BOLD}  Pinned directories:{RESET}")
    for b in bms:
        display = b.replace(str(Path.home()), "~")
        print(f"  {YELLOW}★{RESET}  {display}")
    print()


def cmd_prune():
    """Prune deleted directories from frecency, bookmarks, and cache."""
    from dongle.frecency import prune_frecency
    removed = prune_frecency()
    print(f"  {GREEN}✓{RESET} Pruned {removed} non-existent directory entries from frecency & bookmarks.")


def cmd_intro():
    print(f"""
{BOLD}{CYAN}  Dongle v{VERSION}{RESET} — Lightning-fast fuzzy directory navigation
{DIM}  https://github.com/jeremiahseun/dongle{RESET}

{BOLD}  Navigation:{RESET}
    {GREEN}dg{RESET}            Open directory search (current project)
    {GREEN}dg <query>{RESET}    Open search pre-filled with query
    {GREEN}dgw{RESET}           Workspace search (across all projects)
    {GREEN}dgr{RESET}           Jump to project root immediately
    {GREEN}dgl{RESET}           List all cached paths
    {GREEN}dgrecent{RESET}      Show pinned & recently visited directories
    {GREEN}/{RESET}             Press on empty prompt to search
    {GREEN}Ctrl+O{RESET}        Open picker anywhere (inserts path if prompt not empty)

{BOLD}  Commands:{RESET}
    dongle init <shell>   Output shell integration (bash/zsh/fish)
    dongle root           Print current project root
    dongle recent         Show pinned & recently visited directories
    dongle pin [dir]      Pin / unpin a directory (default: current directory)
    dongle prune          Remove deleted directories from frecency & pins
    dongle scan           Pre-scan & cache current directory
    dongle doctor         Check if everything is set up correctly
    dongle update         Update Dongle to the latest version
    dongle version        Show version

{BOLD}  Picker keys:{RESET}
    {DIM}↑↓ / Ctrl+P/N{RESET}  Navigate results
    {DIM}Enter{RESET}           Go to selected directory
    {DIM}Tab{RESET}             Open Action Menu (VS Code / Cursor, Finder, Copy path, Pin)
    {DIM}Ctrl+B{RESET}          Pin / Unpin selected directory (★ floats to top)
    {DIM}Ctrl+V{RESET}          Toggle live directory preview pane
    {DIM}Ctrl+W{RESET}          Toggle workspace search
    {DIM}Ctrl+R{RESET}          Rescan directory (refresh cache)
    {DIM}Ctrl+U{RESET}          Clear query
    {DIM}Esc / Ctrl+C{RESET}    Cancel

{BOLD}  Setup:{RESET}
    Add to your ~/.zshrc (or equivalent):
    {DIM}eval "$(dongle init zsh)"{RESET}

    Then reload: {DIM}source ~/.zshrc{RESET}
""")


def cmd_doctor():
    """Diagnose installation issues."""
    print(f"\n{BOLD}{CYAN}  Dongle Doctor (v{VERSION}){RESET}\n")
    issues = 0

    if hasattr(sys, '_MEIPASS'):
        print(f"  {GREEN}✓{RESET} Running as standalone binary")
        pick_bin = _find_pick_binary()
        if pick_bin:
            print(f"  {GREEN}✓{RESET} dongle-pick binary found: {DIM}{pick_bin}{RESET}")
        else:
            print(f"  {RED}✗{RESET} dongle-pick binary NOT found alongside dongle")
            issues += 1
    else:
        pick_path = shutil.which("dongle-pick")
        if pick_path:
            print(f"  {GREEN}✓{RESET} dongle-pick found: {DIM}{pick_path}{RESET}")
        else:
            print(f"  {RED}✗{RESET} dongle-pick NOT found in PATH")
            print(f"    {DIM}This is the core picker binary. Reinstall dongle.{RESET}")
            issues += 1

        scan_path = shutil.which("dongle-scan")
        if scan_path:
            print(f"  {GREEN}✓{RESET} dongle-scan found: {DIM}{scan_path}{RESET}")
        else:
            print(f"  {RED}✗{RESET} dongle-scan NOT found in PATH")
            issues += 1

    shell_name = os.path.basename(os.environ.get("SHELL", "unknown"))
    print(f"  {GREEN}✓{RESET} Detected shell: {BOLD}{shell_name}{RESET}")

    rc_files = {
        "zsh": os.path.expanduser("~/.zshrc"),
        "bash": os.path.expanduser("~/.bashrc"),
        "fish": os.path.expanduser("~/.config/fish/config.fish"),
    }

    rc_file = rc_files.get(shell_name)
    if rc_file and os.path.exists(rc_file):
        with open(rc_file) as f:
            content = f.read()
        if "dongle" in content:
            print(f"  {GREEN}✓{RESET} Shell integration found in {DIM}{rc_file}{RESET}")
        else:
            print(f"  {RED}✗{RESET} Shell integration NOT found in {rc_file}")
            if shell_name == "fish":
                print(f'    {BOLD}dongle init fish | source{RESET}')
            else:
                print(f'    {BOLD}eval "$(dongle init {shell_name})"{RESET}')
            issues += 1
    elif rc_file:
        print(f"  {YELLOW}⚠{RESET} Shell config file not found: {rc_file}")
        issues += 1

    shell_dir = _get_shell_dir()
    filenames = {"bash": "bash.sh", "zsh": "zsh.sh", "fish": "fish.fish"}
    script_file = filenames.get(shell_name)
    if script_file:
        script_path = shell_dir / script_file
        if script_path.exists():
            print(f"  {GREEN}✓{RESET} Shell script exists: {DIM}{script_path}{RESET}")
        else:
            print(f"  {RED}✗{RESET} Shell script missing: {script_path}")
            issues += 1

    ws = os.environ.get("DONGLE_WORKSPACES", "")
    if ws:
        print(f"  {GREEN}✓{RESET} DONGLE_WORKSPACES set: {DIM}{ws}{RESET}")
    else:
        print(f"  {YELLOW}⚠{RESET} DONGLE_WORKSPACES not set {DIM}(optional, falls back to parent directory for dgw){RESET}")

    if os.path.exists("/dev/tty"):
        print(f"  {GREEN}✓{RESET} /dev/tty available")
    else:
        print(f"  {RED}✗{RESET} /dev/tty NOT available (picker won't work)")
        issues += 1

    print()
    if issues == 0:
        print(f"  {GREEN}{BOLD}All checks passed!{RESET}")
        print(f"  {DIM}If dg/dgw/dgs still don't work, reload your shell:{RESET}")
        print(f"  {BOLD}source ~/.zshrc{RESET}  {DIM}(or restart your terminal){RESET}")
    else:
        print(f"  {RED}{BOLD}{issues} issue(s) found.{RESET} Fix them above and try again.")
    print()


def cmd_update():
    """Update Dongle to the latest version."""
    print(f"\n{BOLD}{CYAN}  Dongle Updater{RESET}\n")

    if hasattr(sys, '_MEIPASS'):
        print(f"  {DIM}Binary installation detected. Re-running installer...{RESET}\n")
        result = subprocess.run(
            ["bash", "-c", "curl -sSL https://raw.githubusercontent.com/jeremiahseun/dongle/main/install.sh | bash"],
            check=False
        )
        if result.returncode == 0:
            print(f"\n  {GREEN}{BOLD}Updated successfully!{RESET}")
        else:
            print(f"\n  {RED}Update failed.{RESET} Try manually:")
            print(f"  curl -sSL https://raw.githubusercontent.com/jeremiahseun/dongle/main/install.sh | bash")
    else:
        print(f"  {DIM}pip installation detected. Upgrading...{RESET}\n")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "dongle"],
            check=False
        )
        if result.returncode == 0:
            print(f"\n  {GREEN}{BOLD}Updated successfully!{RESET}")
            print(f"  {DIM}Reload your shell to use the new version.{RESET}")
        else:
            print(f"\n  {RED}Update failed.{RESET} Try manually:")
            print(f"  pip install --upgrade dongle")
    print()


def cmd_init(shell: str):
    """Output shell integration script."""
    if hasattr(sys, '_MEIPASS'):
        print(_read_shell_script(shell))
    else:
        shell_dir = _get_shell_dir()
        filenames = {"bash": "bash.sh", "zsh": "zsh.sh", "fish": "fish.fish"}
        if shell not in filenames:
            print(f"Unknown shell: {shell}. Supported: bash, zsh, fish", file=sys.stderr)
            sys.exit(1)
        script_path = shell_dir / filenames[shell]
        if not script_path.exists():
            print(f"Shell script not found: {script_path}", file=sys.stderr)
            sys.exit(1)
        print(f"source '{script_path}'")


def cmd_version():
    print(f"dongle {VERSION}")


def main():
    if len(sys.argv) < 2:
        cmd_intro()
        return

    cmd = sys.argv[1]

    if cmd == "pick":
        sys.argv.pop(1)
        cmd_pick()
    elif cmd == "scan":
        sys.argv.pop(1)
        cmd_scan()
    elif cmd == "list":
        sys.argv.pop(1)
        cmd_list()
    elif cmd == "root":
        cmd_root()
    elif cmd == "recent":
        cmd_recent()
    elif cmd in ("bookmarks", "pins"):
        cmd_bookmarks()
    elif cmd == "pin":
        sys.argv.insert(2, "toggle")
        cmd_bookmarks()
    elif cmd == "prune":
        cmd_prune()
    elif cmd == "init":
        if len(sys.argv) < 3:
            print("Usage: dongle init <shell>", file=sys.stderr)
            print("  Supported shells: bash, zsh, fish", file=sys.stderr)
            sys.exit(1)
        cmd_init(sys.argv[2])
    elif cmd == "doctor":
        cmd_doctor()
    elif cmd == "update":
        cmd_update()
    elif cmd in ("version", "--version", "-v"):
        cmd_version()
    elif cmd in ("help", "--help", "-h"):
        cmd_intro()
    else:
        if cmd.startswith("-"):
            cmd_intro()
        else:
            sys.argv.insert(1, "pick")
            sys.argv.insert(2, "--query")
            main()


if __name__ == "__main__":
    main()
