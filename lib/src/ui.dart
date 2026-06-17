import 'dart:io';
import 'dart:math';
import 'scanner.dart';
import 'frecency.dart';
import 'matcher.dart';

class PickerState {
  bool isWorkspace;
  List<dynamic> paths;
  List<dynamic> filtered;
  int index;
  String query;
  dynamic chosen;
  bool isScanning;

  PickerState({
    required this.isWorkspace,
    required this.paths,
    required this.filtered,
    this.index = 0,
    this.query = '',
    this.isScanning = false,
  });
}

class DonglePicker {
  final String root;
  final String? cwd;
  final Scanner scanner;
  final Frecency frecency;
  late Map<String, int> frecencyScores;

  DonglePicker({required this.root, this.cwd})
    : scanner = Scanner(),
      frecency = Frecency();

  dynamic run({
    bool isWorkspace = false,
    String initialQuery = '',
    List<dynamic>? preloadedPaths,
  }) {
    frecencyScores = frecency.getFrecencyScores();

    var paths =
        preloadedPaths ?? scanner.scanPaths(root, isWorkspace: isWorkspace);
    var filtered = search(initialQuery, paths, frecency: frecencyScores);

    var state = PickerState(
      isWorkspace: isWorkspace,
      paths: paths,
      filtered: filtered,
      query: initialQuery,
    );

    stdin.echoMode = false;
    stdin.lineMode = false;

    try {
      _render(state);

      while (true) {
        int byte = stdin.readByteSync();
        if (byte == -1) break;

        if (byte == 27) {
          // Escape sequence
          int next1 = stdin.readByteSync();
          if (next1 == 91) {
            // [
            int next2 = stdin.readByteSync();
            if (next2 == 65) {
              // Up
              _up(state);
            } else if (next2 == 66) {
              // Down
              _down(state);
            }
          } else {
            // Just Escape
            break;
          }
        } else if (byte == 3 || byte == 27) {
          // Ctrl+C or Escape
          break;
        } else if (byte == 13) {
          // Enter
          if (state.filtered.isNotEmpty) {
            state.chosen = state.filtered[state.index];
          }
          break;
        } else if (byte == 16) {
          // Ctrl+P (Up)
          _up(state);
        } else if (byte == 14) {
          // Ctrl+N (Down)
          _down(state);
        } else if (byte == 21) {
          // Ctrl+U
          state.query = '';
          state.filtered = search(
            state.query,
            state.paths,
            frecency: frecencyScores,
          );
          state.index = 0;
        } else if (byte == 23) {
          // Ctrl+W
          if (!state.isWorkspace) {
            state.isWorkspace = true;
            state.isScanning = true;
            _render(state);
            String wsRoot = scanner.findProjectRoot(
              cwd ?? Directory.current.path,
            );
            state.paths = scanner.scanPaths(wsRoot, isWorkspace: true);
            state.isScanning = false;
            state.filtered = search(
              state.query,
              state.paths,
              frecency: frecencyScores,
            );
            state.index = 0;
          }
        } else if (byte == 18) {
          // Ctrl+R
          state.isScanning = true;
          _render(state);
          state.paths = scanner.scanPaths(root, isWorkspace: state.isWorkspace);
          scanner.saveCache(
            state.isWorkspace ? "WORKSPACE:\$root" : root,
            state.paths,
          );
          state.isScanning = false;
          state.filtered = search(
            state.query,
            state.paths,
            frecency: frecencyScores,
          );
          state.index = 0;
        } else if (byte == 127 || byte == 8) {
          // Backspace
          if (state.query.isNotEmpty) {
            state.query = state.query.substring(0, state.query.length - 1);
            state.filtered = search(
              state.query,
              state.paths,
              frecency: frecencyScores,
            );
            state.index = 0;
          }
        } else {
          // Printable characters
          if (byte >= 32 && byte <= 126) {
            String c = String.fromCharCode(byte);
            String oldQuery = state.query;
            state.query += c;

            List<dynamic> pathsToSearch = state.paths;
            if (oldQuery.isNotEmpty && state.filtered.length < 50) {
              pathsToSearch = state.filtered;
            }

            state.filtered = search(
              state.query,
              pathsToSearch,
              frecency: frecencyScores,
            );
            state.index = 0;
          }
        }

        _render(state);
      }
    } finally {
      stdin.echoMode = true;
      stdin.lineMode = true;
      stdout.write('\x1B[18B');
      stdout.write('\x1B[J');
      stdout.write('\r');
    }

    return state.chosen;
  }

  void _up(PickerState state) {
    if (state.filtered.isNotEmpty) {
      state.index = (state.index - 1) % state.filtered.length;
      if (state.index < 0) state.index += state.filtered.length;
    }
  }

  void _down(PickerState state) {
    if (state.filtered.isNotEmpty) {
      state.index = (state.index + 1) % state.filtered.length;
    }
  }

  void _render(PickerState state) {
    stdout.write('\r');

    String mode = state.isWorkspace ? "Workspace" : "Project";
    String home = Platform.isWindows
        ? Platform.environment['USERPROFILE']!
        : Platform.environment['HOME']!;
    String displayRoot = root.replaceFirst(home, '~');
    int nFiltered = state.filtered.length;
    int nTotal = state.paths.length;

    String status = state.isScanning
        ? "  [Scanning...]"
        : (state.query.isNotEmpty
              ? "  (\$nFiltered/\$nTotal)"
              : "  (\$nTotal dirs)");

    stdout.write('\x1B[1m\x1B[38;5;73m  \$mode  \x1B[0m');
    stdout.write('\x1B[38;5;117m\$displayRoot\x1B[0m');
    stdout.write('\x1B[38;5;242m\$status\x1B[0m\n\r');

    stdout.write('\x1B[1m\x1B[38;5;42m  / \x1B[0m');
    stdout.write('\x1B[1m\x1B[37m\${state.query}\x1B[0m');
    stdout.write('\x1B[38;5;42m█\x1B[0m\x1B[K\n\r');

    int start = max(0, state.index - 7);
    int end = min(state.filtered.length, start + 15);

    int linesRendered = 0;

    if (state.filtered.isEmpty) {
      if (state.query.isNotEmpty) {
        stdout.write('\x1B[38;5;242m    No matches.\x1B[0m\x1B[K\n\r');
        stdout.write(
          '\x1B[38;5;238m    Ctrl+W — search across workspaces\x1B[0m\x1B[K\n\r',
        );
        linesRendered += 2;
      } else {
        stdout.write(
          '\x1B[38;5;238m    Start typing to filter...\x1B[0m\x1B[K\n\r',
        );
        linesRendered += 1;
      }
    } else {
      for (int i = start; i < end; i++) {
        var p = state.filtered[i];
        String displayP = (p is List) ? p[0] as String : p as String;
        bool selected = (i == state.index);

        _renderResultLine(displayP, state.query, selected);
        linesRendered++;
      }
    }

    for (int i = linesRendered; i < 15; i++) {
      stdout.write('\x1B[K\n\r');
    }

    stdout.write(
      '\x1B[38;5;240m─────────────────────────────────────────────────────────\x1B[0m\n\r',
    );
    stdout.write(
      '\x1B[1m\x1B[38;5;243m ↑↓\x1B[0m\x1B[38;5;238m nav  \x1B[0m'
      '\x1B[1m\x1B[38;5;243mEnter\x1B[0m\x1B[38;5;238m select  \x1B[0m'
      '\x1B[1m\x1B[38;5;243m^W\x1B[0m\x1B[38;5;238m workspace  \x1B[0m'
      '\x1B[1m\x1B[38;5;243m^R\x1B[0m\x1B[38;5;238m rescan  \x1B[0m'
      '\x1B[1m\x1B[38;5;243m^U\x1B[0m\x1B[38;5;238m clear  \x1B[0m'
      '\x1B[1m\x1B[38;5;243mEsc\x1B[0m\x1B[38;5;238m cancel \x1B[0m\x1B[K',
    );

    stdout.write('\r\x1B[18A');
  }

  void _renderResultLine(String displayP, String query, bool selected) {
    String selBg = selected ? '\x1B[48;5;17m\x1B[1m\x1B[37m' : '\x1B[0m';
    String arrow = selected ? '❯ ' : '  ';
    String pad = '  ';

    if (query.isNotEmpty) {
      String qLo = query.toLowerCase();
      String pLo = displayP.toLowerCase();
      int idx = pLo.indexOf(qLo);

      if (idx >= 0) {
        String pre = displayP.substring(0, idx);
        String mid = displayP.substring(idx, idx + query.length);
        String post = displayP.substring(idx + query.length);

        String hi = selected
            ? '\x1B[48;5;17m\x1B[1m\x1B[38;5;214m'
            : '\x1B[1m\x1B[38;5;214m';

        stdout.write(
          '\$selBg\$pad\$arrow\$pre\$hi\$mid\$selBg\$post\x1B[0m\x1B[K\n\r',
        );
        return;
      }
    }

    stdout.write('\$selBg\$pad\$arrow\$displayP\x1B[0m\x1B[K\n\r');
  }
}
