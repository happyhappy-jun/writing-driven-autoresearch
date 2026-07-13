# Current VESSL Cloud Official Workflow

## Official Sources

- Application: <https://cloud.vessl.ai>
- Member quickstart: <https://docs.cloud.vessl.ai/guides/get-started/quickstart-user>
- CLI overview: <https://docs.cloud.vessl.ai/cli/overview>
- CLI quickstart: <https://docs.cloud.vessl.ai/cli/quickstart>
- CLI cheat sheet: <https://docs.cloud.vessl.ai/cli/cheatsheet>
- Workspace creation: <https://docs.cloud.vessl.ai/member/workspace/create>
- Autoresearch walkthrough: <https://docs.cloud.vessl.ai/examples/autoresearch>
- GPU instance pricing reference: <https://docs.cloud.vessl.ai/pricing/gpu-instances>
- Billing: <https://docs.cloud.vessl.ai/admin/billing/overview>

Verify live official documentation before using commands that may change.

## Signup and Account Model

Current VESSL Cloud signup may use Google or work email. The user performs identity selection, credentials, verification, legal/age acceptance, and final submission. Current Cloud uses Organization and Team; it does not require the legacy MLOps Project concept.

## CLI Installation and Authentication

The official installation example is:

```bash
curl -fsSL https://api.cloud.vessl.ai/cli/install.sh | bash
```

This downloads and installs a local binary and may update PATH guidance. Review the live script/instructions, explain the destination, and obtain confirmation before running it.

Authenticate and verify without reading token files:

```bash
vesslctl auth login --web
vesslctl auth status
vesslctl config show
vesslctl billing show
vesslctl org list
vesslctl team list
vesslctl cluster list
vesslctl resource-spec list --usable-only
vesslctl storage list
vesslctl volume list
```

The `--web` flag prevents fallback to terminal email/password entry. The browser OAuth step belongs to the user. Do not request access-token values or print the raw config file.

## Workspace, Job, and Volume Cost Card

Use live values from the selected organization/team and pricing summary:

- cluster and region;
- resource-spec slug, GPU type/count, CPU/RAM;
- availability and hourly price;
- credit balance and tutorial duration/cost estimate;
- image and command;
- persistent/temporary storage, capacity, hourly rate, expected lifetime/cost, and mount paths;
- SSH key and public ports;
- Pause or Terminate cleanup plan.

For a Job, also record its name/slug, remote branch/commit, polling timeout, the action to take if polling times out, and the final state. A client timeout does not terminate remote compute.

Create only after explicit confirmation. A typical CLI shape is:

```bash
vesslctl workspace create \
  --name hello-vessl \
  --cluster <cluster-slug> \
  --resource-spec <resource-spec-slug> \
  --image <approved-image>
```

After the Workspace is running, use the official connection path and run:

```bash
python -c 'print("Hello, VESSL Cloud!")'
```

Verify the output, then request a separate cleanup decision.

## Official Autoresearch Job Shape

The current official recipe is <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/autoresearch>. Ralphthon pins commit `97a0af14b0acae042162b1f70f17fbe2d570afa2` and keeps its benchmark files unchanged.

The recipe performs this sequence:

```text
local train.py commit
  -> push dedicated autoresearch/<tag> branch
  -> vesslctl job create with object-volume mount
  -> Job clones participant fork/branch and runs uv run train.py
  -> vesslctl job show -o json polling
  -> vesslctl job logs copied locally
```

Use an exact live single-A100 spec and participant-owned writable fork. Do not let the recipe's H100 default take effect. The recipe's async scripts and unbounded loop are not part of the Ralphthon default.

## Cost and Data Consequences

- Running compute is billable.
- Pause can stop compute while storage charges or preserved state remain.
- Terminate is destructive; independently managed storage may remain.
- Temporary/container state may be lost on cleanup.
- Credit exhaustion is not a cleanup plan.
- Storage, SSH keys, public ports, and Jobs are separate side effects that require their own review.
- `AUTORESEARCH_TIMEOUT_S` stops local polling only; inspect and explicitly terminate the remote Job when the approved plan requires it.
