# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-10-23
### Added
- **Bidirectional Up + Down Search (3–5 Layers Deep & Above)**: Normal search (`/`, `dg`, `dgj`) now scans 5 layers deep inside your current directory (`↓`) **and** 4 layers above (`↑` parent/ancestor and sibling trees) around `$PWD`. Upward directories are badged with `↑ ../...` for instant visual clarity.
- **Directional Commands & Inline Scope Filters (`up` / `down`)**:
  - Shell shortcuts: `dg up [query]` (`dgu`) to search only upward, and `dg down [query]` (`dgd`) to search only downward.
  - Inline query prefixes: type `up <query>` (`u:<query>`) or `down <query>` (`d:<query>`) directly inside the interactive search bar to filter direction on the fly.
  - Live TUI toggle: press `Ctrl+S` inside the picker to cycle between `Up+Down ⇅`, `Down ↓`, and `Up ↑`.
- **Verified Exact-Name Jump + Fallback Suggestions (`dg` & `dgj`)**: Unified `dg <query>` and `dgj <query>` so they only jump immediately without opening the TUI when an **unambiguous exact folder name match** is found (prioritizing downward matches, then upward matches). When no exact match exists (or multiple folders share the name), Dongle opens the interactive TUI pre-filled with your query and shows ranked up/down suggestions instead of jumping to a wrong destination.
- **Automatic Shell `cd` History Bootstrap (`dongle import-history`)**: Dongle now parses `~/.zsh_history`, `~/.bash_history`, and `~/.local/share/fish/fish_history` to learn from your historical `cd` commands automatically on first run (or anytime via `dongle import-history`), so frecency works immediately without starting from scratch.

## [0.6.0] - 2026-10-23
### Added
- **Native C++17 Engine (`src/dongle.cpp`)**: Rebuilt the entire scanner, matcher, frecency engine, and interactive TUI in zero-dependency C++17 (`clang++ -O3`). Startup + directory scan time dropped from ~6.1 seconds (PyInstaller) to **<4 milliseconds** (156 KB binary).
- **Tree Drill-Down & Parent Climbing (`←` / `→` or `Ctrl+H` / `Ctrl+L`)**: Climb up to the parent directory (`..`) or lock into the highlighted folder as the new search root without leaving the picker.
- **Automatic `cd` Frecency Tracking (`chpwd` / `PROMPT_COMMAND`)**: Automatically records every directory you visit in your terminal so frecency rankings always reflect your real workflow.
- **Create Directory on the Fly (`Ctrl+Y` / `Tab -> n`)**: Create a new directory directly from your search query (`mkdir -p`) and `cd` into it immediately.
- **Rich Developer Preview HUD (`Ctrl+V`)**: Displays active Git branch, latest commit message (from `.git/logs/HEAD`), automatic tech stack badges (`🦀 Rust`, `💙 Flutter`, `📦 Node/TS`, `🐍 Python`, `🐹 Go`, `⚡ C/C++`), file/folder counts, and `README.md` snippet.
- **Interactive Action Menu (`Tab`)**: Open in Cursor / VS Code (`e`), reveal in Finder (`o`), copy path to clipboard (`y`), pin/unpin (`p`), or create folder (`n`).
- **Directory Bookmarks / Pinning (`Ctrl+B`, `dongle pin`, `dgpin`) & Pruning (`dongle prune`)**: Pin favorite directories (`★`) to the top of results and prune deleted directories.
- **First-Time Welcome Banner (`dongle welcome`)**: Styled onboarding screen shown upon installation and when running `dongle`.

## [0.2.9] - 2026-02-24
### Changed
- Increased the search limit from 8 to 50 results in interactive picker.
- Implemented scrolling in the results list, keeping the TUI size identical but allowing users to navigate through all 50 results.

## [0.2.8] - 2026-02-24
### Fixed
- Fixed an issue in `dgw` workspace scanning where cached `tuples` were deserialized from JSON as `lists`, leading to an `AttributeError` when splitting paths. Now handles both correctly.

## [0.2.7] - 2026-02-14
### Added
- Feature updates and stability improvements for the fuzzy finder.
- Included multi-workspace mode `dgw`.
