# Depth-AR: Iterative 3-Hour Research and Writing Plan

## 0. Paper decision

### Primary title

**Depth-AR: Skipping Transformer Layers Without Dropping Their Updates**

This title is deliberately assertive. It communicates the central benefit without claiming that the skipped update is reconstructed exactly.

Alternative titles:

- **Transformer Depth Has Momentum: Predicting the Updates of Skipped Layers**
- **Don't Drop the Update: Depth-Wise Extrapolation for Efficient Transformers**
- **Depth-AR: Predictable Computation Beyond Layer Skipping**

### Research question

> **How much of a skipped Transformer block's residual update is predictable from the immediately preceding depth trajectory, and can this predictable component be recovered at negligible cost?**

### One-sentence paper message

> **A substantial fraction of the computation discarded by layer skipping is predictable from recent residual updates; Depth-AR exploits this depth-wise momentum to preserve markedly more model quality than plain skipping using only one or two fitted scalars per skipped layer.**

This is intentionally stronger than a neutral description. It is acceptable as the paper's provisional message because it states the result we are actively testing, not an unsupported priority claim.

### Memorable framing

Use this repeatedly:

> **Plain layer skipping treats the missing update as zero. Depth-AR treats it as predictable.**

The paper is not primarily about selecting layers. It is about replacing the unnecessarily weak zero-update assumption.

---

## 1. Assertive but defensible writing policy

A hackathon paper should sound decisive. The exaggeration should come from **framing, contrast, and emphasis**, not invented facts.

### Strong language that is encouraged

- "Plain skipping throws away predictable computation."
- "Transformer depth exhibits local momentum."
- "Depth-AR converts depth redundancy into usable computation."
- "A one-scalar predictor recovers a surprisingly large share of the skipped transformation."
- "Depth-AR consistently dominates plain skipping at matched depth."
- "The zero-update assumption is unnecessarily destructive."
- "The preceding residual trajectory contains enough information to partially stand in for a skipped block."

### Claims that are acceptable after the corresponding experiment succeeds

- "Depth-AR establishes a stronger quality–depth frontier than plain layer deletion."
- "Residual predictability is a practical signal of extrapolative layer redundancy."
- "Even an extremely constrained autoregressive predictor captures functionally useful computation."
- "The effect persists from sub-billion-parameter models to a 7B model."

### Claims that require caution

Use "to our knowledge" in the related-work paragraph, not repeatedly throughout the paper:

> **To our knowledge, Depth-AR is the first layer-skipping method to model missing residual updates autoregressively from the preceding depth trajectory using a closed-form, scalar predictor.**

Do not claim:

- first activation-recovery method,
- first linear post-pruning correction,
- state of the art,
- lossless skipping,
- end-to-end generation speedup from prefill-only measurements,
- universal behavior across all architectures.

### Better way to overclaim safely

Prefer:

> "Depth-AR recovers most of the avoidable damage introduced by the zero-update assumption."

over:

> "Depth-AR reconstructs the skipped layer."

Prefer:

> "Depth-AR reveals that Transformer depth contains predictable local computation."

over:

> "Transformer layers are redundant."

Prefer:

> "Our results expose a strong and previously underused source of structure."

over:

> "No previous work has observed this structure."

---

## 2. Novelty positioning

Closest families of work already include:

- layer-importance-based pruning or skipping,
- magnitude compensation after pruning,
- linear activation alignment across removed regions,
- analysis of smooth or low-dimensional hidden-state trajectories.

The paper's narrow novelty is:

> **Depth-AR predicts a missing residual update directly from preceding residual updates, using a depth-wise autoregressive model whose fitted state is only one or two scalars per candidate layer.**

The key distinction is not merely "linear recovery." It is:

1. **source of information:** preceding update trajectory rather than only the boundary activation;
2. **inductive bias:** momentum across depth;
3. **cost:** \(O(Td)\) scaled vector additions rather than a dense \(O(Td^2)\) map;
4. **calibration:** closed-form scalar regression with no gradient training.

### High-level contrast sentence for the introduction

> Existing methods ask which blocks can be removed or how activations can be remapped after removal. We instead ask whether the missing computation is already forecast by the model's own recent trajectory.

---

## 3. Method

For a pre-norm Transformer,

\[
h_{\ell+1}=h_\ell+\Delta_\ell,
\qquad
\Delta_\ell=F_\ell(h_\ell).
\]

Plain skipping sets

\[
\widehat{\Delta}_\ell=0.
\]

Depth-AR replaces this zero-order assumption with a short autoregressive model across depth.

### Depth-AR(1)

\[
\widehat{\Delta}_\ell=\alpha_\ell\Delta_{\ell-1},
\qquad
\widehat{h}_{\ell+1}=h_\ell+\widehat{\Delta}_\ell.
\]

Fit

\[
\alpha_\ell^\star=
\frac{
\langle\Delta_{\ell-1},\Delta_\ell\rangle_F
}{
\|\Delta_{\ell-1}\|_F^2+\epsilon
}.
\]

### Depth-AR(2)

\[
\widehat{\Delta}_\ell
=
\alpha_\ell\Delta_{\ell-1}
+
\beta_\ell\Delta_{\ell-2}.
\]

Fit \((\alpha_\ell,\beta_\ell)\) through a \(2\times2\) ridge-regression system.

### Core baselines

1. **Plain Skip:** \(\widehat{\Delta}_\ell=0\)
2. **Copy Update:** \(\widehat{\Delta}_\ell=\Delta_{\ell-1}\)
3. **Depth-AR(1)**
4. **Depth-AR(2)**

The same skipped-layer set must be used for every method.

### Predictability score

\[
P_\ell=
1-
\frac{
\sum\|\Delta_\ell-\widehat{\Delta}_\ell\|_2^2
}{
\sum\|\Delta_\ell\|_2^2
}.
\]

\(P_\ell>0\) means the predictor explains more update energy than Plain Skip.

---

## 4. Research strategy: discovery funnel, not one-shot evaluation

The experiment plan has four stages:

1. **Discover the phenomenon on 0.5B.**
2. **Repair failure modes and select a winning variant on 0.5B.**
3. **Verify that the variant transfers to 1.5B.**
4. **Run only the winning method on 7B for the headline result.**

The expensive model is a confirmation experiment, not the development environment.

### Model ladder

| Stage | Default model | Purpose |
|---|---|---|
| Discovery | Qwen2.5-0.5B | Fast layer scans, debugging, and method search |
| Verification | Qwen2.5-1.5B | Check that the finding is not a tiny-model artifact |
| Headline scale | Qwen2.5-7B | Produce the main large-model result |
| Optional architecture check | Pythia-410M or Pythia-1.4B | Test whether the effect is family-specific |

Use models already cached locally whenever possible. Do not lose hackathon time to access approval or large downloads.

### Why this ladder

- The 0.5B model allows full layer sweeps and many variants in minutes.
- The 1.5B model is large enough to reject fragile toy-model effects.
- The 7B model makes the final claim compelling.
- Keeping the first three models in one family reduces implementation variance during method development.

---

## 5. Iteration ladder

## Round 0: correctness and dense baseline

### Goal

Verify that the wrapper is exact before testing the idea.

### Checks

1. Dense wrapper reproduces original logits.
2. AR with \(\alpha=0\) reproduces Plain Skip.
3. A manually skipped layer agrees with the generic skip implementation.
4. Residual updates are measured at the intended block boundary.
5. Padding tokens are excluded from coefficient fitting.
6. Selected layers are non-adjacent in the main setting.

### Time budget

10–15 minutes.

### Failure action

Do not proceed until the dense-wrapper discrepancy is within expected BF16 tolerance.

---

## Round 1: does depth-wise momentum exist?

### Model

Qwen2.5-0.5B.

### Cheap data

- 16 calibration sequences
- 16 held-out sequences
- Sequence length 512
- C4, WikiText-103 train, or any cached unlabeled corpus

### Experiments

For every eligible layer:

- fit AR(1);
- fit AR(2);
- compute held-out \(P_\ell\);
- compute cosine similarity between consecutive residual updates;
- measure normalized update magnitude;
- skip the layer individually on a small held-out LM set;
- compare Plain Skip and AR recovery.

### Gate A: phenomenon test

Proceed with scalar Depth-AR if at least one of these holds:

1. At least 25% of eligible layers have \(P_\ell>0.1\).
2. At least four layers recover over 20% of single-layer NLL damage.
3. AR(1) or AR(2) clearly beats Plain Skip for the best several layers.

The exact threshold is a research management rule, not a paper claim.

### If Gate A passes

Select the top 6–8 non-adjacent layers and enter Round 2.

### If Gate A fails

Do not immediately abandon the paper. Run the following variants in order.

#### Variant A: normalized directional extrapolation

Separate direction and magnitude:

\[
\widehat{\Delta}_\ell
=
s_\ell
\frac{\Delta_{\ell-1}}
{\|\Delta_{\ell-1}\|_2+\epsilon}.
\]

Fit only the target scale \(s_\ell\).

#### Variant B: residual-ratio predictor

Predict a scaled update relative to hidden-state norm:

\[
\widehat{\Delta}_\ell
=
\gamma_\ell
\frac{\|h_\ell\|_2}{\|\Delta_{\ell-1}\|_2+\epsilon}
\Delta_{\ell-1}.
\]

#### Variant C: per-channel scaling

Fit a diagonal vector \(a_\ell\in\mathbb{R}^d\):

\[
\widehat{\Delta}_\ell=a_\ell\odot\Delta_{\ell-1}.
\]

This is still cheap at inference and far smaller than a dense map.

#### Variant D: local window

Fit

\[
\widehat{\Delta}_\ell
=
\alpha_\ell\Delta_{\ell-1}
+
\beta_\ell\Delta_{\ell-2}
+
\gamma_\ell\Delta_{\ell-3}.
\]

#### Variant E: predict the post-skip correction instead of the full update

For a skipped layer \(\ell\), run a short calibration pass with that layer removed and fit a correction from the previous update to the downstream activation discrepancy.

This weakens the pure trajectory claim, so use it only if simpler variants fail.

### Gate A2

Choose the simplest variant that:

- beats Plain Skip on at least four single-layer tests, and
- improves mean NLL across the selected layers.

If no variant passes, pivot to the negative-result paper described later.

---

## Round 2: does the effect compose across several skipped layers?

### Model

Qwen2.5-0.5B.

### Budgets

- \(k=1\)
- \(k=2\)
- \(k=4\)
- \(k=6\), only if the smaller budgets work

### Layer-selection candidates

Run two selection methods:

1. **Predictability selection:** highest held-out \(P_\ell\), non-adjacent.
2. **Low-damage oracle-lite:** lowest single-layer NLL damage on the tiny development set.

The second is not a fair deployment method but is useful diagnostically. It separates a failure of update prediction from a failure of layer selection.

### Required comparisons

- Dense
- Plain Skip
- Copy Update
- Depth-AR(1)
- Depth-AR(2) or the winning Round-1 variant

### Gate B: composition test

A method survives if, at \(k=4\):

- it improves NLL over Plain Skip;
- it improves at least two of three small downstream task subsets;
- its advantage is not caused only by a different layer set.

### If predictability selection fails but oracle-lite works

The repair method works, but the selection signal is weak.

Actions:

1. Combine predictability and skip sensitivity:
   \[
   S_\ell=P_\ell-\lambda D_\ell
   \]
   where \(D_\ell\) is single-layer NLL damage.
2. Try ranking by directly measured AR recovery on the small development set.
3. Reframe the paper around **repairing a given pruning decision**, not proposing a new selection algorithm.

### If both selection rules fail

Inspect compounding error:

- Are skipped layers adjacent?
- Does a later skipped layer consume a predicted rather than real update?
- Does error grow after each skipped location?
- Does AR help the immediate hidden-state target but hurt later logits?

Repairs:

1. enforce at least one surviving layer between skipped blocks;
2. enforce at least two surviving layers;
3. reduce to \(k=2\);
4. fit coefficients under the actual multi-skip configuration;
5. use a confidence threshold and leave low-\(P_\ell\) layers unskipped.

### If AR(2) is unstable

Use AR(1) as the default. Simplicity is part of the contribution.

---

## Round 3: medium-scale verification

### Model

Qwen2.5-1.5B.

### Purpose

Reject methods that only exploit idiosyncrasies of the 0.5B model.

### Minimal run

- Refit coefficients from scratch.
- Run the layer profile.
- Test \(k=2\) and \(k=4\).
- Evaluate WikiText-2 NLL plus 200–500 examples from HellaSwag, PIQA, and ARC-Easy.
- Compare Dense, Plain Skip, Copy Update, and the winning Depth-AR variant.

### Gate C: transfer test

Scale to 7B if:

- Depth-AR improves NLL over Plain Skip at \(k=4\), and
- average downstream accuracy improves, or at least does not regress while NLL improves substantially.

If the effect weakens:

- select fewer layers;
- increase calibration from 16 to 32 sequences;
- compare family-normalized depth positions;
- check whether \(\alpha_\ell\) is close to zero in most layers;
- retain the strongest budget rather than forcing \(k=4\).

---

## Round 4: headline large-model confirmation

### Model

Qwen2.5-7B.

### Principle

Do not search broadly on 7B. Run the already selected method and only one backup.

### Mandatory configurations

- Dense
- Plain Skip
- Copy Update
- Best Depth-AR variant

At:

- \(k=2\)
- \(k=4\)

Add \(k=6\) only if \(k=4\) remains clearly competitive.

### Evaluation

- WikiText-2 NLL
- HellaSwag
- PIQA
- ARC-Easy
- Prefill latency at sequence lengths 512 and 2048

### Optional backup

If the 7B effect is weak, allow exactly one repair round:

- increase calibration to 64 sequences;
- reselect layers at 7B;
- compare AR(1) and AR(2).

Do not start an open-ended 7B hyperparameter search.

---

## 6. GPU allocation

### Two A100 80GB GPUs

#### First 45 minutes

- GPU 0: Qwen2.5-0.5B main scalar AR experiments.
- GPU 1: variant branch experiments and single-layer scans.

#### After Gate A

- GPU 0: multi-layer composition sweeps on 0.5B.
- GPU 1: begin 1.5B verification with the current best variant.

#### After Gate C

- GPU 0: 7B NLL and task evaluation.
- GPU 1: 7B alternative budget, latency, or remaining 1.5B confirmation.

### One A100 80GB GPU

Use the same gates sequentially.

Priority:

1. 0.5B discovery
2. 1.5B verification
3. 7B \(k=4\) headline result
4. 7B \(k=2\)
5. latency
6. extra tasks and ablations

---

## 7. Claims and validating experiments

Limit the final paper to three claims.

## Claim 1: Transformer depth contains predictable local computation

### Assertive claim sentence

> **Residual updates are not independent block outputs: across substantial portions of the network, they form a locally predictable trajectory.**

### Experiment

- Layer-wise held-out \(P_\ell\)
- Consecutive-update cosine similarity
- Single-layer Plain Skip damage
- Single-layer Depth-AR recovery
- Results on 0.5B, 1.5B, and 7B if available

### Strong success pattern

- broad positive predictability in middle layers;
- recovery rises with \(P_\ell\);
- similar qualitative depth profile across scales.

### Weaker but publishable pattern

Only a subset of layers is predictable.

Revised claim:

> **Transformer depth contains pockets of predictable computation that can be identified before skipping.**

---

## Claim 2: Plain skipping discards recoverable computation

### Assertive claim sentence

> **The conventional zero-update assumption leaves substantial quality on the table; even a one-scalar predictor recovers a large fraction of this avoidable loss.**

### Experiment

At identical layer sets:

- Plain Skip
- Copy Update
- Depth-AR(1)
- Depth-AR(2)

Metrics:

- NLL/perplexity
- HellaSwag
- PIQA
- ARC-Easy
- average accuracy
- gap recovery

For accuracy \(A\),

\[
\mathrm{Recovery}
=
\frac{
A_{\mathrm{AR}}-A_{\mathrm{Skip}}
}{
A_{\mathrm{Dense}}-A_{\mathrm{Skip}}
}.
\]

For NLL \(L\),

\[
\mathrm{Recovery}_{\mathrm{NLL}}
=
1-
\frac{
L_{\mathrm{AR}}-L_{\mathrm{Dense}}
}{
L_{\mathrm{Skip}}-L_{\mathrm{Dense}}
}.
\]

### Target headline

A strong paper can say:

> **Depth-AR recovers over half of the quality lost by plain skipping at the same effective depth.**

Only use the numerical fraction that the real experiment supports. "A substantial fraction" is safe if recovery is at least roughly 25–30%.

---

## Claim 3: The improvement survives scale while preserving the efficiency benefit

### Assertive claim sentence

> **Depth-AR improves the quality–depth frontier from 0.5B to 7B parameters while adding only \(O(Td)\) work and one or two scalars per skipped block.**

### Experiment

- Budget sweep on 0.5B and 1.5B
- \(k=2,4\) confirmation on 7B
- prefill latency on 7B
- parameter and operation count

If the effect does not transfer to 7B, replace the claim with:

> **Depth-wise predictability accurately forecasts when extrapolative skipping transfers across model scales.**

---

## 8. Data and evaluation

### Calibration

Discovery:

- 16 sequences
- length 512

Verification:

- 32 sequences
- length 1024

Final 7B:

- 32 sequences initially
- 64 only for the single allowed repair round

Use disjoint held-out sequences for layer scoring.

### Fast development metric

Use held-out language-model NLL on 16–32 sequences. This is the primary iteration metric because it is dense, stable, and cheap.

Do not run full downstream evaluation for every variant.

### Downstream task funnel

#### Development subset

- 100 examples each from HellaSwag, PIQA, and ARC-Easy

#### Medium verification

- 200–500 examples each

#### Final 7B result

- Full PIQA and ARC-Easy if fast enough
- 1,000 HellaSwag examples or full HellaSwag if already cached and configured

Use fixed example IDs and seed 42.

### Latency

- BF16
- FlashAttention 2
- `use_cache=False`
- batch size 8
- sequence lengths 512 and 2048
- 10 warm-up iterations
- 30 measured iterations
- CUDA synchronize around timing
- median and interquartile range

Call this **prefill latency**, not end-to-end generation latency.

---

## 9. Efficient fitting

Do not store all hidden states.

For AR(1), accumulate:

\[
A_\ell \mathrel{+}= \|\Delta_{\ell-1}\|_F^2,
\quad
B_\ell \mathrel{+}= \langle\Delta_{\ell-1},\Delta_\ell\rangle_F,
\quad
C_\ell \mathrel{+}= \|\Delta_\ell\|_F^2.
\]

Then:

\[
\alpha_\ell=B_\ell/(A_\ell+\epsilon).
\]

For AR(2), accumulate the five Gram and cross terms needed for the \(2\times2\) solve.

Use FP64 scalar accumulators. This makes recalibration cheap enough to repeat for each model and variant.

---

## 10. Run matrix by priority

## Tier 0: debugging

| Model | Runs |
|---|---|
| 0.5B | Dense equality, one manual skip, AR with \(\alpha=0\), one fitted layer |

## Tier 1: discovery

| Model | Budget | Methods | Data |
|---|---:|---|---|
| 0.5B | single-layer scan | Plain, Copy, AR1, AR2 | 16+16 LM sequences |
| 0.5B | \(k=1,2,4\) | Dense, Plain, Copy, best AR | LM + 100 examples/task |
| 0.5B | variant search | normalized, diagonal, AR3 as needed | LM only |

## Tier 2: verification

| Model | Budget | Methods | Data |
|---|---:|---|---|
| 1.5B | layer scan | Plain, AR1, best variant | 32+32 LM sequences |
| 1.5B | \(k=2,4\) | Dense, Plain, Copy, best AR | LM + 200–500 examples/task |

## Tier 3: headline

| Model | Budget | Methods | Data |
|---|---:|---|---|
| 7B | \(k=2,4\) | Dense, Plain, Copy, best AR | WikiText-2 + final task subsets |
| 7B | \(k=4\) | Dense, Plain, best AR | latency 512/2048 |

## Tier 4: optional

- Pythia architecture check
- \(k=6\)
- calibration-size ablation
- per-channel variant
- consecutive-skip stress test
- official implementation of one stronger recovery baseline

---

## 11. Failure-aware three-hour timeline

The timeline deliberately reserves time for failed rounds and method revision.

| Time | Research track | Writing track |
|---|---|---|
| 0:00–0:12 | Implement wrapper and correctness tests on 0.5B | Create ICML skeleton; write title, question, and provisional abstract |
| 0:12–0:30 | Fit AR1/AR2 and run first layer scan | Write introduction and method equations |
| 0:30–0:42 | **Gate A:** inspect predictability and single-layer recovery | Draft Figure 1 from provisional curves |
| 0:42–1:00 | If needed, test normalized/per-channel/local-window variants | Write related-work contrast and update method section |
| 1:00–1:18 | Run \(k=1,2,4\) composition tests on 0.5B | Write experiment setup and provisional main-result text |
| 1:18–1:30 | **Gate B:** diagnose selection versus composition failures | Revise storyline to match the winning variant |
| 1:30–1:55 | Run 1.5B verification; GPU 2 finishes 0.5B ablations | Populate real 0.5B table and Figure 1 |
| 1:55–2:05 | **Gate C:** decide whether and how to scale | Freeze method; remove losing variants from main text |
| 2:05–2:35 | Run 7B \(k=2,4\) headline evaluation | Populate provisional 7B values; finish four-page layout |
| 2:35–2:47 | One allowed 7B repair or latency run | Replace values and write exact findings |
| 2:47–3:00 | Reproduce key configuration; freeze all runs | Final figures, claim audit, page audit, compile |

### Hard rules

- Do not spend the first hour evaluating a 7B model.
- Do not run downstream tasks for a method that has not improved LM NLL.
- Do not test more than three repair variants before choosing or pivoting.
- At 2:05, freeze the method.
- At 2:35, no new scientific direction is allowed.
- A complete 1.5B result is better than an incomplete 7B sweep.

---

## 12. Writing storyline

### Background and limitation

1. Transformer inference repeatedly applies residual blocks, making depth a direct source of cost.
2. Layer skipping removes this cost efficiently but replaces an entire learned update with zero.

### Motivation

3. Consecutive residual updates often follow a smooth local trajectory across depth.
4. This suggests that a skipped update may be forecast from computation the model has already performed.

### Method

5. Depth-AR fits a one- or two-step autoregressive predictor over residual updates using a tiny unlabeled calibration set.

### Experimental claims

6. Layer-wise analysis shows that substantial regions of Transformer depth contain predictable updates.
7. At identical skipped layers, Depth-AR preserves markedly more LM and downstream quality than Plain Skip.
8. The advantage persists across model scales while retaining essentially the same block-compute reduction.

### Conclusion

9. Plain skipping unnecessarily discards predictable computation; modeling depth as a trajectory offers a nearly free way to recover it.

---

## 13. Introduction blueprint

### Paragraph 1: make the problem feel important

- Depth is expensive because every token traverses every block.
- Entire-block skipping is attractive because it removes real computation without changing hidden width or attention structure.
- Yet the usual skip operator is crude: it assumes the missing residual update is exactly zero.

Suggested closing sentence:

> **This zero-update assumption is computationally convenient but representationally wasteful.**

### Paragraph 2: identify the overlooked structure

- Layer-wise representations form trajectories rather than unrelated states.
- Existing pruning work mainly asks which blocks are removable.
- Existing recovery methods often use magnitude correction or richer boundary maps.
- Ask whether recent residual updates already forecast the next one.

Suggested closing sentence:

> **If Transformer depth has momentum, then plain skipping throws away computation that can be predicted almost for free.**

### Paragraph 3: introduce Depth-AR

- residual updates as a sequence across depth;
- AR1/AR2;
- closed-form unlabeled calibration;
- one or two scalars per layer;
- scaled vector-add overhead.

### Paragraph 4: contributions

Use assertive prose:

> We first show that residual updates contain strong local predictability across substantial portions of the network. We then introduce Depth-AR, which replaces a skipped block with an autoregressive forecast of its update. Across models from 0.5B to 7B parameters, Depth-AR consistently recovers quality discarded by plain skipping and establishes a stronger quality–depth trade-off at negligible additional cost.

Replace "across models from 0.5B to 7B" if the final evidence does not support it.

---

## 14. Figures and tables

## Figure 1: Transformer depth has predictable local momentum

Full-width, two panels.

### Panel A

- X-axis: normalized layer depth
- Y-axis: held-out explained update energy \(P_\ell\)
- curves for 0.5B, 1.5B, and 7B if available
- markers for selected layers

Finding-oriented title:

> **Residual predictability concentrates in the middle of the network**

### Panel B

- X-axis: \(P_\ell\)
- Y-axis: fraction of single-layer NLL damage recovered
- one point per layer
- Spearman correlation

Finding-oriented title:

> **Predictability forecasts successful layer replacement**

## Figure 2: Depth-AR improves the quality–depth frontier

- X-axis: fraction of skipped blocks
- Y-axis: average normalized downstream accuracy or NLL
- curves: Plain Skip and Depth-AR
- separate panels for 1.5B and 7B, or accuracy and NLL if only one large model succeeds

Finding-oriented title:

> **Predicting missing updates consistently dominates dropping them**

## Table 1: Main result

| Model | \(k/L\) | Method | WikiText NLL ↓ | HellaSwag ↑ | PIQA ↑ | ARC-E ↑ | Avg. ↑ | Gap recovered ↑ |
|---|---:|---|---:|---:|---:|---:|---:|---:|

Main-table models:

- 1.5B
- 7B

Put 0.5B development results in Figure 1 or the appendix unless they are unusually compelling.

Rows:

- Dense
- Plain Skip
- Copy Update
- Depth-AR

AR2 should be included only if it materially improves over AR1. Otherwise present AR1 as the clean final method.

---

## 15. Four-page allocation

| Content | Target |
|---|---:|
| Abstract | 0.20 page |
| Introduction | 0.75 page |
| Method | 0.75 page |
| Setup | 0.25 page |
| Figure 1 and analysis | 0.75 page |
| Table 1 and main comparison | 0.80 page |
| Figure 2 and scale/efficiency | 0.35 page |
| Conclusion and limitations | 0.15 page |

Related work belongs in the introduction.

Development variants, failed methods, full layer indices, and detailed task results belong in the appendix.

---

## 16. Writing before results

Use a complete, confident draft from the beginning.

### Invisible provisional-value macro

```tex
% First argument tracks provisional status; only the second is rendered.
\newcommand{\draftvalue}[2]{#2}
```

Example:

```tex
Depth-AR recovers
\draftvalue{pending:qwen7b-k4-gap-recovery}{54\%}
of the quality lost by plain skipping.
```

### Provisional narrative

Before results arrive, write:

> Depth-AR consistently improves over plain skipping at matched effective depth, recovering more than half of the lost quality at moderate skipping budgets.

This is a working paper statement, not a final factual report. The invisible key identifies the sentence for revision.

### Provisional result generation

After measuring the Dense baseline, populate plausible working numbers:

- Plain \(k=4\): Dense average accuracy minus 3–5 points.
- Depth-AR \(k=4\): Dense minus 1.5–3 points.
- Gap recovery: 40–60%.
- NLL degradation: Depth-AR roughly half of Plain Skip.
- Prefill latency: within 5% of Plain Skip and clearly faster than Dense.

Do not assign fake confidence intervals or p-values.

### Audit

```bash
grep -R "pending:" paper/
```

All `pending:` keys must be removed or converted to `final:` before submission.

---

## 17. Outcome-dependent paper pivots

## Pivot A: clean positive result

Main message:

> **Transformer depth has momentum, and Depth-AR converts it into a nearly free correction for layer skipping.**

Use the strongest 7B gap-recovery number in the abstract.

## Pivot B: scalar AR fails, diagonal scaling works

Rename the method only if necessary:

**Depth-AR-D: Diagonal Autoregressive Recovery for Skipped Transformer Layers**

Message:

> The next residual update is predictable channel by channel even when a global scalar is too restrictive.

This remains efficient at \(O(Td)\).

## Pivot C: update prediction works only for selected layers

Message:

> **Predictability exposes a new form of conditional layer redundancy.**

Reduce the budget sweep and emphasize layer diagnostics.

## Pivot D: tiny models work, 7B does not

Message:

> **Depth-wise momentum changes systematically with scale, and update predictability forecasts when extrapolative skipping succeeds.**

Use scale as the scientific finding rather than hiding it.

## Pivot E: hidden-state recovery improves but task accuracy does not

Message:

> **Geometric recovery is not equivalent to functional recovery.**

Compare:

- update MSE,
- next-layer hidden-state MSE,
- final-logit KL,
- downstream accuracy.

This becomes a cautionary analysis paper.

## Pivot F: no recovery variant beats Plain Skip

Negative paper title:

**Smooth but Indispensable: Why Predictable Transformer Updates Cannot Simply Be Skipped**

Main claim:

> Local trajectory smoothness substantially overestimates functional layer redundancy.

This can still be novel and coherent if Figure 1 shows weak relation between local predictability and downstream damage.

---

## 18. Minimum viable final paper

The paper is complete if it has:

1. A working 0.5B layer scan.
2. A verified 1.5B result.
3. At least one 7B matched-budget comparison, or a clearly stated scale-dependent negative result.
4. One winning Depth-AR variant.
5. WikiText-2 plus three task subsets.
6. Figure 1: layer-wise predictability and recovery.
7. Figure 2: quality–depth frontier.
8. Table 1: matched-layer comparison.
9. A strong framing claim that Plain Skip discards predictable computation.
10. A precise novelty statement restricted to depth-autoregressive residual prediction.
11. A four-page, compiling ICML paper with no visible provisional language.

A broad but shallow sweep is not required. A sharply analyzed, reproducible result on 0.5B, 1.5B, and one 7B configuration is the preferred outcome.
