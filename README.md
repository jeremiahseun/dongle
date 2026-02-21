<img width="256" height="200" alt="dongle" src="https://github.com/user-attachments/assets/c58d6923-0c32-4d6e-9897-8d422b321033" />

# Dongle

> **Fast, fuzzy directory navigation — for any terminal, any user.**

No more `cd ../../some/deep/nested/folder`. Just press `/` and search.

```
  Dongle  in ~/my-project
  / src comp                          ← you type this
  ──────────────────────────────────
  ❯ src/components/ui                 ← highlighted selection
    src/components/auth
    src/components/dashboard
    src/components/forms/inputs
    tests/components
```

Press Enter. You're there.

---

## Features

- **Google-style live search** — results update as you type
- **Fuzzy matching** — `src/comp` finds `src/components/Button`
- **Any terminal** — works in bash, zsh, fish, and more
- **Fast** — scans and caches paths in milliseconds
- **Not just for developers** — works anywhere you have files
- **Zero config** — one install command, one line in your rc file
- **Lightweight** — pure Python, one dependency (`prompt_toolkit`)

---

## Install

**One-liner:**
```bash
curl -sSL https://raw.githubusercontent.com/yourusername/dongle/main/install.sh | bash
```

**Or via pip:**
```bash
pip install dongle
```

Then add to your shell config:

```bash
# Bash (~/.bashrc)
eval "$(dongle init bash)"

# Zsh (~/.zshrc)
eval "$(dongle init zsh)"

# Fish (~/.config/fish/config.fish)
dongle init fish | source
```

Reload your shell and you're done.

> **Note on Standalone Binaries:** We are currently migrating to fully standalone executables. Soon you will not even need Python installed to use Dongle!

---

## Usage

| Action | Result |
|--------|--------|
| Press `/` on an empty prompt | Open directory search in current folder |
| Press `Ctrl+/` anywhere | Open directory search (insert path at cursor) |
| Type `dg` | Same as pressing / |
| Type `dgw` | Open **Workspace Search** (search across multiple projects) |
| Type `dgs` | Pre-scan and cache the current directory |
| `dongle-pick ~/projects/myapp` | Search from a specific root |
| `dongle-scan` | Warm the cache for current directory |

### Navigation inside the picker

| Key | Action |
|-----|--------|
| Type | Filter results live |
| `↑` / `↓` or `Ctrl+P` / `Ctrl+N` | Move selection |
| `Tab` / `Shift+Tab` | Move selection |
| `Enter` | Navigate to selected path |
| `Esc` or `Ctrl+C` | Cancel |

---

## How it works

1. **On activation**, Dongle quickly walks your current directory tree (skipping `node_modules`, `.git`, build artifacts, etc.)
2. **Paths are cached** for 5 minutes so repeated searches are instant
3. **Fuzzy search** scores results by how well they match — exact substrings rank highest, then character sequence matches
4. **The shell integration** handles the actual `cd` so Dongle works with any shell that supports keybindings

---

## Configuration

Dongle works out of the box, but you can customize by setting environment variables:

```bash
export DONGLE_WORKSPACES="~/Documents/GitHub,~/Projects" # Folders to search when using dgw
export DONGLE_MAX_DEPTH=8       # how deep to scan (default: 6)
export DONGLE_MAX_DIRS=10000    # max directories to index (default: 5000)
export DONGLE_CACHE_TTL=600     # cache lifetime in seconds (default: 300)
export DONGLE_SKIP_DIRS="dist,build,tmp"  # extra dirs to skip
```

---

## Skipped directories

By default, Dongle skips:
`.git`, `node_modules`, `__pycache__`, `dist`, `build`, `.next`, `.nuxt`, `venv`, `.venv`, `target`, `vendor`, `.idea`, `.vscode`, and other common noise directories.

---

## Why Dongle?

| Tool | What it does |
|------|-------------|
| `cd` | Manual path typing — tedious for deep trees |
| `autojump` / `zoxide` | Learns from history — great but needs training |
| `fzf` | General fuzzy finder — powerful but requires setup |
| **Dongle** | Instant visual search from your current root — no training needed |

Dongle is **not** trying to replace any of these — it's a focused tool for one thing: getting to a path within a project quickly and visually.

---

## Roadmap

Dongle is continuously evolving. Check out [ROADMAP.md](ROADMAP.md) to see planned features like File Previews, Windows Support, and Action Menus!

---

## Contributing

Dongle is open source and welcomes contributions!

```bash
git clone https://github.com/yourusername/dongle
cd dongle
pip install -e ".[dev]"
```

Please open an issue before starting large features.

---

## License

MIT — free to use, modify, and distribute.
