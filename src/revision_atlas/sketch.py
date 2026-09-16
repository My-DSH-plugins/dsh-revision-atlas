"""Hand-drawn diagram sketch renderer (ticket 0005, adr/0004).

Deterministic template layout + hand-drawn SVG. The agent supplies **topology
only** — a template, an ordered node list with 1–5-word labels, and an optional
per-node shape. This module supplies **geometry**, guaranteeing the layout
invariant by construction:

  1. no overlap — box spacing exceeds the jitter amplitude;
  2. label fit — every box is sized from a conservative per-character width;
  3. orientation — arrows flow one way (down / right / around the ring);
  4. alignment — one uniform box size per diagram, grid-placed.

Labels are real ``<text>`` (verifier-parseable); jitter applies to *paths only*,
never to text. A hand-drawn feel comes from seeded rough strokes; the true
handwriting-font subset (base64 ``@font-face``) is a follow-up build step — the
font-family stack here is its stand-in until then.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
from typing import Dict, List, Tuple

FONT_SIZE = 16
PAD_X = 14          # horizontal padding inside a box
PAD_Y = 8           # vertical padding inside a box
MIN_W = 72
MIN_H = 40
CHAR_W = 10         # conservative per-char width (px) at FONT_SIZE — overestimate
ROW_GAP = 26        # vertical gap between boxes (flow / tree)
COL_GAP = 28        # horizontal gap between boxes (comparison / tree)
JITTER = 3          # max rough-stroke amplitude; spacing must exceed this
MARGIN = 12         # viewBox margin around the whole drawing
TEMPLATES = ("flow", "tree", "cycle", "comparison")
SHAPES = ("rectangle", "ellipse", "diamond")
STROKE = "#1e1e1e"
FONT_STACK = "'Caveat', 'Patrick Hand', 'Segoe Print', 'Comic Sans MS', cursive"


def node_size(label: str, shape: str = "rectangle") -> Tuple[float, float]:
    """Conservative box size for a single-line label (shape ignored for sizing —
    every box is sized to its text with room to spare, so a label can't overflow)."""
    w = max(MIN_W, len(label) * CHAR_W + 2 * PAD_X)
    h = max(MIN_H, FONT_SIZE + 2 * PAD_Y)
    return w, h


def _rng(seed: str):
    """Deterministic PRNG (md5-seeded LCG) so the same spec renders identically."""
    state = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) & 0x7FFFFFFF

    def rand() -> float:
        nonlocal state
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    return rand


def layout(spec: dict) -> Dict[int, Tuple[float, float, float, float]]:
    """Compute (cx, cy, w, h) per node, keyed by node index.

    All boxes in a diagram share one uniform size (the widest label), so
    alignment holds by construction; each template places them on a regular grid
    or ring whose gaps exceed JITTER.
    """
    nodes = spec["nodes"]
    template = spec.get("template", "flow")
    sizes = [node_size(n["label"], n.get("shape", "rectangle")) for n in nodes]
    w = max(s[0] for s in sizes)
    h = max(s[1] for s in sizes)
    pos: Dict[int, Tuple[float, float, float, float]] = {}
    n = len(nodes)

    if template == "flow":
        total = n * h + (n - 1) * ROW_GAP
        y = -total / 2
        for i in range(n):
            pos[i] = (0, y + h / 2, w, h)
            y += h + ROW_GAP
    elif template == "comparison":
        total = n * w + (n - 1) * COL_GAP
        x = -total / 2
        for i in range(n):
            pos[i] = (x + w / 2, 0, w, h)
            x += w + COL_GAP
    elif template == "tree":
        # root above, one row of children below.
        root_y = -(h + ROW_GAP) / 2
        child_y = +(h + ROW_GAP) / 2
        pos[0] = (0, root_y, w, h)
        m = max(n - 1, 1)
        total = m * w + (m - 1) * COL_GAP
        x = -total / 2
        for i in range(1, n):
            pos[i] = (x + w / 2, child_y, w, h)
            x += w + COL_GAP
    elif template == "cycle":
        radius = max((w + ROW_GAP) * n / (2 * math.pi), 60)
        for i in range(n):
            ang = -math.pi / 2 + i * 2 * math.pi / n
            pos[i] = (radius * math.cos(ang), radius * math.sin(ang), w, h)
    else:
        raise ValueError(f"unknown template {template!r} (use one of {TEMPLATES})")
    return pos


def arrow_segments(spec: dict) -> List[Tuple[float, float, float, float]]:
    """Arrow endpoints (x1,y1,x2,y2) derived from template + node order."""
    pos = layout(spec)
    n = len(spec["nodes"])
    template = spec.get("template", "flow")
    segs: List[Tuple[float, float, float, float]] = []
    if template in ("flow", "cycle"):
        for i in range(n - 1):
            x1, y1, _, h1 = pos[i]
            x2, y2, _, h2 = pos[i + 1]
            segs.append((x1, y1 + h1 / 2, x2, y2 - h2 / 2))
        if template == "cycle" and n > 1:
            x1, y1, _, h1 = pos[n - 1]
            x2, y2, _, h2 = pos[0]
            segs.append((x1, y1 + h1 / 2, x2, y2 - h2 / 2))
    elif template == "tree" and n > 1:
        x1, y1, _, h1 = pos[0]
        for i in range(1, n):
            x2, y2, _, h2 = pos[i]
            segs.append((x1, y1 + h1 / 2, x2, y2 - h2 / 2))
    # comparison: no arrows (side-by-side alternatives, not a sequence)
    return segs


def _jitter(pt: Tuple[float, float], rand) -> Tuple[float, float]:
    return (pt[0] + (rand() * 2 - 1) * JITTER, pt[1] + (rand() * 2 - 1) * JITTER)


def _shape_path(shape: str, cx: float, cy: float, w: float, h: float, rand) -> str:
    if shape == "ellipse":
        pts = [
            (cx + w / 2 * math.cos(2 * math.pi * k / 16), cy + h / 2 * math.sin(2 * math.pi * k / 16))
            for k in range(16)
        ]
    elif shape == "diamond":
        pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
    else:  # rectangle
        pts = [
            (cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
            (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2),
        ]
    j = [_jitter(p, rand) for p in pts]
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in j) + " Z"
    return d


def _arrow_path(x1, y1, x2, y2, rand) -> str:
    mx = (x1 + x2) / 2 + (rand() * 2 - 1) * 2
    my = (y1 + y2) / 2 + (rand() * 2 - 1) * 2
    return f"M {x1:.1f} {y1:.1f} Q {mx:.1f} {my:.1f} {x2:.1f} {y2:.1f}"


def _arrowhead(x, y, ang: float) -> str:
    s = 7
    a1 = ang + math.pi - 0.42
    a2 = ang + math.pi + 0.42
    p1 = (x + s * math.cos(a1), y + s * math.sin(a1))
    p2 = (x + s * math.cos(a2), y + s * math.sin(a2))
    return f"M {x:.1f} {y:.1f} L {p1[0]:.1f} {p1[1]:.1f} L {p2[0]:.1f} {p2[1]:.1f} Z"


def render_svg(spec: dict) -> str:
    """Render the spec to a self-contained hand-drawn SVG (real <text> labels)."""
    nodes = spec["nodes"]
    pos = layout(spec)
    segs = arrow_segments(spec)

    # Bounding box over box corners.
    xs: List[float] = []
    ys: List[float] = []
    for cx, cy, w, h in pos.values():
        xs += [cx - w / 2, cx + w / 2]
        ys += [cy - h / 2, cy + h / 2]
    minx, maxx = min(xs) - MARGIN, max(xs) + MARGIN
    miny, maxy = min(ys) - MARGIN, max(ys) + MARGIN
    vb = f"{minx:.1f} {miny:.1f} {maxx - minx:.1f} {maxy - miny:.1f}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
        f'width="{maxx - minx:.0f}" height="{maxy - miny:.0f}" '
        f'font-family="{FONT_STACK}" font-size="{FONT_SIZE}">',
        f'<g fill="none" stroke="{STROKE}" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round">',
    ]

    for i, (x1, y1, x2, y2) in enumerate(segs):
        r = _rng(f"arrow-{i}")
        parts.append(f'<path d="{_arrow_path(x1, y1, x2, y2, r)}"/>')
        ang = math.atan2(y2 - y1, x2 - x1)
        parts.append(f'<path d="{_arrowhead(x2, y2, ang)}" fill="{STROKE}" stroke="none"/>')

    parts.append("</g>")

    for i, node in enumerate(nodes):
        cx, cy, w, h = pos[i]
        r = _rng(f"box-{i}")
        shape = node.get("shape", "rectangle")
        d = _shape_path(shape, cx, cy, w, h, r)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{STROKE}" stroke-width="1.6" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    for i, node in enumerate(nodes):
        cx, cy, _, _ = pos[i]
        label = html.escape(node["label"])
        parts.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" fill="{STROKE}">{label}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m revision_atlas.sketch spec.json [--out out.svg]")
    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)
    svg = render_svg(spec)
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        with open(out, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {out}")
    else:
        print(svg)
