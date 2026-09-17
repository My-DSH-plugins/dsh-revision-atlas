---
name: build-course-map
description: Build a whole course's revision atlas — discover and order the modules, build each (delegating to build-module-map with per-module human gates), then render ONE fused mind map whose module subtrees are the module maps. Use when the user wants a course index and every module map.
---

# Build a course map

You are the course-level entry point (SPEC §12). You build the WHOLE course: discover
the modules, order them, drive each module through its own plan → two gates →
generate → approve, and finally render the ONE fused map (`mindmaps/index.html`) whose
module subtrees are the module maps, plus the course index (`mindmaps/atlas.json`).

## Where the tools live

The Python package is the `build-module-map` skill's bundle. With `<base>` your own
directory, it is the sibling `<base>/../build-module-map/tools/`:

```
PYTHONPATH=<base>/../build-module-map/tools python3 -m revision_atlas.<module> ...
```

## Step 1 — discover and order

```
PYTHONPATH=<base>/../build-module-map/tools python3 -m revision_atlas.course <course_dir> --mindmaps <out>
```

This resolves the modules directory and prints the course name and the module order.
It never hardcodes the word `modules/`: a modules directory is "a directory whose
children are directories each containing a README". The input may be the course root
or the modules directory directly.

Ordering is: `syllabus.md` first, else the numeric prefix on each module name, else an
**arbitrary** order — and the CLI says so. If it reports `arbitrary`, STOP and ask the
human to approve the order before any per-module work.

The course name (the fused map's root) comes from the syllabus's `**Course title:**`
field, else the course directory's name.

## Step 2 — build every module, one at a time

For each module, in order, delegate to the `build-module-map` skill: extract → plan →
Gate 1 (structure) → Gate 2 (checklists) → approve → generate → notebooks. Each
module's plan is approved by the human before it generates. Work sequentially: finish
module N before starting module N+1.

## Step 3 — stop at the first failure

If any module fails, STOP there. Report what failed, recommend the decisions the human
could take (skip it, fix the source, classify the stray file, re-order), and let the
human decide. Never guess and never silently skip a module. Approval is a normal pause,
not a failure.

## Step 4 — render the fused map

Once every module is built, render the fused map and the course index:

```
PYTHONPATH=<base>/../build-module-map/tools python3 -m revision_atlas.course <course_dir> --mindmaps <out>
```

This writes `mindmaps/index.html` (course root → one subtree per module → leaves, with
`<module-slug>--<leaf-id>` namespacing) and `mindmaps/atlas.json`. Then verify that
every link resolves, and report per-module verification the way `build-module-map`
does.

## Never

- skip a module or reorder silently — the order is faithful to the syllabus or the
  numeric prefixes, or approved by the human;
- build module N+1 before module N is approved and generated;
- render the fused map before every module's notebooks exist.
