"""Mermaid rendering (adr/0002) — build-time, offline.

Renders a leaf's ```mermaid block to a self-contained SVG using a vendored
mermaid bundle (cached at build time, never committed) and a headless Chromium.
The output SVG is what gets inlined into the map; the browser and bundle are
build-machine dependencies only.

Honours adr/0002: pinned mermaid version, top-level `htmlLabels:false` (so
labels are real `<text>`, portable in `<img>`), unique render id per diagram,
helper SVGs filtered out.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

MERMAID_VERSION = "11.17.2"
_CACHE_DIR = Path.home() / ".cache" / "revision-atlas"
_MERMAID_JS = _CACHE_DIR / f"mermaid-{MERMAID_VERSION}.min.js"


def _find_chromium() -> "Optional[str]":
    env = os.environ.get("CHROME_BIN")
    if env:
        return env
    base = Path.home() / "Library/Caches/ms-playwright"
    if base.is_dir():
        for p in base.glob("chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell"):
            if p.is_file():
                return str(p)
        for p in base.glob("chromium-*/chrome-mac-*/Chromium.app/Contents/MacOS/Chromium"):
            if p.is_file():
                return str(p)
    for cmd in ("google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(cmd)
        if p:
            return p
    return None


def _ensure_mermaid_js() -> Path:
    if not _MERMAID_JS.exists():
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        url = f"https://cdn.jsdelivr.net/npm/mermaid@{MERMAID_VERSION}/dist/mermaid.min.js"
        # curl (not urllib): the system Python's TLS cert store is broken on this
        # machine; curl uses the OS keychain and works.
        subprocess.run(
            ["curl", "-sL", "--fail", "--max-time", "120", "-o", str(_MERMAID_JS), url],
            check=True,
        )
    return _MERMAID_JS


def extract_mermaid_source(path: "str | Path", fence_line: int) -> str:
    """Extract the .mmd body of the ```mermaid block that opens at `fence_line`."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    body: List[str] = []
    in_block = False
    for i, line in enumerate(lines, 1):
        if i < fence_line:
            continue
        s = line.strip()
        if s.startswith("```"):
            if in_block:
                break
            in_block = True
            continue
        if in_block:
            body.append(line)
    non_empty = [l for l in body if l.strip()]
    if not non_empty:
        return ""
    indent = min(len(l) - len(l.lstrip()) for l in non_empty)
    return "\n".join(l[indent:] if len(l) >= indent else l for l in body).strip()


def render_mermaid_svgs(mmds: List[str]) -> List[str]:
    """Render a list of .mmd sources to SVG strings (one chromium run)."""
    chromium = _find_chromium()
    if not chromium:
        raise RuntimeError("no headless Chromium found (set CHROME_BIN)")
    mermaid_js = _ensure_mermaid_js().read_text(encoding="utf-8")
    sources_json = json.dumps(mmds).replace("</", "<\\/")

    harness = (
        '<!doctype html><html><head><meta charset="utf-8"><title>PENDING</title></head><body>'
        f"<script>{mermaid_js}</script>"
        "<script>"
        f"const diagrams={sources_json};"
        "(async()=>{"
        "  mermaid.initialize({startOnLoad:false, theme:'neutral', htmlLabels:false, flowchart:{useMaxWidth:false}});"
        "  const holder=document.createElement('div'); holder.id='out'; document.body.appendChild(holder);"
        "  for(let i=0;i<diagrams.length;i++){"
        "    try{ const {svg}=await mermaid.render('d'+i, diagrams[i]);"
        "      const d=document.createElement('div'); d.id='R_'+i; d.innerHTML=svg; holder.appendChild(d);"
        "    }catch(e){ const d=document.createElement('div'); d.id='R_'+i; d.textContent='ERR '+String(e&&e.message); holder.appendChild(d); }"
        "  }"
        "  document.title='DONE';"
        "})();"
        "</script></body></html>"
    )

    with tempfile.TemporaryDirectory() as td:
        hp = Path(td) / "harness.html"
        hp.write_text(harness, encoding="utf-8")
        proc = subprocess.run(
            [chromium, "--headless", "--no-sandbox", "--disable-gpu",
             "--virtual-time-budget=30000", "--dump-dom", hp.as_uri()],
            capture_output=True, text=True, timeout=180,
        )
    dom = proc.stdout
    if "<title>DONE</title>" not in dom:
        raise RuntimeError(f"mermaid render did not finish (stderr: {proc.stderr[:200]})")

    svgs: List[str] = []
    for i in range(len(mmds)):
        m = re.search(rf'<div id="R_{i}">([\s\S]*?)</div>', dom)
        if not m:
            raise RuntimeError(f"diagram {i} missing from rendered DOM")
        s = re.search(r"<svg[\s\S]*?</svg>", m.group(1))
        if not s:
            raise RuntimeError(f"diagram {i} failed: {m.group(1)[:120]}")
        svgs.append(s.group(0))
    return svgs


def render_leaf_mermaids(inv: dict, root: dict) -> dict:
    """Render every mermaid leaf's source block to SVG; attach `diagram["svg"]`."""
    leaves: List[dict] = []

    def walk(node: dict) -> None:
        for b in (node.get("branches") or {}).values():
            walk(b)
        for c in node.get("children", []):
            walk(c)
        if "checklist" in node and node.get("diagram", {}).get("kind") == "mermaid":
            leaves.append(node)

    walk(root)
    if not leaves:
        return root

    sources = [
        extract_mermaid_source(Path(inv["root"]) / leaf["file"], leaf["diagram"]["mmd_line"])
        for leaf in leaves
    ]
    svgs = render_mermaid_svgs(sources)
    for leaf, svg in zip(leaves, svgs):
        leaf["diagram"]["svg"] = svg
        leaf["diagram"]["mermaid"] = MERMAID_VERSION
    return root


if __name__ == "__main__":
    raise SystemExit("import me; no CLI yet")
