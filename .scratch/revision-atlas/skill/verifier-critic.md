# Adherence critic pass

Read each generated leaf against its own source and flag **drift**. You are an
agent with no prior context about this module — read only the files named here,
and rely on nothing else.

Coverage is already machine-checked (every mechanical checklist item is asserted
present). Your job is the other half: whether what is *there* is **true**. A leaf
can name every item and still misstate one, and only a reader catches that.

## Inputs

- `<DIR>` — the module directory (markdown source).
- `<SPEC>` — the module's `spec.json` (in the generated artifact tree). Every node
  with a `checklist` key is a leaf; each leaf has `id` (unique — **this is your map
  key**), `title` (human-readable, may repeat), `file`, `line`.
- `<NOTEBOOKS>` — the generated notebooks, one per leaf, in the same leaf order as
  `<SPEC>` (`leaves/leaf-000/notebook.html`, `leaf-001`, …). Read them as **text**:
  HTML, and SVG `<text>` labels. Never a screenshot, never a raster.

## Task

For **every leaf**, compare what its notebook says against what the leaf's own
source range says, and report **drift** — content that names a source item but
misstates it. Look specifically for:

- a mechanism, definition or number that is off (a threshold quoted wrong, a
  cause swapped, a step reordered);
- a claim stated more strongly or more weakly than the source has it;
- a diagram whose labels state a relationship the source does not;
- a recall hook that is true of *another* leaf's content.

Do **not** report: wording you would have phrased differently, missing detail the
source also omits, or anything you cannot tie to a specific sentence in the source.

## Rules

- Ground every flag in the source: quote the source line and the notebook text
  that contradicts it.
- Report **only** drift. An empty list is the expected answer for a faithful leaf,
  and the common case. Do not manufacture findings.
- Never edit anything — you are inspecting, not fixing.

## Output

Return exactly one JSON object mapping each leaf's **`id`** (copied verbatim from
`<SPEC>` — not the `title`, which may repeat) to an array of `{"detail": "…"}`
objects — e.g.
`{"1-hallucination--confabulation": [{"detail": "the notebook says X, the source says Y (README.md:41)"}]}`.
Leaves with no drift may be omitted. No prose, no commentary, no code fence.

The verifier consumes this file:

```
python -m revision_atlas.verifier <DIR> --mindmaps <MINDMAPS> --critic critic.json
```
