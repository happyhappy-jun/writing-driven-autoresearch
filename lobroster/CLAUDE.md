# lobroster

Research codebase for **Depth-AR** — training-free Transformer layer skipping by
predicting the skipped layer's residual update instead of dropping it.

The full research spec lives in **`GOAL.md`** (authored separately). Read it
before designing or interpreting any experiment. The summary below exists only
so you know what the code is *for*; it is not the spec.

## The idea in one paragraph

Treat depth like an optimization trajectory. Define the per-layer residual
update `Δ_l = h_l − h_{l−1}`. On a small calibration set, fit `Δ_{l+1} ≈ a_l·Δ_l`
(AR(1)) or `Δ_{l+1} ≈ a_l·Δ_l + b_l·Δ_{l−1}` (AR(2)). Then, instead of executing
layer `l+1`, reconstruct it as `ĥ_{l+1} = h_l + a_l·Δ_l`. The AR(1) coefficient
is **closed-form** — `a_l = Σ⟨Δ_l, Δ_{l+1}⟩ / Σ‖Δ_l‖²` — so calibration is a
few minutes on ~32 prompts with no gradient descent.

Baselines to beat: **Full model** and **Plain skip** (`h_{l+1} = h_l`, i.e.
identity). The claim is only interesting if Depth-AR beats *plain skip*.

**A negative result is still a paper.** If extrapolation fails, the question
becomes "does residual predictability imply layer redundancy?" — comparing R²,
cosine similarity, and update norm as predictors of true skip damage. Do not
bury or massage a negative result; it is a valid outcome by design.

## Hardware and how work actually runs

The master node (this box, `/home/lobster`) has **no GPUs**. All compute runs on
four shared lab servers over SSH: **alin10, alin11, alin12** (8× 11 GB 2080 Ti
each) and **alin14** (8× 24 GB 3090). There is **no SLURM** — the `lobroster`
plugin's `gpufleet` tool is the scheduler.

**Use alin14 for anything touching Qwen3-4B.** The 11 GB 2080 Tis cannot hold a
4B model plus the per-layer hidden states that calibration requires, and they
are `sm_75` (no bf16). alin14 GPU0 has ~11.7 GB of orphaned VRAM and is
excluded from scheduling, so treat alin14 as **7 usable GPUs**.

### The loop, every time

1. **Edit here.** `/home/lobster/lobroster` is the single source of truth.
2. **Sync** — `/lobroster:code-sync`. `$HOME` is not shared; a worker runs its
   own copy. **An unsynced worker silently runs old code and produces
   plausible-looking wrong numbers.** This is the top failure mode of this setup.
3. **Check GPUs** — `/lobroster:gpu-status`.
4. **Submit** — `/lobroster:gpu-submit` with `--min-vram 20` so it lands on a
   3090. Queue sweeps with `/lobroster:gpu-queue`.
5. **Read the log before believing the result** — `gpufleet.py logs <id>`.

Never edit code directly on a worker: `code-sync` uses `--delete` and will
destroy it. Never kill or evict a process the fleet did not launch — other
people share these machines.

Environment is defined **here** in `requirements.txt` and propagated by
`/lobroster:env-setup`. To change it, edit that file and re-run env-setup on
every host. Do not hand-install a package on one worker — silent drift across
hosts means results that don't reproduce, and you won't notice until the
numbers disagree.

## Layout

```
src/        library code: model hooks, calibration, skip/AR execution, eval
scripts/    entry points submitted to GPUs (one experiment = one script)
configs/    experiment configs
outputs/    results, figures, tables  -- NOT synced, regenerable
data/       datasets                  -- NOT synced, regenerable
logs/       run logs                  -- NOT synced
```

`data/`, `outputs/`, and `logs/` are excluded from sync by `.syncignore` and
capped at 100 MB/file. Workers should **download or regenerate** datasets and
weights locally (HF cache) rather than having them pushed from here.

Results land in the worker's `outputs/` and are **not** synced back. Pull them
explicitly when an experiment finishes.

## How to work on this

- **Evidence over claims.** Report what the run produced, including when it
  contradicts the hypothesis. Never present a planned or expected number as an
  observed one. If a job failed, say so and show the log.
- **The comparison that matters is Depth-AR vs. plain skip**, not Depth-AR vs.
  the full model. Beating the full model is not the claim; losing less than
  identity-skipping is.
- **Efficiency metric is removed blocks / theoretical FLOPs**, not wall-clock.
  Python forward hooks make latency measurements unreliable — report latency
  only as a secondary, caveated number.
- **Keep the eval harness fixed.** Changing the metric or the eval set between
  conditions invalidates the comparison. Qwen3-4B-Instruct + SQuAD 2.0
  answerable, EM/F1, no-thinking — held constant across Full / Plain skip /
  AR(1) / AR(2).
- Prefer small, cheap checks (200 examples) before committing to a full 500-example
  run. Calibrate on ~32 prompts; that is enough for a closed-form scalar.
- One change at a time. This is a layer-ablation study — confounds are fatal.
