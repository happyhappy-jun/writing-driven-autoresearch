# Weave Trace Patterns

## Boundary Selection

Trace a function when it represents a meaningful workflow step and its input or output helps explain quality, failure, latency, or cost.

Good boundaries:

- Application entrypoints such as `run_agent`, `answer_question`, or `review_paper`.
- Retrieval, paper search, document reading, and context selection.
- Agent tools and external side effects.
- Branching, retry, fallback, validation, or result synthesis.
- Model calls not already captured by automatic integration.

Usually skip:

- Thin wrappers around auto-patched provider or framework calls.
- Pure formatting, getters, setters, and constant lookup.
- Token-level or very high-frequency loops.
- Functions that accept framework clients, streams, database sessions, or other non-serializable objects.
- Functions whose raw inputs would expose unnecessary sensitive content.

## Operation Names

Use stable names that describe product or research behavior:

- `run_research_agent`
- `plan_experiment`
- `search_papers`
- `retrieve_context`
- `compare_runs`
- `execute_tool`
- `draft_review`
- `validate_claims`
- `synthesize_result`

Avoid names coupled to temporary implementation details such as `helper_v2`, `process_data`, or a specific line number.

## Compact Context

Useful fields include:

- `workflow`
- `task_id`
- `app_version` or git SHA
- `prompt_version`
- `model`
- `run_id`
- `dataset_id`
- `retrieval_depth`
- `artifact_ref`
- `privacy`

Prefer IDs, hashes, URLs, short summaries, and artifact references over full documents or large payloads.

## Privacy Guardrails

- Never trace API keys, bearer tokens, cookies, passwords, or connection strings.
- Redact email addresses, private identities, and user-provided secrets when they are not required for debugging.
- Do not log unpublished papers, proprietary notes, or full retrieved documents unless policy explicitly permits it.
- Inspect nested tool arguments and results, not only top-level agent inputs.
- When content capture is unsafe, record structure, identifiers, usage, timing, and error categories instead.

## Trace Review

A useful trace should answer:

1. What user or research task started this execution?
2. Which model, retrieval, and tool Calls ran, and in what order?
3. What input caused each decision?
4. Where did an error, delay, or incorrect value first appear?
5. What final output or artifact did the workflow produce?

Before calling the integration complete, verify:

- A representative task creates one expected root Call.
- The root has the expected child Calls and no obvious duplicates.
- Model usage, tool arguments, outputs, latency, and errors are inspectable where relevant.
- Operation names remain meaningful across different inputs.
- Inputs and outputs contain no credentials or unnecessary private content.
- Existing tests and user-visible behavior remain unchanged.
