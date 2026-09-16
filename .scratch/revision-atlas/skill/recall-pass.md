# Recall & self-test pass

Author each leaf's **recall block** and **self-test (`prompt`/`reveal`)** for a
revision atlas. You are an agent with no prior context about this module — read
only the files named here, and rely on nothing else.

## Inputs

- `<DIR>` — the module directory (markdown source).
- `<SPEC>` — a `spec.json` produced by the deterministic pipeline. Its `root` is
  the tree; every node carrying a `checklist` key is a **leaf**. Each leaf has
  `id` (unique — **this is your map key**), `title` (human-readable, may repeat),
  `kind`, `file`, and `line` (the heading line, or `null` for a sidecar whose whole
  body is the leaf). The `checklist` is already frozen (approved): use it to know
  what must survive, but do not edit it.

## Task

For **every leaf** in `<SPEC>`, read its source and write three things:

1. **`recall`** — 3–5 bullets (≤60 words total) that let a learner reconstruct
   the leaf from memory. These are the *hooks*: the definitions, mechanisms,
   signatures, decisions, or verdicts that, once remembered, reproduce the rest.
2. **`prompt`** — one self-test question that forces **retrieval** of the key
   idea(s), not recognition. No yes/no, no fill-one-blank; ask for the mechanism,
   the signature, or the "how would you tell X from Y" that the leaf is about.
3. **`reveal`** — the model answer: the compact structure the learner should have
   reproduced (the bullets/diagram skeleton the `recall` block maps onto).

A leaf owns: for a README section, from its `line` to the next heading of equal
or higher rank; for a sidecar (`line` is `null`), the whole file.

## Rules — "reproducible, not readable"

- Ground everything in the source: each recall bullet and the reveal must trace
  to the leaf's own range. No invention, no outside knowledge, no editorializing.
- Paraphrase, don't transcribe — no bullet is a source sentence copied verbatim;
  do not drop a load-bearing idea.
- `recall` bullets are dense, not chatty: ≤ ~15 words each, 3–5 total.
- `prompt` targets the leaf's *hardest* idea — the one a learner most often gets
  wrong or fudges. `reveal` is the structure that answers it, not a full essay.
- A leaf with nothing worth recalling → `recall: []`, `prompt: ""`, `reveal: ""`
  (that is fine, not a gap).
- Only produce recall/prompt/reveal — never change the tree, the kinds, or the
  checklist.

## Output

Return exactly one JSON object mapping each leaf's **`id`** (copied verbatim
from `<SPEC>` — not the `title`, which may repeat) to
`{"recall": [...], "prompt": "...", "reveal": "..."}`. No prose, no commentary,
no code fence.
