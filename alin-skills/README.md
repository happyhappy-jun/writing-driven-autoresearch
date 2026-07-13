# alin-skills

A shared collection of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills for the ALIN lab. Skills are reusable, self-contained instructions that teach Claude Code how to do a specific task — document conversion, text processing, tool wrappers, and so on.

The goal of this repo is to make it trivial for lab members to **use**, **share**, and **adapt** skills without learning any new tooling beyond `git` and Claude Code itself.

## Documentation for lab members

- **[QUICKSTART.md](QUICKSTART.md)** / **[QUICKSTART.ko.md](QUICKSTART.ko.md)** — the fastest path: four copy-pasteable Claude Code prompts for install, update, and contribution. Start here.
- **[GUIDE.md](GUIDE.md)** / **[GUIDE.ko.md](GUIDE.ko.md)** — the full walkthrough: why this repo exists, detailed agentic scenarios, gotchas, and tips.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — skill authoring templates, style rules, and the short agent guidance Claude Code follows when installing, adding, or updating skills.

## Install

alin-skills ships as a **Claude Code plugin** named `alin`, distributed through its own marketplace (this repo). Install it from inside a Claude Code session:

```text
/plugin marketplace add alinlab/alin-skills
/plugin install alin@alin-skills
```

The repo is **private**, so both commands require that your GitHub account already has access — ask Woomin for a collaborator invite first (see [QUICKSTART.md](QUICKSTART.md)). Claude Code clones the marketplace using your existing git credentials, exactly like `git clone`; nothing is exposed publicly.

Once installed, run `/reload-plugins` (or start a fresh session) and every skill is available, namespaced as `/alin:<skill-name>` (e.g. `/alin:hwpx`). Claude also auto-routes to them based on each skill's `description`.

To update later: `/plugin marketplace update alin-skills`. See [QUICKSTART.md](QUICKSTART.md) for the full flow, including optional silent auto-updates via `GITHUB_TOKEN`.

## Skills

<!-- skills-table:start -->

### Document & Writing
| Skill | What it does |
| --- | --- |
| [`adversarial-plan`](skills/adversarial-plan/SKILL.md) | Plan in Plan mode, then iterate Codex review ↔ Claude validate-and-revise ping-pong until convergence or a user-configured `max_iter` (default 5, hard cap 10). Falls back to dual-persona self-review when Codex is absent. Saves every iteration's review/revision to `~/.claude/plans/`. |
| [`codex-migration`](skills/codex-migration/SKILL.md) | Migrate installed Claude Code skills to OpenAI Codex CLI (`~/.claude/skills/` to `~/.codex/skills/`), with compatibility auditing and path adaptation. |
| [`commit-feat`](skills/commit-feat/SKILL.md) | Split the current git diff into logical single-feature commits using conventional commit style. |
| [`discussion-and-log`](skills/discussion-and-log/SKILL.md) | Research discussion journal — analyze result files or WandB links, search relevant literature, discuss next directions, and save a dated markdown summary. |
| [`gpu-idle-watch`](skills/gpu-idle-watch/SKILL.md) | Detect idle GPUs in the user's RUNNING Slurm jobs by sampling `nvidia-smi` inside each allocation; only flags GPUs that stay at 0% util across consecutive samples. Optional Slack alert. |
| [`hwpx`](skills/hwpx/SKILL.md) | Read and edit Hangul Word Processor files — full `.hwpx` round-trip editing (inspect, replace, unpack/pack, programmatic helpers) plus `.hwp` read-only extraction to JSON/Markdown/HTML. |
| [`interview-plan`](skills/interview-plan/SKILL.md) | Read the current plan file, surface ambiguities and open decisions, and resolve them through a structured interview before implementation begins. |
| [`job-tracker`](skills/job-tracker/SKILL.md) | Cross-session Slurm job tracker + supervisor. Each session logs the jobs it submits (id + one-line intent + expected output files) to a shared machine-local ledger; any session runs `status` to reconcile it against live `squeue`/`scontrol`/logs/expected outputs and see what's RUNNING/PENDING, FAILED/TIMEOUT, DONE, or trained-but-eval-missing. Useful when you run many jobs across many sessions and `sacct` is disabled. |
| [`read-pptx`](skills/read-pptx/SKILL.md) | Read, view, and analyze `.pptx` (PowerPoint) files on macOS — text extraction + rasterized slide images. |
| [`talk-slide-draft`](skills/talk-slide-draft/SKILL.md) | Generate a `.pptx` talk-slide draft from outline content using a user-provided template. |
| [`figure-to-pptx`](skills/figure-to-pptx/SKILL.md) | Convert a figure PNG/JPG into an editable `.pptx` — image as background, every text label re-created as a native, movable text box with the baked-in text masked. |
| [`korean-spell-check`](skills/korean-spell-check/SKILL.md) | Korean proofreading (맞춤법/문법) via the Nara/PNU public spell-checker surface. |
| [`overleaf-sync`](skills/overleaf-sync/SKILL.md) | Sync an Overleaf project via git — pull, apply generated tables/figures/prose into `.tex` sources, commit, and push; new prose is tone-matched to the manuscript and a personal voice profile learned from past Overleaf projects. |
| [`latex-layout-doctor`](skills/latex-layout-doctor/SKILL.md) | Diagnose and fix LaTeX layout issues — overfull boxes, margin bleeds, float drift, awkward whitespace. |
| [`notation-doctor`](skills/notation-doctor/SKILL.md) | Audit ML paper math notation for consistency — symbol collisions, concept drift, scalar/vector/matrix typography, definition hygiene — plus a symbol glossary and standard-notation suggestions. |
| [`research-site`](skills/research-site/SKILL.md) | Build and maintain a deployable static HTML site (Quarto + Cloudflare Pages) for an ongoing research project. |
| [`progress-report`](skills/progress-report/SKILL.md) | Draft a Korean R&D project (기업/국책 과제) progress/achievement report — extract KPIs from the 계획서, gather the period's evidence (papers, patents, commits, results), build the 목표 대비 달성도 table with cited sources, and fill the `.hwpx` 양식 layout-preserving. Never fabricates achievements. |

### Literature & Related Work
| Skill | What it does |
| --- | --- |
| [`setup-paper-repo`](skills/setup-paper-repo/SKILL.md) | Bootstrap a personal "Papers" Notion database (via Notion MCP) and generate a personalized `addpaper` skill bound to it. |
| [`related-work-search`](skills/related-work-search/SKILL.md) | Systematically search for related work around a research idea — comparative analysis of what's solved and what remains open. |
| [`related-work-verify`](skills/related-work-verify/SKILL.md) | Verify factual accuracy of Related Work entries by reading the arxiv body end-to-end with a 4-pass hallucination check. |
| [`bibtex-verify`](skills/bibtex-verify/SKILL.md) | Verify BibTeX entries against DBLP, Semantic Scholar, and arXiv — catches hallucinated citations, wrong venues/years/authors. |
| [`daily-news`](skills/daily-news/SKILL.md) | Surface the last 7 days of news, papers, and products from X Lists, lab sites, and paper sources (arXiv, alphaXiv, HF). |
| [`meeting-direction`](skills/meeting-direction/SKILL.md) | Read a research progress slide PDF and recommend, at a big-picture level, which recent papers/techniques to build on next — multi-source search (Semantic Scholar + arXiv + web) prioritizing top labs and venues. |
| [`icml-page`](skills/icml-page/SKILL.md) | Build a personalized, filterable ICML 2026 poster & oral plan as a web-page artifact — bundled agenda, keyword-prefilter + parallel subagent curation, day tabs, collapsible sessions, and "why included" tags. |

### Peer Review
| Skill | What it does |
| --- | --- |
| [`paper-reviewer`](skills/paper-reviewer/SKILL.md) | Critically review an AI/ML paper PDF in the style of NeurIPS/ICML/ICLR/ACL/CVPR reviewers. |
| [`rebuttal-helper`](skills/rebuttal-helper/SKILL.md) | Plan-then-draft a paper-grounded rebuttal — classify reviewer points, write a plan, then draft per-reviewer responses. |

### Experiment & HPC
| Skill | What it does |
| --- | --- |
| [`discussion-and-log`](skills/discussion-and-log/SKILL.md) | Analyze result files or WandB links, search relevant literature, discuss next directions, and save a dated summary. |
| [`exp-summary`](skills/exp-summary/SKILL.md) | Summarize experiment results from a folder into a terminal table and a LaTeX-formatted table. |
| [`exp-audit`](skills/exp-audit/SKILL.md) | Audit experiment directories — classify runs as finished/terminated/stale/failed, surface W&B run ids, propose cleanup. |
| [`slurm-eta`](skills/slurm-eta/SKILL.md) | Show current SLURM partition GPU occupancy, running and pending jobs, with remaining/wait time estimates. |
| [`eta`](skills/eta/SKILL.md) | Estimate a RUNNING SLURM job's completion ETA from its StdErr log — parse the latest tqdm/progress bar and project remaining time from average (not instantaneous) speed; prints steps-done/total. |
| [`gpu-idle-watch`](skills/gpu-idle-watch/SKILL.md) | Detect idle GPUs in RUNNING Slurm jobs by sampling `nvidia-smi`; only flags GPUs at 0% util across consecutive samples. |
| [`experiment-planner`](skills/experiment-planner/SKILL.md) | Turn a vague research idea/hypothesis into a falsifiable experiment plan *before* burning GPU/budget, and red-team the design for confounders, weak baselines, data leakage, statistical weakness, and metric gaming. |
| [`preflight`](skills/preflight/SKILL.md) | Smoke-train a HuggingFace Trainer script with synthetic data, measure VRAM/step-time, generate a matching SLURM `.sbatch`. |
| [`sbatch-port`](skills/sbatch-port/SKILL.md) | Port a `.sbatch` between clusters — rewrite account, partition, every absolute path, and the env block for a target server from a per-user registry, then validate and report. Register new servers by pasting a 공지/Slack server-usage message. |
| [`run-and-watch`](skills/run-and-watch/SKILL.md) | Run a long-running command in background and monitor its progress at regular intervals, with optional auto-fix. |
| [`wandb-pull`](skills/wandb-pull/SKILL.md) | Pull a W&B run's config, summary, and key metric history via the API into a compact offline markdown report — no dashboard needed. |
| [`wandb-compare`](skills/wandb-compare/SKILL.md) | Compare 2+ W&B runs — surface config diffs and a metric comparison table, with optional LaTeX export. |
| [`herdr`](skills/herdr/SKILL.md) | Orchestrate a [herdr](https://herdr.dev) multi-agent terminal topology — bridge persistent remote (ssh) agents into the local agents tab, revive layouts, relay messages, and watch + auto-judge agents' permission prompts by policy. |
| [`disk-reclaim`](skills/disk-reclaim/SKILL.md) | Scan a user's account directory, detect quota/free space, categorize deletable artifacts (caches, redundant/final checkpoints, optimizer state, datasets) by reclaimable size, and gate deletion or HuggingFace-Hub upload behind explicit confirmation. |

### Developer Tooling
| Skill | What it does |
| --- | --- |
| [`commit-feat`](skills/commit-feat/SKILL.md) | Split the current git diff into logical single-feature commits using conventional commit style. |
| [`interview-plan`](skills/interview-plan/SKILL.md) | Surface ambiguities and open decisions in a plan, resolve them through a structured interview before implementation. |
| [`adversarial-plan`](skills/adversarial-plan/SKILL.md) | Create a structured plan, adversarially review it for hidden risks and missing assumptions, return a revised plan. |
| [`claude-codex`](skills/claude-codex/SKILL.md) | Run a task against both Claude and Codex side-by-side (compare mode) or as a multi-round debate. |
| [`ml-code-review`](skills/ml-code-review/SKILL.md) | Review ML code for tensor shape/dtype bugs, device errors, gradient flow issues, and numerical stability. |
| [`vulnerability-scanner`](skills/vulnerability-scanner/SKILL.md) | Audit a project for security vulnerabilities, vulnerable dependencies, and best-practice violations. |
| [`model-arch-html`](skills/model-arch-html/SKILL.md) | Generate a single-file `ARCHITECTURE.html` for a deep-learning model repo with inline SVG diagrams and dimension flow. |

### Misc
| Skill | What it does |
| --- | --- |
| [`kakaotalk-mac`](skills/kakaotalk-mac/SKILL.md) | Read KakaoTalk chats, search messages, and send replies from macOS via `kakaocli`. |
| [`skill-discovery`](skills/skill-discovery/SKILL.md) | Scan conversation history for reusable workflows, match against installed skills, draft new SKILL.md files. |
| [`codex-migration`](skills/codex-migration/SKILL.md) | Migrate installed Claude Code skills to OpenAI Codex CLI with compatibility auditing and path adaptation. |
| [`fix-printer`](skills/fix-printer/SKILL.md) | Diagnose a macOS network printer that's no longer recognized and re-register it with a fixed IP via IPP Everywhere (works around broken Bonjour/mDNS and full-tunnel VPN). |

<!-- skills-table:end -->

Skills are grouped by category. Within each group, order is not significant. The `<!-- skills-table:start -->` / `<!-- skills-table:end -->` markers exist so contributors (and Claude Code) can locate the table deterministically — see [CONTRIBUTING.md](CONTRIBUTING.md).

## How to use a skill

Once installed, just ask Claude Code to do the thing — it will pick up the right skill from its `description` frontmatter. Examples:

- "이 HWP 파일을 마크다운으로 바꿔줘"
- "카톡에서 OO님과의 최근 대화 요약해줘"
- "이 README 한국어 맞춤법 검사해줘"

You can also invoke a skill explicitly by its namespaced name — e.g. `/alin:hwpx` — if auto-matching isn't picking it up. (Plugin skills are always prefixed with `alin:`; type `/alin:` and let autocomplete list them.)

## Usage telemetry (skill-usage logging)

The plugin records **which `alin:` skills get used**, so maintainers can see what's
popular and where to focus. This is deliberately lightweight and privacy-conscious:

- **What's logged:** one line per skill invocation — the skill name (e.g. `alin:hwpx`),
  a UTC timestamp, whether you typed it (`slash`) or the model auto-picked it (`tool`),
  your git email (`git config user.email`) as an identifier, hostname, session id, and cwd.
  **No prompt text, no arguments, no file contents, no command output** are ever recorded.
- **Where it goes:** appended locally to `~/.claude/alin-skill-usage.jsonl` on your own
  machine. **Nothing is sent anywhere by default** — it stays a local file until you (or a
  maintainer, with your knowledge) choose to share it.
- **It can never break your session:** the hook fails silently and always exits 0.

**Opt out completely** — set this in your shell profile (`~/.zshrc` / `~/.bashrc`):

```bash
export ALIN_SKILL_TELEMETRY=0     # disables all skill-usage logging
```

> 스킬 사용 로그를 남깁니다. **어떤 `alin:` 스킬을 몇 번 썼는지**(스킬 이름·시각·git 이메일)만
> 내 컴퓨터의 `~/.claude/alin-skill-usage.jsonl`에 로컬로 기록하며, 프롬프트 내용·인자·파일·명령
> 결과는 저장하지 않습니다. 기본적으로 외부로 전송되지 않습니다. 끄려면 `export ALIN_SKILL_TELEMETRY=0`.

Implementation lives in [`hooks/`](hooks/); optional aggregation helpers in [`collector/`](collector/).

## Layout

```
alin-skills/
├── .claude-plugin/
│   ├── plugin.json        # plugin manifest (name: alin)
│   └── marketplace.json   # marketplace catalog — this repo IS the alin-skills marketplace
├── README.md              # you are here
├── QUICKSTART.md          # 4-step quickstart (English)
├── QUICKSTART.ko.md       # 4-step quickstart (한국어)
├── GUIDE.md               # full walkthrough (English)
├── GUIDE.ko.md            # full walkthrough (한국어)
├── CONTRIBUTING.md        # authoring guide + agent guidance
├── hooks/                 # skill-usage telemetry (auto-loaded by the plugin)
│   ├── hooks.json         # UserPromptExpansion + PreToolUse:Skill hooks
│   └── log_skill_usage.py # logger → ~/.claude/alin-skill-usage.jsonl
├── collector/             # OPTIONAL, off by default
│   ├── app.py             # central FastAPI+SQLite collector + /stats
│   └── aggregate_local.py # server-less rollup over local JSONL logs
└── skills/                # every skill lives under here
    └── <skill-name>/
        ├── SKILL.md
        └── scripts/       # optional helpers
```

The repo is **both** the marketplace and the single plugin it ships: `marketplace.json` lists one plugin, `alin`, whose source is the repo root, and `plugin.json` defines that plugin. Skills stay flat inside `skills/` — one folder per skill, each with its own `SKILL.md`. Categories exist only in the README table above, not as subdirectories on disk. Bundled helper scripts are referenced from `SKILL.md` via `${CLAUDE_SKILL_DIR}/scripts/…` so they resolve whether the skill runs as a plugin or a standalone install.

## Attribution

The `kakaotalk-mac` and `korean-spell-check` skills were adapted from [NomaDamas/k-skill](https://github.com/NomaDamas/k-skill) (MIT). Upstream is the source of truth for fixes to the original behavior; lab-specific adaptations live here. The `hwpx` skill's `.hwp` read path uses [`@ohah/hwpjs`](https://www.npmjs.com/package/@ohah/hwpjs) (MIT).
