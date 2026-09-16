"""Leaf-artifact generator (ticket 0005) — deterministic skeleton.

Adds to every leaf the artifact fields the agent pass will later fill:

  - `diagrams` — a list of content-driven diagram slots, decided
    deterministically where the rule is mechanical: each source mermaid block ->
    a `mermaid` entry; a `needs-review` residue -> `[]`; otherwise -> one
    `handdrawn` entry (the default the agent may override with a Gate-2-gated
    proposal). A leaf may hold an array of diagrams.
  - `source` — the raw bullet lines from the leaf's source range (the collapsed
    audit surface the learner diffs against).

The agentic fields (recall block, prompt/reveal, and the diagram art itself)
are a later pass over this skeleton.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from .spec_writer import leaf_range


def _assign_diagrams(inv: dict, node: dict) -> list:
    if node["kind"] == "needs-review":
        return []
    start, end = leaf_range(inv, node)
    file = node["file"]
    mermaid_lines = [
        mline for mline in inv["mermaid_blocks"].get(file, []) if start <= mline < end
    ]
    if mermaid_lines:
        return [
            {
                "kind": "mermaid",
                "justification": f"source mermaid block (line {mline})",
                "mmd_line": mline,
            }
            for mline in mermaid_lines
        ]
    return [{"kind": "handdrawn", "justification": "default — agent may override"}]


def _source_bullets(inv: dict, node: dict) -> List[str]:
    start, end = leaf_range(inv, node)
    path = Path(inv["root"]) / node["file"]
    if not path.exists():
        return []
    bullets: List[str] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if start <= i < end:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ", "+ ")):
                bullets.append(stripped)
    return bullets


def annotate_artifacts(inv: dict, node: dict) -> dict:
    """Add `diagrams` and `source` to every leaf, in place."""
    for b in (node.get("branches") or {}).values():
        annotate_artifacts(inv, b)
    for c in node.get("children", []):
        annotate_artifacts(inv, c)
    if "checklist" in node:
        node["diagrams"] = _assign_diagrams(inv, node)
        node["source"] = _source_bullets(inv, node)
    return node
