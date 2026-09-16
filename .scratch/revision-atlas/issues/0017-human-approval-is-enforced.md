# 0017 — Human approval is enforced, and leaves carry their source fingerprint

- **Blocked by:** —
- **Blocks:** 0012 (the skill drives this)
- **Status:** done

## The question this answers

"Enforce human approval — how shall you ensure and handle that?" Two layers, because
one is defeatable, and an approval defined as a *fingerprint of reviewed content*
rather than a flag on a file.

## 1. Leaf fingerprints, persisted

`leaf_source_sha` hashes the exact lines a leaf owns — its heading to the next
heading of any rank, or the whole file for a sidecar — and it is written per leaf
into `spec.json`. Lines are joined with their boundaries intact: joining on spaces
alone would make text merely *moving between lines* invisible.

The range itself is now expressed once (`leaf_source_lines`), shared by the hash, the
grounding check and the coverage audit, so the three cannot disagree about what a
leaf is made of.

Why per leaf: `refresh-stale-leaves` must regenerate the leaves that changed, not the
module, and a refusal is far more useful when it names the leaf.

## 2. The gate blocks generation

`build` writes the plan (`plan.md`, `spec.json`) and then refuses to generate until
both gates are approved, exiting **3** — distinct from 1 (verification failed) so a
caller can tell a human decision from a bug. Approving is its own act:

```
python -m revision_atlas.build <module> --mindmaps <out> --approve all --by "Name"
python -m revision_atlas.build <module> --mindmaps <out>
```

The record (`{sha, at, by}` per gate — who, when, and what) lives in `spec.json`;
`plan.md` renders each gate's state, and an unapproved plan says `AWAITING HUMAN
APPROVAL` at the top.

## 3. What an approval covers

- **Gate 1** fingerprints the shape: kinds, titles, ids, anchors, edges.
- **Gate 2** fingerprints every leaf's checklist **and the source range those
  checklists claim to capture**.

Including the source is the non-obvious half. Gate 2 asks whether the checklist is
grounded in the source, so a change that adds no item still invalidates it. Found by
testing rather than reasoning: appending a bare paragraph moved neither the structure
nor the items, and the build regenerated silently.

So: an approval survives rebuilding the same plan, lapses when the plan or its source
changes, and **cannot be laundered forward** — a rebuild carries the recorded
fingerprint instead of stamping the current one onto it.

## 4. The verifier keeps the door honest

- `approval` (failure) — an artifact tree must show a current approval for both
  gates. Covers a tree built before the gate existed, one copied in, or anything that
  reached `generate_all` without passing the door.
- `freshness` (failure) — each leaf's source must still hash to what `spec.json`
  recorded, and the finding names the leaf.

## Found and fixed on the way

- **The laundering bug, written by the author of the warning against it.**
  `_carried_approval`'s docstring says a rebuild must not silently launder an approval
  into a fresh one; the code then stamped the current fingerprint onto every carried
  gate. Every rebuild re-approved itself until this was fixed.
- **Order bug:** the refusal diffed the changed leaves *after* writing the new
  `spec.json` over the old one, so the diff was always empty.
- **A false freshness failure:** a tree moved away from its source reported every leaf
  as changed. Unreadable is not changed — SPEC §14's rule, catching its own violation
  within a day of being written.
- **Empty contract:** `spec.json` with no plan cannot establish provenance, and is now
  a failure rather than a silent pass.

## Evidence

Measured from the CLI on a real module:

| step | exit | result |
|---|---|---|
| build, never approved | **3** | `plan.md` + `spec.json` only; no `leaves/`, no `index.html` |
| `--approve all --by A` | 0 | both gates APPROVED with who/when/fingerprint |
| build | 0 | generates; `PASS` |
| rebuild, unchanged | 0 | approval survives — no re-approval needed |
| prose edit, then build | **3** | `checklists LAPSED — approved as b191e8dc… but the plan is now 15266f29…`, and it names `Sec` as the leaf whose source moved |

6 new tests (the gate, the lapse, the record, the unapproved tree, the stale leaf),
93 green.
