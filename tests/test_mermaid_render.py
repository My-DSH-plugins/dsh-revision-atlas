"""Tests for ticket 0005 slice 1 (mermaid render, pure parts)."""
import os
import tempfile
import unittest
from pathlib import Path

from revision_atlas.mermaid_render import diagram_source, extract_mermaid_source

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


class TestDiagramSource(unittest.TestCase):
    def test_agent_authored_mmd_used_directly(self):
        d = {"kind": "mermaid", "mmd": "flowchart TD\n  A --> B"}
        inv = {"root": "/unused"}
        self.assertEqual(diagram_source(inv, {"file": "x.md"}, d), "flowchart TD\n  A --> B")

    def test_source_block_extracted_via_mmd_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(
                "# R\n\n```mermaid\nflowchart LR\n  X --> Y\n```\n", encoding="utf-8"
            )
            d = {"kind": "mermaid", "mmd_line": 3}
            inv = {"root": str(root)}
            self.assertEqual(diagram_source(inv, {"file": "README.md"}, d), "flowchart LR\n  X --> Y")


if __name__ == "__main__":
    unittest.main()
