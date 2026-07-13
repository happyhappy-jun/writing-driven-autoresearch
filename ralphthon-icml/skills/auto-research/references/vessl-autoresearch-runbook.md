# Official VESSL Autoresearch Runbook

Use this runbook only for the Training path. The execution SOT is
[`vessl-ai/vessl-cloud-cookbook/autoresearch`](https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/autoresearch)
at commit `97a0af14b0acae042162b1f70f17fbe2d570afa2`. At that pin, `prepare.py` and the baseline `train.py` match
[`karpathy/autoresearch@228791fb499afffb54b46200aca536f79142f117`](https://github.com/karpathy/autoresearch/commit/228791fb499afffb54b46200aca536f79142f117).

This skill adds a Ralphthon safety and observability overlay. It does not fork, redesign, or shrink the benchmark. At the pinned source, the inherited `prepare.py` and baseline `train.py` are byte-for-byte matches to the named Karpathy commit: their Git blob IDs are respectively `06bea9165abd3ae94ea82dd733997aec7928f40c` and `2e743974c7f06b54311643b314712303fbb26e65` in both repositories.

## 1. Preserve the benchmark

Use a participant-owned, writable fork of `vessl-ai/vessl-cloud-cookbook`. The VESSL Job must be able to clone the selected fork and branch without putting a Git credential in chat, a command, or the repository.

Before spend:

1. Fetch the official commit and create a fresh `autoresearch/<tag>` branch from that exact commit.
2. Run `git remote get-url origin`; verify it is the participant-owned fork and `AUTORESEARCH_REPO_URL` names the same cloud-clonable remote.
3. Verify the branch does not already exist on that remote with `git ls-remote --heads origin "autoresearch/<tag>"`.
4. Compare the recipe with the official pin. Keep `prepare.py`, `pyproject.toml`, `uv.lock`, `benchmarks.md`, `analysis.ipynb`, `results.example.tsv`, and `batch-job/` unchanged. Establish the baseline with the pinned `train.py` unchanged.
5. Push that unchanged pinned branch to the participant fork before any prep spend. Re-run `git ls-remote --heads origin "autoresearch/<tag>"` and require its full remote SHA to equal the local full `git rev-parse HEAD`. This is necessary because the official prep Job clones `AUTORESEARCH_BRANCH`; an absent or mismatched remote branch is a hard stop.
6. After the baseline, make experimental changes only to `train.py`. One candidate contains one stated hypothesis and one change.

Do not vendor a new benchmark, change `evaluate_bpb`, alter data or tokenizer preparation, add dependencies, or change the benchmark defaults. A100 results and H100 results are not directly comparable.

## 2. Complete W&B and VESSL preflight

Complete both required onboarding skills before a Job is created:

- `wandb-onboarding`: pass the synthetic offline tutorial. Keep the API key on the local machine; do not inject it into VESSL.
- `vessl-cloud-onboarding`: verify auth, organization, team, cluster, inventory, billing, and storage without exposing tokens.

The official VESSL recipe uses these controls:

| Variable | Purpose |
| --- | --- |
| `AUTORESEARCH_CACHE_VOLUME` | Required object-volume slug mounted at `/root/.cache/autoresearch` |
| `AUTORESEARCH_RESOURCE_SPEC` | Exact live resource-spec slug |
| `AUTORESEARCH_IMAGE` | Approved container image |
| `AUTORESEARCH_REPO_URL` | Participant-owned cloud-clonable fork |
| `AUTORESEARCH_BRANCH` | Branch used by the one-time prep Job |
| `AUTORESEARCH_TIMEOUT_S` | Local polling timeout; it does **not** terminate the remote Job |
| `AUTORESEARCH_POLL_INTERVAL_S` | Async polling interval; not used by the default bounded linear path |

Do not accept the cookbook's H100 default. Query live inventory:

```bash
vesslctl auth status
vesslctl config show
vesslctl billing show
vesslctl cluster list
vesslctl resource-spec list --usable-only -o json
vesslctl storage list
vesslctl volume list
```

Select an **exact currently usable single-A100 spec** and record the exact live resource spec. After approval, set both `APPROVED_A100_RESOURCE_SPEC` and `AUTORESEARCH_RESOURCE_SPEC` to that same live slug. Never hardcode an illustrative slug, silently use the recipe default, substitute H100/another GPU/CPU, or enlarge the model. Show organization, team, cluster, spec, GPU count, live hourly price, credit, image, object-volume capacity/rate, expected Job and storage lifetime, estimated cost, total cap, and cleanup/timeout action. Obtain explicit confirmation for those exact values.

Data preparation may use a separately approved live CPU spec. It is a separate billable Job and the object volume can continue to cost after compute ends.

## 3. Prepare the official cache once

Set the participant fork and pinned branch explicitly, then run the official script unchanged:

```bash
export AUTORESEARCH_REPO_URL="${PARTICIPANT_FORK_URL:?set the reviewed fork URL}"
export AUTORESEARCH_BRANCH="autoresearch/<tag>"
export AUTORESEARCH_CACHE_VOLUME="<approved-object-volume-slug>"
AUTORESEARCH_RESOURCE_SPEC="<approved-live-cpu-spec>" bash autoresearch/batch-job/prep.sh
```

The remote branch must already have passed the push/SHA check in section 1. The pinned recipe prepares the existing benchmark cache; do not change the shard count or preparation code.

`prep.sh` has no `AUTORESEARCH_TIMEOUT_S` watcher. Treat it as a separately billable Job: approve a prep wall-clock cap and termination action, do not leave it unattended, capture its slug with `vesslctl job list -o json`, and inspect it with `vesslctl job show <slug> -o json`. If the cap expires, interrupt the local waiter, execute the approved `vesslctl job terminate <slug>`, and confirm a terminal state. A local interruption alone does not stop billing.

After prep succeeds, re-export the approved training spec because the inline CPU assignment above is not persistent:

```bash
export AUTORESEARCH_RESOURCE_SPEC="$APPROVED_A100_RESOURCE_SPEC"
test "$AUTORESEARCH_RESOURCE_SPEC" = "$APPROVED_A100_RESOURCE_SPEC"
```

Derive the canonical cache fingerprint with a separately approved read-only CPU verification Job mounting the same object volume. Its command must hash the sorted contents of `data/` and `tokenizer/` without printing file contents:

```bash
set -euo pipefail
cd /root/.cache/autoresearch
find data tokenizer -type f -print0 \
  | LC_ALL=C sort -z \
  | xargs -0 sha256sum \
  | sha256sum \
  | awk '{print "CACHE_SHA256=" $1}'
```

Submit that command with `vesslctl job create` on an approved live CPU spec and the same `--object-volume "${AUTORESEARCH_CACHE_VOLUME}:/root/.cache/autoresearch"` mount. Record only `sha256:<64 lowercase hex>` from the terminal Job log as `cache_fingerprint`; reject placeholder or free-form values. This verification Job has its own price, timeout, slug, terminal-state, and cleanup gate. Repeat the same read-only hash Job at campaign close. If the closing hash differs, invalidate the campaign evidence rather than selecting a winner.

## 4. Verify the A100 and freeze the run card

The live resource-spec inventory is the authoritative hardware contract. Inspect the selected spec's GPU type and count before creation, then confirm with `vesslctl job show <slug> -o json` that the Job uses that exact spec. Retain both records and the resolved GPU identity in the run card and ledger. If identity is absent, differs, or is not one A100, terminate according to the approved cleanup decision and stop. Do not infer hardware from a friendly spec name alone, and do not edit the official runner merely to add a hardware probe.

Before the baseline, freeze:

- official cookbook SHA and Karpathy source SHA;
- fork URL, remote branch, full remote commit, VESSL Job name/slug/state;
- exact resource spec, GPU identity/count, image, cache volume and fingerprint;
- evaluation identity and baseline `train.py` hash;
- W&B entity/project/visibility/upload allowlist;
- wall-clock, price, storage, candidate-count, and cleanup caps.

Upstream MFU uses H100 assumptions. Treat it as diagnostic only; use `val_bpb` as the research metric.

## 5. Run the bounded linear campaign

Use only the official blocking path:

```bash
: "${APPROVED_A100_RESOURCE_SPEC:?set the exact approved live single-A100 slug}"
: "${AUTORESEARCH_RESOURCE_SPEC:?A100 resource spec must be explicit}"
if [ "$AUTORESEARCH_RESOURCE_SPEC" != "$APPROVED_A100_RESOURCE_SPEC" ]; then
  echo "resource spec differs from the approved A100 slug; refusing submission" >&2
  exit 1
fi
bash autoresearch/batch-job/submit.sh > run.log 2>&1
grep "^val_bpb:\|^peak_vram_mb:" run.log
```

Run the three fail-closed resource checks immediately before **every** `submit.sh`. If either variable is unset or the values differ, stop before `vesslctl job create`; never allow the script's H100 default to take effect.

The script pushes the dedicated branch with `--force-with-lease`, calls `vesslctl job create`, mounts the object volume, clones the fork/branch in the Job, runs `uv run train.py`, polls `vesslctl job show -o json`, and retrieves `vesslctl job logs`. Allow that force-with-lease only after proving the branch is unique, dedicated, and on the participant-owned fork.

Use this ceiling:

1. pinned baseline once;
2. at most three sequential candidate runs;
3. one unchanged rerun of the best kept candidate.

The unchanged confirmation needs a unique wrapper identity because official `submit.sh` derives the Job name from the branch tag and short commit. After selecting the best kept candidate, create a new `autoresearch/<run-tag>-confirm` branch pointing to the **same full commit**, prove its `train.py` SHA-256 matches the kept candidate, verify the confirmation branch is absent remotely, push it, and verify its remote SHA. Run `submit.sh` from that branch. Require a new Job name and slug; the recorder must reject reuse. The changed branch creates a unique Job name while the identical commit and `train.py` hash prove the experiment itself is unchanged.

The official `batch-job/submit-async.sh` and `batch-job/wait-jobs.sh` exist for fan-out but are outside this bounded profile. **DO NOT USE** `git reset --hard`, `git add -A`, `LOOP FOREVER`, or `NEVER STOP`. When discarding a candidate, restore only `autoresearch/train.py` from the last kept commit. Stop at the candidate cap, approved cost/wall-clock cap, platform failure, or 16:30 event hard cut—whichever comes first.

Append every outcome to `experiments.jsonl`. Keep a candidate only when `val_bpb` is lower than the current kept result. A single low result is exploratory; support a Track 1 improvement claim only when the unchanged confirmation rerun also moves below the baseline in the same A100/cache/evaluation environment.

## 6. Record locally in W&B offline mode

Do not edit `train.py` to import W&B. Use `WANDB_MODE=offline` in a separate local `uv` environment for local post-processing. After each VESSL Job, retain the local log and a local `vesslctl job show -o json` snapshot. Inspect the snapshot for the lowercase terminal state and the Job's actual resource-spec, then join that exact slug to the freshly saved `resource-spec list --usable-only -o json` record for GPU model/count; cross-check direct Job fields when present. Do not guess JSON keys when the CLI schema changes. Raw logs and Job JSON stay local, but their hashes join the evidence.

This complete invocation shape is required. It intentionally gives `--git-sha` and `--remote-commit`, and approved versus actual resource specs, as separate values so a mismatch fails:

```bash
set -euo pipefail
WANDB_VERSION="0.28.0"
PLUGIN_ROOT="/path/to/ralphthon-icml"
TRAIN_LOG="run.log"
JOB_JSON="job-${VESSL_JOB_SLUG}.json"
BRANCH="$(git branch --show-current)"
LOCAL_GIT_SHA="$(git rev-parse HEAD)"
REMOTE_COMMIT="$(git ls-remote "$AUTORESEARCH_REPO_URL" "refs/heads/$BRANCH" | awk '{print $1}')"
test "$LOCAL_GIT_SHA" = "$REMOTE_COMMIT"

vesslctl job show "$VESSL_JOB_SLUG" -o json > "$JOB_JSON"

: "${CACHE_FINGERPRINT:?use the canonical cache hash from the CPU verification Job}"
: "${JOB_RESOURCE_SPEC:?extract the actual Job spec from the saved Job JSON}"
: "${GPU_IDENTITY:?resolve the normalized A100 model from the exact live/Job spec}"
: "${GPU_COUNT:?resolve the structured GPU count from the exact live/Job spec}"
: "${VESSL_JOB_STATE:?use succeeded, failed, terminated, or cancelled}"
test "$APPROVED_A100_RESOURCE_SPEC" = "$JOB_RESOURCE_SPEC"
test "$GPU_COUNT" -eq 1

WANDB_MODE=offline uv run --with "wandb==$WANDB_VERSION" \
  python "$PLUGIN_ROOT/skills/auto-research/scripts/record_experiment.py" \
  --summary "$TRAIN_LOG" --job-json "$JOB_JSON" \
  --train-py autoresearch/train.py --evaluation-file autoresearch/prepare.py \
  --ledger experiments.jsonl \
  --wandb-dir .wandb-offline --entity "$WANDB_ENTITY" --project "$WANDB_PROJECT" \
  --run-tag "$RUN_TAG" --trial "$TRIAL" \
  --git-sha "$LOCAL_GIT_SHA" --remote-commit "$REMOTE_COMMIT" \
  --hypothesis "$HYPOTHESIS" --change "$CHANGE" --status "$STATUS" \
  --cookbook-sha 97a0af14b0acae042162b1f70f17fbe2d570afa2 \
  --vessl-job-slug "$VESSL_JOB_SLUG" --vessl-job-name "$VESSL_JOB_NAME" \
  --vessl-job-state "$VESSL_JOB_STATE" \
  --approved-resource-spec "$APPROVED_A100_RESOURCE_SPEC" \
  --job-resource-spec "$JOB_RESOURCE_SPEC" \
  --gpu-identity "$GPU_IDENTITY" --gpu-count "$GPU_COUNT" \
  --branch "$BRANCH" --cache-fingerprint "$CACHE_FINGERPRINT" \
  > "recorder-${TRIAL}.json"
```

Add `--failure "<concise local failure>"` only for `--status crash`; do not put secrets, raw logs, paths, or private participant data in it. The recorder computes the log, Job-JSON, `train.py`, and evaluation hashes directly from those four required paths; it does not accept caller-asserted substitutes. It parses the saved Job JSON and requires its slug, name, state, and resource spec to match the separately supplied fields. It also requires full lowercase 40-hex Git SHAs, a canonical `sha256:<64 lowercase hex>` cache hash, exact approved/actual spec equality, a structured GPU count of `1`, an A100 model, and a terminal Job state. Its locked ledger rejects duplicate Job identities, campaign-invariant drift, a non-improving keep, and a confirmation that differs from the best kept commit or `train.py` hash.

The recorder appends the local ledger and creates a W&B **offline** run with `group=<run_tag>` and `job_type=autoresearch-trial`. Its config/metric allowlist is limited to run/trial identity, Git and cookbook SHAs, VESSL Job correlation, approved/actual A100 spec/model/count, canonical cache and evidence hashes, `val_bpb`, reported parameter/VRAM/time values, and keep/discard/crash/confirmation status. It disables or excludes console logs, source code, Git patches, requirements, machine metrics/info, datasets, checkpoints, and artifacts. W&B's offline format still contains a sanitized host label, SDK/Python/platform versions, timestamps/runtime, and SDK telemetry records.

Do not install a W&B secret in VESSL. Do not call W&B Sweeps or W&B Launch; VESSL remains the only compute scheduler.

After every approved offline run exists, show the exact entity, project, visibility, run directories, `group`, `job_type`, config/metric upload allowlist, excluded files, and unavoidable SDK metadata. Obtain explicit confirmation immediately before each `wandb sync --entity` action. If zero SDK metadata is required, do not sync:

```bash
uv run --with "wandb==0.28.0" wandb sync \
  --entity "$WANDB_ENTITY" \
  --project "$WANDB_PROJECT" \
  --skip-console \
  --no-sync-tensorboard \
  "$WANDB_RUN_DIRECTORY"
```

After sync, optionally use the read-only Public API to verify the destination and allowlist. W&B ARIA may analyze an approved synced run; it must not replace VESSL scheduling or make unverified claims.

## 7. Handle timeout and cleanup

`AUTORESEARCH_TIMEOUT_S` stops only the local wait loop. It does not stop the remote Job or billing. On timeout or interrupted polling:

1. recover the Job slug from local output or `vesslctl job list`;
2. run `vesslctl job show <slug> -o json`;
3. show the live state and continuing exposure;
4. execute `vesslctl job terminate <slug>` only when that exact timeout action was already approved or after obtaining explicit confirmation;
5. recheck state and logs and record the confirmed terminal state before reporting cleanup.

At campaign close, inspect all Jobs, W&B offline/sync state, and the object volume. Job termination stops compute but preserves Job configuration, metrics, and logs; a persistent volume may continue to cost. Explain Pause versus Terminate where a Workspace is involved, obtain the cleanup decision, and never claim all cost ended until compute and persistent storage are checked.

## Official sources

- VESSL recipe pin: <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/97a0af14b0acae042162b1f70f17fbe2d570afa2/autoresearch>
- VESSL walkthrough: <https://docs.cloud.vessl.ai/examples/autoresearch>
- VESSL GPU pricing reference: <https://docs.cloud.vessl.ai/pricing/gpu-instances>
- Karpathy source pin: <https://github.com/karpathy/autoresearch/tree/228791fb499afffb54b46200aca536f79142f117>
- W&B offline mode: <https://docs.wandb.ai/models/track/environment-variables>
- W&B sync CLI: <https://docs.wandb.ai/models/ref/cli/wandb-sync>
