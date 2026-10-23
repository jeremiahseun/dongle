# Dongle Roadmap 🗺️

Dongle is continuously evolving. Here is a list of features we are planning to build, currently working on, or have already shipped!

## Planned Features

- **Windows Support**: Ensure full native compatibility with PowerShell and Windows Terminal.
- **GUI Launcher**: An optional GUI wrapper for non-terminal enthusiasts.
- **Custom User Actions**: Allow users to define custom shell commands in `~/.dongle_actions.json` for the `Tab` menu.

## Completed ✅

- **Live File & Directory Previews (`Ctrl+V`)**: Right-hand pane in the picker previewing git branch, directory/file counts, top contents, and `README.md` snippet.
- **Action Menus (`Tab`)**: Press `Tab` on a directory to open in Cursor/VS Code, reveal in Finder, copy path to clipboard, or pin/unpin.
- **Bookmarks / Pinning (`Ctrl+B` & `dongle pin`)**: Pin favorite directories with `★` and prune stale entries with `dongle prune`.
- **Multi-Segment & Acronym Fuzzy Highlighting**: Highlights every matched character across contiguous, multi-word, and acronym searches.
- **Standalone Release Binaries**: Automated GitHub Actions & macOS `--onedir` fast-startup bundles via PyInstaller.
- **Smart Sorting ("Frecent" Tracking)**: Track frequently and recently visited directories to boost them to the top of search results.
- **Workspace Search (`dgw`)**: Cross-project search powered by `DONGLE_WORKSPACES` (with automatic parent fallback).
- **`.gitignore` & `.dongleignore` Integration**: Automatically parse and respect ignore rules.
- **Instant Terminal UI**: Inline TUI using `prompt_toolkit`.
- **Seamless Shell Integration**: Support for Bash, Zsh, and Fish without replacing `cd`.

---

### Contributing
Have a great idea? Feel free to open an issue or submit a PR on [GitHub](https://github.com/jeremiahseun/dongle) to help us bring these features to life!
