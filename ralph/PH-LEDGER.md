# PH-LEDGER — every provisional value in the paper, and what it waits on

**Owner:** `writing`. Rewritten at Pivot B′ (T+1:05). Supersedes the pre-pivot version.

**Regenerate:** `grep -rnoE '\\phm?\{[^}]*\}' ~/writing/section/ ~/writing/tables/`
**Enforce:** `~/writing-audit.sh --final` (fails on `\ph{}`, warns-to-unwrap on `\phm{}`)

---

## ⚠️ TWO MACROS. THEY GET OPPOSITE TREATMENT AT T+2:47.

| Macro | Meaning | Count | Rule at final audit |
|---|---|---|---|
| `\ph{}` | **INVENTED.** No measurement exists. A written-ahead guess. | **113** | **Land the real number, or DELETE THE SENTENCE.** Never ship as measured. |
| `\phm{}` | **MEASURED.** A result file backs it; a same-protocol run may supersede it. | **56** | **UNWRAP IT** (drop macro, keep value). **Deleting it destroys a true claim.** |

This split is the single most important thing in this file. Before it, a fabricated
`2.35` in Table 1 and the measured `24.7` from `r2probe_0.5b.json` were both `\ph{}` and
therefore indistinguishable — and the blanket rule "delete anything still wrapped" would
have thrown away **the entire real 0.5B result** while leaving fiction untouched.


## ✅ `\phm{}` COMPLETENESS + VERIFICATION (master's binding condition 1)

**Status: 207/207 distinct `\phm{}` values verified. 0 unbacked. 0 mismatched.**
**Frozen commit for pass 2: see latest push (positive reframe).** All latency rows now point at
`latency_Qwen2.5-7B.json` (the 1.5B latency file is superseded and no longer cited).
Regenerate any time with `~/verify-phm.py` (exit 0 = all backed and matching);
`~/verify-phm.py --ledger` re-emits the table below.

`~/writing-audit.sh` now runs this on every invocation, so a `\phm{}` that drifts from
its source file fails the audit rather than reaching the PDF.

> **It has already caught two real bugs.** (1) `experiment` re-fit
> `diag_channel_stats_0.5b.json` with a ridge at 13:06; L3's median channel coefficient
> moved −0.296 → −0.198, and the paper's `−0.30` had silently gone **stale against its own
> source**. (2) A copy-update cell was rounded to −0.141 where the file says −0.1405.
> Neither was catchable by eye. Both are fixed.
>
> ⚠️ Note `r1_analysis_0.5b.json` (12:55) predates that refit, so its
> `median_a_l_L4_16_mean` (−0.1937) is stale against the current diag file (−0.1875).
> Both round to the `−0.19` the paper prints, so no claim is affected — but **derived
> analysis files can go stale when a source is regenerated**, and only a key-level check
> catches it.

| Value | Source file | Exact key | Actual | Appears in |
|---|---|---|---|---|
| `\phm{$+0.0009$}` | `r1_analysis_0.5b.json` | `.paper_cited_stats.mean_recovery_delta_ar2_minus_ar1` | `0.0009075` | experiments_appx.tex |
| `\phm{$+0.039$}` | `r2probe_0.5b.json` | `.runs.oracle_lite_k2.gap_recovered_nll.depth_ar1` | `0.03942` | selection_table.tex |
| `\phm{$+0.040$}` | `r2probe_0.5b.json` | `.runs.oracle_lite_k4.gap_recovered_nll.depth_ar1` | `0.04003` | selection_table.tex |
| `\phm{$+0.053$}` | `r2probe_0.5b.json` | `.runs.predictability_k2.gap_recovered_nll.depth_ar_diag` | `0.05342` | experiments.tex, selection_table.tex |
| `\phm{$+0.074$}` | `r2probe_0.5b.json` | `.runs.oracle_lite_k4.gap_recovered_nll.depth_ar_diag` | `0.07443` | selection_table.tex |
| `\phm{$+0.078$}` | `r2probe_0.5b.json` | `.runs.oracle_lite_k2.gap_recovered_nll.depth_ar_diag` | `0.07794` | selection_table.tex |
| `\phm{$+0.163$}` | `r2probe_0.5b.json` | `.runs.recovery_top_k4.gap_recovered_nll.depth_ar1` | `0.163` | selection_table.tex |
| `\phm{$+0.166$}` | `r2probe_0.5b.json` | `.runs.recovery_top_k2.gap_recovered_nll.depth_ar1` | `0.1659` | selection_table.tex |
| `\phm{$+0.194$}` | `r2probe_0.5b.json` | `.runs.predictability_k4.gap_recovered_nll.depth_ar_diag` | `0.1935` | selection_table.tex |
| `\phm{$+0.205$}` | `r2probe_0.5b.json` | `.runs.recovery_top_k2.gap_recovered_nll.depth_ar_diag` | `0.2045` | selection_table.tex |
| `\phm{$+0.247$}` | `r2probe_0.5b.json` | `.runs.recovery_top_k4.gap_recovered_nll.depth_ar_diag` | `0.2465` | selection_table.tex |
| `\phm{$+1.10$}` | `diag_channel_stats_0.5b.json` | `.layers.3.alpha_ar1` | `1.098` | experiments.tex |
| `\phm{$-0.015$}` | `r1_analysis_0.5b.json` | `.paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.rho` | `-0.01525` | experiments.tex, introduction.tex |
| `\phm{$-0.128$}` | `r2probe_0.5b.json` | `.runs.predictability_k4.gap_recovered_nll.depth_ar1` | `-0.1276` | selection_table.tex |
| `\phm{$-0.140$}` | `r2probe_0.5b.json` | `.runs.recovery_top_k2.gap_recovered_nll.copy_update` | `-0.1405` | selection_table.tex |
| `\phm{$-0.19$}` | `diag_channel_stats_0.5b.json` | `mean(.layers.4..16.median)` | `-0.1875` | experiments_appx.tex |
| `\phm{$-0.686$}` | `r2probe_0.5b.json` | `.runs.recovery_top_k4.gap_recovered_nll.copy_update` | `-0.686` | selection_table.tex |
| `\phm{$-0.745$}` | `r2probe_0.5b.json` | `.runs.predictability_k2.gap_recovered_nll.depth_ar1` | `-0.7449` | experiments.tex, selection_table.tex |
| `\phm{$-0.779$}` | `r2probe_0.5b.json` | `.runs.predictability_k2.gap_recovered_nll.copy_update` | `-0.7791` | selection_table.tex |
| `\phm{$-1.736$}` | `r2probe_0.5b.json` | `.runs.oracle_lite_k2.gap_recovered_nll.copy_update` | `-1.736` | selection_table.tex |
| `\phm{$-1.800$}` | `r2probe_0.5b.json` | `.runs.predictability_k4.gap_recovered_nll.copy_update` | `-1.8` | selection_table.tex |
| `\phm{$-2.395$}` | `r2probe_0.5b.json` | `.runs.oracle_lite_k4.gap_recovered_nll.copy_update` | `-2.395` | selection_table.tex |
| `\phm{$-2.42$}` | `ridge_analysis_0.5b.json` | `.by_ridge["10.0"].layer2_recovery_dev` | `-2.423` | experiments_appx.tex |
| `\phm{$-3.68$}` | `ridge_analysis_0.5b.json` | `.by_ridge["0.01"].layer2_recovery_dev` | `-3.679` | experiments_appx.tex |
| `\phm{+11.1}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.recovery.depth_ar1.gap_recovered_avg_acc` | `11.11` | main_table.tex |
| `\phm{+18.5}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.recovery.depth_ar.gap_recovered_avg_acc` | `18.52` | main_table.tex |
| `\phm{+2}` | `r4_headline_7b.json` | `sum_t round((.runs.residual_damage_k2.methods.depth_ar1[t] - plain_skip[t]) * 300)` | `2` | main_table.tex |
| `\phm{+22}` | `r4_headline_7b.json` | `sum_t round((.runs.residual_damage_k4.methods.depth_ar[t] - plain_skip[t]) * 300)` | `22` | main_table.tex |
| `\phm{+3}` | `r3_verify_1.5b.json` | `sum_t round((.runs.residual_damage_k2.methods.depth_ar1[t] - plain_skip[t]) * 300)` | `3` | main_table.tex |
| `\phm{+35.5}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.recovery.depth_ar.gap_recovered_avg_acc` | `35.48` | main_table.tex |
| `\phm{+4}` | `r4_headline_7b.json` | `sum_t round((.runs.residual_damage_k2.methods.depth_ar[t] - plain_skip[t]) * 300)` | `4` | main_table.tex |
| `\phm{+4.3}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.recovery.depth_ar1.gap_recovered_avg_acc` | `4.348` | main_table.tex |
| `\phm{+5}` | `r3_verify_1.5b.json` | `sum_t round((.runs.residual_damage_k2.methods.depth_ar[t] - plain_skip[t]) * 300)` | `5` | main_table.tex |
| `\phm{+8.1}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.recovery.depth_ar1.gap_recovered_avg_acc` | `8.065` | main_table.tex |
| `\phm{+8.7}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.recovery.depth_ar.gap_recovered_avg_acc` | `8.696` | main_table.tex |
| `\phm{-0.015}` | `r1_analysis_0.5b.json` | `.paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.rho` | `-0.01525` | fig1_predictability.tex |
| `\phm{-0.825}` | `r1_layerscan_0.5b.json` | `.layers.3.recovery.depth_ar1` | `-0.8254` | fig1_predictability.tex |
| `\phm{-112}` | `r4_headline_7b.json` | `sum_t round((.runs.residual_damage_k4.methods.copy_update[t] - plain_skip[t]) * 300)` | `-112` | main_table.tex |
| `\phm{-143.5}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.recovery.copy_update.gap_recovered_avg_acc` | `-143.5` | main_table.tex |
| `\phm{-15.8}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.recovery.depth_ar1.gap_recovered_avg_acc` | `-15.79` | main_table.tex |
| `\phm{-151.9}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.recovery.copy_update.gap_recovered_avg_acc` | `-151.9` | main_table.tex |
| `\phm{-157.9}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.recovery.copy_update.gap_recovered_avg_acc` | `-157.9` | main_table.tex |
| `\phm{-16.7}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.recovery.depth_ar1.gap_recovered_avg_acc` | `-16.67` | main_table.tex |
| `\phm{-178}` | `r3_verify_1.5b.json` | `sum_t round((.runs.residual_damage_k4.methods.copy_update[t] - plain_skip[t]) * 300)` | `-178` | main_table.tex |
| `\phm{-180.6}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.recovery.copy_update.gap_recovered_avg_acc` | `-180.6` | main_table.tex |
| `\phm{-21.1}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.recovery.depth_ar.gap_recovered_avg_acc` | `-21.05` | main_table.tex |
| `\phm{-265.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.recovery.copy_update.gap_recovered_avg_acc` | `-265.7` | main_table.tex |
| `\phm{-27.8}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.recovery.depth_ar.gap_recovered_avg_acc` | `-27.78` | main_table.tex |
| `\phm{-3}` | `r2_compose_0.5b.json` | `sum_t round((.runs.residual_damage_k2.methods.depth_ar1[t] - plain_skip[t]) * 100)` | `-3` | main_table.tex |
| `\phm{-30}` | `r2_compose_0.5b.json` | `sum_t round((.runs.residual_damage_k4.methods.copy_update[t] - plain_skip[t]) * 100)` | `-30` | main_table.tex |
| `\phm{-4}` | `r2_compose_0.5b.json` | `sum_t round((.runs.residual_damage_k4.methods.depth_ar[t] - plain_skip[t]) * 100)` | `-4` | main_table.tex |
| `\phm{-4.5}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.recovery.depth_ar1.gap_recovered_avg_acc` | `-4.478` | main_table.tex |
| `\phm{-41}` | `r3_verify_1.5b.json` | `sum_t round((.runs.residual_damage_k2.methods.copy_update[t] - plain_skip[t]) * 300)` | `-41` | main_table.tex |
| `\phm{-44.4}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.recovery.copy_update.gap_recovered_avg_acc` | `-44.44` | main_table.tex |
| `\phm{-5}` | `r2_compose_0.5b.json` | `sum_t round((.runs.residual_damage_k2.methods.depth_ar[t] - plain_skip[t]) * 100)` | `-5` | main_table.tex |
| `\phm{-6.0}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.recovery.depth_ar.gap_recovered_avg_acc` | `-5.97` | main_table.tex |
| `\phm{-66}` | `r4_headline_7b.json` | `sum_t round((.runs.residual_damage_k2.methods.copy_update[t] - plain_skip[t]) * 300)` | `-66` | main_table.tex |
| `\phm{-8}` | `r2_compose_0.5b.json` | `sum_t round((.runs.residual_damage_k2.methods.copy_update[t] - plain_skip[t]) * 100)` | `-8` | main_table.tex |
| `\phm{0.0}` | `r0_checks_0.5b.json` | `.1_dense_equality.max_abs_logit_diff` | `0` | experiments_appx.tex |
| `\phm{0.003125}` | `noise_audit.json` | `.bonferroni.alpha_per_test` | `0.003125` | experiments_appx.tex |
| `\phm{0.01}` | `ridge_analysis_0.5b.json` | `.selected_ridge` | `0.01` | experiments_appx.tex |
| `\phm{0.03}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.2048.derived.depth_ar_overhead_vs_plain_skip_pct` | `0.03206` | experiments.tex |
| `\phm{0.4034}` | `r4_headline_7b.json` | `.runs.residual_damage_k4: plain_skip.wikitext2_nll - dense_nll` | `0.4034` | experiments.tex |
| `\phm{0.57}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.512.depth_ar.iqr_ms` | `0.5688` | experiments_appx.tex |
| `\phm{0.64}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.512.derived.depth_ar_overhead_vs_plain_skip_pct` | `0.6442` | abstract.tex, conclusion.tex, experiments.tex, introduction.tex |
| `\phm{0.8}` | `noise_audit.json` | `.bonferroni.note (expected false positives, uncorrected, m=16)` | `0.8` | experiments_appx.tex |
| `\phm{0.90}` | `r1_layerscan_0.5b.json` | `.layers.3.P_heldout.depth_ar1` | `0.9028` | fig1_predictability.tex, fig1a_appendix.tex |
| `\phm{0.946}` | `r1_analysis_0.5b.json` | `.paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.p_value` | `0.9463` | fig1_predictability.tex |
| `\phm{0.95}` | `r1_analysis_0.5b.json` | `.paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.p_value` | `0.9463` | experiments.tex, introduction.tex |
| `\phm{1.0}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.2048: depth_ar.median_ms - plain_skip.median_ms` | `0.9964` | experiments_appx.tex |
| `\phm{1.141}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.512.derived.speedup_depth_ar_vs_dense` | `1.141` | experiments.tex |
| `\phm{1.148}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.512.derived.speedup_plain_vs_dense` | `1.148` | experiments.tex |
| `\phm{1.18}` | `noise_audit.json` | `.rows[7B/residual_damage/k4/depth_ar].z_abs_delta_over_se` | `1.182` | experiments.tex, main_table.tex |
| `\phm{1.19}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.512.plain_skip.iqr_ms` | `1.194` | experiments_appx.tex |
| `\phm{1.7 \times 10^{3}}` | `r0_checks_0.5b.json` | `.4_boundary_capture.hidden_scale` | `1717` | experiments_appx.tex |
| `\phm{1.95}` | `noise_audit.json` | `.rows[0.5B/recovery_top/k2/depth_ar].z_abs_delta_over_se` | `1.949` | experiments_appx.tex |
| `\phm{1.98}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.dense.wikitext2_nll` | `1.978` | main_table.tex |
| `\phm{10}` | `latency_Qwen2.5-7B.json` | `.config.warmup` | `10` | experiments_appx.tex |
| `\phm{10.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.recovery.depth_ar.gap_recovered_nll` | `10.29` | experiments.tex |
| `\phm{100}` | `noise_audit.json` | `.rows[0.5B/*].n_examples_per_task` | `100` | experiments.tex, experiments_appx.tex |
| `\phm{1024}` | `r3_verify_1.5b.json` | `.config.seq_len` | `1024` | experiments_appx.tex |
| `\phm{11.01}` | `ridge_analysis_0.5b.json` | `.by_ridge["0.0"].layer2_nll_dev` | `11.01` | experiments.tex |
| `\phm{13}` | `r1_analysis_0.5b.json` | `.paper_cited_stats.alpha_ar1_negative_in_layers_4_16.n_negative` | `13` | experiments_appx.tex |
| `\phm{132}` | `noise_audit.json` | `.rows[1.5B/recovery_top/k2/depth_ar].net_questions_vs_plain_skip` | `132` | abstract.tex, experiments.tex, experiments_appx.tex, introduction.tex |
| `\phm{14}` | `noise_audit.json` | `.depth_ar_accuracy_deltas_NOT_significant_at_95pct` | `14` | experiments_appx.tex |
| `\phm{16}` | `r2_compose_0.5b.json` | `.config.n_calib_seqs` | `16` | abstract.tex, experiments.tex, experiments_appx.tex, introduction.tex |
| `\phm{192}` | `r0_checks_0.5b.json` | `.5_padding_excluded.n_tokens_expected` | `192` | experiments_appx.tex |
| `\phm{2}` | `noise_audit.json` | `.bonferroni.n_significant` | `2` | experiments.tex, experiments_appx.tex, introduction.tex |
| `\phm{2.11}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.depth_ar.wikitext2_nll` | `2.111` | main_table.tex |
| `\phm{2.12}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.plain_skip.wikitext2_nll` | `2.122` | main_table.tex |
| `\phm{2.29}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.copy_update.wikitext2_nll` | `2.29` | main_table.tex |
| `\phm{2.33}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.dense.wikitext2_nll` | `2.33` | experiments.tex, experiments_appx.tex, introduction.tex, main_table.tex |
| `\phm{2.36}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.depth_ar1.wikitext2_nll` | `2.359` | main_table.tex |
| `\phm{2.38}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.plain_skip.wikitext2_nll` | `2.382` | main_table.tex |
| `\phm{2.46}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.depth_ar1.wikitext2_nll` | `2.458` | main_table.tex |
| `\phm{2.47}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.wikitext2_nll` | `2.469` | main_table.tex |
| `\phm{2.71}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.depth_ar1.wikitext2_nll` | `2.714` | main_table.tex |
| `\phm{2.73}` | `ridge_analysis_0.5b.json` | `.dense_nll_dev` | `2.728` | experiments.tex |
| `\phm{2.75}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.plain_skip.wikitext2_nll` | `2.752` | main_table.tex |
| `\phm{2.76}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.dense.wikitext2_nll` | `2.763` | main_table.tex |
| `\phm{2.83}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.copy_update.wikitext2_nll` | `2.825` | main_table.tex |
| `\phm{2.95}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.copy_update.wikitext2_nll` | `2.948` | main_table.tex |
| `\phm{2.96}` | `noise_audit.json` | `.bonferroni.z_threshold` | `2.955` | experiments_appx.tex, main_table.tex |
| `\phm{2.97}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.depth_ar1.wikitext2_nll` | `2.974` | main_table.tex |
| `\phm{2.98}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.wikitext2_nll` | `2.985` | main_table.tex |
| `\phm{22}` | `r1_analysis_0.5b.json` | `.paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.n` | `22` | experiments.tex, fig1_predictability.tex, introduction.tex, main_table.tex |
| `\phm{23.3}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.recovery.depth_ar.gap_recovered_nll` | `23.25` | abstract.tex, experiments.tex, experiments_appx.tex, introduction.tex |
| `\phm{3.39}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.depth_ar.wikitext2_nll` | `3.391` | main_table.tex |
| `\phm{3.41}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.copy_update.wikitext2_nll` | `3.413` | main_table.tex |
| `\phm{3.42}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.plain_skip.wikitext2_nll` | `3.421` | main_table.tex |
| `\phm{3.43}` | `r3_verify_1.5b.json` | `.runs.recovery_top_k2.methods.depth_ar.wikitext2_nll` | `3.428` | experiments_appx.tex |
| `\phm{3.8 \times 10^{-6}}` | `r0_checks_0.5b.json` | `.4_boundary_capture.max_abs_err` | `3.815e-06` | experiments_appx.tex |
| `\phm{30}` | `latency_Qwen2.5-7B.json` | `.config.iters` | `30` | experiments_appx.tex |
| `\phm{300}` | `r3_verify_1.5b.json` | `.config.n_task_examples` | `300` | experiments.tex, experiments_appx.tex, main_table.tex |
| `\phm{31.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.copy_update.hellaswag` | `31` | main_table.tex |
| `\phm{32}` | `r3_verify_1.5b.json` | `.config.n_calib_seqs` | `32` | experiments_appx.tex, method.tex |
| `\phm{34.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.copy_update.hellaswag` | `34.33` | main_table.tex |
| `\phm{37.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.copy_update.arc_easy` | `37.33` | main_table.tex |
| `\phm{39.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.copy_update.hellaswag` | `39` | main_table.tex |
| `\phm{4.08}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.2048.plain_skip.iqr_ms` | `4.084` | experiments_appx.tex |
| `\phm{4.16}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.2048.depth_ar.iqr_ms` | `4.162` | experiments_appx.tex |
| `\phm{4.37}` | `noise_audit.json` | `.bonferroni.significant_rows[1].z` | `4.373` | experiments.tex, experiments_appx.tex |
| `\phm{4.46}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.copy_update.wikitext2_nll` | `4.464` | main_table.tex |
| `\phm{4.6}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.recovery.depth_ar.gap_recovered_nll` | `4.552` | abstract.tex, experiments.tex, introduction.tex |
| `\phm{4.9}` | `latency_Qwen2.5-7B.json` | `.by_seq_len.512: depth_ar.median_ms - plain_skip.median_ms` | `4.934` | experiments_appx.tex |
| `\phm{40.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.depth_ar1.hellaswag` | `40` | main_table.tex |
| `\phm{41.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.depth_ar.hellaswag` | `41` | main_table.tex |
| `\phm{42.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.plain_skip.hellaswag` | `42` | main_table.tex |
| `\phm{42.3}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.copy_update.avg_acc` | `42.33` | main_table.tex |
| `\phm{43.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.depth_ar1.hellaswag` | `43` | main_table.tex |
| `\phm{44.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.hellaswag` | `44` | main_table.tex |
| `\phm{44.1}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.copy_update.avg_acc` | `44.11` | main_table.tex |
| `\phm{46.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.depth_ar1.arc_easy` | `46` | main_table.tex |
| `\phm{47.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.copy_update.arc_easy` | `47` | main_table.tex |
| `\phm{48.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.dense.hellaswag` | `48` | main_table.tex |
| `\phm{5}` | `noise_audit.json` | `.rows[1.5B/residual_damage/k2/depth_ar].net_questions_vs_plain_skip` | `5` | experiments_appx.tex |
| `\phm{5.08}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.copy_update.wikitext2_nll` | `5.084` | main_table.tex |
| `\phm{5.99}` | `r3_verify_1.5b.json` | `.runs.recovery_top_k2.methods.plain_skip.wikitext2_nll` | `5.994` | experiments.tex, introduction.tex |
| `\phm{50.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.copy_update.avg_acc` | `50` | main_table.tex |
| `\phm{51.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.depth_ar.avg_acc` | `51` | main_table.tex |
| `\phm{51.3}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.depth_ar1.avg_acc` | `51.33` | main_table.tex |
| `\phm{51.7}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.depth_ar1.avg_acc` | `51.67` | main_table.tex |
| `\phm{512}` | `r2_compose_0.5b.json` | `.config.seq_len` | `512` | experiments_appx.tex |
| `\phm{52.3}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.plain_skip.avg_acc` | `52.33` | main_table.tex |
| `\phm{52.7}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.avg_acc` | `52.67` | main_table.tex |
| `\phm{53.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.copy_update.arc_easy` | `53` | main_table.tex |
| `\phm{54.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k4.methods.copy_update.piqa` | `54` | main_table.tex |
| `\phm{57.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.copy_update.arc_easy` | `57.33` | main_table.tex |
| `\phm{58.0}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.copy_update.hellaswag` | `58` | main_table.tex |
| `\phm{58.7}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.dense.avg_acc` | `58.67` | main_table.tex |
| `\phm{59.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.copy_update.arc_easy` | `59` | main_table.tex |
| `\phm{6.45}` | `noise_audit.json` | `.bonferroni.significant_rows[0].z` | `6.454` | experiments.tex, experiments_appx.tex |
| `\phm{60.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.dense.arc_easy` | `60` | main_table.tex |
| `\phm{60.1}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.copy_update.avg_acc` | `60.11` | main_table.tex |
| `\phm{60.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.copy_update.piqa` | `60.67` | main_table.tex |
| `\phm{61.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.hellaswag` | `61.67` | main_table.tex |
| `\phm{62.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.depth_ar1.hellaswag` | `62.67` | main_table.tex |
| `\phm{63.4}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.depth_ar.avg_acc` | `63.44` | main_table.tex |
| `\phm{63.6}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.depth_ar1.avg_acc` | `63.56` | main_table.tex |
| `\phm{63.8}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.copy_update.avg_acc` | `63.78` | main_table.tex |
| `\phm{63.9}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.plain_skip.avg_acc` | `63.89` | main_table.tex |
| `\phm{64.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.copy_update.piqa` | `64` | main_table.tex |
| `\phm{66.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.piqa` | `66` | main_table.tex |
| `\phm{66.3}` | `r3_verify_1.5b.json` | `.runs.recovery_top_k4.recovery.depth_ar.gap_recovered_nll` | `66.33` | experiments.tex |
| `\phm{67.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.copy_update.avg_acc` | `67` | main_table.tex |
| `\phm{67.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.dense.hellaswag` | `67.33` | main_table.tex |
| `\phm{67.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.depth_ar.arc_easy` | `67.67` | main_table.tex |
| `\phm{68.0}` | `r2_compose_0.5b.json` | `.runs.residual_damage_k2.methods.dense.piqa` | `68` | main_table.tex |
| `\phm{68.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.avg_acc` | `68.33` | main_table.tex |
| `\phm{68.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.depth_ar1.avg_acc` | `68.67` | main_table.tex |
| `\phm{68.9}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.depth_ar.avg_acc` | `68.89` | main_table.tex |
| `\phm{69.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.plain_skip.hellaswag` | `69` | main_table.tex |
| `\phm{7.31}` | `r3_verify_1.5b.json` | `.runs.recovery_top_k4.methods.plain_skip.wikitext2_nll` | `7.313` | experiments.tex |
| `\phm{70.0}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.arc_easy` | `70` | abstract.tex, experiments.tex, experiments_appx.tex, introduction.tex, main_table.tex |
| `\phm{70.3}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.depth_ar.hellaswag` | `70.33` | main_table.tex |
| `\phm{70.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.depth_ar.arc_easy` | `70.67` | main_table.tex |
| `\phm{71.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.plain_skip.arc_easy` | `71` | main_table.tex |
| `\phm{71.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.dense.avg_acc` | `71.33` | main_table.tex |
| `\phm{71.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.depth_ar.piqa` | `71.67` | main_table.tex |
| `\phm{72.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.depth_ar1.piqa` | `72.33` | main_table.tex |
| `\phm{72.6}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.plain_skip.avg_acc` | `72.56` | main_table.tex |
| `\phm{72.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k4.methods.plain_skip.piqa` | `72.67` | main_table.tex |
| `\phm{73.0}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.dense.arc_easy` | `73` | main_table.tex |
| `\phm{73.1}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.depth_ar1.avg_acc` | `73.11` | main_table.tex |
| `\phm{73.3}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.plain_skip.piqa` | `73.33` | main_table.tex |
| `\phm{73.7}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.dense.piqa` | `73.67` | main_table.tex |
| `\phm{74.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.depth_ar1.hellaswag` | `74` | main_table.tex |
| `\phm{74.3}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.plain_skip.avg_acc` | `74.33` | main_table.tex |
| `\phm{74.6}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.depth_ar1.avg_acc` | `74.56` | main_table.tex |
| `\phm{74.8}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.depth_ar.avg_acc` | `74.78` | main_table.tex |
| `\phm{75.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.depth_ar.avg_acc` | `75` | main_table.tex |
| `\phm{75.7}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.plain_skip.piqa` | `75.67` | main_table.tex |
| `\phm{76}` | `diag_channel_stats_0.5b.json` | `100*(1 - .layers.3.frac_channels_positive)` | `75.67` | experiments.tex |
| `\phm{76.0}` | `r3_verify_1.5b.json` | `.runs.residual_damage_k2.methods.copy_update.piqa` | `76` | main_table.tex |
| `\phm{77.3}` | `r4_headline_7b.json` | `.runs.residual_damage_k4.methods.depth_ar.piqa` | `77.33` | main_table.tex |
| `\phm{78.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.depth_ar.piqa` | `78` | main_table.tex |
| `\phm{78.3}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.plain_skip.piqa` | `78.33` | main_table.tex |
| `\phm{78.7}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.dense.arc_easy` | `78.67` | main_table.tex |
| `\phm{79.4}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.dense.avg_acc` | `79.44` | main_table.tex |
| `\phm{79.7}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.dense.piqa` | `79.67` | main_table.tex |
| `\phm{8}` | `latency_Qwen2.5-7B.json` | `.config.batch_size` | `8` | experiments_appx.tex |
| `\phm{80.0}` | `r4_headline_7b.json` | `.runs.residual_damage_k2.methods.dense.hellaswag` | `80` | main_table.tex |
| `\phm{88}` | `diag_channel_stats_0.5b.json` | `100*(1 - mean(.layers.4..16.frac_channels_positive))` | `88.35` | experiments_appx.tex |
| `\phm{896}` | `diag_channel_stats_0.5b.json` | `.layers.3.d_model` | `896` | method.tex |
| `\phm{9}` | `r0_checks_0.5b.json` | `.3_manual_skip_matches.layer` | `9` | experiments_appx.tex |
| `\phm{90}` | `r1_layerscan_0.5b.json` | `100*.layers.3.P_heldout.depth_ar1` | `90.28` | experiments.tex, experiments_appx.tex, introduction.tex |
| `\phm{900}` | `noise_audit.json` | `.rows[1.5B/*].total_questions_graded` | `900` | abstract.tex, experiments.tex, introduction.tex, main_table.tex |


### Protocol-truthfulness pairing (master's additional rule)

Each `\phm{}` below is measured **under the probe protocol**: 16 calibration sequences,
WikiText-103, **NLL-only**, single-layer coefficients, 0.5B. If R2-full supersedes these,
the number **and the protocol sentence must change together**:

| Number | Protocol sentence that must move with it |
|---|---|
| `24.7` / `16.3` headline | `experiments.tex` setup: "16 sequences … for the 0.5B analysis" |
| whole `tab:selection` | its caption: "Fitted on 16 WikiText-103 sequences … 16 disjoint held-out" |
| ridge `11.01` / `2.73` | appendix §ridge: "measured on the DEV split" |

If the probe is **never** superseded, the numbers stay and are simply unwrapped — but the
setup must then describe the probe protocol, not the full one it was written to promise.

---

## `\phm{}` — MEASURED. Unwrap; do not delete.

### The headline. Atomic: all occurrences change together, in one commit.
Source: **`r2probe_0.5b.json`** (`.runs.recovery_top_k4.gap_recovered_nll`)

| Value | Occurrences | Claim | Key |
|---|---|---|---|
| `\phm{24.7}` | `abstract:21`, `introduction:84`, `experiments` | \mname repairs 24.7% of NLL damage, recovery-selected, k=4 | `.depth_ar_diag` = `+0.2465` |
| `\phm{16.3}` | `abstract:22`, `introduction:85`, `experiments` | scalar AR(1) repairs 16.3% | `.depth_ar1` = `+0.1630` |

**Invariant:** abstract, intro and experiments must always agree. A reader who catches the
abstract disagreeing with the table stops trusting the paper.

### Table `tab:selection` — all 18 cells. Source: `r2probe_0.5b.json` `.runs.*`
`predictability_{k2,k4}`, `oracle_lite_{k2,k4}`, `recovery_top_{k2,k4}` ×
{`copy_update`, `depth_ar1`, `depth_ar_diag`} → `.gap_recovered_nll`.
This table is **entirely real**. It is the paper's evidential spine.

### Analysis stats. Source: **`r1_analysis_0.5b.json`** `.paper_cited_stats.*`
| Value | Claim | Key |
|---|---|---|
| `\phm{$-0.015$}`, `\phm{0.95}`, `\phm{22}` | predictability ⊥ recoverability | `.spearman_P_ar1_vs_recovery_ar1.{rho,p_value,n}` |
| `\phm{13}` of `\phm{13}` | all mid-stack α negative | `.alpha_ar1_negative_in_layers_4_16` |
| `\phm{$+0.0009$}` | AR(2) buys nothing → appendix | `.mean_recovery_delta_ar2_minus_ar1` |

### Channel + layer facts. Source: **`diag_channel_stats_0.5b.json`**, **`r1_layerscan_0.5b.json`**
`\phm{88}`% negative channels (L4–16 `frac_channels_positive` mean `0.1165`);
`\phm{$-0.19$}` median coefficient; L3 dissection `\phm{$+1.10$}` scalar vs
`\phm{$-0.30$}` median channel, `\phm{76}`% negative; `\phm{90}`% update energy (L3
`P_heldout`); `\phm{896}` = `d_model`.

> 🚩 **Do NOT draft from `diag_channel_stats_0.5b.json`'s `.notes` field** — it asserts the
> opposite of its own data (claims sign-heterogeneity; the data shows agreement).
> `experiment` is fixing it. **Numbers only, never `.notes`.**

### R0 correctness. Source: **`r0_checks_0.5b.json`** — 6/6 pass, three bit-exact.
`\phm{0.0}` (dense equality, α=0 reduction, padding), `\phm{3.8e-6}` / `\phm{1.7e3}`
(boundary capture vs hidden scale), `\phm{192}` tokens, gap `\phm{2}`, layers 5/9/13.

---

## `\ph{}` — INVENTED (113). Land it or delete the sentence.

| Group | Where | Awaits | If it never lands |
|---|---|---|---|
| **Table 1 scale results** (106 cells) | `tables/main_table.tex` | `r3_verify_1.5b.json`, `r4_headline_7b.json` → regenerate with **`~/gen-table.py`** (one command; recomputes gap-recovered and fails loud on mismatch) | **Cut Table 1 entirely** and narrow the paper to the 0.5B analysis, which stands on its own. Persona §6 / plan §17 Pivot D. |
| **Scale gap-rec `\ph{29}`** | `experiments.tex` (¶ *holds at scale*) | same | delete the paragraph |
| **Latency `\ph{2}`%** | `abstract`, `introduction`, `experiments`, `experiments_appx` | `latency_*.json` | **delete the latency clause from all four.** Atomic. |
| **Protocol constants** `\ph{32}` (larger-model calib), `\ph{8}` batch, `\ph{10}`/`\ph{30}` iters | `method:74`, `experiments`, `experiments_appx` | `.config` block of the JSON backing each table | delete the specific figure, keep the sentence |

**The Group-D lesson, again:** the plan said 32 sequences on C4; the run actually did 16
on WikiText-103. Written-ahead protocol constants are the *quietest* way a false claim
enters a paper — they read as boring setup and nobody re-checks them. Diff every one
against the `.config` of the JSON that backs its specific table.

---

## Unwrapped claims that are still unverified (no macro guards these)

| Claim | Where | Status |
|---|---|---|
| "We evaluate on Qwen2.5-0.5B, 1.5B **and \topscale**" | `experiments.tex` setup | **AT RISK.** Only 0.5B has run. If R3/R4 do not land, this sentence is **false** and must be narrowed to the models actually evaluated. `\topscale` makes it a one-line change. |
| "WikiText-2 NLL" column header | `tables/main_table.tex` | ✅ true by master's ruling (eval moves to WikiText-2 test from R2-final). Fig 1 / R1 stay **WikiText-103** and their captions must say so. |
| "identical skipped-layer set" | both table captions | needs `skipped_layers` echoed per run. `r2probe` **does** carry it ✅; R3/R4 must too. |
| Mechanism of the per-channel win | `experiments.tex` | Deliberately **OPEN**. Two candidates tested, both refuted. Guard against a "because…" clause creeping in during any later edit. |

## Figure provenance (for the T+2:40 figure-verification fan-out)

Figures are a claim surface that **no `\phm{}` key-check touches** — a plot can lie while
every number in the prose verifies. Provenance for a verifier:

| Figure | Plot script | Reads | Hand-entered data? |
|---|---|---|---|
| `fig:momentum` (Fig 1a/1b) | `~/auto-research/plot_fig1.py` | `r1_layerscan_0.5b.json`, `diag_channel_stats_0.5b.json` | none |
| `fig:dissociation` (Fig 2) | `~/auto-research/plot_fig2.py` | `r2_compose_0.5b.json`, `r3_verify_1.5b.json`, `r4_headline_7b.json` | none — only axis cosmetics (`dense_xmax`, label offsets) |

**Both scripts load the result JSONs directly; neither carries a literal data array.**
`plot_fig2.py` already lists `r4_headline_7b.json` with a `^` marker, so the 7B series
**appears in Fig 2 automatically** once R4 writes that file — no edit needed.

**What a figure verifier should check** (the key-check cannot):
1. Does the plotted curve match the JSON it claims to read? (re-run the script; diff the PDF)
2. Does the **caption** describe what is actually drawn? (Fig 1a was originally captioned
   for an α/cosine profile that the asset does not plot — caught by *looking at it*.)
3. Does the **emphasis** follow the data, not our ownership? (master.md rule 9 — the same
   bug as unconditional-bolding, in graphical form: e.g. is our method drawn as the
   visually dominant line where it is in fact worse?)

## Pass-2 scope: what changed after the pass-1 snapshots

The 7B-latency swap (`fc40d93`) postdates the pass-1 verifier snapshots. These must be
**re-verified in pass 2 against `fc40d93`**, not against `11b0423`:

| Fact | Where | Key (`latency_Qwen2.5-7B.json`) |
|---|---|---|
| `0.64`\% overhead @512 | `experiments.tex`, `conclusion.tex` | `.by_seq_len.512.derived.depth_ar_overhead_vs_plain_skip_pct` |
| `0.03`\% overhead @2048 | `experiments.tex` | `.by_seq_len.2048.derived.depth_ar_overhead_vs_plain_skip_pct` |
| `1.141`× vs dense | `experiments.tex` | `.by_seq_len.512.derived.speedup_depth_ar_vs_dense` |
| `1.148`× plain vs dense | `experiments.tex` | `.by_seq_len.512.derived.speedup_plain_vs_dense` |
| resolvability: `4.9`\,ms vs IQR `1.19`/`0.57` | `experiments_appx.tex` | `.by_seq_len.512.{depth_ar,plain_skip}.{median_ms,iqr_ms}` |
| **sub-noise:** `1.0`\,ms vs IQR `4.08`/`4.16` | `experiments_appx.tex` | `.by_seq_len.2048.{depth_ar,plain_skip}.{median_ms,iqr_ms}` |

**The last row is the one to check hardest.** The 2048 overhead is *smaller than the
measurement spread*, and the appendix says so explicitly. A verifier should confirm the
paper does **not** anywhere present `0.03`\% as a resolved measurement — it is quoted only
alongside its own caveat. `latency_Qwen2.5-1.5B.json` is superseded and no longer cited by
any row.

## The unwrap commit (T+2:05) — what pass 2 must check

`\phm{X}` → `X`. That is the entire diff. It is a **pure macro strip**:

```bash
git show <unwrap-commit> | grep '^[-+]' | grep -v '^[-+][-+]' \
  | sed -E 's/\\phm\{([^}]*)\}/\1/g' | sort | uniq -c | sort -rn | head
```
Every `-` line must have an identical `+` counterpart after stripping. **Zero value
changes, zero prose changes.** If any number differs, the unwrap was not mechanical and
must be rejected.
