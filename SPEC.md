# Revision Atlas — Spec (skeleton)

> Status: draft · agreed decisions recorded, not yet ticket-level
> Glossary: see [CONTEXT.md](./CONTEXT.md) · Decision record: [adr/0001](./adr/0001-coverage-invariant.md)

## 1. Purpose and success criteria

A **Revision Atlas** turns a course's markdown into a navigable, offline-capable
revision surface: a course index of modules, one mind map per module (faithful
to the source structure), and — at every terminal branch — a compacted leaf
(recall block + one diagram — hand-drawn by default, mermaid where exactness
matters — + paged notebook + self-test prompt + source audit), with every node
linking back to its source.

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
│           └── leaf   (recall + diagram + notebook + self-test + source)
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

### 4.2 Module plan — `mindmaps/<module>/plan.md` (human source)

The plan is **drafted by the agent, approved by the human** — a human may
hand-edit it, but never writes it from scratch. Headings are the tree (breadth);
the bullets under a leaf are its checklist (depth). Inline annotations carry the
few fields a human *decides* (`· kind: …`, `· diagram: …`), which the agent
proposes and the human approves or corrects; everything else — ids, `sources`,
anchors, `evidence`, hashes, canonical-source dedupe — is computed and emitted
into the derived `spec.yml`.

```markdown
# Plan — 02-model-failure-science · status: proposed

## Coverage: 8 H2 · 10 H3 · 12 collapsibles · 0 unclassified

## The failure classes
### 1. Hallucination & confabulation · diagram: handdrawn
- definition paragraph
- <details>: each collapsible example, by name
### Instruction drift vs. position bias · kind: debate-pair
- for: 04-instruction-drift-vs-05-position-bias-for.md
- against: 04-instruction-drift-vs-05-position-bias-against.md
- decision: ## The decision
```

The derived `spec.yml` is the machine form of this same graph — `kind`, typed
edges (`branches`, `canonical`), and per-node `sources`/`evidence`/`content_hash`
attached — with the leaf shape shown in §4.3. Humans do not read or edit it.

### 4.3 Derived spec — leaf shape (`spec.yml`, generated, not hand-edited)

```yaml
leaf:
  id: m2-c1
  sources: [{ file: "README.md", anchor: "#1-hallucination--confabulation" }]
  checklist:              # enumerated source items that MUST survive
    - "Definition paragraph"
    - "<details>: <name of collapsible example>"
  prompt: "…"             # self-test question (agent-generated, stored, reviewable)
  recall: ["hook", "hook"]  # 3-5 bullets, <=60 words
  reveal: "…"             # answer/structure shown on reveal
  diagram:                # ONE diagram slot; kind chosen by content (§8)
    kind: handdrawn       # handdrawn | mermaid | none
    art: "m2-c1.svg"      # the drawing (hand-drawn, or rendered mermaid)
    src: null             # .mmd source, only when kind == mermaid
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
2. **Plan as contract** (human-approved, before generation): the module plan is
   drafted by the agent as a **human-readable `plan.md`** — headings are the tree, bullets
   are each leaf's checklist — and approved in a **plan stage** with two human
   gates: (a) the **structure plan** (the full heading tree; coverage verified
   against the README and every connected markdown), and (b) the **leaf plan**
   (each leaf's `checklist`, its content captured to the fullest). A
   deterministic script derives `spec.yml` (ids, `sources`, `evidence`, hashes —
   nothing a human must write) from the approved `plan.md`. No artifact is
   generated until the plan is frozen; a leaf without a verified checklist is
   `needs-review`.
3. **Checklist-fed generation**: the per-leaf prompt carries the exhaustiveness
   bar — "cover every checklist item, or mark it out-of-scope". The model never
   decides what content exists.
4. **Verification** (two axes): (a) **coverage** — a deterministic parser
   re-opens each generated artifact and asserts every checklist item is present
   by slug; below threshold → `needs-review` + a red marker, so silent omission
   is impossible. (b) **adherence** — an LLM critic (separate pass, fresh
   context) re-reads each leaf against its checklist + source and flags *drift*
   (content that names an item but misstates it), plus a deterministic grounding
   check that each claim traces to a real source anchor; drift → `needs-review`.
   Adherence reads the **text** artifact — the notebook is HTML and diagrams are
   SVG with real `<text>` labels, never a raster — so the critic is an ordinary
   text pass, not a VLM; any PNG export is display-only, never the verification
   surface. Post-generation human review is exception-based — only `needs-review`
   items (and, for v1, diagram exactness) — never a whole-map re-read; coverage
   was already decided at the plan gates.

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

- **Budgets**: recall block 3–5 bullets ≤60 words; notebook pages by checklist
  size (§9); exactly **one diagram slot per leaf** — never two drawings of the
  same structure.
- **Diagram — content-driven, not a blanket rule**:
  - default `kind: handdrawn` — a hand-drawn flowchart/sketch in the notebook's
    visual language (memory + coherent look);
  - `kind: mermaid` only when (a) the source already contains a ` ```mermaid `
    block — extract and render, near-zero cost — or (b) the content is a decision
    procedure / state machine / multi-branch sequence whose exact branching
    matters. Storage: `.mmd` source (diffable) rendered to SVG at build time
    (adr/0002);
  - `kind: none` for leaves with nothing structural worth drawing.
  - v1: a diagram's exact branching is **human-reviewed**, not machine-checked;
    the verifier asserts label presence only.
- **Hand-drawn art**: SVG with real `<text>` labels — never text→paths, because
  the adherence verifier reads the labels. The handwriting font is embedded as a
  subset (base64 `@font-face`) so it survives offline and re-theming.
- **Self-test**: `prompt`/`reveal` authored at generation, stored in `plan.md` so
  they don't churn and can be hand-edited.
- **Source node**: the collapsed audit bullets live in the map; it is the
  one-click audit surface for leaf-vs-source.
- **Adherence**: generation is verified for more than presence — the critic +
  grounding pass in §6.4 checks that each checklist item is captured faithfully,
  not merely named.

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
- **Vendored look, not a skill dependency**: the handwriting look and hand-drawn
  style are borrowed by copying the template + font + sketch assets into
  `mindmaps/assets/`; the atlas never invokes the `handwritten-notes` /
  `hand-drawn-diagrams` skills at generation time. It borrows the *aesthetics*,
  not the *contract* — its checklist-fed, paged, verified pipeline is its own.
- **Offline**: a leaf notebook works offline exactly like the module map;
  notebooks are leaf-scoped, never course-scoped.

## 10. Rendering

- **Renderer**: markmap v1, behind a seam — the plan (`plan.md` → derived `spec.yml`) is renderer-agnostic.
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
| `build-course-map` | user-invoked | heavy, batched: extract → plan (2 gates) → generate |
| `refresh-stale-leaves` | model-invoked | hash mismatch / "the source changed" / "refresh the atlas" |

`refresh-stale-leaves` is model-invoked so the agent can reach it when it
*notices* staleness; `build-course-map` stays human-gated (expensive, batched).
The skill lives globally (`~/.dsh/skills/revision-atlas/`); artifacts live in
each course repo's `mindmaps/`.

The **plan (`plan.md`, with its derived `spec.yml`) is the common artifact both
skills share** — the router routes by intent and state, not by duplicating the
plan: no plan yet → build (create the plan, both gates, full generate); plan
exists → refresh (diff source against the plan's content hashes). A refresh that
only re-renders an unchanged leaf needs no gate; a refresh that changes
**structure** (a new or removed section or linked file) or a **checklist**
(edited content) re-enters the corresponding human gate for exactly the affected
part — the plan can never change silently.

## 13. Directory layout (in each course repo)

```
mindmaps/
├── atlas.yml
├── assets/               # font(s), flip JS, theme CSS
├── og/                   # PNG thumbnails
└── <module-slug>/
    ├── plan.md            # human source of truth (approved)
    ├── spec.yml           # derived machine contract (generated)
    ├── index.html        # self-contained module map
    └── leaves/<leaf-id>/
        ├── notebook.html
        ├── diagram.svg   # hand-drawn, or rendered mermaid
        └── diagram.mmd   # only when kind == mermaid
```

## 14. Verification & coverage report

`build-course-map` ends by printing, per module: file inventory status; per-leaf
checklist coverage; per-leaf adherence (drift flags from the critic + grounding
misses); broken anchors; offline-purity (no external load-bearing refs in maps);
notebook page count vs budget; `needs-review` count. Any unclassified file or
coverage miss is a **failure**, not a warning.

## 15. Milestones (tracer bullets) and open questions

1. Extractor: inventory + link graph + classification ladder + closure check.
2. Structure plan: full `plan.md` node graph (headings + kinds + diagram hints).
   **Gate 1 — human approves coverage** (every H2/H3/H4, collapsible, mermaid
   block, and linked markdown accounted for). Script derives `spec.yml`.
3. Leaf plan: per-leaf `checklist` drafted from the section content.
   **Gate 2 — human approves checklists** (information captured to the fullest).
4. Renderer: course index + module map (markmap, inline diagrams) — runs against
   the frozen plan.
5. Leaf generator: diagram (hand-drawn/mermaid per §8) + recall/prompt/reveal +
   source node — runs against the frozen checklist.
6. Notebook generator: paged flip template + shared assets.
7. Verifier: coverage (deterministic) + adherence (grounding + LLM critic) + report; post-gen human review is exception-only.

Open: OG-image pipeline; the eventual publish step into the portfolio repo;
whether `needs-review` blocks or merely annotates in v1; the classifier that
assigns each leaf's diagram kind (handdrawn vs mermaid vs none); whether the two
plan gates are one combined approval step or two separate ones.
