# A module's corpus is its own narrative: top-level markdown plus what that markdown links to inside the module

---
Status: accepted
---

The closure invariant (adr/0001) says nothing may be silently dropped, and it was
first implemented by enumerating **every `.md` under the module path** and
requiring each to be classified or explicitly ignored. On a real module that
over-reaches: ML-Engineer M5 keeps a runnable pipeline in `code/`, with its own
`code/README.md`. Nothing in the module's README mentions it — M5's README has 32
markdown links and *all of them are internal anchors*; it contains no file link at
all, and nothing else in the repo links `code/README.md` either. The atlas still
enumerated it, called it residue, and **refused to ship the module**.

The file is not part of the module's narrative. It documents runnable code. But an
ignore list (`code`, `src`, `scripts`, …) is the wrong fix: it grows forever, it is
policy hidden in code, and it cannot tell a code folder's README from a genuinely
orphaned revision sidecar.

## Decision

Scope a module by **what its authors wrote as a unit**:

- **in scope** = every `.md` **directly under** the module path, **plus** every
  `.md` that an in-scope file **links to**, provided the target lies **inside** the
  module path. Link-following is transitive and resolves against the linking file's
  own directory.
- **out of scope** = any other `.md` inside the module path. Reported in the
  coverage report with its reason; **never** a build failure, because it is not part
  of the module's material.
- Noise dirs (`.git`, `node_modules`, `scratch`, `handwrittenNotes`, …) stay
  ignored **by explicit rule**, as §6.1 requires.

The invariant is unchanged in force, only in domain: an **in-scope** file may not
be silently dropped. And the partition is itself checked — in scope ∪ out of scope
must still equal every non-noise `.md` in the tree, so narrowing the scope can
reclassify a file but can never lose one.

## Consequences

- M5 passes: 1 in scope (its README), 1 out of scope (`code/README.md`), 20 leaves.
  M2 is untouched: 11 in scope, 0 out of scope, because everything it owns sits at
  the module's top level.
- A module whose material lives in a subdirectory now needs the narrative to *cite*
  it — which is the honest requirement. If a subdirectory README is genuinely
  revision material, the module's README should link it; if it is not, it stays out
  of scope with no rule to maintain.
- The set of links is now the scope boundary, so a link's resolution is load-bearing
  and must be correct: links resolve against the **linking file's directory**, not
  the module root.

## When to revisit

- If real modules keep material in subdirectories that the top-level markdown does
  not cite, the citation requirement is too strict — consider a per-module
  `atlas.yml` include list rather than re-widening the default.
- If the out-of-scope report grows noisy, filter it by the same noise rules rather
  than by dropping the report.
