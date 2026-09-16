# 0005 — Leaf generator

- **Blocked by:** 0003
- **Blocks:** 0006, 0007
- **Status:** in progress — recall/prompt/reveal pass + renderer upgrade done; agent-authored mermaid + pan/zoom remain

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
- **Renderer upgrade** — `render_map` shows the leaf artifact: recall bullets,
  mermaid SVG inlined as base64 data-URI (image-only node), self-test
  (prompt + collapsed reveal), collapsed source audit. M5 map self-contained, 6
  mermaid data-URIs inlined.

## Remaining

- **Agent-authored mermaid pass** — the instruction + merge for the agent to write
  a `.mmd` diagram (`flowchart`/`mindmap`) for structure-bearing leaves, Gate-2-gated,
  stored in `plan.md` (like recall/prompt/reveal). This replaces the removed
  hand-drawn "diagram content pass".
- **Pan/zoom wiring** — the notebook (0006) adds a small pan/zoom script over the
  static mermaid SVG; the map's `<img>` path already shows the diagram.
- **Size note**: inlining source audit + mermaid in the Layer-1 map pushes M5 to
  ~886 KB. Revisit if the single-file budget matters (e.g. truncate source to a
  count in the map, full bullets in the notebook).
