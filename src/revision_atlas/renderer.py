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
import base64
import html as _html
import json
import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from .extractor import extract
from .leaf_generator import annotate_artifacts
from .mermaid_render import render_leaf_mermaids
from .spec_writer import build_structure, leaf_dir_id

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
    if not leaves_prefix or "checklist" not in node:
        return ""
    href = _link(f"{leaves_prefix.rstrip('/')}/{leaf_dir_id(node)}/notebook.html")
    return f'<a href="{_esc(href)}">notebook</a>'


def _content_html(
    node: dict, leaves_prefix: "Optional[str]" = None, source_base: str = ""
) -> str:
    title = _esc(node["title"])
    kind = node.get("kind")
    if kind in ("module", "section"):
        inner = f"<b>{title}</b>"
    else:
        inner = f'{title} <span style="color:#8b93a7;font-size:11px">· {kind}</span>'
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


def _img_data_uri(svg: str) -> str:
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _diagram_node(d: dict) -> dict:
    """One mermaid diagram slot -> an image-only markmap node (SPEC §10: images
    survive only as image-only nodes), or a placeholder until rendered."""
    if d.get("svg"):
        img = (
            f'<img src="{_img_data_uri(d["svg"])}" '
            'style="max-width:280px;background:#fff;border-radius:4px" />'
        )
        return {"content": img, "children": []}
    return {"content": '<span style="color:#8b93a7">[diagram] mermaid — pending</span>', "children": []}


def _leaf_artifact_children(node: dict) -> List[dict]:
    """The artifact surface a leaf shows in the map: recall bullets, diagrams,
    self-test (prompt + collapsed reveal), and the collapsed source audit."""
    kids: List[dict] = []
    for b in node.get("recall", []):
        kids.append({"content": f"• {_esc(b)}", "children": []})
    for d in node.get("diagrams", []):
        kids.append(_diagram_node(d))
    if node.get("prompt"):
        inner = (
            f'<b>self-test</b><div style="color:#8b93a7;font-size:11px">'
            f"{_esc(node['prompt'])}</div>"
        )
        reveal = node.get("reveal", "")
        if reveal:
            inner += (
                '<details style="font-size:11px;margin-top:2px">'
                "<summary>reveal</summary>"
                f'<div style="color:#9aa3b2">{_esc(reveal)}</div></details>'
            )
        kids.append({"content": inner, "children": []})
    if node.get("source"):
        rows = []
        for it in node["source"]:
            if isinstance(it, dict):
                tag = {"details": "[details] ", "mermaid": "[diagram] "}.get(it.get("kind"), "")
                rows.append(_esc(tag + it.get("text", "")))
            else:
                rows.append(_esc(it))
        src_html = "<br>".join(rows)
        kids.append({
            "content": (
                f'<details style="font-size:11px;color:#9aa3b2">'
                f"<summary>source ({len(node['source'])})</summary>"
                f"<div>{src_html}</div></details>"
            ),
            "children": [],
        })
    return kids


def build_markmap_tree(
    spec: dict, leaves_prefix: "Optional[str]" = None, source_base: str = ""
) -> dict:
    def convert(node: dict) -> dict:
        mn = {"content": _content_html(node, leaves_prefix, source_base)}
        children: List[dict] = []
        for b in (node.get("branches") or {}).values():
            children.append(convert(b))
        for c in node.get("children", []):
            children.append(convert(c))
        if node.get("checklist") is not None:
            children.extend(_leaf_artifact_children(node))
        if children:
            mn["children"] = children
        return mn

    return convert(spec["root"])


def _read_asset(name: str) -> str:
    return (_ASSETS / name).read_text(encoding="utf-8")


def render_map(
    spec: dict, leaves_prefix: "Optional[str]" = None, source_base: str = ""
) -> str:
    """The self-contained module map.

    `leaves_prefix` (e.g. `leaves`) turns each leaf into a link to its notebook;
    `source_base` is the relative path from the map's own directory back to the
    module's markdown, so every source anchor resolves from where the map sits
    (SPEC §13 puts `mindmaps/<slug>/` beside `modules/<slug>/`). Both are the
    caller's to know — `build` derives them from the real layout.
    """
    tree = build_markmap_tree(spec, leaves_prefix, source_base)
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
