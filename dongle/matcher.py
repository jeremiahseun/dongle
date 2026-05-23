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
            fget = frecency.get
            if is_tuple:
                return sorted(paths, key=lambda p: (-fget(p[1], 0), len(p[0])))
            else:
                return sorted(paths, key=lambda p: (-fget(p, 0), len(p)))
        else:
            if is_tuple:
                return sorted(paths, key=lambda p: len(p[0]))
            else:
                return sorted(paths, key=len)

    q = query.lower()
    q_segs = [s for s in _SEP.split(q) if s]
    # PRE-COMPUTE: wrapping query segments in '/' to allow fast substring check
    q_segs_wrapped = [f"/{s}/" for s in q_segs]

    # Pre-fetch frecency.get to avoid dictionary lookup overhead for the method
    # itself in the hot loop.
    fget = frecency.get if frecency else None

    # Optimized: List comprehensions are C-optimized and significantly faster than
    # manual `.append()` calls.
    # The `for s in (...)` trick binds the score result to a local variable
    # without requiring Python 3.8+ walrus operators (`:=`).
    # Adding negative length to the tuple ensures default sorting is correct:
    # high score first, then short length (closer to zero). This avoids calling
    # lambdas or len() entirely during sorting operations.
    if is_tuple:
        if fget:
            scored = [(s + fget(p[1], 0) * 10, -len(p[0]), p)
                      for p in paths
                      for s in (_score(q, q_segs_wrapped, p[0].lower(), len(p[0])),)
                      if s > 0]
        else:
            scored = [(s, -len(p[0]), p)
                      for p in paths
                      for s in (_score(q, q_segs_wrapped, p[0].lower(), len(p[0])),)
                      if s > 0]
    else:
        if fget:
            scored = [(s + fget(p, 0) * 10, -len(p), p)
                      for p in paths
                      for s in (_score(q, q_segs_wrapped, p.lower(), len(p)),)
                      if s > 0]
        else:
            scored = [(s, -len(p), p)
                      for p in paths
                      for s in (_score(q, q_segs_wrapped, p.lower(), len(p)),)
                      if s > 0]

    if not scored:
        return []

    # Partial sort: only need the top _DISPLAY_LIMIT entries
    # The list contains `(score, -length, item)` meaning natural sort `reverse=True`
    # correctly evaluates the highest score first, then least negative length (shortest string).
    if len(scored) > _DISPLAY_LIMIT:
        top = heapq.nlargest(_DISPLAY_LIMIT, scored)
        top.sort(reverse=True)
        return [p for _, _, p in top]

    scored.sort(reverse=True)
    return [p for _, _, p in scored]
