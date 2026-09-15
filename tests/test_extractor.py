"""Acceptance tests for ticket 0001 (extractor).

Run from the repo root with:
    PYTHONPATH=src python3 -m unittest discover -s tests -v
"""
import os
import unittest
from collections import Counter
from pathlib import Path

from revision_atlas.extractor import IGNORED_DIRS, extract

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


def _independent_classified(root):
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*.md")
        if not any(part.lower() in IGNORED_DIRS for part in p.relative_to(root).parts)
    }


class TestExtractor(unittest.TestCase):
    def test_m5_closure_counts_and_structure(self):
        inv = extract(M5)
        self.assertEqual(_classified(inv), {"README.md", "code/README.md"})
        self.assertEqual(inv["closure"]["unaccounted"], 0)

        h = inv["headings"]["README.md"]
        ranks = Counter(x["rank"] for x in h)
        self.assertEqual(ranks[1], 1, "one H1 (module title)")
        self.assertEqual(ranks[2], 9, "nine H2 sections")
        self.assertEqual(ranks[3], 4, "four H3 subsections")
        self.assertEqual(ranks[4], 6, "six H4 stages")
        self.assertEqual(len(inv["mermaid_blocks"]["README.md"]), 6)
        self.assertEqual(len(inv["details_blocks"]["README.md"]), 59)

    def test_m2_closure_ignore_and_links(self):
        inv = extract(M2)
        self.assertEqual(_classified(inv), M2_EXPECTED)
        self.assertEqual(inv["closure"]["unaccounted"], 0)

        by_status = {f["path"]: f["status"] for f in inv["files"]}
        self.assertEqual(by_status.get("scratch/notes-outline.md"), "ignored")

        readme_links = inv["links"]["README.md"]
        targets = {l["target"] for l in readme_links}
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

    def test_closure_matches_independent_walk(self):
        for root in (M5, M2):
            inv = extract(root)
            self.assertEqual(_classified(inv), _independent_classified(root))


if __name__ == "__main__":
    unittest.main()
