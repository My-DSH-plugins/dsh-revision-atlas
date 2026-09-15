# 0004 — Renderer (module map)

- **Blocked by:** 0002
- **Blocks:** 0007
- **Status:** ready after 0002

## Goal

Render the frozen structure to a self-contained module map (markmap), inlining
diagrams as data URIs. Reuse the proven prototype mechanics (`prototype/build-offline.mjs`
pattern and the SPEC §10 markmap workarounds).

## Acceptance

- module map opens offline; every node links to its source anchor
- passes offline-purity check (no external load-bearing refs)
- the renderer is behind a seam — the plan/spec is renderer-agnostic

## Out of scope

- Leaf content generation (0005), notebooks (0006)
