"""The build pipeline: extract → plan → generate → verify.

One entry point for the whole job, so a human (or the skill) can run a module end
to end:

    PYTHONPATH=src python -m revision_atlas.build <module_dir> --mindmaps <dir> \
        [--semantic s.json] [--recall r.json] [--mermaid m.json] [--critic c.json]

The deterministic steps are pure code. The four agent passes arrive as JSON files
produced by the cold passes in `.scratch/revision-atlas/skill/`:

  semantic-pass.md      leaf id -> [claims]                 (Gate-2 input)
  recall-pass.md        leaf id -> {recall,prompt,reveal}
  mermaid-pass.md       leaf id -> [.mmd sources]
  verifier-critic.md    leaf id -> [{detail}]               (adherence drift)

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
from .renderer import render_map
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

    # §13: the module dir holds the map, the review plan, and the spec
    module_out = Path(out_root) / Path(inv["root"]).name
    (module_out / "index.html").write_text(render_map(spec), encoding="utf-8")
    (module_out / "plan.md").write_text(planned["plan_md"], encoding="utf-8")

    rep = verify(inv, spec, out_root, critic=critic)
    return spec, written, rep


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas build (extract → generate → verify)")
    ap.add_argument("module_dir")
    ap.add_argument("--mindmaps", default="mindmaps", help="artifacts root")
    ap.add_argument("--semantic", help="JSON: leaf id -> [claims]")
    ap.add_argument("--recall", help="JSON: leaf id -> {recall,prompt,reveal}")
    ap.add_argument("--mermaid", help="JSON: leaf id -> [.mmd sources]")
    ap.add_argument("--critic", help="JSON: leaf id -> [{detail}]")
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
    # the artifact dir is named for the MODULE DIRECTORY (§13), not the module's
    # display title — `spec["module"]` is the title and would name a dir that
    # does not exist
    module_out = Path(args.mindmaps) / Path(args.module_dir.rstrip("/")).name
    print(f"generated {len(written)} notebooks + index.html under {module_out}")
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
