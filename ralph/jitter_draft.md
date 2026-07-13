# Eval-jitter finding: staged, BLOCKED on data

**Status: NOT IN THE PAPER. The data is not on disk.**
`noise_audit.json` (13:52) has no jitter block, and there is no separate jitter file. The
relayed figure (±4–5 of 900 on bit-identical configs) is almost certainly right, but I have
not read it from a file, so it is not written.

The moment a file lands, the three blocks below go in verbatim and the verifier keys below
get wired. Expected: ~2 minutes.

## Why this finding is worth the wait

It is the sharpest possible form of the paper's central claim. Right now we say the
deployable accuracy differences are *not statistically significant*. With the jitter number
we can say something strictly stronger and far more concrete:

> **the differences are smaller than the run-to-run variation of the evaluation itself.**

That reframes every accuracy non-claim from caution into **precision**. We did not decline to
claim a gain because we were being careful; we declined because we measured the noise floor
and the gain sits underneath it.

## (1) BODY, one line, where the deployable-accuracy claim lives

In `experiments.tex`, `\paragraph{Limitations.}`, appended to the first sentence:

> ..., and indeed at the deployable operating point the accuracy differences are smaller than
> the run-to-run variation of the evaluation itself (\Cref{sec:app-noise}).

**Page cost: zero** if it displaces the existing "(largest \phm{22} … $z=\phm{1.18}$ …)"
parenthetical, which it supersedes. If it does not fit, it replaces that parenthetical rather
than adding to it. I will state the cost before committing either way.

## (2) APPENDIX, into `\subsection{Accuracy deltas, sampling noise, and ratio inflation}`

> \paragraph{A third source of uncertainty: the evaluation is not deterministic.} Binomial
> sampling error is not the only noise in these numbers. Re-running a \emph{bit-identical}
> configuration under a different evaluation batch shape changes the score: language-modelling
> NLL is bit-identical, but multiple-choice items whose top two options are near-tied can flip
> under BF16 reduction-order differences. Duplicating one configuration and evaluating it at
> batch size 32 and at 8, we measure a run-to-run drift of \phm{X} correct answers out of
> \phm{900} with no change to the model, the layer set, or the seed. Every accuracy difference
> we report at the deployable operating point is of that order or smaller. This does not
> weaken the analysis; it locates its floor, and our decision to claim neither improvement nor
> harm there sits exactly on it.
>
> The two Bonferroni survivors are unaffected: at \phm{132} and \phm{90} net answers they are
> \phm{N}$\times$ the measured jitter, and no reordering of the evaluation batch could produce
> them.

## (3) TABLE 1 caption clause (only if page-free; cost stated first)

> Accuracy differences at these layer sets are of the same order as the evaluation's own
> run-to-run jitter (\Cref{sec:app-noise}).

## Verifier keys to wire (once the file exists)

```
X  -> <jitter file>.<key for net-answer drift on the duplicated config>
900 -> total graded (already backed)
N  -> 132 / X   and   90 / X   (compute; do NOT hand-write "25-30x" — master's relayed
       range fits 132 but NOT 90: 90/4.5 is ~20x, not 25-30x. Compute both from the file
       and state the smaller one, or give the range honestly.)
```

## ⚠️ Ceiling note on the "25–30×" figure

Master's relayed "25-30x the jitter" checks out for **+132** (132/4.5 ≈ 29×) but **not for
+90** (90/4.5 ≈ 20×). Writing "both survivors are 25-30x the jitter" would be false for one
of the two. When the file lands, compute each ratio and either give the true range or quote
the smaller survivor. This is the same class as "grows with scale": a true statement about
one cell, silently generalized to two.
