# 0005 — Leaf generator

- **Blocked by:** 0003
- **Blocks:** 0006, 0007
- **Status:** in progress — sketch renderer + recall/prompt/reveal + renderer upgrade done; diagram content pass + wiring remain

## Goal

Against the frozen checklist, generate per leaf: the recall block (3–5 bullets
≤60 words), a list of diagrams (hand-drawn by default; mermaid when content-driven
per §8 / adr/0003), the `prompt`/`reveal`, and the collapsed source audit bullets.

## Acceptance

- a **list** of diagram slots per leaf, each `kind` justified per §8 / adr/0003
- mermaid path honours adr/0002 (build-time SVG; top-level `htmlLabels:false`; unique render id)
- hand-drawn art keeps real `<text>` labels + embedded font subset (§8)
- outputs land per §13 directory layout

## Open decision

- ~~The diagram-kind classifier boundary (handdrawn vs mermaid vs none, §15).~~
  **Resolved** and recorded as `adr/0003`: deterministic where mechanical
  (source mermaid block → `mermaid`; `needs-review` residue → `[]`; else
  `handdrawn`); the agent may propose `mermaid`/`none` during the semantic pass,
  Gate-2-gated. A leaf holds an **array** of diagrams.

## Done

- **Deterministic skeleton** — `leaf_generator.annotate_artifacts(inv, root)` adds
  to every leaf: `diagrams` (list; `{kind, justification[, mmd_line]}`, kind per
  adr/0003) and `source` (the raw `- `/`* `/`+ ` bullet lines from the leaf's range).
  Tested on M2 (all `handdrawn`) and M5 (source-mermaid → array of `mermaid`,
  residue → `[]`, no-mermaid → `handdrawn`); M5's "Deriving the baseline and
  thresholds." H4 holds 4 mermaid entries.
- **Mermaid render** — `mermaid_render.render_leaf_mermaids(inv, root)` renders
  every mermaid entry's source to SVG; M5 smoke yields 6 SVGs (not 3).
- **Recall / prompt / reveal pass** — instruction `.scratch/revision-atlas/skill/
  recall-pass.md` (cold-testable); `spec_writer` accepts `--recall` and renders
  recall/prompt/reveal in `plan.md` (Gate-2 review surface).
- **Renderer upgrade** — `render_map` now shows the leaf artifact instead of the
  checklist placeholder: recall bullets, diagrams (mermaid SVG inlined as base64
  data-URI in an image-only node; hand-drawn shown as "pending" until art lands),
  self-test (`prompt` + collapsed `reveal`), and the collapsed source audit. M5
  map is self-contained (no `<script src`/`<link`), 6 mermaid data-URIs inlined.

- **Hand-drawn sketch renderer** — `sketch.render_svg(spec)` (adr/0004): the agent
  supplies topology only (`{template: flow|tree|cycle|comparison, nodes:[{label,
  shape}]}`); deterministic code lays it out and renders a hand-drawn SVG with
  real `<text>` labels, seeded rough strokes, and the layout invariant (no
  overlap, label fit, orientation, alignment) unit-tested.

## Remaining

- **Diagram content pass** — the agent authoring pass that turns a leaf's frozen
  checklist into a diagram spec (`template` + ordered `nodes` with 1–5-word
  labels + `shape`), Gate-2-gated, stored in `plan.md` (like recall/prompt/reveal).
  This is the "which concepts, which order, which shape" half — the sketch
  renderer already owns the geometry.
- **Wire hand-drawn SVG into the leaf** — for each `handdrawn` slot, run
  `sketch.render_svg` and attach the SVG (as mermaid does), then inline into the
  map/notebook. Needs the diagram content pass first (no spec, no SVG).
- **Font subset** — embed the handwriting font as a base64 `@font-face` subset
  (build-time curl, like the mermaid bundle); until then the font-family stack
  in `sketch.py` is a stand-in and the jitter carries the hand-drawn feel.
- **Size note**: inlining the source audit + mermaid in the Layer-1 map pushes M5
  to ~886 KB (vs ~350 KB for the checklist-only map). Acceptable for now; revisit
  if the "one self-contained HTML" budget matters (e.g. truncate source to a
  count in the map, full bullets in the notebook).
