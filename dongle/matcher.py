import re
import heapq

_SEP = re.compile(r"[ /\\]+")
_DISPLAY_LIMIT = 50   # keep top N candidates; we show at most 15


def _score(q: str, q_segs_wrapped: list, path_lower: str, path_len: int) -> int:
    """
    Score a single path against a pre-processed query.

    q              : lowercased full query string
    q_segs_wrapped : query segments pre-wrapped with '/' for fast substring checks
    path_lower     : already-lowercased path
    path_len       : len(original path)
    """
    if q == path_lower:
        return 1_000_000

    score = 0

    # Substring match — most common fast path, checked before segment split
    idx = path_lower.find(q)
    if idx >= 0:
        # Segment-exact bonus on top of substring score
        # Optimized: Wrapping the path and segments in '/' avoids overhead from split()
        if q_segs_wrapped:
            path_wrapped = f"/{path_lower}/"
            for qsw in q_segs_wrapped:
                if qsw in path_wrapped:
                    score += 50_000
        score += 10_000 - idx
        return score

    # Segment-exact bonus (no full substring match)
    if q_segs_wrapped:
        path_wrapped = f"/{path_lower}/"
        for qsw in q_segs_wrapped:
            if qsw in path_wrapped:
                score += 50_000

    # If we already have segment bonus points, return without fuzzy
    if score > 0:
        return score

    # Fuzzy character-sequence match (most expensive, last resort)
    # Optimized: Using C-optimized `str.find` instead of a manual Python loop
    # significantly improves performance on fallback fuzzy matches.
    idx = -1
    for c in q:
        idx = path_lower.find(c, idx + 1)
        if idx == -1:
            return 0

    return 1_000 - path_len


def search(query: str, paths: list, frecency: dict = None) -> list:
    """
    Filter and rank paths against query.

    - Pre-computes query segments once (not per path).
    - Applies frecency boost when provided.
    - Returns paths sorted best-first.
    """
    if not paths:
        return []

    # Optimized: Hoisting the isinstance check outside the loop avoids evaluating
    # it thousands of times per keystroke during filtering and sorting.
    is_tuple = isinstance(paths[0], (tuple, list))

    if not query:
        if frecency:
            if is_tuple:
                return sorted(paths, key=lambda p: (-frecency.get(p[1], 0), len(p[0])))
            else:
                return sorted(paths, key=lambda p: (-frecency.get(p, 0), len(p)))
        else:
            if is_tuple:
                return sorted(paths, key=lambda p: len(p[0]))
            else:
                return sorted(paths, key=len)

    q = query.lower()
    q_segs = [s for s in _SEP.split(q) if s]
    # PRE-COMPUTE: wrapping query segments in '/' to allow fast substring check
    q_segs_wrapped = [f"/{s}/" for s in q_segs]

    scored = []
    if is_tuple:
        for p in paths:
            display = p[0]
            s = _score(q, q_segs_wrapped, display.lower(), len(display))
            if s > 0:
                if frecency:
                    s += frecency.get(p[1], 0) * 10
                scored.append((s, p))
    else:
        for p in paths:
            s = _score(q, q_segs_wrapped, p.lower(), len(p))
            if s > 0:
                if frecency:
                    s += frecency.get(p, 0) * 10
                scored.append((s, p))

    if not scored:
        return []

    # Partial sort: only need the top _DISPLAY_LIMIT entries
    if len(scored) > _DISPLAY_LIMIT:
        if is_tuple:
            top = heapq.nlargest(_DISPLAY_LIMIT, scored, key=lambda x: (x[0], -len(x[1][0])))
            top.sort(key=lambda x: (-x[0], len(x[1][0])))
        else:
            top = heapq.nlargest(_DISPLAY_LIMIT, scored, key=lambda x: (x[0], -len(x[1])))
            top.sort(key=lambda x: (-x[0], len(x[1])))
        return [p for _, p in top]

    if is_tuple:
        scored.sort(key=lambda x: (-x[0], len(x[1][0])))
    else:
        scored.sort(key=lambda x: (-x[0], len(x[1])))
    return [p for _, p in scored]
