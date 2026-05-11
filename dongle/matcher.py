import re
import heapq

_SEP = re.compile(r"[ /\\]+")
_DISPLAY_LIMIT = 50   # keep top N candidates; we show at most 15


def _score(q: str, q_segs_padded: list, path_lower: str, path_len: int) -> int:
    """
    Score a single path against a pre-processed query.

    q              : lowercased full query string
    q_segs_padded  : query segments surrounded by '/' (e.g. ['/src/'])
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
        if q_segs_padded:
            path_padded = f"/{path_lower}/"
            for qs in q_segs_padded:
                if qs in path_padded:
                    score += 50_000
        score += 10_000 - idx
        return score

    # Segment-exact bonus (no full substring match)
    if q_segs_padded:
        path_padded = f"/{path_lower}/"
        for qs in q_segs_padded:
            if qs in path_padded:
                score += 50_000

    # If we already have segment bonus points, return without fuzzy
    if score > 0:
        return score

    # Fuzzy character-sequence match (most expensive, last resort)
    curr_idx = 0
    for c in q:
        curr_idx = path_lower.find(c, curr_idx)
        if curr_idx == -1:
            return 0
        curr_idx += 1

    return 1_000 - path_len


def search(query: str, paths: list, frecency: dict = None) -> list:
    """
    Filter and rank paths against query.

    - Pre-computes query segments once (not per path).
    - Applies frecency boost when provided.
    - Returns paths sorted best-first.
    """
    if not query:
        if frecency:
            return sorted(
                paths,
                key=lambda p: (
                    -frecency.get(p[1] if isinstance(p, (tuple, list)) else p, 0),
                    len(p[0] if isinstance(p, (tuple, list)) else p),
                ),
            )
        return sorted(
            paths,
            key=lambda p: len(p[0] if isinstance(p, (tuple, list)) else p),
        )

    q = query.lower()
    q_segs_padded = [f"/{s}/" for s in _SEP.split(q) if s]

    scored = []
    for p in paths:
        display = p[0] if isinstance(p, (tuple, list)) else p
        display_lower = display.lower()
        s = _score(q, q_segs_padded, display_lower, len(display))
        if s > 0:
            if frecency:
                full_path = p[1] if isinstance(p, (tuple, list)) else p
                s += frecency.get(full_path, 0) * 10
            scored.append((s, p))

    # Partial sort: only need the top _DISPLAY_LIMIT entries
    if len(scored) > _DISPLAY_LIMIT:
        top = heapq.nlargest(_DISPLAY_LIMIT, scored, key=lambda x: (
            x[0],
            -len(x[1][0] if isinstance(x[1], (tuple, list)) else x[1]),
        ))
        top.sort(key=lambda x: (
            -x[0],
            len(x[1][0] if isinstance(x[1], (tuple, list)) else x[1]),
        ))
        return [p for _, p in top]

    scored.sort(key=lambda x: (
        -x[0],
        len(x[1][0] if isinstance(x[1], (tuple, list)) else x[1]),
    ))
    return [p for _, p in scored]
