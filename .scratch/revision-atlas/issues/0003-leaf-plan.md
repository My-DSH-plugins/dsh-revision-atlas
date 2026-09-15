# 0003 — Leaf plan + Gate 2

- **Blocked by:** 0002
- **Blocks:** 0005, 0006
- **Status:** in progress — deterministic seed done; semantic drafting is the agentic half

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

## Notes

- **Gate UX: two separate gates (decided).**
- **Deterministic seed is done**: `spec_writer.py` annotates every leaf with a
  `checklist` of its grounded mechanical items (collapsibles with verbatim
  `<summary>`, mermaid blocks), captured by line range. Leaf-closure invariant
  tested: every collapsible/mermaid lands in exactly one leaf (0 orphan, 0
  double-count) on both fixtures.
- **Remaining (agentic, not deterministic code)**: the semantic checklist items —
  each leaf's key claims/definitions — are drafted by the agent reading the
  source (the skill's runtime), then Gate 2 approves the combined list. This is
  where `needs-review` leaves like `code/README.md` get human-typed.
