"""Agentic draft: semantic checklist claims for M2's leaves (ticket 0003 demo).

Each leaf title maps to the claim strings the agent distilled from the source —
the "must survive" semantic content, on top of the deterministic seed
(collapsibles + mermaid). This is the agent-pass input to `build_structure`.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from revision_atlas.extractor import extract
from revision_atlas.spec_writer import build_structure

M2 = "/Users/akshayprabhakant/github/GenAI_notes/Harness Engineering/modules/02-model-failure-science"

M2_SEMANTIC = {
    "Opening scene — the postmortem that wasn't": [
        "Ordering agent approved a 40% discount it had no authority to give; root cause read \"the model hallucinated the discount policy\".",
        "Real failure: it followed the most salient instruction (a customer message) that was allowed to outrank standing policy — nothing separated policy from data.",
        "\"The model hallucinated\" was a category error — the cheapest way to avoid naming the harness gap.",
    ],
    "The uncomfortable fact: models fail systematically, not randomly": [
        "An LLM optimizes plausibility of continuation, not truth or intent-fidelity → failures are structural, predictable patterns.",
        "Four signatures: fluent-but-wrong, agreeable, fragile outside distribution, follows the loudest (not most important) instruction.",
        "Which failure reaches a user (with what consequence) is entirely a harness question; some confabulation is irreducible.",
    ],
    "1. Hallucination & confabulation": [
        "Fluent, confident output that is false — incl. justified falsehood, invented citations, fabricated tool results.",
        "Mechanism: most-plausible-continuation; cannot distinguish 'in training data' from 'true'.",
        "Danger: wrongness that reads as rightness (hardest to catch); severity high.",
    ],
    "2. Sycophancy": [
        "Agrees / flatters / gives the answer the user seems to want, even when wrong.",
        "Mechanism: agreement rewarded in training → generalizes to 'what this user wants to hear'.",
        "Signature: the answer flips when the user states a preference first; high severity in judgment roles.",
    ],
    "3. Brittleness & shallow pattern-matching": [
        "Correct for the wrong reasons; competence evaporates under paraphrase / reorder / novel phrasing.",
        "Mechanism: shortcut learning on surface cues; 'works in my tests' = the test set encoded the shortcuts.",
        "Medium-high severity; the mechanism behind eval overfitting.",
    ],
    "4. Instruction drift & compliance decay": [
        "Follows early instructions better than later ones; long/layered policy decays.",
        "Mechanism: attention diluted across context — policy at token 3000 is less salient than the customer message at 3001.",
        "Signature: obeys in a short session, violates in a long one; high severity.",
    ],
    "5. Position & ordering bias": [
        "'Lost in the middle': attends best to the start/end of context, worst to the middle.",
        "Signature: move the same fact middle→end and correctness flips.",
        "Medium severity; compounds with #4; cheaply fixable in context assembly (M4).",
    ],
    "6. Reasoning degradation under load": [
        "Multi-step reasoning decays as complexity grows (more steps/tools/chains), even for 'smart' models.",
        "Mechanism: no persistent scratchpad; intermediate results live in lossy attention; error compounds.",
        "Signature: 2-step flawless, 9-step fails at step 6; high severity — design fix (scratchpads/sub-agents/verification).",
    ],
    "7. Overlooked constraints": [
        "Satisfies the salient goal, silently violates surrounding constraints (2 a.m. flight; omitted liability clause).",
        "Mechanism: constraint saturation — optimizes the salient objective, treats constraints as soft/later.",
        "Signature: passes 'did it do the thing', fails 'did it respect the limits'; high severity.",
    ],
    "8. Tool-call errors": [
        "Calls the wrong tool, with hallucinated arguments, at the wrong time, or in a loop — and misreads the result.",
        "Mechanism: tool use is learned statistical behavior, not guaranteed execution.",
        "High severity — failures stop being text and become actions (M8/M9).",
    ],
    "9. Goal misspecification in the wild": [
        "Does what was literally asked, not meant ('optimize the dashboard' → deletes the data).",
        "Signature: the user is furious and the agent is technically correct.",
        "High severity in autonomous settings → human handoff (M10/M13) + governance (M15).",
    ],
    "Attribution: \"the model failed\" is usually \"the harness set it up to fail\"": [
        "Three candidate causes: model capability (rare), harness design (the overwhelming majority), environment (adversarial input).",
        "~80% of 'model failures' trace to harness layers; even capability limits are harness problems (don't rely on the model where weakest).",
        "The reframe is engineering discipline, not PR — 'which valve let the pressure escape'.",
    ],
    "Failure class → harness layer map": [
        "Table: each of the 9 classes → primary + secondary harness layers (M4…M15).",
        "Read backwards: each module's failure modes are pre-written here (e.g. M5 = classes 1/2 leaking through context).",
    ],
    "Real incidents — the catalog in the wild": [
        "Public, documented incidents, one per failure family, each rooted in a harness layer — not 'the AI'.",
        "Meta-lesson: nobody needed a better model; they needed a missing/thin/over-trusted harness layer ($76k Tahoe, a tribunal ruling, a $100B typo).",
        "Tradeoff: trust-vs-verify is a function of consequence, not model quality.",
    ],
    "What failure science gives the harness engineer": [
        "A design method (start from the failure catalog, fault-tree style).",
        "A language ('sycophancy', 'drift' = precise diagnoses → work items).",
        "A humility baseline (make irreducible failures cheap: caught, contained, visible, recoverable).",
    ],
    "Design exercise": [
        "For 3 scenarios: name failure class(es), attribute the cause, name harness layers + what 'caught' looks like, write the root-cause line you'd refuse.",
        "Stretch: full 4-part analysis of a catalog incident.",
    ],
    "Instruction Drift vs. Position Bias — the two labels are one failure": [
        "Claim: classes 4 & 5 are one attention-allocation failure described at two altitudes.",
        "Decision: one context-assembly owner + standing reorder-and-rerun test; record context-length, rule-position, winning-text on every ticket.",
        "Falsifiable: next long-context incident triaged in hours, not a quarter.",
    ],
    "Class 4 and Class 5 Are Not Confusable": [
        "Claim: separated by the failure curve — drift worsens with length, position flips with order.",
        "Decision: two owners (placement vs instruction/memory); believe only with sweep/substitution/short-session controls.",
    ],
    "Class 6 or Class 4? The Mistake We Are Already Making": [
        "Claim: at postmortem time, evidence cannot separate 6 from 4 — confusion is the default read.",
        "Decision: fund disambiguation probes (reorder/paraphrase + scratchpad ablation), name both classes per ticket, record chain-depth + instruction-distance.",
    ],
    "Class 6 vs Class 4: separable mechanisms, and the discriminator is one probe away": [
        "Claim: separable by a cheap in-session discriminator (re-injection probe; externalized-vs-monolithic; first-error-vs-derived).",
        "Decision: fund whichever layer the four-cell control points at — not both on the same evidence.",
    ],
    "Class 6 — \"Shorten the chain\": the corrected worked example": [
        "Corrects 'shorten the chain': chain depth = derivations between model and answer, not tool calls.",
        "The original conflated two task kinds; the corrected probe is a worked example with readings.",
    ],
    "Task State Across Domains": [
        "Framework = 5 steps: concrete task state → identification → lock-in detection → re-grounding → mirror-probe-trivial.",
        "Cross-domain verdict: survives as a context-stability/escalation scaffold, fails as a decision engine.",
    ],
    "Task-state framework, stress-tested: portfolio rebalancing / trade-instruction agent": [
        "Survives as context hygiene (tames drift #4 + position #5); fails as a governance boundary (missing authority/irreversibility).",
        "Fix = a human approval gate, which the framework cannot manufacture from task state.",
    ],
    "Task State Under Stress — Healthcare Prior-Authorization for Advanced Imaging": [
        "Fails as a decision engine; survives as a context-stability + escalation scaffold.",
        "Root break: assumes task state is separable from context and losslessly reconstructable — medical necessity violates that by construction.",
    ],
    "Task-State Framework, Stress-Tested: Legal M&A Due-Diligence Red-Flag Agent": [
        "Survives only as a citation ledger (doc → clause → flag).",
        "Collapses as a task-state scaffold: goal/open-questions merge, decisions hold almost nothing, mirror-probe-trivial is false.",
    ],
    "Task State vs. Root-Cause — a stress test": [
        "Survives as a control/authorization ledger; fails as investigation memory.",
        "Worst break: missing 'direction' slot — the schema can't track the one field the domain turns on.",
    ],
}


def walk(node):
    yield node
    for b in (node.get("branches") or {}).values():
        yield from walk(b)
    for c in node.get("children", []):
        yield from walk(c)


if __name__ == "__main__":
    out = build_structure(extract(M2), semantic=M2_SEMANTIC)
    plan = out["plan_md"]
    dest = Path(__file__).resolve().parent / "m2-plan.md"
    dest.write_text(plan, encoding="utf-8")

    leaves = [n for n in walk(out["root"]) if "checklist" in n]
    empty = [n["title"] for n in leaves if not n["checklist"]]
    claim_leaves = sum(1 for n in leaves if any(i["kind"] == "claim" for i in n["checklist"]))
    print(f"leaves={len(leaves)} with_claims={claim_leaves} empty={len(empty)}")
    if empty:
        print("STILL EMPTY (title mismatch?):", empty)
    print("wrote:", dest)
