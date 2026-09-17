/**
 * dsh-revision-atlas — a DeepSeek Harness skill plugin.
 *
 * Registers every `skills/<name>/SKILL.md` in this package on `ctx.skills`, so the
 * skills ship with the profile and are invocable via `dsh plugin add` rather than
 * being copied into ~/.dsh/skills by hand. The provider re-reads the skill files on
 * every discovery/load, so editing a SKILL.md body needs no restart.
 *
 * The `build-module-map` skill ships the Python pipeline under
 * `skills/build-module-map/tools/`, invoked as
 * `PYTHONPATH=<base>/tools python3 -m revision_atlas…` — `<base>` is the skill's own
 * directory, announced by the host as `<skill_resources>`.
 *
 * @module dsh-revision-atlas
 */
import { readdirSync, readFileSync } from 'node:fs'
import { readdir, readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const PROVIDER = 'dsh-revision-atlas'
// mirrors @deepseek-ai/dsh-skill's BUNDLED_SKILL_RANK
const RANK = 600
const SKILL_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const SKILLS_ROOT = fileURLToPath(new URL('./skills/', import.meta.url))

export const name = PROVIDER
export const inject = ['skills']

export function apply(ctx) {
  if (loadSkillsSync().length === 0) {
    throw new Error(`${PROVIDER}: no SKILL.md bundles under ${SKILLS_ROOT}`)
  }
  ctx.skills.registerProvider(() => ({
    name: PROVIDER,
    async list(options) {
      throwIfAborted(options?.signal)
      return (await loadSkills(options?.signal)).map(toCandidate)
    },
    async get(candidate, options) {
      throwIfAborted(options?.signal)
      const skill = (await loadSkills(options?.signal)).find(
        (s) => s.name === candidate.name,
      )
      return skill ? toDefinition(skill) : undefined
    },
  }))
}

async function loadSkills(signal) {
  const skills = []
  for (const entry of await readdir(SKILLS_ROOT, { withFileTypes: true })) {
    if (!entry.isDirectory() && !entry.isSymbolicLink()) continue
    throwIfAborted(signal)
    const directory = join(SKILLS_ROOT, entry.name)
    skills.push(parseSkill(await readFile(join(directory, 'SKILL.md'), 'utf8'), directory))
  }
  return skills.sort((a, b) => a.name.localeCompare(b.name))
}

function loadSkillsSync() {
  const skills = []
  for (const entry of readdirSync(SKILLS_ROOT, { withFileTypes: true })) {
    if (!entry.isDirectory() && !entry.isSymbolicLink()) continue
    const directory = join(SKILLS_ROOT, entry.name)
    skills.push(parseSkill(readFileSync(join(directory, 'SKILL.md'), 'utf8'), directory))
  }
  return skills
}

function parseSkill(raw, directory) {
  const { data, body } = parseFrontmatter(raw)
  const skillName = str(data.name)
  const description = str(data.description)
  if (!skillName || !description) {
    throw new Error(`${PROVIDER}: ${directory}/SKILL.md needs name and description in frontmatter`)
  }
  if (!SKILL_NAME.test(skillName)) {
    throw new Error(`${PROVIDER}: invalid skill name "${skillName}"`)
  }
  return {
    name: skillName,
    description,
    invocation: { modelInvocable: true, userInvocable: true },
    provider: PROVIDER,
    source: 'bundled',
    resourceBase: { kind: 'directory', path: directory },
    rank: RANK,
    content: body.trim(),
  }
}

// The frontmatter is two scalar keys on single lines; no YAML dependency for that.
function parseFrontmatter(raw) {
  if (!raw.startsWith('---')) return { data: {}, body: raw }
  const end = raw.indexOf('\n---', 3)
  if (end === -1) return { data: {}, body: raw }
  const head = raw.slice(3, end)
  const data = {}
  for (const line of head.split('\n')) {
    const i = line.indexOf(':')
    if (i > 0) data[line.slice(0, i).trim()] = line.slice(i + 1).trim()
  }
  return { data, body: raw.slice(end + 4).trim() }
}

function str(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : ''
}

function toCandidate(s) {
  return {
    name: s.name,
    description: s.description,
    invocation: s.invocation,
    provider: s.provider,
    source: s.source,
    resourceBase: s.resourceBase,
    rank: s.rank,
  }
}

function toDefinition(s) {
  return { ...toCandidate(s), content: s.content }
}

function throwIfAborted(signal) {
  if (signal?.aborted) throw signal.reason ?? new Error('aborted')
}
