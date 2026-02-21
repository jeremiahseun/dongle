import sys
import os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: dongle init <shell>", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        if len(sys.argv) < 3:
            print("Usage: dongle init <shell>", file=sys.stderr)
            sys.exit(1)

        shell = sys.argv[2]

        # Determine the package directory
        pkg_dir = Path(__file__).parent.resolve()

        if shell == "bash":
            script_path = pkg_dir / "shell" / "bash.sh"
            print(f"source '{script_path}'")
        elif shell == "zsh":
            script_path = pkg_dir / "shell" / "zsh.sh"
            print(f"source '{script_path}'")
        elif shell == "fish":
            script_path = pkg_dir / "shell" / "fish.fish"
            # In fish it's standard to output the content or source it
            print(f"source '{script_path}'")
        else:
            print(f"Unknown shell: {shell}. Supported: bash, zsh, fish", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
