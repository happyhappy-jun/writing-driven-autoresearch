---
name: world-model-ideation
description: Turn a world-model, 월드모델, simulation, predictive-state, embodied-agent, or intervention-model idea into ranked falsifiable research questions and a compact experiment handoff. Use when selecting a world-model research direction, deciding whether an idea needs a world model, defining an action-conditioned or counterfactual comparison, or preparing Ralphthon work for Auto Research Track 1 or Track 2.
---

# World Model Ideation

## Overview

Turn a demo concept into a research question, fair comparison, and smallest useful experiment before designing a polished interface. This skill selects and frames the work; `auto-research` owns evidence management, execution, and submission artifacts.

Read [the evaluation patterns and claim guardrails](references/evaluation-and-claims.md) before ranking candidates. Copy [the research-spec template](assets/research-spec-template.md) into the participant workspace as the handoff to `auto-research`.

## Preflight

Identify the environment, observations, actions or interventions, future target, available data and time, intended Track, and external claims requiring public verification.

If action is unavailable, unobserved, or cannot plausibly change the target, do not call the work action-conditioned or counterfactual. Reframe it as forecasting or representation learning, or reject it as a world-model candidate.

## Workflow

### Candidate Gate

Generate three research questions, not product slogans. Score each from 0–2 for world-model necessity, intervention identifiability, falsifiability, fair-baseline feasibility, and deadline fit using the reference rubric. Reject a candidate with no observable state/action/target path, no disconfirming outcome, or no fair baseline.

Select the highest-scoring viable candidate and state why the others lost. Do not use a visual simulation, generic predictor, or prompt-only demo as proof of a world model.

### Research Handoff

Choose one research pattern from the reference: action-conditioned state prediction, planning with a learned model, representation for downstream control, or counterfactual intervention modeling. Complete `research-spec.md` with:

1. state, observation, action/intervention, target horizon, and why the question needs a world model;
2. falsifiable hypothesis, named baseline, primary **evaluation metric**, success threshold, and claim limit;
3. smallest end-to-end comparison, split or sampling rule, and one appropriate smoke test;
4. likely failure modes and the intended General Track 1, Training Track 1, or Track 2 route.

Keep the handoff concise. Do not turn it into an experiment ledger or a paper; `auto-research` expands it only after a direction is selected.

### Minimum Experiment

Match the proposed model and baseline on observation scope, target horizon, data, and practical budget. Recommend the smallest check that could disprove the hypothesis:

- **Known transition:** verify the metric on a tiny deterministic state/action/next-state case.
- **Action alignment:** swap or permute actions for matched states and check that an action-dependent target changes.
- **Split and leakage:** ensure trajectories, entities, or time windows do not cross the declared split boundary.

Name the relevant check in the handoff. Do not make counterfactual claims without matched interventions or a defensible intervention design.

### Track Routing

- **General Track 1:** send the compact research spec to `auto-research` for the workflow, 2–4 page paper, self-review, and evidence handling. This is the default for a non-Karpathy world-model experiment.
- **Training Track 1:** use `auto-research`'s Training path only when new bounded Karpathy training evidence is actually required; complete its W&B and VESSL gates separately.
- **Track 2:** freeze a completed Track 1 paper first, then use `auto-research`'s Track 2-only path.

## Public-Claim Guardrail

**Do not claim** that Dalpha sponsors world-model research, uses world models, requires the topic, endorses the direction, or judges it unless approved public material says so. The Dalpha special-award category, criteria, and final wording are **unconfirmed**; do not invent a prize, benefit, relationship, or product capability.

World Model is an ideation theme, not a third Ralphthon Track. Keep sponsor or partner narrative separate from the scientific claim and mark proposed copy as draft.

## Verification

- Check that the selected question has a state/action/target path, disconfirming outcome, named baseline, evaluation metric, and minimum experiment.
- Check baseline fairness, action timing, claim limit, and at least one representative failure mode.
- Hand off experiment records, raw outputs, and observed versus planned evidence to `auto-research`; do not present planned work as a result.
- Remove unverified sponsor, award, partner, product, or endorsement statements from public output.

## Output

Return the ranked three-candidate scorecard, selected research pattern, compact research spec, recommended minimum check, Track route, likely failure modes, blockers, and external claims still requiring verification.

## Next Steps

- Direction selected: continue with `auto-research`'s General Track 1 path.
- New Karpathy evidence required: continue with `auto-research`'s Training path and its separate onboarding gates.
- Frozen Track 1 paper ready: continue with `auto-research`'s Track 2-only path.

## Common Mistakes

- Beautiful simulation with no intervention test → add an action-conditioned comparison or reframe it as a demo.
- Counterfactual wording from observational data → narrow the claim to prediction unless the intervention design supports it.
- Accuracy only → choose calibration, rollout error, consistency, constraint violation, or task success as appropriate.
- One successful anecdote → define a comparison and failure mode before execution.
- Sponsor-led premise → remove the brand assumption and verify public facts separately.
