# Revision Atlas

The design context for the **Revision Atlas**: a regenerable, offline-capable,
navigable mind-map view over a course's markdown, with compacted revision
artifacts at the leaves. This glossary holds the words the design documents
(ADR and SPEC) use, so a term means one thing everywhere.

## Language

**Atlas**:
The whole artifact set for one course: a course index map, one module map per
module, and the leaf notebooks/diagrams under them.
_Avoid_: mind map app, site, viewer

**Module**:
A unit of study — a directory containing one README plus zero or more sidecar
markdown files.
_Avoid_: chapter, lesson

**Corpus**:
The set of markdown files a module map must account for: its README and every
sidecar reachable from it.
_Avoid_: source tree, content

**Leaf**:
The terminal node of a branch — one compacted revision unit.
_Avoid_: note, card, section

**Recall block**:
A leaf's memory hooks: 3–5 bullets, ≤60 words total.
_Avoid_: summary, abstract

**Checklist**:
The enumerated source items a leaf must preserve (sub-headings, collapsible
blocks, sidecar claims, diagrams). The generator and the verifier both key off it.
_Avoid_: coverage list, outline

**Source node**:
The collapsible audit block in a leaf that shows the original bullets, so a
reader can check the compaction against the source.
_Avoid_: raw block, dump

**Notebook**:
A leaf's notes, paginated into several pages with a flip interaction — the
replacement for a single-page notes file.
_Avoid_: notes page, sheet

**Relationship**:
A typed edge between nodes (see below). The type is extracted from evidence,
never guessed silently.
_Avoid_: link, reference

**Debate pair**:
Two sidecars arguing for and against one question; mapped as one node with two
branches and a shared decision.
_Avoid_: for/against files, opposing views

**Framework matrix**:
One framework stress-tested across several domains; mapped as one node with one
branch per domain.
_Avoid_: stress tests, domain run

**Aggregator**:
A file whose own content embeds or duplicates its siblings; it is the canonical
source and its embedded copies are referenced, not duplicated.
_Avoid_: container, umbrella doc

**Shared node**:
A document cited by two or more modules; one node referenced from every map
that cites it, not copied per module.
_Avoid_: cross-link, common file

**Course index**:
The top-level map whose nodes are the modules.
_Avoid_: landing map, root map

**Closure**:
The invariant that every corpus file is classified exactly once as
`classified`, `ignored`, or `needs-review`; enforced by a script, a build fails
on any gap.
_Avoid_: completeness, accounting

**Coverage**:
The verification axis that asks, deterministically, whether each mechanical
checklist item is *present* in the generated artifact. A miss fails the build.
_Avoid_: completeness, inclusion

**Grounding**:
The verification axis that asks, deterministically, whether a claim's leaf has a
*real source anchor* — its `file:line` exists. Structural, never a similarity
test: the deterministic axis asserts only paraphrase-invariant facts, and a
paraphrase keeps its subject terms by definition.
_Avoid_: overlap, relevance, fidelity

**Adherence**:
The verification axis that asks whether a claim is *faithful* to the source —
read by the LLM critic, which flags drift. Semantic; the critic's job, never the
deterministic axis's.
_Avoid_: accuracy, correctness, grounding
