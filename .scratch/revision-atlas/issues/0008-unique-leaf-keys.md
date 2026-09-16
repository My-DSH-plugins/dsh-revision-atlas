# 0008 — Unique leaf keys (the duplicate-title collision)

- **Blocked by:** 0003, 0007
- **Blocks:** —
- **Status:** done — fixed at the keying layer, verified end-to-end on M5

## The defect

The three input passes (semantic / recall / mermaid) returned a JSON object keyed
by each leaf's **`title`**, and `_annotate_leaves` looked them up the same way.
A JSON object cannot hold the same key twice, so **two leaves with the same title
collapsed into one entry and both received the same claims.**

M5 has exactly that: two leaves titled `Deriving the baseline and thresholds.` —
README line 157 (volume-based: bucket width `w`, `λ_floor`, `n_required`) and line
767 (per-column: the estimator → SE → tolerance chain, `K = (CV/δ)²`). The cold
semantic subagent emitted ONE key with five mixed claims, so each leaf was given
half the other's content.

Nothing in the pipeline could see it. Coverage counts *mechanical* items (still
present), and the grounding floor compares a claim against its own range — and
these two ranges share the vocabulary of their section (`threshold`, `baseline`),
so a wrong claim still looks grounded. **It had to be fixed where it is
introduced, not detected afterwards.**

## Fix

1. **`spec_writer._dedupe_ids(root)`** — walk the whole tree and make ids unique,
   GitHub-style: the Nth occurrence of a bare slug gets `-1`, `-2`, … appended.
   Called in `build_structure` after sidecars are attached and before
   `_annotate_leaves`, so the id used for lookup is final.
2. **`spec_writer._lookup(data, node)`** — resolve an agent entry by `id` first,
   with a `title` fallback so older title-keyed inputs (the M2 demo, the existing
   tests) keep working.
3. The four pass instructions now say **`id`, copied verbatim — not the `title`,
   which may repeat**, and each states that `id` is the map key.

The id is also the source-anchor fragment (`renderer._anchor_html` →
`<file>#<id>`), and GitHub's own anchor disambiguation for a repeated heading in
one file is precisely `…-1`. So the fix makes the anchor *more* correct, not less:
the map now links the second leaf to `#deriving-the-baseline-and-thresholds-1`,
which is the anchor the README's own table of contents uses.

## Evidence

Cold re-run of both passes on M5 (fresh subagents, instruction + dir + spec only):

| check | result |
|---|---|
| leaf ids | 20 leaves, 20 distinct ids |
| the two colliding leaves | `deriving-the-baseline-and-thresholds`, `…-1` |
| semantic keys | 20/20 ids, no missing, no extra |
| their claims | 4 + 4, **zero overlap**; volume claims on the line-157 leaf, estimator/`K` claims on the line-767 leaf |
| recall keys | 20/20 ids; distinct prompts per leaf |
| build | **PASS**, exit 0 — 20 notebooks, coverage 65/65, grounded 75/75 |

Regression test `test_duplicate_title_leaves_get_distinct_keys` pins both halves:
distinct ids, and claims routed to the right leaf when a pass keys by id.

## Why not "key by title + line"

A line number is stable only until the source is edited, and the atlas is meant to
be regenerated. The id is already the artifact's identity (anchor fragment, and
the natural key for `refresh-stale-leaves`), so the passes key off the thing that
is already unique rather than off a display string plus a workaround.
