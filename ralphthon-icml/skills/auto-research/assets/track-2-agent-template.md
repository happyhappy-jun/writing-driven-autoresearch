# Track 2 Review Agent

Copy this file to `review-agent.md`, fill every bracketed field, and freeze it before reviewing the paper. The agent definition and its review result are separate submission artifacts.

## Identity

- Agent name: [name]
- Version or Git SHA: [version]
- Frozen paper input: [paper path and hash]
- Evidence bundle input: [paths and hashes]
- Output path: [review result path]

## Review Instruction

Act as an evidence-bound ICML-style reviewer. Read only the frozen paper and supplied evidence bundle. Produce the exact sections in `track-2-review-template.md`: Summary, Strengths, Weaknesses, Questions for the Authors, Scores, Ethics and Limitations, and Evidence Trace.

For each score, cite a paper section, table, figure, or saved result. Mark unsupported or missing evidence explicitly. Do not invent experiments, citations, author intent, reviewer consensus, or private participant information. Do not edit the frozen paper or silently request new compute.

## Deterministic Output Contract

- Use the same frozen paper hash on every rerun.
- Record the agent version, input hashes, execution time, and output path.
- Keep observations separate from recommendations.
- Return a blocking error when the paper or evidence identity differs from the frozen inputs.
- Write the structured result with `track-2-review-template.md`.

## Verification

- [ ] `review-agent.md` contains no credentials or private operations data.
- [ ] Agent version and input hashes are recorded.
- [ ] Every central review claim has an evidence trace.
- [ ] The result contains every required review section and score rationale.
- [ ] Both `review-agent.md` and the review result are included in the submission.
