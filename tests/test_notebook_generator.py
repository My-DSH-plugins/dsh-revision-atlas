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
        "source": [{"kind": "bullet", "line": 1, "text": "a bullet"},
                   {"kind": "details", "line": 2, "text": "Collapsible A"}],
    }


class TestPages(unittest.TestCase):
    def test_full_leaf_pages(self):
        pages = _pages(_full_leaf())
        densities = [d for d, _, _ in pages]
        # the notebook opens and closes on its covers (hard pages, shown alone)
        self.assertEqual(densities[0], "hard")
        self.assertEqual(densities[-1], "hard")
        self.assertTrue(all(d == "soft" for d in densities[1:-1]))
        # one page per content block, in order
        html = "".join(inner for _, _, inner in pages)
        for label in ("Recall", "Diagram", "Self-test", "Source audit"):
            self.assertIn(label, html)
        classes = [c for _, c, _ in pages]
        self.assertEqual(classes[0], "page-cover")    # front cover leads
        self.assertEqual(classes[-1], "page-cover")   # back cover closes
        self.assertIn("page-diagram", classes)        # diagram gets plain paper

    def test_empty_leaf_still_has_covers(self):
        pages = _pages({"title": "X", "kind": "section"})
        self.assertEqual(len(pages), 2)                      # front + back cover
        self.assertEqual([d for d, _, _ in pages], ["hard", "hard"])

    def test_content_pages_are_odd_so_the_last_one_faces_the_back_cover(self):
        # StPageFlip pairs from index 1 after the lone front cover, so the back
        # cover only shares a spread when the content count is ODD — and then it
        # shares it with the LAST content page, which must therefore stay the
        # source audit. The filler is a flyleaf at the front, never a tail page.
        pages = _pages(_full_leaf())
        content = pages[1:-1]
        self.assertEqual(len(content) % 2, 1, [c for _, c, _ in pages])
        self.assertEqual(content[0][2], "", "the flyleaf leads the content")
        self.assertIn("Source audit", content[-1][2])       # ...and the audit closes it
        self.assertEqual([d for d, _, _ in content], ["soft"] * len(content))

    def test_an_odd_content_leaf_gets_no_flyleaf(self):
        leaf = _full_leaf()
        # drop one content block (the source audit) so the count is already odd
        leaf = {k: v for k, v in leaf.items() if k != "source"}
        pages = _pages(leaf)
        content = pages[1:-1]
        self.assertEqual(len(content) % 2, 1)
        self.assertNotEqual(content[0][2], "", "no flyleaf when parity is already right")


class TestRenderNotebook(unittest.TestCase):
    def test_self_contained_flip(self):
        html = render_notebook(_full_leaf())
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn("page-flip.browser.js", html)
        self.assertIn("St.PageFlip", html)
        self.assertIn("1. Hallucination &amp; confabulation", html)  # escaped title
        self.assertIn("Reveal answer", html)
        self.assertIn("Source audit", html)
        # notebook geometry: hard covers shown alone and centred, two-page spread
        # between them, and click-anywhere flipping disabled
        self.assertIn("showCover: true", html)
        self.assertIn("usePortrait: false", html)
        self.assertIn("disableFlipByClick: true", html)
        self.assertIn('data-density="hard"', html)
        self.assertIn("at-front", html)
        # the only turn zones are the two margin squares
        self.assertIn("turn-prev", html)
        self.assertIn("turn-next", html)

    def test_asset_prefix_used(self):
        html = render_notebook(_full_leaf(), assets_rel="../../assets")
        # assets carry a content hash so a regenerated notebook can't be served a
        # stale cached stylesheet / flip runtime
        self.assertIn('href="../../assets/page-flip.css?v=', html)
        self.assertIn('href="../../assets/notebook.css?v=', html)
        self.assertIn('src="../../assets/page-flip.browser.js?v=', html)


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
