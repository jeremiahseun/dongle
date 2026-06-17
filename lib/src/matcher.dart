const int _displayLimit = 50;

class MatchResult implements Comparable<MatchResult> {
  final int score;
  final int length;
  final int index;
  final dynamic path;

  MatchResult(this.score, this.length, this.index, this.path);

  @override
  int compareTo(MatchResult other) {
    if (score != other.score) return other.score.compareTo(score);
    if (length != other.length) return length.compareTo(other.length);
    return index.compareTo(other.index);
  }
}

int _score(String q, List<String> qSegsWrapped, String pathLower, int pathLen) {
  if (q == pathLower) return 1000000;

  int score = 0;

  int idx = pathLower.indexOf(q);
  if (idx >= 0) {
    if (qSegsWrapped.isNotEmpty) {
      String pathWrapped = '/$pathLower/';
      for (final qsw in qSegsWrapped) {
        if (pathWrapped.contains(qsw)) {
          score += 50000;
        }
      }
    }
    score += 10000 - idx;
    return score;
  }

  if (qSegsWrapped.isNotEmpty) {
    String pathWrapped = '/$pathLower/';
    for (final qsw in qSegsWrapped) {
      if (pathWrapped.contains(qsw)) {
        score += 50000;
      }
    }
  }

  if (score > 0) return score;

  idx = -1;
  for (int i = 0; i < q.length; i++) {
    idx = pathLower.indexOf(q[i], idx + 1);
    if (idx == -1) return 0;
  }

  return 1000 - pathLen;
}

List<dynamic> search(
  String query,
  List<dynamic> paths, {
  Map<String, int>? frecency,
}) {
  if (paths.isEmpty) return [];

  bool isTuple = paths[0] is List;

  if (query.isEmpty) {
    if (frecency != null && frecency.isNotEmpty) {
      var scored = <MatchResult>[];
      for (int i = 0; i < paths.length; i++) {
        var p = paths[i];
        if (isTuple) {
          int score = frecency[p[1]] ?? 0;
          scored.add(MatchResult(score, (p[0] as String).length, i, p));
        } else {
          int score = frecency[p] ?? 0;
          scored.add(MatchResult(score, (p as String).length, i, p));
        }
      }
      scored.sort();
      return scored.map((e) => e.path).toList();
    } else {
      var sortedPaths = List<dynamic>.from(paths);
      if (isTuple) {
        sortedPaths.sort(
          (a, b) => (a[0] as String).length.compareTo((b[0] as String).length),
        );
      } else {
        sortedPaths.sort(
          (a, b) => (a as String).length.compareTo((b as String).length),
        );
      }
      return sortedPaths;
    }
  }

  String q = query.toLowerCase();
  final sepRegex = RegExp(r'[ /\\]+');
  List<String> qSegs = q.split(sepRegex).where((s) => s.isNotEmpty).toList();
  List<String> qSegsWrapped = qSegs.map((s) => '/$s/').toList();

  var scored = <MatchResult>[];

  if (isTuple) {
    for (int i = 0; i < paths.length; i++) {
      var p = paths[i];
      String display = p[0] as String;
      int displayLen = display.length;
      int s = _score(q, qSegsWrapped, display.toLowerCase(), displayLen);
      if (s > 0) {
        if (frecency != null && frecency.isNotEmpty) {
          s += (frecency[p[1]] ?? 0) * 10;
        }
        scored.add(MatchResult(s, displayLen, i, p));
      }
    }
  } else {
    for (int i = 0; i < paths.length; i++) {
      var p = paths[i];
      String pStr = p as String;
      int pLen = pStr.length;
      int s = _score(q, qSegsWrapped, pStr.toLowerCase(), pLen);
      if (s > 0) {
        if (frecency != null && frecency.isNotEmpty) {
          s += (frecency[pStr] ?? 0) * 10;
        }
        scored.add(MatchResult(s, pLen, i, pStr));
      }
    }
  }

  if (scored.isEmpty) return [];

  scored.sort();

  if (scored.length > _displayLimit) {
    return scored.take(_displayLimit).map((e) => e.path).toList();
  }

  return scored.map((e) => e.path).toList();
}
