# 0001 — Extractor

- **Blocked by:** —
- **Blocks:** 0002
- **Status:** ready

## Goal

Deterministically scan one module directory and emit a normalized inventory:
every markdown file classified `classified` / `ignored` / `needs-review`, its
headings (rank + line), relative `.md` links (with the link's line as evidence),
mermaid blocks, and `<details>` runs.

## Acceptance (the "red" test)

Run against both fixture modules (`ML-Engineer/modules/05-data-engineering-2`
and `GenAI_notes/Harness Engineering/modules/02-model-failure-science`):

- every `.md` is accounted for exactly once; an unclassified file **fails** the run
- M5 reports 9 H2 / 4 H3 / 6 H4 / 59 collapsibles / 6 mermaid blocks
- M2 reports the 5 for/against sidecars, the aggregator, and the 5 task-state files
- `handwrittenNotes/`, `scratch/`, `.git`, `node_modules` are ignored by an explicit rule

## Out of scope

- No LLM. Relationship classification beyond filename/heading rules → `needs-review`
- No `plan.md` / `spec.yml` emission (that's 0002)

## Open decision

- Language: Node (matches the prototype `build-offline.mjs` + the plugin ecosystem). Confirm at implement time.
