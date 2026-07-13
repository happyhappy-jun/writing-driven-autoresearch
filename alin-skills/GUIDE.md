# alin-skills: A Lab Member's Guide

*한국어 버전: [GUIDE.ko.md](GUIDE.ko.md)*

A friendly walkthrough of what alin-skills is, why we built it, and how to start using it through Claude Code.

---

## What is alin-skills?

alin-skills is a **shared repository of Claude Code skills** built by and for members of the ALIN lab.

A "Claude Code skill" is a small, self-contained recipe that teaches Claude Code how to do a specific task end-to-end — converting HWP files to Markdown, checking Korean spelling via the 국립국어원 checker, reading KakaoTalk chats on macOS, and so on. Each skill is just a `SKILL.md` file (plus optional helper scripts). alin-skills bundles all of them into a single **Claude Code plugin** named `alin`, which you install once from a marketplace. Claude Code discovers every skill automatically and picks the right one based on what you ask it to do; you can also call one directly by its namespaced name, like `/alin:hwpx`.

Think of skills as **reusable automations**: once someone figures out how to make Claude do task X reliably, they can package that knowledge as a skill, and everyone else gets it for free.

---

## Why we made this repo

Every lab member accumulates personal tricks for using Claude Code in their day-to-day research — formatting references, pulling data from government portals, linting paper drafts, converting 한글(HWP) documents a reviewer sent. Most of this knowledge lives only in individual heads. It gets reinvented over and over, and the clever workaround you wrote three months ago is already forgotten.

alin-skills exists to turn that private, scattered know-how into **shared collective intelligence**:

- If you figure out a useful workflow, **publish it as a skill** and the whole lab benefits.
- If someone else's skill is *almost* what you need, **adapt and improve it** — the next person gets the improved version.
- Over time, the repo grows into the lab's **institutional memory for agentic workflows** — a living record of what we've collectively taught Claude to do.

The design principle: make sharing and using skills so easy that publishing is strictly lower friction than keeping a workflow to yourself.

---

## How to use alin-skills

### Step 0: Get access to the repo

alin-skills lives at **[github.com/alinlab/alin-skills](https://github.com/alinlab/alin-skills)** as a **private repository**. Before you can clone or contribute, you need to be added as a collaborator.

**To request access**, send Woomin a message (Slack, KakaoTalk, email, or in person) with:

- Your GitHub username (e.g. `@your-handle`)
- A one-line note that you'd like to join alin-skills

Woomin will add you as a collaborator and GitHub will email you an invitation. Accept it, and you're ready to clone. The clone URL is:

```
https://github.com/alinlab/alin-skills.git
```

> If you get a "repository not found" or "permission denied" error, the invite hasn't been accepted yet or your local git isn't authenticated to GitHub. Accept the invite, run `gh auth login` if you use the GitHub CLI, and try again.

### (Optional) Install the GitHub CLI for smoother PR flow

Contribution workflows end with opening a pull request. Two options:

1. **Do nothing extra** — let Claude Code push your branch, then open the PR yourself in the GitHub webpage (one click from the "Compare & pull request" banner).
2. **Install the [GitHub CLI (`gh`)](https://cli.github.com/)** and let Claude Code run `gh pr create` for you — smoother if you'll contribute more than occasionally.

```bash
# macOS + Homebrew
brew install gh

# conda (cross-platform)
conda install -c conda-forge gh
```

After install, run `gh auth login` once. From then on, *"push and open a PR"* is handled in one step.

---

## Using alin-skills

Installing and updating happen entirely inside Claude Code with the `/plugin` commands — no cloning or file copying. Contributing (sharing or improving a skill) still goes through a clone and a PR, since you're editing the repo itself.

### A1. First-time setup (install on a new machine)

In a Claude Code session, run:

```text
/plugin marketplace add alinlab/alin-skills
/plugin install alin@alin-skills
```

The first command registers this repo as a marketplace; the second installs the `alin` plugin from it. Because the repo is **private**, both only work if your GitHub account has been granted access (Step 0). Claude Code clones the marketplace using your normal git credentials — the same SSH key or HTTPS token / `gh auth login` you'd use to `git clone` — so there are no interactive credential prompts to wrestle with.

When it finishes, run `/reload-plugins` (or just start a fresh session) and all the skills are live, each namespaced `/alin:<skill-name>`.

**Do I need to pick which skills to install?** No. The plugin installs all of them at once, but they cost almost nothing until invoked, and Claude only routes to a skill when your request matches its description. A macOS-only skill like `kakaotalk-mac` simply never fires on a Linux box. There's no per-skill install step anymore.

### A2. Pulling the latest updates

```text
/plugin marketplace update alin-skills
```

then `/reload-plugins`. That's it — it fetches the newest version straight from GitHub.

**Optional: silent auto-updates.** Claude Code can refresh marketplaces at startup, but for *private* repos it skips this unless it can authenticate non-interactively. To opt in, put a GitHub token with repo read access in your shell config (`~/.zshrc`):

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

Without the token nothing breaks — you just update manually with the command above.

### A3. Sharing a new skill with the lab

You've built a workflow in your own project — a helper script and a `SKILL.md` — and want to publish it. Contributing edits the repo, so clone it first (any path; this guide assumes `~/code/alin-skills`):

```bash
git clone https://github.com/alinlab/alin-skills.git ~/code/alin-skills
```

Then, in a Claude Code session with your source project open:

> I have a skill at `<path-to-source-skill>` in this project. Please add it to alin-skills at `~/code/alin-skills`, following the "Add a new skill" guidance in the clone's `CONTRIBUTING.md`. Copy it into `skills/<skill-name>/`, adapt the `SKILL.md` to the repo's conventions (strip project-specific paths; reference any bundled scripts via `${CLAUDE_SKILL_DIR}`), add a row to the README skills table, and test by loading the clone with `claude --plugin-dir ~/code/alin-skills`. Commit on a branch but don't push yet.

Claude Code will do the work, show you a summary, and stop before pushing. To finish:

> Push the branch and open a pull request against main.

Alternatively, push manually with `git push -u origin <branch>` and open the PR in the GitHub webpage.

### A4. Improving an existing skill

> The `<skill-name>` skill in alin-skills needs `<what you want changed>`. Please update it at `~/code/alin-skills`, following the "Update an existing skill" guidance in CONTRIBUTING.md. Show me a merge plan before editing, don't rename the folder or change the `name:` frontmatter, and commit on an `update-<skill-name>` branch without pushing.

Claude Code will show the merge plan, wait for your confirmation, apply the edit, test it (`claude --plugin-dir ~/code/alin-skills`), and commit. Push when you're ready.

---

## Tips and common gotchas

- **Reload after install or update.** Run `/reload-plugins` (or start a fresh session) so Claude Code picks up the newly installed or updated skills.
- **Skills are routed by description.** Claude picks a skill based on the `description:` field in the SKILL.md frontmatter, not the filename. If a skill isn't firing, check whether your request matches what the description says the skill is for. You can also force a skill with its namespaced name, e.g. `/alin:hwpx`.
- **No collisions to worry about.** Plugin skills are always namespaced (`alin:<name>`), so they can't clash with your personal skills in `~/.claude/skills/` or with another plugin's skills. The old "should I overwrite this directory?" hazard is gone.
- **Don't edit the installed copy.** The plugin lives in a managed, versioned cache (`~/.claude/plugins/cache/…`) that gets replaced on update. To change a skill, edit it in a clone and open a PR (see A3/A4); local cache edits are lost on the next update.
- **Korean and English both work.** Skill descriptions are in English (for reliable routing) but the body of a `SKILL.md` can be in whatever language matches the task.

---

## Getting help

- **Access or permission issues**: message Woomin directly.
- **A skill is broken or behaving unexpectedly**: open an issue on GitHub, or ping the lab channel.
- **Not sure how to write a good skill**: read `CONTRIBUTING.md` and look at the existing skills in `skills/` for examples.
- **Propose a change to this guide or to the contribution process**: open a PR against `GUIDE.md` or `CONTRIBUTING.md`.

The one philosophy to remember: **if a workflow saves you time, it will probably save someone else time too**. Ship the skill, iterate on feedback, and keep the lab's collective intelligence growing.
