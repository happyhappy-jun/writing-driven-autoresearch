# World-Model Evaluation and Claim Guardrails

Use this reference to select one focused research pattern. Keep experiment execution and evidence records in `auto-research` after the handoff.

## Candidate Scoring Rubric

Score each dimension 0, 1, or 2. Keep the scores and a short reason for every rejected candidate.

| Dimension | 0 — reject or reframe | 1 — risky | 2 — viable |
| --- | --- | --- | --- |
| World-model necessity | A scripted demo or static predictor answers the question. | Dynamics help, but the target is vague. | Future state, rollout, planning, or intervention is central. |
| Intervention identifiability | Action is absent, ambiguous, or after the target. | Action is observed but weakly linked or poorly timed. | Action timing and its path to the target are explicit. |
| Falsifiability | No named failure condition. | Metric exists but no threshold or disconfirming case. | Baseline, metric, threshold, and disconfirming outcome are fixed. |
| Fair-baseline feasibility | Baseline needs different data or privileged inputs. | Matching budget is uncertain. | Observation scope, target horizon, data, and budget can match. |
| Deadline fit | The smallest comparison cannot be run. | A smoke test is possible but risky. | A minimum comparison fits the available time. |

Reject a candidate with a zero in intervention identifiability, falsifiability, or fair-baseline feasibility. Prefer the highest total among viable candidates; use deadline fit to break a tie.

## Candidate Research Patterns

### Action-conditioned state prediction

- Question: Does conditioning on an intervention improve next-state or multi-step prediction?
- Baseline: same model without the action/intervention input, with observations, target, data, and budget matched.
- Metrics: next-state error, rollout error by horizon, calibration, or constraint violations.
- Minimum check: swap known actions for identical states; aligned predictions should beat permuted-action predictions.

### Planning with a learned model

- Question: Does model-based lookahead improve task success under the same interaction budget?
- Baseline: reactive or model-free policy with matched interactions, observations, and practical compute.
- Metrics: task success, regret, unsafe states, planning latency, or sample efficiency.
- Minimum check: use a small environment with a known optimal action sequence.

### Representation for downstream control

- Question: Do learned latent dynamics retain information needed for control or forecasting?
- Baseline: static encoder or reconstruction-only representation with matched latent size, data, and probe budget.
- Metrics: downstream task score, probe performance, or robustness under shift.
- Minimum check: test whether a probe separates a small known control-relevant distinction.

### Counterfactual intervention modeling

- Question: Can the model distinguish outcomes caused by different actions from the same initial state?
- Baseline: observational predictor or scripted heuristic with the same allowed task inputs.
- Metrics: intervention ranking, counterfactual error, consistency, or false causal conclusions.
- Minimum check: use matched initial states with different interventions, randomized interventions, or a documented causal identification strategy.
- Claim limit: observational trajectories alone support action-conditioned prediction, not causal or counterfactual conclusions.

## Handoff Checklist

- State the state, observation, action, target, hypothesis, baseline, metric, threshold, and smallest comparison.
- Match baseline inputs, data, target horizon, and practical budget.
- Name one relevant smoke test: known transition, action alignment, or split/leakage.
- Name shortcut learning, rollout/state-transition, distribution shift, or baseline fairness as a likely failure mode.
- Keep results, raw outputs, and detailed evidence tracking for `auto-research`.

## Public Claim Policy

Do not infer relationships from internal planning notes or draft partner language. For Dalpha or any partner, use only approved public copy. Until verified, treat award category, judging criteria, prize, product relationship, and world-model endorsement as unconfirmed. Exclude private participant/reviewer data, messaging links, raw conversations, tokens, and operational ledgers.

## Track Conversion

- General Track 1: hand the selected spec to Auto Research; it owns the evidence bundle, paper, and self-review.
- Training Track 1: use Auto Research's bounded Karpathy path only for new Karpathy training evidence and follow its separate cost, compute, and observability gates.
- Track 2: freeze the Track 1 paper before reviewing soundness, baseline fairness, metric validity, limitations, and evidence trace.
