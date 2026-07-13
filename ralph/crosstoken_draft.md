# Cross-token extension: paste-ready draft (SCRATCH, not in the build)

All numbers read from `~/ralph/results/r5_crosstoken_0.5b.json`. Scope of the evidence that
has actually landed: **single-layer scan, Qwen2.5-0.5B only, WikiText-2 test, 22 eligible
layers.** No composition, no transfer. The prose below claims exactly that and no more.

## ⚠️ Ceiling discipline (the rule that just caught me)

I wrote "recovery grows with scale" an hour ago and it was true at $k{=}4$ and *false* at
$k{=}2$. It reached four places before pass-2 caught it. So, for this extension:

- It is a **single-layer scan**. Not a deployment result. Never write "improves \mname"
  without "on a single-layer scan at 0.5B".
- 19/22 is **not** "consistently" and **not** "everywhere". Write **19 of 22**.
- The recovery numbers are **means/medians over a layer scan**, not an end-to-end budget.
- No claim about 1.5B/7B, and none about composition, until those files exist.

## Method paragraph (drop-in after `\paragraph{\mname: per-channel autoregression across depth.}`)

> \paragraph{Looking across tokens as well as depth.} The predictor of \cref{eq:diag} uses
> only the previous layer's update at the \emph{same} token position. Nothing forces that.
> Writing $\dd_{\ell-1}(t)$ for the update at layer $\ell-1$ and token $t$, we can give each
> channel a second coefficient on the preceding layer's update at the preceding \emph{token},
> \begin{equation}
> \widehat{\dd}_\ell(t) = \aal_\ell \odot \dd_{\ell-1}(t) \;+\; \bb_\ell \odot \dd_{\ell-1}(t-1),
> \label{eq:crosstoken}
> \end{equation}
> with $\aal_\ell, \bb_\ell \in \mathbb{R}^{d}$ fitted in the same closed form. The state
> grows to $2d$ scalars per skipped block (\phm{1792} on Qwen2.5-0.5B) and the inference cost
> stays at $O(Td)$: the shifted tensor is already resident, and $\bb_\ell = \bm{0}$ recovers
> \cref{eq:diag} exactly, which we verify numerically (\phm{0.0} NLL difference).

Notation: needs `\newcommand{\bb}{\bm{b}}` in `main.tex` (next to `\aal`).

## Results sentence (drop-in, Experiments)

> \paragraph{Depth is not the only axis.} Prediction from the preceding layer at the same
> token is a choice, not a constraint. On a single-layer scan over the \phm{22} eligible
> layers of Qwen2.5-0.5B, adding a per-channel term on the previous \emph{token}'s update
> (\cref{eq:crosstoken}) lowers mean held-out NLL from \phm{3.40} to \phm{3.08} against a
> dense \phm{2.76}, and improves on the depth-only predictor at \phm{19} of the \phm{22}
> layers, lifting median single-layer recovery from \phm{4.8}\% to \phm{8.6}\%. This is
> preliminary: it is a single-layer scan at one scale, we have not composed it across
> multiple skipped blocks, and we do not report it in \Cref{tab:main}. We flag it because it
> suggests the depth trajectory is not the only cheap signal available to a skipped block.

## Scan-table row (append to `tab:selection`, or a small appendix table)

| Predictor | params/layer | mean NLL ↓ | median recovery ↑ | layers better than diag |
|---|---|---|---|---|
| Plain Skip | 0 | (dense 2.76) | 0 | |
| \mname (per-channel, depth only) | `\phm{896}` | `\phm{3.40}` | `\phm{4.8}`\% | |
| \mname + cross-token | `\phm{1792}` | `\phm{3.08}` | `\phm{8.6}`\% | `\phm{19}` of `\phm{22}` |

## Scope ladder (master's, executed from what lands by T+2:35)

| Landed | What the paper may say |
|---|---|
| **scan only (now)** | "preliminary, single-layer 0.5B evidence"; appendix or one Experiments paragraph; **not** in Table 2 |
| **+ composition** | add a composition row; may say it survives multi-layer skipping at 0.5B |
| **+ 1.5B verify** | add a transfer sentence; may say the effect is not a 0.5B artifact |
| **nothing further** | keep exactly the paragraph above; it is honest as-is |

## Verifier keys (add to `verify-phm.py` when this goes in)

```
F_CT = "r5_crosstoken_0.5b.json"
3.08  -> .summary.mean_nll_ct              (3.0827)
3.40  -> .summary.mean_nll_diag            (3.4039)
2.76  -> .dense_nll                        (2.7626)
8.6   -> 100 * .summary.median_recovery_ct   (8.55)
4.8   -> 100 * .summary.median_recovery_diag (4.83)
19    -> .summary.n_layers_ct_beats_diag
22    -> .summary.n_layers
1792  -> .config.params_per_layer.var_ct_diag
0.0   -> .correctness_gate_ct_b0_equals_diag.abs_nll_diff   (pass: true)
```

**Cost check before this ships:** the paper's abstract and Method both say \mname stores "a
$d$-dimensional coefficient vector". If the cross-token variant is presented as \mname rather
than as an extension, that claim becomes false. It is presented here as an **extension**, so
the $O(d)$ claim stands for the method proper. Do not blur them.
