# 0011 — The map reaches the notebooks (and resolves)

- **Blocked by:** 0004, 0006, 0008
- **Blocks:** —
- **Status:** done

## The defect

Two gaps, both in the map — the one surface a reader actually navigates:

- **The map linked to no notebook.** `grep -c "leaves/" index.html` → **0**. Every
  leaf rendered its recall, diagrams, self-test and source audit inline, but the
  paged notebook — the artifact this whole pipeline exists to produce — was
  reachable only by knowing the positional scheme and hand-typing a URL.
- **Every source link was dangling.** All 20 distinct hrefs were bare
  `README.md#<anchor>`, resolving against the map's own directory →
  `mindmaps/<slug>/README.md`, which does not exist. The source is at
  `modules/<slug>/README.md`, so the resolving form from the map is
  `../../modules/<slug>/README.md#<anchor>`. Measured: **20 of 20 fail**.

The notebooks themselves were fine (20 files, ~222 KB each, verified present) —
nothing could reach them.

## Root cause

`render_map(spec)` took only the spec, so it had:

- no **base path** — where the map sits relative to the module markdown, and
- no **leaf → directory mapping** — the dirs were positional (`leaf-{i:03d}`),
  assigned inside `generate_all` and never recorded on the node.

Meanwhile SPEC §13 already specified `leaves/<leaf-id>/`. The code diverged from
the spec, and the divergence is what made the link unbuildable.

## Fix

1. **`spec_writer.leaf_dir_id(node)`** — the stable directory name from the leaf's
   unique id (0008 made it unique). A long heading is truncated to 80 chars with a
   hash of the full id, so it stays a valid path component and stays unique. Both
   the generator and the map derive the name from the same function, so the link
   cannot drift from what was written.
2. **`generate_all`** writes `leaves/<leaf-id>/notebook.html`; **`verifier`** looks
   for the same name (it had its own copy of the positional scheme — the coupling
   that would have silently broken the artifact check).
3. **`render_map(spec, leaves_prefix, source_base)`** — each leaf gets a
   `notebook` link beside its source anchor, and source anchors are built as
   `source_base + file + #id`, percent-encoded (`quote`) so a module named
   `Harness Engineering` still produces a valid href.
4. **`renderer.source_base_for(module_dir, map_dir, override)`** — derived from the
   real layout rather than hard-coded. §13 puts `mindmaps/<slug>/` beside
   `modules/<slug>/`, so the two paths already answer it; `--source-base` covers a
   tree deployed without the source.
5. **`verifier._check_links`** — §14's "broken anchors", now real. Internal links
   (notebooks, shared assets) fail the build; source links that leave the tree are
   `needs-review` with the remedy. This is the check that would have caught the
   original defect at build time.

## Evidence — deterministic

The cold passes were deliberately not re-run (no M5 artifact was reused). Verified
with synthetic fixtures built in the §13 layout:

- map hrefs: `../../modules/05-demo/README.md#mod`, `…/#section-one`,
  `leaves/mod/notebook.html`, `leaves/section-one/notebook.html` — **all resolve**;
  before the fix, 20 of 20 source hrefs did not.
- leaf dirs written: `mod`, `section-one` — ids, not `leaf-000`/`leaf-001`.
- inserting a new section above `section-one` leaves its directory and notebook in
  place (the failure mode a positional name has).
- verdict **PASS**; a deliberately corrupted notebook href → **FAIL** with a
  `links` finding; moving the source tree away → PASS with the source links as
  `needs-review`, not failures.
- 61 tests green (4 new: resolvable links, dir stability on insert, broken link is
  a failure, source-off-tree is a note).

## Not done

- §13's `diagram.svg` / `diagram.mmd` per leaf are still unbuilt (mermaid is
  inlined as data URIs), as are `atlas.yml` and `og/`; `spec.json` is written as
  `spec.json`.
- Fragments are not asserted (see SPEC §14): a wrong `#anchor` still opens the
  right file, and GitHub's own slug rule is not ours to replicate.
