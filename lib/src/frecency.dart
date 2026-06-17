import 'dart:convert';
import 'config.dart';

class Frecency {
  static const int _maxEntries = 1000;
  final DongleConfig config = DongleConfig();

  Map<String, dynamic> _load() {
    if (!config.frecencyFile.existsSync()) {
      return {};
    }
    try {
      final content = config.frecencyFile.readAsStringSync();
      return jsonDecode(content) as Map<String, dynamic>;
    } catch (e) {
      return {};
    }
  }

  void _save(Map<String, dynamic> data) {
    try {
      config.frecencyFile.writeAsStringSync(jsonEncode(data));
    } catch (e) {
      // ignore write errors
    }
  }

  void recordVisit(String path) {
    var data = _load();
    final now = DateTime.now().millisecondsSinceEpoch / 1000.0;

    if (data.containsKey(path)) {
      data[path]['visits'] = (data[path]['visits'] as int) + 1;
      data[path]['last_visit'] = now;
    } else {
      data[path] = {'visits': 1, 'last_visit': now};
    }

    if (data.length > _maxEntries) {
      var entries = data.entries.toList()
        ..sort(
          (a, b) => (b.value['last_visit'] as double).compareTo(
            a.value['last_visit'] as double,
          ),
        );

      var trimmed = <String, dynamic>{};
      for (var i = 0; i < _maxEntries; i++) {
        trimmed[entries[i].key] = entries[i].value;
      }
      data = trimmed;
    }

    _save(data);
  }

  Map<String, int> getFrecencyScores() {
    final data = _load();
    if (data.isEmpty) return {};

    final now = DateTime.now().millisecondsSinceEpoch / 1000.0;
    Map<String, int> scores = {};

    data.forEach((path, info) {
      final visits = (info['visits'] as num?)?.toInt() ?? 1;
      final lastVisit = (info['last_visit'] as num?)?.toDouble() ?? 0.0;
      final age = now - lastVisit;

      double weight;
      if (age < 3600) {
        weight = 4;
      } else if (age < 86400) {
        weight = 2;
      } else if (age < 604800) {
        weight = 1;
      } else {
        weight = 0.5;
      }

      scores[path] = (visits * weight).toInt();
    });

    return scores;
  }

  List<String> getRecentDirs([int n = 10]) {
    final data = _load();
    if (data.isEmpty) return [];

    var entries = data.entries.toList()
      ..sort(
        (a, b) => (b.value['last_visit'] as num).compareTo(
          a.value['last_visit'] as num,
        ),
      );

    return entries.take(n).map((e) => e.key).toList();
  }
}
