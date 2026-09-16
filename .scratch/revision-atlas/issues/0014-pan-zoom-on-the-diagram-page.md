# 0014 — Pan/zoom on the diagram page

- **Blocked by:** 0006 (done)
- **Blocks:** —
- **Status:** OPEN — moved out of 0006, not built

## The gap

A leaf's mermaid diagram is inlined as a static SVG scaled to fit the page box
(`.page-diagram .diagram svg { max-width: 100% }`). A dense flowchart — M5 has six
of them, and the derived ones are wide — becomes unreadable at 520px with no way to
enlarge it. Every other page of the notebook is legible at page size; this one is
the exception.

## Scope

- Pointer-drag to pan and wheel/pinch to zoom the diagram **inside its page**,
  with a reset that returns to fit.
- No conflict with the flip: corner squares are the only turn zones
  (`disableFlipByClick` is already set), so the body of the page is free for the
  gesture — but the gesture must not start inside a `.turn` square.
- Must stay offline and dependency-free (no new vendored JS if avoidable).
- Touch: the notebook currently sets `mobileScrollSupport: false`; verify a drag
  pans rather than flipping.

## Acceptance

- A wide diagram can be zoomed to read its labels, and panned to reach any corner.
- The gesture does not fire a page turn, and the reset restores the fitted view.
- The page still passes the `offline-purity` and `links` verifier axes.

## Evidence required

Headless Chromium showing the transform changing on a synthesised drag/wheel, plus
a before/after screenshot of a dense diagram at page size.
