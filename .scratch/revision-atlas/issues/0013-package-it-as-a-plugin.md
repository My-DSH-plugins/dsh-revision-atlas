# 0013 — Package it as a plugin (DSH, then Claude Code)

- **Blocked by:** 0012
- **Blocks:** —
- **Status:** OPEN — not a valid plugin for either host yet

## Current state

The repo is a Python package plus design docs (`src/revision_atlas`, `SPEC.md`,
`CONTEXT.md`, `adr/`, `prototype/`). It has **no** `package.json`,
`cordis.patch.yml`, entry module, `SKILL.md`, or `.claude-plugin/`, so neither
`dsh plugin add` nor Claude Code can load it.

## DSH — four artifacts

Modelled on the working siblings `dsh-web-artifact-designer-english` (minimal
skill-only shape, no build step) and `dsh-handwritten-notes` (ships tools + skills).

1. **`package.json`** — the host-specific field is
   `"dsh": { "bundle": { "patch": "./cordis.patch.yml" } }`, plus `name` (matching
   the plugin row id), `version`, `license`, `type: module`, `main`, `exports`, and
   a `files` whitelist.
2. **`cordis.patch.yml`** — registers the row with the profile roster
   (`- insert: [{ id: revision-atlas, name: dsh-revision-atlas }]`). Installed with
   `dsh plugin --profile <profile> add <npm|git|link>` — **git works, so no npm
   publish is required to install it**.
3. **Entry module** — exports `name`, `inject: ['skills']`, and `apply(ctx)`
   calling `ctx.skills.registerProvider(...)`. Follow the sibling that auto-
   discovers `skills/*/SKILL.md` and re-reads on each call, so editing a skill body
   needs no restart and no build step.
4. **`skills/revision-atlas/SKILL.md`** — YAML frontmatter (`name` kebab-case,
   `description`); the reference loader throws without it. A skill's `resourceBase`
   is its own directory, so the Python package must live **inside** the bundle
   (e.g. `skills/revision-atlas/tools/revision_atlas/…`), not at the repo root.

## Claude Code — one file

Per the plugin reference: the manifest is optional, and if present `name` is the
only required field. `.claude-plugin/plugin.json` with `name` + `description` +
`version`, and `skills/revision-atlas/SKILL.md` (same layout, same frontmatter).
Validate with `claude plugin validate`.

**The `skills/<name>/SKILL.md` contract is identical on both hosts**, so one
skills tree serves both — DSH's extras are only `package.json` (the `dsh` field),
`cordis.patch.yml`, and the entry module.

## Acceptance

- `dsh plugin --profile <p> add <path-or-git-url>` installs it; the skill appears
  in `/` completion and the skill picker; `/revision-atlas` loads it.
- The bundled Python runs from the installed location (not from a dev checkout).
- `claude plugin validate` passes; the plugin loads in Claude Code and the skill
  invokes.
- Repo root still works for development (`PYTHONPATH=src python3 -m …`).
