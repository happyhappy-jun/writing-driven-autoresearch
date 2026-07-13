# Contributing to alin-skills

This repo is a shared pool of Claude Code skills for the ALIN lab. If a skill saves you time, publish it so it saves someone else time too.

The whole repo is packaged as a single **Claude Code plugin** named `alin`, distributed through the marketplace defined in `.claude-plugin/marketplace.json`. Members install it with `/plugin install alin@alin-skills` (see [QUICKSTART.md](QUICKSTART.md)); they never copy files by hand. Contributing, though, is still plain git: add or edit a `SKILL.md` under `skills/`, test the clone with `claude --plugin-dir`, and open a PR.

---

## Repo layout

```
alin-skills/
├── .claude-plugin/
│   ├── plugin.json        # plugin manifest (name: alin, version)
│   └── marketplace.json   # marketplace catalog (one plugin: alin, source ".")
├── README.md              # skill catalog
├── CONTRIBUTING.md        # this file
├── GUIDE.md / GUIDE.ko.md # human-facing walkthrough
├── QUICKSTART.md / .ko.md # 4-step quickstart
└── skills/
    └── <skill-name>/
        ├── SKILL.md       # required
        └── scripts/       # optional helpers (shell, python, ...)
```

Every skill lives at `skills/<skill-name>/SKILL.md`. The skill's folder name becomes its invocation name, namespaced by the plugin: `skills/hwpx/` → `/alin:hwpx`. Add a new skill by creating a new folder; update one by editing in place. Don't put anything under `.claude-plugin/` except the two manifests — component directories like `skills/` must stay at the repo root.

---

## Add a new skill

1. **Branch:** `git checkout -b add-<skill-name>`
2. **Create the folder:** `mkdir -p skills/<skill-name>/scripts` (the `scripts/` subfolder only if you need helpers).
3. **Write `skills/<skill-name>/SKILL.md`** using the template below.
4. **Make shell helpers executable:** `chmod +x skills/<skill-name>/scripts/*.sh` (git preserves the bit).
5. **Add a row to the README skills table**, inside the `<!-- skills-table:start -->` / `<!-- skills-table:end -->` markers, under the appropriate category group (Document & Writing, Literature & Related Work, Peer Review, Experiment & HPC, Developer Tooling, Misc).
6. **Test locally.** Load the clone as a plugin: `claude --plugin-dir /path/to/alin-skills`, then invoke `/alin:<skill-name>` (run `/reload-plugins` after edits). Iterate until the skill fires and does what you want. Optionally run `claude plugin validate /path/to/alin-skills` to sanity-check the manifests.
7. **Commit, push, PR.**

## Update an existing skill

Edit `skills/<skill-name>/SKILL.md` in place. **Don't rename the folder or change the `name:` frontmatter field** — that's the skill's identity (and its `/alin:<name>` invocation). Only update the README row if the one-sentence summary is genuinely wrong now. Test with `claude --plugin-dir /path/to/alin-skills` + `/reload-plugins`. Commit, push, PR.

## Remove a skill

`git rm -r skills/<skill-name>`, delete the corresponding README row, commit with a short "why" in the message.

## Releasing (how updates reach users)

`.claude-plugin/plugin.json` intentionally has **no `version` field**, so Claude Code uses the git commit SHA as the version. The effect: **every merge to `main` auto-propagates** — users get it the next time they run `/plugin marketplace update alin-skills` (or automatically at startup if they've set `GITHUB_TOKEN`). There's no version-bump ritual; merging the PR *is* the release. Because of this, keep `main` shippable — a half-baked merge reaches everyone, so prefer landing rough work on a branch until it's ready. Run `claude plugin validate .` before you push.

> **If you ever want controlled releases instead:** add a `version` field (semver) to `plugin.json`. Then users only receive changes when that version is bumped, letting you batch PRs into deliberate releases at the cost of the zero-friction propagation above. Pick one model and keep it consistent.

---

## SKILL.md template

```markdown
---
name: <skill-name>
description: One-sentence English description. Claude uses this exact field to route invocations, so be specific about inputs, outputs, and when to use it. Vague descriptions mean the skill never fires.
license: MIT
metadata:
  category: <document-writing|literature|peer-review|experiment-hpc|developer-tooling|misc>
  locale: ko-KR   # optional, only if the skill is language-specific
---

# <Human-Readable Skill Name>

## What this skill does
Two or three sentences. Lead with the concrete action, not the motivation.

## When to use
- "example user request in natural language"
- "another example that would trigger this skill"

## When not to use
- situations where a different skill or plain Claude is better

## Prerequisites
- required tools, permissions, env vars, credentials

## Workflow
### 1. First concrete step
### 2. Next step
### 3. ...

## Done when
- clear completion criteria — the model uses these to decide it's finished

## Notes
- anything else a future reader or editor needs
```

### Style rules

- **`description` must be English** (unambiguous for model routing). Body can be Korean or English — match the natural language of the task.
- Keep sections tight. Link to external docs instead of inlining tutorials.
- **Gate destructive or externally-visible actions** (sending messages, deleting files, writing to shared systems) behind explicit user confirmation in the workflow.
- **No project-specific or user-specific paths** in the skill body. To reference a bundled helper script, use **`${CLAUDE_SKILL_DIR}/scripts/...`** — this resolves to the skill's own directory whether it's installed as a plugin (read-only cache), at the project level, or under `~/.claude/skills/`. Never hardcode `~/.claude/skills/<name>/...`; that path is wrong once the skill ships as a plugin. Anything else must come from user input or the current working directory. Note `${CLAUDE_SKILL_DIR}` is **not** set outside Claude Code (e.g. in a cron job) — for those, tell the user to substitute an absolute path.
- **Don't write persistent state into the skill's own directory.** A plugin's files live in a read-only cache, so a skill that needs to remember things across runs (logs, learned data, caches) must write to the project dir, `~/.claude/`, or another user-writable location — not next to its own `SKILL.md`.

---

## Agent guidance

When a user asks Claude Code to do one of these tasks against an alin-skills clone, follow the short rules below. These are guidelines, not a rigid checklist — apply judgment.

### Installing the plugin for an end user

End users do **not** install via file copying anymore. The flow is, inside a Claude Code session:

```text
/plugin marketplace add alinlab/alin-skills
/plugin install alin@alin-skills
```

then `/reload-plugins`. If a user asks you to "install alin-skills," point them at these commands (the repo is private, so they need GitHub access first). Do not copy skill directories into `~/.claude/skills/` — that's the old pre-plugin flow and produces un-namespaced duplicates.

### Testing a clone's skills (for contributors)

To verify a skill you've added or edited in a clone, load the clone as a plugin instead of copying files:

```text
claude --plugin-dir /path/to/alin-skills
```

Invoke `/alin:<skill-name>`; after further edits run `/reload-plugins`. Run `claude plugin validate /path/to/alin-skills` to check the manifests. Never copy the skill into `~/.claude/skills/` to test — that bypasses the plugin packaging the skill will actually ship under (e.g. `${CLAUDE_SKILL_DIR}` resolution).

### Adding a new skill from the user's current project to a clone

1. Read the source skill to understand what it does, what files it has, and what it depends on.
2. Copy it to `<clone>/skills/<skill-name>/`, preserving the `scripts/` subfolder layout.
3. Adapt `SKILL.md` to match the template in this file. Required frontmatter: `name`, `description` (English, specific), `license`, `metadata.category`. **Strip project-specific paths, credentials, and assumptions** that wouldn't hold for other lab members. Rewrite any reference to a bundled script as `${CLAUDE_SKILL_DIR}/scripts/...`, and move any persistent state the skill writes out of its own directory (the plugin cache is read-only).
4. `chmod +x` any shell helper scripts.
5. **Add a row to the README skills table** — inside the `<!-- skills-table:start -->` / `<!-- skills-table:end -->` markers, under the appropriate category group, don't touch other rows.
6. Test locally: load the clone with `claude --plugin-dir <clone>`, invoke `/alin:<skill-name>` (run `/reload-plugins` after edits), and verify it fires and works. Run `claude plugin validate <clone>` to check the manifests.
7. Show the user a summary of everything you did.
8. Commit on a `add-<skill-name>` branch. **Do not push or open a PR without explicit user confirmation.**

### Updating an existing skill in a clone

1. Confirm `<clone>/skills/<skill-name>/SKILL.md` exists. If not, this is an add task, not an update.
2. Read the current `SKILL.md` in full before writing anything.
3. Produce a short merge plan (what sections will change, what stays) and show it to the user before editing.
4. Apply the edit in place. **Never rename the folder, never change the `name:` frontmatter field.** If the skill's identity needs to change, that's a separate rename task.
5. Update the README row only if the one-sentence summary is now wrong.
6. Test locally the same way as for adds.
7. Show a diff summary and commit on `update-<skill-name>`. No push without explicit confirmation.

### Never do

- **Never copy skills into `~/.claude/skills/` to install or test.** That's the deprecated pre-plugin flow; it creates un-namespaced duplicates and bypasses `${CLAUDE_SKILL_DIR}` resolution. Use `/plugin install` (end users) or `claude --plugin-dir` (contributors).
- **Never edit the installed plugin cache** (`~/.claude/plugins/cache/...`) to change a skill. Edits there are lost on update; change the clone and PR.
- **Never copy credentials**, API keys, `.env` files, or user-specific paths from a source project into a shared skill.
- **Never change a skill's `name:` frontmatter field** during an update. It's the skill's identity.
- **Never push or open a PR without the user's explicit go-ahead.** Branch commits are fine; remote-visible actions are not.
- **Never `git reset --hard`, `git checkout -- .`, or any destructive git operation** to "fix" a dirty working tree. Ask the user — their edits might be in-progress work.
- **Never retry a failed `git clone` silently.** Credential failures (SSH passphrase, 2FA, HTTPS token) won't self-heal; surface the error and suggest the user clone manually in a terminal.

---

## Questions

Ping the lab channel or open an issue. Don't let uncertainty about "the right way" stop you from sharing a useful skill — we'll fix the shape in review.
