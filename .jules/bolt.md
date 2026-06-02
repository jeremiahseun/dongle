## 2024-05-12 - Hoisting Type Checks and Avoiding Python Generator Overhead
**Learning:** In critical paths like filtering a large list of strings (or tuples) on every keystroke, performing type checks (`isinstance(item, (tuple, list))`) in every iteration creates measurable overhead. Additionally, using generators like `all(c in iter for c in q)` is slower than a naive explicit `for` loop that iterates and breaks.
**Action:** When writing filter/search loops that will execute thousands of times per interaction, check the type of the collection elements once before the loop (if homogenous) and branch to specialized loops. Avoid `all(...)` with generator expressions in tight loops; prefer explicit stateful loops.

## 2024-05-13 - Avoid String Split in Hot Loops
**Learning:** Using `.split("/")` in a hot loop (like filtering 10,000s of paths on every keystroke) creates measurable overhead due to array allocations and list iterations.
**Action:** Replace `.split()` with substring searches over slash-wrapped strings. Instead of `q in path.split("/")`, wrap the path and query: `f"/{q}/" in f"/{path}/"`. This utilizes C-level substring search and avoids string allocation for `split()`.

## 2024-05-19 - Use C-optimized str.find for fuzzy matching instead of manual iteration
**Learning:** In hot loops like `_score` for fuzzy path matching, using `str.find(c, idx + 1)` is significantly faster (approx. 40% faster) than a stateful python `for c in path_lower` loop because `find` is implemented in C.
**Action:** When implementing character sequence matching (fuzzy finding), iterate over the query characters and use `str.find` on the target string rather than iterating over the target string in pure Python.
## 2024-06-02 - UI Search Space Pruning
**Learning:** For fuzzy-finders where keystrokes continuously refine a query, filtering against the already-filtered result set instead of the full global path list provides enormous latency improvements (>90%) with barely any code changes.
**Action:** When working on search interfaces with stateful UI loops, always check if monotonic queries (i.e. appended characters) can be optimized by narrowing the search space progressively.

## 2024-06-02 - Culling unmeasurable micro-optimizations
**Learning:** Caching method lookups inside loops (`_find = path.find`) or bypassing list comprehensions on empty lists (`if dirs:`) are generally considered unmeasurable micro-optimizations in Python that clutter code readability unless they are within critical pure-CPU hot paths.
**Action:** Avoid micro-optimizations that only save nanoseconds or target I/O bound blocks. Focus purely on large algorithmic wins, algorithmic reductions in search space, or massive list overhead removals.
