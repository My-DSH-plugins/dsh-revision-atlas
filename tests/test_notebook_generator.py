"""Acceptance tests for ticket 0006 (notebook generator, pure parts)."""
import tempfile
import unittest
from pathlib import Path

from revision_atlas.notebook_generator import (
    SHARED_ASSETS,
    _pages,
    render_notebook,
    write_shared_assets,
)


def _full_leaf():
    return {
        "title": "1. Hallucination & confabulation",
        "kind": "section",
        "file": "README.md",
        "line": 38,
        "recall": ["Fluent false output", "Plausibility not truth"],
        "prompt": "Why does it slip past review?",
        "reveal": "Plausibility, not truth.",
        "diagrams": [{"kind": "mermaid", "svg": "<svg><text>A</text></svg>"}],
        "source": ["- a bullet", "- another bullet"],
    }


class TestPages(unittest.TestCase):
    def test_full_leaf_pages(self):
        pages = _pages(_full_leaf())
        densities = [d for d, _ in pages]
        self.assertEqual(densities[0], "hard")     # cover
        self.assertEqual(densities[-1], "hard")    # back cover
        self.assertIn("soft", densities)           # content pages in between
        # one page per content block, in order
        html = "".join(inner for _, inner in pages)
        self.assertIn("Recall", html)
        self.assertIn("Diagram", html)
        self.assertIn("Self-test", html)
        self.assertIn("Source audit", html)

    def test_empty_leaf_still_has_covers(self):
        leaf = {"title": "X", "kind": "section"}
        pages = _pages(leaf)
        self.assertEqual(len(pages), 2)  # front + back cover only


class TestRenderNotebook(unittest.TestCase):
    def test_self_contained_flip(self):
        html = render_notebook(_full_leaf())
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn("page-flip.browser.js", html)
        self.assertIn("St.PageFlip", html)
        self.assertIn("1. Hallucination &amp; confabulation", html)  # escaped title
        self.assertIn("Reveal answer", html)
        self.assertIn("Source audit", html)
        self.assertIn("data-density=\"hard\"", html)

    def test_asset_prefix_used(self):
        html = render_notebook(_full_leaf(), assets_rel="../../assets")
        self.assertIn('href="../../assets/page-flip.css"', html)
        self.assertIn('src="../../assets/page-flip.browser.js"', html)


class TestSharedAssets(unittest.TestCase):
    def test_writes_all_assets(self):
        with tempfile.TemporaryDirectory() as td:
            write_shared_assets(td)
            assets = Path(td) / "assets"
            for name in SHARED_ASSETS.values():
                self.assertTrue((assets / name).exists(), name)
                self.assertGreater((assets / name).stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
