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

## 2024-05-21 - os.walk String Slicing Normalization Bug
**Learning:** When optimizing `os.walk` by replacing `pathlib.Path` relative calculations with string slicing, the slicing index depends on the length of the root string. If the root string is passed as `.` or `./something`, but `len(os.path.normpath(root))` is used for slicing, paths yielded by `os.walk(root)` will not correctly align with the length of the normalized root, causing path corruption (e.g. slicing `./src/utils` by length of `src` instead of length of `./src`).
**Action:** When replacing `pathlib.Path.relative_to` inside an `os.walk` loop with fast string slicing, ensure you pass the **normalized** root directory (e.g., `root_norm = os.path.normpath(root)`) as the direct argument to `os.walk(root_norm)`. This ensures that all paths yielded begin uniformly with the normalized string, allowing `curr_root[len(root_norm):]` to slice correctly.
