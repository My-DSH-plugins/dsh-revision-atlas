# 0002 — Structure plan + Gate 1

- **Blocked by:** 0001
- **Blocks:** 0003, 0004
- **Status:** ready after 0001

## Goal

From the inventory, draft the **structure plan** in `plan.md`: the full heading
tree, a `Coverage:` summary line, and proposed `· kind:` / `· diagram:`
annotations. Then derive the structure fields of `spec.yml` (ids, `sources`,
`evidence`, canonical-source dedupe).

## Acceptance

- `plan.md` opens with a `Coverage:` line and lists every heading + linked file
- Gate 1 is a human approval of this structure (no generation happens before it)
- `spec.yml` (structure part) is derived, never hand-written

## Out of scope

- Per-leaf checklists (0003)
- Any artifact generation (0004+)

## Open decision

- Gate UX: one combined approval for structure+leaf, or two separate (with 0003, §15).
