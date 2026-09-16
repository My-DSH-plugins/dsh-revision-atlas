"""Acceptance tests for ticket 0005 (leaf generator, deterministic skeleton)."""
import os
import unittest
from pathlib import Path

from revision_atlas.extractor import extract
from revision_atlas.leaf_generator import annotate_artifacts
from revision_atlas.spec_writer import build_structure

M2 = Path(
    os.environ.get(
        "ATLAS_M2",
        "/Users/akshayprabhakant/github/GenAI_notes/Harness Engineering/modules/02-model-failure-science",
    )
)
M5 = Path(
    os.environ.get(
        "ATLAS_M5", "/Users/akshayprabhakant/github/ML-Engineer/modules/05-data-engineering-2"
    )
)


def _leaves(node):
    yield node
    for b in (node.get("branches") or {}).values():
        yield from _leaves(b)
    for c in node.get("children", []):
        yield from _leaves(c)


def _annotated(root_path):
    inv = extract(root_path)
    spec = build_structure(inv)["spec"]
    return inv, annotate_artifacts(inv, spec["root"])


@unittest.skipUnless(M2.is_dir() and M5.is_dir(), "course fixtures not present")
class TestLeafGenerator(unittest.TestCase):
    def test_every_leaf_has_diagrams_and_source(self):
        _, tree = _annotated(M2)
        leaves = [n for n in _leaves(tree) if "checklist" in n]
        self.assertGreater(len(leaves), 0)
        for n in leaves:
            self.assertIn("diagrams", n)
            self.assertIn("source", n)

    def test_m2_no_source_mermaid_defaults_to_empty(self):
        # M2 has no mermaid blocks and no residue -> empty diagrams (adr/0005:
        # the agent proposes mermaid; it is never assumed by the classifier).
        _, tree = _annotated(M2)
        leaves = [n for n in _leaves(tree) if "checklist" in n]
        for n in leaves:
            self.assertEqual(n["diagrams"], [])

    def test_m5_mermaid_residue_and_default(self):
        _, tree = _annotated(M5)
        leaves = {n["title"]: n for n in _leaves(tree) if "checklist" in n}
        # source mermaid block -> mermaid
        self.assertEqual(
            [d["kind"] for d in leaves["Quality gates: validation in the pipeline"]["diagrams"]],
            ["mermaid"],
        )
        # needs-review residue -> no diagrams
        self.assertEqual(leaves["code/README.md"]["diagrams"], [])
        # no mermaid in range -> empty (default), not a handdrawn slot
        self.assertEqual(
            leaves["The transaction feed that changed silently"]["diagrams"], []
        )

    def test_m5_array_of_mermaid_diagrams(self):
        # the second "Deriving the baseline and thresholds." (H4 at line 767)
        # holds four distinct mermaid blocks -> an array of four diagrams.
        _, tree = _annotated(M5)
        leaves = [n for n in _leaves(tree) if "checklist" in n]
        node = next(
            n
            for n in leaves
            if n["title"] == "Deriving the baseline and thresholds." and n["line"] == 767
        )
        self.assertEqual(
            [d["kind"] for d in node["diagrams"]],
            ["mermaid", "mermaid", "mermaid", "mermaid"],
        )

    def test_agent_authored_mermaid_appended(self):
        inv = extract(M2)
        spec = build_structure(
            inv, mermaid={"1. Hallucination & confabulation": ["flowchart TD\n  A --> B"]}
        )["spec"]
        tree = annotate_artifacts(inv, spec["root"])
        leaf = next(
            n for n in _leaves(tree) if n["title"] == "1. Hallucination & confabulation"
        )
        self.assertEqual([d["kind"] for d in leaf["diagrams"]], ["mermaid"])
        self.assertEqual(leaf["diagrams"][0]["mmd"], "flowchart TD\n  A --> B")
        self.assertEqual(leaf["diagrams"][0]["justification"], "agent-authored (Gate-2)")

    def test_source_bullets_extracted(self):
        _, tree = _annotated(M2)
        leaves = [n for n in _leaves(tree) if "checklist" in n]
        node = next(
            n
            for n in leaves
            if n["title"] == "The uncomfortable fact: models fail systematically, not randomly"
        )
        self.assertGreater(len(node["source"]), 0)
        self.assertTrue(all(i["kind"] == "bullet" and i["text"] for i in node["source"]))


if __name__ == "__main__":
    unittest.main()
