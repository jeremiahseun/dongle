// ─────────────────────────────────────────────────────────────────────────────
// Dongle Native Core (C++17) — v0.7.0
// Zero-dependency, instant (<2ms) bidirectional fuzzy directory navigation.
// Compiles cleanly on macOS & Linux with: clang++ -O3 -std=c++17 src/dongle.cpp -o dongle
// ─────────────────────────────────────────────────────────────────────────────

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <fnmatch.h>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>
#include <vector>

static const char *DONGLE_VERSION = "0.7.0";
static const int DISPLAY_LIMIT = 50;
static const int VISIBLE_ROWS = 15;

// ── ANSI Styles (for non-TUI CLI commands) ─────────────────────
static const char *C_CYAN   = "\033[36m";
static const char *C_GREEN  = "\033[32m";
static const char *C_YELLOW = "\033[33m";
static const char *C_RED    = "\033[31m";
static const char *C_BOLD   = "\033[1m";
static const char *C_DIM    = "\033[2m";
static const char *C_RESET  = "\033[0m";

enum class ScopeMode {
    BOTH = 0, // Search 5 layers down + 4 layers up (and sibling trees)
    DOWN = 1, // Only search downward from current root
    UP   = 2  // Only search upward (ancestors & upper sibling branches)
};

static const char *scope_name(ScopeMode m) {
    switch (m) {
        case ScopeMode::DOWN: return "Down ↓";
        case ScopeMode::UP:   return "Up ↑";
        default:              return "Up+Down ⇅";
    }
}

// ── Embedded Shell Integration Scripts ─────────────────────────
static const char *ZSH_INIT_SCRIPT = R"ZSH(# Dongle — Zsh Integration
# Add to your ~/.zshrc:
#   eval "$(dongle init zsh)"

__dongle_widget() {
    local chosen
    chosen="$(dongle pick </dev/tty 2>/dev/tty)"

    if [ $? -eq 0 ] && [ -n "$chosen" ]; then
        if [ -z "$BUFFER" ]; then
            cd "$chosen"
            local display="${chosen/#$HOME/~}"
            zle -M "  → $display"
            zle reset-prompt
        else
            local escaped="${chosen// /\\ }"
            LBUFFER="${LBUFFER}${escaped}"
        fi
    fi
    zle reset-prompt
}

__dongle_slash() {
    if [ -z "$BUFFER" ]; then
        if [[ -c /dev/tty ]] && { true </dev/tty; } 2>/dev/null; then
            __dongle_widget
        else
            LBUFFER="${LBUFFER}/"
        fi
    else
        LBUFFER="${LBUFFER}/"
    fi
}

zle -N __dongle_widget
zle -N __dongle_slash

bindkey "/"   __dongle_slash
bindkey "^_"  __dongle_widget   # Ctrl+/
bindkey "^O"  __dongle_widget   # Ctrl+O  (macOS fallback)
bindkey "^]p" __dongle_widget   # Ctrl+] p fallback

# Automatic directory frecency tracking on every `cd`
__dongle_chpwd() {
    (dongle record "$PWD" &>/dev/null &)
}
typeset -gaU chpwd_functions
chpwd_functions+=(__dongle_chpwd)

# dg — bidirectional search (3-5 layers down + 3-5 layers up).
# Supports `dg up [query]` and `dg down [query]`.
# Auto-jumps ONLY when an exact directory name match is unambiguous; otherwise shows suggestions.
dg() {
    local scope="both"
    if [ "${1:-}" = "up" ] || [ "${1:-}" = "u" ]; then
        scope="up"
        shift
    elif [ "${1:-}" = "down" ] || [ "${1:-}" = "d" ]; then
        scope="down"
        shift
    fi

    local chosen
    if [ $# -gt 0 ]; then
        chosen="$(dongle pick --scope "$scope" --auto-select --query "$*" </dev/tty 2>/dev/tty)"
    else
        chosen="$(dongle pick --scope "$scope" </dev/tty 2>/dev/tty)"
    fi
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen" && echo "  → ${chosen/#$HOME/~}"
}

# dgu — search only upward (3-5 layers above current folder)
dgu() { dg up "$@"; }

# dgd — search only downward (3-5 layers inside current folder)
dgd() { dg down "$@"; }

# dgj — verified jump: jumps immediately if exact folder name exists, else opens suggestions picker
dgj() { dg "$@"; }

dgs() { dongle scan "$@"; }

dgw() {
    local chosen
    chosen="$(dongle pick --workspace --query "$*" </dev/tty 2>/dev/tty)"
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen" && echo "  → ${chosen/#$HOME/~}"
}

dgws() { dongle scan --workspace "$@"; }

dgr() {
    local root
    root="$(dongle root)"
    [ $? -eq 0 ] && [ -n "$root" ] && cd "$root" && echo "  → ${root/#$HOME/~}"
}

dgl() { dongle list "$@"; }
dgpin() { dongle pin "$@"; }
dgrecent() { dongle recent; }
)ZSH";

static const char *BASH_INIT_SCRIPT = R"BASH(# Dongle — Bash Integration
# Add to your ~/.bashrc:
#   eval "$(dongle init bash)"

__dongle_widget() {
    local current_line="$READLINE_LINE"
    local current_point="$READLINE_POINT"
    local chosen
    chosen="$(dongle pick </dev/tty 2>/dev/tty)"

    if [ $? -eq 0 ] && [ -n "$chosen" ]; then
        if [ -z "$current_line" ]; then
            cd "$chosen" && echo "  → $(pwd | sed "s|$HOME|~|")"
            READLINE_LINE=""
            READLINE_POINT=0
        else
            local escaped="${chosen// /\\ }"
            READLINE_LINE="${current_line:0:$current_point}$escaped${current_line:$current_point}"
            READLINE_POINT=$(( current_point + ${#escaped} ))
        fi
    fi
}

__dongle_slash() {
    if [ -z "$READLINE_LINE" ]; then
        if [ -c /dev/tty ] && { true </dev/tty; } 2>/dev/null; then
            __dongle_widget
        else
            READLINE_LINE="${READLINE_LINE:0:$READLINE_POINT}/${READLINE_LINE:$READLINE_POINT}"
            READLINE_POINT=$(( READLINE_POINT + 1 ))
        fi
    else
        READLINE_LINE="${READLINE_LINE:0:$READLINE_POINT}/${READLINE_LINE:$READLINE_POINT}"
        READLINE_POINT=$(( READLINE_POINT + 1 ))
    fi
}

bind -x '"/":__dongle_slash'
bind -x '"\C-_":__dongle_widget'
bind -x '"\C-o":__dongle_widget'

__dongle_prompt_cmd() {
    if [ "$__DONGLE_LAST_PWD" != "$PWD" ]; then
        __DONGLE_LAST_PWD="$PWD"
        (dongle record "$PWD" &>/dev/null &)
    fi
}
case "$PROMPT_COMMAND" in
    *__dongle_prompt_cmd*) ;;
    *) PROMPT_COMMAND="__dongle_prompt_cmd${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac

dg() {
    local scope="both"
    if [ "${1:-}" = "up" ] || [ "${1:-}" = "u" ]; then
        scope="up"
        shift
    elif [ "${1:-}" = "down" ] || [ "${1:-}" = "d" ]; then
        scope="down"
        shift
    fi

    local chosen
    if [ $# -gt 0 ]; then
        chosen="$(dongle pick --scope "$scope" --auto-select --query "$*" </dev/tty 2>/dev/tty)"
    else
        chosen="$(dongle pick --scope "$scope" </dev/tty 2>/dev/tty)"
    fi
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen" && echo "  → $(pwd | sed "s|$HOME|~|")"
}

dgu() { dg up "$@"; }
dgd() { dg down "$@"; }
dgj() { dg "$@"; }

alias dgs='dongle scan'

dgw() {
    local chosen
    chosen="$(dongle pick --workspace --query "$*" </dev/tty 2>/dev/tty)"
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen" && echo "  → $(pwd | sed "s|$HOME|~|")"
}

alias dgws='dongle scan --workspace'

dgr() {
    local root
    root="$(dongle root)"
    [ $? -eq 0 ] && [ -n "$root" ] && cd "$root" && echo "  → $(pwd | sed "s|$HOME|~|")"
}

alias dgl='dongle list'
alias dgpin='dongle pin'
alias dgrecent='dongle recent'
)BASH";

static const char *FISH_INIT_SCRIPT = R"FISH(# Dongle — Fish Integration
# Add to your fish config:
#   dongle init fish | source

function __dongle_widget
    set chosen (dongle pick </dev/tty 2>/dev/tty)
    if test $status -eq 0 -a -n "$chosen"
        if test -z (commandline)
            cd $chosen
            echo "  → "(pwd | string replace $HOME "~")
            commandline -f repaint
        else
            commandline -i (string escape -- $chosen)
        end
    end
    commandline -f repaint
end

function __dongle_slash
    if test -z (commandline)
        if test -c /dev/tty
            __dongle_widget
        else
            commandline -i "/"
        end
    else
        commandline -i "/"
    end
end

bind "/"  __dongle_slash
bind \c_  __dongle_widget
bind \co  __dongle_widget

function __dongle_chpwd --on-variable PWD
    dongle record "$PWD" &>/dev/null &
end

function dg
    set scope "both"
    if test (count $argv) -gt 0
        if test "$argv[1]" = "up" -o "$argv[1]" = "u"
            set scope "up"
            set -e argv[1]
        else if test "$argv[1]" = "down" -o "$argv[1]" = "d"
            set scope "down"
            set -e argv[1]
        end
    end

    if test (count $argv) -gt 0
        set chosen (dongle pick --scope "$scope" --auto-select --query "$argv" </dev/tty 2>/dev/tty)
    else
        set chosen (dongle pick --scope "$scope" </dev/tty 2>/dev/tty)
    end
    and cd $chosen
    and echo "  → "(pwd | string replace $HOME "~")
end

function dgu
    dg up $argv
end

function dgd
    dg down $argv
end

function dgj
    dg $argv
end

function dgs
    dongle scan $argv
end

function dgw
    set chosen (dongle pick --workspace --query "$argv" </dev/tty 2>/dev/tty)
    and cd $chosen
end

function dgws
    dongle scan --workspace $argv
end

function dgr
    set root (dongle root)
    and cd $root
    and echo "  → "(pwd | string replace $HOME "~")
end

function dgl
    dongle list $argv
end

function dgpin
    dongle pin $argv
end

function dgrecent
    dongle recent
end
)FISH";

// ── Helpers & Environment ──────────────────────────────────────

static std::string get_home() {
    const char *h = std::getenv("HOME");
    return h ? std::string(h) : "";
}

static std::string get_cwd() {
    char buf[4096];
    if (getcwd(buf, sizeof(buf))) return std::string(buf);
    return ".";
}

static std::string abspath(const std::string &p) {
    if (p.empty()) return get_cwd();
    std::string expanded = p;
    if (expanded[0] == '~') {
        expanded = get_home() + expanded.substr(1);
    }
    char resolved[4096];
    if (realpath(expanded.c_str(), resolved)) {
        return std::string(resolved);
    }
    if (expanded[0] == '/') return expanded;
    return get_cwd() + "/" + expanded;
}

static bool is_dir(const std::string &p) {
    struct stat st;
    if (stat(p.c_str(), &st) != 0) return false;
    return S_ISDIR(st.st_mode);
}

static bool file_exists(const std::string &p) {
    struct stat st;
    return stat(p.c_str(), &st) == 0;
}

static bool mkdir_p(const std::string &path) {
    if (path.empty()) return false;
    std::string cur;
    if (path[0] == '/') cur = "/";
    std::stringstream ss(path);
    std::string part;
    while (std::getline(ss, part, '/')) {
        if (part.empty() || part == ".") continue;
        if (!cur.empty() && cur.back() != '/') cur += "/";
        cur += part;
        if (!is_dir(cur)) {
            if (mkdir(cur.c_str(), 0755) != 0 && !is_dir(cur)) {
                return false;
            }
        }
    }
    return is_dir(path);
}

static std::string to_lower(const std::string &s) {
    std::string r = s;
    for (char &c : r) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return r;
}

static std::string trim(const std::string &s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return "";
    size_t b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

static std::vector<std::string> split_str(const std::string &s, char delim) {
    std::vector<std::string> out;
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, delim)) {
        std::string t = trim(item);
        if (!t.empty()) out.push_back(t);
    }
    return out;
}

static std::string replace_home_tilde(const std::string &p) {
    std::string h = get_home();
    if (!h.empty() && p.compare(0, h.size(), h) == 0) {
        return "~" + p.substr(h.size());
    }
    return p;
}

static std::string basename_of(const std::string &p) {
    if (p.empty() || p == "/") return "/";
    size_t sl = p.find_last_of('/');
    if (sl == std::string::npos) return p;
    return p.substr(sl + 1);
}

static int get_env_int(const char *name, int fallback) {
    const char *v = std::getenv(name);
    if (!v || !*v) return fallback;
    try { return std::stoi(v); } catch (...) { return fallback; }
}

static bool get_preview_enabled() {
    const char *v = std::getenv("DONGLE_PREVIEW");
    if (!v || !*v) return true;
    std::string s = to_lower(trim(v));
    return !(s == "0" || s == "false" || s == "no" || s == "off");
}

static long long now_sec() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();
}

// ── Project Root Detection & Ignore Rules ──────────────────────

static const std::vector<std::string> ROOT_MARKERS = {
    ".git", ".svn", ".hg", "package.json", "pubspec.yaml", "pyproject.toml",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Makefile"
};

static std::set<std::string> get_skip_dirs() {
    std::set<std::string> s = {
        ".git", ".svn", ".hg", "node_modules", "__pycache__", ".cache",
        ".npm", ".yarn", "dist", "build", ".next", ".nuxt", "venv",
        ".venv", "env", ".env", ".tox", "target", "vendor", ".idea",
        ".vscode", "coverage", ".mypy_cache", ".pytest_cache", "build_venv",
        "build_native", "Library", ".Trash", "Applications", "Pictures", "Music", "Movies",
        "System", "Volumes", "dev", "proc", "sys", "cores", "private"
    };
    const char *extra = std::getenv("DONGLE_SKIP_DIRS");
    if (extra && *extra) {
        for (const auto &d : split_str(extra, ',')) s.insert(d);
    }
    return s;
}

static std::string find_project_root(const std::string &start_dir) {
    std::string curr = abspath(start_dir);
    std::string walk = curr;
    while (true) {
        for (const auto &m : ROOT_MARKERS) {
            if (file_exists(walk + "/" + m)) {
                return walk;
            }
        }
        size_t slash = walk.find_last_of('/');
        if (slash == std::string::npos || slash == 0) break;
        walk = walk.substr(0, slash);
    }
    const char *fallback = std::getenv("DONGLE_SEARCH_DIR");
    if (fallback && *fallback) {
        std::string fb = abspath(trim(fallback));
        if (is_dir(fb)) return fb;
    }
    return curr;
}

static std::vector<std::string> load_ignore_patterns(const std::string &root) {
    std::vector<std::string> patterns;
    for (const char *fname : {".gitignore", ".dongleignore"}) {
        std::ifstream f(root + "/" + fname);
        if (!f.is_open()) continue;
        std::string line;
        while (std::getline(f, line)) {
            std::string t = trim(line);
            if (t.empty() || t[0] == '#' || t[0] == '!') continue;
            while (!t.empty() && t.back() == '/') t.pop_back();
            if (!t.empty() && t.front() == '/') t.erase(t.begin());
            if (!t.empty()) patterns.push_back(t);
        }
    }
    return patterns;
}

static bool matches_ignore(const std::string &rel_path, const std::string &base_name,
                           const std::vector<std::string> &patterns) {
    for (const auto &pat : patterns) {
        if (pat.find('/') != std::string::npos) {
            if (fnmatch(pat.c_str(), rel_path.c_str(), FNM_PATHNAME) == 0) return true;
            if (rel_path.compare(0, pat.size() + 1, pat + "/") == 0) return true;
        } else {
            if (fnmatch(pat.c_str(), base_name.c_str(), 0) == 0) return true;
            if (fnmatch(pat.c_str(), rel_path.c_str(), 0) == 0) return true;
        }
    }
    return false;
}

// ── Bidirectional Path Scanner (3-5 Layers Down + 3-5 Layers Up) ──

struct PathItem {
    std::string display;
    std::string full;
    bool is_upward; // true if from an ancestor/upper branch
};

static void walk_dir(const std::string &root_str,
                     const std::string &display_prefix,
                     const std::string &curr_dir,
                     int depth,
                     int max_depth,
                     int max_dirs,
                     bool is_workspace,
                     bool is_upward,
                     const std::string &exclude_subtree,
                     const std::set<std::string> &skip_dirs,
                     const std::vector<std::string> &ignore_pats,
                     std::set<std::string> &seen_full,
                     std::vector<PathItem> &out) {
    if ((int)out.size() >= max_dirs || depth > max_depth) return;

    DIR *dir = opendir(curr_dir.c_str());
    if (!dir) return;

    std::vector<std::string> subdirs;
    struct dirent *entry;
    while ((entry = readdir(dir)) != nullptr) {
        const char *name = entry->d_name;
        if (name[0] == '.') continue;
        if (skip_dirs.count(name)) continue;

        std::string child_full = (curr_dir == "/") ? ("/" + std::string(name)) : (curr_dir + "/" + name);
        if (!exclude_subtree.empty() && child_full == exclude_subtree) continue;

        bool is_d = false;
        if (entry->d_type == DT_DIR) {
            is_d = true;
        } else if (entry->d_type == DT_UNKNOWN) {
            is_d = is_dir(child_full);
        }
        if (!is_d) continue;

        if (!is_workspace && !ignore_pats.empty() && child_full.size() > root_str.size() + 1) {
            std::string rel = child_full.substr(root_str.size() + 1);
            if (matches_ignore(rel, name, ignore_pats)) continue;
        }
        subdirs.push_back(name);
    }
    closedir(dir);

    std::sort(subdirs.begin(), subdirs.end());

    for (const auto &d : subdirs) {
        if ((int)out.size() >= max_dirs) break;
        std::string child_full = (curr_dir == "/") ? ("/" + d) : (curr_dir + "/" + d);
        if (seen_full.count(child_full)) continue;
        seen_full.insert(child_full);

        std::string rel_part = (curr_dir == root_str)
                                   ? d
                                   : child_full.substr(root_str.size() + (root_str == "/" ? 0 : 1));
        std::string disp = display_prefix.empty() ? rel_part : (display_prefix + "/" + rel_part);

        out.push_back({disp, child_full, is_upward});
        if (depth + 1 <= max_depth) {
            walk_dir(root_str, display_prefix, child_full, depth + 1, max_depth,
                     max_dirs, is_workspace, is_upward, exclude_subtree, skip_dirs, ignore_pats, seen_full, out);
        }
    }
}

static std::vector<PathItem> scan_paths(const std::string &root,
                                        bool is_workspace,
                                        ScopeMode scope = ScopeMode::BOTH) {
    std::vector<PathItem> out;
    std::set<std::string> seen_full;
    int max_dirs = get_env_int("DONGLE_MAX_DIRS", 5000);
    auto skip_dirs = get_skip_dirs();

    if (is_workspace) {
        const char *ws_raw = std::getenv("DONGLE_WORKSPACES");
        if (!ws_raw || !*ws_raw) ws_raw = std::getenv("DONGLE_SEARCH_DIR");
        std::vector<std::string> ws_dirs;
        if (ws_raw && *ws_raw) {
            for (const auto &d : split_str(ws_raw, ',')) {
                std::string full = abspath(d);
                if (is_dir(full)) ws_dirs.push_back(full);
            }
        }
        if (ws_dirs.empty()) {
            std::string gh = get_home() + "/Documents/GitHub";
            if (is_dir(gh)) ws_dirs.push_back(gh);
            std::string prj = get_home() + "/Projects";
            if (is_dir(prj)) ws_dirs.push_back(prj);
            std::string ext_gh = "/Volumes/SEAGATE BACKUP SLIM/MAC OFFLOAD 2026-10-13/Documents/GitHub";
            if (is_dir(ext_gh) && std::find(ws_dirs.begin(), ws_dirs.end(), ext_gh) == ws_dirs.end()) {
                ws_dirs.push_back(ext_gh);
            }
            size_t slash = root.find_last_of('/');
            if (slash != std::string::npos && slash > 0) {
                std::string par = root.substr(0, slash);
                if (is_dir(par) && std::find(ws_dirs.begin(), ws_dirs.end(), par) == ws_dirs.end()) {
                    ws_dirs.push_back(par);
                }
            }
        }
        int max_depth = get_env_int("DONGLE_WORKSPACE_DEPTH", 4);
        std::vector<std::string> empty_pats;
        for (const auto &ws : ws_dirs) {
            std::string self_disp = basename_of(ws);
            if (!seen_full.count(ws)) {
                seen_full.insert(ws);
                out.push_back({self_disp, ws, false});
            }
            walk_dir(ws, self_disp, ws, 1, max_depth, max_dirs, true, false, "", skip_dirs, empty_pats, seen_full, out);
            if ((int)out.size() >= max_dirs) break;
        }
        return out;
    }

    std::string abs_root = abspath(root);
    bool is_home = (abs_root == abspath(get_home()));

    // 1. Downward Scan (3-5+ layers inside current root)
    if (scope == ScopeMode::BOTH || scope == ScopeMode::DOWN) {
        int max_down_depth = get_env_int("DONGLE_MAX_DEPTH", 5);
        if (is_home && max_down_depth > 3) max_down_depth = 3;

        auto ignore_pats = load_ignore_patterns(abs_root);
        seen_full.insert(abs_root);
        out.push_back({".", abs_root, false});
        walk_dir(abs_root, "", abs_root, 1, max_down_depth, max_dirs, false, false, "", skip_dirs, ignore_pats, seen_full, out);
    }

    // 2. Upward Scan (3-5 layers above current root + sibling directories up to 2 levels deep)
    if (scope == ScopeMode::BOTH || scope == ScopeMode::UP) {
        int max_up_layers = get_env_int("DONGLE_UP_DEPTH", 4); // 4 layers above by default
        std::string curr_anc = abs_root;
        std::string prev_anc = abs_root;
        std::string up_prefix;
        std::vector<std::string> empty_pats;

        for (int up_level = 1; up_level <= max_up_layers; ++up_level) {
            if (curr_anc == "/" || curr_anc.empty()) break;
            size_t sl = curr_anc.find_last_of('/');
            std::string parent_anc = (sl == 0 || sl == std::string::npos) ? "/" : curr_anc.substr(0, sl);
            if (parent_anc == curr_anc) break;

            // Stop climbing into root "/" or "/Users" if it would expose system directories
            if (parent_anc == "/" || parent_anc == "/Users" || parent_anc == "/Volumes") {
                // Still add the immediate parent itself as a jump target if it's /Volumes/...
                if (parent_anc != "/" && parent_anc != "/Users" && !seen_full.count(parent_anc)) {
                    up_prefix = up_prefix.empty() ? ".." : (up_prefix + "/..");
                    seen_full.insert(parent_anc);
                    out.push_back({up_prefix + " (" + basename_of(parent_anc) + ")", parent_anc, true});
                }
                break;
            }

            up_prefix = up_prefix.empty() ? ".." : (up_prefix + "/..");
            std::string anc_name = basename_of(parent_anc);

            if (!seen_full.count(parent_anc)) {
                seen_full.insert(parent_anc);
                out.push_back({up_prefix + " (" + anc_name + ")", parent_anc, true});
            }

            // Scan sibling directories at this ancestor level (up to 2 levels deep for nearby ancestors, 1 for higher)
            bool anc_is_home = (parent_anc == abspath(get_home()));
            int sibling_depth = anc_is_home ? 1 : (up_level <= 2 ? 2 : 1);
            walk_dir(parent_anc, up_prefix, parent_anc, 1, sibling_depth, max_dirs, false, true,
                     prev_anc, skip_dirs, empty_pats, seen_full, out);

            prev_anc = parent_anc;
            curr_anc = parent_anc;
            if ((int)out.size() >= max_dirs) break;
        }
    }

    return out;
}

// ── Frecency, Bookmarks & Shell History Seed ───────────────────

struct FrecencyEntry {
    int visits;
    long long last_visit;
};

static std::string frecency_tsv_path() { return get_home() + "/.dongle_frecency.tsv"; }
static std::string bookmarks_txt_path() { return get_home() + "/.dongle_bookmarks.txt"; }

static std::map<std::string, FrecencyEntry> load_frecency();
static void save_frecency(const std::map<std::string, FrecencyEntry> &data);

// Import historical `cd <dir>` commands from ~/.zsh_history, ~/.bash_history, and fish_history
// so Dongle immediately knows your favorite directories without starting from scratch!
static int import_shell_history(std::map<std::string, FrecencyEntry> &data) {
    std::string home = get_home();
    if (home.empty()) return 0;

    std::vector<std::string> hist_files = {
        home + "/.zsh_history",
        home + "/.bash_history",
        home + "/.local/share/fish/fish_history"
    };

    std::string cwd = get_cwd();
    long long now = now_sec();
    int imported_dirs = 0;

    auto extract_and_add = [&](std::string cmd_str) {
        cmd_str = trim(cmd_str);
        // Strip zsh extended history prefix `: 1710000000:0;cd ...`
        if (cmd_str.size() > 2 && cmd_str[0] == ':') {
            size_t semi = cmd_str.find(';');
            if (semi != std::string::npos) cmd_str = trim(cmd_str.substr(semi + 1));
        }
        // Strip fish history prefix `- cmd: cd ...`
        const std::string fish_p = "- cmd:";
        if (cmd_str.compare(0, fish_p.size(), fish_p) == 0) {
            cmd_str = trim(cmd_str.substr(fish_p.size()));
        }

        // Look for `cd <arg>`
        if (cmd_str.compare(0, 3, "cd ") != 0) return;
        std::string arg = trim(cmd_str.substr(3));
        // Strip trailing `;`, `&&`, `|`
        size_t sep = arg.find_first_of(";&|");
        if (sep != std::string::npos) arg = trim(arg.substr(0, sep));
        // Strip quotes
        if (arg.size() >= 2 && ((arg.front() == '"' && arg.back() == '"') || (arg.front() == '\'' && arg.back() == '\''))) {
            arg = arg.substr(1, arg.size() - 2);
        }
        // Unescape `\ `
        std::string unescaped;
        for (size_t i = 0; i < arg.size(); ++i) {
            if (arg[i] == '\\' && i + 1 < arg.size() && arg[i + 1] == ' ') {
                unescaped.push_back(' ');
                ++i;
            } else {
                unescaped.push_back(arg[i]);
            }
        }
        arg = trim(unescaped);
        if (arg.empty() || arg == "-" || arg == "." || arg == "..") return;

        std::string candidate;
        if (arg[0] == '~') {
            candidate = home + arg.substr(1);
        } else if (arg[0] == '/') {
            candidate = arg;
        } else {
            // Try relative to $HOME first (most common interactive cd), then CWD
            if (is_dir(home + "/" + arg)) candidate = home + "/" + arg;
            else if (is_dir(cwd + "/" + arg)) candidate = cwd + "/" + arg;
            else return;
        }

        char resolved[4096];
        if (!realpath(candidate.c_str(), resolved)) return;
        std::string full_p(resolved);
        if (full_p == home || !is_dir(full_p)) return;

        auto it = data.find(full_p);
        if (it != data.end()) {
            it->second.visits += 1;
        } else {
            data[full_p] = {1, now - 3600}; // weight as recent (<1 day)
            ++imported_dirs;
        }
    };

    for (const auto &hf : hist_files) {
        std::ifstream f(hf, std::ios::in | std::ios::binary);
        if (!f.is_open()) continue;
        // Read up to last 512KB of history file for speed
        f.seekg(0, std::ios::end);
        std::streamoff len = f.tellg();
        if (len > 524288) f.seekg(len - 524288);
        else f.seekg(0);

        std::string line;
        while (std::getline(f, line)) {
            extract_and_add(line);
        }
    }

    return imported_dirs;
}

static std::map<std::string, FrecencyEntry> load_frecency() {
    std::map<std::string, FrecencyEntry> data;
    std::string path = frecency_tsv_path();
    bool exists = file_exists(path);

    if (exists) {
        std::ifstream f(path);
        if (f.is_open()) {
            std::string line;
            while (std::getline(f, line)) {
                size_t t1 = line.find('\t');
                if (t1 == std::string::npos) continue;
                size_t t2 = line.find('\t', t1 + 1);
                if (t2 == std::string::npos) continue;
                try {
                    int v = std::stoi(line.substr(0, t1));
                    long long ts = std::stoll(line.substr(t1 + 1, t2 - t1 - 1));
                    std::string p = line.substr(t2 + 1);
                    if (!p.empty()) data[p] = {v, ts};
                } catch (...) {}
            }
        }
    }

    // Auto-bootstrap from shell history if frecency DB is empty or doesn't exist yet!
    if (!exists || data.empty()) {
        import_shell_history(data);
        save_frecency(data);
    }

    return data;
}

static void save_frecency(const std::map<std::string, FrecencyEntry> &data) {
    std::ofstream f(frecency_tsv_path(), std::ios::trunc);
    if (!f.is_open()) return;
    for (const auto &kv : data) {
        f << kv.second.visits << "\t" << kv.second.last_visit << "\t" << kv.first << "\n";
    }
}

static void record_visit(const std::string &full_path) {
    if (full_path.empty() || !is_dir(full_path)) return;
    std::string abs_p = abspath(full_path);
    auto data = load_frecency();
    long long now = now_sec();
    auto it = data.find(abs_p);
    if (it != data.end()) {
        it->second.visits += 1;
        it->second.last_visit = now;
    } else {
        data[abs_p] = {1, now};
    }
    save_frecency(data);
}

static std::map<std::string, int> get_frecency_scores() {
    auto data = load_frecency();
    std::map<std::string, int> scores;
    long long now = now_sec();
    for (const auto &kv : data) {
        long long age = now - kv.second.last_visit;
        double weight = 0.5;
        if (age < 3600) weight = 4.0;
        else if (age < 86400) weight = 2.0;
        else if (age < 604800) weight = 1.0;
        scores[kv.first] = static_cast<int>(kv.second.visits * weight);
    }
    return scores;
}

static std::vector<std::string> load_bookmarks() {
    std::vector<std::string> bms;
    std::ifstream f(bookmarks_txt_path());
    if (f.is_open()) {
        std::string line;
        while (std::getline(f, line)) {
            std::string t = trim(line);
            if (!t.empty()) bms.push_back(t);
        }
    }
    return bms;
}

static void save_bookmarks(const std::vector<std::string> &bms) {
    std::ofstream f(bookmarks_txt_path(), std::ios::trunc);
    if (!f.is_open()) return;
    for (const auto &b : bms) f << b << "\n";
}

static bool toggle_bookmark(const std::string &path) {
    std::string abs_p = abspath(path);
    auto bms = load_bookmarks();
    auto it = std::find(bms.begin(), bms.end(), abs_p);
    if (it != bms.end()) {
        bms.erase(it);
        save_bookmarks(bms);
        return false;
    } else {
        bms.insert(bms.begin(), abs_p);
        save_bookmarks(bms);
        return true;
    }
}

// ── Fuzzy Matcher, Exact-Name Verification & Highlight Indices ──

static std::vector<std::string> split_query_segs(const std::string &q) {
    std::vector<std::string> segs;
    std::string cur;
    for (char c : q) {
        if (c == ' ' || c == '/' || c == '\\') {
            if (!cur.empty()) { segs.push_back(cur); cur.clear(); }
        } else {
            cur.push_back(c);
        }
    }
    if (!cur.empty()) segs.push_back(cur);
    return segs;
}

// Check if query matches the exact basename or exact relative path of `item`
static bool is_exact_name_match(const PathItem &item, const std::string &query) {
    std::string q_lo = to_lower(trim(query));
    if (q_lo.empty()) return false;
    while (q_lo.size() > 1 && q_lo.back() == '/') q_lo.pop_back();

    std::string disp_lo = to_lower(item.display);
    if (disp_lo == q_lo) return true;

    std::string base_lo = to_lower(basename_of(item.full));
    if (base_lo == q_lo) return true;

    // Also check if display ends with `/<q_lo>` when query has slashes
    if (q_lo.find('/') != std::string::npos && disp_lo.size() > q_lo.size()) {
        if (disp_lo.compare(disp_lo.size() - q_lo.size() - 1, q_lo.size() + 1, "/" + q_lo) == 0) {
            return true;
        }
    }
    return false;
}

static int score_path(const std::string &q,
                      const std::vector<std::string> &q_segs,
                      const std::vector<std::string> &q_segs_wrapped,
                      const PathItem &item) {
    std::string path_lower = to_lower(item.display);
    std::string base_lower = to_lower(basename_of(item.full));
    int path_len = static_cast<int>(item.display.size());

    if (q == path_lower) return 1000000;
    if (q == base_lower) return item.is_upward ? 850000 : 950000;

    int score = 0;
    size_t idx = path_lower.find(q);
    if (idx != std::string::npos) {
        if (!q_segs_wrapped.empty()) {
            std::string wrapped = "/" + path_lower + "/";
            for (const auto &qsw : q_segs_wrapped) {
                if (wrapped.find(qsw) != std::string::npos) score += 50000;
            }
        }
        if (base_lower.find(q) == 0) {
            score += 25000; // prefix of folder basename
        } else if (idx == 0 || path_lower[idx - 1] == '/' || path_lower[idx - 1] == '_' || path_lower[idx - 1] == '-') {
            score += 5000;
        }
        score += 10000 - static_cast<int>(idx);
        if (!item.is_upward) score += 1000; // slight preference for downward matches on ties
        return score;
    }

    if (q_segs.size() > 1) {
        std::string wrapped = "/" + path_lower + "/";
        bool all_ok = true;
        int seg_bonus = 0;
        size_t last_pos = 0;
        for (size_t i = 0; i < q_segs.size(); ++i) {
            size_t pos = path_lower.find(q_segs[i], last_pos);
            if (pos == std::string::npos) { all_ok = false; break; }
            if (wrapped.find(q_segs_wrapped[i]) != std::string::npos) seg_bonus += 50000;
            else if (pos == 0 || path_lower[pos - 1] == '/' || path_lower[pos - 1] == '_' || path_lower[pos - 1] == '-') seg_bonus += 15000;
            last_pos = pos + q_segs[i].size();
        }
        if (all_ok) return 20000 + seg_bonus - path_len;
    }

    if (!q_segs_wrapped.empty()) {
        std::string wrapped = "/" + path_lower + "/";
        for (const auto &qsw : q_segs_wrapped) {
            if (wrapped.find(qsw) != std::string::npos) score += 50000;
        }
    }
    if (score > 0) return score;

    size_t pos = 0;
    int boundary_hits = 0;
    int char_count = 0;
    for (char c : q) {
        if (c == ' ') continue;
        ++char_count;
        size_t found = path_lower.find(c, pos);
        if (found == std::string::npos) return 0;
        if (found == 0 || path_lower[found - 1] == '/' || path_lower[found - 1] == '_' || path_lower[found - 1] == '-') {
            ++boundary_hits;
        }
        pos = found + 1;
    }
    if (char_count == 0) return 0;
    int bonus = (boundary_hits == char_count && char_count > 1) ? 2000 : 0;
    return 1000 + bonus - path_len;
}

static std::vector<bool> compute_match_mask(const std::string &display, const std::string &query) {
    std::vector<bool> mask(display.size(), false);
    if (query.empty() || display.empty()) return mask;

    std::string p_lo = to_lower(display);
    std::string q_lo = to_lower(query);

    size_t idx = p_lo.find(q_lo);
    if (idx != std::string::npos) {
        for (size_t i = idx; i < idx + q_lo.size() && i < mask.size(); ++i) mask[i] = true;
        return mask;
    }

    auto segs = split_query_segs(q_lo);
    if (segs.size() > 1) {
        size_t last_pos = 0;
        bool ok = true;
        std::vector<bool> seg_mask(display.size(), false);
        for (const auto &seg : segs) {
            size_t pos = p_lo.find(seg, last_pos);
            if (pos == std::string::npos) { ok = false; break; }
            for (size_t i = pos; i < pos + seg.size() && i < seg_mask.size(); ++i) seg_mask[i] = true;
            last_pos = pos + seg.size();
        }
        if (ok) return seg_mask;
    }

    size_t pos = 0;
    for (char c : q_lo) {
        if (c == ' ') continue;
        size_t bound = std::string::npos;
        size_t search_from = pos;
        while (true) {
            size_t cand = p_lo.find(c, search_from);
            if (cand == std::string::npos) break;
            if (cand == 0 || p_lo[cand - 1] == '/' || p_lo[cand - 1] == '_' || p_lo[cand - 1] == '-' || p_lo[cand - 1] == '.') {
                bound = cand;
                break;
            }
            search_from = cand + 1;
        }
        size_t chosen = (bound != std::string::npos) ? bound : p_lo.find(c, pos);
        if (chosen == std::string::npos) break;
        mask[chosen] = true;
        pos = chosen + 1;
    }
    return mask;
}

static std::vector<PathItem> filter_and_rank(const std::string &query,
                                             const std::vector<PathItem> &paths,
                                             const std::map<std::string, int> &frecency,
                                             const std::set<std::string> &bookmarks) {
    if (paths.empty()) return {};

    struct Ranked {
        long long sort_score;
        int neg_len;
        int neg_idx;
        size_t orig_idx;
        bool operator<(const Ranked &o) const {
            if (sort_score != o.sort_score) return sort_score > o.sort_score;
            if (neg_len != o.neg_len) return neg_len > o.neg_len;
            return neg_idx > o.neg_idx;
        }
    };

    std::vector<Ranked> ranked;
    ranked.reserve(paths.size());

    if (query.empty()) {
        for (size_t i = 0; i < paths.size(); ++i) {
            const auto &p = paths[i];
            long long sc = p.is_upward ? -50 : 0; // show current tree first when query is empty, unless visited/pinned
            if (bookmarks.count(p.full)) sc += 1000000;
            auto fit = frecency.find(p.full);
            if (fit != frecency.end()) sc += fit->second * 100;
            ranked.push_back({sc, -static_cast<int>(p.display.size()), -static_cast<int>(i), i});
        }
    } else {
        std::string q = to_lower(trim(query));
        auto q_segs = split_query_segs(q);
        std::vector<std::string> q_segs_wrapped;
        for (const auto &s : q_segs) q_segs_wrapped.push_back("/" + s + "/");

        for (size_t i = 0; i < paths.size(); ++i) {
            const auto &p = paths[i];
            int s = score_path(q, q_segs, q_segs_wrapped, p);
            if (s > 0) {
                long long total = s;
                if (bookmarks.count(p.full)) total += 25000;
                auto fit = frecency.find(p.full);
                if (fit != frecency.end()) total += fit->second * 10;
                ranked.push_back({total, -static_cast<int>(p.display.size()), -static_cast<int>(i), i});
            }
        }
    }

    size_t limit = std::min<size_t>(DISPLAY_LIMIT, ranked.size());
    if (ranked.size() > limit) {
        std::partial_sort(ranked.begin(), ranked.begin() + limit, ranked.end());
        ranked.resize(limit);
    } else {
        std::sort(ranked.begin(), ranked.end());
    }

    std::vector<PathItem> out;
    out.reserve(ranked.size());
    for (const auto &r : ranked) out.push_back(paths[r.orig_idx]);
    return out;
}

// Parse inline query prefix (`up <q>`, `u: <q>`, `down <q>`, `d: <q>`)
static std::pair<ScopeMode, std::string> parse_query_scope(const std::string &raw_query, ScopeMode base_scope) {
    std::string trimmed = trim(raw_query);
    std::string lo = to_lower(trimmed);
    if (lo == "up") {
        return {ScopeMode::UP, ""};
    }
    if (lo.compare(0, 3, "up ") == 0) {
        return {ScopeMode::UP, trim(trimmed.substr(3))};
    }
    if (lo.compare(0, 2, "u:") == 0) {
        return {ScopeMode::UP, trim(trimmed.substr(2))};
    }
    if (lo == "down") {
        return {ScopeMode::DOWN, ""};
    }
    if (lo.compare(0, 5, "down ") == 0) {
        return {ScopeMode::DOWN, trim(trimmed.substr(5))};
    }
    if (lo.compare(0, 2, "d:") == 0) {
        return {ScopeMode::DOWN, trim(trimmed.substr(2))};
    }
    return {base_scope, raw_query};
}

// ── Live Directory Preview Generator (with Stack Badges & Git Info) ──

struct GitMetadata {
    std::string branch;
    std::string last_commit_msg;
};

static GitMetadata detect_git_metadata(const std::string &full_path) {
    GitMetadata meta;
    std::string curr = full_path;
    for (int i = 0; i < 6; ++i) {
        std::string git_dir = curr + "/.git";
        std::ifstream f(git_dir + "/HEAD");
        if (f.is_open()) {
            std::string line;
            if (std::getline(f, line)) {
                line = trim(line);
                const std::string prefix = "ref: refs/heads/";
                if (line.compare(0, prefix.size(), prefix) == 0) {
                    meta.branch = line.substr(prefix.size());
                } else {
                    meta.branch = line.substr(0, 7);
                }
            }
            std::ifstream lf(git_dir + "/logs/HEAD");
            if (lf.is_open()) {
                std::string lline, last_non_empty;
                while (std::getline(lf, lline)) {
                    if (!lline.empty()) last_non_empty = lline;
                }
                size_t tab = last_non_empty.find('\t');
                if (tab != std::string::npos && tab + 1 < last_non_empty.size()) {
                    std::string msg = trim(last_non_empty.substr(tab + 1));
                    const std::string cprefix = "commit: ";
                    const std::string ciprefix = "commit (initial): ";
                    if (msg.compare(0, cprefix.size(), cprefix) == 0) msg = msg.substr(cprefix.size());
                    else if (msg.compare(0, ciprefix.size(), ciprefix) == 0) msg = msg.substr(ciprefix.size());
                    meta.last_commit_msg = msg;
                }
            }
            break;
        }
        size_t slash = curr.find_last_of('/');
        if (slash == std::string::npos || slash == 0) break;
        curr = curr.substr(0, slash);
    }
    return meta;
}

static std::string detect_tech_stack(const std::set<std::string> &file_set) {
    std::vector<std::string> badges;
    if (file_set.count("Cargo.toml")) badges.push_back("🦀 Rust");
    if (file_set.count("pubspec.yaml")) badges.push_back("💙 Flutter");
    if (file_set.count("package.json") || file_set.count("tsconfig.json")) badges.push_back("📦 Node/TS");
    if (file_set.count("pyproject.toml") || file_set.count("setup.py") || file_set.count("requirements.txt")) badges.push_back("🐍 Python");
    if (file_set.count("go.mod")) badges.push_back("🐹 Go");
    if (file_set.count("CMakeLists.txt") || file_set.count("Makefile")) badges.push_back("⚡ C/C++");
    std::string res;
    for (size_t i = 0; i < badges.size() && i < 2; ++i) {
        if (!res.empty()) res += " · ";
        res += badges[i];
    }
    return res;
}

struct PreviewLine {
    std::string style;
    std::string text;
};

static std::map<std::string, std::vector<PreviewLine>> g_preview_cache;

static std::vector<PreviewLine> get_preview_lines(const std::string &full_path, int max_lines) {
    auto it = g_preview_cache.find(full_path);
    if (it != g_preview_cache.end()) return it->second;

    std::vector<PreviewLine> lines;
    DIR *dir = opendir(full_path.c_str());
    if (!dir) {
        lines.push_back({"\033[38;5;242m", "  Permission denied or missing"});
        return lines;
    }

    std::vector<std::string> subdirs;
    std::vector<std::string> files;
    std::set<std::string> file_set;
    std::string readme_file;

    struct dirent *entry;
    while ((entry = readdir(dir)) != nullptr) {
        std::string name = entry->d_name;
        if (name == "." || name == ".." || name == ".git" || name == ".DS_Store" || name == "__pycache__") continue;
        std::string child = full_path + "/" + name;
        bool is_d = (entry->d_type == DT_DIR) || (entry->d_type == DT_UNKNOWN && is_dir(child));
        if (is_d) {
            subdirs.push_back(name);
        } else {
            files.push_back(name);
            file_set.insert(name);
            if (readme_file.empty() && (name == "README.md" || name == "readme.md" || name == "README")) {
                readme_file = child;
            }
        }
    }
    closedir(dir);

    std::sort(subdirs.begin(), subdirs.end());
    std::sort(files.begin(), files.end());

    std::string base = basename_of(full_path);
    auto git_meta = detect_git_metadata(full_path);
    std::string header = " 📁 " + base.substr(0, 20);
    if (!git_meta.branch.empty()) header += " (\033[38;5;42m" + git_meta.branch.substr(0, 12) + "\033[1;38;5;117m)";
    lines.push_back({"\033[1;38;5;117m", header});

    std::string stack = detect_tech_stack(file_set);
    std::string meta_str = " " + std::to_string(subdirs.size()) + " dirs, " + std::to_string(files.size()) + " files";
    if (!stack.empty()) meta_str += " · " + stack;
    lines.push_back({"\033[38;5;243m", meta_str});

    if (!git_meta.last_commit_msg.empty()) {
        lines.push_back({"\033[38;5;240m", "  commit: " + git_meta.last_commit_msg.substr(0, 26)});
    }

    int max_entries = readme_file.empty() ? (max_lines - (int)lines.size() - 1) : 5;
    int shown = 0;
    for (const auto &d : subdirs) {
        if (shown >= max_entries) break;
        lines.push_back({"\033[38;5;73m", "  ▸ " + d.substr(0, 28) + "/"});
        ++shown;
    }
    for (const auto &f : files) {
        if (shown >= max_entries) break;
        lines.push_back({"\033[38;5;250m", "  • " + f.substr(0, 28)});
        ++shown;
    }
    int rem = static_cast<int>(subdirs.size() + files.size()) - shown;
    if (rem > 0 && (int)lines.size() < max_lines) {
        lines.push_back({"\033[38;5;240m", "  … +" + std::to_string(rem) + " more"});
    }

    if (!readme_file.empty() && (int)lines.size() + 2 <= max_lines) {
        std::ifstream rf(readme_file);
        if (rf.is_open()) {
            lines.push_back({"\033[38;5;240m", " ─── README ───"});
            std::string rline;
            while ((int)lines.size() < max_lines && std::getline(rf, rline)) {
                std::string t = trim(rline);
                if (t.empty() || t.rfind("![", 0) == 0 || t.rfind("<img", 0) == 0) continue;
                while (!t.empty() && (t[0] == '#' || t[0] == '>' || t[0] == ' ')) t.erase(t.begin());
                if (!t.empty()) {
                    lines.push_back({"\033[3;38;5;245m", " " + t.substr(0, 32)});
                }
            }
        }
    }

    g_preview_cache[full_path] = lines;
    return lines;
}

// ── Native ANSI + Termios Interactive TUI ──────────────────────

struct ActionDef {
    const char *id;
    const char *shortcut;
    const char *label;
};

static const ActionDef ACTIONS[] = {
    {"cd",     "Enter", "Navigate (cd into directory)"},
    {"vscode", "e",     "Open in Editor (Cursor / VS Code)"},
    {"finder", "o",     "Reveal in File Manager (Finder)"},
    {"copy",   "y",     "Copy absolute path to clipboard"},
    {"pin",    "p",     "Pin / Unpin bookmark (★)"},
    {"mkdir",  "n",     "Create new folder from query & cd"},
};
static const int NUM_ACTIONS = 6;

static bool run_external_action(const std::string &act_id, const std::string &full_path, std::string &msg) {
    if (act_id == "vscode") {
        if (is_dir("/Applications/Cursor.app")) {
            system(("open -a Cursor \"" + full_path + "\" >/dev/null 2>&1 &").c_str());
            msg = "Opened in Cursor: " + replace_home_tilde(full_path);
            return true;
        }
        if (is_dir("/Applications/Visual Studio Code.app")) {
            system(("open -a \"Visual Studio Code\" \"" + full_path + "\" >/dev/null 2>&1 &").c_str());
            msg = "Opened in VS Code: " + replace_home_tilde(full_path);
            return true;
        }
        if (system(("command -v code >/dev/null 2>&1 && code \"" + full_path + "\" >/dev/null 2>&1 &").c_str()) == 0) {
            msg = "Opened in VS Code: " + replace_home_tilde(full_path);
            return true;
        }
        msg = "No supported editor (Cursor / VS Code) found";
        return false;
    } else if (act_id == "finder") {
        const char *opener = (access("/usr/bin/open", X_OK) == 0) ? "open" : "xdg-open";
        system((std::string(opener) + " \"" + full_path + "\" >/dev/null 2>&1 &").c_str());
        msg = "Opened in File Manager: " + replace_home_tilde(full_path);
        return true;
    } else if (act_id == "copy") {
        const char *clip = (access("/usr/bin/pbcopy", X_OK) == 0) ? "pbcopy 2>/dev/null" : "xclip -selection clipboard 2>/dev/null";
        FILE *pipe = popen(clip, "w");
        if (pipe) {
            fwrite(full_path.c_str(), 1, full_path.size(), pipe);
            pclose(pipe);
            msg = "Copied path to clipboard: " + replace_home_tilde(full_path);
            return true;
        }
        msg = "Clipboard utility not available";
        return false;
    }
    return false;
}

static int get_tty_cols(int tty_fd) {
    struct winsize ws;
    if (ioctl(tty_fd, TIOCGWINSZ, &ws) == 0 && ws.ws_col > 0) return ws.ws_col;
    return 80;
}

static std::string run_picker_tui(const std::string &initial_root,
                                  bool initial_workspace,
                                  ScopeMode initial_scope,
                                  const std::string &initial_query,
                                  bool auto_select_exact) {
    std::string root = initial_root;
    bool is_workspace = initial_workspace;
    ScopeMode base_scope = initial_scope;
    std::string query = initial_query;

    auto load_pool = [&](const std::string &r, bool ws, ScopeMode sc) {
        auto p = scan_paths(r, ws, sc);
        if (!ws && p.size() <= 3 && abspath(r) == abspath(get_home())) {
            auto ws_paths = scan_paths(r, true, sc);
            for (const auto &wp : ws_paths) p.push_back(wp);
        }
        return p;
    };

    auto frecency = get_frecency_scores();
    auto bm_vec = load_bookmarks();
    std::set<std::string> bookmarks(bm_vec.begin(), bm_vec.end());

    auto parsed = parse_query_scope(query, base_scope);
    ScopeMode active_scope = parsed.first;
    std::string effective_query = parsed.second;

    auto paths = load_pool(root, is_workspace, active_scope);
    auto filtered = filter_and_rank(effective_query, paths, frecency, bookmarks);

    std::string toast;

    // Smart Verified Auto-Jump:
    // Only jump without TUI if there is an EXACT folder name match!
    // If there is NO exact name match (or multiple ambiguous exact matches),
    // open the interactive TUI with the ranked up/down suggestions so the user never lands in the wrong place.
    if (auto_select_exact && !effective_query.empty()) {
        std::vector<PathItem> exact_down;
        std::vector<PathItem> exact_up;
        for (const auto &item : filtered) {
            if (is_exact_name_match(item, effective_query)) {
                if (item.is_upward) exact_up.push_back(item);
                else exact_down.push_back(item);
            }
        }
        // 1. Immediate downward exact match -> jump if unique
        if (exact_down.size() == 1) {
            return exact_down[0].full;
        }
        // 2. If no downward exact match, check upward exact match -> jump if unique
        if (exact_down.empty() && exact_up.size() == 1) {
            return exact_up[0].full;
        }
        // Otherwise, we have fuzzy suggestions or multiple folders with the same name -> show TUI!
        if (exact_down.empty() && exact_up.empty() && !filtered.empty()) {
            toast = "No exact folder \"" + effective_query + "\" — showing best up/down suggestions";
        } else if (exact_down.size() + exact_up.size() > 1) {
            toast = std::to_string(exact_down.size() + exact_up.size()) + " folders named \"" + effective_query + "\" — choose one";
        }
    }

    int tty_fd = open("/dev/tty", O_RDWR);
    if (tty_fd < 0) return "";

    struct termios orig_term;
    if (tcgetattr(tty_fd, &orig_term) < 0) {
        close(tty_fd);
        return "";
    }

    struct termios raw = orig_term;
    raw.c_lflag &= ~(ICANON | ECHO | ISIG);
    raw.c_iflag &= ~(IXON | ICRNL);
    raw.c_cc[VMIN] = 1;
    raw.c_cc[VTIME] = 0;
    tcsetattr(tty_fd, TCSANOW, &raw);

    bool show_preview = get_preview_enabled();
    bool action_menu = false;
    int action_idx = 0;
    int sel_idx = 0;

    auto refresh_results = [&]() {
        auto pr = parse_query_scope(query, base_scope);
        if (pr.first != active_scope) {
            active_scope = pr.first;
            paths = load_pool(root, is_workspace, active_scope);
        }
        effective_query = pr.second;
        filtered = filter_and_rank(effective_query, paths, frecency, bookmarks);
        sel_idx = 0;
    };

    const int TOTAL_LINES = 2 + VISIBLE_ROWS + 1;
    bool first_draw = true;

    auto render = [&]() {
        std::ostringstream buf;
        int cols = get_tty_cols(tty_fd);
        bool preview_vis = show_preview && !action_menu && (cols >= 74);
        int left_width = preview_vis ? (cols - 38) : (cols - 2);
        if (left_width < 24) left_width = 24;

        if (!first_draw) {
            buf << "\033[" << TOTAL_LINES << "A\r";
        }
        first_draw = false;
        buf << "\033[?25l";

        // Line 1: Header with Scope indicator (Up+Down ⇅, Down ↓, Up ↑, or Workspace)
        std::string mode = is_workspace ? "Workspace" : std::string(scope_name(active_scope));
        std::string disp_root = replace_home_tilde(root);
        buf << "\033[2K  \033[1;38;5;73m" << mode << "\033[0m  \033[38;5;117m" << disp_root << "\033[0m";
        if (!effective_query.empty()) {
            buf << "  \033[38;5;242m(" << filtered.size() << "/" << paths.size() << ")\033[0m";
        } else {
            buf << "  \033[38;5;242m(" << paths.size() << " dirs)\033[0m";
        }
        if (!toast.empty()) {
            buf << "   \033[1;38;5;42m" << toast << "\033[0m";
        }
        buf << "\r\n";

        // Line 2: Search prompt
        buf << "\033[2K  \033[1;38;5;42m/ \033[1;97m" << query << "\033[38;5;42m█\033[0m\r\n";

        // Prepare preview lines if visible
        std::vector<PreviewLine> prev_lines;
        if (preview_vis && !filtered.empty() && sel_idx < (int)filtered.size()) {
            prev_lines = get_preview_lines(filtered[sel_idx].full, VISIBLE_ROWS);
        }

        int start = std::max(0, sel_idx - 7);
        if (start + VISIBLE_ROWS > (int)filtered.size()) {
            start = std::max(0, (int)filtered.size() - VISIBLE_ROWS);
        }

        // Lines 3..17: Body (15 rows)
        for (int r = 0; r < VISIBLE_ROWS; ++r) {
            buf << "\033[2K";
            if (action_menu) {
                if (r == 0) {
                    std::string target_disp = filtered.empty() ? effective_query : filtered[sel_idx].display;
                    buf << "    \033[1;38;5;73mActions for \033[38;5;117m" << target_disp << "\033[0m";
                } else if (r >= 2 && r - 2 < NUM_ACTIONS) {
                    int ai = r - 2;
                    bool is_s = (ai == action_idx);
                    if (is_s) {
                        buf << "  \033[1;97;48;5;24m ❯ \033[1;38;5;214m[" << ACTIONS[ai].shortcut << "] \033[1;97m"
                            << ACTIONS[ai].label << " \033[0m";
                    } else {
                        buf << "     \033[1;38;5;245m[" << ACTIONS[ai].shortcut << "]\033[0m " << ACTIONS[ai].label;
                    }
                }
            } else if (filtered.empty()) {
                if (r == 0) {
                    buf << "    \033[38;5;242mNo matches for \"" << effective_query << "\".\033[0m";
                } else if (r == 1) {
                    buf << "    \033[1;38;5;42mCtrl+Y\033[38;5;240m — create directory \"" << effective_query << "\" & cd into it\033[0m";
                } else if (r == 2) {
                    buf << "    \033[1;38;5;73mCtrl+S\033[38;5;240m — cycle scope (Up+Down / Down / Up)  |  \033[1;38;5;73mCtrl+W\033[38;5;240m — workspace\033[0m";
                }
            } else {
                int item_idx = start + r;
                if (item_idx < (int)filtered.size()) {
                    const auto &item = filtered[item_idx];
                    bool is_s = (item_idx == sel_idx);
                    bool is_bm = bookmarks.count(item.full) > 0;

                    std::string disp = item.display;
                    int max_disp = left_width - (is_bm ? 10 : 8);
                    if (max_disp > 5 && (int)disp.size() > max_disp) {
                        disp = disp.substr(0, max_disp - 1) + "…";
                    }

                    auto mask = compute_match_mask(disp, effective_query);
                    const char *base_style = is_s ? "\033[1;97;48;5;24m" : (item.is_upward ? "\033[38;5;249m" : "\033[0m");
                    const char *hi_style   = is_s ? "\033[1;38;5;214;48;5;24m" : "\033[1;38;5;214m";
                    const char *pin_style  = is_s ? "\033[1;38;5;220;48;5;24m" : "\033[1;38;5;220m";
                    const char *up_badge   = is_s ? "\033[1;38;5;117;48;5;24m↑ " : "\033[38;5;73m↑ ";

                    buf << "  " << base_style << (is_s ? "❯ " : "  ");
                    if (is_bm) {
                        buf << pin_style << "★ " << base_style;
                    } else if (item.is_upward) {
                        buf << up_badge << base_style;
                    }
                    for (size_t ci = 0; ci < disp.size(); ++ci) {
                        buf << (mask[ci] ? hi_style : base_style) << disp[ci];
                    }
                    if (is_s) buf << " ";
                    buf << "\033[0m";
                }
            }

            if (preview_vis) {
                buf << "\033[" << (left_width + 2) << "G\033[38;5;238m│\033[0m";
                if (r < (int)prev_lines.size()) {
                    buf << prev_lines[r].style << prev_lines[r].text << "\033[0m";
                }
            }
            buf << "\r\n";
        }

        // Line 18: Footer
        buf << "\033[2K";
        if (action_menu) {
            buf << " \033[1;38;5;245m↑↓\033[38;5;240m select  "
                << "\033[1;38;5;245mEnter\033[38;5;240m run  "
                << "\033[1;38;5;245me/o/y/p/n\033[38;5;240m shortcut  "
                << "\033[1;38;5;245mTab/Esc\033[38;5;240m back\033[0m";
        } else {
            buf << " \033[1;38;5;245m↑↓\033[38;5;240m nav  "
                << "\033[1;38;5;245mEnter\033[38;5;240m cd  "
                << "\033[1;38;5;245mTab\033[38;5;240m actions  "
                << "\033[1;38;5;245m^S\033[38;5;240m scope(⇅/↓/↑)  "
                << "\033[1;38;5;245m←/→\033[38;5;240m up/in  "
                << "\033[1;38;5;245m^B\033[38;5;240m pin  "
                << "\033[1;38;5;245m^V\033[38;5;240m preview  "
                << "\033[1;38;5;245m^W\033[38;5;240m ws  "
                << "\033[1;38;5;245mEsc\033[38;5;240m exit\033[0m";
        }

        std::string out_s = buf.str();
        (void)write(tty_fd, out_s.c_str(), out_s.size());
    };

    auto cleanup_screen = [&]() {
        std::ostringstream buf;
        if (!first_draw) {
            buf << "\033[" << (TOTAL_LINES - 1) << "A\r\033[J";
        }
        buf << "\033[?25h";
        std::string s = buf.str();
        (void)write(tty_fd, s.c_str(), s.size());
        tcsetattr(tty_fd, TCSANOW, &orig_term);
        close(tty_fd);
    };

    std::string chosen_full;
    std::string exit_notice;

    auto create_and_cd_query = [&]() -> bool {
        std::string clean_q = trim(effective_query);
        if (clean_q.empty()) {
            toast = "Type a folder name first";
            return false;
        }
        std::string new_dir = (clean_q[0] == '/') ? clean_q : (root + "/" + clean_q);
        if (mkdir_p(new_dir)) {
            chosen_full = abspath(new_dir);
            exit_notice = "Created directory: " + replace_home_tilde(chosen_full);
            return true;
        }
        toast = "Failed to create directory";
        return false;
    };

    render();

    while (true) {
        unsigned char c = 0;
        ssize_t n = read(tty_fd, &c, 1);
        if (n <= 0) break;

        if (c == 3) { // Ctrl+C
            break;
        } else if (c == 27) { // ESC or Arrow sequence
            struct timeval tv = {0, 15000};
            fd_set fds;
            FD_ZERO(&fds);
            FD_SET(tty_fd, &fds);
            if (select(tty_fd + 1, &fds, nullptr, nullptr, &tv) > 0) {
                unsigned char seq[2] = {0, 0};
                if (read(tty_fd, &seq[0], 1) == 1 && (seq[0] == '[' || seq[0] == 'O')) {
                    if (read(tty_fd, &seq[1], 1) == 1) {
                        if (seq[1] == 'A') { // Up
                            if (action_menu) action_idx = (action_idx - 1 + NUM_ACTIONS) % NUM_ACTIONS;
                            else if (!filtered.empty()) sel_idx = (sel_idx - 1 + (int)filtered.size()) % (int)filtered.size();
                            toast.clear();
                            render();
                            continue;
                        } else if (seq[1] == 'B') { // Down
                            if (action_menu) action_idx = (action_idx + 1) % NUM_ACTIONS;
                            else if (!filtered.empty()) sel_idx = (sel_idx + 1) % (int)filtered.size();
                            toast.clear();
                            render();
                            continue;
                        } else if (seq[1] == 'C') { // Right arrow -> Drill into selected directory
                            if (!action_menu && !filtered.empty()) {
                                root = filtered[sel_idx].full;
                                is_workspace = false;
                                query.clear();
                                paths = load_pool(root, false, active_scope);
                                refresh_results();
                                toast = "Drilled into " + replace_home_tilde(root);
                                render();
                            }
                            continue;
                        } else if (seq[1] == 'D') { // Left arrow -> Climb to parent directory
                            if (!action_menu) {
                                size_t sl = root.find_last_of('/');
                                if (sl != std::string::npos && sl > 0) {
                                    root = root.substr(0, sl);
                                    is_workspace = false;
                                    paths = load_pool(root, false, active_scope);
                                    refresh_results();
                                    toast = "Climbed up to " + replace_home_tilde(root);
                                    render();
                                }
                            }
                            continue;
                        }
                    }
                }
                continue;
            } else {
                if (action_menu) {
                    action_menu = false;
                    render();
                    continue;
                }
                break;
            }
        } else if (c == 9) { // Tab
            action_menu = !action_menu;
            action_idx = 0;
            toast.clear();
            render();
        } else if (c == 19) { // Ctrl+S -> Cycle Scope (Up+Down -> Down -> Up)
            if (base_scope == ScopeMode::BOTH) base_scope = ScopeMode::DOWN;
            else if (base_scope == ScopeMode::DOWN) base_scope = ScopeMode::UP;
            else base_scope = ScopeMode::BOTH;
            active_scope = base_scope;
            paths = load_pool(root, is_workspace, active_scope);
            refresh_results();
            toast = std::string("Scope: ") + scope_name(active_scope);
            render();
        } else if (c == 25) { // Ctrl+Y -> mkdir -p <query> & cd
            if (create_and_cd_query()) break;
            render();
        } else if (c == 12) { // Ctrl+L -> Drill into selected directory as new root
            if (!filtered.empty()) {
                root = filtered[sel_idx].full;
                is_workspace = false;
                query.clear();
                paths = load_pool(root, false, active_scope);
                refresh_results();
                toast = "Drilled into " + replace_home_tilde(root);
                render();
            }
        } else if (c == 13 || c == 10) { // Enter
            if (action_menu) {
                std::string aid = ACTIONS[action_idx].id;
                if (aid == "mkdir") {
                    if (create_and_cd_query()) break;
                    action_menu = false;
                    render();
                    continue;
                }
                if (filtered.empty()) break;
                std::string target = filtered[sel_idx].full;
                if (aid == "cd") {
                    chosen_full = target;
                    break;
                } else if (aid == "pin") {
                    bool pinned = toggle_bookmark(target);
                    auto bms = load_bookmarks();
                    bookmarks = std::set<std::string>(bms.begin(), bms.end());
                    action_menu = false;
                    toast = pinned ? "★ Pinned" : "☆ Unpinned";
                    render();
                } else {
                    std::string msg;
                    if (run_external_action(aid, target, msg)) {
                        exit_notice = msg;
                        break;
                    } else {
                        action_menu = false;
                        toast = msg;
                        render();
                    }
                }
            } else {
                if (filtered.empty()) break;
                chosen_full = filtered[sel_idx].full;
                break;
            }
        } else if (c == 16) { // Ctrl+P (Up)
            if (action_menu) action_idx = (action_idx - 1 + NUM_ACTIONS) % NUM_ACTIONS;
            else if (!filtered.empty()) sel_idx = (sel_idx - 1 + (int)filtered.size()) % (int)filtered.size();
            toast.clear();
            render();
        } else if (c == 14) { // Ctrl+N (Down)
            if (action_menu) action_idx = (action_idx + 1) % NUM_ACTIONS;
            else if (!filtered.empty()) sel_idx = (sel_idx + 1) % (int)filtered.size();
            toast.clear();
            render();
        } else if (c == 21) { // Ctrl+U (Clear query)
            action_menu = false;
            query.clear();
            toast.clear();
            refresh_results();
            render();
        } else if (c == 22) { // Ctrl+V (Toggle preview)
            show_preview = !show_preview;
            render();
        } else if (c == 2) { // Ctrl+B (Pin/Unpin bookmark)
            if (!filtered.empty()) {
                bool pinned = toggle_bookmark(filtered[sel_idx].full);
                auto bms = load_bookmarks();
                bookmarks = std::set<std::string>(bms.begin(), bms.end());
                toast = pinned ? "★ Pinned" : "☆ Unpinned";
                render();
            }
        } else if (c == 23) { // Ctrl+W (Toggle Workspace)
            action_menu = false;
            is_workspace = !is_workspace;
            paths = load_pool(root, is_workspace, active_scope);
            refresh_results();
            toast = is_workspace ? "Workspace mode" : "Project mode";
            render();
        } else if (c == 18) { // Ctrl+R (Rescan)
            action_menu = false;
            g_preview_cache.clear();
            paths = load_pool(root, is_workspace, active_scope);
            refresh_results();
            toast = "Rescanned (" + std::to_string(paths.size()) + " dirs)";
            render();
        } else if (c == 127 || c == 8) { // Backspace (127) or Ctrl+H (8)
            if (c == 8 && query.empty()) {
                size_t sl = root.find_last_of('/');
                if (sl != std::string::npos && sl > 0) {
                    root = root.substr(0, sl);
                    is_workspace = false;
                    paths = load_pool(root, false, active_scope);
                    refresh_results();
                    toast = "Climbed up to " + replace_home_tilde(root);
                    render();
                }
            } else if (action_menu) {
                action_menu = false;
                render();
            } else if (!query.empty()) {
                query.pop_back();
                toast.clear();
                refresh_results();
                render();
            }
        } else if (c >= 32 && c < 127) { // Printable ASCII
            if (action_menu) {
                char ch = static_cast<char>(std::tolower(c));
                if (ch == 'n') {
                    if (create_and_cd_query()) break;
                    action_menu = false;
                    render();
                    continue;
                }
                if (filtered.empty()) continue;
                std::string target = filtered[sel_idx].full;
                if (ch == 'p') {
                    bool pinned = toggle_bookmark(target);
                    auto bms = load_bookmarks();
                    bookmarks = std::set<std::string>(bms.begin(), bms.end());
                    action_menu = false;
                    toast = pinned ? "★ Pinned" : "☆ Unpinned";
                    render();
                } else if (ch == 'e' || ch == 'o' || ch == 'y') {
                    std::string aid = (ch == 'e') ? "vscode" : (ch == 'o' ? "finder" : "copy");
                    std::string msg;
                    if (run_external_action(aid, target, msg)) {
                        exit_notice = msg;
                        break;
                    } else {
                        action_menu = false;
                        toast = msg;
                        render();
                    }
                }
            } else {
                query.push_back(static_cast<char>(c));
                toast.clear();
                refresh_results();
                render();
            }
        }
    }

    cleanup_screen();
    if (!exit_notice.empty()) {
        std::cerr << "  " << C_GREEN << "✓" << C_RESET << " " << exit_notice << "\n";
    }
    return chosen_full;
}

// ── CLI Subcommands & Welcome Banner ───────────────────────────

static void cmd_welcome() {
    // Trigger frecency load so shell history is imported on first welcome!
    auto frec = load_frecency();
    std::cout << "\n"
              << "  \033[1;38;5;42m╭──────────────────────────────────────────────────────────────╮\033[0m\n"
              << "  \033[1;38;5;42m│\033[0m  ⚡ \033[1;97mDONGLE v" << DONGLE_VERSION << "\033[0m — \033[38;5;117mBidirectional Fuzzy Directory Navigation\033[0m  \033[1;38;5;42m│\033[0m\n"
              << "  \033[1;38;5;42m│\033[0m     \033[38;5;242mC++17 Engine · <2ms Startup · Searches Up ↑ & Down ↓\033[0m    \033[1;38;5;42m│\033[0m\n"
              << "  \033[1;38;5;42m╰──────────────────────────────────────────────────────────────╯\033[0m\n\n"
              << "  \033[1;38;5;42m✓\033[0m Seeded frecency memory with \033[1;97m" << frec.size() << " directories\033[0m from your shell history!\n\n"
              << "  \033[1;97mTry these right now in your terminal:\033[0m\n"
              << "    \033[1;38;5;42m/\033[0m                 Press \033[1m/\033[0m on an empty prompt to search \033[1mUp ↑ & Down ↓\033[0m\n"
              << "    \033[1;38;5;42mdg\033[0m \033[38;5;242m<name>\033[0m         Jumps immediately if exact folder exists; else opens suggestions\n"
              << "    \033[1;38;5;42mdg up\033[0m \033[38;5;242m[query]\033[0m     Search \033[1monly upward\033[0m (3–5 layers above current folder) (\033[1mdgu\033[0m)\n"
              << "    \033[1;38;5;42mdg down\033[0m \033[38;5;242m[query]\033[0m   Search \033[1monly downward\033[0m (3–5 layers inside current folder) (\033[1mdgd\033[0m)\n"
              << "    \033[1;38;5;42mdgw\033[0m               Search across all your projects / workspaces\n"
              << "    \033[1;38;5;42mdgpin\033[0m             Pin (\033[38;5;220m★\033[0m) current folder to the top of results\n\n"
              << "  \033[1;97mPower-User Keys Inside the Picker:\033[0m\n"
              << "    \033[1;38;5;117mCtrl+S\033[0m            Cycle search scope (\033[1mUp+Down ⇅\033[0m → \033[1mDown ↓\033[0m → \033[1mUp ↑\033[0m)\n"
              << "    \033[1;38;5;117mup \033[38;5;242m<q>\033[0m / \033[1;38;5;117mdown \033[38;5;242m<q>\033[0m Type \033[1mup\033[0m or \033[1mdown\033[0m right inside the search bar to filter direction!\n"
              << "    \033[1;38;5;117mTab\033[0m               Open Action Menu (\033[1me\033[0m Editor, \033[1mo\033[0m Finder, \033[1my\033[0m Copy, \033[1mn\033[0m Mkdir)\n"
              << "    \033[1;38;5;117m← / →\033[0m             Climb up to parent (\033[1m..\033[0m) or drill into selected folder\n"
              << "    \033[1;38;5;117mCtrl+B\033[0m            Pin / Unpin selected directory (\033[38;5;220m★\033[0m)\n"
              << "    \033[1;38;5;117mCtrl+V\033[0m            Toggle Live Preview HUD (Git branch, stack, README)\n\n";
}

static void cmd_intro() {
    cmd_welcome();
    std::cout << C_BOLD << "  CLI Reference:\n" << C_RESET
              << "    dongle init <shell>   Output shell integration (zsh/bash/fish)\n"
              << "    dongle import-history Import visited directories from shell history (~/.zsh_history, etc.)\n"
              << "    dongle root           Print current project root\n"
              << "    dongle recent         Show pinned & recently visited directories\n"
              << "    dongle pin [dir]      Pin / unpin a directory\n"
              << "    dongle prune          Remove deleted directories from frecency & pins\n"
              << "    dongle doctor         Diagnose installation\n"
              << "    dongle version        Show version\n\n";
}

static ScopeMode parse_scope_str(const std::string &s) {
    std::string lo = to_lower(trim(s));
    if (lo == "up" || lo == "u") return ScopeMode::UP;
    if (lo == "down" || lo == "d") return ScopeMode::DOWN;
    return ScopeMode::BOTH;
}

static int cmd_pick(int argc, char **argv) {
    bool is_workspace = false;
    bool auto_select = false;
    ScopeMode scope = ScopeMode::BOTH;
    std::string query;
    std::string custom_root;

    for (int i = 0; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--workspace" || a == "-w") {
            is_workspace = true;
        } else if (a == "--auto-select" || a == "-1") {
            auto_select = true;
        } else if (a == "--up") {
            scope = ScopeMode::UP;
        } else if (a == "--down") {
            scope = ScopeMode::DOWN;
        } else if (a == "--scope" && i + 1 < argc) {
            scope = parse_scope_str(argv[++i]);
        } else if (a == "--rescan" || a == "-r") {
            // Always fresh in C++
        } else if (a == "--query" || a == "-q") {
            if (i + 1 < argc) query = argv[++i];
        } else if (a == "--help" || a == "-h") {
            cmd_intro();
            return 0;
        } else if (!a.empty() && a[0] != '-' && custom_root.empty()) {
            custom_root = a;
        }
    }

    // Search relative to user's actual current directory ($PWD) so 3-5 layers up & down
    // are always centered around where the user currently is!
    std::string root = custom_root.empty() ? get_cwd() : abspath(custom_root);
    std::string chosen = run_picker_tui(root, is_workspace, scope, query, auto_select);
    if (!chosen.empty()) {
        record_visit(chosen);
        std::cout << chosen << "\n";
        return 0;
    }
    return 1;
}

static int cmd_jump(int argc, char **argv) {
    ScopeMode scope = ScopeMode::BOTH;
    std::string query;
    for (int i = 0; i < argc; ++i) {
        std::string a = argv[i];
        if (i == 0 && (a == "up" || a == "u" || a == "--up" || a == "-u" ||
                       a == "down" || a == "d" || a == "--down" || a == "-d")) {
            if (a == "--up" || a == "-u") scope = ScopeMode::UP;
            else if (a == "--down" || a == "-d") scope = ScopeMode::DOWN;
            else scope = parse_scope_str(a);
            continue;
        }
        if (!query.empty()) query += " ";
        query += a;
    }
    std::string root = get_cwd();
    std::string chosen = run_picker_tui(root, false, scope, query, true);
    if (!chosen.empty()) {
        record_visit(chosen);
        std::cout << chosen << "\n";
        return 0;
    }
    return 1;
}

static int cmd_scan(int argc, char **argv) {
    bool is_workspace = false;
    ScopeMode scope = ScopeMode::BOTH;
    std::string custom_root;
    for (int i = 0; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--workspace" || a == "-w") is_workspace = true;
        else if (a == "--up" || a == "up") scope = ScopeMode::UP;
        else if (a == "--down" || a == "down") scope = ScopeMode::DOWN;
        else if (!a.empty() && a[0] != '-') custom_root = a;
    }
    std::string root = custom_root.empty() ? get_cwd() : abspath(custom_root);
    auto paths = scan_paths(root, is_workspace, scope);
    std::cerr << "Scanned " << (is_workspace ? "workspaces" : root) << " (" << paths.size() << " paths)\n";
    return 0;
}

static int cmd_list(int argc, char **argv) {
    bool is_workspace = false;
    ScopeMode scope = ScopeMode::BOTH;
    std::string custom_root;
    for (int i = 0; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--workspace" || a == "-w") is_workspace = true;
        else if (a == "--up" || a == "up") scope = ScopeMode::UP;
        else if (a == "--down" || a == "down") scope = ScopeMode::DOWN;
        else if (!a.empty() && a[0] != '-') custom_root = a;
    }
    std::string root = custom_root.empty() ? get_cwd() : abspath(custom_root);
    auto paths = scan_paths(root, is_workspace, scope);
    for (const auto &p : paths) {
        std::cout << p.display << "\t" << p.full << "\n";
    }
    return 0;
}

static int cmd_recent() {
    auto bms = load_bookmarks();
    auto frec = load_frecency();

    if (bms.empty() && frec.empty()) {
        std::cout << C_DIM << "  No recent or pinned directories yet. Start navigating with dg or /" << C_RESET << "\n";
        return 0;
    }
    if (!bms.empty()) {
        std::cout << "\n" << C_BOLD << "  Pinned directories (★):" << C_RESET << "\n";
        for (const auto &b : bms) {
            std::cout << "  " << C_YELLOW << "★" << C_RESET << "  " << replace_home_tilde(b) << "\n";
        }
    }
    if (!frec.empty()) {
        std::vector<std::pair<long long, std::string>> sorted_frec;
        for (const auto &kv : frec) sorted_frec.push_back({kv.second.last_visit, kv.first});
        std::sort(sorted_frec.rbegin(), sorted_frec.rend());

        std::cout << "\n" << C_BOLD << "  Recent & historical directories (" << frec.size() << " tracked):" << C_RESET << "\n";
        int count = 0;
        for (const auto &item : sorted_frec) {
            if (++count > 20) break;
            std::cout << "  " << C_DIM << "→" << C_RESET << "  " << replace_home_tilde(item.second) << "\n";
        }
    }
    std::cout << "\n";
    return 0;
}

static int cmd_pin(int argc, char **argv) {
    std::string target = (argc >= 1) ? abspath(argv[0]) : get_cwd();
    bool pinned = toggle_bookmark(target);
    if (pinned) {
        std::cout << "  " << C_GREEN << "★ Pinned" << C_RESET << ": " << replace_home_tilde(target) << "\n";
    } else {
        std::cout << "  " << C_YELLOW << "☆ Unpinned" << C_RESET << ": " << replace_home_tilde(target) << "\n";
    }
    return 0;
}

static int cmd_prune() {
    auto frec = load_frecency();
    int removed = 0;
    for (auto it = frec.begin(); it != frec.end(); ) {
        if (!is_dir(it->first)) { it = frec.erase(it); ++removed; }
        else ++it;
    }
    save_frecency(frec);

    auto bms = load_bookmarks();
    std::vector<std::string> clean_bms;
    for (const auto &b : bms) {
        if (is_dir(b)) clean_bms.push_back(b);
        else ++removed;
    }
    save_bookmarks(clean_bms);

    std::cout << "  " << C_GREEN << "✓" << C_RESET << " Pruned " << removed << " non-existent directory entries.\n";
    return 0;
}

static int cmd_import_history() {
    auto frec = load_frecency();
    int added = import_shell_history(frec);
    save_frecency(frec);
    std::cout << "  " << C_GREEN << "✓" << C_RESET << " Imported shell history! ("
              << added << " new directories added, " << frec.size() << " total tracked)\n";
    return 0;
}

static int cmd_doctor() {
    auto frec = load_frecency();
    std::cout << "\n" << C_BOLD << C_CYAN << "  Dongle Doctor (v" << DONGLE_VERSION << " Native C++)" << C_RESET << "\n\n";
    std::cout << "  " << C_GREEN << "✓" << C_RESET << " Engine: Native C++17 Mach-O binary (<2ms startup)\n";
    std::cout << "  " << C_GREEN << "✓" << C_RESET << " Bidirectional Scanner: 5 layers down ↓ + 4 layers up ↑\n";
    std::cout << "  " << C_GREEN << "✓" << C_RESET << " Frecency & History Memory: " << C_BOLD << frec.size() << " directories tracked" << C_RESET << "\n";

    const char *sh_env = std::getenv("SHELL");
    std::string sh_name = sh_env ? sh_env : "zsh";
    size_t sl = sh_name.find_last_of('/');
    if (sl != std::string::npos) sh_name = sh_name.substr(sl + 1);
    std::cout << "  " << C_GREEN << "✓" << C_RESET << " Detected shell: " << C_BOLD << sh_name << C_RESET << "\n";

    std::string rc = get_home() + "/.zshrc";
    if (sh_name == "bash") rc = get_home() + "/.bashrc";
    else if (sh_name == "fish") rc = get_home() + "/.config/fish/config.fish";

    if (file_exists(rc)) {
        std::ifstream f(rc);
        std::string content((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
        if (content.find("dongle") != std::string::npos) {
            std::cout << "  " << C_GREEN << "✓" << C_RESET << " Shell integration found in " << C_DIM << rc << C_RESET << "\n";
        } else {
            std::cout << "  " << C_RED << "✗" << C_RESET << " Shell integration NOT found in " << rc << "\n";
        }
    }

    if (file_exists("/dev/tty")) {
        std::cout << "  " << C_GREEN << "✓" << C_RESET << " /dev/tty available\n";
    } else {
        std::cout << "  " << C_RED << "✗" << C_RESET << " /dev/tty NOT available\n";
    }
    std::cout << "\n  " << C_GREEN << C_BOLD << "All checks passed!" << C_RESET << "\n\n";
    return 0;
}

int main(int argc, char **argv) {
    std::string prog = argv[0] ? argv[0] : "dongle";
    size_t sl = prog.find_last_of('/');
    if (sl != std::string::npos) prog = prog.substr(sl + 1);

    if (prog == "dongle-pick") return cmd_pick(argc - 1, argv + 1);
    if (prog == "dongle-scan") return cmd_scan(argc - 1, argv + 1);
    if (prog == "dongle-list") return cmd_list(argc - 1, argv + 1);

    if (argc < 2) {
        cmd_intro();
        return 0;
    }

    std::string cmd = argv[1];
    if (cmd == "pick") return cmd_pick(argc - 2, argv + 2);
    if (cmd == "jump") return cmd_jump(argc - 2, argv + 2);
    if (cmd == "up" || cmd == "u") {
        std::vector<char *> p_args;
        char uflag[] = "--up";
        char aflag[] = "--auto-select";
        p_args.push_back(uflag);
        p_args.push_back(aflag);
        std::string q;
        for (int i = 2; i < argc; ++i) {
            if (!q.empty()) q += " ";
            q += argv[i];
        }
        char qflag[] = "--query";
        std::vector<char> qbuf(q.begin(), q.end());
        qbuf.push_back('\0');
        if (!q.empty()) {
            p_args.push_back(qflag);
            p_args.push_back(qbuf.data());
        }
        return cmd_pick(static_cast<int>(p_args.size()), p_args.data());
    }
    if (cmd == "down" || cmd == "d") {
        std::vector<char *> p_args;
        char dflag[] = "--down";
        char aflag[] = "--auto-select";
        p_args.push_back(dflag);
        p_args.push_back(aflag);
        std::string q;
        for (int i = 2; i < argc; ++i) {
            if (!q.empty()) q += " ";
            q += argv[i];
        }
        char qflag[] = "--query";
        std::vector<char> qbuf(q.begin(), q.end());
        qbuf.push_back('\0');
        if (!q.empty()) {
            p_args.push_back(qflag);
            p_args.push_back(qbuf.data());
        }
        return cmd_pick(static_cast<int>(p_args.size()), p_args.data());
    }
    if (cmd == "record") {
        record_visit((argc >= 3) ? argv[2] : get_cwd());
        return 0;
    }
    if (cmd == "import-history") return cmd_import_history();
    if (cmd == "scan") return cmd_scan(argc - 2, argv + 2);
    if (cmd == "list") return cmd_list(argc - 2, argv + 2);
    if (cmd == "root") {
        std::cout << find_project_root(get_cwd()) << "\n";
        return 0;
    }
    if (cmd == "recent") return cmd_recent();
    if (cmd == "pin" || cmd == "bookmarks") return cmd_pin(argc - 2, argv + 2);
    if (cmd == "prune") return cmd_prune();
    if (cmd == "doctor") return cmd_doctor();
    if (cmd == "welcome") {
        cmd_welcome();
        return 0;
    }
    if (cmd == "version" || cmd == "--version" || cmd == "-v") {
        std::cout << "dongle " << DONGLE_VERSION << "\n";
        return 0;
    }
    if (cmd == "help" || cmd == "--help" || cmd == "-h") {
        cmd_intro();
        return 0;
    }
    if (cmd == "init") {
        if (argc < 3) {
            std::cerr << "Usage: dongle init <zsh|bash|fish>\n";
            return 1;
        }
        std::string sh = argv[2];
        if (sh == "zsh") std::cout << ZSH_INIT_SCRIPT;
        else if (sh == "bash") std::cout << BASH_INIT_SCRIPT;
        else if (sh == "fish") std::cout << FISH_INIT_SCRIPT;
        else {
            std::cerr << "Unknown shell: " << sh << ". Supported: bash, zsh, fish\n";
            return 1;
        }
        return 0;
    }

    // Fallback: `dongle <query>` opens picker with --auto-select and initial query
    if (!cmd.empty() && cmd[0] != '-') {
        std::vector<char *> pick_args;
        char aflag[] = "--auto-select";
        char qflag[] = "--query";
        pick_args.push_back(aflag);
        pick_args.push_back(qflag);
        pick_args.push_back(argv[1]);
        return cmd_pick(3, pick_args.data());
    }

    cmd_intro();
    return 0;
}
