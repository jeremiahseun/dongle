<img width="256" height="200" alt="dongle" src="https://github.com/user-attachments/assets/c58d6923-0c32-4d6e-9897-8d422b321033" />

# Dongle

> **Lightning-fast fuzzy directory navigation — for any terminal.**

No more \`cd ../../some/deep/nested/folder\`. Press \`/\` and search.

\`\`\`
  Project  ~/my-project  (42 dirs)
  / src comp
  ❯ src/components/ui
    src/components/auth
    src/components/dashboard
    src/components/forms/inputs
    tests/components
  ─────────────────────────────────────────────────────────
  ↑↓ nav   Enter select   ^W workspace   ^R rescan   Esc cancel
\`\`\`

Press **Enter**. You're there.

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
- Detects your OS (macOS / Linux) and architecture (ARM64 / x64)
- Downloads a **single self-contained binary** compiled in Dart (no dependencies needed)
- Adds \`dongle\` to your PATH
- Wires up shell integration in \`~/.zshrc\`, \`~/.bashrc\`, or \`~/.config/fish/config.fish\`

Reload your shell and start using \`/\`.

### Platform support

| Platform | Status |
|----------|--------|
| macOS (Apple Silicon) | ✅ Full support |
| macOS (Intel) | ✅ Full support |
| Linux (x64) | ✅ Full support |
| Linux (ARM64) | 🔜 Coming soon |
| Windows (WSL) | ✅ Works via WSL |
| Windows (native) | 🔜 On the roadmap |

---

## How to use

### The basics

| What you do | What happens |
|-------------|-------------|
| Press \`/\` on an empty prompt | Open directory search |
| Press \`Ctrl+O\` anywhere | Open directory search (insert path at cursor) |
| Press \`Ctrl+/\` anywhere | Same as Ctrl+O |
| Type \`dg\` | Open directory search |
| Type \`dg <query>\` | Open search pre-filled with your query |
| Type \`dgw\` | Search across **all your projects** (workspace mode) |
| Type \`dgr\` | Jump to project root instantly — no picker |
| Type \`dgl\` | List all cached paths in the current project |
| Type \`dgs\` | Re-scan and refresh the cache |
| Type \`dgrecent\` | Show recently visited directories |

### Inside the picker

| Key | Action |
|-----|--------|
| Type anything | Filter results live |
| \`↑\` / \`↓\` or \`Ctrl+P\` / \`Ctrl+N\` | Move selection |
| \`Enter\` | Navigate to selected directory |
| \`Ctrl+W\` | Switch to workspace search without closing |
| \`Ctrl+R\` | Rescan the directory tree (refresh cache) |
| \`Ctrl+U\` | Clear the current query |
| \`Esc\` / \`Ctrl+C\` | Cancel |

### Commands

\`\`\`
dongle init <shell>    Output shell integration (bash / zsh / fish)
dongle root            Print the project root for the current directory
dongle recent          Show recently visited directories
dongle scan            Pre-scan and cache the current directory
dongle list            List all cached paths
dongle doctor          Diagnose installation issues
dongle version         Show version
\`\`\`

---

## Features

### Google-style live search
Results update on every keystroke. The picker stays open until you confirm or cancel — no flickering, no full-screen takeover.

### Smart fuzzy matching
- **Exact substring** — \`comp\` finds \`src/components\` before anything fuzzier
- **Segment bonus** — \`android\` gives a huge boost when the path has an \`/android/\` segment
- **Character sequence** — \`scu\` still finds \`src/components/ui\` as a fallback
- **Match highlighting** — the matched portion lights up in the results list

### Frecency — it learns what you use
Every directory you navigate to is tracked by **frequency × recency**. When you open the picker with no query, your most-visited and most-recently-used directories float to the top automatically. The more you use Dongle, the smarter it gets.

### Smart project root detection
Dongle always searches from your **project root**, not just \`\$PWD\`. If you're deep inside \`ios/src/views/\`, you can still find \`android/\` — Dongle walks upward and finds your \`.git\`, \`package.json\`, \`Cargo.toml\`, \`pubspec.yaml\`, etc.

### Workspace search
Set workspaces in your \`~/.config/dongle/config.yaml\` file and \`dgw\` searches across all your projects at once.

Press \`Ctrl+W\` inside any local search to switch to workspace mode on the fly.

### \`.gitignore\` aware
Dongle reads your \`.gitignore\` and a project-local \`.dongleignore\` file. \`node_modules\`, \`dist\`, \`build\`, and other noise are never shown.

### Instant startup — zero terminal slowdown
Shell integration loads in **under 100 ms** — you'll never notice it. Dongle itself is compiled in Dart ahead-of-time (AOT), allowing the picker to open and interact in sub-10ms times.

---

## Configuration

All settings are optional — Dongle works out of the box.

Create or edit \`~/.config/dongle/config.yaml\`:

\`\`\`yaml
# Dongle Configuration

# Cache lifetime in seconds (default: 300 = 5 minutes)
cache_ttl: 300

# How deep to scan inside a project (default: 6)
max_depth: 6

# How deep to scan inside workspace roots (default: 4)
workspace_depth: 4

# Maximum number of directories to index (default: 5000)
max_dirs: 5000

# Directories to search in workspace mode (dgw)
workspaces:
  - ~/Documents/GitHub
  - ~/Projects

# Extra directories to skip
skip_dirs:
  - tmp
  - .output
\`\`\`

### Custom ignore patterns

Create a \`.dongleignore\` file in any project root — same syntax as \`.gitignore\`:

\`\`\`
# .dongleignore
generated/
*.tmp
fixtures/large
\`\`\`

---

## Skipped by default

Dongle never shows: \`.git\`, \`node_modules\`, \`__pycache__\`, \`dist\`, \`build\`,
\`.next\`, \`.nuxt\`, \`venv\`, \`.venv\`, \`.tox\`, \`target\`, \`vendor\`, \`.idea\`,
\`.vscode\`, \`coverage\`, \`.mypy_cache\`, \`.pytest_cache\`, and more.

---

## Performance

Dongle is designed to stay out of your way. Completely rewritten in Dart for pure AOT compilation performance.

| Scenario | Time |
|----------|------|
| Shell startup (\`dongle init\`) | < 100 ms |
| Search — 100 paths | < 1 ms |
| Search — 500 paths | < 1 ms |
| Search — 1 000 paths | < 1 ms |
| Search — 5 000 paths | ~5 ms |

Cache hits are instant. Background scans never block your prompt.

---

## Why Dongle?

| Tool | What it does |
|------|-------------|
| \`cd\` | Manual path typing — tedious for deep trees |
| \`autojump\` / \`zoxide\` | Learns from history — great, but needs training time |
| \`fzf\` | General-purpose fuzzy finder — powerful but requires extra setup |
| **Dongle** | Instant visual project search + frecency, zero config, works on first run |

Dongle is not trying to replace any of these — it's focused on one thing: **get to a directory inside your project, fast, visually, with no training period.**

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features including File Previews, Action Menus (\`Tab\` → open in VS Code / Finder), and native Windows support.

---

## Contributing

\`\`\`sh
git clone https://github.com/jeremiahseun/dongle
cd dongle
dart pub get
dart compile exe bin/app.dart -o build/dongle
\`\`\`

Please open an issue before starting large features.

---

## License

MIT — free to use, modify, and distribute.
