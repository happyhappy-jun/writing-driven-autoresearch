---
name: wandb-onboarding
description: Use when signing up or 가입 for W&B Cloud, configuring a personal API key, checking authentication, or creating a first experiment-tracking run or 실험 추적 project.
---

# W&B Onboarding

## Overview

Guide signup with browser assistance, hand sensitive identity steps to the user, then verify the SDK offline before any upload. Read [the current official workflow](references/official-workflow.md) for URLs and commands. For official examples and autoresearch analysis, also read [the W&B official ecosystem](references/official-ecosystem.md).

## Preflight

Classify the target as signup, SDK authentication, offline tutorial, or online run. Confirm browser and `uv` availability without inspecting credentials, secret files, cookies, browser storage, or environment-variable values.

## Safety Contract

**Never ask** the user to paste an API key, password, MFA code, or OAuth token into chat. Do not read cookies, browser storage, password managers, `~/.netrc`, environment variable values, or raw credential files.

The user must complete identity-provider selection, credentials, OAuth consent, CAPTCHA, MFA, email verification, legal acceptance, final signup, and API-key copy. Use an **interactive prompt** for the key; never place it in a command argument, source file, generated asset, or repository.

## Workflow

1. Open the official W&B signup page with the available Browser skill. Inspect the current visible options; do not guess selectors when the page changes. If browser control is unavailable, give the exact manual link and checkpoint list.
2. Recommend the Cloud-hosted Free plan and personal entity for an individual tutorial. Present any discovered organization/team separately and let the user choose.
3. Hand off the sensitive signup steps. After the user returns, verify only the visible logged-in state.
4. Guide the user to User Settings → API Keys. The user creates and stores the key privately.
5. For existing credentials, run `wandb login --verify`. For a new key, explain the local credential write, obtain **explicit confirmation**, then run `wandb login --relogin --cloud --verify`. The user enters the key only in the interactive prompt.
6. Copy `assets/wandb-quickstart.py` into a disposable `uv` workspace. Run it first with `WANDB_MODE=offline` and inspect the completed local run.
7. Before any online run or offline-run sync, show the target **entity**, **project**, **visibility**, metrics/config fields, `group`, `job_type`, code/Git/console/system capture settings, every offline run directory, and files or data that would upload. Set or verify project visibility in the official UI, bind the approved destination through `WANDB_ENTITY` and `WANDB_PROJECT`, then obtain explicit confirmation.
8. Prefer syncing the already verified offline run with `wandb sync --entity ... --project ... --skip-console --no-sync-tensorboard <run-directory>`. Verify the authoritative run URL and visible fields after upload. Report what was uploaded and how to remove or change access if needed.

## Autoresearch integration

Keep VESSL as the sole compute scheduler and W&B as the local-first observability layer. Do not modify the official benchmark to import W&B and do not install a W&B key in VESSL. After each VESSL Job finishes, fetch `vesslctl job logs` locally and perform local post-processing with the `auto-research` recorder in `WANDB_MODE=offline`; create an offline run with `group=<run_tag>`, `job_type=autoresearch-trial`, and `val_bpb` summarized by its minimum.

The upload allowlist contains only the approved run/trial, Git/cookbook, VESSL Job, exact A100 resource/model/count, cache/evidence hashes, metric, time, VRAM, parameter, and status fields. Disable console, code, Git, requirements, machine metrics/info, automatic Job creation, datasets, checkpoints, and artifacts. W&B 0.28.0 still writes internal SDK metadata to an offline run: the recorder uses a sanitized host, but SDK/Python/platform versions, timestamps/runtime, and SDK telemetry records remain. Sync only after the user confirms entity, project, visibility, allowlist, exact offline directories, and that metadata disclosure.

W&B ARIA is an optional official analysis surface after approved sync. It may inspect results and propose a falsifiable single-variable probe; do not use ARIA Launch, W&B Launch, Sweeps, or Jobs to schedule this VESSL campaign.

## Completion Levels

| Level | Evidence |
| --- | --- |
| Account ready | User confirms signup and visible logged-in state |
| SDK ready | `wandb login --verify` succeeds without exposing the key |
| Local tutorial ready | Offline run finishes and creates a local W&B run directory |
| Online tutorial ready | User-approved offline run is synced to the intended entity/project and visibility |

## Stop Conditions

Stop before signup submission, team join/create, trial or payment selection, API-key creation/revocation, credential storage, or online upload unless the user has authorized that exact action. If authentication or upload partially succeeds, inspect status before retrying to avoid duplicate keys or runs.

## Verification

- Verify authentication with `wandb login --verify` without printing the key.
- For offline work, confirm the synthetic run completes and creates a local run directory.
- For online work, verify the authoritative W&B URL, entity, project, visibility, config, metrics, group/job type, capture settings, and every uploaded file or data field.
- Report what was uploaded and the remaining privacy, access-control, deletion, or cleanup work.

## Output

Return the completion level, verified evidence, user handoff, exact planned or completed side effect, authoritative run URL when applicable, and remaining privacy or cleanup work.

## Next Steps

- Offline complete: review the upload card and stop for confirmation.
- Online approved: sync the reviewed offline run and verify it.
- Online declined: preserve the local offline artifact and stop.

## Common Mistakes

- Key in a shell argument → use `wandb login --verify` and its interactive prompt.
- Immediate online test → prove the script with `WANDB_MODE=offline` first.
- Project name without entity/visibility → show all three before confirmation.
- “No dataset” assumed safe → config, metrics, logs, code, and system metadata can still upload.
- Putting W&B inside the VESSL benchmark → keep benchmark execution unchanged and record fetched logs locally.
- Using Launch or Sweeps for this campaign → VESSL is the only scheduler; keep the experiment loop bounded and sequential.
