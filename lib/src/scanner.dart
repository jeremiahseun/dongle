import 'dart:io';
import 'dart:convert';
import 'package:path/path.dart' as p;
import 'package:glob/glob.dart';
import 'config.dart';

class Scanner {
  final DongleConfig config = DongleConfig();

  String findProjectRoot(String startDir) {
    var curr = Directory(startDir).absolute;
    while (true) {
      for (final marker in config.rootMarkers) {
        if (File(p.join(curr.path, marker)).existsSync() ||
            Directory(p.join(curr.path, marker)).existsSync()) {
          return curr.path;
        }
      }
      final parent = curr.parent;
      if (parent.path == curr.path) {
        break; // reached filesystem root
      }
      curr = parent;
    }
    return Directory(startDir).absolute.path;
  }

  List<Glob> _loadIgnoreSpecs(String root) {
    List<Glob> globs = [];
    for (final filename in ['.gitignore', '.dongleignore']) {
      final file = File(p.join(root, filename));
      if (file.existsSync()) {
        final lines = file.readAsLinesSync();
        for (var line in lines) {
          line = line.trim();
          if (line.isNotEmpty && !line.startsWith('#')) {
            String pattern = line;
            if (pattern.startsWith('/')) {
              pattern = pattern.substring(1);
            }
            if (!pattern.contains('*')) {
              globs.add(Glob('**/$pattern/**'));
              globs.add(Glob('**/$pattern'));
            } else {
              globs.add(Glob(pattern));
              globs.add(Glob('**/$pattern'));
            }
          }
        }
      }
    }
    return globs;
  }

  String _expandUser(String path) {
    if (path.startsWith('~/') || path == '~') {
      final home = Platform.isWindows
          ? Platform.environment['USERPROFILE']
          : Platform.environment['HOME'];
      return path.replaceFirst('~', home!);
    }
    return path;
  }

  List<dynamic> scanPaths(String root, {bool isWorkspace = false}) {
    List<dynamic> paths = [];
    int maxDirs = config.maxDirs;

    if (isWorkspace) {
      int maxDepth = config.workspaceDepth;
      List<String> workspaceDirs = config.workspaces
          .map((d) => _expandUser(d))
          .toList();

      for (final wsDir in workspaceDirs) {
        final wsPath = Directory(wsDir);
        if (!wsPath.existsSync()) continue;

        final wsParentStr = wsPath.parent.path;
        final wsStr = wsPath.path;

        _walkDirectory(
          dir: wsPath,
          basePath: wsStr,
          baseParentPath: wsParentStr,
          ignoreSpecs: [],
          maxDepth: maxDepth,
          pathsList: paths,
          maxDirs: maxDirs,
          isWorkspace: true,
        );
        if (paths.length >= maxDirs) return paths;
      }
    } else {
      final ignoreSpecs = _loadIgnoreSpecs(root);
      final rootPath = Directory(root);
      int maxDepth = config.maxDepth;
      final rootStr = rootPath.path;

      _walkDirectory(
        dir: rootPath,
        basePath: rootStr,
        baseParentPath: rootStr,
        ignoreSpecs: ignoreSpecs,
        maxDepth: maxDepth,
        pathsList: paths,
        maxDirs: maxDirs,
        isWorkspace: false,
      );
    }

    return paths;
  }

  void _walkDirectory({
    required Directory dir,
    required String basePath,
    required String baseParentPath,
    required List<Glob> ignoreSpecs,
    required int maxDepth,
    required List<dynamic> pathsList,
    required int maxDirs,
    required bool isWorkspace,
    int currentDepth = 0,
  }) {
    if (pathsList.length >= maxDirs) return;
    if (currentDepth > maxDepth) return;

    List<FileSystemEntity> entities;
    try {
      entities = dir.listSync(recursive: false, followLinks: false);
    } catch (e) {
      return;
    }

    for (final entity in entities) {
      if (entity is Directory) {
        final dirName = p.basename(entity.path);
        if (config.skipDirs.contains(dirName)) continue;

        final relPath = p.relative(entity.path, from: basePath);

        if (!isWorkspace) {
          bool ignored = false;
          for (final glob in ignoreSpecs) {
            if (glob.matches(relPath)) {
              ignored = true;
              break;
            }
          }
          if (ignored) continue;

          pathsList.add(relPath);
        } else {
          final relRootPath = p.relative(entity.path, from: baseParentPath);
          pathsList.add([relRootPath, entity.path]);
        }

        if (pathsList.length >= maxDirs) return;

        _walkDirectory(
          dir: entity,
          basePath: basePath,
          baseParentPath: baseParentPath,
          ignoreSpecs: ignoreSpecs,
          maxDepth: maxDepth,
          pathsList: pathsList,
          maxDirs: maxDirs,
          isWorkspace: isWorkspace,
          currentDepth: currentDepth + 1,
        );
      }
    }
  }

  List<dynamic>? loadCache(String cacheKey) {
    if (!config.cacheFile.existsSync()) return null;
    try {
      final content = config.cacheFile.readAsStringSync();
      final data = jsonDecode(content) as Map<String, dynamic>;
      final entry = data[cacheKey];

      if (entry != null) {
        final timestamp = entry['timestamp'] as double;
        final now = DateTime.now().millisecondsSinceEpoch / 1000;
        if (now - timestamp < config.cacheTtl) {
          return entry['paths'] as List<dynamic>;
        }
      }
    } catch (e) {
      // ignore cache read errors
    }
    return null;
  }

  void saveCache(String cacheKey, List<dynamic> paths) {
    Map<String, dynamic> data = {};
    if (config.cacheFile.existsSync()) {
      try {
        data =
            jsonDecode(config.cacheFile.readAsStringSync())
                as Map<String, dynamic>;
      } catch (e) {
        // start fresh if corrupted
      }
    }
    data[cacheKey] = {
      'timestamp': DateTime.now().millisecondsSinceEpoch / 1000,
      'paths': paths,
    };
    try {
      config.cacheFile.writeAsStringSync(jsonEncode(data));
    } catch (e) {
      // ignore cache write errors
    }
  }

  List<dynamic> getPaths(String root) {
    var paths = loadCache(root);
    if (paths == null) {
      paths = scanPaths(root);
      saveCache(root, paths);
    }
    return paths;
  }
}
