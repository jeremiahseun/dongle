## 2024-05-12 - Hoisting Type Checks and Avoiding Python Generator Overhead
**Learning:** In critical paths like filtering a large list of strings (or tuples) on every keystroke, performing type checks (`isinstance(item, (tuple, list))`) in every iteration creates measurable overhead. Additionally, using generators like `all(c in iter for c in q)` is slower than a naive explicit `for` loop that iterates and breaks.
**Action:** When writing filter/search loops that will execute thousands of times per interaction, check the type of the collection elements once before the loop (if homogenous) and branch to specialized loops. Avoid `all(...)` with generator expressions in tight loops; prefer explicit stateful loops.

## 2024-05-13 - Avoid String Split in Hot Loops
**Learning:** Using `.split("/")` in a hot loop (like filtering 10,000s of paths on every keystroke) creates measurable overhead due to array allocations and list iterations.
**Action:** Replace `.split()` with substring searches over slash-wrapped strings. Instead of `q in path.split("/")`, wrap the path and query: `f"/{q}/" in f"/{path}/"`. This utilizes C-level substring search and avoids string allocation for `split()`.

## 2024-05-19 - Use C-optimized str.find for fuzzy matching instead of manual iteration
**Learning:** In hot loops like `_score` for fuzzy path matching, using `str.find(c, idx + 1)` is significantly faster (approx. 40% faster) than a stateful python `for c in path_lower` loop because `find` is implemented in C.
**Action:** When implementing character sequence matching (fuzzy finding), iterate over the query characters and use `str.find` on the target string rather than iterating over the target string in pure Python.

## 2024-05-18 - Tuple Sorting TypeError Bug
**Learning:** Using element-by-element tuple comparison in `.sort()` or `heapq` without lambdas can raise a `TypeError` if there's a tie in the initial elements and the engine falls back to comparing an unorderable object.
**Action:** Always insert a unique tie-breaker integer (like from `enumerate`) into the tuple to guarantee the unorderable object is never evaluated during comparisons.
## 2024-05-20 - Safe Progressive Filtering in TUI
**Learning:** Progressive filtering (searching within the previously filtered subset instead of all paths) is extremely effective for fuzzy finders, reducing search time exponentially on subsequent keystrokes. However, if the underlying search function truncates results (e.g., to a `_DISPLAY_LIMIT`), applying progressive filtering to the truncated list will cause correct matches to be missed.
**Action:** When implementing progressive filtering, conditionally verify that the previous search result was **not** truncated (e.g., `len(state["filtered"]) < _DISPLAY_LIMIT`) before safely using it as the new input space.
## 2024-05-21 - Avoid pathlib.Path allocations in hot loops
**Learning:** In highly repetitive I/O-bound hot loops, such as `os.walk` across deeply nested directory structures (e.g., in `dongle/scanner.py`), creating `pathlib.Path` objects and calling `.relative_to()` imposes substantial overhead (allocations, object instantiation, parsing). Profiling shows it can be up to 10x slower than basic `os.path` operations and standard string slicing.
**Action:** When walking large directory trees or processing thousands of paths interactively, compute string prefixes/lengths ahead of time and extract relative paths using direct string slicing instead of `pathlib.Path(p).relative_to()`.
