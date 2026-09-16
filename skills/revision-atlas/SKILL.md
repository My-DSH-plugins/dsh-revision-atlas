---
name: revision-atlas
description: Build, rebuild and refresh a course module's revision atlas — a mind map whose leaves are paged notebooks, extracted faithfully from the module's markdown with
  machine-checked coverage and adherence. Use this when the user wants to create or
  update a revision atlas, or to review and approve the plan that gates its
  generation.
---

# Revision Atlas

You drive a pipeline that compacts a course module (a README plus the markdown it
links to) into an offline, navigable atlas. The shape is **spec → plan →
implementation**:

- **spec** — the module's own markdown. It is the course author's; you never edit it
  and never second-guess it. Your obligation is fidelity to the source, not criticism
  of it.
- **plan** — `plan.md` + `spec.json`: the faithful tree and each leaf's checklist of
  what must survive compaction. The pipeline writes it and then STOPS.
- **implementation** — the map (`index.html`) and the notebooks, generated only after
  a human approves the plan.
- **tasks** — never authored; derived as the set of leaves whose source moved.

## The one rule

**Never proceed past the plan without a recorded human approval, and never record one
except after the user grants it in this conversation.** Approval is a question, not a
command: you present the plan, the user answers, and their explicit affirmative — in
their own words — is the only thing that authorises generation. A request for changes,
a question, or silence is not approval.

## State → action

| what you find | what you do |
|---|---|
| no `spec.json` under the module's `mindmaps/<module>/` | run the build; it stops with the plan |
| plan present, gates unapproved | present the plan and ask (below) |
| plan approved and current | generate |
| the source moved since the build | the verifier names the leaves; refresh (below) |

## Where the tools live

This skill ships as a bundle: the SKILL.md, the `passes/` instructions, and the
`tools/` directory holding the Python package. Below, `<base>` denotes the directory
this SKILL.md is installed in — DeepSeek Harness announces it as `<skill_resources>`,
and in Claude Code it is simply this skill's own directory, so a relative path like
`tools/` resolves to `<base>/tools/` on either host.

The pipeline is standard-library Python, so it runs as:

```
PYTHONPATH=<base>/tools python3 -m revision_atlas.<module> ...
```

If the skill is installed somewhere read-only, copy `<base>/tools` to a writable
location first and point `PYTHONPATH` there.

## Build

```
PYTHONPATH=<base>/tools python3 -m revision_atlas.build <module_dir> --mindmaps <out> \
    [--semantic s.json] [--recall r.json] [--mermaid m.json]
```

Exit codes: **0** generated · **1** verification failed · **3** awaiting approval (no
artifacts written). The plan is always written first (`mindmaps/<module>/plan.md` and
`spec.json`) — that is the review surface a human reads to approve.

## The four passes — always in fresh subagents

Four things the pipeline cannot do are done by you, one pass at a time, each in a
**fresh subagent** given only the pass instruction, the module directory and
`spec.json`. A pass contaminated by this conversation's context is a pass that cannot
be trusted. The instructions live in `passes/` beside this file:

1. `semantic-pass.md` — each leaf's claims: what must survive compaction.
2. `recall-pass.md` — each leaf's recall block and self-test (prompt + reveal).
3. `mermaid-pass.md` — a diagram where a leaf's shape earns one.
4. `verifier-critic.md` — reads the generated notebooks and flags drift.

Each returns a JSON keyed by leaf id, written to a file. Order matters: recall and
mermaid read the frozen checklist, so run `semantic` first, fold its output into the
build, and only then run the rest.

## Approving — a conversation

When the build stops at exit 3:

1. **Present** the plan: its path, the leaf count, coverage, and the two gate states.
   The thing being approved is `plan.md`; point the user at it.
2. **Ask**, plainly. If your host offers a structured question, use two options —
   **Approve** and **Request changes** — and read the choice. Otherwise ask in prose
   and read the reply.
3. **On approval**: record it, then generate —
   ```
   PYTHONPATH=<base>/tools python3 -m revision_atlas.build <module_dir> --mindmaps <out> \
       [same pass flags] --approve all --by "<the user's name>"
   PYTHONPATH=<base>/tools python3 -m revision_atlas.build <module_dir> --mindmaps <out> \
       [same pass flags]
   ```
   `--approve` is your internal verb — the user never types it, and you run it only
   after their affirmative.
4. **On changes**: revise (re-run the affected passes), re-present, and ask again.
   Never silently adjust what was shown, and never re-approve on the user's behalf.

## Refresh

When the source moves, do not rebuild the module. The verifier's `freshness` findings
name exactly which leaves are stale; those leaves are the task list.

- Rehydrate the pass inputs for every leaf:
  ```
  PYTHONPATH=<base>/tools python3 -m revision_atlas.passes <module_dir> --mindmaps <out> --out <dir>
  ```
  This writes `semantic.json` / `recall.json` / `mermaid.json` — the unchanged
  leaves carry over untouched, which is what makes the refresh incremental.
- Re-run the passes in fresh subagents and fold only the **stale** leaves' entries
  over the rehydrated files; the unchanged leaves stay as they were.
- Rebuild. This re-enters the gates: a source change lapses Gate 2 by design, so the
  user re-approves the *updated* plan — the human reviews what changed before
  anything is regenerated.

## Never

- edit a notebook, the map, or `spec.json` by hand — they are regenerated;
- edit the module's markdown;
- run `--approve` without a just-given human grant;
- substitute "make it read well" for a claim grounded in the source.
