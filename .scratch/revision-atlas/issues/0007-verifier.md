# 0007 — Verifier + coverage report

- **Blocked by:** 0004, 0005, 0006
- **Blocks:** —
- **Status:** ready after 0004+0005+0006

## Goal

Two-axis verification (SPEC §6.4): **coverage** (checklist slugs present,
deterministic) + **adherence** (deterministic grounding + LLM critic), and the
coverage report (SPEC §14).

## Acceptance

- a coverage miss is a **failure**, not a warning
- drift flags from the critic and grounding misses → `needs-review`
- report prints inventory / coverage / adherence / anchors / offline-purity / `needs-review`
- adherence reads the text artifact (HTML + SVG labels), never a raster — no VLM

## Open decision

- `needs-review`: block vs annotate in v1 (§15).
