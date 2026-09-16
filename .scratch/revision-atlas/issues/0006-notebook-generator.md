# 0006 — Notebook generator

- **Blocked by:** 0003, 0005
- **Blocks:** 0007
- **Status:** done — generator, flip, assets, ruled-page geometry, last-spread parity and
  responsive sizing all closed out. Pan/zoom moved to [0014](0014-pan-zoom-on-the-diagram-page.md);
  the reveal-clipping defect stays open in [0010](0010-reveal-clips-on-the-page.md).

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

## Closed out

- **Page margin geometry** — done. The ruled-page geometry was researched and
  implemented as ratios of `--page-w`/`--page-h` (25mm margin rule, 30mm top band,
  10mm bottom margin, 7.1mm college ruling), with the title written ON the first
  rule and the red rule running the full page height.
- **Last-spread parity** — done, and the ticket's own wording was half wrong. The
  parity rule is real: the engine's `createSpread()` (`page-flip.browser.js`) shows
  the front cover alone and then pairs from index 1 — `(1,2), (3,4), …` — so the
  back cover only shares a spread when the content count is ODD. But the blank leaf
  must go **first** (a flyleaf inside the front cover), not at the end: appended
  last it takes the back cover's partner slot and the *blank* leaf faces the cover
  instead of the audit. Verified against the engine — 7 pages →
  `[[0], [1,2], [3,4], [5,6]]`, order
  `[cover, flyleaf, Recall, Diagram, Self-test, Source audit, back cover]`, so the
  final spread is `[Source audit | back cover]`.
- **Responsive sizing** — already done, and this item was stale: the page is sized
  from the viewport at load (`fit()`, keeping the paper's 520/680 aspect), and a
  resize handler re-fits and reloads on a material change (>12px). No
  `size: "stretch"` needed.
- ~~**Leaf-id scheme** — currently `leaf-NNN` (pre-order).~~ **Resolved** — the
  directory is now the leaf's unique id (`leaves/<leaf-id>/`, SPEC §13): stable
  across an inserted section, and the same string the map links to and the agent
  passes key by. See [0011](0011-the-map-reaches-the-notebooks.md).

## Moved out (not this ticket's work)

- **Pan/zoom on the diagram page** — a new interaction on a dense inline SVG, so it
  is its own ticket: [0014](0014-pan-zoom-on-the-diagram-page.md).
- **The self-test reveal clips the page** — a notebook defect, tracked and measured
  in [0010](0010-reveal-clips-on-the-page.md), which is still open on a design call.

## Deferred by the author

- **The source page's overfull *feel*** — left as-is deliberately ("no need to take
  care just now"); the page is paginated correctly, it simply reads denser than a
  hand-written leaf.
