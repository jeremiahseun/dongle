import os
import tempfile
import unittest
from pathlib import Path

from dongle.matcher import search, _score, get_match_indices, _DISPLAY_LIMIT
from dongle.frecency import toggle_bookmark, get_bookmark_set, record_visit, get_frecency_scores, prune_frecency
from dongle.scanner import find_project_root, scan_paths, get_workspace_cache_key
from dongle.preview import get_directory_preview, clear_preview_cache
import dongle.config as config
import dongle.frecency as frecency_mod


def test_score():
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
    many_paths = ["a" * (i % 10 + 1) for i in range(100)]
    res_many = search("", many_paths)
    # The optimized search truncates to _DISPLAY_LIMIT for empty query
    assert len(res_many) == _DISPLAY_LIMIT


def test_multi_segment_and_highlighting():
    paths = [
        "src/components/ui",
        "src/components/auth",
        "tests/unit/components",
    ]
    res = search("src ui", paths)
    assert res[0] == "src/components/ui"

    # Exact substring highlight indices
    idx_sub = get_match_indices("src/components/ui", "comp")
    assert idx_sub == [4, 5, 6, 7]

    # Multi-segment highlight indices
    idx_seg = get_match_indices("src/components/ui", "src ui")
    assert idx_seg == [0, 1, 2, 15, 16]

    # Fuzzy acronym highlight indices ("scu" -> 's' at 0, 'c' at 4, 'u' at 15)
    idx_fuz = get_match_indices("src/components/ui", "scu")
    assert idx_fuz == [0, 4, 15]


def test_bookmarks_priority():
    paths = ["src/a", "src/bb", "src/ccc"]
    bookmarks = {"/repo/src/ccc"}
    res = search("", paths, bookmarks=bookmarks, root="/repo")
    assert res[0] == "src/ccc"


class TestDongleSuite(unittest.TestCase):
    def test_matcher_functions(self):
        test_score()
        test_search()
        test_search_empty_query()
        test_multi_segment_and_highlighting()
        test_bookmarks_priority()

    def test_preview_and_scanner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            (root / ".git" / "HEAD").write_text("ref: refs/heads/feat/revival\n")
            (root / "src" / "ui").mkdir(parents=True)
            (root / "README.md").write_text("# My Awesome Project\nFast directory jumper.\n")

            detected = find_project_root(str(root / "src" / "ui"))
            self.assertEqual(Path(detected).resolve(), root.resolve())

            scanned = scan_paths(str(root))
            self.assertIn("src", scanned)
            self.assertIn(os.path.join("src", "ui"), scanned)

            clear_preview_cache()
            prev = get_directory_preview(str(root))
            flat_text = "".join(t for _, t in prev)
            self.assertIn("feat/revival", flat_text)
            self.assertIn("src/", flat_text)
            self.assertIn("My Awesome Project", flat_text)

    def test_frecency_and_bookmarks_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig_frec = frecency_mod.FRECENCY_FILE
            orig_bm = frecency_mod.BOOKMARKS_FILE
            try:
                frecency_mod.FRECENCY_FILE = Path(tmp) / "frec.json"
                frecency_mod.BOOKMARKS_FILE = Path(tmp) / "bm.json"

                valid_dir = Path(tmp) / "existing_dir"
                valid_dir.mkdir()
                ghost_dir = Path(tmp) / "deleted_dir"

                record_visit(str(valid_dir))
                record_visit(str(ghost_dir))
                scores = get_frecency_scores()
                self.assertIn(str(valid_dir), scores)
                self.assertIn(str(ghost_dir), scores)

                is_pinned = toggle_bookmark(str(valid_dir))
                self.assertTrue(is_pinned)
                self.assertIn(os.path.abspath(str(valid_dir)), get_bookmark_set())

                removed = prune_frecency()
                self.assertEqual(removed, 1)
                self.assertNotIn(str(ghost_dir), get_frecency_scores())
            finally:
                frecency_mod.FRECENCY_FILE = orig_frec
                frecency_mod.BOOKMARKS_FILE = orig_bm


if __name__ == "__main__":
    unittest.main()
