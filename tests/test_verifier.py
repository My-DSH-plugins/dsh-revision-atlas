"""Acceptance tests for ticket 0007 (verifier + coverage report)."""
import json
import tempfile
import unittest
from pathlib import Path

from revision_atlas.extractor import extract
from revision_atlas.leaf_generator import annotate_artifacts
from revision_atlas.notebook_generator import generate_all
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
    (root / "README.md").write_text(readme, encoding="utf-8")
    inv = extract(root)
    spec = build_structure(inv, semantic=semantic, recall=recall)["spec"]
    annotate_artifacts(inv, spec["root"])
    out = root / "out"
    generate_all(inv, spec, str(out))
    return inv, spec, out


def _artifacts(out: Path, root: Path) -> Path:
    """The generated module dir is named after the source dir, not the H1."""
    return out / root.name / "leaves"


def _corrupt_all(out: Path, root: Path, old: str, new: str) -> None:
    """Rewrite every notebook carrying `old`.

    Indexing into the leaf list is a trap: leaf-000 is the module ROOT, whose
    range correctly owns no collapsible — corrupting only that one proves nothing.
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
            inv, spec, out = _build(Path(td), readme=readme)
            # no render_leaf_mermaids() call: the seed has no SVG in the artifact
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
