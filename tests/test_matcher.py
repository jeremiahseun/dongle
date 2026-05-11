from dongle.matcher import search

def test_exact_match():
    paths = ["src/components", "src/components/ui", "tests"]
    res = search("src/components", paths)
    assert res[0] == "src/components"

def test_substring_match():
    paths = ["src/components/ui/button.tsx", "tests/ui/button.tsx"]
    res = search("comp", paths)
    assert res[0] == "src/components/ui/button.tsx"

def test_segment_bonus():
    paths = ["src/ui/comp.tsx", "src/components/ui.tsx"]
    res = search("components", paths)
    assert res[0] == "src/components/ui.tsx"

def test_subsequence_match():
    paths = ["src/components/ui.tsx", "tests/config.ts"]
    res = search("scu", paths)
    assert len(res) == 1
    assert res[0] == "src/components/ui.tsx"

def test_no_match():
    paths = ["src/components/ui.tsx", "tests/config.ts"]
    res = search("xyz", paths)
    assert len(res) == 0

def test_frecency():
    paths = ["src/components/ui.tsx", "src/components/auth.tsx"]
    frecency = {"src/components/auth.tsx": 100}
    res = search("comp", paths, frecency=frecency)
    assert res[0] == "src/components/auth.tsx"
