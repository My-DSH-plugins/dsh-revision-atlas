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
from .spec_writer import build_structure, leaf_dir_id, owns_content

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


def _cover_nav(map_href: str, back: bool = False) -> str:
    """The way home.

    A notebook is a leaf OF the map, and there was no route back to it: the only
    hrefs a notebook carried were its own stylesheets, so opening one from a
    bookmark, a shared link or a fresh tab left the reader with nothing to click
    and no way to see where the leaf sat. On the front cover so it is the first
    thing offered, and on the back cover so it is where the reader ends up.
    """
    if not map_href:
        return ""
    cls = "cover-nav back" if back else "cover-nav"
    return f'<a class="{cls}" href="{_esc(map_href)}">&larr; course map</a>'


def _cover_html(node: dict, map_href: str = "") -> str:
    kind = _esc(node.get("kind", ""))
    # The flex container is an INNER element, never the .page itself: StPageFlip
    # sets display:block on the page element, which silently overrides it.
    return (
        _cover_nav(map_href)
        + '<div class="cover-body">'
        f"<h1>{_esc(node['title'])}</h1>"
        f'<div class="muted">revision leaf · {kind}</div>'
        f"{_anchor_html(node)}"
        "</div>"
    )


def _back_cover_html(node: dict, map_href: str = "") -> str:
    return (
        '<div class="cover-body">'
        f"<h1>{_esc(node['title'])}</h1>"
        '<div class="muted">— end of leaf —</div>'
        f"{_anchor_html(node)}"
        "</div>"
        + _cover_nav(map_href, back=True)
    )


def _recall_html(node: dict) -> str:
    bullets = "".join(f"<li>{_esc(b)}</li>" for b in node.get("recall", []))
    return "<h2>Recall</h2><ul>" + bullets + "</ul>"


def _diagram_html(d: dict) -> str:
    """The diagram page. The SVG sits in an inner wrapper so pan/zoom is one CSS
    transform on one element, and a muted hint says so — a static diagram of a
    dense flowchart is unreadable at page size and nothing on the page said it
    could be moved (`0014`)."""
    return (
        '<h2>Diagram</h2><div class="diagram">'
        '<div class="diagram-zoom">' + d["svg"] + "</div>"
        "</div>"
        '<div class="diagram-hint">drag to pan · scroll to zoom · double-click to reset</div>'
    )


# The nested sheet's capacity, in nested lines, measured against the shipped CSS
# at the reference page box (520x680) and expressed as lines rather than pixels
# because the sheet's ruling is itself a ratio of the page — so this holds at any
# fitted size. `_NESTED_CAP_1LINE` is the usable height with a one-line prompt;
# every further prompt line costs `_NESTED_PROMPT_COST` of it. Both carry slack:
# an over-full nested page would clip, which is the defect this whole mechanism
# exists to remove (ticket 0010).
_NESTED_CHARS = 56          # characters charged per nested line. Measured against
                            # the shipped CSS by sweeping the constant: 56 fills the
                            # fuller pages to ~86% with nothing overflowing, while 64
                            # overflows every page. `reveal-page`'s `overflow-y: auto`
                            # is the net under this estimate.
_NESTED_CAP_1LINE = 16      # usable nested lines when the prompt is one page line
                            # (measured ~17.2 at 520x680; the ratio holds at every
                            # fitted size, since the sheet's ruling scales too)
_NESTED_PROMPT_COST = 1.7   # nested lines consumed by each further prompt line (measured)
_PROMPT_CHARS = 46          # characters that fit on one PAGE line of the prompt


def _nested_budget(prompt: str) -> int:
    """How many nested lines a page's sheet can hold for this prompt."""
    prompt_lines = max(1, -(-len(prompt) // _PROMPT_CHARS))
    return max(3, int(_NESTED_CAP_1LINE - _NESTED_PROMPT_COST * (prompt_lines - 1)))


def _reveal_line_html(line: str) -> str:
    text = line.strip()
    bullet = text.startswith(("- ", "* "))
    if bullet:
        text = text[2:].strip()
    cls = ' class="reveal-bullet"' if bullet else ""
    return f"<p{cls}>{_esc(text)}</p>"


def _chunk_reveal(reveal: str, prompt: str = "") -> List[List[str]]:
    """Paginate a reveal into nested pages that each fit the sheet.

    The same job `_chunk_source` does for the source audit, and for the same
    reason: the sheet is a fixed piece of paper with `overflow: hidden`, so text
    that does not fit is not merely ugly, it is gone. Each source line is charged
    the nested lines it will wrap onto, and a chunk is closed before it would
    exceed the budget. The charge is fractional rather than a per-line `ceil`: a
    line wrapping to 2.1 lines must cost 2.1, or every line landing just past a
    multiple is billed a whole extra line and the sheet ships two-thirds empty.
    """
    budget = _nested_budget(prompt)
    chunks: List[List[str]] = []
    current: List[str] = []
    used = 0.0
    for line in (l for l in reveal.splitlines() if l.strip()):
        cost = max(1.0, len(line.strip()) / _NESTED_CHARS)
        if current and used + cost > budget:
            chunks.append(current)
            current, used = [], 0.0
        current.append(line)
        used += cost
    if current:
        chunks.append(current)
    return chunks or [[]]


def _selftest_html(node: dict) -> str:
    """The self-test page: the prompt, then the answer behind a ">" disclosure.

    The answer is a nested, paginated sheet rather than free-flowing prose — the
    outer page keeps its one-page budget, and the reveal is conserved whatever its
    length (ticket 0010).
    """
    prompt = node.get("prompt") or ""
    inner = f'<h2>Self-test</h2><div class="selftest-body"><p>{_esc(prompt)}</p>'
    reveal = (node.get("reveal") or "").strip()
    if reveal:
        chunks = _chunk_reveal(reveal, prompt)
        pages = "".join(
            '<div class="reveal-page"%s>%s</div>'
            % (" hidden" if i else "", "".join(_reveal_line_html(l) for l in chunk))
            for i, chunk in enumerate(chunks)
        )
        pager = ""
        if len(chunks) > 1:
            last = len(chunks) - 1
            pager = (
                '<div class="reveal-pager">'
                '<button type="button" data-dir="prev" aria-label="Previous reveal page"'
                ' disabled>&lsaquo; Previous</button>'
                f'<span class="pager-count" aria-live="polite">1 / {len(chunks)}</span>'
                '<button type="button" data-dir="next" aria-label="Next reveal page"'
                f"{' disabled' if last == 0 else ''}>Next &rsaquo;</button>"
                "</div>"
            )
        inner += (
            '<details class="reveal-disclosure"><summary>Reveal answer</summary>'
            f'<div class="reveal-body"><div class="reveal-sheet">{pages}</div>{pager}</div>'
            "</details>"
        )
    return inner + "</div>"


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


#: rough character budget for one narrative page (the ruled sheet at reference size)
_NARRATIVE_CHARS = 820


def _narrative_pages(items: List[dict]) -> List[List[dict]]:
    """Chunk the narrative blocks into pages by a measured character budget."""
    pages: List[List[dict]] = []
    cur: List[dict] = []
    used = 0
    for it in items:
        cost = len(it.get("text", "")) + 24  # block overhead
        if cur and used + cost > _NARRATIVE_CHARS:
            pages.append(cur)
            cur, used = [], 0
        cur.append(it)
        used += cost
    if cur:
        pages.append(cur)
    return pages or [[]]


def _narrative_html(items: List[dict]) -> str:
    """One narrative page: the leaf's content in document order, rendered as
    content — prose paragraphs, bullet lists, collapsible summaries, mermaid
    notes. Compacted text when the agent provides it, verbatim otherwise (adr/0007)."""
    parts: List[str] = []
    bullets: List[dict] = []

    def flush_bullets() -> None:
        if bullets:
            parts.append('<ul class="narrative-list">' + "".join(
                f"<li>{_md_inline(b['text'])}</li>" for b in bullets
            ) + "</ul>")
            bullets.clear()

    for it in items:
        if it["kind"] == "bullet":
            bullets.append(it)
            continue
        flush_bullets()
        if it["kind"] == "prose":
            parts.append(f"<p>{_md_inline(it['text'])}</p>")
        elif it["kind"] == "details":
            parts.append(f'<div class="narrative-details">▸ {_md_inline(it["text"])}</div>')
        elif it["kind"] == "mermaid":
            parts.append('<div class="narrative-diagram">[diagram]</div>')
    flush_bullets()
    return '<div class="narrative">' + "".join(parts) + "</div>"


def _pages(node: dict, map_href: str = "") -> List[Tuple[str, str, str]]:
    """Return (density, extra-class, inner-html) pages in flip order.

    A notebook opens and closes on its covers: a hard front cover and a hard back
    cover, each shown alone, centred. The content between them is a soft two-page
    spread. Soft content pages keep forward/backward flips mirrored.
    """
    pages: List[Tuple[str, str, str]] = [("hard", "page-cover", _cover_html(node, map_href))]
    # Narrative first: the source content in document order, rendered as content
    # (compacted by the agent when available, verbatim otherwise). adr/0007.
    narrative = node.get("narrative") or node.get("source", [])
    if narrative:
        for chunk in _narrative_pages(narrative):
            pages.append(("soft", "", _narrative_html(chunk)))
    # Revision spread: recall → self-test → diagrams — the generated aids, appended
    # after the narrative, never interleaved with the source's chronology.
    if node.get("recall"):
        pages.append(("soft", "", _recall_html(node)))
    if node.get("prompt") or node.get("reveal"):
        # `page-selftest` names the page whose inner body does the column layout
        pages.append(("soft", "page-selftest", _selftest_html(node)))
    for d in node.get("diagrams", []):
        if d.get("svg"):
            pages.append(("soft", "page-diagram", _diagram_html(d)))
    # Source audit: the raw verbatim, only when the narrative is compacted (so the
    # reader can check the paraphrase against the original). Without compaction the
    # narrative already IS the raw, and a second copy would be redundant.
    if node.get("narrative") and node.get("source"):
        chunks = _chunk_source(node["source"])
        for i, chunk in enumerate(chunks):
            # the PAGE title only — the stage is still the source audit
            title = "Source audit" if i == 0 else f"Source audit (cont. {i + 1}/{len(chunks)})"
            pages.append(("soft", "", _source_html(chunk, title)))
    # A real book ends on a paired spread. StPageFlip's `createSpread()` shows the
    # front cover alone and then pairs from index 1 — (1,2), (3,4), … — so the back
    # cover (index N+1, where N is the content count) only shares a spread when N is
    # ODD, and then it shares it with the last content page.
    #
    # With an even N the back cover falls out as a lone hard page and the source
    # audit faces nothing. One blank leaf fixes the parity — and it goes FIRST, as
    # the flyleaf a real book has inside the front cover, NOT last: appended at the
    # end it would take the back cover's partner slot and the blank leaf, not the
    # audit, would be the page facing it. (Verified against the engine: 7 pages →
    # [[0], [1,2], [3,4], [5,6]].) A leaf with no content gets no flyleaf.
    content = len(pages) - 1
    if content and content % 2 == 0:
        pages.insert(1, ("soft", "", ""))
    pages.append(("hard", "page-cover", _back_cover_html(node, map_href)))
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


def render_notebook(
    node: dict,
    assets_rel: str = "../../../assets",
    map_href: str = "../../../index.html",
) -> str:
    """Render one leaf to a self-contained flip-notebook HTML string.

    `map_href` is the path back to the fused course map — the leaf's parent surface.
    It defaults to the §13 depth (`leaves/<leaf-id>/notebook.html` → `../../../`
    up to `mindmaps/index.html`), and an empty string drops the link.
    """
    title = _esc(node["title"])
    ver = _asset_version()
    page_divs = []
    for density, extra, inner in _pages(node, map_href):
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
  // --- pan and zoom a diagram inside its page ---------------------------------
  // A dense flowchart is unreadable fitted to a 520px page and there was no way to
  // enlarge it. One transform on an inner wrapper: drag pans, the wheel zooms about
  // the cursor, a double-click returns to the fitted view. The turn squares are the
  // page's top corners and pointer events here never reach them, so a drag cannot
  // turn the book.
  for (const dg of el.querySelectorAll('.diagram')) {{
    const inner = dg.querySelector('.diagram-zoom');
    if (!inner) continue;
    const MIN = 0.6, MAX = 6;
    let s = 1, tx = 0, ty = 0, drag = null;
    const apply = () => {{ inner.style.transform = `translate(${{tx}}px, ${{ty}}px) scale(${{s}})`; }};
    const reset = () => {{ s = 1; tx = 0; ty = 0; apply(); }};
    const capture = (id, on) => {{
      try {{ on ? dg.setPointerCapture(id) : dg.releasePointerCapture(id); }} catch (e) {{ /* not an active pointer */ }}
    }};
    dg.addEventListener('pointerdown', (e) => {{
      if (e.button !== 0) return;
      drag = {{ x: e.clientX - tx, y: e.clientY - ty }};
      capture(e.pointerId, true);
      dg.classList.add('is-panning');
      e.preventDefault();
    }});
    dg.addEventListener('pointermove', (e) => {{
      if (!drag) return;
      tx = e.clientX - drag.x; ty = e.clientY - drag.y; apply();
    }});
    const stop = (e) => {{
      if (!drag) return;
      drag = null; dg.classList.remove('is-panning'); capture(e.pointerId, false);
    }};
    dg.addEventListener('pointerup', stop);
    dg.addEventListener('pointercancel', stop);
    dg.addEventListener('wheel', (e) => {{
      e.preventDefault();
      const r = dg.getBoundingClientRect();
      const next = Math.min(MAX, Math.max(MIN, s * Math.exp(-e.deltaY * 0.0015)));
      const f = next / s;
      // keep whatever is under the cursor under the cursor
      const cx = e.clientX - r.left - r.width / 2 - tx;
      const cy = e.clientY - r.top - r.height / 2 - ty;
      tx -= cx * (f - 1); ty -= cy * (f - 1);
      s = next; apply();
    }}, {{ passive: false }});
    dg.addEventListener('dblclick', reset);
    reset();
  }}

  // --- the nested reveal: swap pages, conserve every answer -------------------
  // The pager sits at the BOTTOM of the page, which is the one region of the
  // notebook with no turn zone (the turn squares are the top margin corners), so
  // a click on it can never turn the book instead of the answer. Independent of
  // the flip, and it only touches its own sheet.
  for (const reveal of el.querySelectorAll('.reveal-sheet')) {{
    const pages = reveal.querySelectorAll('.reveal-page');
    const pager = reveal.parentElement.querySelector('.reveal-pager');
    if (!pager) continue;                       // a one-page answer needs no pager
    const count = pager.querySelector('.pager-count');
    const prev = pager.querySelector('[data-dir="prev"]');
    const next = pager.querySelector('[data-dir="next"]');
    let i = 0;
    const render = () => {{
      pages.forEach((p, n) => {{ p.hidden = n !== i; }});
      count.textContent = (i + 1) + ' / ' + pages.length;
      prev.disabled = i === 0;
      next.disabled = i === pages.length - 1;
    }};
    prev.addEventListener('click', () => {{ if (i > 0) {{ i--; render(); }} }});
    next.addEventListener('click', () => {{ if (i < pages.length - 1) {{ i++; render(); }} }});
    render();
  }}

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
    # A module can legitimately have NO leaves — no enumerable items and no agent
    # passes — and then nothing else creates this directory, so writing the
    # derived contract failed with a bare FileNotFoundError.
    module_dir.mkdir(parents=True, exist_ok=True)
    leaves = [n for n in iter_leaves(spec["root"]) if owns_content(n)]
    written: List[Path] = []
    for leaf in leaves:
        # SPEC §13: `leaves/<leaf-id>/` — the id, not a position. Both the map
        # and the notebook resolve the same name, so inserting a section above a
        # leaf cannot silently re-point a link at a different leaf.
        leaf_dir = module_dir / "leaves" / leaf_dir_id(leaf)
        leaf_dir.mkdir(parents=True, exist_ok=True)
        out = leaf_dir / "notebook.html"
        # the way back lands on THIS leaf, not the top of the map. The fragment is
        # namespaced <module-slug>--<leaf-id> so it resolves in the fused course map;
        # the module's OWN root is tagged with the bare slug (its course anchor).
        frag = module_slug if leaf.get("kind") == "module" else f"{module_slug}--{leaf['id']}"
        out.write_text(
            render_notebook(leaf, map_href=f"../../../index.html#{frag}"),
            encoding="utf-8",
        )
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
