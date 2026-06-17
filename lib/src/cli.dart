import 'dart:io';
import 'package:args/args.dart';
import 'package:path/path.dart' as p;
import 'config.dart';
import 'scanner.dart';
import 'ui.dart';
import 'frecency.dart';

void cmdPick(List<String> args) {
  final parser = ArgParser()
    ..addFlag('workspace', abbr: 'w', defaultsTo: false)
    ..addOption('query', abbr: 'q', defaultsTo: '');

  final parsed = parser.parse(args);
  bool isWorkspace = parsed['workspace'] as bool;
  String query = parsed['query'] as String;

  String root = Directory.current.path;
  if (!isWorkspace) {
    root = Scanner().findProjectRoot(root);
  }

  final picker = DonglePicker(root: root, cwd: Directory.current.path);
  var chosen = picker.run(isWorkspace: isWorkspace, initialQuery: query);

  if (chosen != null) {
    String fullPath;
    if (chosen is List) {
      fullPath = chosen[1] as String;
    } else {
      fullPath = (chosen == '.') ? root : p.join(root, chosen as String);
    }
    Frecency().recordVisit(fullPath);
    print(fullPath);
  } else {
    exit(1);
  }
}

void cmdScan(List<String> args) {
  final parser = ArgParser()
    ..addFlag('workspace', abbr: 'w', defaultsTo: false);

  final parsed = parser.parse(args);
  bool isWorkspace = parsed['workspace'] as bool;

  String root = parsed.rest.isNotEmpty
      ? File(parsed.rest.first).absolute.path
      : Scanner().findProjectRoot(Directory.current.path);

  stderr.writeln("Scanning " + (isWorkspace ? "workspaces" : root) + "...");

  final scanner = Scanner();
  var paths = scanner.scanPaths(root, isWorkspace: isWorkspace);

  String cacheKey = isWorkspace ? "WORKSPACE:\$root" : root;
  scanner.saveCache(cacheKey, paths);

  stderr.writeln("Cached " + paths.length.toString() + " paths");
}

void cmdList(List<String> args) {
  String root = args.isNotEmpty
      ? File(args.first).absolute.path
      : Directory.current.path;
  root = Scanner().findProjectRoot(root);
  final paths = Scanner().getPaths(root);
  for (var path in paths) {
    print(path);
  }
}

void cmdRoot() {
  print(Scanner().findProjectRoot(Directory.current.path));
}

void cmdRecent() {
  var dirs = Frecency().getRecentDirs(20);
  if (dirs.isEmpty) {
    print(
      "\x1B[2m  No recent directories yet. Start navigating with dg or /\x1B[0m",
    );
    return;
  }
  print("\n\x1B[1m  Recent directories:\x1B[0m");
  final home = Platform.isWindows
      ? Platform.environment['USERPROFILE']!
      : Platform.environment['HOME']!;
  for (var d in dirs) {
    String display = d.replaceFirst(home, '~');
    print("  \x1B[2m→\x1B[0m  \$display");
  }
  print("");
}

void cmdInit(List<String> args) {
  if (args.isEmpty) {
    stderr.writeln("Usage: dongle init <shell>");
    stderr.writeln("  Supported shells: bash, zsh, fish");
    exit(1);
  }

  String shell = args.first;
  if (shell == "zsh") {
    print('''
# Dongle — Zsh Integration
__dongle_widget() {
    local chosen
    chosen="\$(dongle pick 2>/dev/tty)"

    if [ \$? -eq 0 ] && [ -n "\$chosen" ]; then
        if [ -z "\$BUFFER" ]; then
            cd "\$chosen"
            local display="\${chosen/#\$HOME/~}"
            zle -M "  → \$display"
            zle reset-prompt
        else
            LBUFFER="\${LBUFFER}\${chosen}"
        fi
    fi
    zle reset-prompt
}

__dongle_slash() {
    if [ -z "\$BUFFER" ]; then
        if [[ -c /dev/tty ]] && { true </dev/tty; } 2>/dev/null; then
            __dongle_widget
        else
            LBUFFER="\${LBUFFER}/"
        fi
    else
        LBUFFER="\${LBUFFER}/"
    fi
}

zle -N __dongle_widget
zle -N __dongle_slash

bindkey "/"   __dongle_slash
bindkey "^_"  __dongle_widget
bindkey "^O"  __dongle_widget

dg() {
    local chosen
    chosen="\$(dongle pick --query "\$*" 2>/dev/tty)"
    [ \$? -eq 0 ] && [ -n "\$chosen" ] && cd "\$chosen"
}
dgs() { dongle scan "\$@"; }
dgw() {
    local chosen
    chosen="\$(dongle pick --workspace --query "\$*" </dev/tty 2>/dev/tty)"
    [ \$? -eq 0 ] && [ -n "\$chosen" ] && cd "\$chosen"
}
dgws() { dongle scan --workspace "\$@"; }
dgr() {
    local root
    root="\$(dongle root)"
    [ \$? -eq 0 ] && [ -n "\$root" ] && cd "\$root" && echo "  → \${root/#\$HOME/~}"
}
dgl() { dongle list "\$@"; }
dgrecent() { dongle recent; }
''');
  } else if (shell == "bash") {
    print('''
# Dongle — Bash Integration
__dongle_widget() {
    local chosen
    chosen="\$(dongle pick </dev/tty 2>/dev/tty)"
    if [ \$? -eq 0 ] && [ -n "\$chosen" ]; then
        if [ -z "\${READLINE_LINE}" ]; then
            printf '\\e[2K\\r'
            cd "\$chosen"
            local display="\${chosen/#\$HOME/~}"
            printf "  → %s\\n" "\$display"
            # Bash history substitution reset
            history -s "\$READLINE_LINE"
        else
            READLINE_LINE="\${READLINE_LINE:0:\${READLINE_POINT}}\${chosen}\${READLINE_LINE:\${READLINE_POINT}}"
            READLINE_POINT=\$((\${READLINE_POINT} + \${#chosen}))
        fi
    fi
}

__dongle_slash() {
    if [ -z "\${READLINE_LINE}" ]; then
        if [[ -c /dev/tty ]] && { true </dev/tty; } 2>/dev/null; then
            __dongle_widget
        else
            READLINE_LINE="/"
            READLINE_POINT=1
        fi
    else
        READLINE_LINE="\${READLINE_LINE:0:\${READLINE_POINT}}/\${READLINE_LINE:\${READLINE_POINT}}"
        READLINE_POINT=\$((\${READLINE_POINT} + 1))
    fi
}

bind -x '"\\C-o": __dongle_widget'
bind -x '"\\C-_": __dongle_widget'
bind -x '"/": __dongle_slash'

dg() {
    local chosen
    chosen="\$(dongle pick --query "\$*" </dev/tty 2>/dev/tty)"
    [ \$? -eq 0 ] && [ -n "\$chosen" ] && cd "\$chosen"
}
dgs() { dongle scan "\$@"; }
dgw() {
    local chosen
    chosen="\$(dongle pick --workspace --query "\$*" </dev/tty 2>/dev/tty)"
    [ \$? -eq 0 ] && [ -n "\$chosen" ] && cd "\$chosen"
}
dgws() { dongle scan --workspace "\$@"; }
dgr() {
    local root
    root="\$(dongle root)"
    [ \$? -eq 0 ] && [ -n "\$root" ] && cd "\$root" && echo "  → \${root/#\$HOME/~}"
}
dgl() { dongle list "\$@"; }
dgrecent() { dongle recent; }
''');
  } else if (shell == "fish") {
    print('''
# Dongle — Fish Integration
function __dongle_widget
    set -l chosen (dongle pick 2>/dev/tty)
    if test \$status -eq 0; and test -n "\$chosen"
        set -l current_cmd (commandline)
        if test -z "\$current_cmd"
            cd "\$chosen"
            set -l display (string replace -r '^'"\$HOME"'/' '~/' "\$chosen")
            echo "  → \$display"
            commandline -f repaint
        else
            commandline -i "\$chosen"
        end
    end
    commandline -f repaint
end

function __dongle_slash
    set -l current_cmd (commandline)
    if test -z "\$current_cmd"
        if test -c /dev/tty
            __dongle_widget
        else
            commandline -i "/"
        end
    else
        commandline -i "/"
    end
end

bind / __dongle_slash
bind \\co __dongle_widget
bind \\c_ __dongle_widget

function dg
    set -l chosen (dongle pick --query "\$argv" 2>/dev/tty)
    if test \$status -eq 0; and test -n "\$chosen"
        cd "\$chosen"
    end
end

function dgw
    set -l chosen (dongle pick --workspace --query "\$argv" </dev/tty 2>/dev/tty)
    if test \$status -eq 0; and test -n "\$chosen"
        cd "\$chosen"
    end
end

function dgs
    dongle scan \$argv
end

function dgws
    dongle scan --workspace \$argv
end

function dgr
    set -l p_root (dongle root)
    if test \$status -eq 0; and test -n "\$p_root"
        cd "\$p_root"
        set -l display (string replace -r '^'"\$HOME"'/' '~/' "\$p_root")
        echo "  → \$display"
    end
end

function dgl
    dongle list \$argv
end

function dgrecent
    dongle recent
end
''');
  } else {
    stderr.writeln("Unknown shell: \$shell. Supported: bash, zsh, fish");
    exit(1);
  }
}

void cmdDoctor() {
  print("\\n\x1B[1m\x1B[36m  Dongle Doctor (Dart Edition)\x1B[0m\\n");
  int issues = 0;

  print("  \x1B[32m✓\x1B[0m Running as standalone Dart binary");

  String shellName = p.basename(Platform.environment['SHELL'] ?? 'unknown');
  print("  \x1B[32m✓\x1B[0m Detected shell: \x1B[1m\${shellName}\x1B[0m");

  final home = Platform.environment['HOME'];
  if (home != null) {
    Map<String, String> rcFiles = {
      "zsh": "\$home/.zshrc",
      "bash": "\$home/.bashrc",
      "fish": "\$home/.config/fish/config.fish",
    };

    String? rcFile = rcFiles[shellName];
    if (rcFile != null && File(rcFile).existsSync()) {
      String content = File(rcFile).readAsStringSync();
      if (content.contains("dongle")) {
        print(
          "  \x1B[32m✓\x1B[0m Shell integration found in \x1B[2m\${rcFile}\x1B[0m",
        );
      } else {
        print("  \x1B[31m✗\x1B[0m Shell integration NOT found in \${rcFile}");
        issues++;
      }
    }
  }

  if (File('/dev/tty').existsSync()) {
    print("  \x1B[32m✓\x1B[0m /dev/tty available");
  } else {
    print(
      "  \x1B[31m✗\x1B[0m /dev/tty NOT available (picker won't work in this exact terminal)",
    );
  }

  final configPath = DongleConfig().configFile.path;
  if (DongleConfig().configFile.existsSync()) {
    print(
      "  \x1B[32m✓\x1B[0m Configuration found at \x1B[2m\${configPath}\x1B[0m",
    );
  } else {
    print("  \x1B[31m✗\x1B[0m Configuration NOT found. Will create defaults.");
    issues++;
  }

  print("");
  if (issues == 0) {
    print("  \x1B[32m\x1B[1mAll checks passed!\x1B[0m");
  } else {
    print("  \x1B[31m\x1B[1m\${issues} issue(s) found.\x1B[0m");
  }
  print("");
}

void cmdIntro() {
  print('''
\x1B[1m\x1B[36m  Dongle\x1B[0m — Lightning-fast fuzzy directory navigation (Dart Edition)
\x1B[2m  https://github.com/jeremiahseun/dongle\x1B[0m

\x1B[1m  Navigation:\x1B[0m
    \x1B[32mdg\x1B[0m            Open directory search (current project)
    \x1B[32mdg <query>\x1B[0m    Open search pre-filled with query
    \x1B[32mdgw\x1B[0m           Workspace search (across all projects)
    \x1B[32mdgr\x1B[0m           Jump to project root immediately
    \x1B[32mdgl\x1B[0m           List all cached paths
    \x1B[32m/\x1B[0m             Press on empty prompt to search

\x1B[1m  Commands:\x1B[0m
    dongle init <shell>   Output shell integration (bash/zsh/fish)
    dongle root           Print current project root
    dongle recent         Show recently visited directories
    dongle scan           Pre-scan & cache current directory
    dongle doctor         Check if everything is set up correctly
    dongle version        Show version

\x1B[1m  Picker keys:\x1B[0m
    \x1B[2m↑↓ / Ctrl+P/N\x1B[0m  Navigate results
    \x1B[2mEnter\x1B[0m           Go to selected directory
    \x1B[2mCtrl+W\x1B[0m          Switch to workspace search
    \x1B[2mCtrl+R\x1B[0m          Rescan directory (refresh cache)
    \x1B[2mCtrl+U\x1B[0m          Clear query
    \x1B[2mEsc / Ctrl+C\x1B[0m    Cancel

\x1B[1m  Setup:\x1B[0m
    Add to your ~/.zshrc (or equivalent):
    \x1B[2meval "\$(dongle init zsh)"\x1B[0m
''');
}

void cmdVersion() {
  print("dongle " + DongleConfig.version);
}
