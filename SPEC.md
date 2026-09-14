# Revision Atlas — Spec (skeleton)

> Status: draft · agreed decisions recorded, not yet ticket-level
> Glossary: see [CONTEXT.md](./CONTEXT.md) · Decision record: [adr/0001](./adr/0001-coverage-invariant.md)

## 1. Purpose and success criteria

A **Revision Atlas** turns a course's markdown into a navigable, offline-capable
revision surface: a course index of modules, one mind map per module (faithful
to the source structure), and — at every terminal branch — a compacted leaf
(recall block + mermaid + sketch + paged notebook + self-test prompt + source
audit), with every node linking back to its source.

**Acceptance test.** The same generic skill, with no per-course tuning, produces
closure-passing, verification-passing atlases for two different module species:

- `ML-Engineer/modules/05-data-engineering-2/` — a monolith README (1710 lines,
  6 embedded mermaid blocks, deep H2/H3/H4 tree);
- `GenAI_notes/Harness Engineering/modules/02-model-failure-science/` — a hub
  README (331 lines) plus 11 sidecars: debate pairs, a framework×domain matrix,
  an aggregator with its own TOC, 12 collapsible catalog entries, zero mermaid.

Both open offline on a phone and look portfolio-ready.

## 2. Non-goals (v1)

- No CI; build runs manually through the skill.
- No editing *through* the map — the markdown stays the source of truth; the
  atlas is a derived, regenerable artifact.
- No cross-course single app yet; two courses = two atlases linked from the
  portfolio.
- No PDF/print pipeline.

## 3. Product model

```
course atlas
├── course index map   (title = course name; nodes = modules)
│     └── module map   (faithful to source; nodes = H2/H3/… and typed sidecar edges)
│           └── leaf   (recall + mermaid + sketch + notebook + self-test + source)
```

The **map** is the index into memory; the **leaf** is the memory itself; the
**notebook** is the depth layer. The map stays scannable at full zoom-out; the
leaf is one screen; the notebook is one tap deeper.

## 4. Data model

### 4.1 Course index — `mindmaps/atlas.yml`

```yaml
course: "Machine Learning Engineering"
repo: "ML-Engineer"
modules:
  - id: 05-data-engineering-2
    title: "Data Engineering II — Quality & Validation"
    readme: "modules/05-data-engineering-2/README.md"
    map: "mindmaps/05-data-engineering-2/index.html"
```

### 4.2 Module spec — `mindmaps/<module>/spec.yml`

```yaml
module: 02-model-failure-science
nodes:
  - id: m2
    kind: module
    title: "Model Failure Science"
    sources: [{ file: "README.md", anchor: "#m2-model-failure-science" }]
  - id: m2-failure-classes
    kind: section
    title: "The failure classes"
    sources: [{ file: "README.md", anchor: "#the-failure-classes" }]
    children: [m2-c1, m2-c2]           # nine classes, all in parallel
  - id: m2-drift-vs-position          # debate pair -> one node, two branches
    kind: debate-pair
    question: "Are instruction drift and position bias one failure?"
    branches:
      for: { file: "04-instruction-drift-vs-05-position-bias-for.md" }
      against: { file: "04-instruction-drift-vs-05-position-bias-against.md" }
    decision: { file: "04-...-against.md", anchor: "#the-decision" }
    evidence: [{ file: "README.md", line: 122 }]   # the link that proved the edge
  - id: m2-task-state
    kind: framework-matrix
    children: [healthcare, finance, legal, sre, cross-domain]  # 5 domains
    canonical: "task-state-across-domains.md"     # aggregator = canonical source
```

Every node carries `sources[]` (file + anchor) and, for typed edges,
`evidence` (the link line). `kind` is always a value from the relationship
table (§6), never a free string.

### 4.3 Leaf schema

```yaml
leaf:
  id: m2-c1
  sources: [{ file: "README.md", anchor: "#1-hallucination--confabulation" }]
  checklist:              # enumerated source items that MUST survive
    - "Definition paragraph"
    - "<details>: <name of collapsible example>"
  prompt: "…"             # self-test question (authored, stored, reviewable)
  recall: ["hook", "hook"]  # 3-5 bullets, <=60 words
  reveal: "…"             # answer/structure shown on reveal
  mermaid: "m2-c1.mmd"    # extracted OR generated (see §8)
  sketch: "m2-c1-sketch.svg"
  notebook: "leaves/m2-c1/notebook.html"
  source: "…"             # collapsed audit bullets
  status: draft | needs-review | verified
  content_hash: "sha256"  # of sources + checklist; staleness key
```

## 5. Relationship kinds

| kind | meaning | evidence |
|---|---|---|
| `section` | heading inside a file | heading token + line |
| `sidecar` | standalone doc linked from a section | the link line |
| `debate-pair` | for/against sidecars on one question | filename + link |
| `framework-matrix` | one framework × N domains | filename/heading pattern |
| `aggregator` | file that embeds its siblings | own TOC / duplicate headings |
| `catalog` | a list of collapsible examples | `<details>` runs |
| `sequence` | numbered progression | `## 1. … ## 2. …` |
| `shared` | cited by ≥2 modules | link count ≥2 |

## 6. Assurance (four parts) — the invariant, see ADR-0001

1. **Inventory closure** (deterministic script): build the file inventory and
   link graph; every `.md` is `classified` / `ignored` / `needs-review`; an
   unaccounted file **fails the build**. `handwrittenNotes/`, `scratch/` and
   similar noise dirs are ignored by an explicit rule, not by default.
2. **Spec as contract** (human-reviewed): the module `spec.yml` above; every
   leaf carries a `checklist` derived from the real content. A leaf with no
   verified checklist is `needs-review`.
3. **Checklist-fed generation**: the per-leaf prompt carries the exhaustiveness
   bar — "cover every checklist item, or mark it out-of-scope". The model never
   decides what content exists.
4. **Verification** (deterministic parser): re-open each generated artifact,
   assert every checklist item is present (by slug), report coverage %; below
   threshold → `needs-review` + a red marker. Silent omission is impossible.

## 7. Extraction rules (script, no LLM)

- Heading rank → depth; siblings of the same rank render in parallel (faithful).
- README links to relative `.md` are **authored evidence**, taken as-is.
- Classification ladder, most-specific first: link graph → filename convention
  (`X-vs-Y-{for,against}`, `task-state-<domain>`, numeric prefixes) → structure
  (own TOC ⇒ aggregator; ends `## The decision` ⇒ debate member) → content
  signals. **LLM only classifies the residue, and the residue is flagged.**
- Canonical-source rule: the aggregator owns the content once; embedded copies
  are referenced, not duplicated.
- Every node records `evidence` (the line that justifies its edge).

## 8. Leaf generation contract

- **Budgets**: recall block 3–5 bullets ≤60 words; mermaid = structure /
  sequence / decisions; sketch = intuition / mental model (no duplicates);
  notebook pages by checklist size (§9).
- **Mermaid**: extract the existing ` ```mermaid ` block when present; when
  absent (Harness M2), generate one from the checklist. Storage: `.mmd` source
  (diffable) rendered to SVG at build time.
- **Sketch**: hand-drawn style, SVG, font subset embedded or text→paths so it
  survives offline and re-theming.
- **Self-test**: `prompt`/`reveal` authored at generation, stored in the spec so
  they don't churn and can be hand-edited.
- **Source node**: the collapsed audit bullets live in the map; it is the
  one-click audit surface for leaf-vs-source.

## 9. Notebook model (replaces single-page notes)

- **Leaf → a notebook of N pages**, not one sheet; page count = f(checklist
  size), roughly one topic-block per page, one chart per page, one "remember"
  spread per leaf.
- **Flip interaction**: touch drag/swipe with hard/soft cover feel; candidate
  StPageFlip (vanilla, offline, mobile); hand-rolled CSS 3D as fallback.
- **Pages are HTML fragments**, not raster images — so they stay crisp at any
  zoom, the verifier can parse them, and size stays small.
- **Shared assets**: one handwriting font + flip JS + theme per module under
  `mindmaps/assets/`, referenced (not inlined) by pages, cached once offline.
- **Offline**: a leaf notebook works offline exactly like the module map;
  notebooks are leaf-scoped, never course-scoped.

## 10. Rendering

- **Renderer**: markmap v1, behind a seam — the `spec.yml` is renderer-agnostic.
- Documented markmap workarounds (from the demo): `data:` image URIs are refused
  at markdown level → diagrams are injected into the tree JSON as base64 after
  transform; images survive only as image-only list items or standalone image
  nodes; bullets become child nodes.
- **SVG-first** for all diagrams; PNG reserved for raster-only textures and
  Open-Graph thumbnails (`mindmaps/og/<module>.png`).

## 11. Offline & packaging

- **Layer 1** — module map is a single self-contained HTML with inline diagrams
  (proven, ~350 KB). Guaranteed offline, zero infra.
- **Layer 2** — PWA precache: per-module "download for offline" prefetches all
  leaf notebooks (never-opened leaves included), shared assets cached once.
- **Layer 3** — "revision pack": a per-module single file with notebooks inlined,
  for the no-signal-at-all case.
- Publishing: project Pages per course repo; `.nojekyll` at the published root;
  portfolio (`akshaydev17.github.io`) links to each atlas (or, later, vendors the
  output under `/atlas/<course>/` for one design + one service worker).

## 12. Skill interface

| skill | invocation | triggers |
|---|---|---|
| `revision-atlas` (router) | user-invoked | names the two below; zero context load |
| `build-course-map` | user-invoked | heavy, batched: extract → spec → artifacts |
| `refresh-stale-leaves` | model-invoked | hash mismatch / "the source changed" / "refresh the atlas" |

`refresh-stale-leaves` is model-invoked so the agent can reach it when it
*notices* staleness; `build-course-map` stays human-gated (expensive, batched).
The skill lives globally (`~/.dsh/skills/revision-atlas/`); artifacts live in
each course repo's `mindmaps/`.

## 13. Directory layout (in each course repo)

```
mindmaps/
├── atlas.yml
├── assets/               # font(s), flip JS, theme CSS
├── og/                   # PNG thumbnails
└── <module-slug>/
    ├── spec.yml
    ├── index.html        # self-contained module map
    └── leaves/<leaf-id>/
        ├── notebook.html
        ├── *.mmd         # mermaid source
        ├── mermaid.svg
        └── sketch.svg
```

## 14. Verification & coverage report

`build-course-map` ends by printing, per module: file inventory status; per-leaf
checklist coverage; broken anchors; offline-purity (no external load-bearing
refs in maps); notebook page count vs budget; `needs-review` count. Any
unclassified file or coverage miss is a **failure**, not a warning.

## 15. Milestones (tracer bullets) and open questions

1. Extractor: inventory + link graph + classification ladder + closure check.
2. Spec writer: `spec.yml` + per-leaf checklist (human-reviewable).
3. Renderer: course index + module map (markmap, inline diagrams).
4. Leaf generator: mermaid + sketch + recall/prompt/reveal + source node.
5. Notebook generator: paged flip template + shared assets.
6. Verifier + coverage report.

Open: OG-image pipeline; the eventual publish step into the portfolio repo;
whether `needs-review` blocks or merely annotates in v1.
