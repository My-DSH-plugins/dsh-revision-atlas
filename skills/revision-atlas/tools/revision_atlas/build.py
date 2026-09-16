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
from datetime import datetime, timezone
from typing import List, Optional

from .extractor import extract
from .leaf_generator import annotate_artifacts
from .mermaid_render import render_leaf_mermaids
from .notebook_generator import generate_all
from .renderer import render_map, source_base_for
from .spec_writer import approval_state, build_structure, render_plan
from .verifier import verify


def _load(path: "Optional[str]"):
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


#: Exit code for "the plan is not approved, so nothing was generated". Distinct
#: from 1 (verification failed) so a caller can tell a HUMAN DECISION from a bug.
AWAITING_APPROVAL = 3

GATES = ("structure", "checklists")


def _carried_approval(module_out: Path) -> dict:
    """The approval already recorded beside the artifacts, if any.

    Read BEFORE the new spec is written, because the fingerprint it holds is the
    only thing that can say whether the plan the human approved is still the plan on
    the page. A rebuild must not silently launder an approval into a fresh one.
    """
    spec_path = module_out / "spec.json"
    if not spec_path.exists():
        return {}
    try:
        return (json.loads(spec_path.read_text(encoding="utf-8")) or {}).get("approval") or {}
    except (ValueError, OSError):
        return {}


def _approve(approval: dict, gates, by: "Optional[str]") -> dict:
    """Record an approval of the CURRENT plan for the named gates."""
    who = (by or _default_approver()).strip()
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out = dict(approval or {})
    for gate in gates:
        out[gate] = {"sha": None, "at": stamp, "by": who}     # sha filled in below
    return out


def _default_approver() -> str:
    import subprocess

    for cmd in (["git", "config", "user.name"],):
        try:
            name = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if name.returncode == 0 and name.stdout.strip():
                return f"{name.stdout.strip()} (git)"
        except (OSError, subprocess.SubprocessError):
            pass
    import getpass

    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def build(
    module_dir: str,
    out_root: str,
    semantic: "Optional[dict]" = None,
    recall: "Optional[dict]" = None,
    mermaid: "Optional[dict]" = None,
    critic: "Optional[dict]" = None,
    source_base: "Optional[str]" = None,
    approve: "Optional[List[str]]" = None,
    approved_by: "Optional[str]" = None,
):
    """Run the whole pipeline for one module. Returns (spec, written, report).

    Generation is gated on a recorded HUMAN APPROVAL of the plan (SPEC §15: Gate 1
    structure, Gate 2 checklists). An approval is a fingerprint of the reviewed
    content, carried across rebuilds: it survives while that content is unchanged and
    lapses the moment it changes. With `approve`, the named gates are recorded for
    the plan as it stands and nothing is generated — so the record exists before the
    artifacts do.
    """
    inv = extract(module_dir)
    planned = build_structure(inv, semantic=semantic, recall=recall, mermaid=mermaid)
    spec = planned["spec"]
    root = spec["root"]
    module_out = Path(out_root) / Path(inv["root"]).name

    approval = _carried_approval(module_out)
    if approve:
        named = list(GATES) if "all" in approve else [g for g in approve if g in GATES]
        approval = _approve(approval, named, approved_by)
        # stamp the CURRENT fingerprint — but only on the gates just approved.
        # Stamping every carried gate would re-point an old approval at whatever the
        # plan has become, which is the laundering this whole mechanism exists to
        # stop; it is an easy line to write, and it was written here first.
        current = approval_state(root, {})
        for gate in named:
            approval[gate]["sha"] = current[gate]["sha"]
    spec["approval"] = approval
    state = approval_state(root, approval)

    # The review surface is written either way: it is what a human has to read in
    # order to approve anything at all.
    module_out.mkdir(parents=True, exist_ok=True)
    (module_out / "plan.md").write_text(
        render_plan(root, planned["coverage"], state), encoding="utf-8"
    )
    if approve:
        print(_approval_report(root, state, just=approve))
        _write_spec(module_out, spec)
        return spec, [], None

    if not state["ready"]:
        # compare against what is on disk BEFORE writing the new spec over it, or the
        # diff is always empty — the file we would be reading is the one we just wrote
        changed = _changed_leaves(module_out, root)
        _write_spec(module_out, spec)
        print(_awaiting_report(
            root, state, module_dir, out_root,
            approve_flags(semantic, recall, mermaid), changed=changed,
        ))
        return spec, [], None

    annotate_artifacts(inv, root)
    render_leaf_mermaids(inv, root)
    written = generate_all(inv, spec, out_root)

    # §13: the module dir holds the map, the review plan, and the spec
    (module_out / "index.html").write_text(
        render_map(
            spec,
            leaves_prefix="leaves",
            source_base=source_base_for(module_dir, module_out, source_base),
        ),
        encoding="utf-8",
    )

    rep = verify(inv, spec, out_root, critic=critic)
    return spec, written, rep


def _write_spec(module_out: Path, spec: dict) -> None:
    (module_out / "spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")


def approve_flags(semantic, recall, mermaid) -> str:
    """The pass flags a later `--approve` must repeat to hash the same plan."""
    return " ".join(
        f"--{name} <{name}.json>"
        for name, val in (("semantic", semantic), ("recall", recall), ("mermaid", mermaid))
        if val is not None
    )


def _gate_line(name: str, gate: dict) -> str:
    if gate["approved"]:
        return f"  {name:10} APPROVED  {gate['at']} by {gate['by']}  ({gate['sha']})"
    if gate["stale"]:
        return (f"  {name:10} LAPSED    approved as {gate['approved_sha']} "
                f"({gate['at']} by {gate['by']}) but the plan is now {gate['sha']} "
                f"— it changed since it was approved")
    return f"  {name:10} not approved"


def _approval_report(root: dict, state: dict, just) -> str:
    lines = ["", f"Recorded approval for — {root['title']}", ""]
    for gate in GATES:
        lines.append(_gate_line(gate, state[gate]))
    lines += ["", f"approved: {', '.join(just)}"]
    if state["ready"]:
        lines.append("Both gates are approved and current — run the build to generate.")
    else:
        awaiting = [g for g in GATES if not state[g]["approved"]]
        lines.append(f"Still awaiting: {', '.join(awaiting)}")
    return "\n".join(lines)


def _changed_leaves(module_out: Path, root: dict) -> "List[str]":
    """Leaves whose source moved since the artifacts were built.

    An approval lists two hashes, which is honest but unhelpful when it lapses: this
    says which leaves to re-read. It is the same comparison `refresh-stale-leaves`
    will use, and the same one the verifier's freshness axis asserts.
    """
    before = {
        n.get("id"): n.get("source_sha")
        for n in _walk_nodes(_persisted_root(module_out))
        if n.get("source_sha")
    }
    if not before:
        return []
    changed = []
    for n in _walk_nodes(root):
        was = before.get(n.get("id"))
        if was and n.get("source_sha") and was != n.get("source_sha"):
            changed.append(n.get("title") or n.get("id"))
    return changed


def _persisted_root(module_out: Path) -> dict:
    spec_path = module_out / "spec.json"
    if not spec_path.exists():
        return {}
    try:
        return (json.loads(spec_path.read_text(encoding="utf-8")) or {}).get("root") or {}
    except (ValueError, OSError):
        return {}


def _walk_nodes(node: dict):
    if not node:
        return
    yield node
    for b in (node.get("branches") or {}).values():
        yield from _walk_nodes(b)
    for c in node.get("children", []):
        yield from _walk_nodes(c)


def _awaiting_report(root: dict, state: dict, module_dir, out_root, flags: str,
                     changed: "Optional[List[str]]" = None) -> str:
    changed = changed or []
    lines = [
        "", f"AWAITING APPROVAL — {root['title']}", "",
        "Nothing was generated. The plan is written; read it, then approve:",
        "",
        f"    {out_root}/{Path(module_dir).name}/plan.md",
        "",
    ]
    for gate in GATES:
        lines.append(_gate_line(gate, state[gate]))
    if changed:
        lines.append("")
        lines.append("  leaves whose source moved since they were built:")
        for name in changed[:12]:
            lines.append(f"    - {name}")
        if len(changed) > 12:
            lines.append(f"    … and {len(changed) - 12} more")
    lines += [
        "",
        "Gate 1 — structure: every section and linked file appears with the right kind.",
        "Gate 2 — checklists: every claim is grounded; nothing invented, nothing dropped.",
        "",
        "To approve (repeat the same pass flags the build used):",
        "",
        f"    PYTHONPATH=src python3 -m revision_atlas.build {module_dir} "
        f"--mindmaps {out_root} {flags} --approve all",
        "",
        f"Exit code {AWAITING_APPROVAL}: awaiting a human decision, not a failure.",
    ]
    return "\n".join(lines)


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas build (extract → generate → verify)")
    ap.add_argument("module_dir")
    ap.add_argument("--mindmaps", default="mindmaps", help="artifacts root")
    ap.add_argument("--semantic", help="JSON: leaf id -> [claims]")
    ap.add_argument("--recall", help="JSON: leaf id -> {recall,prompt,reveal}")
    ap.add_argument("--mermaid", help="JSON: leaf id -> [.mmd sources]")
    ap.add_argument("--critic", help="JSON: leaf id -> [{detail}]")
    ap.add_argument(
        "--source-base",
        default=None,
        help="path from the map back to the module markdown (default: derived "
        "from the layout; set it if the artifact tree ships without the source)",
    )
    ap.add_argument("--json", help="also write the verification report here")
    ap.add_argument(
        "--approve",
        nargs="+",
        choices=["structure", "checklists", "all"],
        help="Record YOUR approval of the plan as it stands and exit without "
        "generating. Gate 1 is the structure, Gate 2 the checklists. Repeat the "
        "same pass flags you will build with, or the fingerprints differ.",
    )
    ap.add_argument(
        "--by",
        default=None,
        help="who is approving (default: your git user.name, else your login name)",
    )
    args = ap.parse_args(argv)

    spec, written, rep = build(
        args.module_dir,
        args.mindmaps,
        semantic=_load(args.semantic),
        recall=_load(args.recall),
        mermaid=_load(args.mermaid),
        critic=_load(args.critic),
        source_base=args.source_base,
        approve=args.approve,
        approved_by=args.by,
    )
    if rep is None:
        # either just approved, or the plan is still waiting for one: both already
        # printed their own report, and neither may generate anything
        return 0 if args.approve else AWAITING_APPROVAL
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
