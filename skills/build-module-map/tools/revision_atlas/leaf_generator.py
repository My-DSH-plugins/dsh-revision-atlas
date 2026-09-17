"""Leaf-artifact generator (ticket 0005) — deterministic skeleton.

Adds to every leaf the artifact fields the agent pass will later fill:

  - `diagrams` — a list of diagram slots (adr/0005: mermaid only). Decided
    deterministically where the rule is mechanical: each source mermaid block ->
    a `mermaid` entry; a `needs-review` residue -> `[]`; otherwise -> `[]` (the
    agent may *propose* a mermaid diagram during the semantic pass, Gate-2-gated).
    A leaf may hold an array of mermaid diagrams.
  - `source` — the raw bullet lines from the leaf's source range (the collapsed
    audit surface the learner diffs against).

The agentic text fields (recall block, prompt/reveal) merge in spec_writer's
plan (`--recall`); the agent-authored mermaid diagram is a later pass over this
skeleton (rendered at build time per adr/0002).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .spec_writer import _content_blocks, leaf_range


def _assign_diagrams(inv: dict, node: dict) -> list:
    if node["kind"] == "needs-review":
        return []
    start, end = leaf_range(inv, node)
    file = node["file"]
    mermaid_lines = [
        mline for mline in inv["mermaid_blocks"].get(file, []) if start <= mline < end
    ]
    diagrams = [
        {
            "kind": "mermaid",
            "justification": f"source mermaid block (line {mline})",
            "mmd_line": mline,
        }
        for mline in mermaid_lines
    ]
    # agent-authored mermaid (adr/0005), attached by spec_writer's --mermaid pass.
    for mmd in node.get("mermaid", []):
        diagrams.append(
            {"kind": "mermaid", "justification": "agent-authored (Gate-2)", "mmd": mmd}
        )
    return diagrams


def _plain(text: str) -> str:
    """Strip inline HTML so an audit line reads as text, not markup."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _source_items(inv: dict, node: dict) -> List[dict]:
    """The leaf's audit surface — its narrative blocks in source order.

    Prose, bullets, collapsibles and mermaid, verbatim, so the verifier can check
    coverage against it and a reader can diff the compacted narrative against the
    original (adr/0007). Shared with `_checklist_seed` via `_content_blocks`.
    """
    return _content_blocks(inv, node)


def annotate_artifacts(inv: dict, node: dict) -> dict:
    """Add `diagrams` and `source` to every leaf, in place."""
    for b in (node.get("branches") or {}).values():
        annotate_artifacts(inv, b)
    for c in node.get("children", []):
        annotate_artifacts(inv, c)
    if "checklist" in node:
        node["diagrams"] = _assign_diagrams(inv, node)
        node["source"] = _source_items(inv, node)
    return node
