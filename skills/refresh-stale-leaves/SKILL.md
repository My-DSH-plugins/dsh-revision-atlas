---
name: refresh-stale-leaves
description: Regenerate only the leaves of a module map whose source changed, leaving the rest untouched. Use when a module's markdown has moved since the atlas was built and the verifier reports stale leaves — not for a first build, which is build-module-map or build-course-map.
---

# Refresh stale leaves

The atlas is built; the source has since moved. Regenerate the changed leaves and
nothing else. This is the `build-module-map` skill's refresh half, wrapped so you can
reach it the moment you notice staleness.

## Where the tools live

The Python package is the `build-module-map` skill's bundle. With `<base>` your own
directory, it is the sibling `<base>/../build-module-map/tools/`:

```
PYTHONPATH=<base>/../build-module-map/tools python3 -m revision_atlas.<module> ...
```

## What to do

1. **Name the task list.** Run the verifier and read its `freshness` findings — each
   names a leaf whose `source_sha` no longer matches its source. Those leaves are
   the only thing that needs work.
2. **Rehydrate the pass inputs.**
   ```
   PYTHONPATH=<base>/../build-module-map/tools python3 -m revision_atlas.passes <module_dir> --mindmaps <out> --out <dir>
   ```
   This writes `semantic.json` / `recall.json` / `mermaid.json` for every leaf, so
   the unchanged ones carry over untouched.
3. **Re-run the passes** (each in a fresh subagent, per the `build-module-map` skill)
   and fold only the stale leaves' entries over the rehydrated files.
4. **Rebuild.** A source change lapses Gate 2 by design, so the user re-approves the
   *updated* plan before anything is regenerated. Present, ask, and proceed only on
   their affirmative — never self-approve. Then render the map the way
   `build-module-map` does.
5. **Verify and report.**

The pass instructions, the approval conversation and the "never" list all live in the
`build-module-map` skill.
