"""Acceptance tests for ticket 0002 (structure plan)."""
import os
import unittest
from pathlib import Path

from revision_atlas.extractor import extract
from revision_atlas.spec_writer import build_structure, main

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

        # The plan is a review artifact: gates, approval status, source anchors.
        # the plan states the gate it is waiting on, and that generation is blocked
        self.assertIn("AWAITING HUMAN APPROVAL", out["plan_md"])
        self.assertIn("1 — structure", out["plan_md"])
        self.assertIn("2 — checklists", out["plan_md"])
        self.assertIn("not approved", out["plan_md"])
        self.assertIn("[src README.md:", out["plan_md"])

    def test_m5_has_no_in_scope_residue(self):
        # `code/README.md` is a subdirectory's own README — out of the module's
        # narrative scope, so it is neither a needs-review node nor a `DECIDE`.
        inv = extract(M5)
        out = build_structure(inv)
        nodes = list(_all_nodes(out["root"]))
        self.assertEqual([n for n in nodes if n["kind"] == "needs-review"], [])
        self.assertEqual(out["coverage"]["needs_review"], 0)
        self.assertEqual(out["coverage"]["sections"], 9 + 4 + 6)
        self.assertNotIn("DECIDE — ", out["plan_md"])   # no residue marker emitted
        self.assertEqual({o["path"] for o in inv["out_of_scope"]}, {"code/README.md"})

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

    def test_recall_merge(self):
        out = build_structure(
            extract(M2),
            recall={
                "1. Hallucination & confabulation": {
                    "recall": ["fluent false output", "plausibility not truth"],
                    "prompt": "Why does a fluent wrong answer slip past review?",
                    "reveal": "It optimizes plausibility, not truth.",
                }
            },
        )
        leaf = next(
            n for n in _all_nodes(out["root"]) if n["title"] == "1. Hallucination & confabulation"
        )
        self.assertEqual(leaf["recall"], ["fluent false output", "plausibility not truth"])
        self.assertEqual(leaf["prompt"], "Why does a fluent wrong answer slip past review?")
        self.assertEqual(leaf["reveal"], "It optimizes plausibility, not truth.")
        # reviewable in plan.md (Gate 2)
        self.assertIn("recall:", out["plan_md"])
        self.assertIn("fluent false output", out["plan_md"])
        self.assertIn("prompt: Why does a fluent wrong answer slip past review?", out["plan_md"])
        self.assertIn("reveal: It optimizes plausibility, not truth.", out["plan_md"])

    def test_mermaid_merge(self):
        mmd = "flowchart TD\n  A[Plausibility] --> B[Wrong]"
        out = build_structure(
            extract(M2),
            mermaid={"1. Hallucination & confabulation": [mmd]},
        )
        leaf = next(
            n for n in _all_nodes(out["root"]) if n["title"] == "1. Hallucination & confabulation"
        )
        self.assertEqual(leaf["mermaid"], [mmd])
        # reviewable in plan.md (Gate 2): a fenced mermaid block
        self.assertIn("[diagram] mermaid (agent-authored)", out["plan_md"])
        self.assertIn("```mermaid", out["plan_md"])
        self.assertIn("A[Plausibility] --> B[Wrong]", out["plan_md"])

    def test_leaf_dir_id_is_derived_from_the_id_not_a_position(self):
        # SPEC §13: `leaves/<leaf-id>/`. A position would re-point every link
        # below an inserted section at a different leaf (ticket 0011).
        from revision_atlas.spec_writer import leaf_dir_id

        self.assertEqual(leaf_dir_id({"id": "section-one"}), "section-one")
        self.assertEqual(leaf_dir_id({"title": "Some Heading"}), "some-heading")

        # A long heading stays a valid path component and stays unique to its id.
        name = leaf_dir_id({"id": "x" * 200})
        self.assertEqual(len(name), 80)
        self.assertNotEqual(name, leaf_dir_id({"id": "x" * 199}))
        self.assertTrue(name.startswith("x" * 71))   # still recognisable

    def test_section_intros_get_checklists(self):
        # A section with children owns its intro range and gets a checklist, so
        # its intro prose isn't silently dropped (regression from the cold test).
        out = build_structure(extract(M2))
        nodes = {n["title"]: n for n in _all_nodes(out["root"])}
        for title in ("The failure classes", "Contested boundaries", "M2 · Model Failure Science"):
            self.assertIn("checklist", nodes[title], title)
        # Intro seed is mechanical-empty (no collapsibles/mermaid in the intro),
        # but the key exists so the agent can fill it — and children's content is
        # not double-counted (the closure test asserts that globally).
        self.assertEqual(nodes["The failure classes"]["checklist"], [])


DUPLICATE_READ_ME = """# Mod

## Alpha

Alpha intro.

### Deriving the baseline and thresholds

Prose about bucket width.

## Beta

Beta intro.

### Deriving the baseline and thresholds

Prose about per-column statistics.
"""


class TestDuplicateTitles(unittest.TestCase):
    """Two headings with the same text (ticket 0008).

    Self-contained on purpose: the real incident was M5's two `Deriving the
    baseline and thresholds.` sections, but a regression test for identity
    handling must not depend on a course repo happening to still contain that
    heading.
    """

    def _tree(self, semantic=None):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(DUPLICATE_READ_ME, encoding="utf-8")
            return build_structure(extract(root), semantic=semantic)["root"]

    def test_same_titled_leaves_get_distinct_ids(self):
        out = self._tree()
        leaves = [
            n
            for n in _all_nodes(out)
            if n["title"] == "Deriving the baseline and thresholds"
        ]
        self.assertEqual(len(leaves), 2)
        # GitHub-style: the second occurrence carries the suffix, so the id is
        # also the anchor the README's own table of contents would use.
        self.assertEqual(
            sorted(n["id"] for n in leaves),
            ["deriving-the-baseline-and-thresholds", "deriving-the-baseline-and-thresholds-1"],
        )

    def test_id_keyed_claims_do_not_cross_between_the_two_leaves(self):
        vol, col = "deriving-the-baseline-and-thresholds", "deriving-the-baseline-and-thresholds-1"
        root = self._tree(semantic={vol: ["volume-based baseline"], col: ["per-column baseline"]})
        by_id = {n["id"]: n for n in _all_nodes(root)}

        def claims(leaf_id):
            return [c["text"] for c in by_id[leaf_id]["checklist"] if c["kind"] == "claim"]

        self.assertEqual(claims(vol), ["volume-based baseline"])
        self.assertEqual(claims(col), ["per-column baseline"])

    def test_a_title_keyed_pass_still_lands_on_both_leaves(self):
        # The fallback for older title-keyed inputs: ambiguous by construction,
        # so both leaves get the entry — which is why the passes key by id.
        root = self._tree(semantic={"Deriving the baseline and thresholds": ["shared"]})
        leaves = [
            n for n in _all_nodes(root) if n["title"] == "Deriving the baseline and thresholds"
        ]
        for leaf in leaves:
            self.assertEqual(
                [c["text"] for c in leaf["checklist"] if c["kind"] == "claim"], ["shared"]
            )


class TestPlanWriterCLI(unittest.TestCase):
    def test_out_dir_and_semantic_file(self):
        import contextlib
        import io
        import json
        import tempfile

        d = tempfile.TemporaryDirectory()
        root = Path(d.name)
        (root / "README.md").write_text("# R\n\n## A\ncontent\n", encoding="utf-8")
        semfile = root / "semantic.json"
        semfile.write_text(json.dumps({"A": ["claim one"]}), encoding="utf-8")
        outdir = root / "out"
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([str(root), "--out-dir", str(outdir), "--semantic", str(semfile)])
            self.assertEqual(rc, 0)
            self.assertTrue((outdir / "plan.md").exists())
            self.assertTrue((outdir / "spec.json").exists())
            self.assertIn("claim one", (outdir / "plan.md").read_text(encoding="utf-8"))
        finally:
            d.cleanup()


if __name__ == "__main__":
    unittest.main()
