---
name: weave-add-tracing
description: Add W&B Weave tracing to an existing LLM, agent, RAG, or tool-using application with minimal behavioral change. Use when the user asks to integrate Weave, instrument code with @weave.op, trace model or tool calls, choose trace boundaries, account for framework auto-patching, protect sensitive trace data, debug missing traces, or verify a real trace tree. Keep this skill focused on tracing; route evaluations, assets, and general W&B documentation elsewhere.
---

# Add W&B Weave Tracing

Instrument an existing AI application, run a representative task, and verify that the resulting Weave trace explains the application's behavior. Preserve the application design unless the user explicitly requests a refactor.

## Operating Rules

- Verify current SDK and integration behavior with official W&B Weave documentation before relying on exact APIs or auto-patching claims.
- Add observability without changing prompts, control flow, retries, tool behavior, or user-visible output.
- Initialize Weave once at the application boundary. Reuse an existing valid `weave.init()` call.
- Prefer a small trace tree of meaningful workflow, model, retrieval, and tool boundaries over decorating every helper.
- Do not duplicate calls already captured by a supported provider or framework integration.
- Trace only serializable inputs and outputs. Summarize or reference large objects and documents.
- Never send credentials, access tokens, private notes, unpublished documents, or unnecessary personal data to Weave.
- Do not introduce `weave.Model`, datasets, assets, scorers, or evaluations unless the user separately requests them.

## Workflow

### 1. Preflight

1. Detect the project language, package manager, entrypoint, and normal test or run command.
2. Search for existing Weave setup and classify the task:
   - **Fresh**: no Weave integration exists.
   - **Evolve**: `weave.init()`, `@weave.op`, or framework tracing already exists.
3. Identify model providers, agent frameworks, tools, retrieval, callbacks, retries, and async boundaries.
4. Confirm the target Weave project from existing configuration or `team/project`. Do not put credentials in source code.
5. Read `references/codebase-analysis.md` for a repository-wide integration scan.

### 2. Build a Compact Trace Map

Present the proposed root and child Calls before editing. Include file, symbol, reason, and capture behavior.

```text
run_agent()                         root workflow Op
|- provider model call             automatic integration
|- retrieve_context()              custom Op
`- execute_tool()                  custom Op
```

Recommend an Op when its inputs and outputs help answer at least one question:

- What decision did the application make?
- Which model, retrieval, or tool step failed?
- Where did latency or an incorrect value first appear?
- Which step produced the user-visible result?

Do not create a plan file unless the user asks for one. When the user has requested implementation, continue after presenting the compact map without adding mandatory approval gates.

### 3. Apply Minimal Instrumentation

1. Add the dependency using the repository's existing package manager.
2. Place or reuse one `weave.init()` call before traced work begins.
3. Preserve supported automatic provider or framework tracing.
4. Add `@weave.op()` only to selected application-owned functions.
5. Keep Op names stable and inputs and outputs compact and serializable.
6. Add redaction, summaries, IDs, hashes, or references when raw content is too sensitive or large.

For Fresh vs Evolve rules, auto-patched wrappers, and unsafe inputs, follow `references/codebase-analysis.md`. For operation names, privacy, and granularity, follow `references/trace-patterns.md`.

### 4. Validate End to End

1. Run formatting, static checks, and focused tests appropriate to the changed files.
2. Run one representative smoke task when credentials and network access permit.
3. Open the emitted Weave URL and verify:
   - one expected root Call;
   - expected model, retrieval, and tool children;
   - useful inputs, outputs, latency, usage, and error state;
   - no duplicate spans from wrapping auto-patched calls;
   - no secrets or unnecessary private content.
4. If a live run is not possible, provide the exact command and expected trace tree. Do not claim that UI verification happened.
5. Remove noisy Ops or add a missing decision boundary based on the observed trace.

## Hands-on

Use [`assets/handson_weave.ipynb`](assets/handson_weave.ipynb) when the user asks for a guided introduction rather than integration into an existing codebase.

- Part 1: create and inspect a deterministic nested trace.
- Part 2: inspect one simple tool-calling agent trace.
- Optional Claude Code integration: explain content capture and get confirmation before changing hooks or credentials.

## References

- Read `references/codebase-analysis.md` before scanning or patching an application.
- Read `references/trace-patterns.md` when selecting boundaries, naming Ops, or reviewing privacy and noise.
- Workflow informed by the official [wandb/weave-integration-skills](https://github.com/wandb/weave-integration-skills) repository, narrowed here to tracing-only hackathon workflows.

## Response Shape

Return:

1. The compact proposed or implemented trace tree.
2. Changed files and instrumentation points.
3. Auto-patched calls intentionally left unwrapped.
4. Privacy or serialization risks.
5. Validation performed and expected Weave UI behavior.
