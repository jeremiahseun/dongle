## 2024-05-12 - Hoisting Type Checks and Avoiding Python Generator Overhead
**Learning:** In critical paths like filtering a large list of strings (or tuples) on every keystroke, performing type checks (`isinstance(item, (tuple, list))`) in every iteration creates measurable overhead. Additionally, using generators like `all(c in iter for c in q)` is slower than a naive explicit `for` loop that iterates and breaks.
**Action:** When writing filter/search loops that will execute thousands of times per interaction, check the type of the collection elements once before the loop (if homogenous) and branch to specialized loops. Avoid `all(...)` with generator expressions in tight loops; prefer explicit stateful loops.

## 2024-05-13 - Avoid String Split in Hot Loops
**Learning:** Using `.split("/")` in a hot loop (like filtering 10,000s of paths on every keystroke) creates measurable overhead due to array allocations and list iterations.
**Action:** Replace `.split()` with substring searches over slash-wrapped strings. Instead of `q in path.split("/")`, wrap the path and query: `f"/{q}/" in f"/{path}/"`. This utilizes C-level substring search and avoids string allocation for `split()`.

## 2024-05-19 - Use C-optimized str.find for fuzzy matching instead of manual iteration
**Learning:** In hot loops like `_score` for fuzzy path matching, using `str.find(c, idx + 1)` is significantly faster (approx. 40% faster) than a stateful python `for c in path_lower` loop because `find` is implemented in C.
**Action:** When implementing character sequence matching (fuzzy finding), iterate over the query characters and use `str.find` on the target string rather than iterating over the target string in pure Python.

## 2024-06-25 - Avoid Lambda Overhead in Python Sort via Native Tuple Ordering
**Learning:** In a hot search loop filtering thousands of paths on every keystroke, sorting the results via `heapq.nlargest` or `list.sort()` with a custom `key=lambda...` introduces significant evaluation overhead per item. For a list of 50,000 paths, this amounts to >300ms bottleneck. Additionally, utilizing `isinstance` check dynamically within list comprehensions or loops adds unnecessary type checking overhead.
**Action:** Extract list comprehension or map operations into for-loops where `_append` is pre-fetched (`_append = list.append`). When assembling the array of matches to be sorted, eagerly structure the results as native tuples `(-score, length, unique_index, item)`. This intrinsically sorts the data in the optimal order natively by `heapq.nsmallest` or `list.sort()` without the overhead of dynamic key generation. The `unique_index` ensures `TypeError` is not raised if ties evaluate to trailing unorderable objects. Use `type(x) in (...)` over `isinstance` for slightly faster evaluation.
