# 0018 — The course index and `build-course-map`

- **Blocked by:** the module layer (done)
- **Blocks:** —
- **Status:** OPEN — the top layer of the product, specified since SPEC line 9 and
  never built

## The gap

SPEC §1, §3, §4.1, §12, §13, §14 and §15.4 all specify a **course atlas**: a course
index map (`mindmaps/atlas.yml`, title = course name, one node per module) above one
module map per module, and a `build-course-map` skill that builds the whole course
(heavy, batched) and ends by printing per-module verification.

What shipped is the module layer only. `revision_atlas.build` builds one module, and
the shipped skills are `revision-atlas` (per-module) and `refresh-stale-leaves`.
Pointed at a directory of modules, the pipeline finds no module README at depth 0 and
fails — it does **not** produce the course atlas the product model is.

This was flagged as "unbuilt" in [0011](0011-the-map-reaches-the-notebooks.md) and in
passing, but never ticketed, so it stayed invisible — and the shipped skill's scope
diverged from what §12 names it.

## Missing

1. **Course index renderer** — `atlas.yml` (title = course name, nodes = modules) and
   the top-level index map linking into each module map.
2. **`build-course-map`** — a course-level entry point that walks the modules under a
   course directory and drives `build` once per module, then renders the index.
3. **Skill wiring** — restore §12's shape: `revision-atlas` (router) → `build-course-map`
   (course, user-invoked) + `refresh-stale-leaves` (model-invoked).

## Acceptance

- Pointed at `…/Harness Engineering/modules`, it builds every module and the course
  index; the index has one node per module, each linking to that module's map.
- Per-module gates still apply: each module's plan is approved before it generates,
  and a module with stale leaves is refreshed, not rebuilt blindly.
- The course index is regenerable and machine-checked the same way the module maps
  are (a module that fails to verify fails the course build).

## Evidence required

The existing protocol: build the two fixture courses (M5 and M2) end-to-end as a
course, and confirm the index, the per-module maps, and the gate behaviour. A cold
run of the router + `build-course-map` skill against a course directory.
