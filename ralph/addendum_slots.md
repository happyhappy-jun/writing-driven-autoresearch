# Addendum slots: all four, drafted BOTH ways. Tree untouched.

**`d034a8b` is the submission of record.** Nothing here is in the paper. Each slot lands only
if its file lands, at exactly the scope the file supports, and each is drafted so a null or
adverse result reads as naturally as a favourable one.

Files on disk as of drafting: **none of the four**. Checked, not assumed.

---

## SLOT 1 — Qwen3 second family (scale trend)

**Where:** the scale-trend sentence in Experiments; appendix rows via `gen-table` (Qwen3 block).

**Ceiling rules, pre-committed:**
- "Grows with scale" is a **k=4** claim. On Qwen2.5 it was FALSE at k=2 (8.4 → 8.2 → 7.3).
  Check Qwen3's k=2 before writing anything unqualified.
- **NLL-only cells support no accuracy claim.** Not "presumably", not "we expect".
- Family sweep says **exactly what ran**: 0.6B–8B, plus 14B/32B only if their files exist.
  **Never imply 32B ran.** It is a race; if it loses, it is not in the sentence.
- Per-model, from each file's `config`: dtype, GPU, corpus, seq_len. If Qwen3 ran a different
  precision or corpus than Qwen2.5, **the sentence says so.**

**If the trend HOLDS:**
> The trend is not specific to one model family. On Qwen3 at four skipped blocks, \mname
> recovers X\% to Y\% of the plain-skip language-modelling damage from 0.6B to 8B. We measure
> likelihood only for this family and make no downstream-accuracy claim for it.

**If the trend DOES NOT hold (flat, or non-monotone):**
> The trend is family-specific. On Qwen3 at four skipped blocks, recovery is [flat / declining]
> with scale (X\%, Y\%, Z\%), so the growth we observe on Qwen2.5 is not a general property of
> Transformer depth. We report this rather than confining the claim to the family that shows it.

*The second sentence is the one that matters. If Qwen3 flattens the trend, that is a finding
about our own headline, and it goes in with the same prominence.*

---

## SLOT 2 — Qwen3 task evals: the damage axis as a PRE-REGISTERED prediction

**Only if 4B/8B task cells land.** The damage axis (ρ = 0.820, p = 9e-08 on 28 Qwen2.5 runs)
makes a prediction for a family it has never seen: **gains should track plain-skip damage, and
be null where damage is small.** That is a genuine out-of-sample test, and it is the strongest
form of evidence available to this paper.

**Pre-registered, before the file lands:**

**CONFIRMED:**
> The damage ordering was fitted on Qwen2.5 alone. Applied out of sample to Qwen3 it predicts
> the outcome correctly: gains are null where skipping does little damage and large where it
> does much (\phm{...}). An ordering that transfers to an unseen model family is evidence of a
> mechanism rather than a coincidence of our runs.

**REFUTED:**
> The damage ordering was fitted on Qwen2.5 alone, and it does **not** transfer to Qwen3:
> [the null runs show gains / the high-damage runs do not]. We report this with the prominence
> of a headline, because it is one. The ordering describes the runs we performed and does not,
> on this evidence, generalize across model families. The aphorism in \Cref{sec:...} must be
> read as a summary of our measurements, not as a law.

*The refutation would falsify the paper's spine. It is written first, and in full, precisely so
that it cannot be quietly softened after the fact.*

**Jitter/Bonferroni consequence:** any Qwen3 task numbers enter the audit and **regrow the
family a fifth time** (16 → 37 → 41 → 63 → ?). Every constant re-read from the JSON, and every
site swept. This has silently falsified correct-when-written prose four times already.

---

## SLOT 3 — jitter_replication: noise floor from one config → a distribution

**Strictly stronger than what we have.** The current paragraph rests on **one duplicated
config** (batch 32 vs 8, max swing 4 of 900). A replication gives a measured *distribution*.

> \paragraph{A third source of uncertainty: the evaluation is not deterministic.} ... Across
> \phm{N} duplicated configurations, re-scoring an identical setup under a different task batch
> shape moves the score by a median of \phm{X} and at most \phm{Y} answers of \phm{900}, with
> language-modelling NLL identical to within one ulp. Every accuracy difference we report at
> light budgets is of that order or smaller.

**Rules:** quote the **distribution** (median and max), not a single point. The four Bonferroni
survivors' jitter ratios (33×, 22.5×, and the 7B k=8 pair) get **recomputed against the new
floor** — if the floor rises, those ratios fall, and if any survivor drops near it, **that is a
finding and it goes in the paper.** Do not assume the survivors survive; check.

---

## SLOT 4 — Fig 2 extra 0.5B points (k = 3, 5, 7)

Asset + caption move together (**D0**). Denser sampling only; no new claim. **But re-verify
the caption's pattern claims against the new curve** — a denser curve can break a monotonicity
the sparse one implied. Captions drift; bodies do not. That check is mandatory, not optional.

---

## Mini-audit before the addendum push (non-negotiable)

```
~/gen-table.py --check          # tables regenerate byte-identical; never hand-type a cell
~/verify-phm.py                 # every new value backed by an exact JSON key
~/build-writing.sh
~/writing-audit.sh --final      # 0 \ph AND 0 \phm
hand render-check               # conclusion's last words on p4, 0 hits on p5
git commit -m "post-deadline addendum: ..."   # clearly labeled, separate from d034a8b
```

**The unwrap wrinkle:** the paper has no `\phm{}` left. New numbers go in bare, but they are
**still wired into `verify-phm.py` with exact JSON keys** and verified against the raw `.tex`.
The verifier never needed the macro, only a spec entry.

**The rule does not relax because the deadline passed: no number enters the paper that I have
not read from a file.**
