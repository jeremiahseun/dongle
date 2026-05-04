import sys
import asyncio
import selectors
import json
import urllib.request
from dongle.config import VERSION

def patch_asyncio():
    """
    Apply asyncio event loop patch for macOS to avoid errors with prompt_toolkit.
    """
    if sys.platform == 'darwin':
        class SelectEventLoop(asyncio.SelectorEventLoop):
            def __init__(self):
                super().__init__(selectors.SelectSelector())
        class SelectEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
            def new_event_loop(self):
                return SelectEventLoop()
        asyncio.set_event_loop_policy(SelectEventLoopPolicy())


def check_for_updates():
    """Check GitHub for a newer release. Returns True if update available."""
    try:
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
