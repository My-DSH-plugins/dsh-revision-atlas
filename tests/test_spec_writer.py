"""Acceptance tests for ticket 0002 (structure plan)."""
import os
import unittest
from pathlib import Path

from revision_atlas.extractor import extract
from revision_atlas.spec_writer import build_structure

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


def _all_nodes(node):
    yield node
    for b in (node.get("branches") or {}).values():
        yield from _all_nodes(b)
    for c in node.get("children", []):
        yield from _all_nodes(c)


@unittest.skipUnless(M5.is_dir() and M2.is_dir(), "course fixtures not present")
class TestStructurePlan(unittest.TestCase):
    def test_m2_tree_is_faithful_and_typed(self):
        out = build_structure(extract(M2))
        root = out["root"]
        self.assertEqual(root["kind"], "module")
        self.assertTrue(root["title"].startswith("M2"))

        nodes = list(_all_nodes(root))
        kinds = [n["kind"] for n in nodes]
        self.assertEqual(kinds.count("debate-pair"), 2)
        self.assertEqual(kinds.count("framework-matrix"), 1)
        self.assertEqual(kinds.count("worked-example"), 1)
        self.assertEqual(kinds.count("needs-review"), 0)

        # Faithful: every README H2 section becomes a section node.
        section_titles = {n["title"] for n in nodes if n["kind"] == "section"}
        self.assertIn("The failure classes", section_titles)
        self.assertIn("Real incidents — the catalog in the wild", section_titles)

        # Debate pairs carry both sides.
        for d in (n for n in nodes if n["kind"] == "debate-pair"):
            self.assertIn("for", d["branches"])
            self.assertIn("against", d["branches"])
            self.assertTrue(d["branches"]["for"]["file"].endswith("-for.md"))
            self.assertTrue(d["branches"]["against"]["file"].endswith("-against.md"))

        # Framework matrix owns all five task-state files; aggregator is canonical.
        fm = next(n for n in nodes if n["kind"] == "framework-matrix")
        self.assertEqual(fm["canonical"], "task-state-across-domains.md")
        self.assertEqual(len(fm["children"]), 5)

        # Worked example is typed.
        we = next(n for n in nodes if n["kind"] == "worked-example")
        self.assertEqual(we["file"], "06-class-6-chain-depth-worked-example.md")

        # Coverage summary is derived, not hand-written.
        self.assertEqual(out["coverage"]["classified"], 11)
        self.assertEqual(out["coverage"]["needs_review"], 0)
        self.assertEqual(out["coverage"]["collapsibles"], 13)

        # Human-readable plan opens with the coverage line and mirrors headings.
        self.assertIn("## Coverage:", out["plan_md"])
        self.assertIn("The failure classes", out["plan_md"])
        self.assertIn("kind: debate-pair", out["plan_md"])
        self.assertIn("kind: framework-matrix", out["plan_md"])

    def test_m5_flags_residue(self):
        out = build_structure(extract(M5))
        nodes = list(_all_nodes(out["root"]))
        nr = [n for n in nodes if n["kind"] == "needs-review"]
        self.assertEqual([n["file"] for n in nr], ["code/README.md"])
        self.assertEqual(out["coverage"]["needs_review"], 1)
        self.assertEqual(out["coverage"]["sections"], 9 + 4 + 6)

    def test_leaf_checklist_closure(self):
        # Every collapsible and every mermaid block lands in exactly one leaf's
        # checklist — no orphan, no double-count.
        for label, root_path in (("M2", M2), ("M5", M5)):
            out = build_structure(extract(root_path))
            leaves = [n for n in _all_nodes(out["root"]) if "checklist" in n]
            seed_details = sum(1 for n in leaves for i in n["checklist"] if i["kind"] == "details")
            seed_mermaid = sum(1 for n in leaves for i in n["checklist"] if i["kind"] == "mermaid")
            self.assertEqual(seed_details, out["coverage"]["collapsibles"], label)
            self.assertEqual(seed_mermaid, out["coverage"]["mermaid"], label)

    def test_real_incidents_leaf_has_checklist(self):
        out = build_structure(extract(M2))
        nodes = list(_all_nodes(out["root"]))
        ri = next(n for n in nodes if n["title"] == "Real incidents — the catalog in the wild")
        self.assertIn("checklist", ri)
        self.assertGreater(len(ri["checklist"]), 0)

    def test_semantic_merge(self):
        out = build_structure(
            extract(M2),
            semantic={"1. Hallucination & confabulation": ["Fluent false output"]},
        )
        leaf = next(
            n for n in _all_nodes(out["root"]) if n["title"] == "1. Hallucination & confabulation"
        )
        self.assertEqual(leaf["checklist"][0]["kind"], "claim")
        self.assertEqual(leaf["checklist"][0]["text"], "Fluent false output")
        self.assertIn("Fluent false output", out["plan_md"])


if __name__ == "__main__":
    unittest.main()
