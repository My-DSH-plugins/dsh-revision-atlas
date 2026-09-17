# 0018 — The course index and `build-course-map`

- **Blocked by:** the module layer (done)
- **Blocks:** —
- **Status:** IN PROGRESS — spec corrected to the fused map (A); building now

## The gap

SPEC §1, §3, §4.1, §12, §13, §14 and §15.4 all specify a **course atlas**: one fused
course map (`mindmaps/index.html`, title = course name, one subtree per module) whose
leaves are the per-module notebooks, and a `build-course-map` skill that builds the
whole course (heavy, batched) and ends by printing per-module verification.

What shipped is the module layer only. `revision_atlas.build` builds one module, and
the shipped skills are `revision-atlas` (per-module) and `refresh-stale-leaves`.
Pointed at a directory of modules, the pipeline finds no module README at depth 0 and
fails — it does **not** produce the course atlas the product model is.

This was flagged as "unbuilt" in [0011](0011-the-map-reaches-the-notebooks.md) and in
passing, but never ticketed, so it stayed invisible — and the shipped skill's scope
diverged from what §12 names it.

## Missing

1. **Fused course-map renderer** — `atlas.json` (course name + ordered modules) and the
   single `index.html` whose module subtrees hold the leaves, with
   `<module-slug>--<leaf-id>` namespacing.
2. **`build-course-map`** — the primary, course-level entry point: discover + order the
   modules, delegate each to `build-module-map` (per-module plan → 2 gates → generate),
   stop at the first failure, then render the one fused map.
3. **`build-module-map`** — extract the current per-module pipeline (extract → plan →
   gates → generate → notebooks) into its own skill; the inner unit, not the front door.
4. **Skill wiring** — restore §12's shape, now four skills: `revision-atlas` (router) →
   `build-course-map` (course, user-invoked) + `build-module-map` (module) +
   `refresh-stale-leaves` (model-invoked).

## Acceptance

- Pointed at `…/Harness Engineering/modules`, it builds every module and renders one
  fused `mindmaps/index.html`: course root → one subtree per module → leaves, with
  `<module-slug>--<leaf-id>` fragments and notebook back-links resolving to it.
- Per-module gates still apply: each module's plan is approved before it generates,
  and a module with stale leaves is refreshed, not rebuilt blindly.
- The course index is regenerable and machine-checked the same way the module maps
  are (a module that fails to verify fails the course build).

## Evidence required

The existing protocol: build the two fixture courses (M5 and M2) end-to-end as a
course, and confirm the fused map, the per-module gates, and the namespaced-id links.
A cold run of the router + `build-course-map` skill against a course directory.

## Grill log — Round 1 (settled)

- **Module-dir discovery (Q1):** a module directory is "a directory whose children
  are directories each containing a README"; never hardcode the name `modules/`.
  Verified on both fixtures: the heuristic uniquely picks `modules/` (siblings
  `discussions/`, `frameworks/`, `tech/` hold flat files or a top-level README, not
  subdirs-with-READMEs).
- **Approval granularity (Q2):** per module, inside `build-course-map`.
- **Ordering (Q3):** syllabus.md first → numeric prefix on module names → else fix an
  order and get it approved before per-module work.
- **Failure isolation (Q4):** stop at the first failure; report what failed; recommend
  decisions; let the human decide how to proceed. (Approval is a normal pause, not a
  failure.)
- **Router + modular skills (Q5):** `revision-atlas` becomes a router; a new
  single-module skill carries the current pipeline; `refresh-stale-leaves` stays
  module-level — confirmed already module-level (reads one module's `spec.json` and
  refreshes its stale leaves).

### Facts that settle apparent open points

- Both fixtures' module dirs are `NN-slug`, and each README H1 already carries
  `M# · Title` (e.g. `# M5 · Context Engineering II: Retrieval & Grounding`). The
  syllabus "Module map" table agrees with the numeric order. ⇒ **index node title =
  module README H1**; syllabus supplies order only, not titles.
- Syllabus "6 parts" is an editorial layer absent from the dirs. ⇒ the fused map
  mirrors course → modules → leaves only; no "parts" level is invented.

## Round 2 — settled

- **Map structure = A (fused).** One `mindmaps/index.html`: course root → module
  subtrees → leaves. No separate `<module>/index.html`. `initialExpandLevel` collapses
  to module level so the fused map *is* the course index at rest.
- **Leaf ids namespaced** `<module-slug>--<leaf-id>` across the fused map, its
  map → notebook links, and every notebook's `← module map` back-link
  (`../../../index.html#<module-slug>--<leaf-id>`).
- **Root name source:** syllabus `**Course title:**` field (verbatim) → parent-dir
  name of the modules dir → the modules dir's own name (when layout is
  `<courseName>/<moduleName>`). `repo` = the directory name.
- **Primary skill = `build-course-map`** (course-level). The module layer is the
  reusable inner unit, not the front door — the drift this issue existed to catch.
