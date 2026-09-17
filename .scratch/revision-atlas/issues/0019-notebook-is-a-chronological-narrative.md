# 0019 — The notebook is a chronological narrative, not a typed collection

- **Blocked by:** — (independent of the course layer)
- **Blocks:** —
- **Status:** OPEN — decided in adr/0007; SPEC §8/§9 and the glossary updated

## The gap

The notebook was ordered by function (recall → diagrams → self-test → source-audit
"Bibliography"), which (a) lost the source's document chronology, and (b) had no
page for prose at all — prose was captured as coverage-only claims and never
rendered. A prose-only section therefore produced an empty notebook while passing
every gate. See adr/0007.

## Missing

1. **Enumerate prose deterministically.** `_source_items` enumerates bullets,
   collapsibles, mermaid — add prose paragraphs as a block kind, in source order.
   A prose-only section must become a leaf (its prose is a checklist item).
2. **Reorder `_pages`**: cover → **narrative** (document order) → **revision spread**
   (recall → self-test → diagrams) → **source audit** (raw verbatim, collapsed) →
   back cover.
3. **Render the narrative compacted.** The semantic pass produces the compacted
   (paraphrased) narrative per block, not coverage-only claims; the notebook renders
   it in document order. A missing pass falls back to verbatim, and the audit still
   holds the raw.
4. **Source audit** becomes the raw-verbatim appendix (renamed from "Bibliography").
5. **Coverage** checks each enumerated block (prose + bullets + collapsibles +
   mermaid) survived the compaction in the narrative.

## Acceptance

- `04-context-engineering-1` (pure prose) builds a notebook whose pages carry the
  prose in document order — no empty notebook.
- A prose-only section is a leaf (non-empty checklist) and is counted in coverage.
- Page order in any notebook is narrative first, aids after, audit last; the
  revision spread is never interleaved with the narrative.

## Evidence required

Build a prose-only module and confirm: non-empty checklist, prose blocks enumerated,
notebook pages in narrative → aids → audit order, coverage passes. Re-run the two
fixture courses end-to-end.
