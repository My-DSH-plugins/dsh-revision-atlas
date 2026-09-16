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

from .spec_writer import leaf_range


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
    """Every source item the leaf owns, in source order.

    This is the leaf's **audit surface** — the leaf-vs-source list. It carries all
    three kinds of item the leaf can own, not just its bullet lines, because the
    verifier (0007) checks checklist coverage against this surface: a collapsible
    seed is only checkable if the collapsible is actually enumerated here.
    """
    start, end = leaf_range(inv, node)
    file = node["file"]
    items: List[dict] = []

    path = Path(inv["root"]) / file
    if path.exists():
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if start <= i < end:
                stripped = line.strip()
                if stripped.startswith(("- ", "* ", "+ ")):
                    items.append({"kind": "bullet", "line": i, "text": stripped[2:].strip()})
    for d in inv["details_blocks"].get(file, []):
        if start <= d["line"] < end:
            items.append({"kind": "details", "line": d["line"], "text": _plain(d["summary"])})
    for m in inv["mermaid_blocks"].get(file, []):
        if start <= m < end:
            items.append({"kind": "mermaid", "line": m, "text": "mermaid diagram"})

    items.sort(key=lambda it: it["line"])
    return items


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
