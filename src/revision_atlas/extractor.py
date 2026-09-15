"""Deterministic inventory extractor for a course-module directory.

Ticket 0001. No LLM: walks one module directory and emits, for every markdown
file, its classification (classified / ignored / needs_review), its headings,
relative .md links, mermaid fences and <details> blocks.

Closure invariant (enforced, not merely reported):
- every .md is accounted for exactly once (unaccounted fails the run);
- every relative .md link that points inside the module tree resolves to a real
  file (a dangling link fails the run).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

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


def _parse_file(path: Path) -> Tuple[List[dict], List[dict], List[int], List[int]]:
    """Return (headings, links, mermaid_lines, details_lines) for one markdown file."""
    headings: List[dict] = []
    links: List[dict] = []
    mermaid_lines: List[int] = []
    details_lines: List[int] = []
    in_fence = False
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
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
                details_lines.append(lineno)
            for lm in _LINK_RE.finditer(line):
                target = lm.group(1).strip()
                if _is_relative_md(target):
                    links.append({"target": target, "line": lineno})
    return headings, links, mermaid_lines, details_lines


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
    details: Dict[str, List[int]] = {}

    for rel in md_files:
        posix = rel.as_posix()
        matched = next((part for part in rel.parts if part.lower() in IGNORED_DIRS), None)
        if matched is not None:
            files.append(
                {"path": posix, "status": "ignored", "reason": f"noise dir ({matched})"}
            )
            continue
        reason = "module README" if posix.lower() == "readme.md" else "sidecar"
        files.append({"path": posix, "status": "classified", "reason": reason})
        h, l, m, d = _parse_file(root / rel)
        headings[posix] = h
        links[posix] = l
        mermaid[posix] = m
        details[posix] = d

    # Resolve relative .md links against the inventory. A link whose target sits
    # inside the module tree but does not exist is dangling. Links that point
    # outside the tree (cross-module references) are never "dangling".
    dangling: List[dict] = []
    for source, llist in links.items():
        for l in llist:
            tgt = l["target"].split("#", 1)[0].strip()
            if not tgt:
                continue
            resolved = (root / tgt).resolve()
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
        # Always 0 in 0001: relationship classification (and the residue that
        # becomes `needs_review`) is owned by 0002.
        "needs_review": sum(1 for f in files if f["status"] == "needs_review"),
        "unaccounted": sum(
            1 for f in files if f["status"] not in ("classified", "ignored", "needs_review")
        ),
        "dangling_links": len(dangling),
    }

    return {
        "root": str(root),
        "files": files,
        "headings": headings,
        "links": links,
        "mermaid_blocks": mermaid,
        "details_blocks": details,
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
