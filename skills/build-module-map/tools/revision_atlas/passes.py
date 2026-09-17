"""Recover the agent-pass inputs from a generated tree (ticket 0012).

The pass outputs — claims, recall blocks, agent-authored mermaid — are already
persisted inside `spec.json` (the derived contract). `dump_passes` turns them back
into the three JSON shapes `build --semantic/--recall/--mermaid` consume, so a
refresh can re-run a pass for only the stale leaves and reuse the rest without
hand-reading the contract.

The flow this serves, from the skill:

    1. the verifier's `freshness` findings name the stale leaves;
    2. `dump_passes` rehydrates everyone's pass inputs from `spec.json`;
    3. the stale leaves' pass(es) re-run in fresh subagents and merge over the
       rehydrated inputs;
    4. the build re-runs — which re-enters the gates, because a source change
       lapses Gate 2 by design.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

from .notebook_generator import iter_leaves
from .spec_writer import owns_content


def passes_from_spec(spec: dict) -> Dict[str, dict]:
    """Rehydrate the three pass-input dicts from a generated spec.

    Each leaf's claims live in its `checklist` as `kind: "claim"`; its recall block
    in `recall`/`prompt`/`reveal`; its agent-authored diagrams in `mermaid`. The
    mechanical seeds (details, source mermaid) are deliberately left behind — they
    are deterministic and will be re-derived, not re-supplied.
    """
    semantic: Dict[str, List[str]] = {}
    recall: Dict[str, dict] = {}
    mermaid: Dict[str, List[str]] = {}
    for node in iter_leaves(spec["root"]):
        if not owns_content(node):
            continue
        claims = [c["text"] for c in node.get("checklist", []) if c.get("kind") == "claim"]
        if claims:
            semantic[node["id"]] = claims
        if any(node.get(k) for k in ("recall", "prompt", "reveal")):
            recall[node["id"]] = {
                "recall": node.get("recall", []),
                "prompt": node.get("prompt", ""),
                "reveal": node.get("reveal", ""),
            }
        if node.get("mermaid"):
            mermaid[node["id"]] = node["mermaid"]
    return {"semantic": semantic, "recall": recall, "mermaid": mermaid}


def dump_passes(module_dir: str, out_root: str, out_dir: str) -> List[Path]:
    """Write semantic.json / recall.json / mermaid.json for a built module."""
    from .extractor import extract

    inv = extract(module_dir)
    spec_path = Path(out_root) / Path(inv["root"]).name / "spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for name, data in passes_from_spec(spec).items():
        path = out / f"{name}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        written.append(path)
    return written


def main(argv: "Optional[List[str]]" = None) -> int:
    ap = argparse.ArgumentParser(
        description="Rehydrate the agent-pass inputs from a built tree's spec.json",
    )
    ap.add_argument("module_dir", help="the course-module directory")
    ap.add_argument("--mindmaps", default="mindmaps", help="the generated artifacts root")
    ap.add_argument("--out", default=".", help="write semantic/recall/mermaid.json here")
    args = ap.parse_args(argv)

    written = dump_passes(args.module_dir, args.mindmaps, args.out)
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
