# 0002 — Structure plan + Gate 1

- **Blocked by:** 0001
- **Blocks:** 0003, 0004
- **Status:** done

## Goal

From the inventory, draft the **structure plan** in `plan.md`: the full heading
tree, a `Coverage:` summary line, and proposed `· kind:` / `· diagram:`
annotations. Then derive the structure fields of `spec.json` (ids, `sources`,
`evidence`, canonical-source dedupe).

## Acceptance

- `plan.md` opens with a `Coverage:` line and lists every heading + linked file
- Gate 1 is a human approval of this structure (no generation happens before it)
- `spec.json` (structure part) is derived, never hand-written

## Out of scope

- Per-leaf checklists (0003)
- Any artifact generation (0004+)

## Open decision

- Gate UX: one combined approval for structure+leaf, or two separate (with 0003, §15).
- `· diagram:` annotations are deferred — the diagram-kind classifier is §15's open
  question; 0002 emits `· kind:` only.

## Notes (implementation)

- The derived machine contract is emitted as `spec.json` (stdlib `json`, no
  PyYAML dependency) rather than `spec.json`; trivially switchable if a YAML
  dependency is added.
- Typed edges carry `evidence` (`{file, line}` = the README line that cited the
  sidecar); unlinked nodes (framework-matrix, needs-review) have none.
