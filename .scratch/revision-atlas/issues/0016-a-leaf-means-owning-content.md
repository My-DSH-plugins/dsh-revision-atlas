# 0016 — A leaf means owning content

- **Blocked by:** —
- **Blocks:** —
- **Status:** done

## The defect

The demo map listed three leaves. The module root was one of them, and its notebook
was **two pages: a front cover and a back cover, with nothing between** — an artifact
with no content, linked from the map and counted in the report.

Cause, and it is a vocabulary mismatch rather than a coding slip:

- `LEAF_KINDS` includes `module` and `section` **on purpose**. A heading owns its
  intro range even when it has children, which is what stops intro prose from being
  silently dropped (the fix in 0003).
- But that means a checklist is attached **by kind**, and `"checklist" in node` was
  then used as the definition of "leaf" — in three places that must agree: the
  notebook generator (which nodes get artifacts), the renderer (which nodes get a
  `notebook` link), and the verifier (which nodes are checked).

So a node owning only its own heading carried an *empty* checklist, passed the
predicate, and got an empty notebook.

## Fix

`spec_writer.owns_content(node)`: a node is a leaf when it has something to compact —
a non-empty checklist, or a recall / prompt / reveal / diagrams block. Evaluated
after annotation, which is when a node's content is known. The three decision sites
now call it instead of duplicating the predicate, so the notebook set, the link set
and the verified set cannot drift apart.

A node with intro prose is still a leaf: a semantic pass compacts the intro into
claims, the checklist is non-empty, the notebook carries it. **A root is not
excluded for being a root — it is excluded for being empty.**

## Evidence

- The demo module: `Leaves: 3 → 2`, `leaves/why-the-sky-is-blue/` gone, and the map's
  root node now reads `Why the sky is blue  README.md:1` with no `notebook` link
  beside its two real leaves. Verdict still **PASS**.
- Two regression tests: a root owning only its heading has an empty checklist and is
  not a leaf; a root whose intro a pass compacted into claims is one.
- 76 tests green.
