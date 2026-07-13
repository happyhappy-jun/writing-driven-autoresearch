# Experiment Loop Tracking Patterns

## Lifecycle Mapping

Map the local research workflow before adding W&B:

| Local concept | W&B representation |
|---|---|
| Experiment comparison boundary | Project |
| One experiment session | Run group |
| One candidate experiment | Run |
| Hypothesis and fixed inputs | Config and notes |
| Epoch, step, or stage measurements | Run history with `run.log()` |
| Final objective and outcome | Run summary |
| Git commit and working-tree change | W&B code provenance |

The loop should use the experiment's local return value for selection and stopping. Log that same value to W&B after it is computed.

## Run Identity

Use stable IDs that remain useful outside the current process:

```text
project: experiments-<problem>
group: <session-id>
job_type: research-iteration
name: iter-003-<candidate-id>
```

Useful relationships:

- `parent_run_id`: candidate that inspired the current change.
- `baseline_run_id`: fixed baseline used for delta calculation.
- `candidate_id`: stable local identifier used in logs and output files.
- `change_id`: commit, patch, or mutation identifier.

Do not use the generated W&B run name as the only identifier the experiment loop understands.

## Instrumentation Shape

Adapt this sketch to the repository rather than introducing a parallel experiment system:

```python
import math
import os
import time

import wandb
from wandb import AlertLevel


def run_candidate(spec, experiment_fn):
    alerts_enabled = os.environ.get("WANDB_ENABLE_ALERTS") == "1"
    started_at = time.monotonic()

    with wandb.init(
        project=spec.project,
        group=spec.session_id,
        job_type="research-iteration",
        name=f"iter-{spec.iteration:03d}-{spec.candidate_id}",
        notes=spec.hypothesis_summary,
        tags=spec.tags,
        config={
            "session_id": spec.session_id,
            "iteration": spec.iteration,
            "candidate_id": spec.candidate_id,
            "parent_run_id": spec.parent_run_id,
            "objective_name": spec.objective_name,
            "objective_direction": spec.objective_direction,
            "seed": spec.seed,
        },
    ) as run:
        try:
            result = experiment_fn(run)
            score = float(result.objective)
            duration_sec = time.monotonic() - started_at

            run.summary["objective/final"] = score
            run.summary["objective/improved"] = result.improved
            run.summary["ops/duration_sec"] = duration_sec
            run.summary["ops/exit_code"] = 0
            run.summary["ops/status"] = "finished"

            if not math.isfinite(score) and alerts_enabled:
                run.alert(
                    title="Experiment objective is non-finite",
                    text=f"candidate={spec.candidate_id} objective={score}",
                    level=AlertLevel.ERROR,
                    wait_duration=300,
                )
            return result
        except Exception as error:
            run.summary["ops/exit_code"] = 1
            run.summary["ops/status"] = "failed"
            run.summary["ops/error_type"] = type(error).__name__
            if alerts_enabled:
                run.alert(
                    title="Experiment candidate failed",
                    text=f"candidate={spec.candidate_id} error={type(error).__name__}",
                    level=AlertLevel.ERROR,
                    wait_duration=300,
                )
            raise
```

The experiment can accept the run object for step logging, or use a narrow callback when passing the SDK object through the code would create unwanted coupling.

## Objective Semantics

Define these before logging:

- Exact objective key and unit.
- `maximize` or `minimize` direction.
- Baseline value and tolerance.
- Whether repeated seeds are aggregated locally or represented as separate runs.
- What qualifies as `improved`.

For a maximizing objective:

```text
delta_from_baseline = final - baseline
improved = delta_from_baseline > tolerance
```

For a minimizing objective, reverse the subtraction. Store the direction in config so downstream analysis does not have to guess.

## Alert Guardrails

Alert only when a person can take a clear action:

| Condition | Suggested action |
|---|---|
| Subprocess failure | Inspect run logs and the candidate patch |
| Missing or non-finite objective | Inspect metric parsing and experiment output |
| Time or cost budget exceeded | Stop or reduce the remaining search budget |
| Stagnation limit reached | Review the hypothesis strategy or terminate the loop |
| Session completed | Review the best candidate and reproduction evidence |

Use environment-controlled enablement and cooldowns. Scriptable alerts require user or team alert delivery configuration.

## Validation Checklist

- One smoke candidate creates exactly one run.
- A second candidate in the same session shares the same group and has a different run ID.
- Config contains iteration, candidate, objective direction, and provenance IDs.
- Step metrics use consistent names and steps.
- Summary contains the final objective, improvement decision, duration, exit code, and status.
- A failed candidate remains failed locally and records failure context in W&B.
- Alerts do not send when enablement is off.
- No API key, secret, private full prompt, or large source file is logged.
- The experiment loop produces the same local decision with W&B disabled.
