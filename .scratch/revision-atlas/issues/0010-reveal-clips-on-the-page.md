# 0010 — A long reveal is clipped by the page

- **Blocked by:** 0006 (notebook), the recall pass
- **Blocks:** —
- **Status:** done — **frozen**: the nested sheet (option A), prototyped for review and then
  folded into `notebook.css` + `_selftest_html()`. One part is deliberately left open — the
  recall pass still has no budget for `reveal`; see the end of this file.

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

---

## Resolved — the nested sheet (frozen)

**Decision.** Option A, but built as *a page inside the page* rather than extra
sibling pages: the answer lives in a smaller, finer-ruled sheet on the self-test
page, with its own `‹ Previous · n / N · Next ›` pager at the bottom. Sibling
continuation pages were the alternative — simpler, no new state — but they grow the
leaf's page count and drop the prompt, which is the context that makes a self-test
a self-test.

Why this medium suits it, measured rather than assumed:

- The sheet is `flex: 1` inside the page's column, so the **outer page cannot
  overflow by construction** — it absorbs whatever the prompt leaves. `bounded to
  one page` is a property of the layout, not of anyone's care.
- Every dimension is a ratio of `--page-w`/`--page-h`, so the sheet holds the
  **same number of nested lines at any fitted size** (measured: 274 px usable at
  520×680 = 13.8 nested lines; 168 px at 320×418 = 13.8 nested lines). That is
  what lets the generator pick the chunk size in Python without knowing the window.
- The pager sits at the **bottom**, the one region with no turn zone (the turn
  squares are the top margin corners), so it can never be confused with a page turn.

**Implementation.** `.reveal*` rules in `notebook.css`; `_chunk_reveal()` +
`_selftest_html()` in `notebook_generator.py`; the pager JS in the notebook's own
inline script (runs before the flip, touches only its own sheet).

`_NESTED_CHARS = 56` was **swept, not guessed**: the value that fills the fuller
pages to ~86% with nothing overflowing, where 64 overflows every page. The first
two estimates (40, then 64) were both wrong in opposite directions and produced 13
half-empty pages; the constant now carries the measurement and its provenance.

**The safety net.** `.reveal-page { height: 100%; overflow-y: auto }`. The line
budget is an estimate; if a chunk ever overflows anyway — text packing worse than
the average it was charged for — that page scrolls instead of clipping. A
scrollbar inside a nested page is a blemish; losing the end of an answer is the
defect this ticket exists for.

**Evidence.**
- 550-word reveal (the real M5 worst case) → 7 nested pages, **0 of 7 overflow**,
  no JS errors, counter `1 / 7`; `next ×2 → 3 / 7` showing "Step 9", end at
  `7 / 7` with Next disabled, `prev → 6 / 7`.
- Collapsed: the sheet is genuinely not rendered (`checkVisibility() === false`) —
  and it took an explicit re-assert of the hiding, because the flex column needs an
  author `display` on the disclosure's content, which **beats the UA's own
  hide-the-content rule** in Chrome's pre-`::details-content` implementation.
  Without it the marker said "closed" while the answer stayed on the page.
- Chunking conserves every line, in order, exactly once (test).
- 8 new tests; 73 green.

## Resolved — the reveal now has a budget (500 words)

Nested paging makes the notebook *robust* to an unbounded reveal; it does not make
the reveal *good*. SPEC §8 calls `reveal` "the compact structure the learner should
have reproduced", and `recall-pass.md` bounds `recall` at ≤60 words while leaving
`reveal` unbounded — this run produced up to 549 words, which is a 7-page nested
answer where one page was wanted.

**Decided: ≤500 words.** Stated in `recall-pass.md` (with `recall`'s ≤60 beside it)
and in SPEC §8's budgets, and **asserted** by `_check_budgets` as `needs-review` — a
long reveal is faithful and merely longer than it should be, so it annotates rather
than blocks, but it is visible instead of silent. The nested sheet stays as the
guarantee that nothing is lost when a pass overshoots anyway: the budget makes one
page the norm, the pager makes several pages survivable.
