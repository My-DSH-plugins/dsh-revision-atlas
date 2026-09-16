"""Acceptance tests for ticket 0004 (renderer)."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from revision_atlas.extractor import extract
from revision_atlas.leaf_generator import annotate_artifacts
from revision_atlas.mermaid_render import render_leaf_mermaids
from revision_atlas.renderer import main, render_map
from revision_atlas.spec_writer import build_structure

M2 = Path(
    os.environ.get(
        "ATLAS_M2",
        "/Users/akshayprabhakant/github/GenAI_notes/Harness Engineering/modules/02-model-failure-science",
    )
)


@unittest.skipUnless(M2.is_dir(), "course fixture not present")
class TestRenderer(unittest.TestCase):
    def _html(self, recall=None):
        inv = extract(M2)
        spec = build_structure(inv, recall=recall)["spec"]
        annotate_artifacts(inv, spec["root"])
        render_leaf_mermaids(inv, spec["root"])  # M2 has no mermaid -> no-op
        return render_map(spec)

    def test_self_contained_and_titled(self):
        html = self._html()
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn('<svg id="mindmap">', html)
        self.assertIn("M2 · Model Failure Science", html)  # <title> + root node
        self.assertIn("Markmap.create", html)
        # offline purity: no external script/link loads
        self.assertNotIn("<script src", html)
        self.assertNotIn("<link", html)

    def test_nodes_anchors_and_kinds(self):
        html = self._html()
        self.assertIn("The failure classes", html)  # a section title
        self.assertIn("README.md:34", html)  # its source anchor
        self.assertIn("debate-pair", html)  # a kind badge
        # leaf artifact surface: the collapsed source audit (M2 has no source
        # mermaid, so no diagram nodes — diagrams are mermaid-only per adr/0005).
        self.assertIn("source (", html)
        self.assertNotIn("hand-drawn", html)

    def test_leaf_shows_recall_and_selftest(self):
        recall = {
            "1. Hallucination & confabulation": {
                "recall": ["fluent false output", "plausibility not truth"],
                "prompt": "Why does a fluent wrong answer slip past review?",
                "reveal": "It optimizes plausibility, not truth.",
            }
        }
        html = self._html(recall=recall)
        self.assertIn("fluent false output", html)
        self.assertIn("plausibility not truth", html)
        self.assertIn("Why does a fluent wrong answer slip past review?", html)
        self.assertIn("It optimizes plausibility, not truth.", html)
        # reveal is behind a <details>; the '<' is JSON-escaped to \u003c in the
        # inlined tree, so assert on the surviving fragment.
        self.assertIn("summary>reveal", html)


class TestRendererCLI(unittest.TestCase):
    def test_cli_writes_index(self):
        d = tempfile.TemporaryDirectory()
        root = Path(d.name)
        (root / "README.md").write_text("# R\n\n## A\ncontent\n", encoding="utf-8")
        outdir = root / "out"
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([str(root), "--out-dir", str(outdir)])
            self.assertEqual(rc, 0)
            html = (outdir / "index.html").read_text(encoding="utf-8")
            self.assertIn("Markmap.create", html)
            self.assertNotIn("<script src", html)
        finally:
            d.cleanup()


if __name__ == "__main__":
    unittest.main()
