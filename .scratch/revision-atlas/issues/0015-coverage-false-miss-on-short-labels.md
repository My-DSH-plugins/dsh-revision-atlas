# 0015 — Coverage false-misses a collapsible with a short label

- **Blocked by:** —
- **Blocks:** —
- **Status:** OPEN — found by a synthetic fixture while closing 0006

## The defect

`_check_coverage` decides whether a collapsible is present by taking the words of
its `<summary>` and requiring them in the artifact:

```python
needed = _words(_plain(item.get("summary") or item.get("text") or ""))
if needed and _covers(words, needed):
    covered += 1
else:
    missed.append(f"collapsible “{label[:60]}”")     # ← also taken when needed == []
```

`_words()` keeps only tokens longer than two characters that are not stop words
(`len(w) > 2` and `w not in _STOP`). A summary made **entirely** of short or stop
tokens yields `needed == []`, falls through to the `else`, and is reported as a
missing item — a **false FAILURE** (exit 1) for a collapsible that is present and
correctly audited.

## Reproduce

A module README with `<details><summary>C1</summary>` (2 chars) and one mermaid
block:

```
Leaves: 2 · artifacts 2 · checklist items 2 · coverage 1/2
## FAILURES
- [coverage] Sec: checklist item not present: collapsible “C1”
```

The notebook contains the item — its source audit renders `[details] C1`. Renaming
the summary to `Collapsible one` flips the same build to **PASS** with 2/2. So the
miss is the checker's, not the artifact's.

Plausible in real material: `C1`, `Q3`, `06`, `Why?` (both tokens are stop words),
`A/B`, `2. TBD`. M5 and M2 happen to have long summaries, which is why this has not
surfaced.

## Fix direction

The item is *unverifiable by word matching*, which is not the same as *absent*.
Either:

- **fall back to a literal substring test** when `_words()` yields nothing —
  the label's raw text (case-insensitive, whitespace-normalised) must still appear
  in the artifact. Keeps a real assertion instead of weakening the axis; or
- count it separately as `needs-review` ("label too short to verify") and exclude it
  from the coverage denominator.

Prefer the first: the coverage invariant should stay a failure axis, and a literal
match is still a real check.

## Acceptance

- A collapsible with a short/stopword-only summary is correctly **found** when its
  text is present, and still **missed** when it is genuinely absent.
- The existing `len(w) > 2`/stop-word filter stays for the multi-word case (it is
  what keeps `_covers` from matching on noise).
