# W&B MCP Analysis Workflows

## Connection Preflight

Prefer the hosted W&B MCP server. If it is unavailable, explain the setup without exposing credentials:

```bash
export WANDB_API_KEY=...
claude mcp add --transport http wandb https://mcp.withwandb.com/mcp \
  --header "Authorization: Bearer ${WANDB_API_KEY}"
```

Verify with: `List my W&B entities.` Do not run configuration commands unless the user asks to configure the client.

## Discover An Unfamiliar Project

1. `list_entities_tool` when the entity is unknown.
2. `query_wandb_entity_projects` when the project is unknown.
3. `probe_project_tool` for Models metrics, configs, and tags.
4. `infer_trace_schema_tool` for Weave fields and sample values.
5. Run a targeted query using discovered names and keys.

## Analyze Models Runs

- Use `query_wandb_tool` for run, config, summary, sweep, and artifact questions.
- Use `get_run_history_tool` for curves and time series.
- Use `compare_runs_tool` for config differences, metric deltas, and aligned history.
- Use `diagnose_run_tool` for convergence, overfitting, and non-finite metric checks.

Do not rank runs with incompatible datasets, seeds, or metric definitions without stating the mismatch.

## Analyze Weave Traces

1. Call `infer_trace_schema_tool` first.
2. Use `count_weave_traces_tool` for counts that do not require payloads.
3. Use `query_weave_traces_tool` with `detail_level="summary"` for broad analysis.
4. Use `resolve_trace_roots_tool` to map child failures to root workflows.
5. Request `detail_level="full"` only for a small set of selected traces.

## Analyze Evaluations

Start with `summarize_evaluation_tool` for scorer pass rates, error counts, and task-level weaknesses. Use raw trace queries only to explain representative failures or inspect fields omitted from the aggregate.

## Analyze Artifacts And Registry

- Use `list_registries_tool` and `list_registry_collections_tool` for discovery.
- Use `list_artifact_versions_tool` to enumerate versions.
- Use `get_artifact_details_tool` for lineage and file details.
- Use `compare_artifact_versions_tool` for explicit version diffs.

## Persist Findings

Only after an explicit request:

1. Use `log_analysis_to_wandb` when computed values need to become a W&B analysis run.
2. Use `create_wandb_report_tool` for a durable narrative with run or metric panels.

## Evidence Checklist

- State the entity/project and time range.
- Name the metric and whether higher or lower is better.
- Include ids or versions for important evidence.
- Report missing runs, incomplete histories, running evaluations, or schema ambiguity.
- Separate retrieved facts, calculations, and recommendations.
