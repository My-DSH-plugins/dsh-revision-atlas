# Hand-drawn diagram geometry is guaranteed by a deterministic layout invariant — not by agent coordinates or a vision pass

---
Status: accepted
---

Every hand-drawn leaf diagram must look right in a way the learner can trust:
boxes must not overlap, labels must fit their boxes, arrows must flow one
direction, positions must align. Three candidate owners for that guarantee were
considered and the first two rejected:

- **An LLM choosing coordinates** gives no guarantee — a model is bad at
  geometry, will happily place overlapping boxes or a 40-character label in a
  30-px box, and will not know it did. Asking it to "place these without
  overlapping" is exactly the unreliability the atlas exists to remove.
- **A VLM checking the render afterwards** gives no guarantee either — it is a
  stochastic *report* of what it sees, can miss a 2-px overlap or a tight label,
  disagrees with itself across runs, and answers a question code answers with
  certainty. It is also unavailable on the build machine (the agent model here
  has no image input).

Overlap, alignment, orientation, and label-fit are **geometric**, not semantic:
they are computable from `(x, y, width, height)` and text width. So the
guarantee belongs to deterministic code, by construction, not to any model's
eyes.

## Decision

Split content from geometry, and fix the geometry as an **invariant**:

- **The agent supplies topology only** — which concepts become nodes, which
  arrows connect them, the 1–5-word labels, and which layout shape the content
  is (`flow` / `tree` / `cycle` / `comparison`). This is semantic, Gate-2-gated,
  reviewed in `plan.md` like recall/prompt/reveal. The agent never emits pixel
  coordinates.
- **Deterministic code supplies geometry** — a template layout computes
  positions; the following invariant is guaranteed on the output and is
  machine-checkable:

  1. **No overlap** — box spacing exceeds the sketch's jitter amplitude, so even
     a wobbly hand-drawn border cannot touch a neighbor.
  2. **Label fit** — each box is sized from a conservative per-character text
     width (overestimate, never underestimate), so a label cannot overflow.
  3. **Orientation** — arrows flow one direction (down or right, per template).
  4. **Alignment** — positions sit on a regular grid with constant gaps.

The invariant is the contract; the algorithm is swappable. The current
algorithm is fixed templates (each collision-free by construction); a layered
or force-directed layout may replace it later **only if** it still upholds the
same invariant, which the verifier asserts on the output regardless of which
algorithm produced it.

## Consequences

- A VLM has **no role in the guarantee path**. If one is ever used, it is
  exception-only, for the *subjective* "does this look pleasant" question —
  never for overlap/alignment, which code already proves.
- The verifier (0007) asserts the invariant against every rendered diagram; a
  violation is a build failure, not a warning.
- The cost: the template set is deliberately small (four shapes). If real leaves
  need a shape the templates cannot express, the topology is wrong or a new
  template is added — the invariant does not bend.

## When to revisit

- If the four templates prove too rigid (real leaves repeatedly need layouts
  they cannot express), add a general layered/force-directed layout **under the
  same invariant**, not a looser one.
- If a vision model becomes cheap *and* we want subjective aesthetic QA, add it
  as an exception-only critic — still never as the overlap/alignment guarantee.
- If the conservative text-width estimate turns out to clip an exotic glyph,
  tighten the per-character bound (a one-line change) rather than introducing a
  model into the path.
