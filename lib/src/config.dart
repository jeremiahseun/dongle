import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:yaml/yaml.dart';

class DongleConfig {
  static const String version = "0.4.0";

  late final File cacheFile;
  late final File frecencyFile;
  late final File configFile;

  Set<String> skipDirs = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".cache",
    ".npm",
    ".yarn",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "venv",
    ".venv",
    "env",
    ".env",
    ".tox",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    "coverage",
    ".mypy_cache",
    ".pytest_cache",
  };

  Set<String> rootMarkers = {
    ".git",
    ".svn",
    ".hg",
    "package.json",
    "pubspec.yaml",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Makefile",
  };

  int cacheTtl = 300;
  int maxDepth = 6;
  int workspaceDepth = 4;
  int maxDirs = 5000;
  List<String> workspaces = [];

  static final DongleConfig _instance = DongleConfig._internal();
  factory DongleConfig() => _instance;

  DongleConfig._internal() {
    final home = _getHomeDir();
    cacheFile = File(p.join(home, '.dongle_cache.json'));
    frecencyFile = File(p.join(home, '.dongle_frecency.json'));

    final configDir = Directory(p.join(home, '.config', 'dongle'));
    if (!configDir.existsSync()) {
      configDir.createSync(recursive: true);
    }
    configFile = File(p.join(configDir.path, 'config.yaml'));

    _loadConfig();
  }

  String _getHomeDir() {
    if (Platform.isWindows) {
      return Platform.environment['USERPROFILE'] ?? '';
    }
    return Platform.environment['HOME'] ?? '';
  }

  void _loadConfig() {
    if (!configFile.existsSync()) {
      _writeDefaultConfig();
      return;
    }

    try {
      final String yamlString = configFile.readAsStringSync();
      final yaml = loadYaml(yamlString) as YamlMap?;
      if (yaml == null) return;

      if (yaml['cache_ttl'] is int) cacheTtl = yaml['cache_ttl'] as int;
      if (yaml['max_depth'] is int) maxDepth = yaml['max_depth'] as int;
      if (yaml['workspace_depth'] is int)
        workspaceDepth = yaml['workspace_depth'] as int;
      if (yaml['max_dirs'] is int) maxDirs = yaml['max_dirs'] as int;

      if (yaml['workspaces'] is YamlList) {
        workspaces = (yaml['workspaces'] as YamlList)
            .map((e) => e.toString())
            .toList();
      }

      if (yaml['skip_dirs'] is YamlList) {
        skipDirs.addAll(
          (yaml['skip_dirs'] as YamlList).map((e) => e.toString()),
        );
      }
    } catch (e) {
      stderr.writeln("Warning: Failed to parse config.yaml: $e");
    }
  }

  void _writeDefaultConfig() {
    final String defaultConfig = '''
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
  # - ~/Documents/GitHub
  # - ~/Projects

# Extra directories to skip
skip_dirs:
  # - tmp
  # - .output
''';
    try {
      configFile.writeAsStringSync(defaultConfig);
    } catch (e) {
      // Ignore write errors on initial setup
    }
  }
}
