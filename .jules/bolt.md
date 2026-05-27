## 2024-05-12 - Hoisting Type Checks and Avoiding Python Generator Overhead
**Learning:** In critical paths like filtering a large list of strings (or tuples) on every keystroke, performing type checks (`isinstance(item, (tuple, list))`) in every iteration creates measurable overhead. Additionally, using generators like `all(c in iter for c in q)` is slower than a naive explicit `for` loop that iterates and breaks.
**Action:** When writing filter/search loops that will execute thousands of times per interaction, check the type of the collection elements once before the loop (if homogenous) and branch to specialized loops. Avoid `all(...)` with generator expressions in tight loops; prefer explicit stateful loops.

## 2024-05-13 - Avoid String Split in Hot Loops
**Learning:** Using `.split("/")` in a hot loop (like filtering 10,000s of paths on every keystroke) creates measurable overhead due to array allocations and list iterations.
**Action:** Replace `.split()` with substring searches over slash-wrapped strings. Instead of `q in path.split("/")`, wrap the path and query: `f"/{q}/" in f"/{path}/"`. This utilizes C-level substring search and avoids string allocation for `split()`.

## 2024-05-19 - Use C-optimized str.find for fuzzy matching instead of manual iteration
**Learning:** In hot loops like `_score` for fuzzy path matching, using `str.find(c, idx + 1)` is significantly faster (approx. 40% faster) than a stateful python `for c in path_lower` loop because `find` is implemented in C.
**Action:** When implementing character sequence matching (fuzzy finding), iterate over the query characters and use `str.find` on the target string rather than iterating over the target string in pure Python.

## 2026-05-27 - Pre-fetching methods and caching properties in hot loops
**Learning:** In hot loops in Python, dictionary and attribute lookups add overhead. Caching function/method lookups (like `fget = frecency.get`, `_score_local = _score`, `_append = scored.append`) and caching string property results (like `len()` and `.lower()`) before and during loop evaluations reduces redundancy and overhead. List comprehensions were attempted but did not yield further performance improvements over explicit for-loops with pre-fetched append methods due to internal conditional checks.
**Action:** When a method or property is called repeatedly in a hot loop on static variables or across static iterations, bind it to a local variable or pre-calculate it to bypass object inspection overhead.
