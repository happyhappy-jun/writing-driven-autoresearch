# ralphthon-icml

Claude Code plugin and skill repository for `Ralphthon @ICML "Auto Research" supported by Codex`.

The plugin exposes five core event workflows and three W&B companion workflows as Agent Skills.

## Included

| Skill | Purpose |
| --- | --- |
| `hello-ralphthon-icml` | Welcome attendees and prepare QR/POP orientation copy. |
| `auto-research` | Build general Track 1 research, run the pinned official VESSL autoresearch recipe on A100 with local-first W&B tracking, or package a no-compute Track 2 Review Agent and result. |
| `wandb-onboarding` | Guide W&B Cloud signup, private API-key login, and an offline-first synthetic run. |
| `vessl-cloud-onboarding` | Verify current VESSL Cloud and `vesslctl` setup before optional billable compute. |
| `world-model-ideation` | Convert a world-model concept into a falsifiable experiment and Track path. |
| `wandb-track-experiment` | Add one-run-per-candidate experiment tracking, provenance, summaries, and guarded alerts. |
| `weave-add-tracing` | Add compact, useful Weave traces to an existing LLM or agent application. |
| `wandb-project-analyst` | Analyze live Models and Weave project data with the W&B MCP server. |

Every skill lives at `skills/<skill-name>/SKILL.md`. A skill may include `references/` for detailed official guidance, `assets/` for templates and notebooks, and `scripts/` for executable helpers.

## Install

Install from GitHub as a Claude Code plugin marketplace:

```text
/plugin marketplace add team-attention/ralphthon-icml
/plugin install ralphthon-icml@ralphthon-icml
```

To work on the plugin locally, add the checkout itself as the marketplace source:

```text
/plugin marketplace add ./ralphthon-icml
/plugin install ralphthon-icml@ralphthon-icml
```

Claude Code reads `.claude-plugin/plugin.json`, discovers every skill under `skills/`, and namespaces them as `/ralphthon-icml:<skill-name>`. Workflow behavior, verification, and output contracts live in each `SKILL.md`.

## Usage

Ask naturally, or invoke a skill by name:

```text
Create a Ralphthon @ICML attendee welcome pack.
Use auto-research to freeze a research spec for Track 1 and Track 2.
Use wandb-onboarding to verify a synthetic W&B run offline before upload.
Use vessl-cloud-onboarding to check VESSL Cloud pricing without creating compute.
Use world-model-ideation to compare three falsifiable world-model questions.
Use wandb-track-experiment to add W&B tracking and alerts to my experiment loop.
Use weave-add-tracing to add Weave tracing to my agent.
Use wandb-project-analyst to compare the best runs in my W&B project.
Walk me through the W&B Models hands-on notebook.
Walk me through the W&B Weave hands-on notebook.
```

A skill also invokes explicitly as `/ralphthon-icml:auto-research`.

W&B and VESSL Cloud use a hybrid browser-and-terminal workflow. Claude Code can open official pages, inspect visible state, and run safe diagnostics. The user handles credentials, OAuth, MFA, CAPTCHA, email verification, legal acceptance, API keys, payment details, and final signup submission.

## Auto Research Paths

`auto-research` starts by choosing exactly one mutually exclusive path:

- **Training path:** use [`vessl-ai/vessl-cloud-cookbook/autoresearch`](https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/autoresearch) pinned at [`97a0af14b0acae042162b1f70f17fbe2d570afa2`](https://github.com/vessl-ai/vessl-cloud-cookbook/tree/97a0af14b0acae042162b1f70f17fbe2d570afa2/autoresearch) as the execution source of truth, run it on an explicitly approved live single-A100 spec, then use verified evidence for a Track 1 paper. At that pin, its baseline `prepare.py` and `train.py` match [`karpathy/autoresearch@228791f`](https://github.com/karpathy/autoresearch/commit/228791fb499afffb54b46200aca536f79142f117). This path requires W&B and VESSL Cloud onboarding.
- **General Track 1 path:** use a non-Karpathy workflow or credible existing evidence to produce the research agent workflow, paper, and self-review. It **does not automatically require W&B, VESSL, or A100**.
- **Track 2-only:** freeze a reusable **Track 2 Review Agent** as `review-agent.md`, then use it to review an existing Track 1 paper without provisioning compute, cloning the training repository, or claiming a new experiment. Submit both the agent artifact and review result.

The Training path does not define a custom model or benchmark preset. Its **unchanged benchmark** keeps the official recipe's preparation, dependencies, and baseline intact. After the baseline, each candidate may modify only `train.py`, with one hypothesis and one change. The safety overlay permits one baseline, at most three **sequential** candidates, and one unchanged confirmation rerun. It does not import the cookbook's parallel fan-out, unbounded loop, H100 default, or destructive reset guidance. Only a lower `val_bpb` that repeats in the same A100/cache/evaluation environment may support a Track 1 claim; A100 and published H100 measurements are not directly comparable.

The official cookbook remains the only remote compute plane: a participant-owned fork/branch is pushed, `vesslctl job create` clones it, an object volume supplies the benchmark cache, and `vesslctl job show`/`job logs` return state and results. The branch, volume, Job, and polling-timeout behavior are reviewed before spend. A polling timeout does not stop remote billing, so the approved cleanup flow must inspect and, when authorized, terminate the Job.

Experiment metadata is written after each fetched VESSL log to the local append-only recorder `skills/auto-research/scripts/record_experiment.py`; W&B offline is mandatory. W&B receives only approved run/trial, Git/cookbook, VESSL Job/A100/cache correlation, metric, resource, time, and status fields, grouped by campaign with `job_type=autoresearch-trial`. Console output, code, Git patches, requirements, machine metrics/info, datasets, checkpoints, artifacts, credentials, and API keys are disabled or excluded. W&B's offline format still contains internal SDK metadata such as a sanitized host label, SDK/Python/platform versions, timestamps/runtime, and SDK telemetry records. Before any `wandb sync`, disclose those fields and show the entity, project, visibility, allowlist, and exact offline run directories, then obtain explicit confirmation.

Before VESSL creates anything billable, query `vesslctl resource-spec list --usable-only` and show a live cost card with the exact resource spec, hourly price, credits, image, expected wall time, storage exposure, and cleanup choice. The created Job configuration must retain that confirmed **single A100** spec; stop rather than silently falling back to another GPU or enlarging the model. If VESSL exposes runtime GPU identity independently, cross-check it without changing the benchmark.

Manual live-account boundary: repository tests do not create accounts, submit OAuth/MFA/CAPTCHA, enter an API key, sync a W&B run, authenticate VESSL, or create/stop paid compute. Those steps remain user-controlled and require their documented action-time confirmations.

Test the full safety gate with this prompt:

```text
Use auto-research in Training path with the pinned official VESSL cookbook. Verify W&B offline first, show the approved sync fields, inspect the current VESSL single-A100 live cost and object-volume exposure, and stop for confirmation before creating compute.
```

## W&B Workflows

- [`skills/wandb-track-experiment`](skills/wandb-track-experiment/SKILL.md) instruments Claude Code, Ralph loop, and other iterative research workflows with one W&B run per candidate and opt-in alerts.
- [`skills/weave-add-tracing`](skills/weave-add-tracing/SKILL.md) adds and verifies focused Weave trace trees without changing application behavior.
- [`skills/wandb-project-analyst`](skills/wandb-project-analyst/SKILL.md) uses the W&B MCP server to inspect existing runs, traces, evaluations, and artifacts.

The skills are organized by W&B product workflow rather than competition track. Track 1 commonly uses experiment tracking; Track 2 commonly uses Weave tracing, while both can use project analysis.

## W&B Hands-on

Models, based on the official [W&B Intro notebook](https://github.com/wandb/examples/blob/master/colabs/intro/Intro_to_Weights_%26_Biases.ipynb):

- [`handson_models.ipynb`](skills/wandb-track-experiment/assets/handson_models.ipynb): one run with config, metrics, summary, and a guarded scriptable alert.

Weave, based on [hw-oh/weave-initial-course](https://github.com/hw-oh/weave-initial-course/tree/main/notebooks):

- [`handson_weave.ipynb`](skills/weave-add-tracing/assets/handson_weave.ipynb): a short `@weave.op` tracing walkthrough, Trace UI inspection, one simple tool-calling agent, and optional Claude Code integration.

Each notebook ships inside the skill that teaches it, so an installed plugin can always resolve it.

## Official Platform Material

VESSL's current repository collection includes the main [VESSL Cloud cookbook](https://github.com/vessl-ai/vessl-cloud-cookbook), [Gemma 4 fine-tuning](https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/gemma4-finetuning), [GPU cost benchmark](https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/gpu-cost-benchmark), [AQR finance](https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/aqr-finance), and the [recipe template](https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/_template). See the skill's [curated current/legacy map](skills/vessl-cloud-onboarding/references/official-repositories.md). Older `vessl-ai/examples` and `vessl-training-recipes` repositories are reference-only, not the current Cloud execution source.

W&B does not maintain one repository literally named "cookbook." Its official equivalents are the [documentation source](https://github.com/wandb/docs), [agent skills](https://github.com/wandb/skills), [examples](https://github.com/wandb/examples), [education](https://github.com/wandb/edu), [Artifacts examples](https://github.com/wandb/artifacts-examples), [Launch Jobs](https://github.com/wandb/launch-jobs), and [Sweeps](https://github.com/wandb/sweeps). The optional [ARIA autoresearch](https://docs.wandb.ai/aria/autoresearch) surface may analyze an approved synced run, but VESSL remains the scheduler. See the [W&B ecosystem map](skills/wandb-onboarding/references/official-ecosystem.md) for what this plugin uses and deliberately excludes.

## Public Event Facts

- Luma: <https://luma.com/hjuo7auc>
- Title: `Ralphthon @ICML "Auto Research" supported by Codex`
- Venue: `NAVER D2SF 강남`, 서울 서초구 서초대로74길 14 삼성화재 서초타워 18층
- Track 1: AI Scientist agent plus a 2-4 page workshop-style short paper and self-review.
- Track 2: Review Agent plus an ICML-style structured review of a Track 1 paper.
- Ralph Loop: 12:30-15:30.
- Human editing and final paper/agent submission: 15:30-16:30.
- The final paper/agent hard cut is 16:30; peer and self-review follow.

Verify live attendee-visible facts before publishing event copy.

## Safety Boundaries

- Never commit passwords, API keys, access tokens, payment information, credentials, or account-specific configuration.
- Never publish private participant or reviewer data, guest exports, outreach status, private messaging links, raw Slack/Telegram/Gmail/Fireflies content, or internal operations ledgers.
- Do not fabricate research results, citations, runs, reviews, metrics, or evidence.
- Treat Dalpha award wording, criteria, prizes, product relationships, and world-model endorsement as unconfirmed until approved public copy exists.
- W&B online runs require a review of entity, project, visibility, and uploaded data.
- VESSL Cloud Workspace/Job creation requires live price, credit, resource, duration, and cleanup confirmation.

## Validation

Run:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_plugin.py
claude plugin validate . --strict
```

`scripts/validate_plugin.py` enforces this repository's contract: the manifests, the `skills/<name>/SKILL.md` layout, frontmatter, resolvable links, and the absence of Codex-era artifacts. `claude plugin validate` is Claude Code's own manifest check and is the authority on manifest schema.

Expected catalog output:

```text
Validation passed
- plugin: ralphthon-icml
- skills (8): auto-research, hello-ralphthon-icml, vessl-cloud-onboarding, wandb-onboarding, wandb-project-analyst, wandb-track-experiment, weave-add-tracing, world-model-ideation
```

## Continue on Another Mac

```bash
git clone https://github.com/team-attention/ralphthon-icml.git
cd ralphthon-icml
python3 -m unittest discover -s tests -v
python3 scripts/validate_plugin.py
claude plugin validate . --strict
```
