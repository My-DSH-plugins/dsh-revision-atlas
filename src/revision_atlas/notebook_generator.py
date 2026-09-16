"""Per-leaf paged notebook generator (ticket 0006, SPEC §9).

Turns a leaf (recall + mermaid diagrams + self-test + source audit) into a
paged flip notebook: StPageFlip (vendored, MIT) for the flip, a ruled-paper
theme, and the Kalam handwriting font — all offline. Shared assets (flip JS,
flip CSS, theme CSS, font) are written once under `mindmaps/assets/` and
referenced by relative URL from each notebook, so they're cached once per module.
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import json
import math
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .extractor import extract
from .leaf_generator import annotate_artifacts
from .mermaid_render import render_leaf_mermaids
from .spec_writer import build_structure, leaf_dir_id

_ASSETS = Path(__file__).resolve().parent / "assets"

# vendored/theme assets copied to mindmaps/assets/ (filename -> subdir)
SHARED_ASSETS = {
    "page-flip.browser.js": "page-flip.browser.js",
    "page-flip.css": "page-flip.css",
    "notebook.css": "notebook.css",
    "kalam.woff2": "kalam.woff2",
}


def _esc(text: str) -> str:
    return _html.escape(text)


_BULLET = re.compile(r"^\s*[-*+]\s+")


def _md_inline(text: str) -> str:
    """Render the inline Markdown a source bullet actually contains.

    The source audit kept its raw lines verbatim, so `- **What it is:** …` was
    printed with the bullet dash and the asterisks showing. Escape first, then
    turn the emphasis markers into real markup — never the other way round.
    """
    t = _esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t, flags=re.S)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


_SOURCE_CHARS_PER_LINE = 42   # Kalam at the ruled size, across the ruled width
_SOURCE_LINES_PER_PAGE = 15   # ruling lines left for body text after the heading


def _chunk_source(items: List[dict]) -> List[List[dict]]:
    """Split the leaf's source items over as many pages as they need.

    The lines-per-page count is a constant of the page's own ratios (ruling,
    margins and type all scale together), so a character budget is enough and it
    holds at any window size. Without this the source ran past the ruling and
    `overflow: hidden` silently dropped whatever did not fit.
    """
    pages: List[List[dict]] = []
    cur: List[dict] = []
    used = 0
    for it in items:
        text = it.get("text", "")
        lines = max(1, math.ceil(len(text) / _SOURCE_CHARS_PER_LINE)) + 1  # + skipped rule
        if cur and used + lines > _SOURCE_LINES_PER_PAGE:
            pages.append(cur)
            cur, used = [], 0
        cur.append(it)
        used += lines
    if cur:
        pages.append(cur)
    return pages or [[]]


def _anchor_html(node: dict) -> str:
    f = node.get("file")
    if not f:
        return ""
    line = node.get("line")
    label = f"{f}:{line}" if line is not None else f"{f} — whole file"
    return f'<div class="anchor">{_esc(label)}</div>'


def _cover_html(node: dict) -> str:
    kind = _esc(node.get("kind", ""))
    # The flex container is an INNER element, never the .page itself: StPageFlip
    # sets display:block on the page element, which silently overrides it.
    return (
        '<div class="cover-body">'
        f"<h1>{_esc(node['title'])}</h1>"
        f'<div class="muted">revision leaf · {kind}</div>'
        f"{_anchor_html(node)}"
        "</div>"
    )


def _back_cover_html(node: dict) -> str:
    return (
        '<div class="cover-body">'
        f"<h1>{_esc(node['title'])}</h1>"
        '<div class="muted">— end of leaf —</div>'
        f"{_anchor_html(node)}"
        "</div>"
    )


def _recall_html(node: dict) -> str:
    bullets = "".join(f"<li>{_esc(b)}</li>" for b in node.get("recall", []))
    return "<h2>Recall</h2><ul>" + bullets + "</ul>"


def _diagram_html(d: dict) -> str:
    return '<h2>Diagram</h2><div class="diagram">' + d["svg"] + "</div>"


def _selftest_html(node: dict) -> str:
    inner = f"<p>{_esc(node['prompt'])}</p>"
    if node.get("reveal"):
        inner += (
            "<details><summary>Reveal answer</summary>"
            f"<p>{_esc(node['reveal'])}</p></details>"
        )
    return "<h2>Self-test</h2>" + inner


def _source_row(item: dict) -> str:
    """One audit line. The surface enumerates every source item kind — bullets,
    collapsibles and mermaid blocks — so the verifier can check coverage against
    it, and a reader can audit the leaf against its source in one place."""
    kind = item.get("kind", "bullet")
    text = item.get("text", "")
    if kind == "details":
        return f'<div class="src-details">[details] {_md_inline(text)}</div>'
    if kind == "mermaid":
        return '<div class="src-mermaid">[diagram] mermaid</div>'
    return f'<div>{_md_inline(_BULLET.sub("", text))}</div>'


def _source_html(items: List[dict], title: str = "Source audit") -> str:
    rows = "".join(_source_row(i) for i in items)
    return f'<h2>{_esc(title)}</h2><div class="source">{rows}</div>'


def _pages(node: dict) -> List[Tuple[str, str, str]]:
    """Return (density, extra-class, inner-html) pages in flip order.

    A notebook opens and closes on its covers: a hard front cover and a hard back
    cover, each shown alone, centred. The content between them is a soft two-page
    spread. Soft content pages keep forward/backward flips mirrored.
    """
    pages: List[Tuple[str, str, str]] = [("hard", "page-cover", _cover_html(node))]
    if node.get("recall"):
        pages.append(("soft", "", _recall_html(node)))
    for d in node.get("diagrams", []):
        if d.get("svg"):
            pages.append(("soft", "page-diagram", _diagram_html(d)))
    if node.get("prompt") or node.get("reveal"):
        pages.append(("soft", "", _selftest_html(node)))
    src = node.get("source", [])
    if src:
        chunks = _chunk_source(src)
        for i, chunk in enumerate(chunks):
            title = "Source audit" if i == 0 else f"Source audit (cont. {i + 1}/{len(chunks)})"
            pages.append(("soft", "", _source_html(chunk, title)))
    pages.append(("hard", "page-cover", _back_cover_html(node)))
    return pages


def _asset_version() -> str:
    """Short content hash of the shared assets.

    Appended to every asset URL so a regenerated notebook can never be served the
    browser's cached copy of an older stylesheet or flip runtime — a bare
    `assets/notebook.css` is cached indefinitely and makes a fix look like it
    didn't land.
    """
    h = hashlib.sha256()
    for src_name in sorted(SHARED_ASSETS):
        h.update((_ASSETS / src_name).read_bytes())
    return h.hexdigest()[:8]


def render_notebook(node: dict, assets_rel: str = "../../../assets") -> str:
    """Render one leaf to a self-contained flip-notebook HTML string."""
    title = _esc(node["title"])
    ver = _asset_version()
    page_divs = []
    for density, extra, inner in _pages(node):
        cls = "page" + (f" {extra}" if extra else "")
        dattr = ' data-density="hard"' if density == "hard" else ""
        page_divs.append(f'<div class="{cls}"{dattr}>{inner}</div>')
    pages = "\n".join(page_divs)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<title>{title} — Revision Atlas notebook</title>
<link rel="stylesheet" href="{assets_rel}/page-flip.css?v={ver}" />
<link rel="stylesheet" href="{assets_rel}/notebook.css?v={ver}" />
</head>
<body>
<div class="stage">
  <div class="book" id="book">
{pages}
  </div>
  <button class="turn turn-prev" id="prevZone" type="button" aria-label="Previous page"></button>
  <button class="turn turn-next" id="nextZone" type="button" aria-label="Next page"></button>
</div>
<script src="{assets_rel}/page-flip.browser.js?v={ver}"></script>
<script>
(() => {{
  const el = document.getElementById('book');
  const stage = document.querySelector('.stage');
  const prevZone = document.getElementById('prevZone');
  const nextZone = document.getElementById('nextZone');

  // --- size the page to the window ----------------------------------------
  // A notebook page keeps a paper's aspect; fit it to whatever window the reader
  // actually has, so the book never overflows and content is never clipped. The
  // ruling's geometry is all ratios of --page-w / --page-h, so it scales with it.
  const RATIO = 520 / 680;
  const fit = () => {{
    const maxH = Math.max(300, window.innerHeight - 32);
    const maxW = Math.max(150, (window.innerWidth - 40) / 2);  // two pages abreast
    let h = Math.min(680, maxH);
    let w = h * RATIO;
    if (w > maxW) {{ w = maxW; h = w / RATIO; }}
    return {{ w: Math.round(w), h: Math.round(h) }};
  }};
  const size = fit();
  const apply = (s) => {{
    const rs = document.documentElement.style;
    rs.setProperty('--page-w', s.w + 'px');
    rs.setProperty('--page-h', s.h + 'px');
    // the cover shift is half the REAL page width, never a literal
    rs.setProperty('--cover-shift-front', (-s.w / 2) + 'px');
    rs.setProperty('--cover-shift-back', (s.w / 2) + 'px');
  }};
  apply(size);

  // A notebook opens and closes on its covers: hard front/back covers shown alone
  // and centred, soft two-page spread in between. Nothing on the page flips on a
  // click — the only turn zones are the margin square at the top-left and its
  // mirror at the top-right (see .turn in notebook.css).
  const pf = new St.PageFlip(el, {{
    width: size.w, height: size.h, showCover: true, usePortrait: false,
    showPageCorners: true, disableFlipByClick: true,
    maxShadowOpacity: 0.35, mobileScrollSupport: false,
  }});
  pf.loadFromHTML(el.querySelectorAll('.page'));
  prevZone.onclick = () => pf.flipPrev();
  nextZone.onclick = () => pf.flipNext();

  // The notebook opens and closes on its covers, each a single CENTRED page.
  // StPageFlip centres the spread footprint, which parks the front cover on the
  // right half and the back cover on the left half — so shift the book by half a
  // page (in the matching direction) while a cover is showing. The turn zone with
  // nothing to turn to is hidden (a cover shows only one page).
  const syncCover = () => {{
    const i = pf.getCurrentPageIndex();
    const last = pf.getPageCount() - 1;
    stage.classList.toggle('at-front', i === 0);
    stage.classList.toggle('at-back', i === last && last > 0);
    prevZone.classList.toggle('is-hidden', i === 0);
    nextZone.classList.toggle('is-hidden', i >= last);
  }};
  pf.on('flip', syncCover);
  syncCover();

  // Re-fit on a material window change. A static notebook has no state worth
  // preserving across a re-layout, so a reload is the honest response.
  let t;
  window.addEventListener('resize', () => {{
    clearTimeout(t);
    t = setTimeout(() => {{
      const s = fit();
      if (Math.abs(s.w - size.w) > 12 || Math.abs(s.h - size.h) > 12) location.reload();
    }}, 250);
  }});

  // StPageFlip's own corner fold fires over a diagonal/5 (~171px) zone at EVERY
  // book corner — far bigger than the page's margin square, and it includes the
  // bottom corners. Confine it: hand the flip engine the pointer only while it is
  // inside a turn square, and park it mid-book the moment the pointer leaves —
  // StPageFlip clears the fold on a point that is not on a corner, so the fold
  // disappears again. Raw moves are held back so its wide zone never sees them.
  const flipEl = el.querySelector('.stf__block') || el;
  const relay = (x, y) => {{
    const ev = new MouseEvent('mousemove', {{ clientX: x, clientY: y, bubbles: true }});
    ev.atlasRelay = true;   // flagged so our own filter lets it through
    flipEl.dispatchEvent(ev);
  }};
  let wasInZone = false;
  document.addEventListener('mousemove', (e) => {{
    if (e.atlasRelay) return;
    e.stopPropagation();
    const t = e.target;
    const inZone = !!(t && t.classList && t.classList.contains('turn'));
    if (inZone) {{
      relay(e.clientX, e.clientY);          // fold follows the pointer inside the square
    }} else if (wasInZone) {{
      const r = el.getBoundingClientRect();  // park mid-book → the fold is cleared
      relay(r.left + r.width / 2, r.top + r.height / 2);
    }}
    wasInZone = inZone;
  }}, true);
}})();
</script>
</body>
</html>
"""


def write_shared_assets(out_root: "str | Path") -> Path:
    """Copy vendored + theme assets into <out_root>/assets/ (idempotent)."""
    assets = Path(out_root) / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name in SHARED_ASSETS.items():
        (assets / dst_name).write_bytes((_ASSETS / src_name).read_bytes())
    return assets


def iter_leaves(node):
    yield node
    for b in (node.get("branches") or {}).values():
        yield from iter_leaves(b)
    for c in node.get("children", []):
        yield from iter_leaves(c)


def generate_all(inv: dict, spec: dict, out_root: str) -> List[Path]:
    """Generate notebooks for every leaf + the shared assets; return the files.

    Also writes the module's `spec.json` next to the notebooks (SPEC §13's derived
    machine contract), so the verifier can read the frozen checklists from the
    artifact tree instead of re-running the pipeline.
    """
    module_slug = Path(inv["root"]).name
    write_shared_assets(out_root)
    module_dir = Path(out_root) / module_slug
    leaves = [n for n in iter_leaves(spec["root"]) if "checklist" in n]
    written: List[Path] = []
    for leaf in leaves:
        # SPEC §13: `leaves/<leaf-id>/` — the id, not a position. Both the map
        # and the notebook resolve the same name, so inserting a section above a
        # leaf cannot silently re-point a link at a different leaf.
        leaf_dir = module_dir / "leaves" / leaf_dir_id(leaf)
        leaf_dir.mkdir(parents=True, exist_ok=True)
        out = leaf_dir / "notebook.html"
        out.write_text(render_notebook(leaf), encoding="utf-8")
        written.append(out)
    (module_dir / "spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return written


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas notebook generator (ticket 0006)")
    ap.add_argument("module_dir")
    ap.add_argument("--semantic", help="JSON: leaf id -> claims")
    ap.add_argument("--recall", help="JSON: leaf id -> {recall,prompt,reveal}")
    ap.add_argument("--mermaid", help="JSON: leaf id -> [mermaid .mmd strings]")
    ap.add_argument("--out-dir", default="mindmaps", help="write mindmaps/ here")
    args = ap.parse_args(argv)

    inv = extract(args.module_dir)
    semantic = _load(args.semantic)
    recall = _load(args.recall)
    mermaid = _load(args.mermaid)
    spec = build_structure(inv, semantic=semantic, recall=recall, mermaid=mermaid)["spec"]
    annotate_artifacts(inv, spec["root"])
    render_leaf_mermaids(inv, spec["root"])
    written = generate_all(inv, spec, args.out_dir)
    print(f"wrote {len(written)} notebooks + assets under {args.out_dir}")
    return 0


def _load(path: "Optional[str]"):
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    raise SystemExit(main())
