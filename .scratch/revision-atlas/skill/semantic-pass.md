# Semantic checklist pass

Draft the **semantic half** of each leaf's checklist for a revision atlas. You
are an agent with no prior context about this module — read only the files named
here, and rely on nothing else.

## Inputs

- `<DIR>` — the module directory (markdown source).
- `<SPEC>` — a `spec.json` produced by the deterministic pipeline. Its `root` is
  the tree; every node carrying a `checklist` key is a **leaf**. Each leaf has
  `title`, `kind`, `file`, and `line` (the heading line, or `null` for a sidecar
  file whose whole body is the leaf).

## Task

For **every leaf** in `<SPEC>`, read its source and write 2–4 **claims** — the
content that must survive compaction: a definition, mechanism, signature,
decision, or verdict as the source states it.

A leaf owns: for a README section, from its `line` to the next heading of equal
or higher rank; for a sidecar (`line` is `null`), the whole file.

## Rules — "every must-survive idea is captured"

- Ground every claim in the source: each must trace to a paragraph or line. No
  invention, no outside knowledge, no editorializing.
- 2–4 claims per leaf; prefer fewer, denser claims over many thin ones.
- Paraphrase, don't transcribe — each claim ≤ ~25 words and never a source sentence copied verbatim; do not drop a load-bearing idea.
- A leaf with nothing worth claiming → an empty list (that is fine, not a gap).
- Only ADD claims — never change the tree, the kinds, or the mechanical seed.

## Output

Return exactly one JSON object mapping each leaf's **exact `title`** (copied
verbatim from `<SPEC>`) to an array of claim strings. No prose, no commentary,
no code fence.
