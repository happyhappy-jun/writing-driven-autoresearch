# Pivot drafts — SCRATCH, outside the build

Not `\input` anywhere. Nothing here renders. `section/` is **frozen** until master's A2
call. Everything below is paste-ready.

**Every number is READ FROM `~/ralph/results/*.json`.** Speculative values carry `\ph{}`.

---

# ★ BLOCK B′ — per-channel is the DEFAULT, no rename (master's A2-likely path)

`\mname` stays **Depth-AR**. The per-channel diagonal becomes the method; scalar AR(1)
demotes to the ablation that *explains why per-channel is necessary*.

Teaser numbers (master, pending T+0:45 confirmation — keep `\ph{}` until the JSON lands):
L1 recovery `\ph{+0.612}` per-channel vs `+0.112` scalar (scalar value is real, from R1);
L3 rescued from `-0.825` (real) to `\ph{+0.052}`.

## ☠️ THE MECHANISM SENTENCE IS DEAD — DO NOT WRITE IT

I hypothesised: *"channels disagree in sign, so they cancel in the scalar fit."*
**The data refutes this.** Verified by reading `diag_channel_stats_0.5b.json` directly:

| | Measured (layers 4–16) |
|---|---|
| `frac_channels_positive` (mean) | **0.117** → ~**88% of channels are NEGATIVE** |
| `median(a_ℓ)` (mean) | **−0.194** |
| scalar `alpha_ar1` | **−0.18 … −0.23** — sits essentially **ON** the channel median |

The channels **agree** in sign. The scalar is a **faithful summary** of them, not a
cancellation artifact. `r1_analysis_0.5b.json` records this explicitly:
`.mechanism_pivot_b.channels_agree_in_sign = true`.

> ### 🚩 LANDMINE IN THE RESULTS FILE — flagged to master
> The `notes` field of `diag_channel_stats_0.5b.json` still asserts the **opposite**:
> *"…the channel population is sign-heterogeneous and the scalar is a cancellation
> artifact, NOT a description of most channels."* That is a **stale hypothesis, refuted
> by the very file it is attached to.** Anyone drafting prose from that note will write a
> false mechanism into the paper. **Trust `.mechanism_pivot_b`, not `.notes`.**

Master's own competing mechanism guess is *also* unsupported:
`spearman(|alpha − median(a_ℓ)|, diag advantage) = +0.016, p = 0.94` — the scalar's
divergence from the channel population does **not** predict where the diagonal wins.

## ✅ What IS now a measured fact — write this

The sentence I was about to cut is the **correct** one, and it is now backed at two
independent levels:

> **Successive blocks in the middle of the network partially undo one another.**
> Not only is every fitted scalar negative through layers 4–16 (13/13), but ~88% of the
> *individual channels* carry a negative coefficient, with a median of −0.194. The
> anti-correlation is a property of the update population, not an artifact of summarising
> it with one number.

And symmetrically, momentum is **late**: `frac_channels_positive` climbs from 0.12 in the
middle to **0.63–0.67** at layers 20–21, where `median(a_ℓ)` finally turns positive.
The depth profile is a genuine sign flip, measured channel-wise.

## ⛔ MECHANISM FOR THE DIAGONAL'S WIN: OPEN. DO NOT ASSERT ONE.

Two candidate mechanisms have now been tested and **both failed** (mine, master's). We can
say **what** happens — per-channel beats scalar; depth anti-correlates mid-stack; momentum
is late — but we have **not established why** per-channel wins. The paper states the effect
and leaves the mechanism open. Writing a third untested guess would be exactly the failure
the first two just avoided.

*Permitted:* layer 4 as an **illustrative single case** — the energy-weighted scalar
collapses to $\alpha = -0.001$ while ~82% of its channels agree on a clearly negative
coefficient (median $-0.174$). Present as a worked example of *how* scalar and channel
views can come apart, explicitly **not** as the general mechanism (the Spearman above
says it does not generalise).

## Contribution block (drop-in for `introduction.tex` ¶7)

> We introduce \textbf{\mname (Depth-wise AutoRegressive update prediction)}, which
> replaces the zero-update assumption with a closed-form autoregressive forecast of the
> missing residual update, fitted per channel on unlabeled text with no gradient
> training. \mname contributes three results. (1) **The zero-update assumption is
> unnecessarily destructive**: a skipped block's residual update is substantially
> predictable from the preceding depth trajectory, and predicting it recovers
> `\ph{X}`\% of the quality plain skipping discards at $k=4$. (2) **The predictor must be
> per-channel.** A single global scalar --- the obvious first instantiation --- fails
> almost everywhere, and at some layers it is actively harmful: at layer 3 of
> Qwen2.5-0.5B, substituting the scalar prediction is markedly *worse than dropping the
> update outright* (recovery $-0.83$), while the per-channel predictor repairs the same
> layer. Granting the predictor one coefficient per channel --- and relaxing nothing else
> --- is what separates a method that works from one that does not. (3) **Depth is
> anti-correlated before it is autoregressive, and predictability is not
> recoverability.** Through the middle of the network, successive blocks partially undo
> one another: every fitted scalar coefficient is negative across layers 4--16, and
> $\ph{88}\%$ of individual channels carry a negative coefficient. Positive depth-wise
> momentum appears only in the final quarter of the stack. And held-out explained update
> energy $P_\ell$ --- the natural, cheap layer-selection signal --- is uncorrelated with
> the damage a predictor actually repairs (Spearman $-0.015$, $p=0.95$, $n=22$):
> geometric fidelity in residual space is not functional preservation, so layer selection
> must be validated against recovery, not against predictability.

Finding (3) **survives Pivot B intact** and is worth keeping: it is the honest, hard-won
negative result inside a positive paper, and it is what stops a reviewer asking "why not
just rank by $P_\ell$?".

**Note on (2):** it says *that* per-channel is necessary, never *why*. Both mechanisms we
tested failed (see above). Do not let a "because…" clause creep back into this sentence
during editing — it is the single most likely place for an unmeasured claim to re-enter.

## Method paragraph (drop-in, replaces `\paragraph{\mname: autoregression across depth.}`)

> \paragraph{\mname: per-channel autoregression across depth.} We model the update
> sequence as autoregressive in depth, with one coefficient per channel. Writing
> $\bm{a}_\ell \in \mathbb{R}^{d}$ for the fitted coefficient vector,
> \begin{equation}
> \widehat{\dd}_\ell = \bm{a}_\ell \odot \dd_{\ell-1},
> \qquad
> \widehat{\hh}_{\ell+1} = \hh_\ell + \bm{a}_\ell \odot \dd_{\ell-1},
> \end{equation}
> where $\odot$ is the elementwise product broadcast over the $T$ token positions. Each
> channel $j$ has a closed-form least-squares solution, computed independently:
> \begin{equation}
> a_{\ell,j}^{\star} =
> \frac{\sum_t \Delta_{\ell-1,tj}\,\Delta_{\ell,tj}}
>      {\sum_t \Delta_{\ell-1,tj}^{2} + \epsilon}.
> \end{equation}
> The fitted state is $d$ scalars per skipped block --- $896$ on Qwen2.5-0.5B --- against
> the $d^2 \approx 8\times10^5$ of a dense boundary map, and inference cost stays at
> $O(Td)$: one elementwise multiply and one add, on a tensor already resident in the
> residual stream. Setting every channel of $\bm{a}_\ell$ to a common value recovers the
> scalar predictor of \cref{eq:ar1}; setting it to $\bm{0}$ recovers plain skipping.

## Cost claim (update everywhere it appears)

- **params:** $O(d)$ per skipped block ($d = 896$ on 0.5B) — *not* $O(1)$. The abstract,
  intro ¶7, and Method ¶*Cost* currently all say "one or two scalars per skipped layer".
  **All three must change together** — same atomic-commit rule as Group A.
- **compute:** $O(Td)$ — unchanged. Still one scaled vector op. This is the load-bearing
  efficiency claim and it survives.
- Still: no gradient training, closed form, unlabeled calibration.

---

# BLOCK C/E — fallback: "predictability is not recoverability"

Use **only if** per-channel fails to confirm at T+0:45. Full draft retained from the
previous revision — title *Predictable but Indispensable: Why Skipped Transformer Updates
Resist Cheap Recovery*, built on the four R1 facts (median $P_\ell = 0.028$; 1/22 layers
with $P>0.1$; Spearman $-0.015$; L3 $P=0.90$ yet recovery $-0.83$; momentum confined to
L17–22, best repair $16.8\%$ at L21). Under this pivot the abstract's gap-recovery
headline is **deleted**, not softened.

---

# Figure 1 captions — REAL, zero `\ph{}`, valid under both pivots

Panel B is the centerpiece either way.

```latex
% Panel B — the dissociation
\caption{\textbf{Predictability does not imply recoverability.} For each eligible layer of
Qwen2.5-0.5B, held-out explained update energy $P_\ell$ (\cref{eq:pscore}, $x$-axis)
against the fraction of that layer's single-layer plain-skip NLL damage that the scalar
predictor repairs ($y$-axis). The two are uncorrelated (Spearman $-0.015$, $p=0.95$,
$n=22$). Layer~3 (annotated) is the extreme case: a one-scalar model explains $90\%$ of
its update energy, yet substituting that prediction is markedly worse than dropping the
update outright, nearly doubling the damage. Accurate forecasting in residual space is
therefore not the same as preserving the model's function. Coefficients are fitted on 16
WikiText-103 sequences and both $P_\ell$ and the NLL damage are measured on 16 disjoint
held-out WikiText-103 sequences, in FP32 on an NVIDIA TITAN X (Pascal) GPU.}
```

```latex
% Panel A — depth profile. Now backed at BOTH the scalar and the channel level.
\caption{\textbf{Successive blocks partially undo one another, until they do not.}
Fitted coefficient against layer index for Qwen2.5-0.5B, shown two ways: the single
global scalar $\alpha_\ell$, and the fraction of the $d=896$ per-channel coefficients
that are positive. Through the middle of the network the two agree that depth is
\emph{anti}-correlated --- every scalar coefficient is negative across layers 4--16, and
only $12\%$ of channels there are positive (median coefficient $-0.19$) --- so a skipped
block's update is not a continuation of its predecessor but partly a reversal of it.
Positive depth-wise momentum emerges only in the final quarter of the stack, where the
positive-channel fraction rises above $0.6$. Fitted and scored on disjoint 16-sequence
splits of WikiText-103, in FP32 on an NVIDIA TITAN X (Pascal) GPU.}
```
*(Panel A states only what is measured, at two independent levels of granularity. It says
nothing about **why** the per-channel predictor outperforms the scalar — both candidate
mechanisms were tested and refuted.)*

---

# STAGED: appendix correctness numbers (pivot-independent, apply on A2 call)

Real, from `r0_checks_0.5b.json` — **6/6 pass, three of them bit-exact**. This is free
credibility and costs three lines. Replaces the qualitative list in
`experiments_appx.tex` §A.1:

> All six checks pass on Qwen2.5-0.5B (24 blocks, 22 eligible). The dense wrapper
> reproduces the unmodified model's logits **bit-exactly** (max absolute logit difference
> $0.0$), as do the $\alpha_\ell = 0$ reduction to Plain Skip (checked at layers 5, 9, 13)
> and a hand-written single-layer skip (layer 9). Residual updates are captured at the
> block boundary of \cref{eq:residual} to a maximum absolute error of
> $3.8\times10^{-6}$ against a hidden-state scale of $1.7\times10^{3}$ --- eight orders of
> magnitude smaller. Scrambling the padded token slots moves neither the fitted
> accumulators nor the held-out NLL ($0.0$ change, 192 real tokens counted), confirming
> padding is excluded from \cref{eq:fit}. The selected layer set is non-adjacent by
> construction (minimum gap 2, first and last blocks excluded).
