# Weave Tracing Codebase Analysis

Use this guide before modifying an existing application.

## 1. Detect Existing Integration

Search for:

```text
import weave
weave.init(
@weave.op
weave.op(
```

Classify the task:

- **Fresh**: no Weave setup exists. Identify one application boundary for initialization.
- **Evolve**: Weave already exists. Reuse the current project and initialization unless it is demonstrably wrong.

In an Evolve task, report what is already traced before proposing additions. Never add a second `weave.init()` merely because the integration is incomplete.

## 2. Discover the Application Shape

Inspect source files and identify:

- Runtime entrypoints and long-lived server startup.
- Agent or workflow orchestration functions.
- LLM provider SDK calls.
- Agent tools and external APIs.
- Retrieval, parsing, and context-selection functions.
- Retry, fallback, branching, callback, and post-processing logic.
- Existing tests and the smallest representative run command.

Do not inventory every utility for its own sake. Follow call paths that contribute to model or agent behavior.

## 3. Check Automatic Integrations

Use current official Weave documentation to determine which provider or framework calls are auto-patched after `weave.init()`.

For each wrapper around an auto-patched call:

- Only delegates to the traced SDK call: leave it unwrapped.
- Adds branching, retries, aggregation, or user-visible semantics: consider a custom Op.
- Receives non-serializable framework objects: do not decorate it unless inputs can be safely transformed.

The goal is a readable hierarchy, not two spans representing the same work.

## 4. Check Serialization and Privacy

Before recommending `@weave.op()`, inspect parameters and return values for:

- SDK clients, response streams, file handles, database sessions, and framework state.
- Large documents, images, binary payloads, or full retrieval corpora.
- Credentials, personal information, private notes, and unpublished content.

Prefer a safe application-owned boundary with primitive or structured inputs. Use IDs, hashes, short summaries, or references when full values are unnecessary.

## 5. Produce the Trace Map

For each proposed boundary, record:

| Field | Meaning |
|---|---|
| File and symbol | Exact patch location |
| Role | Root workflow, retrieval, tool, synthesis, or other decision |
| Capture mode | Custom Op or automatic integration |
| Parent | Expected parent Call |
| Risk | Privacy, payload size, serialization, or call frequency |
| Decision | Add, keep existing, or intentionally skip |

Example:

```text
- add: `agent.py:run_agent()` - root workflow Op
  - automatic: OpenAI model call - already auto-patched
  - add: `tools.py:search_papers()` - external tool Op
- skip: `formatting.py:clean_text()` - pure utility
- skip: `agent.py:call_model()` - thin wrapper around auto-patched call
```

## 6. Recheck After the Patch

Compare the actual trace with the map. A mismatch usually means one of these:

- Initialization happens after the first call.
- A selected function is not reached by the smoke task.
- Parent context is lost across a thread, process, or callback boundary.
- An automatic integration was not enabled for the installed version.
- A custom Op failed to serialize its input or output.
- The same provider call is represented by both automatic and manual tracing.
