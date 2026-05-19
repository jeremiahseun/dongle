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
