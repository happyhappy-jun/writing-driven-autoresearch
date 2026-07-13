# Official W&B Ecosystem for Autoresearch

W&B does not maintain a single repository named “cookbook.” Use the official documentation repository as the primary SOT, then use the official experimental agent skills and example repositories as task-specific references.

Research snapshot verified on 2026-07-11: [`wandb/docs@ecfe9f49`](https://github.com/wandb/docs/commit/ecfe9f49a952b1520d86cc9f4d325ba9619dfe97) and [`wandb/skills@6ca7ed0a`](https://github.com/wandb/skills/commit/6ca7ed0a00f3a4bf60a2124757fe0fa303344026). These pins make this research auditable; live official docs still govern UI, authentication, SDK, and CLI behavior at action time.

## Primary sources

- Product documentation source: <https://github.com/wandb/docs>
- Published documentation: <https://docs.wandb.ai>
- Core Python SDK and CLI: <https://github.com/wandb/wandb>
- Models quickstart: <https://docs.wandb.ai/models/quickstart>
- Login CLI: <https://docs.wandb.ai/models/ref/cli/wandb-login>
- Offline environment variables: <https://docs.wandb.ai/models/track/environment-variables>
- Offline sync command: <https://docs.wandb.ai/models/ref/cli/wandb-sync>
- Run grouping and `job_type`: <https://docs.wandb.ai/models/runs/grouping>
- SDK privacy/capture settings: <https://docs.wandb.ai/models/ref/python/experiments/settings>
- Read-only Public API: <https://docs.wandb.ai/models/ref/python/public-api>
- W&B MCP Server: <https://docs.wandb.ai/platform/mcp-server>
- W&B MCP Server source: <https://github.com/wandb/wandb-mcp-server>

## Official agent and autoresearch material

- W&B agent skills: <https://github.com/wandb/skills>
- Hypothesis-generation reference: <https://github.com/wandb/skills/blob/main/skills/wandb-primary/references/HYPOTHESIS_GENERATION.md>
- ARIA autoresearch: <https://docs.wandb.ai/aria/autoresearch>

The official hypothesis pattern moves from prior evidence to an anomaly, mechanism, and one falsifiable single-variable probe. Use it to shape the next Ralphthon candidate after reviewing the current ledger. Do not convert the bounded campaign into a broad sweep.

ARIA is currently documented as a Preview surface. It can analyze runs, recommend follow-up experiments, and work with W&B Launch. In this repository, use ARIA only after an explicitly approved sync for analysis or recommendations. Do not enable Launch: VESSL is the sole scheduler and source of remote Job state.

## Official example repositories

- General examples: <https://github.com/wandb/examples>
- Educational material: <https://github.com/wandb/edu>
- Artifacts examples: <https://github.com/wandb/artifacts-examples>
- Launch Job examples: <https://github.com/wandb/launch-jobs>
- Sweeps examples: <https://github.com/wandb/sweeps>

These are reference only, not dependencies. Review the current license and version before copying material. `wandb/edu` is useful for learning but has its own GPL licensing terms. Artifacts, Launch, and Sweeps are intentionally disabled for the Ralphthon VESSL campaign: they would add uploads or a second scheduling/control plane.

The official W&B MCP Server can query W&B data from clients including Claude Code, but it is optional and disabled by default here. Hosted and local deployments require a W&B API key or bearer-token path and expand what an agent can read. Configure it only as a separate, explicitly approved integration with the credential stored in the client's secret mechanism; never put the token in this repository, a generated skill asset, chat, or a command argument. It is an analysis surface, not the VESSL compute scheduler.

## Ralphthon selection

Use only this narrow slice by default:

1. interactive `wandb login --verify` without exposing the key;
2. synthetic `WANDB_MODE=offline` verification;
3. local post-VESSL-Job offline tracking;
4. explicit entity/project/visibility/allowlist confirmation;
5. `wandb sync --skip-console --no-sync-tensorboard` for the named offline directory;
6. read-only destination and field verification.

Do not upload datasets, checkpoints, models, code, Git patches, requirements, console output, machine metrics/info, or API keys. W&B's offline format retains internal SDK metadata (sanitized host, versions, timestamps/runtime, and SDK telemetry records), so disclose it before sync; if zero SDK metadata is required, do not sync. Do not use a mutable W&B autoresearch container image as the executable default; the pinned VESSL cookbook remains the execution source of truth.
