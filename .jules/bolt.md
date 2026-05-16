## 2024-05-16 - [Remove lambda in heapq]
**Learning:** Using `lambda` functions as keys in `heapq.nlargest` creates significant overhead in the hot path of filtering. Native tuple comparisons are much faster.
**Action:** When sorting or filtering large collections using `heapq`, structure elements as tuples `(primary_key, secondary_key, data)` rather than appending `(data)` and using `key=lambda x: ...` to sort.
