# This file is kept for backwards compatibility with existing installations
# before the v0.3.0 architectural refactoring. It now proxies to the new cli interface.

import sys
from dongle.cli import cmd_pick, cmd_scan, cmd_list, main

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] in ("scan", "list", "pick"):
        main()
    else:
        cmd_pick()
