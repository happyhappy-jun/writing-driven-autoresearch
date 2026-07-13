---
name: auto-research
description: Use when preparing Ralphthon research specifications or 연구 명세, automated experiments, a Track 1 short paper or 논문, a Track 2 review agent or 리뷰, or an evidence-backed submission under the event deadline.
---

# Auto Research

## Overview

Turn one testable idea into reproducible evidence, then produce a submission-ready artifact. When the task needs new autoresearch training evidence, run the official VESSL cookbook recipe on one approved A100 with a bounded safety and W&B observability overlay. Keep claims no stronger than the recorded results.

Read [the event workflow and evidence contract](references/workflow.md) before planning. For a Training campaign, also read the complete [official VESSL autoresearch runbook](references/vessl-autoresearch-runbook.md). Copy the appropriate template from `assets/` into the participant workspace.

## Preflight

Confirm the selected Track, current time, 16:30 submission hard cut, permitted public data, available evidence, and whether the work creates new autoresearch training evidence. Do not load private participant, reviewer, messaging, or operations records.

## Submission Contract

| Path | Required output |
| --- | --- |
| Track 1 | Agent workflow plus a **2-4 page** workshop-style short paper and **self-review** |
| Track 2 | Review agent plus an **ICML-style review** result for a Track 1 paper |
| Both | Complete Track 1 evidence first, then review the frozen paper with Track 2 |

Treat the final paper/agent submission at **16:30** as a hard cut. Peer and self-review may follow. During the **Ralph Loop**, operate through the coding agent and preserve an audit trail of prompts, code, runs, and outputs.

## Workflow

Select exactly one path below. Do not merge the compute and no-compute preflight requirements. Use the bundled references, assets, and recorder directly from this skill.

## Select exactly one path

### Training path (Track 1 or Both)

Choose this path only when generating **new autoresearch training evidence**. It includes all compute, cost, metric, and onboarding requirements below.

1. Freeze a **research spec** containing one **falsifiable hypothesis**, a named **baseline**, `val_bpb` as the **evaluation metric**, dataset, budget, and stop condition.
2. **REQUIRED SUB-SKILL:** Use `wandb-onboarding`, including its synthetic offline run. Before online sync, show entity, project, visibility, and the exact W&B allowlist and obtain **explicit confirmation**.
3. **REQUIRED SUB-SKILL:** Use `vessl-cloud-onboarding`. Run `vesslctl resource-spec list --usable-only -o json`; show the live exact single A100 spec, hourly price, credit, image, object volume, wall-clock cap, total estimate, and cleanup/timeout plan. Provision only after **explicit confirmation**.
4. Use [`vessl-ai/vessl-cloud-cookbook/autoresearch`](https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/autoresearch) pinned at `97a0af14b0acae042162b1f70f17fbe2d570afa2` as the execution SOT. Use a participant-owned writable fork and the recipe's `vesslctl job create` flow. Override its default with the approved live A100 spec; **do not fall back** to another GPU, CPU, or a larger model, and never substitute H100.
5. Keep the official benchmark unchanged: this is an unchanged benchmark, not a reimplementation. The baseline uses the pinned `prepare.py` and `train.py`; candidates may modify only `train.py`, one hypothesis and one change at a time. Do not modify the evaluation harness, dependencies, benchmark reports, data, tokenizer, or batch-job scripts.
6. Copy [the campaign control file](assets/AUTORESEARCH.md), [VESSL A100 run card](assets/vessl-a100-run-card.md), [experiment ledger template](assets/experiment-ledger.md), and `scripts/record_experiment.py`, then execute the complete [official VESSL autoresearch runbook](references/vessl-autoresearch-runbook.md). The recorder consumes each fetched VESSL log locally, appends `experiments.jsonl`, and creates only an allowlisted W&B offline run until separately approved sync.
7. Run one baseline, at most three candidate trials executed sequentially, and one **winner confirmation**. Do not use the cookbook's parallel fan-out or unbounded loop. Keep only a lower `val_bpb`.

Do not fall back when the approved single A100 is unavailable; stop and report the blocker.
8. Separate evidence from interpretation, report **failure modes** and limitations, and produce Track 1 plus its self-review. For Both, freeze Track 1, copy [the Track 2 Review Agent template](assets/track-2-agent-template.md) to `review-agent.md`, freeze its version/input hashes, and run it with [the Track 2 review result template](assets/track-2-review-template.md). Submit both artifacts.

Training uses a **W&B allowlist** containing only `run_tag`, `trial`, Git and cookbook SHAs, remote branch/commit, VESSL Job slug/name/state, approved/actual resource spec, exact A100 model/count, canonical cache and evidence hashes, `val_bpb`, reported parameter/VRAM/time values, and status. Store runs locally with `group=run_tag` and `job_type=autoresearch-trial`. Exclude console logs, source code, Git patches, requirements, machine metrics/info, datasets, checkpoints, artifacts, secrets, and private participant data. W&B's offline format still includes internal SDK metadata (sanitized host, SDK/Python/platform versions, timestamps/runtime, and SDK telemetry records); disclose it in the action-time sync approval.

The cookbook recipe is the sole execution profile; no custom micro preset is provided. Preserve its benchmark settings and record A100 results only against the same pinned cache/evaluation identity. The cookbook's polling timeout does not terminate a remote Job: inspect the Job and execute the approved termination action when it fires. Append every outcome to `experiments.jsonl`, and preserve unrelated files with file-scoped Git operations. **DO NOT USE** `git reset --hard`, `git add -A`, `LOOP FOREVER`, or `NEVER STOP`.

### General Track 1 path (or Both)

Choose this path for a non-Karpathy research workflow or when credible evidence already exists. It **does not automatically require W&B, VESSL, or A100**. Do not force this path through the A100 runbook or require `val_bpb` when a different metric is appropriate.

1. Copy [the Track 1 submission template](assets/track-1-submission-template.md).
2. Freeze a research spec with one falsifiable hypothesis, a fair baseline, primary evaluation metric and threshold, evidence inputs, budget, stop condition, and failure modes.
3. Record the research agent workflow, versions, commands/prompts, human checkpoints, raw outputs, exclusions, and negative or inconclusive results.
4. Recompute the headline result from the frozen evidence, then produce the 2-4 page paper and self-review. Never present planned work as an observed run.
5. For Both, freeze the paper and evidence bundle before running the Track 2 Review Agent below.

### Track 2-only frozen-paper path

Choose this mutually exclusive path only to review a **frozen Track 1 paper** and its existing evidence. It can **skip** training onboarding and the A100 runbook: it **does not require `val_bpb`**, **does not require a GPU**, and **does not require W&B or VESSL**, a cost card, account creation, or new experiments.

1. Record the frozen paper version and the supplied evidence paths without changing them.
2. Copy [the Track 2 Review Agent template](assets/track-2-agent-template.md) to `review-agent.md`; freeze its name/version, input hashes, instruction, output contract, and evidence guardrails.
3. Run that agent with [the Track 2 review result template](assets/track-2-review-template.md) to assess soundness, evidence support, weaknesses, questions, and confidence.
4. Trace review statements to the frozen artifact. Do not invent a missing run or demand Karpathy-specific metrics from unrelated research.
5. Return both `review-agent.md` and the ICML-style review result with blockers. If evidence is insufficient, say so; do not silently switch paths.

## Integrity Gate

**Do not fabricate** results, citations, runs, reviewer evidence, or sponsor claims. Never backfill experiments to match prose. Label planned or expected results explicitly. If a run fails, report the failure and narrow the claim.

Stop and correct the artifact when:

- a number cannot be traced to a saved result;
- the paper and review use different experiment versions;
- a claimed improvement lacks the named baseline or metric;
- negative or inconclusive evidence was omitted;
- private participant, reviewer, or operations data appears in the artifact.

On the Training path only, also stop when the live GPU is not exactly one A100, an approved price/resource field changed, or a candidate changes the data, tokenizer, evaluation harness, or more than one experimental factor. These compute gates do not apply to Track 2-only.

## Verification

- Recompute headline values from the frozen evidence and confirm the winner rerun before claiming improvement.
- Trace every number and central claim to a saved result; verify citations, the 2-4 page limit, baseline fairness, metric validity, negative results, and self-review.
- For Track 2, verify the paper/evidence hashes and that `review-agent.md` produced the structured result without inventing missing evidence.
- For Training, inspect the append-only ledger, offline W&B run directories, VESSL Job correlation, exact experiment count, best confirmed `val_bpb`, artifact paths, cost exposure, and cleanup state.
- Treat MFU as diagnostic only; use `val_bpb` as the research metric. Do not compare A100 measurements directly with the official H100 benchmark.

## Output

For Training, return the frozen research spec, resource/approval state, exact experiment count, best confirmed `val_bpb`, artifact paths, Track artifacts, cleanup, blockers, and next action. For General Track 1, return the research spec, agent workflow, frozen evidence, short paper, self-review, blockers, and next action. For Track 2-only, return the frozen paper version, supplied evidence paths, `review-agent.md`, ICML-style review result, confidence, blockers, and next review action; omit all compute, cost, W&B, GPU, and training-metric fields.

## Next Steps

- Track 1 complete: freeze the paper and run self-review.
- Track 2 complete: attach both `review-agent.md` and the structured review with evidence trace.
- Both complete: confirm the reviewer used the frozen Track 1 version.
- Training complete: obtain the documented Pause/Terminate cleanup decision and report any remaining storage exposure.

## Common Mistakes

- Training: broad topic without a falsifiable hypothesis → reduce to one measurable comparison.
- Training: paper-first workflow → finish one real end-to-end run before polishing prose.
- Review-as-summary → score soundness, evidence, weaknesses, questions, and confidence.
- Deadline optimism → preserve a complete small result instead of an unfinished large experiment.
- Training: cheap-credit optimism → live hourly price, storage, duration, and cleanup still require explicit confirmation.
- Training: single lucky score → rerun the winner before making a Track 1 improvement claim.
