import re

def fuzzy_score(query: str, path: str) -> int:
    """
    Calculate a fuzzy match score for a query against a path.
    Higher is better. 0 means no match.
    
    Feature 4: Added a massive bonus for exact segment matches.
    """
    if not query:
        return 1
        
    query = query.lower()
    path_lower = path.lower()
    
    # Exact match gets highest priority
    if query == path_lower:
        return 1000000
        
    # Split query into segments (by space or /)
    query_segments = re.split(r'[ /\\]+', query)
    path_segments = re.split(r'[ /\\]+', path_lower)
    
    score = 0
    
    # Feature 4: Bonus for exact segment matches
    # If a query segment perfectly matches a path segment, give a huge boost.
    for q_seg in query_segments:
        if not q_seg: continue
        if q_seg in path_segments:
            score += 50000
            
    # Substring match
    if query in path_lower:
        score += 10000 - path_lower.find(query)
        return score
        
    # Fuzzy character sequence match
    it = iter(path_lower)
    if all(c in it for c in query):
        # Character sequence match score: 
        # Base score + bonus for shorter paths (closer match)
        score += 1000 - len(path)
        return score
        
    return score

def search(query: str, paths: list) -> list:
    """Filter and sort paths based on query."""
    if not query:
        return sorted(paths, key=len)
        
    scored = []
    for p in paths:
        s = fuzzy_score(query, p)
        if s > 0:
            scored.append((s, p))
            
    # Sort by score (desc), then length (asc)
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    return [p for s, p in scored]
