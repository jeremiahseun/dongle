<img width="256" height="200" alt="dongle" src="https://github.com/user-attachments/assets/c58d6923-0c32-4d6e-9897-8d422b321033" />

# Dongle ⚡

> **Instant (<2ms) native fuzzy directory navigation — for any terminal.**

No more \`cd ../../some/deep/nested/folder\`. Press \`/\` and search.

\`\`\`
  Project  ~/my-project  (42 dirs)
  / src comp
  ❯ ★ src/components/ui       │ 📁 ui (main)
      src/components/auth     │  2 dirs, 5 files · 📦 Node/TS
      src/components/forms    │   commit: feat: add button variants
      tests/components        │   ▸ buttons/
                              │   ▸ modals/
                              │   • Button.tsx
  ─────────────────────────────────────────────────────────
  ↑↓ nav  Enter cd  Tab actions  ^H/^L up/in  ^B pin  ^V preview  ^W ws  ^Y mkdir  Esc exit
```

Press **Enter** to jump there — or press **Tab** to open in Cursor/VS Code, reveal in Finder, copy the path, or create a folder on the fly.

---

## Demo

https://github.com/user-attachments/assets/6460e432-f732-4d4b-8324-1308ee36460c

---

## Install

### One command (recommended)

\`\`\`
curl -sSL https://raw.githubusercontent.com/jeremiahseun/dongle/main/install.sh > install_dongle.sh && bash install_dongle.sh && rm install_dongle.sh
\`\`\`

That's it. The installer:
- Compiles or downloads the **156 KB Native C++17 binary** — zero Python overhead, zero dependencies, `<2ms` startup
- Adds `~/.dongle/bin` to your `PATH`
- Wires up instant shell integration in `~/.zshrc`, `~/.bashrc`, or `~/.config/fish/config.fish`

Reload your shell (`source ~/.zshrc`) and press `/`.

---

## How to use

### Shell Shortcuts

| What you do | What happens |
|-------------|-------------|
| Press `/` on an empty prompt | Open live directory search |
| Press `Ctrl+O` anywhere | Open directory search (inserts escaped path at cursor if prompt non-empty) |
| Press `Ctrl+/` anywhere | Same as `Ctrl+O` |
| Type `dg` | Open directory search |
| Type `dg <query>` | Open search pre-filled with query (**auto-jumps immediately if 1 match!**) |
| Type `dgj <query>` | **Instant headless jump** to #1 best match without opening TUI |
| Type `dgw` | Search across **all your projects** (workspace mode) |
| Type `dgr` | Jump to project root instantly — no picker |
| Type `dgpin` | Pin / unpin (`★`) the current directory |
| Type `dgl` | List all paths in the current project |
| Type `dgrecent` | Show pinned & recently visited directories |

### Inside the Picker

| Key | Action |
|-----|--------|
| Type anything | Filter results live (substring, multi-segment, and acronym matching) |
| `↑` / `↓` or `Ctrl+P` / `Ctrl+N` | Move selection |
| `Enter` | Navigate (`cd`) to selected directory |
| `←` / `→` or `Ctrl+H` / `Ctrl+L` | **Climb up (`..`)** to parent directory or **drill into** selected folder as new root |
| `Tab` | Open **Action Menu** (`[e]` Cursor/VS Code, `[o]` Finder, `[y]` Copy path, `[p]` Pin, `[n]` Mkdir) |
| `Ctrl+B` | Pin / Unpin selected directory (`★` floats to top) |
| `Ctrl+V` | Toggle live right-pane Developer Preview HUD |
| `Ctrl+Y` | **Create new directory (`mkdir -p`)** from current query and `cd` into it |
| `Ctrl+W` | Toggle between Project and Workspace search without closing |
| `Ctrl+R` | Rescan the directory tree |
| `Ctrl+U` | Clear the current query |
| `Esc` / `Ctrl+C` | Cancel |

### CLI Commands

```
dongle                 Show welcome banner & quick-start guide
dongle init <shell>    Output shell integration (zsh / bash / fish)
dongle jump <query>    Print #1 best-matching directory path
dongle root            Print the project root for the current directory
dongle recent          Show pinned & recently visited directories
dongle pin [dir]       Pin or unpin a directory (default: current directory)
dongle prune           Remove deleted directories from frecency & bookmarks
dongle scan            Scan the current directory
dongle list            List all discovered paths
dongle doctor          Diagnose installation issues
dongle version         Show version
\`\`\`

---

## Features

- **⚡ Native C++17 Engine (`<2ms` startup)**: Single `156 KB` Mach-O/ELF binary compiled with `clang++ -O3`. Zero runtime dependencies, zero terminal lag.
- **🔭 Developer Preview HUD (`Ctrl+V`)**: Shows active Git branch, latest commit message, automatic tech stack badges (`🦀 Rust`, `💙 Flutter`, `📦 Node/TS`, `🐍 Python`, `🐹 Go`, `⚡ C/C++`), file counts, and `README.md` snippet.
- **🌲 Tree Drill-Down & Parent Climbing (`←` / `→`)**: Climb above your project root with `←` (`Ctrl+H`) or drill deep into any folder with `→` (`Ctrl+L`).
- **🧠 Automatic `cd` Frecency + Bookmarks (`★`)**: Automatically learns from every `cd` in your shell (`chpwd` hook) and lets you pin favorite folders with `Ctrl+B` or `dgpin`.
- **🛠️ Action Menu (`Tab`) & Mkdir on the Fly (`Ctrl+Y`)**: Open directories directly in Cursor/VS Code, reveal in Finder, copy paths to clipboard, or create missing directories on the fly.

---

## License

MIT — free to use, modify, and distribute.
