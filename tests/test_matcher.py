import pytest
from dongle.matcher import search, _score

def test_score():
    q = "scu"
    q_segs = ["scu"]
    q_segs_wrapped = ["/scu/"]

    # Exact match
    assert _score("exact", ["/exact/"], "exact", 5) == 1_000_000

    # Fuzzy match
    s1 = _score("scu", [], "src/components/ui", len("src/components/ui"))
    assert s1 == 1000 - len("src/components/ui")

    s2 = _score("scu", [], "not matching", len("not matching"))
    assert s2 == 0

def test_search():
    paths = ["src/components/ui", "src/utils", "src/components/auth"]
    result = search("scu", paths)
    assert "src/components/ui" in result

def test_search_empty_query():
    paths = ["src/a", "src/bb", "src/ccc", "src/dddd"]

    # Empty query should sort by length ascending when no frecency
    res = search("", paths)
    assert res == ["src/a", "src/bb", "src/ccc", "src/dddd"]

    # Test with frecency
    frecency = {"src/dddd": 100, "src/ccc": 10}
    res_frec = search("", paths, frecency=frecency)
    assert res_frec[0] == "src/dddd"
    assert res_frec[1] == "src/ccc"

    # Test with tuples
    paths_tuples = [("src/a", "a"), ("src/bb", "bb"), ("src/ccc", "ccc")]
    res_tup = search("", paths_tuples)
    assert res_tup == paths_tuples

    # Empty query with more than _DISPLAY_LIMIT items
    many_paths = ["a" * (i%10 + 1) for i in range(100)]
    res_many = search("", many_paths)
    # The optimized search truncates to _DISPLAY_LIMIT for empty query
    from dongle.matcher import _DISPLAY_LIMIT
    assert len(res_many) == _DISPLAY_LIMIT
