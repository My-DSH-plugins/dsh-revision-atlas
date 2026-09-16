# dsh-revision-atlas

Turn a course's Markdown into an **offline-first revision atlas**: a navigable mind
map of every module, whose leaves are compacted recall units — mermaid diagrams and
page-flip notebooks — with **machine-checked coverage** so no source
content is silently dropped.

## The problem

Long-form course notes — 1,700-line modules, cross-linked sidecar files, for/against
debate pairs, collapsible example catalogs — are hard to revise. An atlas compacts
them into a structure you can navigate on a phone in minutes, online or offline, and
traces every node back to the exact source line it came from.

## What it produces

```
course atlas
└── course index   (title = course name; nodes = modules)
    └── module map (faithful to the source headings)
        └── leaf    (recall block · mermaid · notebook · self-test · source audit)
```

- **Faithful structure** — the map mirrors the document's own headings; nothing is
  re-authored or reordered.
- **Compacted leaves** — each leaf is one screen: 3–5 recall hooks, a structural
  mermaid diagram, a self-test prompt, and a page-flip notebook
  for depth.
- **Source audit** — every leaf keeps its original bullets in a collapsible node, and
  every node links back to its source anchor.
- **Offline-first** — module maps are single self-contained files; notebooks are
  precached so even leaves you've never opened work with no signal at all.

## Why you can trust it

The one failure a summarizer cannot afford is a *silent omission*. The atlas enforces
coverage as a machine-checked invariant, not a prompt: a deterministic inventory
closes over every source file, each leaf carries a checklist of the items that must
survive, and a verifier re-checks every generated artifact against that checklist. An
unclassified file or a coverage miss **fails the build** — it never ships.

## How it works

`extract → spec → render → verify`

1. **Extract** (deterministic) — heading tree, link graph, and typed relationships
   (sections, sidecars, debate pairs, framework matrices, aggregators, shared nodes).
2. **Spec** (human-reviewed) — a per-module contract: nodes, sources, and the leaf
   checklists that define what must survive.
3. **Render** — course index, module maps, and per-leaf artifacts (mermaid,
   notebook).
4. **Verify** — re-parse every artifact, assert checklist coverage, report the
   result. Nothing is trusted on faith.

It ships as a **DeepSeek Harness skill** (global install, usable across any course
repo), with artifacts written to each course's `mindmaps/` directory.

## Status

**Design phase** — the specification is complete enough to implement. This repository
currently holds the design; the skill and generator are the next milestones.

Roadmap:

- [ ] Extractor: inventory + link graph + relationship classification + closure check
- [ ] Spec writer: per-module `spec.yml` with per-leaf checklists
- [ ] Renderer: course index + module maps (self-contained, offline)
- [ ] Leaf generator: mermaid + recall/prompt/reveal + source audit
- [ ] Notebook generator: page-flip notebooks with shared assets
- [x] Verifier + coverage report

## Documentation

- [`CONTEXT.md`](CONTEXT.md) — the glossary.
- [`SPEC.md`](SPEC.md) — the full spec: data model, coverage invariant, notebook
  model, offline packaging, skill interface.
- [`adr/0001-coverage-invariant.md`](adr/0001-coverage-invariant.md) — the decision
  behind the coverage invariant.
- [`adr/0002-mermaid-rendering.md`](adr/0002-mermaid-rendering.md) — mermaid is
  rendered to SVG at build time, not in the viewer.
- [`adr/0003-diagram-kind-classifier.md`](adr/0003-diagram-kind-classifier.md) — a
  leaf's diagram kind is content-driven (mermaid vs hand-drawn vs none). **Superseded
  by adr/0005.**
- [`adr/0004-handdrawn-geometry-invariant.md`](adr/0004-handdrawn-geometry-invariant.md) —
  hand-drawn geometry guaranteed by a deterministic layout invariant. **Superseded
  by adr/0005.**
- [`adr/0005-diagrams-are-mermaid.md`](adr/0005-diagrams-are-mermaid.md) — diagrams
  are mermaid, rendered at build time; the hand-drawn sketch path is removed.
- [`adr/0006-module-scope.md`](adr/0006-module-scope.md) — a module's corpus is its
  top-level markdown plus what that markdown links to inside the module.
