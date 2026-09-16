# 0009 — `build` writes the map

- **Blocked by:** 0004, 0006
- **Blocks:** —
- **Status:** done

## The defect

SPEC §13 puts the map at `mindmaps/<module>/index.html` — it is the artifact the
reader actually navigates. `render_map` existed and the step was wired into
`renderer.py`'s own CLI, but `build.build()` never called it: the one-command
pipeline wrote `leaves/`, `plan.md` and `spec.json` and silently omitted the map.

Found while verifying ticket 0008: the fix had to be shown to reach *the
artifact*, and the artifact was not there.

## Fix

`build.build()` writes `module_out / "index.html"` from `render_map(spec)` beside
the plan, so one command produces the whole §13 tree. Regression assertion added
to `TestBuildPipeline.test_end_to_end_build`.

## Evidence

M5 end-to-end: `05-data-engineering-2/` now holds `index.html`, `leaves/`,
`plan.md`, `spec.json`; the map carries each leaf's own recall (the volume leaf
and the per-column leaf render different blocks). Verifier still **PASS**, exit 0;
56 tests green.
