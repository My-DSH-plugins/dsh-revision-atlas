# Revision Atlas — Spec (skeleton)

> Status: draft · agreed decisions recorded, not yet ticket-level
> Glossary: see [CONTEXT.md](./CONTEXT.md) · Decision record: [adr/0001](./adr/0001-coverage-invariant.md)

## 1. Purpose and success criteria

A **Revision Atlas** turns a course's markdown into a navigable, offline-capable
revision surface: one fused course map (the course name at the root, one faithful
subtree per module), and — at every terminal branch — a compacted leaf
(recall block + a mermaid diagram where structure matters + paged notebook +
self-test prompt + source audit), with every node
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
course atlas  (one fused map — `mindmaps/index.html`)
├── course root          (title = course name)
│     └── module subtree (faithful to source; nodes = H2/H3/… and typed sidecar edges)
│           └── leaf     (recall + diagram + notebook + self-test + source)
```

The **map** is the index into memory; the **leaf** is the memory itself; the
**notebook** is the depth layer. The map stays scannable at full zoom-out; the
leaf is one screen; the notebook is one tap deeper.

## 4. Data model

### 4.1 Course index — `mindmaps/atlas.json`

```json
{
  "course": "Machine Learning Engineering",
  "repo": "ML-Engineer",
  "index": "mindmaps/index.html",
  "modules": [
    {
      "id": "05-data-engineering-2",
      "title": "Data Engineering II — Quality & Validation",
      "readme": "modules/05-data-engineering-2/README.md",
      "anchor": "mindmaps/index.html#05-data-engineering-2"
    }
  ]
}
```

Each module's subtree lives in the one fused map; `anchor` is its entry point. Leaf
ids are namespaced `<module-id>--<leaf-id>` inside that document, so two modules
with the same heading text cannot collide.

### 4.2 Module plan — `mindmaps/<module>/plan.md` (human source)

The plan is **drafted by the agent, approved by the human** — a human may
hand-edit it, but never writes it from scratch. Headings are the tree (breadth);
the bullets under a leaf are its checklist (depth). Inline annotations carry the
few fields a human *decides* (`· kind: …`, `· diagram: …`), which the agent
proposes and the human approves or corrects; everything else — ids, `sources`,
anchors, `evidence`, hashes, canonical-source dedupe — is computed and emitted
into the derived `spec.json`.

```markdown
# Plan — 02-model-failure-science · status: proposed

## Coverage: 8 H2 · 10 H3 · 12 collapsibles · 0 unclassified

## The failure classes
### 1. Hallucination & confabulation · diagram: mermaid
- definition paragraph
- <details>: each collapsible example, by name
### Instruction drift vs. position bias · kind: debate-pair
- for: 04-instruction-drift-vs-05-position-bias-for.md
- against: 04-instruction-drift-vs-05-position-bias-against.md
- decision: ## The decision
```

The derived `spec.json` is the machine form of this same graph — `kind`, typed
edges (`branches`, `canonical`), and per-node `sources`/`evidence`/`content_hash`
attached — with the leaf shape shown in §4.3. Humans do not read or edit it.

### 4.3 Derived spec — leaf shape (`spec.json`, generated, not hand-edited)

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
  diagrams:               # mermaid, or empty — a leaf may hold an array (§8)
    - kind: mermaid
      art: "m2-c1.svg"    # rendered mermaid SVG
      src: "m2-c1.mmd"    # .mmd source (diffable)
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
   link graph. A `.md` is **in scope** when it sits *directly under the module
   path*, or when an in-scope file *links to it* and it lies *inside the module
   path* — that is the module's own narrative, and nothing else (adr/0006). Every
   in-scope `.md` is `classified` / `ignored` / `needs-review`; an unaccounted
   in-scope file **fails the build**. `handwrittenNotes/`, `scratch/` and similar
   noise dirs are ignored by an explicit rule, not by default. A `.md` that is
   inside the module but out of scope — a subdirectory's own README that nothing
   in the narrative cites — is **reported**, never failed: narrowing the scope can
   reclassify a file, it cannot lose one.
2. **Plan as contract** (human-approved, before generation): the module plan is
   drafted by the agent as a **human-readable `plan.md`** — headings are the tree, bullets
   are each leaf's checklist — and approved in a **plan stage** with two human
   gates: (a) the **structure plan** (the full heading tree; coverage verified
   against the README and every connected markdown), and (b) the **leaf plan**
   (each leaf's `checklist`, its content captured to the fullest). A
   deterministic script derives `spec.json` (ids, `sources`, `evidence`, hashes —
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
   check that each claim traces to a real source anchor — its leaf's `file:line`
    exists. **Grounding is structural, never a similarity test**: the deterministic
    axis asserts only *paraphrase-invariant* facts (structure, presence, anchors,
    and a floor-level "shares no subject term" smell), because a paraphrase is
    *supposed* to change the glue words and a similarity threshold would false-flag
    it. Semantic fidelity belongs to the critic. Drift → `needs-review`.
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

- **What a leaf is**: a node that *owns content* — a checklist item, a recall
  block, a self-test or a diagram. A heading owns its intro range even when it has
  children (that is what stops intro prose being dropped), so having a checklist is
  NOT the same as being a leaf: a module root whose range is only its own heading is
  a **parent**, and gets no notebook, no link and no place in the leaf count. One
  node owning content in exactly one place is the point.
- **Budgets**: recall block 3–5 bullets ≤60 words; **reveal ≤500 words** — the
  answer, not the chapter, and 500 is the balance between carrying the information
  and having the notebook paginate it across several nested pages; notebook pages by
  checklist size (§9); a leaf holds a **list of diagrams** — never two drawings of the
  same structure, but an array when the leaf legitimately has several.
- **Diagram — mermaid, or none** (see adr/0005, adr/0002):
  - `kind: mermaid` when (a) the source already contains a ` ```mermaid `
    block — extract and render, near-zero cost — or (b) the leaf has structure
    worth drawing (a decision procedure / state machine / multi-branch sequence /
    taxonomy / mental model), authored by the agent as `flowchart` or `mindmap`,
    Gate-2-gated. Storage: `.mmd` source (diffable) rendered to SVG at build time
    (adr/0002);
  - an empty `diagrams: []` otherwise — the deterministic default; a diagram is
    *proposed* by the agent, never assumed by the classifier.
  - v1: a diagram's exact branching is **human-reviewed**, not machine-checked;
    the verifier asserts label presence only.
- **Interactivity**: diagrams are static SVG inlined into the HTML; the notebook
  adds a small pan/zoom script so a reader can zoom/reset/click-drag offline,
  without shipping `mermaid.js` (adr/0002's size decision). PDF export is the one
  accepted loss — a dense static SVG prints illegibly.
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
- **The reveal is a page inside the page.** The self-test's answer is the one
  block of a leaf that can grow without bound, and a page is a fixed sheet of
  paper — so the answer lives in a nested, finer-ruled sheet with its own pager.
  That keeps the leaf's page budget stable and conserves the answer at any
  length. The generator chunks it into nested pages from measured line budgets,
  and the sheet scrolls rather than clipping if an estimate is ever wrong:
  nothing load-bearing may vanish silently, and a hidden answer that turns out
  half-clipped when asked for is exactly that.
- **Flip interaction**: touch drag/swipe with hard/soft cover feel; candidate
  StPageFlip (vanilla, offline, mobile); hand-rolled CSS 3D as fallback.
- **Page titles** are reader-facing, not stage names: the last pages of a leaf
  render as **Bibliography** and **Bibliography (cont. n/N)**. The stage that
  produces them is still the source audit — the title is the notebook's register,
  not the pipeline's.
- **Pages are HTML fragments**, not raster images — so they stay crisp at any
  zoom, the verifier can parse them, and size stays small.
- **Shared assets**: one handwriting font + flip JS + theme per module under
  `mindmaps/assets/`, referenced (not inlined) by pages, cached once offline.
- **Vendored look, not a skill dependency**: the notebook's handwriting look is
  borrowed by copying the template + font into `mindmaps/assets/`; the atlas
  never invokes the `handwritten-notes` skill at generation time. It borrows the
  *aesthetics*, not the *contract* — its checklist-fed, paged, verified pipeline
  is its own. (Diagrams are mermaid — adr/0005 — no hand-drawn skill involved.)
- **Offline**: a leaf notebook works offline exactly like the module map;
  notebooks are leaf-scoped, never course-scoped.

## 10. Rendering

- **Renderer**: markmap v1, behind a seam — the plan (`plan.md` → derived `spec.json`) is renderer-agnostic.
- Documented markmap workarounds (from the demo): `data:` image URIs are refused
  at markdown level → diagrams are injected into the tree JSON as base64 after
  transform; images survive only as image-only list items or standalone image
  nodes; bullets become child nodes.
- **SVG-first** for all diagrams; PNG reserved for raster-only textures and
  Open-Graph thumbnails (`mindmaps/og/<module>.png`).

## 11. Offline & packaging

- **Layer 1** — the fused course map is a single self-contained HTML with inline
  diagrams. Guaranteed offline, zero infra.
- **Layer 2** — PWA precache: per-course "download for offline" prefetches all
  leaf notebooks (never-opened leaves included), shared assets cached once.
- **Layer 3** — "revision pack": a per-course single file with notebooks inlined,
  for the no-signal-at-all case.
- Publishing: project Pages per course repo; `.nojekyll` at the published root;
  portfolio (`akshaydev17.github.io`) links to each atlas (or, later, vendors the
  output under `/atlas/<course>/` for one design + one service worker).

## 12. Skill interface

### 12.1 The flow — spec → plan → implementation

The familiar three-stage shape, with the stages named for what they hold here:

| stage | ours | who writes it | gate |
|---|---|---|---|
| **spec** — what must be true | the module README and its sidecars | the course author, before the tool runs | — |
| **plan** — how it becomes an atlas | `plan.md` + `spec.json`: the faithful tree, and each leaf's checklist (what must survive compaction) | the pipeline, reviewed by a human | **blocking** — Gate 1 structure, Gate 2 checklists |
| **tasks** — what remains to do | **derived, not authored**: the set of stale leaves | computed from the leaf fingerprints | — |
| **implementation** | the artifacts: the fused map and the notebooks | the pipeline | — |
| **verify** | the §14 report | machine | coverage · grounding · adherence · freshness · approval |

**No hop drifts silently**, which is the property the whole shape exists for:

- *spec → plan* — every node cites `file:line`; coverage enumerates the collapsibles,
  mermaid blocks and sidecars; the plan's own fingerprints are recorded (§14.1).
- *plan → artifacts* — coverage asserts each checklist item is present in its
  notebook.
- *artifacts → source* — grounding asserts every claim traces to a real anchor; the
  critic reads the rest for drift.
- *plan → time* — the approval's fingerprint lapses on any change to the plan or to
  the source its checklists claim to capture.
- *artifacts → source over time* — each leaf's `source_sha`, naming the leaves that
  moved.

Three deliberate departures from the usual shape:

1. **The spec is not ours.** It pre-exists and belongs to the course author, so there
   is no "does the plan satisfy the spec?" gate — the pipeline's obligation is
   fidelity to the source, not criticism of it.
2. **One human gate, not three.** The plan is the only thing a human approves; the
   rest is machine-checked, and a human re-enters through a `needs-review` item
   rather than through a stage (§15: post-generation review is exception-only).
3. **The task layer costs nothing to keep current.** Because it is a diff rather than
   a document, "what needs doing" never goes stale and never needs re-approval —
   only the plan does.

`build-course-map` drives spec → plan → implementation and stops at the gates;
`refresh-stale-leaves` **is** the task layer. The router routes on this state:

| state | what happens |
|---|---|
| no plan | build the plan; stop at the gates, naming what to read |
| plan present, unapproved | say so; name the plan and the command that approves it |
| plan approved | generate, then report |
| leaf fingerprints moved | the moved leaves are the task list |

| skill | invocation | triggers |
|---|---|---|
| `revision-atlas` (router) | user-invoked | names the three below; zero context load |
| `build-course-map` | user-invoked | course: discover → order → per-module build (delegated) → fused map |
| `build-module-map` | user-invoked / inner unit | one module: extract → plan (2 gates) → generate |
| `refresh-stale-leaves` | model-invoked | hash mismatch / "the source changed" / "refresh the atlas" |

`refresh-stale-leaves` is model-invoked so the agent can reach it when it
*notices* staleness; `build-course-map` stays human-gated (expensive, batched).
The skills ship in the plugin bundle (npm); artifacts live in each course repo's
`mindmaps/`. `build-course-map` is the front door: it delegates each module to
`build-module-map` (one pipeline, never duplicated) and renders the fused map once
every module is built.

The **plan (`plan.md`, with its derived `spec.json`) is the common artifact both
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
├── atlas.json            # course index (generated): course name + ordered modules
├── index.html            # THE fused course map — one file, one subtree per module
├── assets/               # font(s), flip JS, theme CSS
├── og/                   # PNG thumbnails
└── <module-slug>/
    ├── plan.md            # human source of truth (approved)
    ├── spec.json           # derived machine contract (generated)
    └── leaves/<leaf-id>/
        ├── notebook.html
        ├── diagram.svg   # rendered mermaid
        └── diagram.mmd   # the .mmd source (diffable)
```

`spec.json` carries the approval record and, per leaf, the fingerprint of the source
range that leaf was built from — so a later run can say *which* leaves went stale
rather than suspecting the module, and a tree can state its own provenance.

`<leaf-id>` is the leaf's unique heading-derived id (the same string used as its
source-anchor fragment), **never a position**. A positional name (`leaf-003`)
shifts the moment a section is inserted above it, and every link, bookmark and
`refresh-stale-leaves` lookup then quietly resolves to a different leaf — the
directory name has to be a function of the thing, not of its index.

Inside the one fused map, a leaf's id is **namespaced by its module** —
`<module-slug>--<leaf-id>` — because the document now spans every module, and two
modules with the same heading would otherwise collide (the 0008 duplicate-title
bug at course scale). The same namespaced id is the fragment in every map → notebook
link and every notebook's `← module map` back-link (which resolves from
`leaves/<leaf-id>/notebook.html` up to `mindmaps/index.html`, so it carries one
extra `../` level than a per-module map did).

The map is the navigation surface: `index.html` links each leaf to its own
`leaves/<leaf-id>/notebook.html`, and its source anchors are relative paths that
resolve from where the map actually sits (see §14, `links`).

## 14. Verification & coverage report

`build-course-map` ends by printing, per module: file inventory status; per-leaf
checklist coverage; per-leaf adherence (drift flags from the critic + grounding
misses); broken anchors; offline-purity (no external load-bearing refs in maps);
notebook page count vs budget; `needs-review` count. Any unclassified file or
coverage miss is a **failure**, not a warning.

**A check must distinguish "I could not test this" from "this is wrong."** An empty
test is not a negative result, and conflating the two is how this project has produced
its most misleading verdicts in both directions: an empty notebook passed because
existence was checked and not content ([0016]); a clipped answer passed because text
was checked and not layout ([0010]); a present collapsible *failed* because a label's
tokenisability was checked and not its presence ([0015]). Every one of those was a
correct artifact and a wrong check. Where the input cannot be tested as designed, the
check says so — a coarser real assertion, or an explicit `needs-review` — rather than
silently answering the question with the only branch it has.

**`links` (broken anchors).** Every `href` in the map and in every notebook must
resolve from the file that carries it — a dead link is invisible until someone
clicks it, which is exactly the class of breakage this project refuses to ship.
The two kinds of link carry different levels, because they fail for different
reasons: a link **inside** the artifact tree (a leaf's notebook, the shared
assets) is the build's own promise, so breaking it is a **failure**; a link **out**
to the module markdown can only resolve when the tree ships beside its source — the
§13 layout does, a bare copy of `mindmaps/` does not — so that is `needs-review`
with an explicit remedy. Resolution is asserted, not the fragment: a wrong
`#anchor` still opens the right file, and GitHub's own slug rule is not ours to
replicate.

### 14.1 The human gates are enforced, not implied

Gate 1 (structure) and Gate 2 (checklists) are **blocking**. `build` writes the plan
and then refuses to generate anything until both are approved, exiting **3** —
distinct from 1 (verification failed) so a caller can tell a human decision from a
bug.

**Approval is a conversation, not a command.** The human surface is the chat: the
skill presents the plan and stops, the user grants approval in their own words, and
only then does the skill record it — `--approve` is the skill's *internal verb*, the
thing it runs after the user's affirmative, never a line the user is asked to type.
The audit trail is the conversation that contains the grant, plus the record (`who`,
`when`, and the fingerprints). A rogue agent could self-approve — the agent runs the
commands either way — but it cannot approve anything other than the plan it showed,
or do so invisibly: the fingerprints bind the record to the exact plan presented.

An approval is a **fingerprint of the content it reviewed**, not a flag on a file:

- Gate 1's fingerprint covers the shape — kinds, titles, ids, anchors, edges.
- Gate 2's covers every leaf's checklist **and the source range those checklists
  claim to capture** — because Gate 2's question is whether the checklist is
  grounded in the source, so prose that changed without changing an item still
  invalidates the approval. (Measured: appending a paragraph moved neither the
  structure nor the items, and regeneration proceeded silently until the source was
  included.)

Consequences, all of them deliberate: an approval **survives** rebuilding the same
plan; it **lapses** the moment that plan or its source changes, and the plan says so
(`LAPSED — approved as … but the plan is now …`); and it cannot be laundered forward,
because a rebuild carries the recorded fingerprint rather than stamping the current
one onto it. The refusal names the leaves whose source moved, so a human knows what
to re-read.

Two layers, because one is defeatable: the gate stops an unapproved plan being
generated, and the verifier's `approval` axis fails any artifact tree that cannot
show a current approval — an old tree, a copied one, or anything that reached the
generator without passing the door. The `freshness` axis fails a tree whose source
has moved on since it was built.

## 15. Milestones (tracer bullets) and open questions

1. Extractor: inventory + link graph + classification ladder + closure check.
2. Structure plan: full `plan.md` node graph (headings + kinds + diagram hints).
   **Gate 1 — human approves coverage** (every H2/H3/H4, collapsible, mermaid
   block, and linked markdown accounted for). Script derives `spec.json`.
3. Leaf plan: per-leaf `checklist` drafted from the section content.
   **Gate 2 — human approves checklists** (information captured to the fullest).
4. Renderer: the fused course map (course root + module subtrees; markmap, inline
   diagrams, `<module-slug>--<leaf-id>` namespacing) — runs against the frozen plan.
5. Leaf generator: diagram (mermaid per §8) + recall/prompt/reveal +
   source node — runs against the frozen checklist.
6. Notebook generator: paged flip template + shared assets.
7. Verifier: coverage (deterministic) + adherence (grounding + LLM critic) + report; post-gen human review is exception-only.

Open: OG-image pipeline; the eventual publish step into the portfolio repo;
whether `needs-review` blocks or merely annotates in v1; whether the two
plan gates are one combined approval step or two separate ones.

- **The map is structure; the notebook is the leaf.** A node never carries a
  leaf's content — no recall bullets, no prompt, no source audit, no inline
  diagram. That was a degraded second copy of the notebook (unstyled,
  unpaginated, question without answer) and it made the map end in bullet lists
  instead of leaves. Every node, parent or leaf, shows a title, its kind, its
  source anchor and the link into its notebook. The map is the outline and the
  way in; content has exactly one home.
