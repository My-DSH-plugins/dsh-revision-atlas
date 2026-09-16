"""Assemble the skill bundle (ticket 0013).

A skill is not usable until the Python it drives travels with it: the SKILL.md
invokes the pipeline as `PYTHONPATH=<base>/tools python3 -m revision_atlas…`, and
`<base>` is the skill's own directory. This produces that self-contained directory —
the skill content plus a copy of this package under `tools/` — for either install
route the host offers:

- a plain skills-dir install (`~/.dsh/skills/<name>/`, SPEC §12), or
- a plugin provider, whose `resourceBase` points at the same directory.

`src/revision_atlas/` remains the source of truth for development and tests; the
bundle's copy is generated, never hand-edited, so the two cannot drift by
disagreement — only by forgetting to reassemble, which the cold run will catch.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import List, Optional

#: the repo root — `skills/` and `src/revision_atlas/` hang off it
_REPO = Path(__file__).resolve().parents[2]

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info")


def assemble(target: str, skills_dir: str = "skills") -> List[Path]:
    """Copy every skill plus a tools/ copy of the package into `target`."""
    root = Path(target)
    skills_root = (_REPO / skills_dir).resolve()
    written: List[Path] = []
    for skill in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        dst = root / skill.name
        shutil.copytree(skill, dst, dirs_exist_ok=True, ignore=_IGNORE)
        written.append(dst)
    # the pipeline rides along with the entry skill
    tools = root / "revision-atlas" / "tools" / "revision_atlas"
    shutil.copytree(
        _REPO / "src" / "revision_atlas", tools, dirs_exist_ok=True, ignore=_IGNORE
    )
    written.append(tools)
    return written


def main(argv: "Optional[List[str]]" = None) -> int:
    ap = argparse.ArgumentParser(description="Assemble the Revision Atlas skill bundle")
    ap.add_argument("target", help="write the bundle here (a skills dir, or a temp dir)")
    args = ap.parse_args(argv)

    for path in assemble(args.target):
        print(f"assembled {path}")
    print()
    print("Install as plain skills, or point a plugin's resourceBase at it:")
    print(f"  ~/.dsh/skills/  <-  {Path(args.target) / 'revision-atlas'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
