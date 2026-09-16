# 0007 — Verifier + coverage report

- **Blocked by:** 0004, 0005, 0006
- **Blocks:** —
- **Status:** done — deterministic axes + report + critic pass; critic cold-test pending

## Goal

Two-axis verification (SPEC §6.4): **coverage** (checklist items present,
deterministic) + **adherence** (deterministic grounding + LLM critic), and the
coverage report (SPEC §14).

## Acceptance

- a coverage miss is a **failure**, not a warning ✓
- drift flags from the critic and grounding misses → `needs-review` ✓
- report prints inventory / coverage / adherence / anchors / offline-purity / `needs-review` ✓
- adherence reads the text artifact (HTML + SVG labels), never a raster — no VLM ✓

## Open decision — resolved

- **`needs-review`: block vs annotate.** §14 settles it: "any unclassified file or
  a coverage **miss** is a failure, not a warning", while §6.4 routes *drift* and
  *grounding* misses to `needs-review`. So: coverage/missing-artifact/dangling-link/
  external-reference → **FAIL** (exit 1); grounding drift and critic findings →
  **annotate** (exit 0).

## Done — `src/revision_atlas/verifier.py`

Seven checks, run by `verify(inv, spec, out_root, critic=None)`:

| check | level | what it asserts |
|---|---|---|
| `closure` | failure | every corpus file classified; no dangling relative `.md` link (ADR-0001) |
| `artifact` | failure | `spec.json` + a notebook for every leaf |
| `coverage` | failure | each leaf's **mechanical** checklist items present in its artifact |
| `grounding` | needs-review | each claim traces to ≥60% of its words in the leaf's own source range |
| `anchor` | failure | every leaf's `file`/`line` exists |
| `offline-purity` | failure | no external (http/https/protocol-relative) resource in any artifact |
| `labels` | failure | every diagram SVG carries non-empty real `<text>` labels |

CLI: `python -m revision_atlas.verifier <module_dir> --mindmaps <dir> [--critic j] [--json p]`
— exit 0 pass, 1 fail, 2 no artifacts. The critic pass is
`.scratch/revision-atlas/skill/verifier-critic.md`; its JSON is merged as
`needs-review`.

## Coverage checks the seeds, not the claims — on purpose

A claim is agent-written prose, and a compaction is under no obligation to repeat
its wording; requiring a claim's words to appear verbatim in the artifact would
raise a false alarm on every leaf. Whether a claim is *faithful* is an adherence
question, and that is where it is asked (grounding + critic). The mechanical seeds
(collapsibles, mermaid blocks) are exactly the opposite: they are concrete source
items that must not vanish, so they are the coverage check.

## Consequent change to the audit surface (0005/0006)

`leaf.source` changed from a list of bullet **strings** to a list of
`{kind, line, text}` **items** — bullets, collapsibles (`[details] …`) and mermaid
blocks (`[diagram] mermaid`). A collapsible seed is only checkable if the
collapsible is actually enumerated on the audit surface; before this it had nothing
to match against. `generate_all` also writes `spec.json` beside the notebooks
(§13's derived contract) so the verifier reads the frozen checklists from the
artifact tree rather than re-running the pipeline.

## Evidence

- M2 end-to-end: 12 files · 29 leaves · 29 artifacts · coverage 13/13 · claims 4/4 · **PASS**.
- Negative: a collapsible removed from its audit → exit 1 (1 coverage miss);
  an external `https://` reference → exit 1; a fabricated claim → exit 0 + `needs-review`.
- 51 tests green (13 new).

## Remaining

- **Critic cold-test** — `verifier-critic.md` is written but not yet run cold
  against M2/M5 with a fresh subagent (same protocol as the other passes).
- The verifier is not yet reachable from `build-course-map` — it lands with the
  skill wrapping.
