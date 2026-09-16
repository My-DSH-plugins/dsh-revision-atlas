# Diagrams are mermaid, rendered at build time — the hand-drawn sketch path is removed

---
Status: accepted
---

ADR-0003 made hand-drawn the default diagram kind (mermaid only where exactness
mattered), and ADR-0004 built a deterministic geometry invariant for a
hand-rolled sketch renderer. Implementing that renderer (0005) surfaced two facts
that reverse the premise:

1. **Hand-rolling graph layout + edge routing is a rabbit hole.** The `cycle`
   template drew arrows "bottom-centre → top-centre", which is correct for a
   vertical stack and nonsense on a ring — arrows exited/entered boxes at
   arbitrary, mismatched points. That routing bug is exactly the problem a real
   layout engine (dagre, already inside mermaid) solves for free.
2. **"Mermaid in the notes isn't interactive" is false.** The notebook is HTML;
   a static build-time SVG (adr/0002) plus a tiny pan/zoom script gives
   zoom / reset / click-drag offline — without shipping the 3.4 MB `mermaid.js`
   that adr/0002 refused.

So the correct boundary is: **mermaid owns layout and edge routing**; the atlas
must not reimplement a graph engine.

## Decision

- **Diagrams are mermaid only.** `flowchart` for exact structure (decision
  procedures, state machines, multi-branch sequences); `mindmap` for the
  intuition / taxonomy cases that "hand-drawn" used to cover. Rendered to static
  SVG at build time (adr/0002), inlined into the map and notebook; the notebook
  adds a small pan/zoom wrapper for interactivity.
- **Diagram kind is `mermaid | none`.** The deterministic classifier extracts
  source ```mermaid blocks (near-zero cost) and defaults everything else to an
  empty `diagrams: []`. The agent may *propose* a mermaid diagram
  (`flowchart`/`mindmap`) for a leaf, Gate-2-gated, stored in `plan.md` with its
  diffable `.mmd` source.
- **PDF export legibility is the one accepted loss.** A dense static SVG prints
  illegibly; mitigate by keeping diagrams sparse (1–5 nodes), and accept the rest.

## Supersedes

- **adr/0003** — its "hand-drawn default" is reversed; its "mermaid when free or
  exactness-critical" half is absorbed into this decision.
- **adr/0004** — retired. The geometry invariant existed only because we hand-rolled
  layout; dagre/mermaid now owns geometry, so the invariant machinery is deleted.

**adr/0002 (build-time mermaid rendering) is unchanged** and now governs *all*
diagrams, not just the source-authored ones.

## Consequences

- `sketch.py`, its tests, and the hand-drawn font vendoring are removed. The
  diagram "content pass" becomes agent-authored `.mmd`, not a JSON topology.
- Correct layout and edge routing by construction (mermaid), a smaller codebase,
  and no vision pass in the loop (mermaid renders are deterministic).
- The agent's diagram skill is now *"write the right mermaid for this leaf"* —
  a narrower, more testable job than *"author a hand-drawn topology."*

## When to revisit

- If a genuinely non-graph diagram need arises that mermaid cannot express
  (rare — flowchart/mindmap/sequence/state cover nearly all), reconsider a
  custom renderer under a fresh ADR.
- If PDF export becomes a hard requirement, revisit static SVG vs a raster or
  print-oriented export — **not** hand-drawn.
