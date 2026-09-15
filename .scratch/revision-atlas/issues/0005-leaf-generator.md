# 0005 — Leaf generator

- **Blocked by:** 0003
- **Blocks:** 0006, 0007
- **Status:** ready after 0003

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

- The diagram-kind classifier boundary (handdrawn vs mermaid vs none, §15).
