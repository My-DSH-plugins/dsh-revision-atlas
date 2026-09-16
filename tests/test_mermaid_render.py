"""Tests for ticket 0005 slice 1 (mermaid render, pure parts)."""
import os
import unittest
from pathlib import Path

from revision_atlas.mermaid_render import extract_mermaid_source

M5 = Path(
    os.environ.get(
        "ATLAS_M5", "/Users/akshayprabhakant/github/ML-Engineer/modules/05-data-engineering-2"
    )
)


@unittest.skipUnless(M5.is_dir(), "course fixture not present")
class TestMermaidExtract(unittest.TestCase):
    def test_extract_mermaid_source(self):
        # M5's "Quality gates" mermaid block opens at line 113.
        src = extract_mermaid_source(M5 / "README.md", 113)
        self.assertIn("flowchart", src)
        self.assertIn("RAW", src)  # a node id from that block
        self.assertNotIn("```", src)  # fences stripped

    def test_extract_is_idempotent_shape(self):
        src = extract_mermaid_source(M5 / "README.md", 113)
        lines = src.splitlines()
        self.assertTrue(lines[0].startswith("flowchart"))
        # dedent: no leading indentation on the first line
        self.assertFalse(lines[0].startswith((" ", "\t")))


if __name__ == "__main__":
    unittest.main()
