import sys
import os
print(f"stdin isatty: {sys.stdin.isatty()}", file=sys.stderr)
print(f"stdout isatty: {sys.stdout.isatty()}", file=sys.stderr)
try:
    print(f"tty: {os.ttyname(sys.stdin.fileno())}", file=sys.stderr)
except Exception as e:
    print(f"tty error: {e}", file=sys.stderr)
