# alin-skills Quickstart

Shared Claude Code skills for the ALIN lab. Full guide: [GUIDE.md](GUIDE.md) · 한국어: [QUICKSTART.ko.md](QUICKSTART.ko.md)

## 1. Get access

Ping Woomin with your GitHub username. Accept the collaborator invite GitHub emails you.

## 2. Install

alin-skills is a **Claude Code plugin** named `alin`. Install it from inside a Claude Code session — no cloning, no copying:

```text
/plugin marketplace add alinlab/alin-skills
/plugin install alin@alin-skills
```

Because the repo is private, both commands work only if your GitHub account has access (Step 1). Claude Code clones the marketplace with your existing git credentials, so the same auth that lets you `git clone` lets you install. Then run `/reload-plugins` (or start a fresh session) and the skills go live.

Every skill is namespaced `/alin:<skill-name>` (e.g. `/alin:hwpx`), and Claude auto-routes to them by description. Type `/alin:` and let autocomplete list all of them. Don't need a skill on this machine (e.g. the macOS-only `kakaotalk-mac` on a Linux box)? Just don't invoke it — there's no per-skill install step.

## 3. Update

```text
/plugin marketplace update alin-skills
```

This pulls the latest catalog + plugin from GitHub. Run `/reload-plugins` afterward. For **silent auto-updates at startup** (private repos skip these by default), add a token with repo read access to your shell config:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

## 4. Share a skill you built

Contributing still works through a clone + PR (you're editing the repo, not just using it). Clone once:

```bash
git clone https://github.com/alinlab/alin-skills.git ~/code/alin-skills
```

Then, in a Claude Code session with your project open:

> Add the `<skill-name>` skill from this project to alin-skills at `~/code/alin-skills`, following the "Add a new skill" guidance in CONTRIBUTING.md. Commit on a branch but don't push yet.

Claude Code will adapt the skill, add it under `skills/`, update the README table, test it by loading the clone with `claude --plugin-dir`, and commit on a branch. To finish publishing:

> Push the branch and open a pull request against main.
