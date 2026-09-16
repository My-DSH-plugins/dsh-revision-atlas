# 0006 — Notebook generator

- **Blocked by:** 0003, 0005
- **Blocks:** 0007
- **Status:** in progress — core generator + flip + assets done; responsive sizing + leaf-id scheme remain

## Goal

Per-leaf paged notebook with a flip interaction and shared assets (vendored
handwriting font + template + flip JS) per §9. Vendored look, no runtime skill
coupling.

## Acceptance

- notebook has N pages sized by the checklist; flip works offline and on touch
- pages are HTML fragments with real text (the verifier can parse them)
- shared assets are cached once per module

## Open decision

- ~~Flip implementation: StPageFlip vs hand-rolled CSS 3D.~~ **Resolved: StPageFlip**
  (npm `page-flip` 2.0.7). Verified: MIT license, no dependencies, 863★, not
  archived, last pushed 2024-01. It is the "mermaid of page-flip" — hand-rolling
  curl physics is exactly the rabbit hole adr/0005 warned against. Vendored
  browser bundle + CSS + Kalam font under `src/revision_atlas/assets/`.

## Done

- `notebook_generator.render_notebook(node)` → paged flip notebook: cover /
  recall / diagram(s) / self-test (prompt + collapsed reveal) / source audit /
  back cover. Hard covers via `data-density="hard"`, `showCover: true`.
- `write_shared_assets(out_root)` copies flip JS + CSS, theme CSS (ruled paper +
  Kalam `@font-face`), and the font into `mindmaps/assets/`; notebooks reference
  them by relative URL (cached once, offline).
- `generate_all(inv, spec, out_root)` + `main` CLI (`--semantic/--recall/--mermaid/
  --out-dir`) produce one notebook per leaf (`leaf-NNN` ids).
- Verified: 38 tests green (5 new notebook tests); headless-Chromium smoke shows
  StPageFlip initializes with no JS errors (injects `stf__parent`/`stf__block`/
  `stf__item` + a canvas, 6 pages) and the mermaid SVG + Kalam pages render.

## Remaining

- **Responsive sizing** — the flip uses a fixed 520×680; make it fill the viewport
  (`size: "stretch"` / `autoSize`) for phone.
- **Pan/zoom on the diagram page** — inline mermaid SVG is static; add the small
  pan/zoom wrapper (shared with the map's notebook layer).
- **Leaf-id scheme** — currently `leaf-NNN` (pre-order); decide a stable,
  content-hash-based id for `refresh-stale-leaves` to match (§12).
