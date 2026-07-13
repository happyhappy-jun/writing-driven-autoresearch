# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`/home/lobster` is the **orchestration root** for a 3-hour, fully autonomous
research sprint producing an ICML-workshop paper on **Depth-AR** (training-free
Transformer layer skipping: predict a skipped block's residual update from the
preceding depth trajectory instead of assuming it is zero).

**`~/DEPTH-AR-PLAN.md` is the spec.** Read it before any research decision. It
is 1100 lines and covers the method, the gates, the pre-committed pivots, and a
paper story for every outcome including negative ones. The persona files are the
operating manual; the plan is the source of truth.

This is not a normal repo. It is a **three-agent team** running against a clock.

## The three agents

Each runs as a Claude pane in the herdr tab `ralph`, all with cwd `/home/lobster`.
Read the persona file for whichever role you are before doing anything.

| Agent | Persona | Owns | Never touches |
|---|---|---|---|
| `master` | `~/master.md` | the clock, gates, decisions, shared state | doesn't run experiments or edit LaTeX |
| `experiment` | `~/experiment.md` | `~/auto-research/`, all GPUs, all model loading, fitting, eval, result JSON | `~/writing/` — not one character |
| `writing` | `~/writing.md` | `~/writing/` (Overleaf git bridge, all `.tex`, captions, citations, the build) | never runs a model or touches a GPU |

Also: `~/writing-guidelines.md`, `~/writing-style-guide.md` for prose rules.

**There is no human. Nobody will answer a question, ever.** Never call
`AskUserQuestion`; never end a turn waiting for input. Every decision comes from
the pre-committed defaults in the persona files within the time budget. A wrong
decision made beats a right decision deferred. If genuinely stuck, take the
**reversible** option, log it in `~/ralph/DECISIONS.md`, and move on.

## Shared state — the contract between agents

Everything crossing an agent boundary goes through a **file**, never through chat.

```
~/ralph/STATUS.md      phase, gates, worker state   (master writes)
~/ralph/DECISIONS.md   every decision + why         (master writes)
~/ralph/RESULTS.md     headline numbers
~/ralph/results/*.json experiment output            (experiment writes, writing READS DIRECTLY)
~/ralph/T0             sprint start, epoch seconds
~/ralph/clock.sh       elapsed / remaining / phase
```

**`writing` reads result JSON from disk, never a number relayed through chat.**
Numbers get corrupted every time they are retyped; the file is the truth.
Never invent, round in your favor, or quietly retry a disappointing number — a
measured negative result is a **success** here (the plan has pivots A–F for it).

## Commands

```bash
~/ralph/clock.sh                 # T+elapsed / remaining / current phase / next gate
~/build-writing.sh               # build ~/writing -> ~/writing-main.pdf (pdfLaTeX, Tectonic fallback)
```

GPU work (see below — there is no local GPU, everything is remote):

```bash
G=~/.claude/skills/lobroster/scripts/gpufleet.py
bash ~/.claude/skills/lobroster/scripts/lobrsync.sh   # sync code master -> workers FIRST
python3 $G status                                     # what is free / who holds what
python3 $G submit --name X --gpus 1 --min-vram 20 \
  --workdir '~/lobroster' --cmd 'python ...' \
  --activate 'source ~/.gpufleet/venvs/lobroster/bin/activate'
python3 $G ps                                         # state + current/peak GPU memory
python3 $G logs <job_id>                              # READ THIS before believing a result
python3 $G dispatch --watch 60                        # drain the queue as GPUs free up
```

Skills: `/lobroster:gpu-status`, `gpu-submit`, `gpu-queue`, `code-sync`, `env-setup`.

## Hardware reality — the plan is wrong about this

**`DEPTH-AR-PLAN.md` §6 and `experiment.md` §1 both assume "two A100 80GB GPUs".
Those do not exist.** Do not plan compute against them.

What actually exists: **this master node has no GPUs at all.** All compute is on
four shared, multi-user lab servers reached over SSH, with **no scheduler** —
`gpufleet` *is* the scheduler:

- **alin14** — 8× RTX 3090 (24 GB), but **GPU0 holds orphaned VRAM and is excluded**,
  so **7 usable**. This is the only box with real headroom.
- **alin10 / alin11 / alin12** — 8× RTX 2080 Ti (11 GB) each; `sm_75`, **no bf16**.

Consequences for the plan: 24 GB ≠ 80 GB. Model sizes and batch/sequence budgets
must be re-derived, and the 7B stage in plan §6 is not obviously feasible.
Prefer alin14 + the smallest model that tests the phenomenon. If a plan step
assumes 80 GB, **say so and adapt rather than silently OOM**.

Other people share these machines. **Never kill, signal, or evict a process the
fleet did not launch** — `OTHER` GPUs are off limits, and `sudo` is unavailable.

## The loop that actually matters

`$HOME` is **not shared** between the master and the workers. A worker runs its
**own copy** of the code.

1. Edit here → 2. **sync** → 3. check GPUs → 4. submit → 5. **read the log**.

**Skipping the sync is the top failure mode of this setup**: an unsynced worker
silently runs old code and produces plausible-looking wrong numbers. A sync is
~1 KB and effectively free. Do it every time.

The Python environment is defined **once** in `~/lobroster/requirements.txt`
(torch 2.5.1+cu124, transformers 4.46.3, Python 3.11) and propagated by
`env-setup` to all four hosts. Never hand-install a package on one worker —
silent drift means results that don't reproduce across hosts, and you will not
notice until the numbers disagree.

## Two project directories — know which is which

- **`~/auto-research/`** — what `experiment.md` says the experiment agent owns.
  Currently near-empty (`smoke_test.py`, `obs.py`).
- **`~/lobroster/`** — scaffold + the synced environment, with its own `CLAUDE.md`.
  It is what the `gpufleet` tooling and the four workers are wired to.

These have **not** been reconciled. Before writing experiment code, pick one and
say which; do not scatter code across both.
