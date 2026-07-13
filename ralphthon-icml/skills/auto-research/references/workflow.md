# Ralphthon Auto Research Workflow

## Public Event Frame

- Track 1 — AI Scientist: build an agent that produces a 2–4 page workshop-style short paper. The paper and underlying workflow may both be evaluated.
- Track 2 — Review Agent: build an agent that returns an ICML-style structured review of a Track 1 paper.
- Participants may enter Track 1, Track 2, or both.
- Research specification: 11:00–12:30.
- Ralph Loop: 12:30–15:30.
- Human editing and final paper/agent submission: 15:30–16:30.
- The 16:30 hard cut applies to the final paper/agent submission; peer and self-review follow.

Do not add private attendee, reviewer, messaging, or operations data to research artifacts.

## Research Spec

Freeze these fields before implementation:

1. Question and falsifiable hypothesis.
2. Intervention or system being tested.
3. Baseline and why it is fair.
4. Primary evaluation metric and success threshold.
5. Dataset/task and sampling rule.
6. Compute/API/time budget.
7. Reproducibility inputs: seed, version, prompt/config, environment.
8. Stop condition and fallback scope.
9. Known failure modes and safety/privacy constraints.

## Evidence Contract

- Save raw outputs before aggregation.
- Record failed runs and exclusions with reasons.
- Derive tables and headline values from one frozen result set.
- Distinguish exploratory findings from confirmatory results.
- Use “we observe” for small or inconclusive samples; do not claim robustness or generality without evidence.
- Include negative results when they change the conclusion.
- Verify every citation and never invent bibliographic details.

## Track 1 Self-Review

Check problem clarity, reproducibility, baseline fairness, metric validity, evidence-to-claim alignment, limitations, and page count. Return blocking corrections before stylistic edits.

## Track 2 Review Shape

Freeze and submit the Track 2 Review Agent definition separately from its result. Record the agent version and frozen paper/evidence hashes. The result must return Summary, Strengths, Weaknesses, Questions, Soundness, Presentation, Contribution, Overall Recommendation, Confidence, Ethics/Limitations, and Evidence Trace. Explain every score from the submitted paper.
