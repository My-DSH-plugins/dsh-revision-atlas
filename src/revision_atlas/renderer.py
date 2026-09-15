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
from pathlib import Path
from typing import List, Optional

from .extractor import extract
from .spec_writer import build_structure

_ASSETS = Path(__file__).resolve().parent / "assets"


def _esc(text: str) -> str:
    return _html.escape(text)


def _anchor_html(node: dict) -> str:
    f = node.get("file")
    if f:
        line = node.get("line")
        if line is not None:
            href = f"{f}#{node.get('id', '')}"
            label = f"{f}:{line}"
        else:
            href = f
            label = f
        return f'<a href="{_esc(href)}">{_esc(label)}</a>'
    ev = node.get("evidence")
    if ev:
        return f'<a href="{_esc(ev["file"])}">cited {_esc(ev["file"])}:{ev["line"]}</a>'
    return ""


def _content_html(node: dict) -> str:
    title = _esc(node["title"])
    kind = node.get("kind")
    if kind in ("module", "section"):
        inner = f"<b>{title}</b>"
    else:
        inner = f'{title} <span style="color:#8b93a7;font-size:11px">· {kind}</span>'
    anchor = _anchor_html(node)
    if anchor:
        inner += f'<div style="color:#9aa3b2;font-size:10px">{anchor}</div>'
    return inner


def _checklist_html(item: dict) -> str:
    kind = item["kind"]
    if kind == "claim":
        return _esc(item["text"])
    if kind == "details":
        # summary is HTML captured verbatim from <summary>; render it, don't escape.
        label = item.get("summary") or f"line {item['line']}"
        return f'<span style="color:#8b93a7">[details]</span> {label}'
    if kind == "mermaid":
        return f'<span style="color:#8b93a7">[diagram]</span> mermaid (line {item["line"]})'
    return ""


def build_markmap_tree(spec: dict) -> dict:
    def convert(node: dict) -> dict:
        mn = {"content": _content_html(node)}
        children: List[dict] = []
        for b in (node.get("branches") or {}).values():
            children.append(convert(b))
        for c in node.get("children", []):
            children.append(convert(c))
        if node.get("checklist"):
            for item in node["checklist"]:
                children.append({"content": _checklist_html(item), "children": []})
        if children:
            mn["children"] = children
        return mn

    return convert(spec["root"])


def _read_asset(name: str) -> str:
    return (_ASSETS / name).read_text(encoding="utf-8")


def render_map(spec: dict) -> str:
    tree = build_markmap_tree(spec)
    opts = {"initialExpandLevel": 2, "duration": 300, "maxWidth": 800}
    tree_json = json.dumps(tree).replace("<", "\\u003c")
    opts_json = json.dumps(opts)
    title = _esc(spec["module"])

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
        f"  window.mm = markmap.Markmap.create('svg#mindmap', {opts_json}, {tree_json});\n"
        "  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {\n"
        "    document.documentElement.classList.add('markmap-dark');\n"
        "  }\n"
        "})();\n"
        "</script>\n"
        "</body>\n</html>\n"
    )

    return head + scripts


def main(argv: "List[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Revision Atlas module-map renderer (ticket 0004)")
    ap.add_argument("module_dir")
    ap.add_argument("--semantic", help="JSON file mapping leaf title -> claims (agent pass)")
    ap.add_argument("--out-dir", default=".", help="write index.html here")
    args = ap.parse_args(argv)

    inv = extract(args.module_dir)
    semantic = None
    if args.semantic:
        with open(args.semantic, encoding="utf-8") as f:
            semantic = json.load(f)
    spec = build_structure(inv, semantic=semantic)["spec"]
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render_map(spec), encoding="utf-8")
    print(f"wrote {out / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
