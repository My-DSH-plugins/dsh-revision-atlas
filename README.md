# Revision Atlas

Turn a course's Markdown into an **offline revision atlas**: a navigable mind map of
the course whose leaves are compacted revision units — a recall block, a mermaid
diagram, a self-test, and a page-flip notebook — with **machine-checked coverage** and
a **human-gated plan**, so no source content is ever silently dropped.

Long-form course notes — 1,700-line modules, cross-linked sidecar files, for/against
debate pairs, collapsible example catalogs — are hard to revise. An atlas compacts
them into a structure you can navigate on a phone in minutes, online or offline, and
traces every node back to the exact source line it came from.

## How it works

It runs the familiar **spec → plan → implementation** shape, and it stops at the plan
for you.

1. **Spec** — your module's Markdown. It is the source of truth and is never edited,
   re-authored, or second-guessed.
2. **Plan** — the pipeline mirrors the document's own headings into a plan, and drafts
   each leaf's checklist of what must survive compaction. It then **stops**: nothing
   is generated until you approve the plan.
3. **Approval** — the skill presents the plan and asks. You either ask for changes or
   say "proceed"; only your explicit yes records the approval — who, when, and a
   fingerprint of exactly what was approved.
4. **Implementation** — the map and the notebooks are generated.
5. **Verify** — a verifier re-checks every artifact: coverage (nothing dropped),
   grounding (nothing invented), adherence (no drift), and freshness (still true to
   the source).

Change a file later, and the verifier names exactly which leaves went stale; those are
the only thing that gets re-planned and re-approved.

## What it produces

```
course atlas
└── module map   (faithful to the source headings; the index into memory)
    └── leaf     (recall block · mermaid · self-test · page-flip notebook)
```

- **Faithful structure** — the map mirrors the document's own headings; nothing is
  reordered or paraphrased away.
- **Compacted leaves** — each leaf is one screen of hooks, with the notebook as the
  depth layer.
- **Source audit** — every leaf keeps its original bullets, and every node links back
  to its exact `file:line`.
- **Offline-first** — maps and notebooks are self-contained; they work with no
  network.

## Why a plugin, not a bare skill

DSH already loads a plain `SKILL.md` from `~/.dsh/skills`. That is enough for a
pure-instructions skill, and it is **not** the convenient choice here, because the
`build-module-map` skill is not instructions-only:

- it ships a **Python pipeline** (extract → plan → generate → verify) plus four
  **pass instructions** that run as fresh subagents;
- it needs a stable, versioned install rather than a manual copy into the skills
  directory;
- its `<base>/tools` references map onto the host's skill-registry `resourceBase` —
  the directory announced as `<skill_resources>`.

A plugin provides all three via `dsh plugin add` and `ctx.skills.registerProvider()`.

## What's inside

| skill | invocation | what it does |
|---|---|---|
| `revision-atlas` | user-invoked | router — names the three below; no pipeline of its own |
| `build-course-map` | user-invoked | discover + order modules, build each, render the ONE fused course map |
| `build-module-map` | user-invoked | build / rebuild / approve a single module's map — spec → plan → implementation |
| `refresh-stale-leaves` | model-invoked | regenerate only the leaves whose source moved |

The `build-module-map` skill carries four pass instructions (`semantic`, `recall`,
`mermaid`, `verifier-critic`) and the standard-library Python package under `tools/`;
the other skills reach it through that bundle.

## Install

npm is the distribution channel — the same `skills/<name>/SKILL.md` tree works on both
hosts.

### DeepSeek Harness

```sh
dsh plugin --profile <profile> add dsh-revision-atlas
```

Restart `dsh web` (or refresh), then type `/revision-atlas` (the router) in the
composer or pick it from the skill picker.

### Claude Code

```sh
npm install dsh-revision-atlas
claude plugin install node_modules/dsh-revision-atlas
```

Claude Code distributes plugins through **marketplaces and paths**, not npm — npm is
only a plugin's *dependency* registry. So the npm step here is a transport: it fetches
the files, and Claude installs them from the local path. The
`.claude-plugin/plugin.json` manifest ships in the package.

## Why you can trust it

The one failure a summarizer cannot afford is a *silent omission*. Two things make it
loud instead:

- **Coverage is an invariant, not a prompt.** A deterministic inventory closes over
  every source file; each leaf carries a checklist; a verifier re-checks every
  generated artifact against it. An unclassified file or a coverage miss **fails the
  build**.
- **The plan cannot change silently.** Approving a plan fingerprints the content you
  reviewed; that approval lapses the moment the plan or its source changes, and the
  plan says so — with the changed leaves named.

## Development

While the plugin is unpublished — or while you are editing it — link the checkout so
changes are picked up without re-publishing:

```sh
dsh plugin --profile <profile> add link:$PWD
claude plugin install $PWD
```

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m revision_atlas.package --tools   # re-sync the bundled copy
```

## Documentation

- [`SPEC.md`](SPEC.md) — the full spec: the flow (§12.1), coverage invariant (§6),
  verification (§14), directory layout (§13).
- [`CONTEXT.md`](CONTEXT.md) — the glossary.
- [`adr/`](adr/) — the recorded decisions (coverage invariant, mermaid rendering,
  diagrams-are-mermaid, module scope).

## License

MIT
