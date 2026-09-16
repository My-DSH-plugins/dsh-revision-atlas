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
            skill = Path(td) / "revision-atlas"
            self.assertTrue((skill / "SKILL.md").exists())
            self.assertTrue((skill / "passes" / "semantic-pass.md").exists())
            self.assertTrue((skill / "tools" / "revision_atlas" / "build.py").exists())
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
