# 0012 — The skill itself (router + the two entry points)

- **Blocked by:** 0007, 0011 (both done)
- **Blocks:** 0013
- **Status:** OPEN — never ticketed until now; no code written

## Why this ticket is late, and why it matters

The seven tracer-bullet tickets (0001–0007) were cut for the seven *pipeline
stages* in SPEC §15 — the machinery, bottom-up. The thing the project exists for
was never ticketed. The only traces anywhere: one closing line in 0007 ("it lands
with the skill wrapping") and SPEC §15's Open list ("the eventual publish step into
the portfolio repo").

So the working definition of done was "the seven stages exist and verify", not
"a reader can install this and run it". That is the mistake of
[0009](0009-build-writes-the-map.md) one level up: *the stages exist* is not *the
product exists*, exactly as *the map is written* was not *the map works*.

SPEC §12 has specified the skill interface all along: a `revision-atlas` router,
plus `build-course-map` (user-invoked) and `refresh-stale-leaves` (model-invoked).
The omission is in the ticket cutting, not the design.

## Goal

Realise SPEC §12: `skills/revision-atlas/SKILL.md` carrying the router and both
entry points, so an agent can drive the pipeline from a course module directory.

| skill | invocation | triggers |
|---|---|---|
| `revision-atlas` | user-invoked | names the two below; zero context load |
| `build-course-map` | user-invoked | heavy, batched: extract → plan (2 gates) → generate |
| `refresh-stale-leaves` | model-invoked | hash mismatch / "the source changed" / "refresh the atlas" |

## Missing machinery (not just prose)

1. **Staleness detection does not exist.** SPEC §12 keys `refresh-stale-leaves` off
   a hash mismatch, but nothing records a per-leaf source hash — the only hash in
   the codebase is `_asset_version()`, a cache-buster for shared CSS/JS. Needed:
   hash each leaf's own `file:line` range at build time, persist it in `spec.json`,
   and compare on refresh to decide which leaves to regenerate.
2. **The gates are text only.** `plan.md` says "status: `proposed` — flip to
   `approved` after both gates pass", but nothing reads it; generation proceeds
   regardless. Decide and implement: does the skill *refuse* to generate below an
   approved plan (a real gate), or is approval a human convention?
3. ~~**The recall pass has no reveal budget.**~~ **Done** — capped at 500 words in
   `recall-pass.md`, in SPEC §8, and asserted by `_check_budgets` (0010).
4. **The four agent passes are files, not steps.** `semantic-pass.md`,
   `recall-pass.md`, `mermaid-pass.md` and `verifier-critic.md` exist and are
   cold-tested, but the skill has to state when each runs, in what order, and what
   it does with a pass that comes back short.

## Acceptance

- `build-course-map` run from a cold agent (only the SKILL.md + a module dir)
  produces `plan.md` + `spec.json` and stops at the gates.
- After approval it generates the full §13 tree and prints the §14 report.
- `refresh-stale-leaves` on an edited module regenerates **only** the affected
  leaves, and is a no-op when nothing changed.
- The router loads no pipeline context when it is only routing.

## Evidence required

A fresh-subagent cold test per the established protocol (instruction + dir only),
plus a staleness test: edit one section, confirm exactly that leaf's artifacts
change and the rest are byte-identical.
