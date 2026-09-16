"""Acceptance tests for ticket 0006 (notebook generator, pure parts)."""
import tempfile
import unittest
from pathlib import Path

from revision_atlas.notebook_generator import (
    SHARED_ASSETS,
    _chunk_reveal,
    _nested_budget,
    _pages,
    _selftest_html,
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


class TestNestedReveal(unittest.TestCase):
    """The reveal is paginated inside the page, not clipped by it (ticket 0010)."""

    def _long(self):
        return "\n".join(
            "- Step %d. " % i + "the mechanism narrows here because the fitted "
            "distribution sets the limit and the run rule decides when to fire"
            for i in range(1, 26)
        )

    def test_a_long_reveal_is_chunked_and_nothing_is_dropped(self):
        reveal = self._long()
        chunks = _chunk_reveal(reveal, "a short prompt?")
        self.assertGreater(len(chunks), 1)
        # every line survives, in order, exactly once
        flat = [l for c in chunks for l in c]
        self.assertEqual(flat, [l for l in reveal.splitlines() if l.strip()])

    def test_every_chunk_stays_inside_the_line_budget(self):
        prompt = "x" * 130                      # a three-line prompt
        budget = _nested_budget(prompt)
        for chunk in _chunk_reveal(self._long(), prompt):
            cost = sum(max(1.0, len(l.strip()) / 56.0) for l in chunk)
            self.assertLessEqual(cost, budget, chunk[:1])

    def test_a_longer_prompt_leaves_room_for_fewer_lines(self):
        self.assertLess(_nested_budget("x" * 280), _nested_budget("short?"))

    def test_a_short_reveal_is_one_page_and_gets_no_pager(self):
        html = _selftest_html({"prompt": "why?", "reveal": "- one\n- two"})
        self.assertIn('<div class="reveal-page">', html)
        self.assertNotIn("reveal-pager", html)          # nothing to page through
        self.assertNotIn(" hidden", html)

    def test_the_answer_hides_behind_the_disclosure(self):
        html = _selftest_html({"prompt": "why?", "reveal": "- one\n- two\n- three"})
        self.assertIn('<details class="reveal-disclosure">', html)
        self.assertIn("<summary>Reveal answer</summary>", html)
        self.assertIn('<div class="reveal-sheet">', html)

    def test_a_paginated_reveal_gets_a_pager_and_only_page_one_shows(self):
        html = _selftest_html({"prompt": "why?", "reveal": self._long()})
        self.assertIn("reveal-pager", html)
        self.assertIn("pager-count", html)
        self.assertIn(" disabled", html)                 # "Previous" starts disabled
        self.assertEqual(html.count(" hidden>"), html.count('<div class="reveal-page"') - 1)

    def test_a_prompt_without_a_reveal_has_no_sheet(self):
        html = _selftest_html({"prompt": "why?"})
        self.assertIn("Self-test", html)
        self.assertNotIn("reveal-sheet", html)

    def test_bullet_lines_keep_the_hand_written_bullet(self):
        html = _selftest_html({"prompt": "q", "reveal": "- a bullet"})
        self.assertIn('class="reveal-bullet"', html)
        self.assertNotIn("- a bullet", html)             # the dash becomes the marker


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
        for label in ("Recall", "Diagram", "Self-test", "Bibliography"):
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
        self.assertIn("Bibliography", content[-1][2])         # ...and the audit closes it
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
        self.assertIn("Bibliography", html)
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


class TestDiagramPanZoom(unittest.TestCase):
    """A dense diagram must be movable (0014)."""

    def test_the_diagram_gets_a_transformable_wrapper_and_a_hint(self):
        from revision_atlas.notebook_generator import _diagram_html

        html = _diagram_html({"kind": "mermaid", "svg": "<svg><text>A</text></svg>"})
        self.assertIn('class="diagram-zoom"', html)      # one element to transform
        self.assertIn('class="diagram-hint"', html)      # and it says so
        self.assertIn("scroll to zoom", html)

    def test_the_notebook_carries_the_pan_zoom_behaviour(self):
        html = render_notebook(
            {"title": "T", "kind": "section", "prompt": "q",
             "diagrams": [{"kind": "mermaid", "svg": "<svg><text>A</text></svg>"}]}
        )
        for needed in ("pointerdown", "pointermove", "wheel", "dblclick",
                       "setPointerCapture", "scale(${"):
            self.assertIn(needed, html)
