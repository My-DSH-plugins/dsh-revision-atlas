# Revision Atlas

The design context for the **Revision Atlas**: a regenerable, offline-capable,
navigable mind-map view over a course's markdown, with compacted revision
artifacts at the leaves. This glossary holds the words the design documents
(ADR and SPEC) use, so a term means one thing everywhere.

## Language

**Atlas**:
The whole artifact set for one course: one fused course map, the course index,
and the leaf notebooks/diagrams under each module.
_Avoid_: mind map app, site, viewer

**Course**:
The level above a module — the directory that *contains* the modules. A course is
recognised by **structure, never by the word `modules/`**: it holds a modules
directory, which is "a directory whose children are directories each containing a
README". Beside that directory a course typically carries a `syllabus.md` and
other files, which are not themselves modules.

A course has a **name** and an **order**, both derived, never invented:

- *Name* — the syllabus's `**Course title:**` field, else the course directory's
  own name.
- *Order* — the syllabus's sequential `M# · Title` headings, else the numeric
  prefix on each module name, else an arbitrary order that the human approves
  before any module is built.

One course renders as **one fused course map** — `mindmaps/index.html`, course
root → one subtree per module → leaves, with `<module>--<leaf-id>` namespacing so
two modules' identical headings cannot collide — plus the course index
(`mindmaps/atlas.json`). A course is what `build-course-map` builds; a single
module is what `build-module-map` builds.
_Avoid_: repo, folder, subject, textbook

**Module**:
A unit of study — a directory containing one README plus zero or more sidecar
markdown files.
_Avoid_: chapter, lesson

**Corpus**:
The set of markdown files a module map must account for: its README and every
sidecar reachable from it.
_Avoid_: source tree, content

**Leaf**:
A node that *owns content* — a narrative (prose and items in its source range),
a recall block, a self-test or a diagram — and therefore gets a notebook. A
heading owns its intro range even when it has children, so a node can carry a
narrative and still be a **parent**: a module root whose range is only its own
heading is not a leaf.
_Avoid_: note, card, section, terminal node

**Leaf id**:
A leaf's unique, heading-derived identity: the source-anchor fragment, the
artifact directory (`leaves/<leaf-id>/`), and the key every agent pass maps by.
A function of the heading, never of the leaf's position — an index re-points every
link below an inserted section.
_Avoid_: leaf number, index, slug

**Narrative**:
A leaf's faithful mirror of its source range, in **document order**: prose
paragraphs, bullets, collapsibles and mermaid, **compacted** (paraphrased — never
verbatim transcription). The primary content of the notebook.
_Avoid_: body, transcript, summary

**Revision spread**:
The generated revision aids of a leaf — recall block, self-test, diagrams —
rendered as a trailing section **after** the narrative, never interleaved with it.
_Avoid_: aids section, practice section

**Recall block**:
A leaf's memory hooks: 3–5 bullets, ≤60 words total. Part of the revision spread.
_Avoid_: summary, abstract

**Checklist**:
The machine contract of what a leaf must preserve: the deterministically
enumerated blocks (prose, bullets, collapsibles, mermaid) plus the agent's
compacted claims. Coverage, Gate 2 and staleness key off it — it is never a page.
_Avoid_: coverage list, outline, page

**Source audit**:
The raw-verbatim appendix at the back of a notebook, listing the original
bullets/collapsibles/mermaid so a reader can check the compacted narrative against
the source. Collapsed, not the primary content.
_Avoid_: raw block, dump, bibliography

**Notebook**:
A leaf's paged, flip-interaction surface: the **narrative** (document order),
then the **revision spread**, then the **source audit**. Page order mirrors the
source, not the stage.
_Avoid_: notes page, sheet

**Nested sheet**:
The finer-ruled page inside a self-test page that holds the reveal, with its own
pager. It exists because the reveal is the one unbounded block in a leaf: the
outer page keeps a fixed page budget, and the answer is conserved beside it at
any length.
_Avoid_: inner page, sub-page, overlay

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
The machine index for one course — `mindmaps/atlas.json`: the course name, its
`repo`, and the ordered modules (each with id, title, readme, and its anchor into
the fused map). Data, not a map: the *map* is the fused course map.
_Avoid_: landing map, root map, TOC

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

**Approval**:
A human's recorded decision on a gate, fingerprinted to the plan it reviewed — so it
survives rebuilding an unchanged plan and lapses when that plan or its source changes.
Not a flag on a file: the reviewed content *is* the approval's subject.
_Avoid_: sign-off, status flag, approved marker

**Links**:
The verification axis that asks whether every `href` in the map and in every
notebook *resolves* from the file that carries it. A link inside the artifact tree
is a build promise (a break is a failure); a link out to the module markdown is a
deployment fact (ship beside the source, or it is `needs-review`). Resolution only
— a fragment is a jump target, not a resource.
_Avoid_: anchors, references
