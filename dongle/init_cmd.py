import sys
import os
import shutil
import subprocess
from pathlib import Path


CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def _get_shell_dir() -> Path:
    """Find shell scripts whether running from pip install or PyInstaller binary."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "dongle" / "shell"
    return Path(__file__).parent.resolve() / "shell"


def _read_shell_script(shell: str) -> str:
    """Read and return a shell integration script's content."""
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


def cmd_intro():
    """Show a friendly introduction when dongle is run with no arguments."""
    print(f"""
{BOLD}{CYAN}  🔌 Dongle{RESET} — Fast, fuzzy directory navigation
{DIM}  https://github.com/jeremiahseun/dongle{RESET}

{BOLD}  Quick Start:{RESET}
    {GREEN}dg{RESET}     Open directory search (current project)
    {GREEN}dgw{RESET}    Workspace search (across all projects)
    {GREEN}dgs{RESET}    Pre-scan & cache the current directory
    {GREEN}/{RESET}      Press on empty prompt to search

{BOLD}  Commands:{RESET}
    dongle init <shell>   Output shell integration (bash/zsh/fish)
    dongle doctor         Check if everything is set up correctly
    dongle update         Update Dongle to the latest version
    dongle version        Show version

{BOLD}  Setup:{RESET}
    Add this to your ~/.zshrc (or equivalent):
    {DIM}eval "$(dongle init zsh)"{RESET}

    Then reload: {DIM}source ~/.zshrc{RESET}
""")


def cmd_doctor():
    """Diagnose installation issues."""
    print(f"\n{BOLD}{CYAN}  🔌 Dongle Doctor{RESET}\n")
    issues = 0

    # 1. Check dongle-pick is available
    pick_path = shutil.which("dongle-pick")
    if pick_path:
        print(f"  {GREEN}✓{RESET} dongle-pick found: {DIM}{pick_path}{RESET}")
    else:
        print(f"  {RED}✗{RESET} dongle-pick NOT found in PATH")
        print(f"    {DIM}This is the core picker binary. Reinstall dongle.{RESET}")
        issues += 1

    # 2. Check dongle-scan is available
    scan_path = shutil.which("dongle-scan")
    if scan_path:
        print(f"  {GREEN}✓{RESET} dongle-scan found: {DIM}{scan_path}{RESET}")
    else:
        print(f"  {RED}✗{RESET} dongle-scan NOT found in PATH")
        issues += 1

    # 3. Check shell integration
    shell_name = os.path.basename(os.environ.get("SHELL", "unknown"))
    print(f"  {GREEN}✓{RESET} Detected shell: {BOLD}{shell_name}{RESET}")

    rc_files = {
        "zsh": os.path.expanduser("~/.zshrc"),
        "bash": os.path.expanduser("~/.bashrc"),
        "fish": os.path.expanduser("~/.config/fish/config.fish"),
    }

    rc_file = rc_files.get(shell_name)
    if rc_file and os.path.exists(rc_file):
        with open(rc_file, "r") as f:
            content = f.read()
        if "dongle" in content:
            print(f"  {GREEN}✓{RESET} Shell integration found in {DIM}{rc_file}{RESET}")
        else:
            print(f"  {RED}✗{RESET} Shell integration NOT found in {rc_file}")
            print(f"    {DIM}Add this line:{RESET}")
            if shell_name == "fish":
                print(f'    {BOLD}dongle init fish | source{RESET}')
            else:
                print(f'    {BOLD}eval "$(dongle init {shell_name})"{RESET}')
            issues += 1
    elif rc_file:
        print(f"  {YELLOW}⚠{RESET} Shell config file not found: {rc_file}")
        issues += 1

    # 4. Check shell scripts exist
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

    # 5. Check DONGLE_WORKSPACES
    ws = os.environ.get("DONGLE_WORKSPACES", "")
    if ws:
        print(f"  {GREEN}✓{RESET} DONGLE_WORKSPACES set: {DIM}{ws}{RESET}")
    else:
        print(f"  {YELLOW}⚠{RESET} DONGLE_WORKSPACES not set {DIM}(optional, needed for dgw){RESET}")

    # 6. Check /dev/tty
    if os.path.exists("/dev/tty"):
        print(f"  {GREEN}✓{RESET} /dev/tty available")
    else:
        print(f"  {RED}✗{RESET} /dev/tty NOT available (picker won't work)")
        issues += 1

    # Summary
    print("")
    if issues == 0:
        print(f"  {GREEN}{BOLD}All checks passed!{RESET}")
        print(f"  {DIM}If dg/dgw/dgs still don't work, reload your shell:{RESET}")
        print(f"  {BOLD}source ~/.zshrc{RESET}  {DIM}(or restart your terminal){RESET}")
    else:
        print(f"  {RED}{BOLD}{issues} issue(s) found.{RESET} Fix them above and try again.")
    print("")


def cmd_update():
    """Update Dongle to the latest version."""
    print(f"\n{BOLD}{CYAN}  🔌 Dongle Updater{RESET}\n")

    if hasattr(sys, '_MEIPASS'):
        # Standalone binary mode — re-run the install script
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
        # Pip-installed mode
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
    print("")


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


def main():
    if len(sys.argv) < 2:
        cmd_intro()
        return

    cmd = sys.argv[1]

    if cmd == "init":
        if len(sys.argv) < 3:
            print("Usage: dongle init <shell>", file=sys.stderr)
            print("  Supported shells: bash, zsh, fish", file=sys.stderr)
            sys.exit(1)
        cmd_init(sys.argv[2])
    elif cmd == "doctor":
        cmd_doctor()
    elif cmd == "update":
        cmd_update()
    elif cmd == "version":
        print("dongle 0.2.1")
    elif cmd in ("help", "--help", "-h"):
        cmd_intro()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print("Run 'dongle' with no arguments for help.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
