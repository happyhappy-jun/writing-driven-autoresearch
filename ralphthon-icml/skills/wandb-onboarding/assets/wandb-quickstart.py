"""A synthetic W&B run that is offline by default."""

from __future__ import annotations

import os

import wandb


os.environ.setdefault("WANDB_MODE", "offline")

with wandb.init(
    entity=os.environ.get("WANDB_ENTITY") or None,
    project=os.environ.get("WANDB_PROJECT", "wandb-quickstart"),
    config={"epochs": 1, "learning_rate": 0.01, "data": "synthetic"},
    settings=wandb.Settings(save_code=False, disable_git=True),
) as run:
    run.log({"accuracy": 0.90, "loss": 0.10})
