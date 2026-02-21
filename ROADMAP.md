# Dongle Roadmap 🗺️

Dongle is continuously evolving. Here is a list of features we are planning to build, currently working on, or have already shipped!

## Planned Features

- **Standalone Release Binaries**: Automate Github Actions to compile Dongle into native executable binaries using PyInstaller. This ensures users won't even need Python installed to use it.
- **File Previews**: Introduce a right-hand pane in the picker to preview the directory's contents (top 5 files, `README.md` snippet, or git status).
- **Smart Sorting ("Frecent" Tracking)**: Track frequently and recently visited directories to boost them to the top of the search results automatically.
- **Action Menus**: Press `Tab` on a directory to reveal actions like "Open in VS Code", "Open in GUI file explorer", or "Run git status".
- **Windows Support**: Ensure full compatibility with PowerShell and Windows Terminal.
- **GUI Launcher**: An optional GUI wrapper for non-terminal enthusiasts.

## In Progress

- **Workspace Search (`dgw`)**: Cross-project search powered by the `DONGLE_WORKSPACES` environment variable.
- **`.gitignore` Integration**: Automatically parse and respect `.gitignore` and `.dongleignore` files without manual configuration.

## Completed ✅

- **Instant Terminal UI**: Built an inline TUI using `prompt_toolkit`.
- **Fuzzy Search Algorithm**: Smart substring and character sequence matching.
- **Seamless Shell Integration**: Support for Bash, Zsh, and Fish without replacing `cd` or destroying shell environments.
- **Auto Background Scans**: Keep cache perfectly warm via background execution.

---

### Contributing
Have a great idea? Feel free to open an issue or submit a PR on [GitHub](https://github.com/jeremiahseun/dongle) to help us bring these features to life!
