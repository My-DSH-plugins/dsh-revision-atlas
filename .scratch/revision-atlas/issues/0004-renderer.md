# 0004 — Renderer (module map)

- **Blocked by:** 0002
- **Blocks:** 0007
- **Status:** done

## Notes

- `renderer.py`: `build_markmap_tree(spec)` + `render_map(spec)` + CLI
  (`--semantic` / `--out-dir`). Consumes the spec tree (never the markdown), so
  the spec — not markmap — is the source of truth (§10 seam).
- Vendored the markmap runtime into `src/revision_atlas/assets/`
  (d3@7.9.0, markmap-view@0.18.12, markmap-toolbar@0.18.12) — the renderer is
  fully offline, no npm at render time.
- Every node renders its title, kind badge, and a source anchor (link to
  `file#id` / `file:line`); leaf checklist items render as child nodes.
- Verified: headless render of M2 shows 14 markmap nodes + root/section titles
  in the DOM; 354 KB self-contained `index.html`, 0 external loads.
- Deferred to 0005: diagrams are not yet inlined (no data URIs); leaf content
  (recall block, notebook link) upgrades the checklist nodes later.

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
