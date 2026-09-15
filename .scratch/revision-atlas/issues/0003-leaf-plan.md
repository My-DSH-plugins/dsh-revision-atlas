# 0003 — Leaf plan + Gate 2

- **Blocked by:** 0002
- **Blocks:** 0005, 0006
- **Status:** ready after 0002

## Goal

Draft per-leaf **checklists** (the bullets under each leaf heading in `plan.md`):
every sub-heading, collapsible, claim, and diagram that must survive. Gate 2 is
human approval of these checklists. `spec.yml` gains the checklist fields from
the approved plan.

## Acceptance

- every leaf has a non-empty checklist; a leaf without one is `needs-review`
- each checklist item maps to real source content (grounding, not invention)
- `spec.yml` checklist fields are derived from the approved `plan.md`

## Out of scope

- Generating recall/diagram/prompt/reveal (0005)

## Open decision

- `prompt`/`reveal` placement: written back into `plan.md` post-generation (SPEC §8) — confirm.
