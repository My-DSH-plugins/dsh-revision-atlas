"""Module-map renderer (ticket 0004).

Turns a Revision Atlas spec tree into a self-contained, offline markmap HTML:
every node carries its title, kind, and a source anchor; a leaf's checklist
items render as child nodes. The viewer (d3 + markmap) and toolbar are inlined
from vendored assets, so the file works with zero network.

The renderer is behind a seam: it consumes `spec` (the machine contract), never
the markdown — so the spec, not markmap, is the source of truth (SPEC §10).
"""
from __future__ import annotations

import argparse
import html as _html
import json
import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from .extractor import extract
from .leaf_generator import annotate_artifacts
from .mermaid_render import render_leaf_mermaids
from .spec_writer import build_structure, leaf_dir_id, owns_content

_ASSETS = Path(__file__).resolve().parent / "assets"


def _esc(text: str) -> str:
    return _html.escape(text)


def source_base_for(
    module_dir: str, map_dir: str, override: "Optional[str]" = None
) -> str:
    """The relative path from the map's own directory back to the module markdown.

    SPEC §13 puts `mindmaps/<slug>/` beside `modules/<slug>/`, so the real layout
    already answers this — derive it from the two paths instead of hard-coding a
    guess (an href of bare `README.md` only resolves if the README happened to sit
    next to the map, which it does not). An artifact tree deployed somewhere else
    — a portfolio site with no course repo around it — passes `override`.
    """
    if override is not None:
        return f"{override.rstrip('/')}/" if override else ""
    try:
        rel = os.path.relpath(Path(module_dir).resolve(), Path(map_dir).resolve())
    except ValueError:  # different drives on Windows — nothing sensible to build
        return ""
    return "" if rel == "." else f"{rel.rstrip('/')}/"


def _link(path: str, frag: str = "") -> str:
    """A relative href, percent-encoded.

    A course module or a source file can be named with a space (`Harness
    Engineering`, `My Notes.md`); an unencoded space in an href is at the mercy
    of the browser. Everything outside the artifact is reached through the base
    path the caller supplies — the renderer never guesses where it is deployed.
    """
    href = quote(path, safe="/")
    return f"{href}#{quote(frag, safe='-_.')}" if frag else href


def _anchor_html(node: dict, source_base: str = "") -> str:
    f = node.get("file")
    if f:
        line = node.get("line")
        if line is not None:
            href = _link(source_base + f, node.get("id", ""))
            label = f"{f}:{line}"
        else:
            href = _link(source_base + f)
            label = f
        return f'<a href="{_esc(href)}">{_esc(label)}</a>'
    ev = node.get("evidence")
    if ev:
        return f'<a href="{_esc(_link(source_base + ev["file"]))}">cited {_esc(ev["file"])}:{ev["line"]}</a>'
    return ""


def _notebook_html(node: dict, leaves_prefix: "Optional[str]") -> str:
    """The leaf's paged notebook — the artifact this map exists to reach.

    Only leaves get one, and only when the caller names the prefix: the map and
    `generate_all` derive the same directory name from the same id, so the link
    cannot drift from what was written.
    """
    if not leaves_prefix or not owns_content(node):
        return ""
    href = _link(f"{leaves_prefix.rstrip('/')}/{leaf_dir_id(node)}/notebook.html")
    return f'<a href="{_esc(href)}">notebook</a>'


def _content_html(
    node: dict, leaves_prefix: "Optional[str]" = None, source_base: str = "",
    id_prefix: str = "", root_id: "Optional[str]" = None,
) -> str:
    title = _esc(node["title"])
    kind = node.get("kind")
    # The node's id rides on the element that wraps its TITLE, and inline, so the
    # map can be linked INTO (`index.html#<leaf-id>`) without changing the layout
    # the map would otherwise draw. A block wrapper here does alter it — markmap's
    # own CSS keys off its inner div.
    #
    # In the fused course map every id is namespaced `<module-slug>--<leaf-id>` so
    # two modules with the same heading cannot collide in the one document (0008 at
    # course scale). The module's OWN root is the exception: it is tagged with the
    # bare `slug`, because that is the anchor a course index / portfolio links to.
    raw_id = root_id if root_id is not None else f"{id_prefix}{node.get('id', '')}"
    nid = _esc(raw_id)
    if kind in ("module", "section"):
        inner = f'<b data-atlas-node="{nid}">{title}</b>'
    else:
        inner = (
            f'<span data-atlas-node="{nid}">{title}</span>'
            f' <span style="color:#8b93a7;font-size:11px">· {kind}</span>'
        )
    links = [
        x
        for x in (
            _anchor_html(node, source_base),
            _notebook_html(node, leaves_prefix),
        )
        if x
    ]
    if links:
        inner += f'<div style="color:#9aa3b2;font-size:10px">{" · ".join(links)}</div>'
    return inner


def build_markmap_tree(
    spec: dict, leaves_prefix: "Optional[str]" = None, source_base: str = "",
    id_prefix: str = "", root_id_override: "Optional[str]" = None,
) -> dict:
    """The module's STRUCTURE — and nothing else.

    A leaf used to fan out into its recall bullets, its diagrams, its self-test
    prompt and its source audit. That was a degraded second copy of the notebook:
    unstyled, unpaginated, with the question but never the answer, and it made the
    map end in bullet lists instead of leaves. The notebook is where a leaf's
    content lives (SPEC §9); the map's job is the outline and the way in, so every
    node — parent or leaf — carries a title, its kind, its source anchor and its
    `notebook` link.

    Measured consequence: the map no longer inlines each leaf's diagram as a base64
    data URI — ~22 KB per diagram (a 17 KB SVG), so ~130 KB for a six-diagram
    module. The map's own bulk is the vendored d3 + markmap libraries (~300 KB,
    constant), so that is a saving rather than the main event.
    """
    def convert(node: dict, is_root: bool = False) -> dict:
        root_id = root_id_override if is_root else None
        mn = {"content": _content_html(
            node, leaves_prefix, source_base, id_prefix=id_prefix, root_id=root_id,
        )}
        children: List[dict] = []
        for b in (node.get("branches") or {}).values():
            children.append(convert(b))
        for c in node.get("children", []):
            children.append(convert(c))
        if children:
            mn["children"] = children
        return mn

    return convert(spec["root"], is_root=True)


def _read_asset(name: str) -> str:
    return (_ASSETS / name).read_text(encoding="utf-8")


def render_map(
    spec: dict, leaves_prefix: "Optional[str]" = None, source_base: str = "",
    id_prefix: str = "",
) -> str:
    """The self-contained module map (a course of one module).

    `leaves_prefix` (e.g. `leaves`) turns each leaf into a link to its notebook;
    `source_base` is the relative path from the map's own directory back to the
    module's markdown, so every source anchor resolves from where the map sits.
    `id_prefix` namespaces every `data-atlas-node` id — the fused renderer passes
    `<module-slug>--` so two modules with the same heading cannot collide.
    """
    tree = build_markmap_tree(spec, leaves_prefix, source_base, id_prefix=id_prefix)
    opts = {"initialExpandLevel": 2, "duration": 300, "maxWidth": 800}
    return _render_html(tree, spec["module"], opts)


def _render_html(tree: dict, title: str, opts: dict) -> str:
    tree_json = json.dumps(tree).replace("<", "\\u003c")
    opts_json = json.dumps(opts)
    title = _esc(title)

    head = f"""<!doctype html>
<html>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=4.0, user-scalable=yes" />
<title>{title} — Revision Atlas</title>
<style>
* {{ margin: 0; padding: 0; }}
html {{ font-family: ui-sans-serif, system-ui, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'; }}
#mindmap {{ display: block; width: 100vw; height: 100vh; }}
.markmap-dark {{ background: #27272a; color: white; }}
{_read_asset('markmap-toolbar.css')}
</style>
</head>
<body>
<svg id="mindmap"></svg>
"""

    scripts = (
        f"<script>{_read_asset('d3.min.js')}</script>"
        f"<script>{_read_asset('markmap-view.js')}</script>"
        f"<script>{_read_asset('markmap-toolbar.js')}</script>"
        "<script>\n"
        "((r) => { setTimeout(r); })(() => {\n"
        "  const { markmap, mm } = window;\n"
        "  const toolbar = new markmap.Toolbar();\n"
        "  toolbar.attach(mm);\n"
        "  const el = toolbar.render();\n"
        "  el.setAttribute('style', 'position:absolute;bottom:20px;right:20px');\n"
        "  document.body.append(el);\n"
        "});\n"
        "</script>\n"
        "<script>\n"
        "(() => {\n"
        "  const markmap = window.markmap;\n"
        f"  const tree = {tree_json};\n"
        f"  const base = {json.dumps(opts)};\n"
        "  // A leaf's notebook links BACK to the node it belongs to, so arriving from\n"
        "  // one should land on that leaf rather than the top of the map. The target is\n"
        "  // identified by the id we tagged its title with; the map has to open deep\n"
        "  // enough to reveal it, and then centre it.\n"
        "  const wanted = decodeURIComponent((location.hash || '').slice(1)).trim();\n"
        "  const isId = (s) => /^[a-z0-9-]+$/.test(s);\n"
        "  const depthOf = (needle) => {\n"
        "    const hit = (n, d) => {\n"
        "      if (String(n.content || '').indexOf('data-atlas-node=\"' + needle + '\"') !== -1) return d;\n"
        "      for (const c of n.children || []) { const r = hit(c, d + 1); if (r >= 0) return r; }\n"
        "      return -1;\n"
        "    };\n"
        "    return hit(tree, 0);\n"
        "  };\n"
        "  const depth = wanted && isId(wanted) ? depthOf(wanted) : -1;\n"
        "  // markmap expands levels 0..N-1, so revealing a node AT depth d needs d+1\n"
        "  const opts = depth >= 0 ? { ...base, initialExpandLevel: Math.max(base.initialExpandLevel, depth + 1) } : base;\n"
        "  const mm = markmap.Markmap.create('svg#mindmap', opts, null);\n"
        "  window.mm = mm;\n"
        "  const focus = () => {\n"
        "    const svg = document.querySelector('svg#mindmap');\n"
        "    const el = document.querySelector('[data-atlas-node=\"' + wanted + '\"]');\n"
        "    if (!el || !window.d3 || !mm.svg || !mm.zoom) return;   // never break the map\n"
        "    const s = svg.getBoundingClientRect(), r = el.getBoundingClientRect();\n"
        "    const t = window.d3.zoomTransform(svg);\n"
        "    if (!t.k) return;\n"
        "    const cx = (r.left + r.width / 2 - s.left - t.x) / t.k;\n"
        "    const cy = (r.top + r.height / 2 - s.top - t.y) / t.k;\n"
        "    const nt = window.d3.zoomIdentity\n"
        "      .translate(s.width / 2 - cx * t.k, s.height / 2 - cy * t.k)\n"
        "      .scale(t.k);\n"
        "    // applied at once, not animated: you are ARRIVING at a leaf you chose,\n"
        "    // so there is nothing to glide from. It also keeps this verifiable —\n"
        "    // a d3 transition does not advance under a headless virtual clock.\n"
        "    window.d3.select(svg).call(mm.zoom.transform, nt);\n"
        "  };\n"
        "  mm.setData(tree).then(() => { mm.fit(); if (depth >= 0) focus(); });\n"
        "  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {\n"
        "    document.documentElement.classList.add('markmap-dark');\n"
        "  }\n"
        "})();\n"
        "</script>\n"
        "</body>\n</html>\n"
    )

    return head + scripts


def build_course_tree(course_name: str, modules: "List[dict]") -> dict:
    """Compose module subtrees under a course root (SPEC §3 — the fused map).

    `modules` is a list of `{"spec": …, "slug": …, "source_base": …}`. Each
    module's root is tagged with its bare `slug` (the anchor a course index or a
    portfolio page deep-links to); every descendant is tagged `<slug>--<id>` so two
    modules with the same heading cannot collide in the one document (the 0008
    duplicate-title bug, now at course scale). A leaf's notebook link resolves to
    `<slug>/leaves/<leaf-id>/notebook.html`, so `leaves_prefix` carries the slug.
    """
    children: List[dict] = []
    for m in modules:
        spec = m["spec"]
        slug = m["slug"]
        children.append(build_markmap_tree(
            spec,
            leaves_prefix=f"{slug}/leaves",
            source_base=m.get("source_base", ""),
            id_prefix=f"{slug}--",
            root_id_override=slug,
        ))
    return {"content": _esc(course_name), "children": children}


def render_course_map(course_name: str, modules: "List[dict]") -> str:
    """The one fused course map: course root → module subtrees → leaves.

    Rendered collapsed to module level (`initialExpandLevel: 1`) so the fused map
    *is* the course index at rest; a reader expands a module to reveal its faithful
    H2/H3 tree. Contrast `render_map` (a course of one module, base level 2).
    """
    tree = build_course_tree(course_name, modules)
    opts = {"initialExpandLevel": 1, "duration": 300, "maxWidth": 800}
    return _render_html(tree, course_name, opts)


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas module-map renderer (ticket 0004+0005)")
    ap.add_argument("module_dir")
    ap.add_argument("--semantic", help="JSON file mapping leaf id -> claims (agent pass)")
    ap.add_argument("--recall", help="JSON file mapping leaf id -> {recall,prompt,reveal} (self-test pass)")
    ap.add_argument("--mermaid", help="JSON file mapping leaf id -> [mermaid .mmd strings] (diagram pass)")
    ap.add_argument("--out-dir", default=".", help="write index.html here")
    ap.add_argument(
        "--leaves-prefix",
        default="leaves",
        help="dir holding <leaf-id>/notebook.html, relative to the map ('' disables the links)",
    )
    ap.add_argument(
        "--source-base",
        default=None,
        help="path from the map's dir back to the module's markdown "
        "(default: derived from --out-dir and module_dir)",
    )
    args = ap.parse_args(argv)

    inv = extract(args.module_dir)
    semantic = None
    if args.semantic:
        with open(args.semantic, encoding="utf-8") as f:
            semantic = json.load(f)
    recall = None
    if args.recall:
        with open(args.recall, encoding="utf-8") as f:
            recall = json.load(f)
    mermaid = None
    if args.mermaid:
        with open(args.mermaid, encoding="utf-8") as f:
            mermaid = json.load(f)
    spec = build_structure(inv, semantic=semantic, recall=recall, mermaid=mermaid)["spec"]
    # Leaf artifacts (0005): diagram slots + source bullets, then mermaid SVGs.
    annotate_artifacts(inv, spec["root"])
    render_leaf_mermaids(inv, spec["root"])
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = source_base_for(args.module_dir, out, args.source_base)
    (out / "index.html").write_text(
        render_map(spec, leaves_prefix=args.leaves_prefix, source_base=base),
        encoding="utf-8",
    )
    print(f"wrote {out / 'index.html'}")
    print(f"source base: {base!r} · leaves prefix: {args.leaves_prefix!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
