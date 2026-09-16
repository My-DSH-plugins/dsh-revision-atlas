"""Verifier + coverage report (ticket 0007, SPEC §6.4 and §14).

Two axes, per §6.4:

  - **coverage** (deterministic). Re-open each generated artifact and assert every
    *mechanical* checklist item — every collapsible and every mermaid block the leaf
    owns — is present in it. A miss is a **failure** (§14: "any unclassified file or
    coverage miss is a failure, not a warning"), because a miss is precisely the
    silent omission this whole project exists to make impossible.
  - **adherence** (deterministic grounding + an LLM critic). Check that each claim
    traces to the leaf's own source, and merge the critic's drift report when one is
    supplied. Both annotate as `needs-review`; neither blocks the build.

Coverage deliberately checks the *mechanical* items and not the claims. A claim is
agent-written prose, and a compaction is under no obligation to repeat its wording —
requiring a claim's words to appear verbatim in the artifact would raise a false
alarm on every leaf. Whether a claim is *faithful* is an adherence question, and
that is where it is asked.

Everything here reads text: HTML, and SVG with real `<text>` labels. Never a raster,
never a VLM (§6.4).
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .extractor import extract
from .notebook_generator import iter_leaves
from .spec_writer import leaf_range

# a claim "traces to the source" when at least this share of its content words
# appear in the leaf's own source range
_GROUNDING_MIN = 0.6

_STOP = frozenset(
    "the a an and or of to in is are was were for with on at by from as it its this that "
    "these those be been being not no do does did than then so such can could may might "
    "will would shall should into out over under more most less least each every their "
    "there where when which who whom what how why all any both few other some own same".split()
)


def _words(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 2]


def _plain(text: str) -> str:
    """Checklist summaries hold the raw `<summary>` HTML — strip it before
    matching, or the tag names (`strong`, `em`) fail every collapsible."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _html.unescape(text or ""))).strip()


def _visible_text(markup: str) -> str:
    """The text a reader actually sees: scripts, styles and tags removed."""
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", _html.unescape(t)).lower()


def _covers(artifact_words: set, needed: List[str]) -> bool:
    """True when the artifact carries every content word of `needed`."""
    return all(w in artifact_words for w in needed)


@dataclass
class Finding:
    level: str      # "failure" | "needs-review"
    check: str
    where: str
    detail: str


@dataclass
class Report:
    module: str
    stats: Dict[str, int] = field(default_factory=dict)
    coverage: List[dict] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    out_of_scope: List[dict] = field(default_factory=list)

    @property
    def failures(self) -> List[Finding]:
        return [f for f in self.findings if f.level == "failure"]

    @property
    def needs_review(self) -> List[Finding]:
        return [f for f in self.findings if f.level == "needs-review"]

    def ok(self) -> bool:
        return not self.failures

    def render(self) -> str:
        out: List[str] = [f"# Verification — {self.module}", ""]
        s = self.stats
        out.append(
            f"Inventory: {s.get('enumerated', 0)} files · "
            f"{s.get('classified', 0)} classified · {s.get('ignored', 0)} ignored · "
            f"{s.get('needs_review_files', 0)} needs-review · "
            f"{s.get('out_of_scope', 0)} out of scope"
        )
        out.append(
            f"Leaves: {s.get('leaves', 0)} · artifacts {s.get('artifacts', 0)} · "
            f"checklist items {s.get('checklist_items', 0)} · "
            f"coverage {s.get('covered', 0)}/{s.get('checklist_items', 0)} · "
            f"grounded claims {s.get('grounded', 0)}/{s.get('claims', 0)}"
        )
        out.append("")

        if self.out_of_scope:
            out.append(
                "## Out of scope (inside the module, but the module's own markdown "
                "never reaches it — informational)"
            )
            for o in self.out_of_scope:
                out.append(f"- {o['path']}: {o['reason']}")
            out.append("")

        seen = [c for c in self.coverage if c["missed"]]
        if seen:
            out.append("## Coverage misses (FAILURES)")
            for c in seen:
                out.append(f"- {c['leaf']}: missing {', '.join(c['missed'])}")
            out.append("")
        else:
            out.append("## Coverage: every mechanical checklist item is present")
            out.append("")

        if self.needs_review:
            out.append("## Needs review")
            for f in self.needs_review:
                out.append(f"- {f.where}: {f.detail}")
            out.append("")

        if self.failures:
            out.append("## FAILURES")
            for f in self.failures:
                out.append(f"- [{f.check}] {f.where}: {f.detail}")
            out.append("")
        out.append(
            "## Verdict: " + ("FAIL — do not ship" if self.failures else "PASS") + ""
            + (f" ({len(self.needs_review)} needs-review)" if self.needs_review else "")
        )
        return "\n".join(out)


def _leaf_artifact(module_dir: Path, i: int) -> Path:
    return module_dir / "leaves" / f"leaf-{i:03d}" / "notebook.html"


def _check_closure(inv: dict, rep: Report) -> None:
    """Every corpus file accounted for, no dangling relative .md link (ADR-0001)."""
    c = inv["closure"]
    for e in inv["files"]:
        if e["status"] == "needs_review":
            rep.findings.append(Finding(
                "failure", "closure", e["path"],
                "unclassified corpus file — classify it or ignore it by rule",
            ))
    for d in inv.get("dangling_links", []):
        rep.findings.append(Finding(
            "failure", "closure", f"{d['file']}:{d['line']}",
            f"links `{d['target']}` which does not exist",
        ))
    rep.stats["needs_review_files"] = c["needs_review"]
    rep.stats["out_of_scope"] = c.get("out_of_scope", 0)
    rep.out_of_scope = inv.get("out_of_scope", [])


def _check_artifacts(module_dir: Path, leaves: List[dict], rep: Report) -> None:
    if not (module_dir / "spec.json").exists():
        rep.findings.append(Finding(
            "failure", "artifact", str(module_dir / "spec.json"),
            "no spec.json next to the notebooks — the frozen contract is missing",
        ))
    for i, leaf in enumerate(leaves):
        p = _leaf_artifact(module_dir, i)
        if not p.exists():
            rep.findings.append(Finding(
                "failure", "artifact", leaf["title"], f"no notebook at {p}",
            ))
    rep.stats["artifacts"] = sum(
        1 for i in range(len(leaves)) if _leaf_artifact(module_dir, i).exists()
    )


def _check_coverage(module_dir: Path, leaves: List[dict], rep: Report) -> None:
    """Each leaf's mechanical checklist items must be present in its artifact."""
    total = covered = 0
    for i, leaf in enumerate(leaves):
        p = _leaf_artifact(module_dir, i)
        missed: List[str] = []
        if p.exists():
            markup = p.read_text(encoding="utf-8")
            words = set(_words(_visible_text(markup)))
            has_svg = "<svg" in markup
            for item in leaf.get("checklist", []):
                if item["kind"] == "details":
                    total += 1
                    label = _plain(item.get("summary") or item.get("text") or "")
                    needed = _words(label)
                    if needed and _covers(words, needed):
                        covered += 1
                    else:
                        missed.append(f"collapsible “{label[:60]}”")
                elif item["kind"] == "mermaid":
                    total += 1
                    if has_svg:
                        covered += 1
                    else:
                        missed.append("mermaid diagram")
        rep.coverage.append({"leaf": leaf["title"], "missed": missed})
        for m in missed:
            rep.findings.append(Finding(
                "failure", "coverage", leaf["title"], f"checklist item not present: {m}",
            ))
    rep.stats["checklist_items"] = total
    rep.stats["covered"] = covered


def _source_text(inv: dict, leaf: dict) -> str:
    start, end = leaf_range(inv, leaf)
    path = Path(inv["root"]) / leaf["file"]
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    lo = 0 if leaf.get("line") is None else start - 1
    hi = len(lines) if end == float("inf") else int(end) - 1
    return " ".join(lines[lo:hi])


def _check_grounding(inv: dict, leaves: List[dict], rep: Report) -> None:
    """Every claim must trace to the leaf's own source range (§6.4b)."""
    claims = grounded = 0
    for leaf in leaves:
        src = set(_words(_source_text(inv, leaf)))
        for item in leaf.get("checklist", []):
            if item["kind"] != "claim":
                continue
            claims += 1
            needed = _words(item["text"])
            if not needed:
                grounded += 1
                continue
            hit = sum(1 for w in needed if w in src) / len(needed)
            if hit >= _GROUNDING_MIN:
                grounded += 1
            else:
                rep.findings.append(Finding(
                    "needs-review", "grounding", leaf["title"],
                    f"claim traces to only {hit:.0%} of its words in the source: "
                    f"“{item['text'][:70]}”",
                ))
    rep.stats["claims"] = claims
    rep.stats["grounded"] = grounded


def _check_anchors(inv: dict, leaves: List[dict], rep: Report) -> None:
    files = {f["path"]: f for f in inv["files"]}
    counts: Dict[str, int] = {}
    for leaf in leaves:
        f = leaf.get("file")
        if not f:
            continue
        if f not in files:
            rep.findings.append(Finding(
                "failure", "anchor", leaf["title"], f"source `{f}` is not in the corpus",
            ))
            continue
        line = leaf.get("line")
        if line is None:
            continue
        if f not in counts:
            counts[f] = len((Path(inv["root"]) / f).read_text(encoding="utf-8").splitlines())
        if not 1 <= line <= counts[f]:
            rep.findings.append(Finding(
                "failure", "anchor", leaf["title"],
                f"anchor {f}:{line} is past the end of a {counts[f]}-line file",
            ))


_EXTERNAL = re.compile(r'(?:src|href)\s*=\s*["\'](https?:)?//', re.I)


def _check_offline(module_dir: Path, leaves: List[dict], rep: Report) -> None:
    """An artifact must not load anything off the network (offline = online)."""
    for i, leaf in enumerate(leaves):
        p = _leaf_artifact(module_dir, i)
        if not p.exists():
            continue
        for m in _EXTERNAL.finditer(p.read_text(encoding="utf-8")):
            rep.findings.append(Finding(
                "failure", "offline-purity", leaf["title"],
                f"loads an external resource: {m.group(0)}",
            ))


def _check_labels(module_dir: Path, leaves: List[dict], rep: Report) -> None:
    """Diagrams carry real, non-empty <text> labels (§6.4: read the text, no VLM)."""
    for i, leaf in enumerate(leaves):
        p = _leaf_artifact(module_dir, i)
        if not p.exists():
            continue
        markup = p.read_text(encoding="utf-8")
        for svg in re.findall(r"(?s)<svg\b.*?</svg>", markup):
            if "flowchart" not in svg[:400]:
                continue
            labels = [
                _html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
                for t in re.findall(r"(?s)<text\b.*?</text>", svg)
            ]
            if not any(labels):
                rep.findings.append(Finding(
                    "failure", "labels", leaf["title"],
                    "a diagram has no readable <text> labels (text→paths?)",
                ))


def _merge_critic(critic: dict, rep: Report) -> None:
    """Fold in the LLM critic's drift report (§6.4b). Annotations only."""
    for leaf, entries in (critic or {}).items():
        for e in entries if isinstance(entries, list) else []:
            detail = e.get("detail") or e.get("drift") or str(e)
            rep.findings.append(Finding("needs-review", "critic", leaf, detail))


def verify(inv: dict, spec: dict, out_root: str, critic: "Optional[dict]" = None) -> Report:
    leaves = [n for n in iter_leaves(spec["root"]) if "checklist" in n]
    module_dir = Path(out_root) / Path(inv["root"]).name
    rep = Report(module=spec["module"])
    rep.stats["enumerated"] = inv["closure"]["enumerated"]
    rep.stats["classified"] = inv["closure"]["classified"]
    rep.stats["ignored"] = inv["closure"]["ignored"]
    rep.stats["leaves"] = len(leaves)
    _check_closure(inv, rep)
    _check_artifacts(module_dir, leaves, rep)
    _check_coverage(module_dir, leaves, rep)
    _check_grounding(inv, leaves, rep)
    _check_anchors(inv, leaves, rep)
    _check_offline(module_dir, leaves, rep)
    _check_labels(module_dir, leaves, rep)
    _merge_critic(critic, rep)
    return rep


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas verifier (ticket 0007)")
    ap.add_argument("module_dir", help="the course-module directory verified")
    ap.add_argument("--mindmaps", default="mindmaps", help="the generated artifacts root")
    ap.add_argument("--critic", help="JSON: the LLM critic's drift report")
    ap.add_argument("--json", help="also write the report as JSON here")
    args = ap.parse_args(argv)

    inv = extract(args.module_dir)
    spec_path = Path(args.mindmaps) / Path(inv["root"]).name / "spec.json"
    if not spec_path.exists():
        print(f"no spec.json at {spec_path} — generate the notebooks first", file=sys.stderr)
        return 2
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    critic = None
    if args.critic:
        critic = json.loads(Path(args.critic).read_text(encoding="utf-8"))

    rep = verify(inv, spec, args.mindmaps, critic=critic)
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
