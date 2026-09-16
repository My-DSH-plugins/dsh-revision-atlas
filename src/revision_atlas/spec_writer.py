"""Structure-plan writer (ticket 0002).

Turns the extractor's inventory into a structure plan — the first, human-approved
artifact of the pipeline:

  - `plan_md` — a human-readable Markdown outline (headings = the faithful tree;
    sidecar nodes attached with `· kind:` annotations),
  - `spec` — the derived machine contract (ids, kinds, sources, children, typed
    edges), which 0004+ consume.

Deterministic; no LLM. The human gate (approval of plan_md) happens after this
function returns; nothing here generates any leaf artifact.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .extractor import extract


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    s = re.sub(r"[\s]+", "-", s)
    return s or "node"


def _h1_title(entry: dict, headings: Dict[str, List[dict]]) -> str:
    h1 = next((h for h in headings.get(entry["path"], []) if h["rank"] == 1), None)
    return h1["text"] if h1 else entry["path"]


def _build_heading_tree(headings: List[dict], file: str):
    """Faithfully mirror the README heading outline as a node tree."""
    root = None
    stack: List[dict] = []
    line_to_node: Dict[int, dict] = {}
    for h in headings:
        node = {
            "id": _slug(h["text"]),
            "title": h["text"],
            "kind": "section",
            "rank": h["rank"],
            "file": file,
            "line": h["line"],
            "children": [],
        }
        if root is None:
            root = node
            root["kind"] = "module"
            stack = [root]
        else:
            while stack and stack[-1]["rank"] >= h["rank"]:
                stack.pop()
            parent = stack[-1] if stack else root
            parent["children"].append(node)
            stack.append(node)
        line_to_node[h["line"]] = node
    return root, line_to_node


def _leaf_node(entry: dict, headings: Dict[str, List[dict]], kind: str) -> dict:
    return {
        "id": _slug(_h1_title(entry, headings)),
        "title": _h1_title(entry, headings),
        "kind": kind,
        "file": entry["path"],
        "line": None,
        "children": [],
    }


def _coverage(inv: dict, root: dict) -> dict:
    c = inv["closure"]
    h = inv["headings"].get(root["file"], [])
    return {
        "files": c["enumerated"],
        "classified": c["classified"],
        "ignored": c["ignored"],
        "needs_review": c["needs_review"],
        "sections": sum(1 for x in h if x["rank"] >= 2),
        "collapsibles": sum(len(v) for v in inv["details_blocks"].values()),
        "mermaid": sum(len(v) for v in inv["mermaid_blocks"].values()),
    }


# A node that owns source text directly (and thus gets a checklist), as opposed
# to a composite (`debate-pair`, `framework-matrix`) whose branches/children own
# it. Heading nodes (`module`, `section`) own their intro range even when they
# have children.
LEAF_KINDS = frozenset(
    {"module", "section", "worked-example", "needs-review", "debate-for", "debate-against", "framework-domain"}
)


def leaf_range(inv: dict, node: dict):
    """Return (start, end) of the line range a node owns in its source file.

    A heading node owns from its own line to the next heading of ANY rank — so a
    section with children owns only its intro, a terminal section owns its full
    body. A sidecar leaf (no line) owns the whole file.
    """
    if node.get("line") is None:
        return 1, float("inf")
    start = node["line"]
    for h in inv["headings"].get(node["file"], []):
        if h["line"] > start:
            return start, h["line"]
    return start, float("inf")


def _checklist_seed(inv: dict, node: dict) -> list:
    """Grounded checklist items for a leaf: its collapsibles and mermaid blocks.

    This is the deterministic seed; the agent appends semantic items (the key
    claims) and the human approves the combined checklist at Gate 2.
    """
    file = node["file"]
    start, end = leaf_range(inv, node)
    items = []
    for d in inv["details_blocks"].get(file, []):
        if start <= d["line"] < end:
            items.append({"kind": "details", "line": d["line"], "summary": d["summary"]})
    for mline in inv["mermaid_blocks"].get(file, []):
        if start <= mline < end:
            items.append({"kind": "mermaid", "line": mline})
    return items


def _dedupe_ids(root: dict) -> dict:
    """Make node ids globally unique (GitHub-style `-N` suffix).

    The id is the source-anchor fragment (renderer) *and* the agent-pass key
    (see `_annotate_leaves`). Two leaves that share a title must never collapse
    into one JSON key — the duplicate-title bug that silently gives each a copy
    of the other's claims. Dedupe every bare slug across the whole tree,
    appending `-1`, `-2`, … from the second occurrence. For duplicate headings
    within a single file this matches GitHub's own anchor disambiguation exactly
    (`#deriving-the-baseline-and-thresholds-1`).
    """
    seen: Dict[str, int] = {}

    def walk(node: dict) -> None:
        slug = node.get("id")
        if slug:
            n = seen.get(slug, 0)
            seen[slug] = n + 1
            if n:
                node["id"] = f"{slug}-{n}"
        for b in (node.get("branches") or {}).values():
            walk(b)
        for c in node.get("children", []):
            walk(c)

    walk(root)
    return root


def _lookup(data: "Optional[Dict]", node: dict):
    """Resolve a leaf's entry from an agent-pass map, by id (the unique key)
    first, with a title fallback for older title-keyed inputs (M2 demo, tests).
    """
    if not data:
        return None
    if node.get("id") and node["id"] in data:
        return data[node["id"]]
    return data.get(node["title"])


def _annotate_leaves(
    inv: dict,
    node: dict,
    semantic: "Optional[Dict[str, List[str]]]" = None,
    recall: "Optional[Dict[str, dict]]" = None,
    mermaid: "Optional[Dict[str, List[str]]]" = None,
) -> dict:
    """Attach a `checklist` to every leaf: agent claims + deterministic seed.

    `semantic` maps a leaf's id to the claim strings the agent drafted from the
    source (the agentic half; absent in the deterministic seed alone). `recall`
    maps a leaf's id to `{recall, prompt, reveal}` — the self-test agent pass.
    `mermaid` maps a leaf's id to the agent-authored `.mmd` strings (ticket
    0005, adr/0005). All three fold into the plan.md review surface alongside
    the checklist they must survive.
    """
    for b in (node.get("branches") or {}).values():
        _annotate_leaves(inv, b, semantic, recall, mermaid)
    for c in node.get("children", []):
        _annotate_leaves(inv, c, semantic, recall, mermaid)
    if node["kind"] in LEAF_KINDS:
        claims = [{"kind": "claim", "text": t} for t in (_lookup(semantic, node) or [])]
        node["checklist"] = claims + _checklist_seed(inv, node)
        rc = _lookup(recall, node)
        if rc:
            node["recall"] = rc.get("recall", [])
            node["prompt"] = rc.get("prompt", "")
            node["reveal"] = rc.get("reveal", "")
        mm = _lookup(mermaid, node) or []
        if mm:
            node["mermaid"] = mm
    return node


def _anchor(node: dict) -> str:
    """A compact source/citation anchor to render beside a node."""
    if node.get("evidence"):
        return f"[cited {node['evidence']['file']}:{node['evidence']['line']}]"
    if node.get("file"):
        if node.get("line") is not None:
            return f"[src {node['file']}:{node['line']}]"
        return f"[src {node['file']} — whole file]"
    return ""


def _render_md(root: dict, coverage: dict) -> str:
    lines: List[str] = []

    def walk(node: dict, depth: int) -> None:
        pad = "  " * max(depth - 1, 0)
        anchor = _anchor(node)
        if node["kind"] in ("module", "section"):
            entry = "#" * node["rank"] + " " + node["title"]
            if anchor:
                entry += "  " + anchor
            lines.append(entry)
        else:
            label = node["title"]
            if node["kind"] == "needs-review":
                label = f"⚠ DECIDE — {label}"
            entry = f"{pad}- **{label}** · kind: {node['kind']}"
            if anchor:
                entry += " · " + anchor
            lines.append(entry)
            for bname, bnode in (node.get("branches") or {}).items():
                lines.append(f"{pad}  - {bname}: `{bnode['file']}`")
            if node.get("canonical"):
                lines.append(f"{pad}  - canonical: `{node['canonical']}`")
        if node.get("checklist") is not None:
            ipad = pad + "  "
            if not node["checklist"]:
                lines.append(f"{ipad}- (checklist: empty — semantic items pending)")
            for it in node["checklist"]:
                if it["kind"] == "claim":
                    lines.append(f"{ipad}- {it['text']}")
                elif it["kind"] == "details":
                    label = it["summary"] or f"line {it['line']}"
                    lines.append(f"{ipad}- [details] {label}")
                elif it["kind"] == "mermaid":
                    lines.append(f"{ipad}- [diagram] mermaid (line {it['line']})")
        if node.get("recall") is not None:
            lines.append(f"{ipad}recall:")
            for r in node["recall"]:
                lines.append(f"{ipad}  - {r}")
        if node.get("prompt"):
            lines.append(f"{ipad}prompt: {node['prompt']}")
        if node.get("reveal"):
            lines.append(f"{ipad}reveal: {node['reveal']}")
        for mm in node.get("mermaid", []):
            lines.append(f"{ipad}[diagram] mermaid (agent-authored):")
            lines.append(f"{ipad}  ```mermaid")
            for mline in mm.strip().splitlines():
                lines.append(f"{ipad}  {mline}")
            lines.append(f"{ipad}  ```")
        for child in node.get("children", []):
            walk(child, depth + 1)

    walk(root, 1)
    cov = coverage
    head = [
        f"# Plan — {root['title']}",
        "",
        "> **status:** `proposed` — flip to `approved` after both gates pass.",
        "",
        "## How to review",
        "",
        "- **Gate 1 — structure:** every section and linked file appears below with the right `kind`; resolve any `⚠ DECIDE` item.",
        "- **Gate 2 — leaf checklists:** every claim is grounded in the source (follow each leaf's `[src …]` anchor); nothing invented, nothing load-bearing dropped.",
        "",
        "## Coverage: "
        f"{cov['classified']} classified · {cov['ignored']} ignored · "
        f"{cov['needs_review']} needs-review · {cov['sections']} sections · "
        f"{cov['leaves']} leaves · {cov['collapsibles']} collapsibles · "
        f"{cov['mermaid']} mermaid",
        "",
    ]
    return "\n".join(head + lines)


def build_structure(
    inv: dict,
    semantic: "Optional[Dict[str, List[str]]]" = None,
    recall: "Optional[Dict[str, dict]]" = None,
    mermaid: "Optional[Dict[str, List[str]]]" = None,
) -> dict:
    readme = next(f for f in inv["files"] if f.get("kind") == "module")
    readme_headings = inv["headings"].get(readme["path"], [])
    root, line_to_node = _build_heading_tree(readme_headings, readme["path"])

    sidecars = [
        f for f in inv["files"] if f["status"] == "classified" and f.get("kind") != "module"
    ]
    residue = [f for f in inv["files"] if f["status"] == "needs_review"]

    # Group sidecars into composite nodes.
    debate: Dict[str, Dict[str, dict]] = {}
    domains: List[dict] = []
    aggregator: Optional[dict] = None
    worked: List[dict] = []
    for f in sidecars:
        k = f["kind"]
        if k in ("debate-for", "debate-against"):
            stem = re.sub(r"-(for|against)\.md$", "", f["path"], flags=re.I)
            debate.setdefault(stem, {})["for" if k == "debate-for" else "against"] = f
        elif k == "framework-domain":
            domains.append(f)
        elif k == "aggregator":
            aggregator = f
        elif k == "worked-example":
            worked.append(f)

    # README link targets -> first line that cites them (attachment point).
    link_line: Dict[str, int] = {}
    for l in inv["links"].get(readme["path"], []):
        base = l["target"].rsplit("/", 1)[-1]
        link_line.setdefault(base, l["line"])

    def attach(node: dict, file: "Optional[str]"):
        line = link_line.get(file) if file else None
        if line is not None:
            # Evidence: the README line that cites this sidecar (the edge's proof).
            node["evidence"] = {"file": readme["path"], "line": line}
        sec = None
        for h in readme_headings:
            if h["line"] <= line and (sec is None or h["line"] > sec["line"]):
                sec = h
        parent = line_to_node.get(sec["line"]) if sec else root
        parent["children"].append(node)

    for stem, pair in sorted(debate.items()):
        src = pair.get("for") or pair.get("against")
        node = {
            "id": _slug(_h1_title(src, inv["headings"])),
            "title": _h1_title(src, inv["headings"]),
            "kind": "debate-pair",
            "file": None,
            "line": None,
            "children": [],
            "branches": {},
        }
        if "for" in pair:
            node["branches"]["for"] = _leaf_node(pair["for"], inv["headings"], "debate-for")
        if "against" in pair:
            node["branches"]["against"] = _leaf_node(
                pair["against"], inv["headings"], "debate-against"
            )
        attach(node, (pair.get("for") or pair.get("against"))["path"].rsplit("/", 1)[-1])

    for f in worked:
        attach(_leaf_node(f, inv["headings"], "worked-example"), f["path"].rsplit("/", 1)[-1])

    # Framework matrix: one node owning every task-state file; the aggregator is
    # the canonical source. Attach at root (these files aren't linked from README).
    if domains or aggregator:
        all_f = list(domains) + ([aggregator] if aggregator else [])
        title = _h1_title(aggregator, inv["headings"]) if aggregator else "Task state"
        matrix = {
            "id": _slug(title),
            "title": title,
            "kind": "framework-matrix",
            "file": None,
            "line": None,
            "children": [_leaf_node(f, inv["headings"], "framework-domain") for f in sorted(all_f, key=lambda x: x["path"])],
            "canonical": aggregator["path"] if aggregator else None,
        }
        root["children"].append(matrix)

    for f in residue:
        root["children"].append(
            {"id": _slug(f["path"]), "title": f["path"], "kind": "needs-review",
             "file": f["path"], "line": None, "children": []}
        )

    _dedupe_ids(root)
    _annotate_leaves(inv, root, semantic, recall, mermaid)

    def _leaf_stats(node, acc):
        for b in (node.get("branches") or {}).values():
            _leaf_stats(b, acc)
        for c in node.get("children", []):
            _leaf_stats(c, acc)
        if "checklist" in node:
            acc["leaves"] += 1
            if not node["checklist"]:
                acc["empty"] += 1

    stats = {"leaves": 0, "empty": 0}
    _leaf_stats(root, stats)
    coverage = _coverage(inv, root)
    coverage["leaves"] = stats["leaves"]
    coverage["empty_leaves"] = stats["empty"]
    return {
        "module": root["title"],
        "coverage": coverage,
        "root": root,
        "plan_md": _render_md(root, coverage),
        "spec": {"module": root["title"], "root": root},
    }


def main(argv: "List[str] | None" = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Revision Atlas plan writer (tickets 0002+0003)")
    ap.add_argument("module_dir", help="path to a course-module directory")
    ap.add_argument(
        "--semantic",
        help="JSON file mapping leaf id -> claim strings (the agent pass)",
    )
    ap.add_argument(
        "--recall",
        help="JSON file mapping leaf id -> {recall, prompt, reveal} (self-test pass)",
    )
    ap.add_argument(
        "--mermaid",
        help="JSON file mapping leaf id -> [mermaid .mmd strings] (diagram pass)",
    )
    ap.add_argument(
        "--out-dir",
        help="write plan.md + spec.json here (default: print both to stdout)",
    )
    args = ap.parse_args(argv)

    inv = extract(args.module_dir)
    semantic = None
    if args.semantic:
        with open(args.semantic, encoding="utf-8") as f:
            semantic = json.load(f)
    recall = None
    if args.recall:
        with open(args.recall, encoding="utf-8") as f:
            recall = json.load(f)
    mermaid = None
    if args.mermaid:
        with open(args.mermaid, encoding="utf-8") as f:
            mermaid = json.load(f)
    out = build_structure(inv, semantic=semantic, recall=recall, mermaid=mermaid)

    if args.out_dir:
        Path(args.out_dir).mkdir(parents=True, exist_ok=True)
        Path(args.out_dir, "plan.md").write_text(out["plan_md"], encoding="utf-8")
        Path(args.out_dir, "spec.json").write_text(
            json.dumps(out["spec"], indent=2), encoding="utf-8"
        )
        print(f"wrote {args.out_dir}/plan.md and {args.out_dir}/spec.json")
    else:
        print(out["plan_md"])
        print("\n--- spec.json (derived) ---")
        print(json.dumps(out["spec"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
