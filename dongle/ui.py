import os
import shutil
import sys
from pathlib import Path


def run_picker(root, paths, is_workspace=False, cwd=None, initial_query=""):
    """Run the interactive TUI picker. All heavy imports are deferred to here."""
    # Lazy: prompt_toolkit is only imported when the picker actually opens
    from prompt_toolkit import Application
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, ConditionalContainer
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style

    from dongle.config import CACHE_FILE, WORKSPACE_CACHE_FILE, get_preview_enabled
    from dongle.matcher import search, get_match_indices, _DISPLAY_LIMIT
    from dongle.scanner import scan_paths, save_cache, find_project_root, get_workspace_cache_key
    from dongle.frecency import get_frecency_scores, get_bookmark_set, toggle_bookmark
    from dongle.preview import get_directory_preview, clear_preview_cache, ACTIONS, execute_action

    if paths is None:
        paths = scan_paths(root, is_workspace=is_workspace)

    frecency = get_frecency_scores()
    bookmarks = get_bookmark_set()

    def _resolve_full_path(item) -> str:
        if isinstance(item, (tuple, list)):
            return item[1]
        return root if item == "." else os.path.join(root, item)

    state = {
        "is_workspace": is_workspace,
        "paths": paths,
        "filtered": search(initial_query, paths, frecency, bookmarks, root),
        "index": 0,
        "query": initial_query,
        "chosen": None,
        "is_scanning": False,
        "show_preview": get_preview_enabled(),
        "action_menu": False,
        "action_index": 0,
        "toast": "",
    }

    def _recompute_search(use_progressive=False):
        if use_progressive and len(state["filtered"]) < _DISPLAY_LIMIT:
            pool = state["filtered"]
        else:
            pool = state["paths"]
        state["filtered"] = search(
            state["query"],
            pool,
            frecency,
            bookmarks,
            None if state["is_workspace"] else root,
        )
        state["index"] = 0

    kb = KeyBindings()

    @kb.add("c-c")
    @kb.add("escape")
    def _cancel(event):
        if state["action_menu"]:
            state["action_menu"] = False
            event.app.invalidate()
        else:
            event.app.exit()

    @kb.add("tab")
    def _toggle_actions(event):
        if not state["filtered"]:
            return
        state["action_menu"] = not state["action_menu"]
        state["action_index"] = 0
        state["toast"] = ""
        event.app.invalidate()

    @kb.add("c-v")
    def _toggle_preview(event):
        state["show_preview"] = not state["show_preview"]
        event.app.invalidate()

    @kb.add("c-b")
    def _pin_selected(event):
        if not state["filtered"]:
            return
        item = state["filtered"][state["index"]]
        full_p = _resolve_full_path(item)
        is_pinned = toggle_bookmark(full_p)
        bookmarks.clear()
        bookmarks.update(get_bookmark_set())
        state["toast"] = "★ Pinned" if is_pinned else "☆ Unpinned"
        event.app.invalidate()

    def _run_selected_action(action_id: str, event):
        if not state["filtered"]:
            return
        item = state["filtered"][state["index"]]
        full_p = _resolve_full_path(item)

        if action_id == "cd":
            state["chosen"] = item
            event.app.exit()
        elif action_id == "pin":
            is_pinned = toggle_bookmark(full_p)
            bookmarks.clear()
            bookmarks.update(get_bookmark_set())
            state["action_menu"] = False
            state["toast"] = "★ Pinned" if is_pinned else "☆ Unpinned"
            event.app.invalidate()
        else:
            should_exit, msg = execute_action(action_id, full_p)
            if should_exit:
                if msg:
                    sys.stderr.write(f"  ✓ {msg}\n")
                    sys.stderr.flush()
                event.app.exit()
            else:
                state["action_menu"] = False
                state["toast"] = msg
                event.app.invalidate()

    @kb.add("enter")
    def _select(event):
        if not state["filtered"]:
            event.app.exit()
            return
        if state["action_menu"]:
            act_id = ACTIONS[state["action_index"]][0]
            _run_selected_action(act_id, event)
        else:
            state["chosen"] = state["filtered"][state["index"]]
            event.app.exit()

    @kb.add("up")
    @kb.add("c-p")
    def _up(event):
        if state["action_menu"]:
            state["action_index"] = (state["action_index"] - 1) % len(ACTIONS)
        elif state["filtered"]:
            state["index"] = (state["index"] - 1) % len(state["filtered"])
            state["toast"] = ""
        event.app.invalidate()

    @kb.add("down")
    @kb.add("c-n")
    def _down(event):
        if state["action_menu"]:
            state["action_index"] = (state["action_index"] + 1) % len(ACTIONS)
        elif state["filtered"]:
            state["index"] = (state["index"] + 1) % len(state["filtered"])
            state["toast"] = ""
        event.app.invalidate()

    @kb.add("c-u")
    def _clear(event):
        state["action_menu"] = False
        state["query"] = ""
        state["toast"] = ""
        _recompute_search(use_progressive=False)
        event.app.invalidate()

    @kb.add("c-w")
    def _workspace(event):
        state["action_menu"] = False
        state["is_workspace"] = not state["is_workspace"]
        state["is_scanning"] = True
        state["toast"] = ""
        event.app.invalidate()
        ws_root = find_project_root(cwd or os.getcwd())
        state["paths"] = scan_paths(ws_root, is_workspace=state["is_workspace"])
        state["is_scanning"] = False
        _recompute_search(use_progressive=False)
        event.app.invalidate()

    @kb.add("c-r")
    def _rescan(event):
        state["action_menu"] = False
        state["is_scanning"] = True
        state["toast"] = "Rescanning..."
        clear_preview_cache()
        event.app.invalidate()
        state["paths"] = scan_paths(root, is_workspace=state["is_workspace"])
        cache_file = WORKSPACE_CACHE_FILE if state["is_workspace"] else CACHE_FILE
        cache_key = get_workspace_cache_key() if state["is_workspace"] else root
        save_cache(cache_key, state["paths"], cache_file)
        state["is_scanning"] = False
        state["toast"] = "Cache refreshed"
        _recompute_search(use_progressive=False)
        event.app.invalidate()

    @kb.add(Keys.Any)
    def _type(event):
        if not (event.data and len(event.data) == 1 and event.data.isprintable()):
            return

        # If inside action menu, allow single-key action shortcuts (e, o, y, p)
        if state["action_menu"]:
            ch = event.data.lower()
            for act_id, _label, shortcut in ACTIONS:
                if ch == shortcut.lower():
                    _run_selected_action(act_id, event)
                    return
            return

        old_query = state["query"]
        state["query"] += event.data
        state["toast"] = ""
        _recompute_search(use_progressive=bool(old_query))
        event.app.invalidate()

    @kb.add("backspace")
    def _backspace(event):
        if state["action_menu"]:
            state["action_menu"] = False
            event.app.invalidate()
            return
        state["query"] = state["query"][:-1]
        state["toast"] = ""
        _recompute_search(use_progressive=False)
        event.app.invalidate()

    def get_prompt_text():
        mode = "Workspace" if state["is_workspace"] else "Project"
        display_root = root.replace(str(Path.home()), "~")
        n_filtered = len(state["filtered"])
        n_total = len(state["paths"])

        if state["is_scanning"]:
            status = "  [Scanning...]"
        elif state["query"]:
            status = f"  ({n_filtered}/{n_total})"
        else:
            status = f"  ({n_total} dirs)"

        toast_part = f"   {state['toast']}" if state["toast"] else ""

        return [
            ("class:title", f"  {mode}  "),
            ("class:title-path", display_root),
            ("class:title-count", status),
            ("class:toast", f"{toast_part}\n"),
            ("class:prompt", "  / "),
            ("class:query", state["query"]),
            ("class:cursor", "█"),  # block cursor
        ]

    def _highlight(display_p: str, full_p: str, query: str, selected: bool):
        sel = "class:selected" if selected else ""
        arrow = "❯ " if selected else "  "
        pin = "★ " if full_p in bookmarks else ""
        pad = "  "

        prefix_style = f"{sel} class:pin" if (selected and pin) else ("class:pin" if pin else sel)
        tokens = [(sel, f"{pad}{arrow}")]
        if pin:
            tokens.append((prefix_style, pin))

        if not query:
            tokens.append((sel, f"{display_p}\n"))
            return tokens

        match_indices = set(get_match_indices(display_p, query))
        if not match_indices:
            tokens.append((sel, f"{display_p}\n"))
            return tokens

        hi = f"{sel} class:match" if selected else "class:match"
        # Group consecutive characters with identical highlight state to minimize tuple count
        curr_in_match = (0 in match_indices)
        buf = []
        for idx, ch in enumerate(display_p):
            in_m = (idx in match_indices)
            if in_m != curr_in_match and buf:
                tokens.append((hi if curr_in_match else sel, "".join(buf)))
                buf = [ch]
                curr_in_match = in_m
            else:
                buf.append(ch)
        if buf:
            tokens.append((hi if curr_in_match else sel, "".join(buf)))
        tokens.append((sel, "\n"))
        return tokens

    def get_results_text():
        if state["action_menu"] and state["filtered"]:
            item = state["filtered"][state["index"]]
            display_p = item[0] if isinstance(item, (tuple, list)) else item
            lines = [
                ("class:title", f"    Actions for "),
                ("class:title-path", f"{display_p}\n\n"),
            ]
            for i, (_act_id, label, shortcut) in enumerate(ACTIONS):
                is_sel = (i == state["action_index"])
                style = "class:selected" if is_sel else ""
                arrow = "  ❯ " if is_sel else "    "
                key_style = f"{style} class:match" if is_sel else "class:footer-key"
                lines.append((style, f"{arrow}"))
                lines.append((key_style, f"[{shortcut}] "))
                lines.append((style, f"{label}\n"))
            return lines

        if not state["filtered"]:
            if state["query"]:
                return [
                    ("class:no-match", "    No matches.\n"),
                    ("class:hint", "    Ctrl+W — toggle workspace search\n"),
                ]
            return [("class:hint", "    Start typing to filter...\n")]

        results = []
        start = max(0, state["index"] - 7)
        end = min(len(state["filtered"]), start + 15)

        for i in range(start, end):
            p = state["filtered"][i]
            display_p = p[0] if isinstance(p, (tuple, list)) else p
            full_p = _resolve_full_path(p)
            results.extend(_highlight(display_p, full_p, state["query"], i == state["index"]))

        return results

    def get_preview_text():
        if not state["filtered"]:
            return [("class:hint", "  No selection\n")]
        item = state["filtered"][state["index"]]
        full_p = _resolve_full_path(item)
        return get_directory_preview(full_p, max_lines=14)

    def get_footer_text():
        if state["action_menu"]:
            return [
                ("class:footer-key", " ↑↓"),
                ("class:footer", " select action  "),
                ("class:footer-key", "Enter"),
                ("class:footer", " run  "),
                ("class:footer-key", "e/o/y/p"),
                ("class:footer", " shortcut  "),
                ("class:footer-key", "Tab/Esc"),
                ("class:footer", " back "),
            ]
        return [
            ("class:footer-key", " ↑↓"),
            ("class:footer", " nav  "),
            ("class:footer-key", "Enter"),
            ("class:footer", " cd  "),
            ("class:footer-key", "Tab"),
            ("class:footer", " actions  "),
            ("class:footer-key", "^B"),
            ("class:footer", " pin  "),
            ("class:footer-key", "^V"),
            ("class:footer", " preview  "),
            ("class:footer-key", "^W"),
            ("class:footer", " workspace  "),
            ("class:footer-key", "^R"),
            ("class:footer", " rescan  "),
            ("class:footer-key", "Esc"),
            ("class:footer", " cancel "),
        ]

    style = Style.from_dict({
        "title": "#5f9ea0 bold",
        "title-path": "#87ceeb",
        "title-count": "#666666",
        "toast": "#00d787 bold",
        "prompt": "#00d787 bold",
        "query": "#ffffff bold",
        "cursor": "#00d787",
        "selected": "bg:#1a3a5c #ffffff bold",
        "match": "#ffaf00 bold",
        "selected match": "bg:#1a3a5c #ffaf00 bold",
        "pin": "#ffd700 bold",
        "selected pin": "bg:#1a3a5c #ffd700 bold",
        "no-match": "#666666",
        "hint": "#555555",
        "footer": "#555555",
        "footer-key": "#888888 bold",
        "preview-border": "#333333",
        "preview-title": "#87ceeb bold",
        "preview-git": "#00d787 bold",
        "preview-meta": "#666666",
        "preview-dir": "#5f9ea0",
        "preview-file": "#aaaaaa",
        "preview-readme": "#777777 italic",
    })

    @Condition
    def is_preview_visible():
        if not state["show_preview"] or state["action_menu"]:
            return False
        cols = shutil.get_terminal_size((80, 24)).columns
        return cols >= 72

    prompt_win = Window(
        content=FormattedTextControl(get_prompt_text, focusable=False),
        height=2,
    )
    results_win = Window(
        content=FormattedTextControl(get_results_text, focusable=False),
        height=15,
    )
    divider_win = Window(
        width=1,
        char="│",
        style="class:preview-border",
        height=15,
    )
    preview_win = Window(
        content=FormattedTextControl(get_preview_text, focusable=False),
        width=36,
        height=15,
    )
    body_container = VSplit([
        results_win,
        ConditionalContainer(
            content=VSplit([divider_win, preview_win]),
            filter=is_preview_visible,
        ),
    ])
    footer_win = Window(
        content=FormattedTextControl(get_footer_text, focusable=False),
        height=1,
    )

    layout = Layout(HSplit([prompt_win, body_container, footer_win]))

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
    )

    app.run()
    return state["chosen"]
