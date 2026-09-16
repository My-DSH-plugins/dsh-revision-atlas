"""Deterministic inventory extractor for a course-module directory.

Ticket 0001. No LLM. Walks one module directory and emits, for every markdown
file: its classification (classified / ignored / needs_review), a deterministic
relationship `kind` where one applies, its headings, relative .md links, mermaid
fences, and its `<details>` collapsibles with their `<summary>` labels.

Deterministic classification (SPEC §7, filename/structure signals only — the
residue is flagged, never guessed):

  root README.md                    -> module
  *-for.md / *-against.md           -> debate-for / debate-against
  task-state-*.md (own TOC or >1 H1)-> aggregator
  task-state-*.md                   -> framework-domain
  *worked-example*.md               -> worked-example
  everything else                   -> needs_review  (0002 / human types it)

These file-level hints map up to SPEC §5 node kinds in 0002: a debate-for and its
debate-against become one `debate-pair` node; the `framework-domain` files and
their `aggregator` become one `framework-matrix` node.

Closure invariant (enforced, not merely reported): every .md is accounted for
exactly once, and every relative .md link that points inside the module tree
resolves to a real file.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Directories treated as noise. A .md under any of these is `ignored`, not
# classified. Case-insensitive, matched on any path segment.
IGNORED_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "handwrittennotes",
        "scratch",
        ".venv",
        "venv",
        "env",
        ".uv-cache",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
    }
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_DEBATE_RE = re.compile(r"-(for|against)\.md$", re.IGNORECASE)
_TASK_STATE_RE = re.compile(r"^task-state-[a-z0-9-]+\.md$", re.IGNORECASE)
_SUMMARY_RE = re.compile(r"<summary[^>]*>(.*?)</summary>", re.IGNORECASE | re.DOTALL)


def _fence_info(stripped: str) -> "str | None":
    """Return a fence's info string if `stripped` opens/closes a code fence.

    ``""`` is a bare (closing) fence; ``"mermaid"`` is an opening mermaid fence;
    ``None`` means the line is not a fence.
    """
    for opener in ("```", "~~~"):
        if stripped.startswith(opener):
            return stripped[len(opener):].strip()
    return None


def _is_relative_md(target: str) -> bool:
    if target.startswith(("http://", "https://", "//", "#", "mailto:", "data:")):
        return False
    return target.split("#", 1)[0].lower().endswith(".md")


def _extract_summary(lines: List[str], start: int, window: int = 5) -> "str | None":
    """Return the verbatim inner text of a <details> block's <summary>, or None.

    Scans forward from the `<details>` line, since a summary may sit on the same
    line or a later one. Verbatim: inner markdown/HTML is preserved and only
    surrounding whitespace is trimmed — stripping markup is 0002's call.
    """
    chunk = "".join(lines[start:start + window])
    m = _SUMMARY_RE.search(chunk)
    return m.group(1).strip() if m else None


def _parse_file(path: Path) -> Tuple[List[dict], List[dict], List[int], List[dict]]:
    """Return (headings, links, mermaid_lines, details) for one markdown file.

    `details` items are `{"line": int, "summary": str | None}` — a collapsible's
    position and its label. Bodies are never copied; they stay addressed by
    position and are read later by the generator.
    """
    headings: List[dict] = []
    links: List[dict] = []
    mermaid_lines: List[int] = []
    details: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    in_fence = False
    for idx, line in enumerate(lines):
        lineno = idx + 1
        stripped = line.strip()
        fence = _fence_info(stripped)
        if fence is not None:
            if in_fence:
                if fence == "":
                    in_fence = False
            else:
                in_fence = True
                if fence.lower() == "mermaid":
                    mermaid_lines.append(lineno)
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line.rstrip("\n"))
        if m:
            headings.append(
                {"rank": len(m.group(1)), "text": m.group(2).strip(), "line": lineno}
            )
        if "<details" in stripped:
            details.append({"line": lineno, "summary": _extract_summary(lines, idx)})
        for lm in _LINK_RE.finditer(line):
            target = lm.group(1).strip()
            if _is_relative_md(target):
                links.append({"target": target, "line": lineno})
    return headings, links, mermaid_lines, details


def _classify_sidecar(posix: str, headings: List[dict]) -> "str | None":
    """Deterministically type a non-README sidecar, or return None (residue)."""
    name = posix.rsplit("/", 1)[-1]
    m = _DEBATE_RE.search(name)
    if m:
        return "debate-" + m.group(1).lower()
    if _TASK_STATE_RE.match(name):
        h1_count = sum(1 for h in headings if h["rank"] == 1)
        has_toc = any(
            h["rank"] == 2 and h["text"].strip().lower().startswith("table of contents")
            for h in headings
        )
        if h1_count > 1 or has_toc:
            return "aggregator"
        return "framework-domain"
    if "worked-example" in name.lower():
        return "worked-example"
    return None


def extract(root: "str | Path") -> dict:
    root = Path(root)
    rroot = root.resolve()
    md_files = sorted(
        p.relative_to(root)
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() == ".md"
    )

    files: List[dict] = []
    headings: Dict[str, List[dict]] = {}
    links: Dict[str, List[dict]] = {}
    mermaid: Dict[str, List[int]] = {}
    details: Dict[str, List[dict]] = {}

    def _inside(p: Path) -> bool:
        try:
            return p.resolve().is_relative_to(rroot)
        except ValueError:
            return False

    def _noise(rel: Path) -> "Optional[str]":
        return next((part for part in rel.parts if part.lower() in IGNORED_DIRS), None)

    # --- what belongs to this module? ----------------------------------------
    # A file is IN SCOPE when it sits DIRECTLY under the module path, or when an
    # in-scope file links to it and it lies INSIDE the module path. A module's
    # narrative is its top-level markdown plus whatever that markdown reaches — a
    # subdirectory's own README (a `code/` folder, a `notebooks/` folder) is not
    # part of the narrative unless something in the narrative cites it. This is
    # what keeps a module's scope its own, without an ever-growing ignore list.
    seeds = [rel for rel in md_files if len(rel.parts) == 1 and _noise(rel) is None]
    in_scope: List[Path] = []
    seen: set = set()
    queue = list(seeds)
    while queue:
        rel = queue.pop(0)
        posix = rel.as_posix()
        if posix in seen:
            continue
        seen.add(posix)
        in_scope.append(rel)
        h, l, m, d = _parse_file(root / rel)
        headings[posix] = h
        links[posix] = l
        mermaid[posix] = m
        details[posix] = d
        for link in l:
            target = link["target"].split("#", 1)[0].strip()
            if not target or not target.lower().endswith(".md"):
                continue
            cand = root / rel.parent / target      # links resolve against the file
            if not cand.exists() or not _inside(cand):
                continue                           # outside the module: not ours
            crev = cand.relative_to(root)
            if _noise(crev) is None and crev.as_posix() not in seen:
                queue.append(crev)

    for rel in in_scope:
        posix = rel.as_posix()
        h = headings[posix]
        if posix.lower() == "readme.md":
            files.append(
                {"path": posix, "status": "classified", "kind": "module", "reason": "module README"}
            )
        else:
            kind = _classify_sidecar(posix, h)
            if kind is not None:
                files.append(
                    {"path": posix, "status": "classified", "kind": kind, "reason": f"typed: {kind}"}
                )
            else:
                files.append(
                    {"path": posix, "status": "needs_review", "reason": "untyped sidecar (residue)"}
                )

    # Noise dirs are ignored BY EXPLICIT RULE (SPEC §6.1). Anything else inside
    # the module that the narrative never reaches is reported as out of scope —
    # visible in the report, but never a build failure, because it is not part of
    # the module's own material.
    out_of_scope: List[dict] = []
    for rel in md_files:
        posix = rel.as_posix()
        if posix in seen:
            continue
        matched = _noise(rel)
        if matched is not None:
            files.append(
                {"path": posix, "status": "ignored", "reason": f"noise dir ({matched})"}
            )
        else:
            out_of_scope.append({
                "path": posix,
                "reason": "not directly under the module and not linked by an in-scope file",
            })

    # Resolve relative .md links against the inventory. A link whose target sits
    # inside the module tree but does not exist is dangling. Links that point
    # outside the tree (cross-module references) are never "dangling".
    dangling: List[dict] = []
    for source, llist in links.items():
        for l in llist:
            tgt = l["target"].split("#", 1)[0].strip()
            if not tgt:
                continue
            resolved = (root / Path(source).parent / tgt).resolve()
            inside = False
            try:
                inside = resolved.is_relative_to(rroot)
            except ValueError:
                inside = False
            if inside and not resolved.exists():
                dangling.append({"source": source, "target": tgt, "line": l["line"]})

    closure = {
        "enumerated": len(files),
        "classified": sum(1 for f in files if f["status"] == "classified"),
        "ignored": sum(1 for f in files if f["status"] == "ignored"),
        "needs_review": sum(1 for f in files if f["status"] == "needs_review"),
        "unaccounted": sum(
            1 for f in files if f["status"] not in ("classified", "ignored", "needs_review")
        ),
        "out_of_scope": len(out_of_scope),
        "dangling_links": len(dangling),
    }

    return {
        "root": str(root),
        "files": files,
        "headings": headings,
        "links": links,
        "mermaid_blocks": mermaid,
        "details_blocks": details,
        "out_of_scope": out_of_scope,
        "dangling_links": dangling,
        "closure": closure,
    }


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas extractor (ticket 0001)")
    ap.add_argument("module_dir", help="path to a course-module directory")
    args = ap.parse_args(argv)
    inv = extract(args.module_dir)
    print(json.dumps(inv, indent=2))
    c = inv["closure"]
    return 0 if (c["unaccounted"] == 0 and c["dangling_links"] == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
