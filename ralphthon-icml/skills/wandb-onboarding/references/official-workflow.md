# W&B Cloud Official Workflow

## Official Sources

- Signup: <https://wandb.ai/signup>
- Models Quickstart: <https://docs.wandb.ai/models/quickstart>
- CLI login: <https://docs.wandb.ai/models/ref/cli/wandb-login>
- Offline environment variables: <https://docs.wandb.ai/models/track/environment-variables>
- Sync CLI: <https://docs.wandb.ai/models/ref/cli/wandb-sync>
- User settings and API keys: <https://docs.wandb.ai/platform/app/settings-page/user-settings>
- ARIA autoresearch: <https://docs.wandb.ai/aria/autoresearch>
- Pricing: <https://wandb.ai/site/pricing/>

Verify the live official page when UI labels or plan details matter.

## Signup Handoff

The official signup flow may offer Apple, GitHub, Google, Microsoft, or email/password. Browser automation may open and inspect the page. The user completes provider choice, credentials, OAuth approval, CAPTCHA/MFA, email verification, legal acceptance, and final submission.

For a personal tutorial, recommend the Cloud-hosted Free plan and personal entity. Do not automatically join an organization, create a team, begin a trial, or make a payment choice.

## API Key and Login

Personal API keys are created in User Settings and the full secret may be shown only at creation. For a new key, the user stores it in a password or secrets manager and enters it directly into the forced terminal prompt:

```bash
uv tool run --from wandb wandb login --relogin --cloud --verify
```

The installed-project equivalent is `uv run wandb login --relogin --cloud --verify`. If credentials already exist and the user only wants validation, do not force a new prompt:

```bash
uv run wandb login --verify
```

Do not echo the key, pass it as an argument, print `WANDB_API_KEY`, or read credential files. Login may write credentials locally; explain this before requesting confirmation.

## Offline-First Tutorial

```bash
mkdir wandb-quickstart
cd wandb-quickstart
uv init --bare
uv add wandb
cp <skill-path>/assets/wandb-quickstart.py .
WANDB_MODE=offline uv run wandb-quickstart.py
```

Confirm a completed offline run before proposing an upload.

## Online Sync Gate

Present this card and obtain explicit confirmation:

- entity:
- project:
- visibility/access:
- config keys and values:
- metric keys:
- code/Git capture:
- console and machine metric/info capture:
- unavoidable SDK metadata (sanitized host, SDK/Python/platform versions, timestamps/runtime, SDK telemetry records):
- group and job type:
- exact offline run directories:
- files, tables, artifacts, stdout, or system metadata expected to upload:

Before syncing, set or verify the approved project visibility in the W&B UI. Bind the approved destination explicitly rather than relying on the default team. Sync only the reviewed offline directory:

```bash
wandb sync \
  --entity "$WANDB_ENTITY" \
  --project "$WANDB_PROJECT" \
  --skip-console \
  --no-sync-tensorboard \
  "$WANDB_RUN_DIRECTORY"
```

Verify the URL printed by W&B and inspect the intended entity, project, visibility, config, and metrics on the official run page.

## Local post-Job autoresearch pattern

Do not add W&B SDK calls to the official VESSL/Karpathy benchmark and do not store a W&B key in VESSL. Fetch `vesslctl job logs` to the local machine, then create one W&B offline run per trial. Use:

- `group=<run_tag>`;
- `job_type=autoresearch-trial`;
- `val_bpb` with minimum summary;
- disabled console, code, Git, requirements, machine metrics/info, and automatic Job creation;
- no dataset, checkpoint, model, table, or Artifact logging.

The W&B offline record still contains internal SDK metadata: a sanitized host label, SDK/Python/platform versions, timestamps/runtime, and SDK telemetry records. `--skip-console` does not remove those records. Show this disclosure in the upload card; if the user requires zero SDK metadata, preserve the run locally and do not sync it.

Correlate the offline run with the full Git/cookbook SHAs, remote branch/commit, VESSL Job slug/name/state, exact live A100 spec and identity, and cache fingerprint. Crash runs finish with a nonzero exit code. Treat W&B as observability only; VESSL remains the compute scheduler.
