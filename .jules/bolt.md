## 2024-05-12 - Hoisting Type Checks and Avoiding Python Generator Overhead
**Learning:** In critical paths like filtering a large list of strings (or tuples) on every keystroke, performing type checks (`isinstance(item, (tuple, list))`) in every iteration creates measurable overhead. Additionally, using generators like `all(c in iter for c in q)` is slower than a naive explicit `for` loop that iterates and breaks.
**Action:** When writing filter/search loops that will execute thousands of times per interaction, check the type of the collection elements once before the loop (if homogenous) and branch to specialized loops. Avoid `all(...)` with generator expressions in tight loops; prefer explicit stateful loops.

## 2024-05-13 - Avoid String Split in Hot Loops
**Learning:** Using `.split("/")` in a hot loop (like filtering 10,000s of paths on every keystroke) creates measurable overhead due to array allocations and list iterations.
**Action:** Replace `.split()` with substring searches over slash-wrapped strings. Instead of `q in path.split("/")`, wrap the path and query: `f"/{q}/" in f"/{path}/"`. This utilizes C-level substring search and avoids string allocation for `split()`.
## 2024-05-18 - Python Iteration vs C-Optimized Search
**Learning:** In hot paths (like fallback fuzzy matching where strings fail to match most of the time), Python-level stateful loops (`for c in string: if c == target...`) are orders of magnitude slower than C-optimized standard library methods like `str.find()`. Replacing the loop with sequential `find()` calls handles non-matches instantaneously rather than paying the interpreter overhead per character.
**Action:** When performing substring or character sequence searches in performance-critical Python loops, prefer `str.find()`, `str.startswith()`, or regex implementations that push work to C, avoiding explicit `for` iteration when possible.
