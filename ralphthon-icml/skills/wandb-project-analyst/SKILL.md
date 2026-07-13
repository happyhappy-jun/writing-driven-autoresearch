---
name: wandb-project-analyst
description: Analyze live W&B Models and Weave project data using the W&B MCP server, including runs, histories, configs, traces, evaluations, artifacts, registries, comparisons, diagnoses, and reports. Use when the user asks what happened in a W&B project, which run or model is best, why a run or trace failed, how evaluations performed, what changed between versions, or to save an evidence-backed analysis as a W&B Report.
---

# W&B Project Analyst

Use W&B MCP as the primary interface for reading and analyzing data already stored in W&B. Ground conclusions in retrieved run, trace, evaluation, and artifact evidence.

## Operating Rules

- Identify the entity, project, time range, metric, and comparison target from the request or discover missing scope with MCP.
- Probe unfamiliar Models projects and infer unfamiliar Weave schemas before querying them.
- Use summary-level trace data for broad analysis and full trace payloads only for a small set of relevant traces.
- Prefer purpose-built history, comparison, diagnosis, and evaluation tools over manual broad queries.
- Distinguish observed facts from inferences and recommendations. Include run ids, trace ids, artifact versions, timestamps, or W&B links when available.
- Confirm full retrieval for broad rankings instead of assuming the newest page is complete.
- Do not persist an analysis run or create a W&B Report unless the user explicitly asks to save or publish the findings.
- Never request, print, or store the value of `WANDB_API_KEY`.
- Use the official `wandb-primary` skill when available for W&B SDK patterns or as a fallback when an MCP capability is unavailable.

## Workflow

1. Normalize the analytical question and target W&B project.
2. Verify MCP access. If the entity or project is unknown, discover it before proceeding.
3. Select the product surface:
   - Models runs: probe keys, then query runs, histories, comparisons, or diagnoses.
   - Weave traces: infer the schema, then count or query traces and resolve roots when needed.
   - Evaluations: use evaluation summaries before raw trace analysis.
   - Artifacts and Registry: list, inspect, and compare explicit versions.
4. Retrieve only the fields and time range needed to answer the question.
5. Compute or synthesize the answer, checking denominators, missing data, and baseline comparability.
6. Return evidence, caveats, and the next useful investigation.
7. If explicitly requested, log computed analysis values and create a W&B Report.

## Product Routing

For Models questions, prefer this sequence:

```text
probe project -> query runs or history -> compare or diagnose -> summarize
```

For Weave questions, prefer this sequence:

```text
infer schema -> count or query summary traces -> resolve roots -> inspect selected full traces
```

For evaluation questions, start with the evaluation summary and inspect raw traces only when the aggregate result is insufficient.

## References

- Read `references/mcp-analysis-workflows.md` for concrete W&B MCP tool chains, evidence rules, and setup fallback.

## Demo Prompts

Use a real accessible entity and project:

```text
Analyze the top five runs by eval/primary_score in ENTITY/PROJECT and compare their configs.
Find failed Weave traces in ENTITY/PROJECT from the last 24 hours and group the root workflows by failure mode.
Summarize the latest evaluation in ENTITY/PROJECT and identify the weakest scorer.
Compare artifact versions model:v2 and model:v3 and explain what changed.
```

## Response Shape

Lead with the answer, then list supporting evidence, caveats or missing data, and recommended next action. Include a W&B Report link only when a report was explicitly requested and successfully created.
