# This file is kept for backwards compatibility with existing installations
# before the v0.3.0 architectural refactoring. It now proxies to the new cli interface.

from dongle.cli import cmd_pick, cmd_scan, cmd_list

if __name__ == "__main__":
    cmd_pick()
