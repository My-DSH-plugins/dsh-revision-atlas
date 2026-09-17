"""Acceptance tests for ticket 0007 (verifier + coverage report)."""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from revision_atlas.extractor import extract
from revision_atlas.leaf_generator import annotate_artifacts
from revision_atlas.notebook_generator import generate_all, iter_leaves
from revision_atlas.spec_writer import build_structure
from revision_atlas.verifier import verify

READ_ME = """# Mod

## Section one

Intro prose.

- a bullet worth keeping
- another bullet

<details><summary><strong>Collapsible A</strong></summary>

The body of the collapsible.

</details>
"""


def _build(root: Path, readme: str = READ_ME, semantic=None, recall=None):
    """A complete §13 tree, built the way a human would: approve, then generate."""
    from revision_atlas.build import build

    (root / "README.md").write_text(readme, encoding="utf-8")
    spec, written, rep = build(
        str(root), str(root / "out"),
        semantic=semantic, recall=recall, approve=["all"],
    )
    assert rep is None, rep.render()          # approving generates nothing
    spec, written, rep = build(
        str(root), str(root / "out"), semantic=semantic, recall=recall,
    )
    assert rep is not None and rep.ok(), rep.render() if rep else "no report"
    return extract(root), spec, root / "out"


def _artifacts(out: Path, root: Path) -> Path:
    """The generated module dir is named after the source dir, not the H1."""
    return out / root.name / "leaves"


def _corrupt_all(out: Path, root: Path, old: str, new: str) -> None:
    """Rewrite every notebook carrying `old`.

    Indexing into the leaf list is a trap: the FIRST leaf is the module ROOT,
    whose range correctly owns no collapsible — corrupting only that proves nothing.
    """
    n = 0
    for nb in _artifacts(out, root).glob("*/notebook.html"):
        text = nb.read_text(encoding="utf-8")
        if old in text:
            nb.write_text(text.replace(old, new), encoding="utf-8")
            n += 1
    assert n, f"{old!r} appeared in no notebook — the fixture is not exercising it"


class TestVerifierPasses(unittest.TestCase):
    def test_clean_module_passes(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(Path(td))
            rep = verify(inv, spec, str(out))
            self.assertTrue(rep.ok(), rep.render())
            self.assertEqual(rep.stats["checklist_items"], 1)   # the collapsible
            self.assertEqual(rep.stats["covered"], 1)

    def test_report_prints_the_section_14_lines(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(Path(td))
            text = verify(inv, spec, str(out)).render()
            for needle in ("Inventory:", "Leaves:", "Coverage", "Verdict"):
                self.assertIn(needle, text)


class TestVerifierFails(unittest.TestCase):
    def test_missing_collapsible_fails_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(Path(td))
            # simulate a silently dropped collapsible on the audit surface
            _corrupt_all(out, Path(td), "Collapsible A", "gone")
            rep = verify(inv, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(any(f.check == "coverage" for f in rep.failures))

    def test_mermaid_seed_without_a_rendered_diagram_fails(self):
        readme = READ_ME + "\n```mermaid\nflowchart TD\n  A --> B\n```\n"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root, readme=readme)
            # a real build renders the diagram, so remove it to exercise the miss
            for nb in (out / root.name / "leaves").glob("*/notebook.html"):
                nb.write_text(re.sub(r"(?s)<svg\b.*?</svg>", "", nb.read_text(encoding="utf-8")),
                              encoding="utf-8")
            rep = verify(inv, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(
                any(f.check == "coverage" and "mermaid" in f.detail for f in rep.failures)
            )

    def test_external_reference_fails_offline_purity(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(Path(td))
            _corrupt_all(
                out, Path(td), "</head>",
                '<link rel="stylesheet" href="https://cdn.example.com/a.css" /></head>',
            )
            rep = verify(inv, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(any(f.check == "offline-purity" for f in rep.failures))

    def test_unclassified_file_fails_closure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root)
            (root / "mystery-notes.md").write_text("# Mystery\n", encoding="utf-8")
            fresh = extract(root)               # the corpus changed under the plan
            rep = verify(fresh, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(any(f.check == "closure" for f in rep.failures))

    def test_missing_artifact_fails(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(Path(td))
            next(_artifacts(out, Path(td)).glob("*/notebook.html")).unlink()  # one artifact gone
            rep = verify(inv, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(any(f.check == "artifact" for f in rep.failures))

    def test_missing_spec_json_fails(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(Path(td))
            (out / Path(td).name / "spec.json").unlink()
            rep = verify(inv, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(any(f.check == "artifact" and "spec.json" in f.detail
                                for f in rep.failures))


class TestVerifierAnnotates(unittest.TestCase):
    def test_ungrounded_claim_is_needs_review_not_failure(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(
                Path(td), semantic={"Section one": ["quantum tunnelling in ferrofluid bearings"]}
            )
            rep = verify(inv, spec, str(out))
            self.assertTrue(rep.ok(), "an adherence miss must NOT block the build")
            self.assertTrue(any(f.check == "grounding" for f in rep.needs_review))
            self.assertEqual(rep.stats["grounded"], 0)

    def test_grounded_claim_passes(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(
                Path(td), semantic={"Section one": ["a bullet worth keeping"]}
            )
            rep = verify(inv, spec, str(out))
            self.assertEqual(rep.stats["claims"], 1)
            self.assertEqual(rep.stats["grounded"], 1)
            self.assertFalse(rep.needs_review)

    def test_paraphrased_claim_is_not_flagged(self):
        # A paraphrase keeps its subject terms but changes the glue words. The
        # floor (≥1 shared subject term) must not flag it — the old 60% overlap
        # threshold did, and this test is the regression guard against its return.
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(
                Path(td), semantic={"Section one": ["retain the useful bullet"]}
            )
            rep = verify(inv, spec, str(out))
            self.assertEqual(rep.stats["grounded"], 1)
            self.assertFalse(rep.needs_review)

    def test_critic_drift_merges_as_needs_review(self):
        with tempfile.TemporaryDirectory() as td:
            inv, spec, out = _build(Path(td))
            rep = verify(
                inv, spec, str(out),
                critic={"Section one": [{"detail": "names the collapsible but misstates it"}]},
            )
            self.assertTrue(rep.ok())
            self.assertTrue(
                any(f.check == "critic" and "misstates" in f.detail for f in rep.needs_review)
            )


class TestVerifierCLI(unittest.TestCase):
    def test_cli_exit_codes(self):
        import contextlib
        import io

        from revision_atlas.verifier import main

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build(root)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([str(root), "--mindmaps", str(root / "out")])
            self.assertEqual(rc, 0)
            # a corrupt artifact must fail loudly
            _corrupt_all(root / "out", root, "Collapsible A", "x")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = main([str(root), "--mindmaps", str(root / "out")])
            self.assertEqual(rc, 1)

    def test_cli_without_artifacts_returns_2(self):
        import contextlib
        import io

        from revision_atlas.verifier import main

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text("# Mod\n\n## A\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                rc = main([str(root), "--mindmaps", str(root / "nowhere")])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()


class TestBuildPipeline(unittest.TestCase):
    """The one entry point: extract -> generate -> verify."""

    def test_end_to_end_build(self):
        from revision_atlas.build import build

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(READ_ME, encoding="utf-8")
            build(str(root), str(root / "mindmaps"), approve=["all"])
            spec, written, rep = build(str(root), str(root / "mindmaps"))
            self.assertTrue(rep.ok(), rep.render())
            # ONE notebook: the module root owns no content of its own — its
            # range is just its heading — so it is a parent, not a leaf, and gets
            # no artifact. (It used to get an empty one: cover, back cover, nothing
            # between.) `Section one` owns the prose and the collapsible.
            self.assertEqual(len(written), 1)
            self.assertTrue((root / "mindmaps" / root.name / "plan.md").exists())
            self.assertTrue((root / "mindmaps" / root.name / "spec.json").exists())
            self.assertTrue((root / "mindmaps" / "assets" / "notebook.css").exists())
            # the map is the fused course map at the artifacts root, rendered by
            # the course layer once the module is built
            from revision_atlas.course import render_course
            render_course(root.name, [root], str(root / "mindmaps"))
            map_html = root / "mindmaps" / "index.html"
            self.assertTrue(map_html.exists())
            self.assertIn("<svg", map_html.read_text(encoding="utf-8"))

    def _built(self, td: str):
        """Build one module in the §13 layout: mindmaps/ beside modules/."""
        from revision_atlas.build import build
        from revision_atlas.course import render_course

        base = Path(td)
        root = base / "modules" / "demo"
        root.mkdir(parents=True)
        (root / "README.md").write_text(READ_ME, encoding="utf-8")
        build(str(root), str(base / "mindmaps"), approve=["all"])   # the human gate
        spec, written, rep = build(str(root), str(base / "mindmaps"))
        render_course("Demo", [root], str(base / "mindmaps"))
        return base, root, spec, rep

    def test_the_map_links_every_leaf_and_every_link_resolves(self):
        # The notebooks are the artifact; the map is how a reader reaches them.
        # Before this, the map linked to nothing and every source href was a bare
        # `README.md#…`, which does not sit next to the map (ticket 0011).
        with tempfile.TemporaryDirectory() as td:
            base, root, spec, rep = self._built(td)
            self.assertTrue(rep.ok(), rep.render())
            module_out = base / "mindmaps" / "demo"
            map_html = base / "mindmaps" / "index.html"
            hrefs = set(
                re.findall(r'href=\\?"([^"\\]+)\\?"', map_html.read_text(encoding="utf-8"))
            )

            from revision_atlas.spec_writer import owns_content

            # in the fused map a leaf's notebook link carries the module slug
            for leaf in [n for n in iter_leaves(spec["root"]) if owns_content(n)]:
                self.assertIn(f"demo/leaves/{leaf['id']}/notebook.html", hrefs)

            for href in hrefs:
                target = map_html.parent / href.split("#")[0].split("?")[0]
                self.assertTrue(target.exists(), f"{href} does not resolve from the map")

            # §13 names leaf dirs by id — never by position
            leaf_dirs = sorted(p.name for p in (module_out / "leaves").iterdir())
            self.assertEqual(leaf_dirs, ["section-one"])
            self.assertNotIn("mod", leaf_dirs)      # the contentless root gets none

    def test_a_leaf_dir_survives_an_inserted_section(self):
        # A position-based dir (`leaf-001`) shifts the moment a section is added
        # above it, silently re-pointing every existing link at another leaf.
        with tempfile.TemporaryDirectory() as td:
            base, root, spec, rep = self._built(td)
            before = (base / "mindmaps" / "demo" / "leaves" / "section-one" / "notebook.html")
            self.assertTrue(before.exists())

            (root / "README.md").write_text(
                "# Mod\n\n## A brand new section\n\nNew prose.\n\n" + READ_ME.split("\n", 2)[2],
                encoding="utf-8",
            )
            from revision_atlas.build import build

            # a changed plan lapses the approval by design, so re-approve first
            build(str(root), str(base / "mindmaps"), approve=["all"])
            build(str(root), str(base / "mindmaps"))
            self.assertTrue(before.exists(), "inserting a section renamed an existing leaf")


    def test_a_broken_map_link_is_a_failure(self):
        with tempfile.TemporaryDirectory() as td:
            base, root, spec, rep = self._built(td)
            map_html = base / "mindmaps" / "index.html"
            map_html.write_text(
                map_html.read_text(encoding="utf-8").replace(
                    "demo/leaves/section-one/notebook.html", "demo/leaves/nope/notebook.html"
                ),
                encoding="utf-8",
            )
            rep2 = verify(extract(root), spec, str(base / "mindmaps"))
            self.assertFalse(rep2.ok())
            self.assertTrue(any(f.check == "links" for f in rep2.failures), rep2.render())

    def test_source_links_off_the_tree_are_a_note_not_a_failure(self):
        # A bare copy of `mindmaps/` — a portfolio site with no course repo around
        # it — still ships: the source anchors cannot resolve there, but the
        # artifact itself is intact, so that is needs-review, not a broken build.
        with tempfile.TemporaryDirectory() as td:
            base, root, spec, rep = self._built(td)
            os.rename(base / "modules", base / "modules-moved")
            rep2 = verify(extract(base / "modules-moved" / "demo"), spec, str(base / "mindmaps"))
            self.assertTrue(rep2.ok(), rep2.render())
            self.assertTrue(any(f.check == "links" for f in rep2.needs_review))
            self.assertFalse([f for f in rep2.failures if f.check == "links"])

    def test_a_plain_linked_sidecar_is_classified_and_mirrored(self):
        # A standalone doc linked from the README with no special filename convention
        # is a `sidecar` (SPEC §5), not an unclassified closure failure — and its own
        # heading tree is mirrored, not flattened into one empty leaf.
        from revision_atlas.build import build
        from revision_atlas.extractor import extract

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(
                "# Mod\n\n## Section one\n\nSee [the companion](companion.md).\n\n"
                "- a bullet\n",
                encoding="utf-8",
            )
            (root / "companion.md").write_text(
                "# Companion\n\n## Sub A\n\nprose a\n\n## Sub B\n\nprose b\n",
                encoding="utf-8",
            )
            inv = extract(str(root))
            kinds = {f["path"]: f.get("kind") for f in inv["files"]}
            self.assertEqual(kinds["companion.md"], "sidecar")
            self.assertFalse([f for f in inv["files"] if f["status"] == "needs_review"])
            build(str(root), str(root / "mindmaps"), approve=["all"])
            spec, written, rep = build(str(root), str(root / "mindmaps"))
            self.assertTrue(rep.ok(), rep.render())
            nodes = [n for n in iter_leaves(spec["root"])]
            sidecar = next(n for n in nodes if n.get("kind") == "sidecar")
            self.assertEqual([c["title"] for c in sidecar["children"]], ["Sub A", "Sub B"])
            self.assertIsNotNone(sidecar.get("evidence"), "sidecar lacks its link-line evidence")

    def test_build_merges_the_agent_passes(self):
        from revision_atlas.build import build

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(READ_ME, encoding="utf-8")
            passes = {
                "semantic": {"Section one": ["a bullet worth keeping"]},
                "recall": {"Section one": {"recall": ["hooks"], "prompt": "q?", "reveal": "a."}},
            }
            # the approval fingerprints the pass-fed plan, so approve with the SAME
            # passes — otherwise the build correctly calls the approval LAPSED
            build(str(root), str(root / "mindmaps"), approve=["all"], **passes)
            spec, written, rep = build(
                str(root), str(root / "mindmaps"), critic={"Section one": [{"detail": "planted drift"}]},
                **passes,
            )
            self.assertTrue(rep.ok())                                # critic annotates only
            self.assertTrue(any(f.check == "critic" for f in rep.needs_review))
            # the module ROOT is the first leaf; the recall lands on "Section one"
            all_html = "".join(
                p.read_text(encoding="utf-8")
                for p in (root / "mindmaps" / root.name / "leaves").glob("*/notebook.html")
            )
            self.assertIn("hooks", all_html)


class TestLeafMeansOwningContent(unittest.TestCase):
    """A node is a leaf because it has content, not because of its kind.

    The module root and a section both get a checklist by KIND (a heading owns its
    intro range, so intro prose is never dropped). Treating "has a checklist" as
    "is a leaf" gave a root with no intro prose a notebook of two covers and
    nothing between.
    """

    def test_a_root_that_owns_only_its_heading_gets_no_notebook(self):
        from revision_atlas.spec_writer import owns_content

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(READ_ME, encoding="utf-8")
            inv = extract(root)
            spec = build_structure(inv)["spec"]
            annotate_artifacts(inv, spec["root"])
            by_id = {n["id"]: n for n in _all_nodes(spec["root"])}

            self.assertIn("checklist", by_id["mod"])          # still enumerated...
            self.assertEqual(by_id["mod"]["checklist"], [])   # ...but empty
            self.assertFalse(owns_content(by_id["mod"]))      # so: not a leaf
            self.assertTrue(owns_content(by_id["section-one"]))

    def test_a_root_with_intro_prose_is_a_leaf(self):
        from revision_atlas.spec_writer import owns_content

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(READ_ME, encoding="utf-8")
            inv = extract(root)
            # a semantic pass compacts the root's own range into claims
            spec = build_structure(inv, semantic={"mod": ["the module's own intro"]})["spec"]
            annotate_artifacts(inv, spec["root"])
            by_id = {n["id"]: n for n in _all_nodes(spec["root"])}
            self.assertTrue(owns_content(by_id["mod"]))


def _all_nodes(node):
    yield node
    for b in (node.get("branches") or {}).values():
        yield from _all_nodes(b)
    for c in node.get("children", []):
        yield from _all_nodes(c)


class TestArtifactMustHaveContent(unittest.TestCase):
    def test_a_covers_only_notebook_is_a_failure(self):
        """Existence is not content (0016). This is the check that was missing."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root)
            module_out = out / root.name
            # a leaf's notebook, stripped to its covers
            leaf_dir = module_out / "leaves" / "section-one"
            nb = leaf_dir / "notebook.html"
            nb.write_text(
                '<!doctype html><html><body>'
                '<div class="page page-cover" data-density="hard">front</div>'
                '<div class="page page-cover" data-density="hard">back</div>'
                '</body></html>',
                encoding="utf-8",
            )
            rep = verify(inv, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(
                any(f.check == "artifact" and "no content pages" in f.detail
                    for f in rep.failures),
                rep.render(),
            )


class TestEmptyModule(unittest.TestCase):
    def test_a_module_with_no_leaves_still_produces_an_artifact_tree(self):
        """No enumerable items and no passes is legal — it must not crash (0016)."""
        from revision_atlas.build import build

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(
                "# A module\n\n## A section\n\nProse, and nothing enumerable.\n",
                encoding="utf-8",
            )
            build(str(root), str(root / "mindmaps"), approve=["all"])
            spec, written, rep = build(str(root), str(root / "mindmaps"))
            self.assertEqual(written, [])
            module_out = root / "mindmaps" / root.name
            self.assertTrue((module_out / "spec.json").exists())
            # the map is course-level, rendered even for a module with no leaves
            from revision_atlas.course import render_course
            render_course(root.name, [root], str(root / "mindmaps"))
            self.assertTrue((root / "mindmaps" / "index.html").exists())


class TestRevealBudget(unittest.TestCase):
    """SPEC §8: reveal ≤500 words, asserted rather than hoped (0010)."""

    def test_a_reveal_over_budget_is_needs_review_not_a_failure(self):
        long_reveal = " ".join("word%d" % i for i in range(520))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(
                root,
                recall={"section-one": {"recall": ["a hook"], "prompt": "why?",
                                        "reveal": long_reveal}},
            )
            rep = verify(inv, spec, str(out))
            self.assertTrue(rep.ok(), rep.render())          # annotates, never blocks
            self.assertTrue(
                any(f.check == "budget" and "over the 500-word budget" in f.detail
                    for f in rep.needs_review),
                rep.render(),
            )

    def test_a_reveal_within_budget_is_silent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(
                root,
                recall={"section-one": {"recall": ["a hook"], "prompt": "why?",
                                        "reveal": " ".join("word%d" % i for i in range(480))}},
            )
            rep = verify(inv, spec, str(out))
            self.assertFalse([f for f in rep.needs_review if f.check == "budget"])


SHORT_LABEL_READ_ME = """# Mod

## Section one

Intro prose.

<details><summary>C1</summary>

The body of the collapsible.

</details>
"""


class TestShortLabelCoverage(unittest.TestCase):
    """A label with no matchable words is unverifiable, not absent (0015).

    `_words()` drops tokens of <=2 chars and stop words. A collapsible labelled
    "C1" or "Why?" therefore yields NOTHING to require, and the check used to treat
    that empty requirement as a missing item — a false FAILURE (exit 1) for a
    collapsible that was present and correctly audited.
    """

    def test_a_short_label_present_in_the_artifact_is_found(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root, readme=SHORT_LABEL_READ_ME)
            rep = verify(inv, spec, str(out))
            self.assertTrue(rep.ok(), rep.render())
            self.assertEqual(rep.stats["covered"], rep.stats["checklist_items"])

    def test_a_short_label_that_is_genuinely_absent_still_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root, readme=SHORT_LABEL_READ_ME)
            # blank the label out of every notebook's audit
            for nb in (out / root.name / "leaves").glob("*/notebook.html"):
                nb.write_text(nb.read_text(encoding="utf-8").replace("C1", "Z9"), encoding="utf-8")
            rep = verify(inv, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(
                any(f.check == "coverage" and "C1" in f.detail for f in rep.failures),
                rep.render(),
            )


class TestHumanApproval(unittest.TestCase):
    """Generation is gated on a recorded approval, and the approval is of a PLAN.

    An approval fingerprints the content it reviewed: it survives rebuilding the same
    plan and lapses the moment that plan — or the source the checklists claim to
    capture — changes. So a human decision cannot be laundered into a later plan.
    """

    READ_ME = "# Mod\n\n## Section one\n\nIntro prose.\n\n<details><summary>C1</summary>\n\nBody.\n\n</details>\n"

    def _module(self, td):
        root = Path(td)
        (root / "README.md").write_text(self.READ_ME, encoding="utf-8")
        return root

    def test_building_an_unapproved_plan_generates_nothing(self):
        from revision_atlas.build import build

        with tempfile.TemporaryDirectory() as td:
            root = self._module(td)
            spec, written, rep = build(str(root), str(root / "mindmaps"))
            self.assertEqual(written, [])
            self.assertIsNone(rep)                       # nothing ran, nothing passed
            module_out = root / "mindmaps" / root.name
            self.assertTrue((module_out / "plan.md").exists())    # the review surface
            self.assertTrue((module_out / "spec.json").exists())
            self.assertEqual(list((module_out).glob("leaves")), [])
            self.assertFalse((module_out / "index.html").exists())

    def test_approving_then_building_generates_and_survives_a_rebuild(self):
        from revision_atlas.build import build

        with tempfile.TemporaryDirectory() as td:
            root = self._module(td)
            build(str(root), str(root / "mindmaps"), approve=["all"], approved_by="Tester")
            spec, written, rep = build(str(root), str(root / "mindmaps"))
            self.assertTrue(written and rep.ok(), rep.render() if rep else "no report")
            # a second rebuild of the SAME plan must not need re-approval
            spec, written, rep = build(str(root), str(root / "mindmaps"))
            self.assertTrue(written and rep.ok())

    def test_a_source_edit_without_a_re_approval_lapses_the_gate(self):
        from revision_atlas.build import build

        with tempfile.TemporaryDirectory() as td:
            root = self._module(td)
            build(str(root), str(root / "mindmaps"), approve=["all"])
            build(str(root), str(root / "mindmaps"))
            # prose only: no new heading, no new checklist item — and it must STILL
            # invalidate Gate 2, whose subject is the source the checklists capture
            (root / "README.md").write_text(self.READ_ME + "\nExtra prose.\n", encoding="utf-8")
            spec, written, rep = build(str(root), str(root / "mindmaps"))
            self.assertEqual(written, [])
            self.assertIsNone(rep)

    def test_the_approval_records_who_and_what(self):
        from revision_atlas.build import build

        with tempfile.TemporaryDirectory() as td:
            root = self._module(td)
            build(str(root), str(root / "mindmaps"), approve=["all"], approved_by="A Tester")
            spec = json.loads((root / "mindmaps" / root.name / "spec.json").read_text())
            for gate in ("structure", "checklists"):
                self.assertEqual(spec["approval"][gate]["by"], "A Tester")
                self.assertTrue(spec["approval"][gate]["at"])
                self.assertTrue(spec["approval"][gate]["sha"])

    def test_the_verifier_fails_a_tree_with_no_recorded_approval(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root)
            spec_path = out / root.name / "spec.json"
            spec_path.write_text("{}", encoding="utf-8")          # strip the record
            rep = verify(inv, spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(any(f.check == "approval" for f in rep.failures), rep.render())

    def test_the_verifier_fails_a_leaf_whose_source_moved_on(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root)
            # the README moves on after the artifacts were built
            (root / "README.md").write_text(
                READ_ME + "\n\nA paragraph added after the build.\n", encoding="utf-8"
            )
            rep = verify(extract(root), spec, str(out))
            self.assertFalse(rep.ok())
            self.assertTrue(
                any(f.check == "freshness" and "source changed" in f.detail
                    for f in rep.failures),
                rep.render(),
            )


class TestDumpPasses(unittest.TestCase):
    """`--dump-passes` turns spec.json back into the pass-input JSONs (0012)."""

    def test_the_pass_inputs_round_trip_through_the_tree(self):
        import json

        from revision_atlas.passes import dump_passes

        passes_in = {
            "semantic": {"section-one": ["a claim about the intro"]},
            "recall": {"section-one": {"recall": ["a hook"], "prompt": "why?",
                                       "reveal": "- because."}},
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root, **passes_in)
            dumped_dir = root / "dumped"
            dump_passes(str(root), str(out), str(dumped_dir))

            got = {
                name: json.loads((dumped_dir / f"{name}.json").read_text(encoding="utf-8"))
                for name in passes_in
            }
            self.assertEqual(got["semantic"], passes_in["semantic"])
            self.assertEqual(got["recall"], passes_in["recall"])

    def test_mechanical_seeds_are_not_rehydrated(self):
        import json

        from revision_atlas.passes import dump_passes

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv, spec, out = _build(root)
            dumped_dir = root / "dumped"
            dump_passes(str(root), str(out), str(dumped_dir))
            semantic = json.loads((dumped_dir / "semantic.json").read_text(encoding="utf-8"))
            # the collapsible is a deterministic seed, not a claim — it must not leak
            # into the claims file, or a rebuild would double-count it
            self.assertEqual(semantic, {})
