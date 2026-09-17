# Semantic compaction pass

Draft the **compacted narrative** of each leaf for a revision atlas. You are an
agent with no prior context about this module — read only the files named here,
and rely on nothing else.

## Inputs

- `<DIR>` — the module directory (markdown source).
- `<SPEC>` — a `spec.json` produced by the deterministic pipeline. Its `root` is
  the tree; every node carrying a `checklist` key is a **leaf**. Each leaf has
  `id` (unique — **this is your map key**), `title` (human-readable, may repeat),
  `kind`, `file`, `line`, and a `checklist` — the deterministic enumeration of its
  content **blocks** in document order. Each block has `kind` (`prose` / `bullet` /
  `details` / `mermaid`) and `text` (the verbatim source).

## Task

For **every leaf** in `<SPEC>`, rewrite each block's `text` more densely — the
compacted narrative. **Keep the list the same length and order as the `checklist`:
one output string per block, in the same order.** Never merge two blocks, never
drop one, never reorder.

A `prose` block is a paragraph; a `bullet` is one list item; a `details` is a
collapsible (rewrite its summary); a `mermaid` is a diagram (return a short label
for what it draws — e.g. "flowchart: X").

## Rules — "faithful in meaning and order, never verbatim"

- One output string per checklist block, in the same order — the output array
  must be the same length as the leaf's `checklist`.
- Paraphrase each block's text: denser, ≤ ~25 words, never a source sentence
  copied verbatim. A block that is already tight may return nearly as-is.
- Ground every rewrite in its block — no invention, no outside knowledge, no
  editorializing.
- Only ADD your rewrite — never change the tree, the kinds, the lines, or the
  block list.

## Output

Return exactly one JSON object mapping each leaf's **`id`** (copied verbatim from
`<SPEC>` — not the `title`, which may repeat) to an array of compacted strings,
one per checklist block, in the same order. No prose, no commentary, no code fence.
