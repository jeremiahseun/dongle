import os
import sys
import asyncio
from prompt_toolkit import Application
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.buffer import Buffer

from dongle.matcher import search
from dongle.scanner import scan_paths, save_cache, find_project_root

def run_picker(root, paths, is_workspace=False, cwd=None, initial_query=""):
    """
    Run the interactive TUI picker.
    """
    if paths is None:
        paths = scan_paths(root, is_workspace=is_workspace)
        # We don't save here because we might want to do it in cli.py instead
        # but for simplicity let's assume scanner handles it or it's done elsewhere.

    current_query = initial_query
    filtered_paths = search(current_query, paths)
    selected_index = 0
    
    # State to track if we've switched to workspace mode mid-session
    state = {
        "is_workspace": is_workspace,
        "paths": paths,
        "filtered": filtered_paths,
        "index": 0,
        "query": initial_query,
        "chosen": None,
        "is_scanning": False
    }

    kb = KeyBindings()

    @kb.add("c-c")
    @kb.add("escape")
    def _(event):
        event.app.exit()

    @kb.add("enter")
    def _(event):
        if state["filtered"]:
            state["chosen"] = state["filtered"][state["index"]]
        event.app.exit()

    @kb.add("up")
    @kb.add("c-p")
    def _(event):
        state["index"] = (state["index"] - 1) % len(state["filtered"]) if state["filtered"] else 0

    @kb.add("down")
    @kb.add("c-n")
    def _(event):
        state["index"] = (state["index"] + 1) % len(state["filtered"]) if state["filtered"] else 0

    # Feature 3: Workspace Fallback (Ctrl+W)
    @kb.add("c-w")
    def _(event):
        if not state["is_workspace"]:
            # Trigger workspace scan
            state["is_workspace"] = True
            state["is_scanning"] = True
            event.app.invalidate()
            
            # Use find_project_root logic or search dir
            ws_root = find_project_root(cwd or os.getcwd())
            state["paths"] = scan_paths(ws_root, is_workspace=True)
            state["is_scanning"] = False
            
            # Re-filter
            state["filtered"] = search(state["query"], state["paths"])
            state["index"] = 0
            event.app.invalidate()

    def get_prompt_text():
        # Feature 3 Visual Hint
        hint = ""
        if not state["filtered"] and not state["is_workspace"]:
            hint = " (No results. Press Ctrl+W for workspace search)"
            
        prefix = "Workspace " if state["is_workspace"] else ""
        scan_msg = " [Scanning...]" if state["is_scanning"] else ""
        
        return [
            ("class:title", f"  Dongle {prefix}Search in {root}{scan_msg}{hint}\n"),
            ("class:prompt", f"  / {state['query']}"),
        ]

    def get_results_text():
        if not state["filtered"]:
            return [("class:error", "    No matches found.")]
            
        results = []
        # Show top 15 results
        start = max(0, state["index"] - 7)
        end = min(len(state["filtered"]), start + 15)
        
        for i in range(start, end):
            p = state["filtered"][i]
            # Handle workspace tuple results
            display_p = p[0] if isinstance(p, (tuple, list)) else p
            
            if i == state["index"]:
                results.append(("class:selected", f"  ❯ {display_p}\n"))
            else:
                results.append(("", f"    {display_p}\n"))
        return results

    prompt_control = FormattedTextControl(get_prompt_text)
    results_control = FormattedTextControl(get_results_text)

    layout = Layout(HSplit([
        Window(content=prompt_control, height=2),
        Window(content=results_control)
    ]))

    app = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=False,
    )

    # Simple buffer-less interaction for now, or we can use a Buffer
    # To support typing, we need to capture keys.
    
    @kb.add(Keys.Any)
    def _(event):
        if event.data and len(event.data) == 1:
            state["query"] += event.data
            state["filtered"] = search(state["query"], state["paths"])
            state["index"] = 0
            
    @kb.add("backspace")
    def _(event):
        state["query"] = state["query"][:-1]
        state["filtered"] = search(state["query"], state["paths"])
        state["index"] = 0

    app.run()
    return state["chosen"]
