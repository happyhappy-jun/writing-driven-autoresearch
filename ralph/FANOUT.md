# Verification fan-out — exact spec (pre-written T+1:13; two-pass per master.md §5b)
# PASS 2 ADDITION (T+1:26): verify the post-freeze \phm unwrap commit's diff is a PURE macro
# strip — zero value changes (`git show <unwrap-commit>` touches only \phm{X}→X patterns).

## PASS 2 SCOPE (pinned T+1:33 — pass 1 done: 7 PASS / 3 NO, all fixes dispatched)
Pass 2 re-verifies ONLY the delta since pass-1 snapshots, plus the always-run suite:
1. **Unwrap-commit purity** (above) — pure macro strip, zero value changes.
2. **Latency surfaces** (commit fc40d93 postdated snapshots): every latency sentence vs
   latency_Qwen2.5-7B.json (0.6442/0.0321/1.1406/1.1480/1.151; IQR caveat at 2048;
   "prefill" per sentence; 7B named; Group A latency-fact identity re-check).
3. **Pass-1 fix commit files** (verify each fix landed AND introduced nothing new):
   experiments_appx §app-protocol (per-run protocols: 0.5B analysis 16/16 wt-103 len512 vs
   0.5B composition 32-seq wt-2 test, 100-ex); related_works novelty sentence says
   PER-CHANNEL not scalar; intro:49 no bare "free"; intro:90 + experiments:75 counts-form
   (no typeset % — appendix worked example MAY keep it); experiments:80 superlative = 70.0%
   (r3 recovery_top_k2 = 0.70019) w/ catastrophic context; experiments:82 "at k=4";
   method:31 "fitting-free"; fig1a_appendix:8 "sits"; conclusion:14 seq-512 qualifier;
   PH-LEDGER header/L77/L88 hygiene.
4. **gen-table re-test** (pass-1 item 11 failed on schema drift): reconciled script must
   regenerate BOTH tables diff-clean; bold-by-ownership line gone from the script.
5. **Always-run**: verify-phm.py exit 0; ~/writing-audit.sh --final (post-unwrap: 0 \phm too);
   master's independent greps (\ph{, \phm{ post-unwrap, STAND-terms, a100, olp_);
   body p4 / refs p5; anonymous; working tree clean + pushed.
Anything NOT in this scope was verified in pass 1 against files that have not changed since.

Run these as PARALLEL subagents (Agent tool, one per item; ~12-16 total is correct).
Each returns PASS or `NO: <paper value> vs <JSON value> @ <file:key>`. Any NO → real value
or delete the sentence. Do not relay numbers through chat prose — verifiers read files.

## A. \phm key verification (sample + tool)
1. Run `python3 ~/verify-phm.py` (exit 0 = all backed+matching) — then HAND-CHECK a random
   sample of 8 ledger rows yourself against raw JSONs (tool author ≠ auditor).
2. Verify ~/ralph/PH-LEDGER.md has NO row whose source is writing's own arithmetic —
   every row cites an experiment JSON key (rule 3).

## B. Group A / Group D
3. Group A: extract the headline numbers from abstract, intro, experiments, conclusion,
   Table 1 caption — assert ALL FIVE identical.
4. Group D: for each table/figure, protocol constants in prose (n_seq, seq_len, n_examples,
   batch, corpus, dtype, hardware) == that run's JSON config block. Known truths:
   0.5B=fp32/TITAN X/100-ex/wikitext-2-test-eval; 1.5B=bf16/3090/300-ex/len1024;
   7B=bf16/3090/300-ex (verify vs r4 config on disk).

## C. Statistics (rule 10 + derived stats)
5. Recompute spearman(P_ar1, recovery_ar1) from r1_layerscan (expect −0.0152, n=22).
6. Recompute the noise audit for TWO rows (one deployable, one recovery_top) from raw
   methods blocks: absolute question counts, SEs from real p_t and n. Expect: deployable
   deltas inside 1se; 1.5B recovery_top k=2 ≈ +132/900 outside noise.
7. Sweep prose for ANY fraction: check its denominator; noise-level gaps must appear as
   absolute counts (rule 10), and no accuracy fraction survives in prose in either direction.

## D. Figures (a plot is a claim surface)
0. **ASSET-CAPTION DRIFT** (added T+1:26 after a live instance): for EVERY figure asset,
   compare the PDF's mtime against the last commit touching its caption `.tex`. Asset newer
   than caption ⇒ suspect: verify the caption describes the CURRENT drawing (series count,
   bands, panel titles, sign language). This class is invisible to key-checks — a plot can be
   regenerated under a caption describing its predecessor.
8. fig1a/fig1b: sample 5 plotted points each vs r1_layerscan values; axes/labels honest.
9. fig2 v2: verify band widths equal computed SEs from JSON n_examples + p_t (sample 3);
   the 7B points (if present) match r4 JSON; the one positive point IS drawn.
10. ALL captions + panel titles: no asserted negative ("does not" → must be "no measurable
    gain" class); each caption names the model/hardware/protocol of the run it plots;
    canonical-sentence consistency (benefit only in catastrophic regime; undetectable at
    deployable point at our n; never "harms").

## E. Tables
11. Regenerate Table 1 + Table 2 via `python3 ~/gen-table.py` into a SCRATCH dir; diff
    against the committed .tex — must be identical (no hand edits, rule 9).
12. Bolding: per column, bold == genuine best value (Plain Skip bolds acc columns where
    true; \mname bolds NLL). Check 4 random columns by hand.

## F. Final text sweeps (also in writing-audit.sh, but run independently)
13. `grep -rn '\\ph{' section/ tables/` → must be EMPTY (only \phm may remain, then unwrap).
14. `grep -rniE 'stand|n-gram|speculative|drafting|gumbel' section/ tables/ figures/`
    (filter understand/standard/outstanding) → empty.
15. `grep -rni 'a100' section/ tables/ figures/` → empty. `grep -rn 'olp_' ~/writing
    --exclude-dir=.git` → empty.
16. Latency sentences: every one contains "prefill"; no bare "free"; numbers match
    latency JSON (7B version if it landed, else 1.5B, protocol-truthful).

## Canonical claims (what the paper may assert — check nothing exceeds these)
- NLL recovery: real, 5–18% deployable (0.5B/1.5B; 7B per r4), huge denominators. ✓fractions ok
- Accuracy: benefit ONLY in catastrophic regime (+132/900 etc., outside noise); at the
  deployable point UNDETECTABLE at our sample sizes, either direction; NEVER "harms".
- Cost: +0.23%/+0.18% prefill latency (1.5B; or 7B numbers if landed). "prefill" mandatory.
- Mechanism: OPEN; L3 case study assertable; "blocks partially undo one another" assertable
  (two-level evidence); scalar = norm-weighted average misdescribing sign-mixed layers.
- Predictability ⟂ recoverability (ρ=−0.0152, p=0.9463); P is energy-blind (ridge 2.73→11.01).
- "To our knowledge" ≤ 1 use. No SOTA/lossless/first-ever. No end-to-end speedup claims.
