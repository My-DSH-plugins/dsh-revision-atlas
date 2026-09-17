# The notebook is a chronological narrative, not a typed collection

---

Status: accepted

---

The notebook was organized **by function**: recall → diagrams → self-test →
source-audit ("Bibliography"). That grouping lost the source's **document
chronology** — a section's content is prose interleaved with bullets, collapsibles
and sub-headings, in the author's order — and it had **no page for prose at all**.
Prose was captured only as coverage-checked "claims" and never rendered, so a
prose-only section produced an empty notebook while passing every machine gate.

That is the "nothing silently dropped" invariant violated by construction, not by
accident: the page plan had no slot where prose could appear.

## Decision

The leaf's notebook is a **chronological narrative** of the section's content:

- **Narrative** — the source content (prose paragraphs, bullets, collapsibles,
  mermaid) in **document order**, **compacted** by the agent (paraphrased, faithful
  in meaning and order, never verbatim transcription).
- **Prose is enumerated deterministically**, the same way bullets/collapsibles/mermaid
  already are, so a dropped prose block is a coverage miss — closing the
  prose-only-empty-notebook hole.
- **Generated aids** (recall, self-test, diagrams) form a trailing **revision
  spread**, appended *after* the narrative — never interleaved with the source's
  chronology, which they are not part of.
- **Source audit** (raw verbatim) survives as a collapsed appendix at the back, so a
  reader can check the *compacted* narrative against the *original*.
- **Checklist** is the machine contract (coverage, Gate 2, staleness) — never a page.

Page order: cover → narrative → revision spread → source audit → back cover.

## Consequences

- `owns_content` now includes "the narrative is non-empty" — a prose-only section is
  a leaf, because its prose is enumerated deterministically.
- The extractor enumerates prose paragraphs (a new block kind) in addition to
  bullets/collapsibles/mermaid, in source order.
- The semantic pass's job narrows to **compacting** the enumerated prose (paraphrase),
  not being the only thing that captures it. A missing or empty pass can no longer
  silently drop prose: the enumeration still requires it, and the verbatim fallback
  is the audit.
- Coverage checks each enumerated block survived the compaction; the critic checks
  the paraphrase didn't drift.

## When to revisit

- If verbatim fallback turns out to be the norm (agents consistently refuse to
  compact), the split between "enumerate" and "compact" may be one step too many —
  consider compacting in the deterministic pass instead.
- If the revision spread grows (more generated aid kinds), decide whether it stays
  one trailing section or becomes a named back-matter sequence.
