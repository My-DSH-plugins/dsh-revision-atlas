"""Acceptance tests for ticket 0005 — hand-drawn sketch renderer (adr/0004).

The invariant is checked against `layout()` output (geometry), not pixels:
no overlap, label fit, orientation, determinism, and real <text> labels.
"""
import unittest

from revision_atlas.sketch import (
    CHAR_W,
    FONT_SIZE,
    PAD_X,
    PAD_Y,
    arrow_segments,
    layout,
    node_size,
    render_svg,
)


def _spec(template, labels):
    return {"template": template, "nodes": [{"label": s} for s in labels]}


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return abs(ax - bx) < aw and abs(ay - by) < ah


class TestLayoutInvariant(unittest.TestCase):
    TEMPLATES = ("flow", "tree", "cycle", "comparison")

    def test_no_overlap_all_templates(self):
        for t in self.TEMPLATES:
            spec = _spec(t, ["Alpha", "Beta long label", "Gamma", "Delta", "Epsilon"])
            pos = layout(spec)
            boxes = list(pos.values())
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    self.assertFalse(_overlap(boxes[i], boxes[j]), f"{t}: {i} overlaps {j}")

    def test_label_fit(self):
        for label in ("X", "Hallucination", "plausibility is not truth", "A B C D E"):
            w, h = node_size(label)
            self.assertGreaterEqual(w, len(label) * CHAR_W + 2 * PAD_X, label)
            self.assertGreaterEqual(h, FONT_SIZE + 2 * PAD_Y, label)

    def test_layout_uses_uniform_box(self):
        spec = _spec("flow", ["x", "a much longer label than the others"])
        pos = layout(spec)
        widths = {w for _, _, w, _ in pos.values()}
        heights = {h for _, _, _, h in pos.values()}
        self.assertEqual(len(widths), 1)   # one uniform size -> alignment by construction
        self.assertEqual(len(heights), 1)

    def test_orientation(self):
        # flow: arrows point down
        segs = arrow_segments(_spec("flow", ["A", "B", "C"]))
        self.assertEqual(len(segs), 2)
        for x1, y1, x2, y2 in segs:
            self.assertGreater(y2, y1)

        # tree: root above children, all arrows point down
        segs = arrow_segments(_spec("tree", ["Root", "L", "R"]))
        self.assertEqual(len(segs), 2)
        for x1, y1, x2, y2 in segs:
            self.assertGreater(y2, y1)

        # comparison: side-by-side alternatives carry no arrows
        self.assertEqual(arrow_segments(_spec("comparison", ["For", "Against"])), [])

        # cycle: a closed loop — every node is both a source and a target
        segs = arrow_segments(_spec("cycle", ["A", "B", "C"]))
        self.assertEqual(len(segs), 3)


class TestRender(unittest.TestCase):
    def test_deterministic(self):
        spec = _spec("flow", ["Cause", "Effect", "Outcome"])
        self.assertEqual(render_svg(spec), render_svg(spec))

    def test_real_text_labels_not_paths(self):
        spec = _spec("tree", ["Root idea", "Child A", "Child B"])
        svg = render_svg(spec)
        self.assertIn("<text", svg)
        self.assertEqual(svg.count("<text"), 3)  # one real <text> per node
        # the label text survives verbatim as text content (verifier-parseable),
        # so it is never baked into a path `d` attribute.
        for label in ("Root idea", "Child A", "Child B"):
            self.assertIn(f">{label}</text>", svg)

    def test_shapes_render(self):
        spec = {
            "template": "flow",
            "nodes": [
                {"label": "Input", "shape": "ellipse"},
                {"label": "Decide?", "shape": "diamond"},
                {"label": "Output", "shape": "rectangle"},
            ],
        }
        svg = render_svg(spec)
        self.assertIn("<svg", svg)
        self.assertIn("viewBox", svg)
        self.assertEqual(svg.count("<text"), 3)   # one real label per node
        self.assertGreater(svg.count("<path"), 0)  # shapes + arrows drawn as rough paths


if __name__ == "__main__":
    unittest.main()
