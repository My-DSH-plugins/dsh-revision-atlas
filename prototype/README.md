# mindmap-demo (prototype)

A **throwaway prototype** that proved the "module -> h2 -> h3 -> leaf with a
diagram" navigation idea — online and offline. It was built against ML-Engineer's
`modules/05-data-engineering-2/README.md` shape (one dummy root level added; for
real modules the module `#` heading would BE the root), then relocated here:
course content stays in the course repo, and this prototype belongs to the atlas.

## Files

| File | What it is |
|---|---|
| `demo.md` | Human-readable source. Markdown headings = the tree; a list item that is only an image becomes a diagram node at the leaf. |
| `images/*.svg` | Dummy UML-style diagrams (stand-ins for real Mermaid/UML renders). |
| `demo-map.html` | **The interactive map — one self-contained file that works with ZERO internet** (viewer code + all diagrams are baked in). |
| `build.sh` | Regenerates `demo-map.html` from `demo.md`. |
| `build-offline.mjs` | The build logic (see "Why it works offline" below). |

## How the content maps to the tree

- `## M5 — …` -> a module branch
- `### Drift at ingestion …` -> an H2 section
- `#### Volume and arrival rate` -> an H3 subsection
- `##### Stage A — ingestion gate` -> a leaf "stage"
- bullets under it -> children of the stage; the image-only list item -> the diagram node

Navigation chain: **M5 -> Drift at ingestion -> Volume and arrival rate ->
Stage A** -> diagram.

## Why it works offline

`demo-map.html` is fully self-contained:

- the viewer (d3 + markmap + toolbar) and all CSS are **inlined** into the file,
- the diagram SVGs are embedded as base64 **data: URIs** directly in the map's
  data tree.

One subtlety: markmap's Markdown parser refuses `data:` image URLs, so the
build (`build-offline.mjs`) first transforms `demo.md` into the markmap tree,
then rewrites every `<img src>` in the tree to a data: URI — the file has no
`<script src>`, `<link>`, or `<img src="http…">` left in it at all. The same
file therefore also works when hosted anywhere (GitHub Pages, htmlpreview, …).

Regenerate after editing `demo.md` or `images/`:

```bash
bash prototype/build.sh   # from the repo root; needs node + internet once
```

## Viewing it

`demo-map.html` is self-contained, so the easiest path needs no server:

**Open the file directly** — clone/download the repo, then open
`prototype/demo-map.html` in a browser (on a phone, open it with Chrome).

**On a phone, offline:**

1. GitHub -> repo -> `prototype/demo-map.html` -> **⋮ -> Download** (saves the raw file).
2. In Files/Downloads, tap the file -> **open with Chrome**. (If asked, always pick
   Chrome, not a text/HTML-code viewer.)
3. Verify: turn on airplane mode, open it again — it still works.

**Online preview, no setup:**
`https://htmlpreview.github.io/?https://github.com/My-DSH-plugins/dsh-revision-atlas/blob/main/prototype/demo-map.html`

**GitHub Pages (optional):** if you enable Pages on this repo, it serves at
`https://my-dsh-plugins.github.io/dsh-revision-atlas/prototype/demo-map.html`.

Gestures: **drag** = pan, **pinch** = zoom, **tap a circle** = expand/collapse;
a floating toolbar (bottom-right) has +/−/fit controls.
