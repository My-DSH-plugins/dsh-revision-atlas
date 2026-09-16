# Mermaid diagram pass

Author the **mermaid diagram(s)** for a revision atlas leaf. You are an agent
with no prior context about this module — read only the files named here, and
rely on nothing else.

## Inputs

- `<DIR>` — the module directory (markdown source).
- `<SPEC>` — a `spec.json` produced by the deterministic pipeline. Its `root` is
  the tree; every node carrying a `checklist` key is a **leaf**. Each leaf has
  `title`, `kind`, `file`, and `line` (the heading line, or `null` for a sidecar
  whose whole body is the leaf). The `checklist` is already frozen: use it to
  know the load-bearing content, but do not edit it.

## Task

For **leaves whose content has structure worth drawing**, write one (rarely two)
mermaid diagram(s) as raw `.mmd` source. For every other leaf, write nothing —
an empty list is the correct, expected answer.

A diagram earns its place when the leaf is a **decision procedure, state
machine, multi-branch sequence, taxonomy, or a mental model whose shape the
learner should hold in memory**. Prose paragraphs and plain lists usually do
*not* need one.

## Rules — "sparse, grounded, valid"

- **Ground every node and edge in the source**: each box and arrow traces to the
  leaf's own range. No invention, no outside knowledge, no editorializing.
- **1–5 nodes.** A memory-hook diagram is sparse; if you need more than ~5 nodes,
  the leaf is probably several diagrams or none.
- **Pick the right kind**: `flowchart` (or `flowchart TD/LR`) for decision /
  sequence / state; `mindmap` for taxonomy / "how the pieces fit" / mental
  model. Never draw the same structure twice.
- **Valid mermaid syntax** — it will be rendered at build time and fails loudly.
- **Labels short**: 1–5 words per node; no full sentences.
- Only produce diagrams — never change the tree, the kinds, or the checklist.

## Output

Return exactly one JSON object mapping each leaf's **exact `title`** (copied
verbatim from `<SPEC>`) to an array of mermaid `.mmd` strings — e.g.
`{"1. Hallucination & confabulation": ["flowchart TD\n  A[Plausibility] --> B[Wrong]"]}`.
Leaves with no diagram may be omitted. No prose, no commentary, no code fence
around the whole JSON (the `.mmd` strings are inside it).
