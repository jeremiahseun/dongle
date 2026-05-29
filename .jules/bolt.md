## 2024-05-12 - Hoisting Type Checks and Avoiding Python Generator Overhead
**Learning:** In critical paths like filtering a large list of strings (or tuples) on every keystroke, performing type checks (`isinstance(item, (tuple, list))`) in every iteration creates measurable overhead. Additionally, using generators like `all(c in iter for c in q)` is slower than a naive explicit `for` loop that iterates and breaks.
**Action:** When writing filter/search loops that will execute thousands of times per interaction, check the type of the collection elements once before the loop (if homogenous) and branch to specialized loops. Avoid `all(...)` with generator expressions in tight loops; prefer explicit stateful loops.

## 2024-05-13 - Avoid String Split in Hot Loops
**Learning:** Using `.split("/")` in a hot loop (like filtering 10,000s of paths on every keystroke) creates measurable overhead due to array allocations and list iterations.
**Action:** Replace `.split()` with substring searches over slash-wrapped strings. Instead of `q in path.split("/")`, wrap the path and query: `f"/{q}/" in f"/{path}/"`. This utilizes C-level substring search and avoids string allocation for `split()`.

## 2024-05-19 - Use C-optimized str.find for fuzzy matching instead of manual iteration
**Learning:** In hot loops like `_score` for fuzzy path matching, using `str.find(c, idx + 1)` is significantly faster (approx. 40% faster) than a stateful python `for c in path_lower` loop because `find` is implemented in C.
**Action:** When implementing character sequence matching (fuzzy finding), iterate over the query characters and use `str.find` on the target string rather than iterating over the target string in pure Python.

## 2024-05-20 - Lambda and Attribute Lookup Overhead in Heapq/Sort
**Learning:** In hot loops, relying on `key=lambda x: ...` for `heapq.nlargest` or list sorting over large lists creates significant function call and evaluation overhead. We observed up to 4x slower sorting operations when sorting lists of 50,000+ matches using lambda compared to element-by-element native tuple comparison. Additionally, repeated dynamic lookups for methods like `list.append`, `dict.get`, and global functions add significant runtime overhead in these loops.
**Action:** Always structure data tuples into natively sortable formats (e.g. `(score, -length, -index, item)`) to eliminate lambda sorting overhead, letting Python's highly optimized internal C sorting handle logic naturally. Hoist method lookups (e.g. `_append = scored.append`, `fget = frecency.get`) outside of loops prior to intensive loop processing.
