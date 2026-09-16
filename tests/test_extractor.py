"""Acceptance tests for ticket 0001 (extractor).

Run from the repo root with:
    PYTHONPATH=src python3 -m unittest discover -s tests -v
"""
import contextlib
import io
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from revision_atlas.extractor import IGNORED_DIRS, extract, main

M5 = Path(
    os.environ.get(
        "ATLAS_M5", "/Users/akshayprabhakant/github/ML-Engineer/modules/05-data-engineering-2"
    )
)
M2 = Path(
    os.environ.get(
        "ATLAS_M2",
        "/Users/akshayprabhakant/github/GenAI_notes/Harness Engineering/modules/02-model-failure-science",
    )
)

M2_EXPECTED = {
    "04-instruction-drift-vs-05-position-bias-against.md",
    "04-instruction-drift-vs-05-position-bias-for.md",
    "06-class-6-chain-depth-worked-example.md",
    "06-reasoning-load-vs-04-instruction-drift-against.md",
    "06-reasoning-load-vs-04-instruction-drift-for.md",
    "README.md",
    "task-state-across-domains.md",
    "task-state-finance-rebalance.md",
    "task-state-healthcare-prior-auth.md",
    "task-state-legal-due-diligence.md",
    "task-state-sre-incident.md",
}


def _classified(inv):
    return {f["path"] for f in inv["files"] if f["status"] == "classified"}


def _non_ignored(inv):
    return {
        f["path"] for f in inv["files"] if f["status"] in ("classified", "needs_review")
    }


def _independent_non_ignored(root):
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() == ".md"
        and not any(part.lower() in IGNORED_DIRS for part in p.relative_to(root).parts)
    }


@unittest.skipUnless(M5.is_dir() and M2.is_dir(), "course fixtures not present")
class TestExtractor(unittest.TestCase):
    def test_m5_closure_counts_and_structure(self):
        inv = extract(M5)
        self.assertEqual(_classified(inv), {"README.md"})
        # A subdirectory's own README (`code/`) is not part of the module's
        # narrative: out of scope, reported, and NOT residue to classify.
        self.assertEqual(
            {f["path"] for f in inv["files"] if f["status"] == "needs_review"}, set()
        )
        self.assertEqual(inv["closure"]["unaccounted"], 0)
        self.assertEqual(inv["closure"]["needs_review"], 0)
        self.assertEqual({o["path"] for o in inv["out_of_scope"]}, {"code/README.md"})
        self.assertEqual(inv["closure"]["out_of_scope"], 1)

        by = {f["path"]: f for f in inv["files"]}
        self.assertEqual(by["README.md"]["kind"], "module")

        h = inv["headings"]["README.md"]
        ranks = Counter(x["rank"] for x in h)
        self.assertEqual(ranks[1], 1, "one H1 (module title)")
        self.assertEqual(ranks[2], 9, "nine H2 sections")
        self.assertEqual(ranks[3], 4, "four H3 subsections")
        self.assertEqual(ranks[4], 6, "six H4 stages")
        self.assertEqual(len(inv["mermaid_blocks"]["README.md"]), 6)
        details = inv["details_blocks"]["README.md"]
        self.assertEqual(len(details), 59)
        self.assertTrue(all(d["summary"] for d in details), "every collapsible carries its label")

    def test_m2_closure_kinds_and_links(self):
        inv = extract(M2)
        self.assertEqual(_classified(inv), M2_EXPECTED)
        self.assertEqual(inv["closure"]["needs_review"], 0)
        self.assertEqual(inv["closure"]["unaccounted"], 0)

        by = {f["path"]: f for f in inv["files"]}
        self.assertEqual(by["scratch/notes-outline.md"]["status"], "ignored")
        kinds = {p: by[p]["kind"] for p in M2_EXPECTED}
        self.assertEqual(kinds["README.md"], "module")
        self.assertEqual(kinds["04-instruction-drift-vs-05-position-bias-for.md"], "debate-for")
        self.assertEqual(kinds["04-instruction-drift-vs-05-position-bias-against.md"], "debate-against")
        self.assertEqual(kinds["06-reasoning-load-vs-04-instruction-drift-for.md"], "debate-for")
        self.assertEqual(kinds["06-class-6-chain-depth-worked-example.md"], "worked-example")
        self.assertEqual(kinds["task-state-across-domains.md"], "aggregator")
        self.assertEqual(kinds["task-state-finance-rebalance.md"], "framework-domain")

        details = inv["details_blocks"]["README.md"]
        self.assertEqual(len(details), 12)
        self.assertTrue(all(d["summary"] for d in details), "every collapsible carries its label")

        targets = {l["target"] for l in inv["links"]["README.md"]}
        self.assertEqual(
            targets,
            {
                "06-reasoning-load-vs-04-instruction-drift-for.md",
                "06-reasoning-load-vs-04-instruction-drift-against.md",
                "04-instruction-drift-vs-05-position-bias-for.md",
                "04-instruction-drift-vs-05-position-bias-against.md",
                "06-class-6-chain-depth-worked-example.md",
                "../03-harness-architecture/README.md",  # cross-module "Next module" link
            },
        )

    def test_scope_partitions_every_markdown(self):
        """In scope + out of scope must still account for every non-noise .md in
        the module. Narrowing the scope can reclassify a file, never lose one.
        """
        for root in (M5, M2):
            inv = extract(root)
            accounted = _non_ignored(inv) | {o["path"] for o in inv["out_of_scope"]}
            self.assertEqual(accounted, _independent_non_ignored(root))

    def test_only_top_level_and_linked_files_are_in_scope(self):
        """The module's scope is its own narrative: top-level markdown, plus what
        that markdown links to inside the module path — nothing else."""
        inv = extract(M2)
        self.assertEqual(_classified(inv) | _non_ignored(inv), M2_EXPECTED)
        # every in-scope file is either top-level or reachable from one that is
        self.assertTrue(all("/" not in p or p in M2_EXPECTED for p in _non_ignored(inv)))
        self.assertEqual(inv["out_of_scope"], [])

        m5 = extract(M5)
        self.assertEqual(_classified(m5), {"README.md"})
        self.assertTrue(all(len(p.split("/")) > 1 for p in (o["path"] for o in m5["out_of_scope"])))


class TestExtractorBehavior(unittest.TestCase):
    def _tmp_module(self, files):
        d = tempfile.TemporaryDirectory()
        root = Path(d.name)
        for rel, content in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return d, root

    def test_dangling_link_flagged_and_fails(self):
        d, root = self._tmp_module(
            {"README.md": "[present](present.md) and [gone](missing.md)\n", "present.md": "# p\n"}
        )
        try:
            inv = extract(root)
            self.assertEqual([x["target"] for x in inv["dangling_links"]], ["missing.md"])
            self.assertEqual(inv["closure"]["dangling_links"], 1)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(root)]), 1)
        finally:
            d.cleanup()

    def test_cross_module_link_not_dangling(self):
        d, root = self._tmp_module({"README.md": "[m3](../03/README.md)\n"})
        try:
            inv = extract(root)
            self.assertEqual(inv["dangling_links"], [])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(root)]), 0)
        finally:
            d.cleanup()

    def test_ignore_reason_names_matched_segment(self):
        d, root = self._tmp_module({"scratch/x.md": "# x\n"})
        try:
            inv = extract(root)
            self.assertEqual(inv["files"][0]["reason"], "noise dir (scratch)")
        finally:
            d.cleanup()

    def test_case_insensitive_md_extension(self):
        d, root = self._tmp_module({"NOTES.MD": "# notes\n"})
        try:
            inv = extract(root)
            self.assertIn("NOTES.MD", {f["path"] for f in inv["files"]})
        finally:
            d.cleanup()

    def test_residue_becomes_needs_review(self):
        d, root = self._tmp_module({"README.md": "# r\n", "mystery.md": "# m\n"})
        try:
            inv = extract(root)
            by = {f["path"]: f["status"] for f in inv["files"]}
            self.assertEqual(by["mystery.md"], "needs_review")
            self.assertEqual(inv["closure"]["needs_review"], 1)
        finally:
            d.cleanup()

    def test_deterministic_kinds(self):
        d, root = self._tmp_module(
            {
                "README.md": "# r\n",
                "a-vs-b-for.md": "# f\n",
                "a-vs-b-against.md": "# a\n",
                "task-state-alpha.md": "# A\n\n## Scenario\n",
                "task-state-across.md": "# A\n\n## Table of Contents\n\n# B\n",
            }
        )
        try:
            inv = extract(root)
            kinds = {f["path"]: f["kind"] for f in inv["files"] if f["status"] == "classified"}
            self.assertEqual(kinds["a-vs-b-for.md"], "debate-for")
            self.assertEqual(kinds["a-vs-b-against.md"], "debate-against")
            self.assertEqual(kinds["task-state-alpha.md"], "framework-domain")
            self.assertEqual(kinds["task-state-across.md"], "aggregator")
        finally:
            d.cleanup()

    def test_details_summaries_captured_verbatim(self):
        # summary on the same line, and on the following line; markup preserved
        d, root = self._tmp_module(
            {
                "README.md": (
                    "# r\n"
                    "\n"
                    "<details><summary>Inline label</summary>\n"
                    "body\n"
                    "</details>\n"
                    "\n"
                    "<details>\n"
                    "<summary><strong>Nested label</strong> — with markup</summary>\n"
                    "body\n"
                    "</details>\n"
                    "\n"
                    "<details>\n"
                    "no summary here\n"
                    "</details>\n"
                )
            }
        )
        try:
            blocks = extract(root)["details_blocks"]["README.md"]
            self.assertEqual([b["line"] for b in blocks], [3, 7, 12])
            self.assertEqual(blocks[0]["summary"], "Inline label")
            self.assertEqual(blocks[1]["summary"], "<strong>Nested label</strong> — with markup")
            self.assertIsNone(blocks[2]["summary"])
        finally:
            d.cleanup()


if __name__ == "__main__":
    unittest.main()
