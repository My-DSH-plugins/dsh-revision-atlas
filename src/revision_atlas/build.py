"""The build pipeline: extract → plan → generate → verify.

One entry point for the whole job, so a human (or the skill) can run a module end
to end:

    PYTHONPATH=src python -m revision_atlas.build <module_dir> --mindmaps <dir> \
        [--semantic s.json] [--recall r.json] [--mermaid m.json] [--critic c.json]

The deterministic steps are pure code. The four agent passes arrive as JSON files
produced by the cold passes in `.scratch/revision-atlas/skill/`:

  semantic-pass.md      leaf title -> [claims]              (Gate-2 input)
  recall-pass.md        leaf title -> {recall,prompt,reveal}
  mermaid-pass.md       leaf title -> [.mmd sources]
  verifier-critic.md    leaf title -> [{detail}]            (adherence drift)

Exit code is the verifier's: 0 pass, 1 fail, 2 nothing to verify.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .extractor import extract
from .leaf_generator import annotate_artifacts
from .mermaid_render import render_leaf_mermaids
from .notebook_generator import generate_all
from .spec_writer import build_structure
from .verifier import verify


def _load(path: "Optional[str]"):
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build(
    module_dir: str,
    out_root: str,
    semantic: "Optional[dict]" = None,
    recall: "Optional[dict]" = None,
    mermaid: "Optional[dict]" = None,
    critic: "Optional[dict]" = None,
):
    """Run the whole pipeline for one module. Returns (spec, written, report)."""
    inv = extract(module_dir)
    planned = build_structure(inv, semantic=semantic, recall=recall, mermaid=mermaid)
    spec = planned["spec"]

    annotate_artifacts(inv, spec["root"])
    render_leaf_mermaids(inv, spec["root"])
    written = generate_all(inv, spec, out_root)

    # the plan is the human review artifact (§13) and lives beside the artifacts
    module_out = Path(out_root) / Path(inv["root"]).name
    (module_out / "plan.md").write_text(planned["plan_md"], encoding="utf-8")

    rep = verify(inv, spec, out_root, critic=critic)
    return spec, written, rep


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas build (extract → generate → verify)")
    ap.add_argument("module_dir")
    ap.add_argument("--mindmaps", default="mindmaps", help="artifacts root")
    ap.add_argument("--semantic", help="JSON: leaf title -> [claims]")
    ap.add_argument("--recall", help="JSON: leaf title -> {recall,prompt,reveal}")
    ap.add_argument("--mermaid", help="JSON: leaf title -> [.mmd sources]")
    ap.add_argument("--critic", help="JSON: the critic's drift report")
    ap.add_argument("--json", help="also write the verification report here")
    args = ap.parse_args(argv)

    spec, written, rep = build(
        args.module_dir,
        args.mindmaps,
        semantic=_load(args.semantic),
        recall=_load(args.recall),
        mermaid=_load(args.mermaid),
        critic=_load(args.critic),
    )
    module_out = Path(args.mindmaps) / Path(spec["module"]).name
    print(f"generated {len(written)} notebooks under {module_out}")
    print()
    print(rep.render())
    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "module": rep.module,
                    "stats": rep.stats,
                    "coverage": rep.coverage,
                    "findings": [f.__dict__ for f in rep.findings],
                    "ok": rep.ok(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return 0 if rep.ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())
