"""Per-leaf paged notebook generator (ticket 0006, SPEC §9).

Turns a leaf (recall + mermaid diagrams + self-test + source audit) into a
paged flip notebook: StPageFlip (vendored, MIT) for the flip, a ruled-paper
theme, and the Kalam handwriting font — all offline. Shared assets (flip JS,
flip CSS, theme CSS, font) are written once under `mindmaps/assets/` and
referenced by relative URL from each notebook, so they're cached once per module.
"""
from __future__ import annotations

import argparse
import html as _html
import json
from pathlib import Path
from typing import List, Optional, Tuple

from .extractor import extract
from .leaf_generator import annotate_artifacts
from .mermaid_render import render_leaf_mermaids
from .spec_writer import build_structure

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


def _anchor_html(node: dict) -> str:
    f = node.get("file")
    if not f:
        return ""
    line = node.get("line")
    label = f"{f}:{line}" if line is not None else f"{f} — whole file"
    return f'<div class="anchor">{_esc(label)}</div>'


def _cover_html(node: dict) -> str:
    kind = _esc(node.get("kind", ""))
    return (
        f"<h1>{_esc(node['title'])}</h1>"
        f'<div class="muted">revision leaf · {kind}</div>'
        f"{_anchor_html(node)}"
    )


def _back_cover_html(node: dict) -> str:
    return (
        f"<h1>{_esc(node['title'])}</h1>"
        '<div class="muted">— end of leaf —</div>'
        f"{_anchor_html(node)}"
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


def _source_html(node: dict) -> str:
    rows = "".join(f"<div>{_esc(b)}</div>" for b in node.get("source", []))
    return '<h2>Source audit</h2><div class="source">' + rows + "</div>"


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
    if node.get("source"):
        pages.append(("soft", "", _source_html(node)))
    pages.append(("hard", "page-cover", _back_cover_html(node)))
    return pages


def render_notebook(node: dict, assets_rel: str = "../../../assets") -> str:
    """Render one leaf to a self-contained flip-notebook HTML string."""
    title = _esc(node["title"])
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
<link rel="stylesheet" href="{assets_rel}/page-flip.css" />
<link rel="stylesheet" href="{assets_rel}/notebook.css" />
</head>
<body>
<div class="stage">
  <div class="book" id="book">
{pages}
  </div>
  <button class="turn turn-prev" id="prevZone" type="button" aria-label="Previous page"></button>
  <button class="turn turn-next" id="nextZone" type="button" aria-label="Next page"></button>
</div>
<script src="{assets_rel}/page-flip.browser.js"></script>
<script>
(() => {{
  const el = document.getElementById('book');
  // A notebook opens and closes on its covers: hard front/back covers shown alone
  // and centred, soft two-page spread in between. Nothing on the page flips on a
  // click — the only turn zones are the margin square at the top-left and its
  // mirror at the top-right (see .turn in notebook.css).
  const pf = new St.PageFlip(el, {{
    width: 520, height: 680, showCover: true, usePortrait: false,
    showPageCorners: true, disableFlipByClick: true,
    maxShadowOpacity: 0.35, mobileScrollSupport: false,
  }});
  pf.loadFromHTML(el.querySelectorAll('.page'));
  document.getElementById('prevZone').onclick = () => pf.flipPrev();
  document.getElementById('nextZone').onclick = () => pf.flipNext();

  // The notebook opens and closes on its covers, each a single CENTRED page.
  // StPageFlip centres the spread footprint, which parks the front cover on the
  // right half and the back cover on the left half — so shift the book by half a
  // page (in the matching direction) while a cover is showing. The turn zone with
  // nothing to turn to is hidden (a cover shows only one page).
  const stage = document.querySelector('.stage');
  const prevZone = document.getElementById('prevZone');
  const nextZone = document.getElementById('nextZone');
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

  // StPageFlip's own corner fold fires over a diagonal/5 (~171px) zone at EVERY
  // book corner — far bigger than the page's margin square, and it includes the
  // bottom corners. Confine it to the square: forward hover that happens inside a
  // turn zone to the flip engine (so the real fold renders there), and hold back
  // every mousemove that happens outside one, so no fold appears anywhere else.
  const flipEl = el.querySelector('.stf__block') || el;
  const relay = (x, y) => flipEl.dispatchEvent(new MouseEvent('mousemove', {{
    clientX: x, clientY: y, bubbles: true,
  }}));
  [prevZone, nextZone].forEach((zone) => {{
    zone.addEventListener('mousemove', (e) => relay(e.clientX, e.clientY));
    zone.addEventListener('mouseleave', () => relay(0, 0));
  }});
  document.addEventListener('mousemove', (e) => {{
    const t = e.target;
    if (!(t && t.classList && t.classList.contains('turn'))) e.stopPropagation();
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


def _iter_leaves(node):
    yield node
    for b in (node.get("branches") or {}).values():
        yield from _iter_leaves(b)
    for c in node.get("children", []):
        yield from _iter_leaves(c)


def generate_all(inv: dict, spec: dict, out_root: str) -> List[Path]:
    """Generate notebooks for every leaf + the shared assets; return the files."""
    module_slug = Path(inv["root"]).name
    write_shared_assets(out_root)
    leaves = [n for n in _iter_leaves(spec["root"]) if "checklist" in n]
    written: List[Path] = []
    for i, leaf in enumerate(leaves):
        leaf_dir = Path(out_root) / module_slug / "leaves" / f"leaf-{i:03d}"
        leaf_dir.mkdir(parents=True, exist_ok=True)
        out = leaf_dir / "notebook.html"
        out.write_text(render_notebook(leaf), encoding="utf-8")
        written.append(out)
    return written


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas notebook generator (ticket 0006)")
    ap.add_argument("module_dir")
    ap.add_argument("--semantic", help="JSON: leaf title -> claims")
    ap.add_argument("--recall", help="JSON: leaf title -> {recall,prompt,reveal}")
    ap.add_argument("--mermaid", help="JSON: leaf title -> [mermaid .mmd strings]")
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
