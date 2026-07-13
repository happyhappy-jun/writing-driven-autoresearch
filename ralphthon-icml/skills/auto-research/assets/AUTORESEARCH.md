# Official VESSL Autoresearch Campaign Control

## Fixed contract

- Execution source: `vessl-ai/vessl-cloud-cookbook/autoresearch`
- Official cookbook revision: `97a0af14b0acae042162b1f70f17fbe2d570afa2`
- Karpathy source revision: `228791fb499afffb54b46200aca536f79142f117`
- Identity: one campaign `run_tag`; trials are `baseline`, `candidate-1` through `candidate-3`, and `winner-confirmation`
- Hardware: exactly one NVIDIA A100; no GPU fallback
- Metric: `val_bpb`, lower is better; MFU is diagnostic only
- Benchmark: official `prepare.py` and baseline `train.py` unchanged; no custom benchmark, data, tokenizer, evaluation, dependency, or runner edits
- Budget: baseline + at most three sequential candidates + one unchanged winner confirmation, further bounded by the approved cost/wall-clock cap
- Frozen identities: fork/branch/commit, cache fingerprint, evaluation identity, A100 resource spec, and Job correlation

## Before baseline

- [ ] W&B synthetic offline tutorial passed
- [ ] Planned W&B entity/project/visibility, `group`, `job_type`, allowlist, and SDK-metadata disclosure were reviewed; no upload has been approved yet
- [ ] VESSL live A100 spec, hourly price, credit, image, object volume, duration, estimate, timeout action, and cleanup received explicit confirmation
- [ ] The live resource-spec record proves one A100 and the VESSL Job configuration references that exact spec
- [ ] The participant-owned fork, dedicated branch, and cloud clone path are verified
- [ ] The unchanged pinned branch is pushed and its full remote SHA equals local HEAD before the prep Job
- [ ] Prep Job cap/termination is approved; the canonical `sha256:<64hex>` cache fingerprint is produced by the separately approved read-only CPU hash Job
- [ ] Cookbook and Karpathy pins, cache fingerprint, evaluation identity, and baseline `train.py` hash are frozen
- [ ] A new `experiments.jsonl` is initialized as an empty file; the ledger documentation example was not copied
- [ ] `record_experiment.py` runs locally after VESSL logs are fetched; every W&B run remains offline until a later directory-specific `wandb sync` confirmation

## Immediately before each W&B sync

- [ ] The completed offline run's exact directory is shown
- [ ] Entity, project, visibility, config/metric allowlist, and excluded files are shown again
- [ ] Unavoidable W&B SDK metadata (sanitized host, SDK/Python/platform versions, timestamps/runtime, and SDK telemetry records) is disclosed
- [ ] The user explicitly confirms this exact directory and destination now; a pre-baseline planning approval is not reused

## Trial rule

Write one hypothesis and one change before editing. After the pinned baseline, modify only `train.py`. Before and after every Job, verify the official benchmark files, cache/evaluation identity, branch/commit, approved spec equals the created Job spec, exactly one A100, and terminal-state correlation. Keep only a strictly lower `val_bpb`; otherwise restore only that file from the last kept commit. Append the outcome even when it crashes. Trial IDs and Job name/slug/log hash are unique and sequential. Winner-confirmation requires a kept candidate and is last; run it from a unique `autoresearch/<run-tag>-confirm` branch pointing to the same full commit and identical `train.py` hash as the best kept candidate. Do not alter the harness, data, tokenizer, evaluation, dependencies, batch-job scripts, logging allowlist, or prior ledger lines.

## Stop rule

Stop after three candidates, after winner confirmation, at the approved wall-clock/cost cap, on platform incompatibility, or at the event hard cut—whichever comes first. Do not use parallel fan-out or an unbounded loop. A local polling timeout does not stop the VESSL Job: inspect it and execute only the approved termination action. Re-run the read-only cache hash Job at close and invalidate the campaign if it changed. Never scale the model or select another GPU automatically.
