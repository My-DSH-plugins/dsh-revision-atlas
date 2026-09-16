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
    def test_every_leaf_has_diagram_and_source(self):
        _, tree = _annotated(M2)
        leaves = [n for n in _leaves(tree) if "checklist" in n]
        self.assertGreater(len(leaves), 0)
        for n in leaves:
            self.assertIn("diagram", n)
            self.assertIn("source", n)

    def test_m2_defaults_to_handdrawn(self):
        # M2 has no mermaid blocks and no residue -> every leaf is handdrawn.
        _, tree = _annotated(M2)
        leaves = [n for n in _leaves(tree) if "checklist" in n]
        self.assertEqual({n["diagram"]["kind"] for n in leaves}, {"handdrawn"})

    def test_m5_mermaid_residue_and_default(self):
        _, tree = _annotated(M5)
        leaves = {n["title"]: n for n in _leaves(tree) if "checklist" in n}
        # source mermaid block in range -> mermaid
        self.assertEqual(
            leaves["Quality gates: validation in the pipeline"]["diagram"]["kind"], "mermaid"
        )
        # needs-review residue -> none
        self.assertEqual(leaves["code/README.md"]["diagram"]["kind"], "none")
        # no mermaid in range -> handdrawn default
        self.assertEqual(
            leaves["The transaction feed that changed silently"]["diagram"]["kind"], "handdrawn"
        )

    def test_source_bullets_extracted(self):
        _, tree = _annotated(M2)
        leaves = [n for n in _leaves(tree) if "checklist" in n]
        node = next(
            n
            for n in leaves
            if n["title"] == "The uncomfortable fact: models fail systematically, not randomly"
        )
        self.assertGreater(len(node["source"]), 0)
        self.assertTrue(all(b.startswith("- ") for b in node["source"]))


if __name__ == "__main__":
    unittest.main()
