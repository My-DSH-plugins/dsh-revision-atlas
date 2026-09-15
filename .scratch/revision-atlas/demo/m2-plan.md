# Plan — M2 · Model Failure Science · status: proposed

## Coverage: 11 classified · 1 ignored · 0 needs-review · 18 sections · 26 leaves · 13 collapsibles · 0 mermaid

# M2 · Model Failure Science
## Opening scene — the postmortem that wasn't
    - Ordering agent approved a 40% discount it had no authority to give; root cause read "the model hallucinated the discount policy".
    - Real failure: it followed the most salient instruction (a customer message) that was allowed to outrank standing policy — nothing separated policy from data.
    - "The model hallucinated" was a category error — the cheapest way to avoid naming the harness gap.
## The uncomfortable fact: models fail systematically, not randomly
    - An LLM optimizes plausibility of continuation, not truth or intent-fidelity → failures are structural, predictable patterns.
    - Four signatures: fluent-but-wrong, agreeable, fragile outside distribution, follows the loudest (not most important) instruction.
    - Which failure reaches a user (with what consequence) is entirely a harness question; some confabulation is irreducible.
## The failure classes
### 1. Hallucination & confabulation
      - Fluent, confident output that is false — incl. justified falsehood, invented citations, fabricated tool results.
      - Mechanism: most-plausible-continuation; cannot distinguish 'in training data' from 'true'.
      - Danger: wrongness that reads as rightness (hardest to catch); severity high.
### 2. Sycophancy
      - Agrees / flatters / gives the answer the user seems to want, even when wrong.
      - Mechanism: agreement rewarded in training → generalizes to 'what this user wants to hear'.
      - Signature: the answer flips when the user states a preference first; high severity in judgment roles.
### 3. Brittleness & shallow pattern-matching
      - Correct for the wrong reasons; competence evaporates under paraphrase / reorder / novel phrasing.
      - Mechanism: shortcut learning on surface cues; 'works in my tests' = the test set encoded the shortcuts.
      - Medium-high severity; the mechanism behind eval overfitting.
### 4. Instruction drift & compliance decay
      - Follows early instructions better than later ones; long/layered policy decays.
      - Mechanism: attention diluted across context — policy at token 3000 is less salient than the customer message at 3001.
      - Signature: obeys in a short session, violates in a long one; high severity.
### 5. Position & ordering bias
      - 'Lost in the middle': attends best to the start/end of context, worst to the middle.
      - Signature: move the same fact middle→end and correctness flips.
      - Medium severity; compounds with #4; cheaply fixable in context assembly (M4).
### 6. Reasoning degradation under load
      - Multi-step reasoning decays as complexity grows (more steps/tools/chains), even for 'smart' models.
      - Mechanism: no persistent scratchpad; intermediate results live in lossy attention; error compounds.
      - Signature: 2-step flawless, 9-step fails at step 6; high severity — design fix (scratchpads/sub-agents/verification).
### 7. Overlooked constraints
      - Satisfies the salient goal, silently violates surrounding constraints (2 a.m. flight; omitted liability clause).
      - Mechanism: constraint saturation — optimizes the salient objective, treats constraints as soft/later.
      - Signature: passes 'did it do the thing', fails 'did it respect the limits'; high severity.
### 8. Tool-call errors
      - Calls the wrong tool, with hallucinated arguments, at the wrong time, or in a loop — and misreads the result.
      - Mechanism: tool use is learned statistical behavior, not guaranteed execution.
      - High severity — failures stop being text and become actions (M8/M9).
### 9. Goal misspecification in the wild
      - Does what was literally asked, not meant ('optimize the dashboard' → deletes the data).
      - Signature: the user is furious and the agent is technically correct.
      - High severity in autonomous settings → human handoff (M10/M13) + governance (M15).
### Contested boundaries
      - **Instruction Drift vs. Position Bias — the two labels are one failure** · kind: debate-pair
        - for: `04-instruction-drift-vs-05-position-bias-for.md`
        - against: `04-instruction-drift-vs-05-position-bias-against.md`
      - **Class 6 or Class 4? The Mistake We Are Already Making** · kind: debate-pair
        - for: `06-reasoning-load-vs-04-instruction-drift-for.md`
        - against: `06-reasoning-load-vs-04-instruction-drift-against.md`
      - **Class 6 — "Shorten the chain": the corrected worked example** · kind: worked-example
        - Corrects 'shorten the chain': chain depth = derivations between model and answer, not tool calls.
        - The original conflated two task kinds; the corrected probe is a worked example with readings.
## Attribution: "the model failed" is usually "the harness set it up to fail"
    - Three candidate causes: model capability (rare), harness design (the overwhelming majority), environment (adversarial input).
    - ~80% of 'model failures' trace to harness layers; even capability limits are harness problems (don't rely on the model where weakest).
    - The reframe is engineering discipline, not PR — 'which valve let the pressure escape'.
## Failure class → harness layer map
    - Table: each of the 9 classes → primary + secondary harness layers (M4…M15).
    - Read backwards: each module's failure modes are pre-written here (e.g. M5 = classes 1/2 leaking through context).
## Real incidents — the catalog in the wild
    - Public, documented incidents, one per failure family, each rooted in a harness layer — not 'the AI'.
    - Meta-lesson: nobody needed a better model; they needed a missing/thin/over-trusted harness layer ($76k Tahoe, a tribunal ruling, a $100B typo).
    - Tradeoff: trust-vs-verify is a function of consequence, not model quality.
    - [details] <strong>1. Legal liability & court sanctions</strong>
    - [details] <strong>2. Hallucinated citations & fabricated facts (professional/academic)</strong>
    - [details] <strong>3. Prompt injection & RCE (the attack surface)</strong>
    - [details] <strong>4. Supply chain & dependency compromise</strong>
    - [details] <strong>5. Data exfiltration & confidentiality</strong>
    - [details] <strong>6. Guardrails, safety & misbehavior (governance)</strong>
    - [details] <strong>7. Destructive & irreversible actions (tool boundaries)</strong>
    - [details] <strong>8. Runaway loops, cost & reliability (orchestration + ops)</strong>
## What failure science gives the harness engineer
    - A design method (start from the failure catalog, fault-tree style).
    - A language ('sycophancy', 'drift' = precise diagnoses → work items).
    - A humility baseline (make irreducible failures cheap: caught, contained, visible, recoverable).
## Design exercise
    - For 3 scenarios: name failure class(es), attribute the cause, name harness layers + what 'caught' looks like, write the root-cause line you'd refuse.
    - Stretch: full 4-part analysis of a catalog incident.
    - [details] <strong>Answers — Scenario A (the summarizer that dropped the liability clause)</strong>
    - [details] <strong>Answers — Scenario B (the reviewer who agrees)</strong>
    - [details] <strong>Answers — Scenario C (the escalation that didn't)</strong>
    - [details] <strong>Answers — Stretch (Chevrolet Tahoe, sold for $1)</strong>
  - **Task State Across Domains** · kind: framework-matrix
    - canonical: `task-state-across-domains.md`
    - **Task State Across Domains** · kind: framework-domain
      - Framework = 5 steps: concrete task state → identification → lock-in detection → re-grounding → mirror-probe-trivial.
      - Cross-domain verdict: survives as a context-stability/escalation scaffold, fails as a decision engine.
    - **Task-state framework, stress-tested: portfolio rebalancing / trade-instruction agent** · kind: framework-domain
      - Survives as context hygiene (tames drift #4 + position #5); fails as a governance boundary (missing authority/irreversibility).
      - Fix = a human approval gate, which the framework cannot manufacture from task state.
    - **Task State Under Stress — Healthcare Prior-Authorization for Advanced Imaging** · kind: framework-domain
      - Fails as a decision engine; survives as a context-stability + escalation scaffold.
      - Root break: assumes task state is separable from context and losslessly reconstructable — medical necessity violates that by construction.
    - **Task-State Framework, Stress-Tested: Legal M&A Due-Diligence Red-Flag Agent** · kind: framework-domain
      - Survives only as a citation ledger (doc → clause → flag).
      - Collapses as a task-state scaffold: goal/open-questions merge, decisions hold almost nothing, mirror-probe-trivial is false.
    - **Task State vs. Root-Cause — a stress test** · kind: framework-domain
      - Survives as a control/authorization ledger; fails as investigation memory.
      - Worst break: missing 'direction' slot — the schema can't track the one field the domain turns on.