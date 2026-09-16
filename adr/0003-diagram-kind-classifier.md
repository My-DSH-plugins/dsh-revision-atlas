# Diagram kind is content-driven: mermaid for source-authored or exactness-critical structure, hand-drawn as the residual

---
Status: superseded by adr/0005
---

A leaf needs a diagram, but not every leaf wants the same kind: a hand-drawn
sketch is a memory hook (the *shape* of an idea), while a mermaid diagram is a
claim about exact structure (states, sequence, decision paths). Letting the
generator pick freely fails in both directions — it invents mermaid where the
source gives no structure (false precision: an authoritative-looking diagram
that teaches a wrong branch), or it sketches where exactness matters (false
confidence: the learner memorizes a branch that isn't there). The kind must
therefore be chosen by a rule that separates "safe to sketch" from "must be
exact", and the exactness judgment must be human-gated.

## Decision

The diagram kind is decided content-first, in two passes, with this priority:
**mermaid whenever it is free or justified; hand-drawn as the residual
catch-all.**

1. **Deterministic (code, no model, no gate)**:
   - a `needs-review` residue → `[]` (never draw over something flagged for a
     human decision);
   - the leaf's source range already contains a ```mermaid block → **mermaid**,
     one entry per block — faithful extraction and render, zero invention, so no
     gate is needed;
   - otherwise → **hand-drawn** placeholder.

2. **Semantic (agent proposes, Gate 2 approves)**:
   - the agent reviews each hand-drawn placeholder and may keep it, **upgrade it
     to mermaid**, or propose `[]` (nothing worth drawing);
   - the upgrade rule is the only judgment in the whole classifier: *a decision
     procedure / state machine / multi-branch sequence whose exact branching
     matters* → mermaid. Every proposal is human-gated at Gate 2.

## Why hand-drawn is the residual, not the preference

Hand-drawn is the default because it is the **only kind that needs no semantic
judgment and carries no false-precision risk**, so the deterministic build can
always produce a valid placeholder:

- Mermaid-for-exactness requires answering *"does exact branching matter
  here?"* — exactly the judgment the whole skill exists to human-gate. It
  cannot be a code default.
- A sketch that is slightly off is still a sketch; a mermaid that is slightly
  off is false precision — it looks authoritative and the learner trusts it.
  The low-stakes artifact is the default, and the high-stakes artifact is
  reached only by gate (or extracted for free from source).
- Source-authored mermaid is the one *uncontroversial* mermaid: nothing is
  invented, the author's own diagram is preserved at near-zero cost.
- Hand-drawn also matches the notebook's handwritten aesthetic (§9); mermaid is
  the deliberate exception when precision outweighs visual coherence.

This ADR governs *which kind* a leaf carries. `adr/0002` governs *how* mermaid
is rendered once a leaf carries it — the two are deliberately split.

## Consequences

- The deterministic build never stalls and never invents mermaid silently:
  every mermaid is either source-authored (traceable to a ```mermaid block) or
  Gate-2-approved (human-visible in `plan.md`).
- The cost: the semantic pass and Gate 2 must run before a hand-drawn
  placeholder becomes a committed mermaid, and the reviewer must genuinely
  judge exactness. For v1, a diagram's exact branching is human-reviewed, not
  machine-checked — the verifier asserts label presence only (SPEC §8).

## When to revisit

- If Gate 2 keeps upgrading most hand-drawn placeholders to mermaid, the
  residual is the wrong default — invert it to "mermaid unless explicitly
  judged intuition-only".
- If hand-drawn sketches turn out unprofessional or break the verifier (labels
  not parseable as real `<text>`), drop hand-drawn in favor of mermaid
  everywhere.
- If source mermaid blocks render poorly, that is an `adr/0002` problem
  (version/styling), not this decision.
- If `[]` turns out more common than expected, promote "nothing worth drawing"
  to a first-class deterministic rule rather than an agent proposal.
