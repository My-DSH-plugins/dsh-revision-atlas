# 0001 — Extractor

- **Blocked by:** —
- **Blocks:** 0002
- **Status:** done

## Goal

Deterministically scan one module directory and emit a normalized inventory:
every markdown file classified `classified` / `ignored` / `needs-review`, its
headings (rank + text + line), relative `.md` links (target + line), mermaid
fences (line), and `<details>` collapsibles as `{line, summary}` — the label
captured verbatim, the body addressed by position and never copied.

## Acceptance (the "red" test)

Run against both fixture modules (`ML-Engineer/modules/05-data-engineering-2`
and `GenAI_notes/Harness Engineering/modules/02-model-failure-science`):

- every `.md` is accounted for exactly once; an unclassified file **fails** the run
- M5 reports 9 H2 / 4 H3 / 6 H4 / 59 collapsibles / 6 mermaid blocks
- M2 reports the 5 for/against sidecars, the aggregator, and the 5 task-state files
- `handwrittenNotes/`, `scratch/`, `.git`, `node_modules` are ignored by an explicit rule

## Out of scope

- No LLM. Deterministic filename/structure classification is **in scope**; the
  residue is flagged `needs_review` (typed by 0002 / the human).
- No `plan.md` / `spec.json` emission (that's 0002). The §7 content-signal ladder
  and node-graph assembly (debate-for + debate-against → one `debate-pair` node,
  `framework-domain`×N + `aggregator` → one `framework-matrix` node) are 0002.

## Decision

- Language: **Python**, stdlib only. Code in `src/revision_atlas/extractor.py`,
  tests in `tests/test_extractor.py`.
  Run: `PYTHONPATH=src python3 -m unittest discover -s tests`.
