"""Observability layer for the auto-research agent loop.

Two independent layers, both safe to import when W&B is unreachable:

  Weave  -> traces the agent loop's own steps (@weave.op on decision boundaries)
  Models -> one W&B run per experiment candidate, grouped by research session

Offline by default. Nothing uploads until WANDB_MODE is changed and the run
directory is explicitly synced.
"""

from __future__ import annotations

import functools
import os
import time
import uuid
from contextlib import contextmanager

import wandb

# Offline unless the caller opts in. Set before any wandb/weave call.
os.environ.setdefault("WANDB_MODE", "offline")

DEFAULT_PROJECT = os.environ.get("WANDB_PROJECT", "auto-research")
ALERTS_ENABLED = os.environ.get("WANDB_ENABLE_ALERTS") == "1"

# Weave has no offline mode: it needs a live backend. Tracing degrades to a
# no-op rather than taking the agent loop down with it.
_weave_active = False


def _authenticated() -> bool:
    """True only if a key is already on disk or in env. Never prompts."""
    if os.environ.get("WANDB_API_KEY"):
        return True
    try:
        return bool(wandb.api.api_key)
    except Exception:  # noqa: BLE001
        return False


def init_tracing(project: str | None = None) -> bool:
    """Initialize Weave once, at the application boundary. Returns success.

    Requires 'entity/project' and an existing login. Importing weave without a
    key opens an interactive prompt that would hang a headless loop on stdin,
    so authentication is checked before the import, not after.
    """
    global _weave_active
    if _weave_active:
        return True

    target = project or os.environ.get("WEAVE_PROJECT")
    if os.environ.get("WANDB_MODE") == "offline":
        print("[obs] tracing off: WANDB_MODE=offline (Weave has no offline mode)")
        return False
    if not target or "/" not in target:
        print("[obs] tracing off: set WEAVE_PROJECT='entity/project'")
        return False
    if not _authenticated():
        print("[obs] tracing off: not logged in (run `wandb login`)")
        return False

    try:
        import weave

        weave.init(target)
        _weave_active = True
        print(f"[obs] weave tracing live: {target}")
    except Exception as exc:  # noqa: BLE001 - observability must not break the loop
        print(f"[obs] weave tracing disabled: {exc}")
    return _weave_active


def op(fn):
    """Mark a decision boundary. Becomes a Weave Op only once tracing is live.

    Bound lazily at call time: decorators run at import, before init_tracing().
    """
    traced = None

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        nonlocal traced
        if not _weave_active:
            return fn(*args, **kwargs)
        if traced is None:
            import weave

            traced = weave.op()(fn)
        return traced(*args, **kwargs)

    return wrapper


def new_session_id(prefix: str = "session") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@contextmanager
def candidate_run(
    session_id: str,
    iteration: int,
    hypothesis: str,
    objective_name: str,
    objective_direction: str = "minimize",
    project: str = DEFAULT_PROJECT,
    entity: str | None = None,
    config: dict | None = None,
    tags: list[str] | None = None,
    baseline_run_id: str | None = None,
):
    """One W&B run per candidate. Exceptions propagate so failures stay failures.

    Log inside the block with run.log({...}); set run.summary["objective/final"]
    to the value the loop compares against.
    """
    assert objective_direction in ("minimize", "maximize")

    run_config = {
        "session_id": session_id,
        "iteration": iteration,
        "objective_name": objective_name,
        "objective_direction": objective_direction,
        "baseline_run_id": baseline_run_id,
        **(config or {}),
    }

    started = time.monotonic()
    with wandb.init(
        entity=entity,
        project=project,
        group=session_id,
        job_type="research-iteration",
        name=f"iter-{iteration:03d}",
        notes=hypothesis,
        tags=tags or [],
        config=run_config,
        settings=wandb.Settings(save_code=False, disable_git=True),
    ) as run:
        status = "failed"
        try:
            yield run
            status = "succeeded"
        finally:
            duration = time.monotonic() - started
            run.summary["ops/duration_sec"] = duration
            run.summary["ops/status"] = status

            objective = run.summary.get("objective/final")
            if status == "succeeded" and _is_bad_objective(objective):
                status = "invalid-objective"
                run.summary["ops/status"] = status
                alert(
                    f"iteration {iteration}: objective missing or non-finite",
                    f"{objective_name}={objective!r}",
                )
            elif status == "failed":
                alert(f"iteration {iteration} failed", hypothesis)


def _is_bad_objective(value) -> bool:
    if value is None:
        return True
    try:
        f = float(value)
    except (TypeError, ValueError):
        return True
    return f != f or f in (float("inf"), float("-inf"))


def alert(title: str, text: str) -> None:
    """Guarded: silent unless WANDB_ENABLE_ALERTS=1 and a run is live online."""
    if not ALERTS_ENABLED:
        return
    run = wandb.run
    if run is None or os.environ.get("WANDB_MODE") == "offline":
        return
    try:
        run.alert(title=title, text=text)
    except Exception as exc:  # noqa: BLE001
        print(f"[obs] alert not delivered: {exc}")
