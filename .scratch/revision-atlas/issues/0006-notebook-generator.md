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

- `notebook_generator.render_notebook(node)` → paged flip notebook: hard front
  cover / recall / diagram(s) / self-test (prompt + collapsed reveal) / source
  audit / hard back cover. The covers are hard pages **shown alone**, the content
  between them is a soft **two-page spread**.
- **StPageFlip cover geometry** (measured in headless Chromium, not guessed):
  StPageFlip centres the *spread footprint*, so a closed cover is parked on the
  half it physically occupies — the **front cover on the right** (centre +260px
  right of the viewport centre) and the **back cover on the left** (centre −260px
  left). `notebook.css` therefore shifts the book by half a page while a cover is
  showing: `.at-front { translateX(-260px) }`, `.at-back { translateX(+260px) }`,
  on a 440ms transition so the shift animates as the cover opens or closes.
  Verified: the closed front cover measures centre 700 in a 1400px viewport
  (viewport centre 700), and both transforms compute correctly.
- **Click-to-flip disabled** (`disableFlipByClick: true`); only the two corner
  buttons flip, and the corner with nothing to flip to is hidden (front cover has
  no *prev*, back cover has no *next*).
- `write_shared_assets(out_root)` copies flip JS + CSS, theme CSS (ruled paper +
  Kalam `@font-face`), and the font into `mindmaps/assets/`; notebooks reference
  them by relative URL (cached once, offline).
- `generate_all(inv, spec, out_root)` + `main` CLI produce one notebook per leaf.
- Verified: 38 tests green; headless smoke (StPageFlip initialises, no JS errors)
  and visual QA of the closed cover and the open spread.

## Remaining

- **Page margin geometry** — deliberately absent pending a reference image: a
  horizontal top rule, a vertical left rule, and a vertical right rule framing
  the writing area. The ruled lines currently run edge-to-edge, baseline-aligned.
- **Last-spread parity** — StPageFlip pairs (cover alone) → [2|3] → [4|5] → (last
  alone), so with an even number of content pages the back cover shows alone and
  the source audit is *not* facing it. A blank filler page (as a real book uses)
  would force `[source | back cover]`; decide whether to add it.
- **Responsive sizing** — the flip uses a fixed 520×680; consider `size: "stretch"`.
- **Pan/zoom on the diagram page** — inline mermaid SVG is static.
- ~~**Leaf-id scheme** — currently `leaf-NNN` (pre-order).~~ **Resolved** — the
  directory is now the leaf's unique id (`leaves/<leaf-id>/`, SPEC §13): stable
  across an inserted section, and the same string the map links to and the agent
  passes key by. See [0011](0011-the-map-reaches-the-notebooks.md).
