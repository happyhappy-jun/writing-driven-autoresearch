# favsel: pre-registered prediction, sentence pre-written BOTH ways

**Not in the paper.** `ct_favsel_0.5b_k{2,4}.json` are not on disk. If they land by T+2:38,
one of the two sentences below goes into the appendix CT subsection, chosen by what the file
says. If they miss, nothing is written and nothing is implied.

## The pre-registration

The damage axis predicts: favourable-selection sets are **high-damage**, so the damage axis
expects a **large** cross-token gain there. This prediction is recorded *before* the data
lands. That is what makes it a test rather than a story.

**Both outcomes get equal prominence.** A confirmation strengthens the spine; a refutation is
reported with the same weight, in the same place, in the same voice. Writing only the
confirming sentence in advance would make the "prediction" decorative.

## If CONFIRMED (large CT gain on the favsel sets)

> Cross-token selection provides a test of the damage axis rather than another illustration of
> it. We predicted, before running it, that favourable-selection sets would be high-damage and
> would therefore show a large cross-token gain. They do: at $k=\phm{K}$ the extension recovers
> \phm{X}\% of the plain-skip damage against \phm{Y}\% for the depth-only predictor. The axis
> predicted the sign and the magnitude of a result it had not seen.

## If REFUTED (small or absent CT gain)

> Cross-token selection provides a test of the damage axis, and the axis fails it. We predicted,
> before running it, that favourable-selection sets would be high-damage and would therefore
> show a large cross-token gain. They do not: at $k=\phm{K}$ the extension recovers \phm{X}\%
> against \phm{Y}\% for the depth-only predictor. We report this with the same prominence we
> would have given a confirmation. The damage ordering we describe elsewhere is a description of
> the runs we performed, not a law with predictive force, and this is the clearest evidence of
> that limit.

## Verifier keys (wire on landing)

```
X -> ct_favsel_0.5b_k<K>.json .runs.*.recovery.depth_ar_ct.gap_recovered_nll  (x100)
Y -> ct_favsel_0.5b_k<K>.json .runs.*.recovery.depth_ar.gap_recovered_nll     (x100)
```

Page cost: one sentence in the appendix. **Zero body cost.**
