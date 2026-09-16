# 0005 — Leaf generator

- **Blocked by:** 0003
- **Blocks:** 0006, 0007
- **Status:** in progress — deterministic skeleton done; agentic pass + mermaid render remain

## Goal

Against the frozen checklist, generate per leaf: the recall block (3–5 bullets
≤60 words), one diagram (hand-drawn by default; mermaid when content-driven per
§8), the `prompt`/`reveal`, and the collapsed source audit bullets.

## Acceptance

- exactly one diagram slot per leaf, with its `kind` justified per §8
- mermaid path honours adr/0002 (build-time SVG; top-level `htmlLabels:false`; unique render id)
- hand-drawn art keeps real `<text>` labels + embedded font subset (§8)
- outputs land per §13 directory layout

## Open decision

- ~~The diagram-kind classifier boundary (handdrawn vs mermaid vs none, §15).~~
  **Resolved:** deterministic where mechanical (source mermaid block → `mermaid`;
  `needs-review` residue → `none`; else `handdrawn` default); the agent may
  propose `mermaid` (generate fresh) or `none` during the semantic pass, with a
  one-line justification, Gate-2-gated.

## Done (deterministic skeleton)

- `leaf_generator.annotate_artifacts(inv, root)` adds to every leaf:
  - `diagram` — `{kind, justification[, mmd_line]}`, kind assigned per the rule above;
  - `source` — the raw `- `/`* `/`+ ` bullet lines from the leaf's source range.
- Tested on M2 (all `handdrawn`) and M5 (source-mermaid → `mermaid`, residue →
  `none`, no-mermaid → `handdrawn`); source bullets extracted.

## Remaining (agentic + render)

- Recall block (3–5 bullets ≤60 words), `prompt`/`reveal` — agent pass (like the
  semantic pass), stored in `plan.md`.
- Diagram art: render the source mermaid `.mmd` to SVG (adr/0002 machinery:
  vendored mermaid bundle + headless Chromium), or generate a hand-drawn SVG —
  then inline the SVG into the map.
- Renderer upgrade: the map's leaf shows the artifact (recall + diagram + prompt +
  collapsed source) instead of the checklist placeholder.
