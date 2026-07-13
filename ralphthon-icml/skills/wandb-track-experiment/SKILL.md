---
name: wandb-track-experiment
description: Add W&B Models experiment tracking and guarded alerts to iterative experiment workflows, including Claude Code or Ralph-loop autoresearch. Use when the user asks to instrument experiments, create one W&B run per candidate, group related runs, record hypotheses and code provenance, log metrics and summaries, detect failed or stalled experiments, or validate that runs are comparable and reproducible. Use wandb-project-analyst for analysis of data already stored in W&B.
---

# Track Experiments with W&B

Instrument an experiment loop so every candidate becomes a comparable W&B run with enough context to understand what changed, what happened, and whether the objective improved.

## Operating Rules

- Treat W&B as an observation layer. The experiment loop, including a Ralph loop, must continue making decisions from local results rather than a required round trip to W&B.
- Use one W&B run per candidate experiment, not one long run for the entire research session.
- Use a shared run `group` to connect iterations from the same experiment session.
- Keep `config` for independent variables and provenance, `run.log()` for changing measurements, and `run.summary` for final comparison values.
- Preserve the existing experiment command, objective calculation, retry behavior, and stopping logic.
- Prefer structured IDs and short summaries over full prompts, source files, or large generated outputs.
- Keep live alerts disabled until Scriptable run alerts and a destination are configured.
- Verify exact SDK and alert behavior against current official W&B documentation before implementing brittle details.
- Use W&B Models for experiments and system metrics; use `weave-add-tracing` for model, agent, and tool traces.

## Workflow

### 1. Find the Research Loop Contract

Identify:

1. The experiment loop controller and candidate entrypoint.
2. The unit that represents one iteration or candidate.
3. The primary objective name, value, and `maximize` or `minimize` direction.
4. Baseline value or baseline run, if one exists.
5. Iteration, time, cost, and retry budgets.
6. Where hypothesis, code change, seed, dataset, command, and result are already represented.

Read `references/experiment-tracking-patterns.md` before changing code.

### 2. Define the Run Contract

Default lifecycle:

```text
Experiment session
|- candidate iteration 0 -> W&B run
|- candidate iteration 1 -> W&B run
`- candidate iteration 2 -> W&B run
```

Use these W&B fields consistently:

- `project`: the research problem or comparison boundary.
- `group`: stable experiment session ID.
- `job_type`: `research-iteration` unless the repository already uses a taxonomy.
- `name`: iteration plus a short hypothesis or candidate ID.
- `tags`: optional `baseline`, `candidate`, `ablation`, or failure category.
- `notes`: a concise human-readable hypothesis or change summary.

Recommended config keys:

- `session_id`, `iteration`, `candidate_id`, `parent_run_id`
- `hypothesis_id`, `change_id`, `code_revision`
- `objective_name`, `objective_direction`, `baseline_run_id`
- `dataset_id`, `seed`, `experiment_command`
- `iteration_budget`, `time_budget_sec`, `cost_budget_usd`

### 3. Add Minimal Logging

1. Wrap each candidate lifecycle in one `wandb.init()` context.
2. Pass immutable experiment inputs and provenance in `config`.
3. Log step or epoch metrics next to the code that produces them.
4. Finalize comparison fields once in `run.summary`.
5. Allow exceptions to propagate through the run context so failed experiments remain failed locally and in W&B.
6. Enable W&B code saving when permitted so git state and a working-tree diff can support reproduction.

Recommended metric shape:

- `objective/value`
- `train/loss`, `eval/loss`, or domain metrics already produced by the experiment
- `ops/duration_sec`, `ops/cost_usd`, `ops/exit_code`
- `loop/iteration`, `loop/stagnation_count`

Recommended summary shape:

- `objective/final`, `objective/best`
- `objective/delta_from_baseline`, `objective/improved`
- `ops/duration_sec`, `ops/cost_usd`, `ops/exit_code`, `ops/status`

Do not invent metrics the experiment cannot compute reliably.

### 4. Add Guarded Alerts

Make alert enablement explicit, such as `WANDB_ENABLE_ALERTS=1`. Keep it off by default.

Start with a few actionable conditions:

- experiment process exits unsuccessfully;
- objective is missing or non-finite;
- time or cost budget is exceeded;
- the loop reaches its configured stagnation limit;
- optional final notification when the research session completes.

Use a cooldown for repeated conditions. Do not alert on every ordinary metric fluctuation or every successful iteration.

### 5. Validate One Iteration

1. Run formatting, static checks, and focused tests.
2. Execute one baseline or cheap smoke candidate when credentials and resources permit.
3. Confirm exactly one new W&B run appears for that candidate.
4. Check group, config, metric history, summary, status, logs, and code provenance.
5. Confirm alerts remain dry unless explicitly enabled.
6. Report the run URL and the exact expected schema when a live run is not possible.
7. Hand analysis of recorded runs to `wandb-project-analyst` and W&B MCP.

## Hands-on

Use [`assets/handson_models.ipynb`](assets/handson_models.ipynb) for a short introduction to one run, config, metric logging, summary, and a guarded scriptable alert.

Run its single code cell once. Keep `SEND_ALERT=False` until the user confirms that alert delivery is configured.

## References

- Read `references/experiment-tracking-patterns.md` for the run lifecycle, code shape, alert guards, and validation checklist.
- Use the official [wandb/skills](https://github.com/wandb/skills) repository for broad W&B SDK and project-analysis patterns; keep this skill focused on experiment instrumentation.

## Response Shape

Return:

1. The experiment session and candidate run contract.
2. Config, metric, and summary schema.
3. Changed files and lifecycle insertion points.
4. Guarded alert conditions.
5. Validation performed and expected W&B behavior.
