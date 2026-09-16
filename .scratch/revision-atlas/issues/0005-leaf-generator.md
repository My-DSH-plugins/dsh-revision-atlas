# 0005 — Leaf generator

- **Blocked by:** 0003
- **Blocks:** 0006, 0007
- **Status:** in progress — deterministic skeleton + mermaid render + recall/prompt/reveal + agent-authored mermaid + renderer upgrade done; pan/zoom (0006) remains

## Goal

Against the frozen checklist, generate per leaf: the recall block (3–5 bullets
≤60 words), a list of **mermaid** diagrams (adr/0005 — the hand-drawn sketch path
was removed), the `prompt`/`reveal`, and the collapsed source audit bullets.

## Acceptance

- a **list** of diagram slots per leaf, each `kind: mermaid` (adr/0005)
- mermaid path honours adr/0002 (build-time SVG; top-level `htmlLabels:false`; unique render id)
- diagrams are static SVG inlined into the HTML; the notebook adds a small pan/zoom script
- outputs land per §13 directory layout

## Open decision

- ~~Diagram-kind classifier (handdrawn vs mermaid vs none).~~ **Reversed by adr/0005:**
  mermaid is the only diagram kind. The classifier extracts source mermaid blocks
  and defaults everything else to `[]`; the agent may *propose* a mermaid
  diagram (`flowchart`/`mindmap`), Gate-2-gated. `adr/0003` and `adr/0004` are
  superseded (kept, status flipped, not deleted).

## Done

- **Deterministic skeleton** — `leaf_generator.annotate_artifacts(inv, root)` adds
  to every leaf: `diagrams` (list; source-mermaid → `mermaid` entries, else `[]`)
  and `source` (raw bullet lines). Tested on M2 (all `[]`) and M5 (source-mermaid →
  array of `mermaid`, residue/no-mermaid → `[]`).
- **Mermaid render** — `mermaid_render.render_leaf_mermaids(inv, root)` renders
  every mermaid entry to SVG; M5 smoke yields 6 SVGs.
- **Recall / prompt / reveal pass** — instruction `recall-pass.md`; `spec_writer
  --recall` merges recall/prompt/reveal and renders them in `plan.md`.
- **Agent-authored mermaid pass** — instruction `mermaid-pass.md`; `spec_writer
  --mermaid` merges `.mmd` strings and renders them as fenced blocks in `plan.md`
  (Gate-2). `leaf_generator` appends them to `diagrams`; `mermaid_render` renders
  them via the `mmd` (direct source) path alongside source `mmd_line` blocks.
  Smoke: a `flowchart` and a `mindmap` both render to SVG.
- **Renderer upgrade** — `render_map` shows the leaf artifact: recall bullets,
  mermaid SVG inlined as base64 data-URI (image-only node), self-test
  (prompt + collapsed reveal), collapsed source audit. M5 map self-contained, 6
  mermaid data-URIs inlined.

## Remaining

- **Pan/zoom wiring** — the notebook (0006) adds a small pan/zoom script over the
  static mermaid SVG; the map's `<img>` path already shows the diagram.
- **Size note**: inlining source audit + mermaid in the Layer-1 map pushes M5 to
  ~886 KB. Revisit if the single-file budget matters (e.g. truncate source to a
  count in the map, full bullets in the notebook).
