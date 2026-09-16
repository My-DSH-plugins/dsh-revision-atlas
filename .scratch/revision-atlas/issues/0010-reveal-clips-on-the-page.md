# 0010 — A long reveal is clipped by the page

- **Blocked by:** 0006 (notebook), the recall pass
- **Blocks:** —
- **Status:** OPEN — measured; fix not chosen

## The defect

The self-test page is a fixed ruled page: 520 × 680 px, padding 151 px, so the
**content box is 529 px** and `.page` clips with `overflow: hidden`. The reveal
lives in a `<details>` that is closed by default, so the page looks right — and
the moment a learner clicks **Reveal answer**, the answer is cut off with no
scrollbar and no sign that anything is missing.

Measured on the M5 build (all 20 self-test pages, headless Chromium, Kalam loaded
and the page box set exactly as StPageFlip sizes it):

| state | pages clipping | worst ratio |
|---|---|---|
| collapsed (default) | **0 / 20** | 1.00 |
| reveal expanded | **20 / 20** | **5.14** |

Worst offenders: `leaf-012` 2720 px in 529 px (5.14×), `leaf-010` 4.17×,
`leaf-019` 3.57×, `leaf-007` / `leaf-013` / `leaf-018` 2.96×. The three smallest
still overflow by ~15 px.

This is the project's own forbidden failure mode: content silently dropped. The
source audit already paginates (`_chunk_source`) precisely so nothing is lost —
the reveal is the one block that can grow without bound and the one block that
does not.

## Root cause — two, and they compound

1. **The recall pass puts no bound on `reveal`.** The instruction calls it "the
   model answer … the compact structure the learner should have reproduced", but
   no length is stated, and this run produced reveals up to 549 words / 3293
   characters. `recall` (≤60 words) is bounded; `reveal` is not.
2. **The notebook has no overflow strategy for a page whose content is agent-written.**
   Anything longer than ~16 ruled lines is clipped.

Fixing only (1) leaves the invariant to the agent's restraint; fixing only (2)
prints an essay where a hook was wanted. Both are worth doing.

## Options

- **A. Paginate the reveal** (recommended) — continue the page metaphor: a long
  reveal spills onto as many self-test pages as it needs, exactly as the source
  audit does. Consistent with "a page is filled the way a hand fills it", and
  nothing is lost at any length. Changes a leaf's page count.
- **B. Make the reveal scroll inside the page** — smallest change; breaks the
  physical-page reading (a page that scrolls is not a page), and needs a visible
  affordance or it is still invisible clipping.
- **C. Constrain the pass only** — add a word budget to the reveal in
  `recall-pass.md`. Cheap, keeps pages honest, but cannot guarantee the invariant
  against an over-producing agent.

Not chosen yet — this is a notebook design decision, not a bug fix with one
obvious shape.

## Reproduce

```bash
PYTHONPATH=src python3 -m revision_atlas.build <M5> --mindmaps /tmp/out \
  --semantic semantic-pass.json --recall recall-pass.json
# then load a leaf's notebook, open every <details>, and compare
# .page scrollHeight against clientHeight - padding
```
