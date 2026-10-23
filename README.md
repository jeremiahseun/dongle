<img width="256" height="200" alt="dongle" src="https://github.com/user-attachments/assets/c58d6923-0c32-4d6e-9897-8d422b321033" />

# Dongle ⚡

> **Instant (`<2ms`) native bidirectional fuzzy directory navigation — for any terminal.**

No more `cd ../../../some/other/folder` or `cd src/deep/nested/folder`. Press `/` and search **both up and down** your directory tree simultaneously.

```
  Up+Down ⇅  ~/GitHub/dongle  (68 dirs · 12↓ 56↑)
  / comp
  ❯ ★ src/components/ui         │ 📁 ui (main)
      src/components/auth       │  2 dirs, 5 files · 📦 Node/TS
    ↑ ../design-system/comp     │   commit: feat: add button variants
    ↑ ../../shared/components   │   ▸ buttons/
                                │   ▸ modals/
                                │   • Button.tsx
  ─────────────────────────────────────────────────────────
  ↑↓ nav  Enter cd  Tab actions  ^S scope(⇅/↓/↑)  ^H/^L up/in  ^B pin  ^V preview  ^W ws  ^Y mkdir  Esc
```

Press **Enter** to jump there — or press **Tab** to open in Cursor/VS Code, reveal in Finder, copy the path, or create a folder on the fly.

---

## Demo

https://github.com/user-attachments/assets/43702b03-e262-4154-a566-f1e46d771dc0



---

## Install

### One command (recommended)

```bash
curl -sSL https://raw.githubusercontent.com/jeremiahseun/dongle/main/install.sh > install_dongle.sh && bash install_dongle.sh && rm install_dongle.sh
```

That's it. The installer:
- Compiles or downloads the **156 KB Native C++17 binary** — zero Python overhead, zero dependencies, `<2ms` startup
- Automatically **imports your existing `cd` history** from `~/.zsh_history`, `~/.bash_history`, and `fish_history` so Dongle knows your favorite directories from day one
- Adds `~/.dongle/bin` to your `PATH`
- Wires up instant shell integration in `~/.zshrc`, `~/.bashrc`, or `~/.config/fish/config.fish`

Reload your shell (`source ~/.zshrc`) and press `/`.

---

## How to use

### Shell Shortcuts & Directional Search

By default, Dongle searches **5 layers deep** inside your current directory (`↓`) **AND 4 layers above** (`↑` parent/ancestor and sibling directories) at the same time.

| What you do | What happens |
|-------------|-------------|
| Press `/` on an empty prompt | Open live **Up + Down (`⇅`)** directory search |
| Press `Ctrl+O` or `Ctrl+/` anywhere | Open directory search (inserts escaped path at cursor if prompt non-empty) |
| Type `dg` | Open interactive **Up + Down (`⇅`)** directory search |
| Type `dg <name>` or `dgj <name>` | **Smart Verified Jump**: jumps immediately if `<name>` matches an **exact** folder name (checking down first, then up). If no exact folder name exists, opens the interactive TUI with ranked up/down suggestions so you never land in the wrong place! |
| Type `dg up [query]` or `dgu [query]` | Search **only upward (`↑`)** 3–5 layers above current directory |
| Type `dg down [query]` or `dgd [query]` | Search **only downward (`↓`)** 3–5 layers inside current directory |
| Type `dgw` | Search across **all your projects** (workspace mode) |
| Type `dgr` | Jump to project root instantly — no picker |
| Type `dgpin` | Pin / unpin (`★`) the current directory |
| Type `dgl` | List all discovered up & down paths around current directory |
| Type `dgrecent` | Show pinned & recently visited directories |

### Inside the Picker

| Key / Input | Action |
|-------------|--------|
| Type anything | Filter results live across both downward and upward (`↑ ../`) directories |
| Type `up <query>` or `u:<query>` | Dynamically restrict search to **Upward (`↑`)** directories only |
| Type `down <query>` or `d:<query>` | Dynamically restrict search to **Downward (`↓`)** directories only |
| `Ctrl+S` | Cycle search scope live: **Up+Down (`⇅`)** → **Down only (`↓`)** → **Up only (`↑`)** |
| `↑` / `↓` or `Ctrl+P` / `Ctrl+N` | Move selection |
| `Enter` | Navigate (`cd`) to selected directory |
| `←` / `→` or `Ctrl+H` / `Ctrl+L` | **Climb up (`..`)** to parent directory or **drill into** selected folder as new root |
| `Tab` | Open **Action Menu** (`[e]` Cursor/VS Code, `[o]` Finder, `[y]` Copy path, `[p]` Pin, `[n]` Mkdir) |
| `Ctrl+B` | Pin / Unpin selected directory (`★` floats to top) |
| `Ctrl+V` | Toggle live right-pane Developer Preview HUD |
| `Ctrl+Y` | **Create new directory (`mkdir -p`)** from current query and `cd` into it |
| `Ctrl+W` | Toggle between Local (Up+Down) and Global Workspace search without closing |
| `Ctrl+R` | Rescan the directory tree |
| `Ctrl+U` | Clear the current query |
| `Esc` / `Ctrl+C` | Cancel |

### CLI Commands

```
dongle                   Show welcome banner & quick-start guide
dongle up [query]        Search only upward (3-5 layers above current dir)
dongle down [query]      Search only downward (3-5 layers inside current dir)
dongle jump <query>      Smart jump: auto-jumps on exact match, else opens suggestions TUI
dongle import-history    Import past `cd` commands from zsh/bash/fish history
dongle init <shell>      Output shell integration (zsh / bash / fish)
dongle root              Print the project root for the current directory
dongle recent            Show pinned & recently visited directories
dongle pin [dir]         Pin or unpin a directory (default: current directory)
dongle prune             Remove deleted directories from frecency & bookmarks
dongle scan              Scan the current directory
dongle list [--up|--down] List discovered paths (both, up-only, or down-only)
dongle doctor            Diagnose installation issues
dongle version           Show version
```

---

## Features

- **⚡ Native C++17 Engine (`<2ms` startup)**: Single `156 KB` Mach-O/ELF binary compiled with `clang++ -O3`. Zero runtime dependencies, zero terminal lag.
- **⇅ Bidirectional 3–5 Layer Search (Up & Down)**: Searches 5 layers deep inside your current folder AND 4 layers above (`..`, `../..`, `../../..`, `../../../..` and sibling trees) simultaneously. Filter direction anytime with `dg up`, `dg down`, `Ctrl+S`, or inline `up ` / `down ` prefixes.
- **🎯 Verified Exact-Name Jump + Fallback Suggestions (`dg` & `dgj`)**: Never jump blindly into the wrong directory again. `dg <query>` and `dgj <query>` verify that an exact folder name match exists (prioritizing downward over upward) before auto-jumping; otherwise, they automatically open the interactive suggestion list from your current location up and down.
- **🕰️ Instant Shell History Learning (`dongle import-history`)**: Automatically parses `~/.zsh_history`, `~/.bash_history`, and `fish_history` on first run so Dongle already knows your most-visited directories without starting from scratch, plus learns from every new `cd` via shell hooks.
- **🔭 Developer Preview HUD (`Ctrl+V`)**: Shows active Git branch, latest commit message, automatic tech stack badges (`🦀 Rust`, `💙 Flutter`, `📦 Node/TS`, `🐍 Python`, `🐹 Go`, `⚡ C/C++`), file counts, and `README.md` snippet.
- **🛠️ Action Menu (`Tab`) & Mkdir on the Fly (`Ctrl+Y`)**: Open directories directly in Cursor/VS Code, reveal in Finder, copy paths to clipboard, or create missing directories on the fly.

---

## License

MIT — free to use, modify, and distribute.
