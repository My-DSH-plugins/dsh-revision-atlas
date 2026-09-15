# Mermaid is rendered to SVG at build time, not in the viewer

---
Status: proposed
---

Mermaid may be absent (Harness M2 has none) or present (ML-Engineer M5 has six
flowchart blocks), and the atlas must stay offline and verifiable either way. We
decided rendered SVG is produced once at build time — a pinned mermaid bundle plus
the diagram sources loaded into a headless Chromium, then the DOM dumped — rather
than shipping mermaid to the phone: M5's six diagrams cost 295 KB of SVG (38 KB
gzipped) against 3.4 MB of viewer JavaScript inlined into every map, and offline
single-file maps cannot rely on gzip. Labels stay real `<text>`/`<tspan>` markup,
so the coverage verifier can assert a diagram's labels exactly as it asserts
prose, and the SVG carries no external references and no embedded fonts.

## Evidence — ML-Engineer M5, mermaid 11.17.2, 6 flowchart blocks

| Measurement | Result |
|---|---|
| Rendering wall time (all 6, one browser run) | 1454 ms |
| SVG payload | 295 KB raw · 38 KB gzip · 394 KB as base64 data-URI |
| Per-diagram range | 26 KB – 118 KB |
| Label portability | 0 `foreignObject` · 45–292 non-empty `<tspan>` per diagram |
| External references | none (XML namespaces only) |
| Font dependency | `"trebuchet ms",verdana,arial,sans-serif` in an internal `<style>` — generic fallback |
| Rejected client-side alternative | `mermaid.min.js` = 3488 KB raw / 956 KB gzip, inlined per map file |

## Build-time mechanics the implementation must honour

- **Renderer**: the Chromium headless shell already on this machine
  (`~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell`),
  driven with `--dump-dom --virtual-time-budget=20000`. No Puppeteer, no 150 MB
  download. `mermaid-cli` stays an option for machines without a browser
  (`PUPPETEER_EXECUTABLE_PATH`); an online render service is rejected — it breaks
  offline regeneration and ships coursework to a third party.
- **`htmlLabels: false` must be top level.** Nested under `flowchart` it is
  ignored and labels return as HTML in `foreignObject`, which is not portable when
  an SVG is used as an `<img>`.
- **A unique render id per diagram.** Mermaid scopes its `<style>` block by that id
  (`#d0 …`), so a reused id makes styles collide between diagrams.
- **The dump contains two helper SVGs under 1 KB** alongside the real diagrams; the
  extractor must select by size or container, not "every `<svg>`".
- **Pin the mermaid version and record it with the artifact** — the same source can
  render differently across majors (11.17.2 measured; 12.0.0 is current).

**Consequences**: the build machine needs a browser, but artifacts are committed so
consumers never do; regenerating a diagram requires that browser or a re-render
elsewhere; `.mmd` sources stay in the spec next to their rendered SVG so any
diagram can be re-rendered and re-verified.

## Scope

This ADR governs *how* mermaid is rendered **when a leaf carries one**. Whether a
leaf carries mermaid at all is a per-leaf content decision (SPEC §8): hand-drawn
is the default, mermaid appears only for source-authored blocks or for decision /
state / sequence leaves whose exact branching matters — never two drawings of the
same structure. For v1 the exact branching of generated diagrams is human-reviewed,
not machine-checked.
