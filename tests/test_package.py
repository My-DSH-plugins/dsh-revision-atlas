"""Acceptance tests for 0013's assembler: the bundle is self-contained."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revision_atlas.package import assemble

_REPO = Path(__file__).resolve().parents[1]


class TestAssemble(unittest.TestCase):
    def test_the_bundle_runs_the_pipeline_from_its_own_tools(self):
        with tempfile.TemporaryDirectory() as td:
            written = assemble(td)
            skill = Path(td) / "build-module-map"
            self.assertTrue((skill / "SKILL.md").exists())
            self.assertTrue((skill / "passes" / "semantic-pass.md").exists())
            self.assertTrue((skill / "tools" / "revision_atlas" / "build.py").exists())
            # the four-skill surface: router + course + module + refresh
            for name in ("revision-atlas", "build-course-map", "refresh-stale-leaves"):
                self.assertTrue((Path(td) / name / "SKILL.md").exists(), name)
            # the SKILL.md must use <base>, not a dev-checkout path
            body = (skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("<base>/tools", body)
            self.assertNotIn("PYTHONPATH=src", body)
            # the copied package actually imports and its CLI answers
            r = subprocess.run(
                [sys.executable, "-m", "revision_atlas.build", "--help"],
                cwd=td,
                env={"PYTHONPATH": str(skill / "tools"), "PATH": "/usr/bin:/bin"},
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("--approve", r.stdout)


if __name__ == "__main__":
    unittest.main()


class TestToolsInSync(unittest.TestCase):
    """The bundle's tools/ is a COPY of src/ — and it must stay one.

    Committed so a fresh clone and the linked plugin work without a build step; the
    test converts the "edited src/ and forgot to re-sync" hazard from a silent drift
    into a red test (SPEC §14: a miss is a failure, not a warning).
    """

    def _files(self, root):
        out = {}
        for p in root.rglob("*"):
            if not p.is_file() or "__pycache__" in p.parts or p.name.endswith(".pyc"):
                continue
            out[str(p.relative_to(root))] = p.read_bytes()
        return out

    def test_the_bundle_tools_match_src(self):
        src = _REPO / "src" / "revision_atlas"
        tools = _REPO / "skills" / "build-module-map" / "tools" / "revision_atlas"
        a, b = self._files(src), self._files(tools)
        self.assertEqual(
            set(a), set(b),
            "file sets differ — run: python3 -m revision_atlas.package --tools",
        )
        for name in a:
            self.assertEqual(
                a[name], b[name],
                f"{name} differs — run: python3 -m revision_atlas.package --tools",
            )
