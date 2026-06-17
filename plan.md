1. **Optimize empty query sorting in `dongle/matcher.py`**:
   - In the `search` function, when `query` is empty and `frecency` is provided, the current implementation uses generator expressions inside `sorted()`.
   - Generator expressions incur overhead compared to list comprehensions because they yield values lazily instead of utilizing C-optimized list building.
   - I will replace the generator expressions `((-fget(p[1], 0), len(p[0]), i, p) for ...)` with list comprehensions `[(-fget(p[1], 0), len(p[0]), i, p) for ...]`.
   - The same applies to the non-tuple paths branch.
   - This optimization reduces the sorting time for empty queries (the initial state of the app) by avoiding the overhead of Python generators.

2. **Add optimization comments**:
   - I will add a comment explaining that list comprehensions are faster than generator expressions for `sorted()` because they allocate lists in C rather than executing lazy Python generators.

3. **Run tests**:
   - I will test the changes locally and execute the test command `PYTHONPATH=. pytest tests/` to ensure nothing is broken.

4. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**:
   - I will call `pre_commit_instructions` and follow the provided steps.

5. **Create a Pull Request**:
   - I will submit the code with the title "⚡ Bolt: [performance improvement]" and describe the What, Why, Impact, and Measurement of the change.
