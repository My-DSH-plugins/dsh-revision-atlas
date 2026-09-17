"""Course-level build: discover, order, and render the fused course map.

SPEC §12: `build-course-map` is the primary, course-level entry point. The Python
side hands the skill three deterministic primitives it cannot do itself well:

- `resolve` — find the modules directory under a course directory (never hardcode
  the name `modules/`; a modules dir is "a directory whose children are directories
  each containing a README").
- `order_modules` — the faithful module order: syllabus.md, else the numeric prefix
  on each module name, else an arbitrary order the skill must get approved.
- `render_course` — the ONE fused map (`mindmaps/index.html`) whose module subtrees
  are the module maps, plus the course index (`mindmaps/atlas.json`).

The per-module build (plan → two gates → generate) stays in `build`; this module
only assembles what is already built. It reads each module's frozen `spec.json`
from the artifact tree, so it cannot drift from what was actually generated.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .renderer import render_course_map, source_base_for


class CourseError(Exception):
    """A discovery/ordering decision the skill must surface to the human.

    Distinct from a verification failure: the pipeline cannot proceed without a
    human decision (which directory is the course, what order the modules go in),
    so the skill reports the options and stops rather than guessing.
    """


def _has_readme(path: Path) -> bool:
    return any(
        p.is_file() and p.name.lower().startswith("readme")
        for p in path.iterdir()
    )


def _is_modules_dir(path: Path) -> bool:
    """Q1 heuristic: a dir whose children are directories each containing a README."""
    children = [p for p in path.iterdir() if p.is_dir()]
    if not children:
        return False
    return all(_has_readme(p) for p in children)


def resolve(course_dir: str) -> Tuple[Path, Path]:
    """Return (course_root, modules_dir).

    The input may be the course root *or* the modules directory directly (the
    acceptance test points at `…/Harness Engineering/modules`). If neither, raise
    `CourseError` — the skill reports the options, never guesses.
    """
    root = Path(course_dir).resolve()
    if _is_modules_dir(root):
        return root.parent, root
    matches = [p for p in root.iterdir() if p.is_dir() and _is_modules_dir(p)]
    if len(matches) == 1:
        return root, matches[0]
    if not matches:
        raise CourseError(
            f"no modules directory found under {root} — expected a directory whose "
            f"children are directories each containing a README (or a parent of one)"
        )
    raise CourseError(
        f"multiple module directories found under {root}: "
        + ", ".join(sorted(str(m) for m in matches))
        + " — name which one, or point me at it directly"
    )


def discover_modules(modules_dir: Path) -> List[Path]:
    return sorted(
        p for p in modules_dir.iterdir() if p.is_dir() and _has_readme(p)
    )


def _num_prefix(path: Path) -> Optional[int]:
    m = re.match(r"^(\d+)", path.name)
    return int(m.group(1)) if m else None


def _syllabus_module_numbers(course_root: Path) -> Optional[List[int]]:
    """The ordered `M#` sequence from the syllabus's module map, if machine-readable.

    Both fixture syllabi list modules as `M1 · Title` (in a two-column table and
    again under `### Part …` headings). The `M#` numbers in document order are the
    author's intended order; we return them deduplicated.
    """
    syl = course_root / "syllabus.md"
    if not syl.exists():
        return None
    text = syl.read_text(encoding="utf-8")
    seen: Dict[int, int] = {}
    order: List[int] = []
    # The `### Part …` sections list modules as `**M# · Title**` in reading order;
    # the two-column "Module map" table interleaves (M1,M10,M2,M11,…), so it is
    # NOT the order — only the bold section headers are sequential.
    for m in re.finditer(r"\*\*M(\d{1,3})\s*·", text):
        n = int(m.group(1))
        if n not in seen:
            seen[n] = 1
            order.append(n)
    return order or None


def order_modules(module_dirs: List[Path], course_root: Path) -> Tuple[List[Path], str]:
    """Order modules: syllabus → numeric prefix → arbitrary (skill must approve).

    Returns (ordered, source) where `source` is "syllabus", "numeric" or "arbitrary".
    "arbitrary" is a decision the skill surfaces for approval before per-module work.
    """
    dirs = list(module_dirs)
    # 1. syllabus.md, if it maps cleanly onto the module dirs
    syl_nums = _syllabus_module_numbers(course_root)
    by_num: Dict[int, Path] = {}
    for d in dirs:
        n = _num_prefix(d)
        if n is not None:
            by_num[n] = d
    if syl_nums and set(syl_nums) == set(by_num) and len(syl_nums) == len(by_num):
        ordered = [by_num[n] for n in syl_nums]
        return ordered, "syllabus"
    # 2. every module name carries a number → sort by it
    if all(_num_prefix(d) is not None for d in dirs):
        return sorted(dirs, key=lambda d: _num_prefix(d)), "numeric"
    # 3. no machine order → deterministic arbitrary, and the skill asks the human
    return sorted(dirs, key=lambda d: d.name.lower()), "arbitrary"


def course_name(course_root: Path) -> str:
    """The course's display title: syllabus `**Course title:**` field, else the dir name."""
    syl = course_root / "syllabus.md"
    if syl.exists():
        m = re.search(r"\*\*Course title:\*\*\s*([^*]+)", syl.read_text(encoding="utf-8"))
        if m:
            # the field ends with a markdown hard-break `\` before the next `**…**`
            return m.group(1).strip().rstrip("\\").strip()
    return course_root.name


def module_slug(module_dir: Path) -> str:
    return module_dir.name


def _course_root(module_dirs: List[Path]) -> Path:
    """The course directory: the parent of the modules dir (or the module's parent)."""
    parent = Path(module_dirs[0]).resolve().parent
    return parent.parent if _is_modules_dir(parent) else parent


def module_title(module_dir: Path, out_root: Path) -> str:
    """The module's display title — its README H1, read from the frozen spec."""
    spec_path = out_root / module_dir.name / "spec.json"
    if spec_path.exists():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            if spec.get("module"):
                return spec["module"]
        except (ValueError, OSError):
            pass
    # fallback: the directory name is a stable, honest title
    return module_dir.name


def render_course(
    course_title: str, module_dirs: List[Path], out_root: str, repo: Optional[str] = None
) -> str:
    """Render the fused map + course index from already-built module specs.

    Returns the path to the written index.html.
    """
    out = Path(out_root)
    out.mkdir(parents=True, exist_ok=True)
    course_root = _course_root(module_dirs)
    modules: List[dict] = []
    atlas_modules: List[dict] = []
    for md in module_dirs:
        slug = module_slug(md)
        spec_path = out / slug / "spec.json"
        if not spec_path.exists():
            raise CourseError(
                f"{slug} has no spec.json under {out} — build it first "
                f"(python -m revision_atlas.build {md} --mindmaps {out})"
            )
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        modules.append({
            "spec": spec,
            "slug": slug,
            "source_base": source_base_for(str(md), out),
        })
        readme = md / "README.md"
        try:
            readme_rel = (
                str(readme.resolve().relative_to(course_root.resolve()))
                if readme.exists() else None
            )
        except ValueError:
            readme_rel = None
        atlas_modules.append({
            "id": slug,
            "title": spec.get("module") or slug,
            "readme": readme_rel,
            "anchor": f"mindmaps/index.html#{slug}",
        })
    (out / "index.html").write_text(
        render_course_map(course_title, modules), encoding="utf-8"
    )
    atlas = {
        "course": course_title,
        "repo": repo or course_root.name,
        "index": "mindmaps/index.html",
        "modules": atlas_modules,
    }
    (out / "atlas.json").write_text(json.dumps(atlas, indent=2), encoding="utf-8")
    return str(out / "index.html")


def render_single(module_dir: str, out_root: str) -> str:
    """Render the fused map for ONE module (build-module-map's viewable output)."""
    md = Path(module_dir).resolve()
    course_root = md.parent.parent if _is_modules_dir(md.parent) else md.parent
    title = course_name(course_root)
    return render_course(title, [md], out_root, repo=course_root.name)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Course map assembly: discover, order and render the fused map "
        "(modules must already be built with `python -m revision_atlas.build`)"
    )
    ap.add_argument("course_dir", nargs="?", help="the course root, or its modules directory")
    ap.add_argument("--module", help="render a single module instead of a whole course")
    ap.add_argument("--mindmaps", default="mindmaps", help="artifacts root")
    args = ap.parse_args(argv)

    if args.module:
        index = render_single(args.module, args.mindmaps)
        print(f"wrote {index}")
        return 0

    if not args.course_dir:
        ap.error("provide course_dir or --module")

    course_root, modules_dir = resolve(args.course_dir)
    dirs = discover_modules(modules_dir)
    if not dirs:
        print(f"no modules found under {modules_dir}")
        return 2
    ordered, source = order_modules(dirs, course_root)
    title = course_name(course_root)
    print(f"course: {title}")
    print(f"order ({source}): " + ", ".join(d.name for d in ordered))
    if source == "arbitrary":
        print("  (arbitrary order — ask the human to approve it before building)")
    index = render_course(title, ordered, args.mindmaps, repo=course_root.name)
    print(f"wrote {index} + {args.mindmaps}/atlas.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
