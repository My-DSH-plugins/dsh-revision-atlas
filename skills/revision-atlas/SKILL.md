---
name: revision-atlas
description: Route to the revision-atlas skills: build-course-map (a whole course's fused map), build-module-map (one module), refresh-stale-leaves (regenerate stale leaves). This router carries no pipeline of its own.
---

# Revision Atlas — router

You are the front door, not the pipeline. Read what the user wants and what is already
built, then hand off to the skill that owns that job:

| intent | go to |
|---|---|
| build / rebuild a whole course (course index + every module map) | `build-course-map` |
| build / rebuild ONE module | `build-module-map` |
| the source moved; regenerate only the stale leaves | `refresh-stale-leaves` |

Say which skill to invoke, then load that skill and let **it** drive. Do not re-implement
its pipeline here, and do not run any Python yourself — each skill knows its own tools.
