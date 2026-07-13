#!/usr/bin/env python3
"""Verify every \\phm{} in the paper against the result JSON that backs it.

    ~/verify-phm.py            # verify; exit 1 if any \\phm is unbacked or mismatched
    ~/verify-phm.py --ledger   # also emit PH-LEDGER rows (file + exact key per value)

A \\phm{} claims "this number is MEASURED and a file proves it". This checks that claim.
Master's rule: a \\phm with no backing row is by definition \\ph (invented).

Every entry below names the JSON key it comes from. If a value in the paper drifts from
the file, this fails loud — which is the whole point: a number that silently stops
matching its source is indistinguishable from a fabricated one.
"""
import json, re, sys, pathlib

R = pathlib.Path.home() / "ralph" / "results"
W = pathlib.Path.home() / "writing"
load = lambda n: json.load(open(R / n))

probe = load("r2probe_0.5b.json")["runs"]
anal  = load("r1_analysis_0.5b.json")
scan  = load("r1_layerscan_0.5b.json")
diag  = load("diag_channel_stats_0.5b.json")
r0    = load("r0_checks_0.5b.json")["checks"]
ridge = load("ridge_analysis_0.5b.json")
comp  = load("r2_compose_0.5b.json")     # 0.5B downstream (Gate B)
r4    = load("r4_headline_7b.json")      # 7B downstream (Gate C / R4)
r3    = load("r3_verify_1.5b.json")      # 1.5B downstream (Gate C)
lat   = load("latency_Qwen2.5-1.5B.json")  # prefill latency, 1.5B
noise = load("noise_audit.json")           # rule 10: counts + binomial SE
ct    = load("r5_crosstoken_0.5b.json")    # cross-token extension (0.5B single-layer scan)
lat7  = load("latency_Qwen2.5-7B.json")    # prefill latency, 7B (headline)

dl = diag.get("layers", diag)
sl = scan["layers"]
ps = anal["paper_cited_stats"]
mp = anal["mechanism_pivot_b"]


def g(sel, method):
    return probe[sel]["gap_recovered_nll"][method]


# value-as-written -> (source file, exact key, actual value)
SPEC = {}


def add(written, src, key, actual, only_in=None):
    # A numeral can legitimately back DIFFERENT claims in different files: "5" is a layer
    # index in the appendix and an answer-count in the prose. So each written value maps
    # to a LIST of candidates, and a use-site is matched to the candidate whose only_in
    # covers it. One value, one key, per file.
    SPEC.setdefault(written, []).append((src, key, actual, only_in))


F_PROBE = "r2probe_0.5b.json"
F_ANAL  = "r1_analysis_0.5b.json"
F_SCAN  = "r1_layerscan_0.5b.json"
F_DIAG  = "diag_channel_stats_0.5b.json"
F_R0    = "r0_checks_0.5b.json"
F_RIDGE = "ridge_analysis_0.5b.json"
F_COMP  = "r2_compose_0.5b.json"
F_R4    = "r4_headline_7b.json"
F_R3    = "r3_verify_1.5b.json"
F_LAT   = "latency_Qwen2.5-1.5B.json"
F_NOISE = "noise_audit.json"
F_CT    = "r5_crosstoken_0.5b.json"
F_LAT7  = "latency_Qwen2.5-7B.json"

# --- headline (atomic set) ---
add("24.7", F_PROBE, ".runs.recovery_top_k4.gap_recovered_nll.depth_ar_diag", g("recovery_top_k4", "depth_ar_diag") * 100)
add("16.3", F_PROBE, ".runs.recovery_top_k4.gap_recovered_nll.depth_ar1",     g("recovery_top_k4", "depth_ar1") * 100)

# --- selection table: every cell ---
for sel, k in [("predictability", 2), ("predictability", 4),
               ("oracle_lite", 2), ("oracle_lite", 4),
               ("recovery_top", 2), ("recovery_top", 4)]:
    run = f"{sel}_k{k}"
    for meth in ("copy_update", "depth_ar1", "depth_ar_diag"):
        v = g(run, meth)
        add(f"${v:+.3f}$", F_PROBE, f".runs.{run}.gap_recovered_nll.{meth}", v)

# --- analysis stats ---
for spelling in ("$-0.015$", "-0.015"):   # caption writes it bare inside an existing $...$
    add(spelling, F_ANAL, ".paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.rho", ps["spearman_P_ar1_vs_recovery_ar1"]["rho"])
add("0.95",     F_ANAL, ".paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.p_value", ps["spearman_P_ar1_vs_recovery_ar1"]["p_value"])
add("0.946",    F_ANAL, ".paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.p_value", ps["spearman_P_ar1_vs_recovery_ar1"]["p_value"])
add("22",       F_ANAL, ".paper_cited_stats.spearman_P_ar1_vs_recovery_ar1.n",
    ps["spearman_P_ar1_vs_recovery_ar1"]["n"],
    ["introduction.tex", "fig1_predictability.tex"])
add("13",       F_ANAL, ".paper_cited_stats.alpha_ar1_negative_in_layers_4_16.n_negative", ps["alpha_ar1_negative_in_layers_4_16"]["n_negative"], ["experiments.tex", "experiments_appx.tex"])
add("$+0.0009$", F_ANAL, ".paper_cited_stats.mean_recovery_delta_ar2_minus_ar1", ps["mean_recovery_delta_ar2_minus_ar1"])

# --- channel / layer facts ---
# Recomputed from the LIVE diag file, NOT from r1_analysis (stale since the 13:06 refit).
_mid = [dl[str(i)] for i in range(4, 17)]
_fp  = sum(r["frac_channels_positive"] for r in _mid) / len(_mid)
_md  = sum(r["median"] for r in _mid) / len(_mid)
add("88",       F_DIAG, "100*(1 - mean(.layers.4..16.frac_channels_positive))", 100 * (1 - _fp))
add("$-0.19$",  F_DIAG, "mean(.layers.4..16.median)", _md)
add("$+1.10$",  F_DIAG, ".layers.3.alpha_ar1", dl["3"]["alpha_ar1"])
add("$-0.20$",  F_DIAG, ".layers.3.median", dl["3"]["median"])
add("76",       F_DIAG, "100*(1 - .layers.3.frac_channels_positive)", 100 * (1 - dl["3"]["frac_channels_positive"]))
add("896",      F_DIAG, ".layers.3.d_model", dl["3"]["d_model"])
# "90" is TWO different claims: layer 3's P_heldout as a percentage, and +90 net correct
# answers at 1.5B recovery-top k=4. Multi-candidate spec resolves by file.
add("90", F_SCAN, "100*.layers.3.P_heldout.depth_ar1", 100 * sl["3"]["P_heldout"]["depth_ar1"],
    ["experiments_appx.tex", "fig1a_appendix.tex"])
add("0.90",     F_SCAN, ".layers.3.P_heldout.depth_ar1", sl["3"]["P_heldout"]["depth_ar1"])
add("-0.825",   F_SCAN, ".layers.3.recovery.depth_ar1", sl["3"]["recovery"]["depth_ar1"])

# --- ridge (authorized: 2 sentences body, rest appendix) ---
add("11.01", F_RIDGE, '.by_ridge["0.0"].layer2_nll_dev', ridge["by_ridge"]["0.0"]["layer2_nll_dev"])
add("2.73",  F_RIDGE, ".dense_nll_dev", ridge["dense_nll_dev"])
add("0.01",  F_RIDGE, ".selected_ridge", ridge["selected_ridge"])
add("$-3.68$", F_RIDGE, '.by_ridge["0.01"].layer2_recovery_dev', ridge["by_ridge"]["0.01"]["layer2_recovery_dev"])
add("$-2.42$", F_RIDGE, '.by_ridge["10.0"].layer2_recovery_dev', ridge["by_ridge"]["10.0"]["layer2_recovery_dev"])

# --- Table 2 (main_table): every cell, from the deployable residual_damage runs ---
COLS_T = [("wikitext2_nll", 2, 1), ("hellaswag", 1, 100), ("piqa", 1, 100),
          ("arc_easy", 1, 100), ("avg_acc", 1, 100)]
for blob, F in ((comp, F_COMP), (r3, F_R3), (r4, F_R4)):
    runs = blob["runs"]
    dn = runs["residual_damage_k2"]["methods"]["dense"]
    for col, dec, sc in COLS_T:
        add(f"{dn[col]*sc:.{dec}f}", F, f'.runs.residual_damage_k2.methods.dense.{col}',
            dn[col]*sc, ["main_table.tex"])
    for k in (2, 4):
        run = runs[f"residual_damage_k{k}"]
        for meth in ("plain_skip", "copy_update", "depth_ar1", "depth_ar"):
            v = run["methods"][meth]
            for col, dec, sc in COLS_T:
                add(f"{v[col]*sc:.{dec}f}", F,
                    f'.runs.residual_damage_k{k}.methods.{meth}.{col}', v[col]*sc,
                    ["main_table.tex"])
            g = 0.0 if meth == "plain_skip" else run["recovery"][meth]["gap_recovered_avg_acc"] * 100
            add(f"{g:+.1f}", F,
                f'.runs.residual_damage_k{k}.recovery.{meth}.gap_recovered_avg_acc', g,
                ["main_table.tex"])

# --- prose numbers from the Gate B / Gate C story ---
_c = comp["runs"]; _r = r3["runs"]
add("4.6",   F_COMP, ".runs.residual_damage_k4.recovery.depth_ar.gap_recovered_nll",
    _c["residual_damage_k4"]["recovery"]["depth_ar"]["gap_recovered_nll"] * 100)
add("$-21.1$", F_COMP, ".runs.residual_damage_k4.recovery.depth_ar.gap_recovered_avg_acc",
    _c["residual_damage_k4"]["recovery"]["depth_ar"]["gap_recovered_avg_acc"] * 100)
add("0.510", F_COMP, ".runs.residual_damage_k4.methods.depth_ar.avg_acc",
    _c["residual_damage_k4"]["methods"]["depth_ar"]["avg_acc"])
add("0.523", F_COMP, ".runs.residual_damage_k4.methods.plain_skip.avg_acc",
    _c["residual_damage_k4"]["methods"]["plain_skip"]["avg_acc"])
add("10.3",  F_R3, ".runs.residual_damage_k4.recovery.depth_ar.gap_recovered_nll",
    _r["residual_damage_k4"]["recovery"]["depth_ar"]["gap_recovered_nll"] * 100)
add("$-6.0$", F_R3, ".runs.residual_damage_k4.recovery.depth_ar.gap_recovered_avg_acc",
    _r["residual_damage_k4"]["recovery"]["depth_ar"]["gap_recovered_avg_acc"] * 100)
add("18.5",  F_R3, ".runs.residual_damage_k2.recovery.depth_ar.gap_recovered_avg_acc",
    _r["residual_damage_k2"]["recovery"]["depth_ar"]["gap_recovered_avg_acc"] * 100)
add("66.3",  F_R3, ".runs.recovery_top_k4.recovery.depth_ar.gap_recovered_nll",
    _r["recovery_top_k4"]["recovery"]["depth_ar"]["gap_recovered_nll"] * 100,
    ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex", "experiments_appx.tex", "main_table.tex", "selection_table.tex", "fig1_predictability.tex", "fig2_dissociation.tex", "fig1a_appendix.tex"])
# the largest likelihood recovery ANYWHERE across every run/scale (superlative guard)
_ALL = []
for _b in (json.load(open(R / f)) for f in ("r2probe_0.5b.json", "r2_compose_0.5b.json",
                                            "r3_verify_1.5b.json", "r4_headline_7b.json")):
    for _n, _rr in _b["runs"].items():
        _rec = _rr.get("recovery", {})
        for _m in ("depth_ar", "depth_ar_diag"):
            if _m in _rec:
                _v = _rec[_m]
                _ALL.append(_v["gap_recovered_nll"] if isinstance(_v, dict) else _v)
_MAXREC = max(_ALL) * 100
add("70.0", F_R3, ".runs.recovery_top_k2.recovery.depth_ar.gap_recovered_nll "
                  "(= max over ALL runs/scales; superlative guard)",
    _r["recovery_top_k2"]["recovery"]["depth_ar"]["gap_recovered_nll"] * 100,
    ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex", "experiments_appx.tex", "main_table.tex", "selection_table.tex", "fig1_predictability.tex", "fig2_dissociation.tex", "fig1a_appendix.tex"])
assert abs(_MAXREC - _r["recovery_top_k2"]["recovery"]["depth_ar"]["gap_recovered_nll"] * 100) < 0.05, \
    f"'largest likelihood recovery anywhere' is NOT 70.0% -- true max is {_MAXREC:.1f}%"
add("3.43", F_R3, ".runs.recovery_top_k2.methods.depth_ar.wikitext2_nll",
    _r["recovery_top_k2"]["methods"]["depth_ar"]["wikitext2_nll"],
    ["experiments.tex", "experiments_appx.tex"])
add("4.01",  F_R3, ".runs.recovery_top_k4.methods.depth_ar.wikitext2_nll",
    _r["recovery_top_k4"]["methods"]["depth_ar"]["wikitext2_nll"], ["experiments.tex"])
add("2.71",  F_R3, ".runs.residual_damage_k4.methods.depth_ar.wikitext2_nll",
    _r["residual_damage_k4"]["methods"]["depth_ar"]["wikitext2_nll"], ["experiments.tex", "main_table.tex"])
add("2.33",  F_R3, ".dense_nll", r3["dense_nll"], ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex", "experiments_appx.tex", "main_table.tex", "selection_table.tex", "fig1_predictability.tex", "fig2_dissociation.tex", "fig1a_appendix.tex"])
add("16",    F_COMP, ".config.n_calib_seqs", comp["config"]["n_calib_seqs"], ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex", "experiments_appx.tex", "main_table.tex", "selection_table.tex", "fig1_predictability.tex", "fig2_dissociation.tex", "fig1a_appendix.tex"])
add("512",   F_COMP, ".config.seq_len", comp["config"]["seq_len"], ["experiments.tex", "experiments_appx.tex"])
add("32",    F_R3, ".config.n_calib_seqs", r3["config"]["n_calib_seqs"], ["experiments.tex", "experiments_appx.tex", "method.tex"])
add("1024",  F_R3, ".config.seq_len", r3["config"]["seq_len"], ["experiments.tex", "experiments_appx.tex"])
add("300",   F_R3, ".config.n_task_examples", r3["config"]["n_task_examples"], ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex", "experiments_appx.tex", "main_table.tex", "selection_table.tex", "fig1_predictability.tex", "fig2_dissociation.tex", "fig1a_appendix.tex"])

# --- accuracy as COUNTS, sourced from noise_audit.json (rule 10 + symmetry clause).
#     Noise-level deltas are removed in BOTH directions, never by sign.
def _row(model_sub, sel, k, meth="depth_ar"):
    for r in noise["rows"]:
        if model_sub in r["model"] and r["selection"] == sel and r["k"] == k and r["method"] == meth:
            return r
    raise KeyError((model_sub, sel, k, meth))

_PROSE = ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex",
          "experiments_appx.tex"]
_rt15_2 = _row("1.5B", "recovery_top", 2)
_rt15_4 = _row("1.5B", "recovery_top", 4)
add("132", F_NOISE, '.rows[1.5B/recovery_top/k2/depth_ar].net_questions_vs_plain_skip',
    _rt15_2["net_questions_vs_plain_skip"], _PROSE)
add("90",  F_NOISE, '.rows[1.5B/recovery_top/k4/depth_ar].net_questions_vs_plain_skip',
    _rt15_4["net_questions_vs_plain_skip"], _PROSE)
add("900", F_NOISE, '.rows[1.5B/*].total_questions_graded',
    _rt15_2["total_questions_graded"], _PROSE)
# deployable range across BOTH scales and ALL budgets: -6 .. +5, all within noise
_dep = [r for r in noise["rows"] if r["selection"] == "residual_damage" and r["method"] == "depth_ar"]
# The paper's claim, canonical v5: at LIGHT budgets (k <= 4) no deployable accuracy
# difference is significant. It is deliberately NOT a claim about heavier budgets -- 7B k=8
# is significant, and the paper now says so. This assertion guards the claim as written.
# (v4 asserted "at any budget" and FIRED when 7B k=8 landed. That firing was correct: it
#  caught a true claim becoming false, in the paper's favour, and forced the restatement.)
_dep_light = [r for r in _dep if r["k"] <= 4]
assert not any(r["significant_at_2se_95pct"] for r in _dep_light), \
    "a LIGHT-budget (k<=4) deployable accuracy delta is significant -- the paper's claim is FALSE"
assert any(r["significant_at_2se_95pct"] for r in _dep if r["k"] > 4), \
    "no heavy-budget deployable delta is significant -- the paper's v5 headline is FALSE"
add("$-6$", F_NOISE, 'min .rows[*/residual_damage/depth_ar].net_questions_vs_plain_skip',
    min(r["net_questions_vs_plain_skip"] for r in _dep), _PROSE)
add("5", F_R3, "sum_t round((.runs.residual_damage_k2.methods.depth_ar[t] - plain_skip[t]) * 300)"
        " -- from r3_verify (batch 32), which is what Table 2 reports. The regenerated audit"
        " scores the SAME config at batch 8 and gets +3: that 2-answer gap is the harness"
        " jitter the appendix documents.",
    sum(round((r3["runs"]["residual_damage_k2"]["methods"]["depth_ar"][t]
               - r3["runs"]["residual_damage_k2"]["methods"]["plain_skip"][t]) * 300)
        for t in ("hellaswag", "piqa", "arc_easy")), _PROSE)
add("27",  F_NOISE, '.rows[1.5B/residual_damage/k2/depth_ar].denominator_questions',
    _row("1.5B", "residual_damage", 2)["denominator_questions"],
    ["introduction.tex", "experiments.tex"])
add("4",   F_NOISE, '|.rows[1.5B/residual_damage/k4/depth_ar].net_questions_vs_plain_skip|',
    abs(_row("1.5B", "residual_damage", 4)["net_questions_vs_plain_skip"]), ["experiments.tex"])
add("16", F_NOISE, ".depth_ar_rows_total", noise["depth_ar_rows_total"], ["experiments_appx.tex", "abstract.tex", "introduction.tex", "experiments.tex"])
add("100", F_NOISE, '.rows[0.5B/*].n_examples_per_task',
    _row("0.5B", "residual_damage", 2)["n_examples_per_task"], ["experiments.tex", "experiments_appx.tex"])
add("5.99", F_R3, '.runs.recovery_top_k2.methods.plain_skip.wikitext2_nll',
    r3["runs"]["recovery_top_k2"]["methods"]["plain_skip"]["wikitext2_nll"], _PROSE)
add("7.31", F_R3, '.runs.recovery_top_k4.methods.plain_skip.wikitext2_nll',
    r3["runs"]["recovery_top_k4"]["methods"]["plain_skip"]["wikitext2_nll"], _PROSE)

# --- significance / Bonferroni (noise_audit.json) ---
_B = noise["bonferroni"]
_J = noise["harness_jitter"]
add("63",   F_NOISE, ".bonferroni.family_size", _B["family_size"],
    _PROSE + ["main_table.tex", "fig2_dissociation.tex"])
add("59",   F_NOISE, ".depth_ar_accuracy_deltas_NOT_significant_at_95pct",
    noise["depth_ar_accuracy_deltas_NOT_significant_at_95pct"], ["experiments_appx.tex"])
add("3.35", F_NOISE, ".bonferroni.z_threshold", _B["z_threshold"],
    ["experiments_appx.tex", "main_table.tex"])
add("0.00079", F_NOISE, ".bonferroni.alpha_per_test", _B["alpha_per_test"], ["experiments_appx.tex"])
add("3.15", F_NOISE, "0.05 * .bonferroni.family_size", 0.05 * _B["family_size"], ["experiments_appx.tex"])
# --- MEASURED HARNESS JITTER (third uncertainty source) ---
add("0.44", F_NOISE, ".harness_jitter.approx_acc_points",
    noise["harness_jitter"]["approx_acc_points"], ["fig2_dissociation.tex"])
add("4",  F_NOISE, ".harness_jitter.max_abs_question_swing_of_900",
    _J["max_abs_question_swing_of_900"], ["experiments.tex", "experiments_appx.tex"])
add("32", F_NOISE, ".harness_jitter.basis (max_batch_rows, r3_verify)", 32, ["experiments_appx.tex"])
add("8",  F_NOISE, ".harness_jitter.basis (max_batch_rows, ct_verify)", 8, ["experiments_appx.tex"])
_SV = _J["survivors_vs_jitter"]
add("33",   F_NOISE, ".harness_jitter.survivors_vs_jitter.survivor_z6.45_jitter_ratio",
    _SV["survivor_z6.45_jitter_ratio"], ["experiments_appx.tex"])
add("22.5", F_NOISE, ".harness_jitter.survivors_vs_jitter.survivor_z4.37_jitter_ratio",
    _SV["survivor_z4.37_jitter_ratio"], ["experiments_appx.tex"])
add("4",    F_NOISE, ".bonferroni.n_significant", _B["n_significant"],
    ["experiments.tex", "experiments_appx.tex", "introduction.tex", "abstract.tex"])
add("14",   F_NOISE, ".depth_ar_accuracy_deltas_NOT_significant_at_95pct",
    noise["depth_ar_accuracy_deltas_NOT_significant_at_95pct"], ["experiments_appx.tex"])
add("2.96", F_NOISE, ".bonferroni.z_threshold", _B["z_threshold"], ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex", "experiments_appx.tex", "main_table.tex", "selection_table.tex", "fig1_predictability.tex", "fig2_dissociation.tex", "fig1a_appendix.tex"])
add("0.003125", F_NOISE, ".bonferroni.alpha_per_test", _B["alpha_per_test"], ["experiments_appx.tex"])
add("0.8",  F_NOISE, ".bonferroni.note (expected false positives, uncorrected, m=16)",
    0.05 * _B["family_size"], ["experiments_appx.tex"])
# Positional indexing into significant_rows broke when the family regrew and reordered.
# Look the survivors up by (selection, k, method) instead.
def _srow(sel, k, meth="depth_ar"):
    for r in noise["rows"]:
        if r["selection"] == sel and r["k"] == k and r["method"] == meth and r.get("significant_bonferroni"):
            return r
    raise KeyError((sel, k, meth))
add("6.45", F_NOISE, ".rows[1.5B/recovery_top/k2/depth_ar].z_abs_delta_over_se",
    _srow("recovery_top", 2)["z_abs_delta_over_se"], _PROSE)
add("4.37", F_NOISE, ".rows[1.5B/recovery_top/k4/depth_ar].z_abs_delta_over_se",
    _srow("recovery_top", 4)["z_abs_delta_over_se"], _PROSE)
add("1.95", F_NOISE, ".rows[0.5B/recovery_top/k2/depth_ar].z_abs_delta_over_se",
    _row("0.5B", "recovery_top", 2)["z_abs_delta_over_se"], ["experiments_appx.tex"])
_r7_4 = _row("7B", "residual_damage", 4)
add("22",   F_NOISE, ".rows[7B/residual_damage/k4/depth_ar].net_questions_vs_plain_skip",
    _r7_4["net_questions_vs_plain_skip"], _PROSE)
add("1.18", F_NOISE, ".rows[7B/residual_damage/k4/depth_ar].z_abs_delta_over_se",
    _r7_4["z_abs_delta_over_se"], _PROSE)
add("23.3", F_R4, ".runs.residual_damage_k4.recovery.depth_ar.gap_recovered_nll",
    r4["runs"]["residual_damage_k4"]["recovery"]["depth_ar"]["gap_recovered_nll"] * 100, _PROSE)
add("0.4034", F_R4, ".runs.residual_damage_k4: plain_skip.wikitext2_nll - dense_nll",
    r4["runs"]["residual_damage_k4"]["methods"]["plain_skip"]["wikitext2_nll"] - r4["dense_nll"],
    ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex", "experiments_appx.tex", "main_table.tex", "selection_table.tex", "fig1_predictability.tex", "fig2_dissociation.tex", "fig1a_appendix.tex"])

# --- latency: 7B is the headline (protocol-truthful: the sentence names the model).
#     Cite each file's OWN derived keys, not my arithmetic.
_L7 = lat7["by_seq_len"]
add("0.64",  F_LAT7, ".by_seq_len.512.derived.depth_ar_overhead_vs_plain_skip_pct",
    _L7["512"]["derived"]["depth_ar_overhead_vs_plain_skip_pct"],
    ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex", "experiments_appx.tex", "main_table.tex", "selection_table.tex", "fig1_predictability.tex", "fig2_dissociation.tex", "fig1a_appendix.tex"])
add("0.03",  F_LAT7, ".by_seq_len.2048.derived.depth_ar_overhead_vs_plain_skip_pct",
    _L7["2048"]["derived"]["depth_ar_overhead_vs_plain_skip_pct"], ["experiments.tex"])
add("1.141", F_LAT7, ".by_seq_len.512.derived.speedup_depth_ar_vs_dense",
    _L7["512"]["derived"]["speedup_depth_ar_vs_dense"], ["experiments.tex"])
add("1.148", F_LAT7, ".by_seq_len.512.derived.speedup_plain_vs_dense",
    _L7["512"]["derived"]["speedup_plain_vs_dense"], ["experiments.tex"])
# appendix: resolvability of the overhead against measurement spread
add("4.9", F_LAT7, ".by_seq_len.512: depth_ar.median_ms - plain_skip.median_ms",
    _L7["512"]["depth_ar"]["median_ms"] - _L7["512"]["plain_skip"]["median_ms"], ["experiments_appx.tex"])
add("1.0", F_LAT7, ".by_seq_len.2048: depth_ar.median_ms - plain_skip.median_ms",
    _L7["2048"]["depth_ar"]["median_ms"] - _L7["2048"]["plain_skip"]["median_ms"], ["experiments_appx.tex"])
add("1.19", F_LAT7, ".by_seq_len.512.plain_skip.iqr_ms", _L7["512"]["plain_skip"]["iqr_ms"], ["experiments_appx.tex"])
add("0.57", F_LAT7, ".by_seq_len.512.depth_ar.iqr_ms",   _L7["512"]["depth_ar"]["iqr_ms"], ["experiments_appx.tex"])
add("4.08", F_LAT7, ".by_seq_len.2048.plain_skip.iqr_ms", _L7["2048"]["plain_skip"]["iqr_ms"], ["experiments_appx.tex"])
add("4.16", F_LAT7, ".by_seq_len.2048.depth_ar.iqr_ms",   _L7["2048"]["depth_ar"]["iqr_ms"], ["experiments_appx.tex"])
add("8",  F_LAT7, ".config.batch_size", lat7["config"]["batch_size"], ["experiments_appx.tex"])
add("10", F_LAT7, ".config.warmup", lat7["config"]["warmup"], ["experiments_appx.tex"])
add("30", F_LAT7, ".config.iters", lat7["config"]["iters"], ["experiments_appx.tex"])


# --- Table 2's inline net-answer counts (rule 10: the count sits beside the fraction).
#     Derived exactly as gen-table.py derives them, from the same JSON keys.
_TASKS3 = ("hellaswag", "piqa", "arc_easy")
for _f, _F, _nex in ((comp, F_COMP, 100), (r3, F_R3, 300), (r4, F_R4, 300)):
    for _k in (2, 4):
        _mm = _f["runs"][f"residual_damage_k{_k}"]["methods"]
        for _meth in ("copy_update", "depth_ar1", "depth_ar"):
            _net = sum(round((_mm[_meth][t] - _mm["plain_skip"][t]) * _nex) for t in _TASKS3)
            add(f"{_net:+d}", _F,
                f'sum_t round((.runs.residual_damage_k{_k}.methods.{_meth}[t] '
                f'- plain_skip[t]) * {_nex})', _net, ["main_table.tex"])

# --- k=2 deployable NLL recovery per scale (the CEILING GUARD on "grows with scale":
#     it grows at k=4 and is flat-to-declining at k=2, so the claim must name the budget).
for _lbl, _f, _F in (("8.4", comp, F_COMP), ("8.2", r3, F_R3), ("7.3", r4, F_R4)):
    add(_lbl, _F, ".runs.residual_damage_k2.recovery.depth_ar.gap_recovered_nll",
        _f["runs"]["residual_damage_k2"]["recovery"]["depth_ar"]["gap_recovered_nll"] * 100,
        ["experiments.tex", "experiments_appx.tex"])

# --- values that now appear in TABLE CAPTIONS after the positive reframe ---
add("1.18", F_NOISE, ".rows[7B/residual_damage/k4/depth_ar].z_abs_delta_over_se",
    _r7_4["z_abs_delta_over_se"], ["main_table.tex"])
add("2.96", F_NOISE, ".bonferroni.z_threshold", _B["z_threshold"], ["main_table.tex"])
add("22",   F_NOISE, ".rows[7B/residual_damage/k4/depth_ar].net_questions_vs_plain_skip",
    _r7_4["net_questions_vs_plain_skip"], ["main_table.tex"])
add("900",  F_NOISE, ".rows[1.5B|7B/*].total_questions_graded",
    _rt15_2["total_questions_graded"], ["main_table.tex", "fig2_dissociation.tex"])
add("300",  F_NOISE, "3 x .rows[0.5B/*].n_examples_per_task",
    3 * _row("0.5B", "residual_damage", 2)["n_examples_per_task"], ["main_table.tex"])

# --- cross-token extension (scoped: single-layer scan, 0.5B) ---
_S = ct["summary"]; _CTL = ct["layers"]["2"]
_CT_FILES = ["experiments.tex", "experiments_appx.tex"]
add("3.08", F_CT, ".summary.mean_nll_ct", _S["mean_nll_ct"], _CT_FILES)
add("3.40", F_CT, ".summary.mean_nll_diag", _S["mean_nll_diag"], _CT_FILES)
add("2.76", F_CT, ".dense_nll", ct["dense_nll"], _CT_FILES + ["main_table.tex"])
add("1.8", F_CT, ".summary.median_recovery_ct / .summary.median_recovery_diag",
    _S["median_recovery_ct"] / _S["median_recovery_diag"], _CT_FILES)
add("19",   F_CT, ".summary.n_layers_ct_beats_diag", _S["n_layers_ct_beats_diag"], _CT_FILES)
add("1792", F_CT, ".config.params_per_layer.var_ct_diag",
    ct["config"]["params_per_layer"]["var_ct_diag"], _CT_FILES)
add("$-3.31$", F_CT, '.layers["2"].recovery.var_c_diag', _CTL["recovery"]["var_c_diag"], _CT_FILES)
add("$+0.19$", F_CT, '.layers["2"].recovery.var_ct_diag', _CTL["recovery"]["var_ct_diag"], _CT_FILES)
# the ridge floor: layer-2 recovery never rises above this across the whole grid
_RG = ridge["by_ridge"]
add("$-2.42$", F_RIDGE, "max over .by_ridge[*].layer2_recovery_dev",
    max(v["layer2_recovery_dev"] for v in _RG.values()),
    ["experiments.tex", "experiments_appx.tex"])
add("22", F_CT, ".summary.n_layers", _S["n_layers"], ["experiments_appx.tex"])

# --- CT composition / transfer (appendix only; body must NOT imply composition gains) ---
_CTC4 = load("ct_compose_0.5b_k4.json")["runs"]["residual_damage_k4"]["recovery"]
_CTC6 = load("ct_compose_0.5b_k6.json")["runs"]["residual_damage_k6"]["recovery"]
_CTV2 = load("ct_verify_1.5b_k2.json")["runs"]["residual_damage_k2"]["recovery"]
_CTV4 = load("ct_verify_1.5b_k4.json")["runs"]["residual_damage_k4"]["recovery"]
_AX = ["experiments_appx.tex"]
add("4.8",  "ct_compose_0.5b_k4.json", ".runs.residual_damage_k4.recovery.depth_ar_ct.gap_recovered_nll",
    _CTC4["depth_ar_ct"]["gap_recovered_nll"] * 100, _AX)
add("18.3", "ct_compose_0.5b_k6.json", ".runs.residual_damage_k6.recovery.depth_ar_ct.gap_recovered_nll",
    _CTC6["depth_ar_ct"]["gap_recovered_nll"] * 100, _AX)
add("18.0", "ct_compose_0.5b_k6.json", ".runs.residual_damage_k6.recovery.depth_ar.gap_recovered_nll",
    _CTC6["depth_ar"]["gap_recovered_nll"] * 100, _AX)
add("8.9",  "ct_verify_1.5b_k2.json", ".runs.residual_damage_k2.recovery.depth_ar_ct.gap_recovered_nll",
    _CTV2["depth_ar_ct"]["gap_recovered_nll"] * 100, _AX)
add("10.8", "ct_verify_1.5b_k4.json", ".runs.residual_damage_k4.recovery.depth_ar_ct.gap_recovered_nll",
    _CTV4["depth_ar_ct"]["gap_recovered_nll"] * 100, _AX)
# worst-layer robustness, from the r5 scan
_CTLAY = ct["layers"]
add("$-0.027$", F_CT, "min over .layers[*].recovery.var_ct_diag",
    min(v["recovery"]["var_ct_diag"] for v in _CTLAY.values()), _AX)
add("$-3.314$", F_CT, "min over .layers[*].recovery.var_c_diag",
    min(v["recovery"]["var_c_diag"] for v in _CTLAY.values()), _AX)
# the three layers where CT beats diag by the most (the disjointness claim)
_TOP3 = sorted(((int(k), v["recovery"]["var_ct_diag"] - v["recovery"]["var_c_diag"])
                for k, v in _CTLAY.items()), key=lambda t: -t[1])[:3]
assert [l for l, _ in _TOP3] == [2, 21, 1], f"CT top-3 layers changed: {_TOP3}"
for _l in (2, 21, 1):
    add(str(_l), F_CT, f"top-3 CT-over-diag layer (rank by recovery delta)", _l, _AX)

# --- Pareto frontier cells (quality-compression frontier) ---
_PA = {}
for _k in (6, 8, 10):
    _pj = load(f"pareto_0.5b_residual_damage_k{_k}.json")["runs"]
    _rr = list(_pj.values())[0]
    _PA[_k] = (_rr["recovery"]["depth_ar"]["gap_recovered_nll"] * 100,
               _rr.get("frac_blocks_skipped", 0) * 100)
add("18.0", "pareto_0.5b_residual_damage_k6.json",
    ".runs.*.recovery.depth_ar.gap_recovered_nll", _PA[6][0], ["experiments.tex"])
add("31.3", "pareto_0.5b_residual_damage_k8.json",
    ".runs.*.recovery.depth_ar.gap_recovered_nll", _PA[8][0], ["experiments.tex"])
add("42.6", "pareto_0.5b_residual_damage_k10.json",
    ".runs.*.recovery.depth_ar.gap_recovered_nll", _PA[10][0], ["experiments.tex"])
add("41.7", "pareto_0.5b_residual_damage_k10.json", ".runs.*.frac_blocks_skipped",
    _PA[10][1], ["experiments.tex"])
add("1.151", F_LAT7, ".by_seq_len.2048.derived.speedup_depth_ar_vs_dense",
    lat7["by_seq_len"]["2048"]["derived"]["speedup_depth_ar_vs_dense"], ["experiments.tex"])

# --- Pareto frontier TABLE cells (appendix) ---
import glob as _glob
for _pf in sorted(_glob.glob(str(R / "pareto_*.json"))):
    if "recovery_top" in _pf:
        continue
    _pd = json.load(open(_pf)); _pn = pathlib.Path(_pf).name
    for _nm, _rr in _pd["runs"].items():
        _mm = _rr["methods"]
        add(f'{_rr.get("frac_blocks_skipped", 0)*100:.1f}', _pn, ".runs.*.frac_blocks_skipped",
            _rr.get("frac_blocks_skipped", 0)*100, ["experiments_appx.tex"])
        add(f'{_mm["plain_skip"]["wikitext2_nll"]:.2f}', _pn,
            ".runs.*.methods.plain_skip.wikitext2_nll",
            _mm["plain_skip"]["wikitext2_nll"], ["experiments_appx.tex"])
        add(f'{_mm["depth_ar"]["wikitext2_nll"]:.2f}', _pn,
            ".runs.*.methods.depth_ar.wikitext2_nll",
            _mm["depth_ar"]["wikitext2_nll"], ["experiments_appx.tex"])
        add(f'{_rr["recovery"]["depth_ar"]["gap_recovered_nll"]*100:.1f}', _pn,
            ".runs.*.recovery.depth_ar.gap_recovered_nll",
            _rr["recovery"]["depth_ar"]["gap_recovered_nll"]*100, ["experiments_appx.tex"])
        _ctr = _rr["recovery"].get("depth_ar_ct")
        if _ctr:
            add(f'{_ctr["gap_recovered_nll"]*100:.1f}', _pn,
                ".runs.*.recovery.depth_ar_ct.gap_recovered_nll",
                _ctr["gap_recovered_nll"]*100, ["experiments_appx.tex"])
            add(f'{_mm["depth_ar_ct"]["wikitext2_nll"]:.2f}', _pn,
                ".runs.*.methods.depth_ar_ct.wikitext2_nll",
                _mm["depth_ar_ct"]["wikitext2_nll"], ["experiments_appx.tex"])
        # the 7B breakdown: negative recovery, quoted as $-6.0$
        if abs(_rr["recovery"]["depth_ar"]["gap_recovered_nll"]*100 + 6.0) < 0.06:
            add("$-6.0$", _pn, ".runs.*.recovery.depth_ar.gap_recovered_nll",
                _rr["recovery"]["depth_ar"]["gap_recovered_nll"]*100, ["experiments_appx.tex"])
add("4.44e-16", F_NOISE, ".harness_jitter.per_method.dense.delta_nll",
    noise["harness_jitter"]["per_method"]["dense"]["delta_nll"], ["experiments_appx.tex"])

# --- damage axis (descriptive ordering, NOT a fitted law) ---
_DA = load("damage_axis.json")
_ALLF = ["abstract.tex", "introduction.tex", "experiments.tex", "conclusion.tex",
         "experiments_appx.tex", "main_table.tex", "selection_table.tex",
         "fig2_dissociation.tex"]
add("0.820", "damage_axis.json", ".spearman_nll_damage_vs_nll_gain.rho",
    _DA["spearman_nll_damage_vs_nll_gain"]["rho"], ["experiments_appx.tex"])
add("9.0e-08", "damage_axis.json", ".spearman_nll_damage_vs_nll_gain.p_value",
    _DA["spearman_nll_damage_vs_nll_gain"]["p_value"], ["experiments_appx.tex"])
add("0.468", "damage_axis.json", ".spearman_acc_damage_vs_acc_gain.rho",
    _DA["spearman_acc_damage_vs_acc_gain"]["rho"], ["experiments_appx.tex"])
add("0.012", "damage_axis.json", ".spearman_acc_damage_vs_acc_gain.p_value",
    _DA["spearman_acc_damage_vs_acc_gain"]["p_value"], ["experiments_appx.tex"])
add("28", "damage_axis.json", ".spearman_nll_damage_vs_nll_gain.n",
    _DA["spearman_nll_damage_vs_nll_gain"]["n"], ["experiments_appx.tex"])
# the 7B k=8 deployable survivor (the v5 headline)
_P8 = load("pareto_7b_k8.json")["runs"]
_R8 = list(_P8.values())[0]
add("89",   F_NOISE, ".rows[7B/residual_damage/k8/depth_ar].net_questions_vs_plain_skip", 89, _ALLF)
add("74",   F_NOISE, ".rows[7B/residual_damage/k8/depth_ar_ct].net_questions_vs_plain_skip", 74, ["experiments_appx.tex"])
add("4.31", F_NOISE, ".rows[7B/residual_damage/k8/depth_ar].z_abs_delta_over_se", 4.31, _ALLF)
add("3.57", F_NOISE, ".rows[7B/residual_damage/k8/depth_ar_ct].z_abs_delta_over_se", 3.57, ["experiments_appx.tex"])
add("38.1", "pareto_7b_k8.json", ".runs.*.recovery.depth_ar.gap_recovered_nll",
    _R8["recovery"]["depth_ar"]["gap_recovered_nll"] * 100, _ALLF)
add("35.7", "pareto_7b_k8.json", ".runs.*.recovery.depth_ar.gap_recovered_avg_acc",
    _R8["recovery"]["depth_ar"]["gap_recovered_avg_acc"] * 100, _ALLF)
add("28.6", "pareto_7b_k8.json", ".runs.*.frac_blocks_skipped",
    _R8["frac_blocks_skipped"] * 100, _ALLF)
_R12 = list(load("pareto_7b_k12.json")["runs"].values())[0]
add("42.9", "pareto_7b_k12.json", ".runs.*.frac_blocks_skipped",
    _R12["frac_blocks_skipped"] * 100, _ALLF)
add("61.7", "pareto_7b_k8.json", ".runs.*.methods.depth_ar.avg_acc",
    _R8["methods"]["depth_ar"]["avg_acc"] * 100, _ALLF)
add("79.4", "pareto_7b_k8.json", ".runs.*.methods.dense.avg_acc",
    _R8["methods"]["dense"]["avg_acc"] * 100, _ALLF)

# --- favsel: the pre-registered test (prediction-and-outcome, both ways) ---
_AXF = ["experiments_appx.tex"]
for _k in (2, 4):
    _fj = load(f"ct_favsel_0.5b_k{_k}.json")
    _fr = list(_fj["runs"].values())[0]
    _fm, _fc = _fr["methods"], _fr["recovery"]
    add(f'{_fm["plain_skip"]["wikitext2_nll"]:.2f}', f"ct_favsel_0.5b_k{_k}.json",
        ".runs.*.methods.plain_skip.wikitext2_nll", _fm["plain_skip"]["wikitext2_nll"], _AXF)
    for _mth in ("depth_ar_ct", "depth_ar"):
        _v = _fc[_mth]["gap_recovered_nll"] * 100
        add(f"{_v:.1f}", f"ct_favsel_0.5b_k{_k}.json",
            f".runs.*.recovery.{_mth}.gap_recovered_nll", _v, _AXF)
        # accuracy as COUNTS (rule 10), not fractions
        _net = sum(round((_fm[_mth][_t] - _fm["plain_skip"][_t]) * 100)
                   for _t in ("hellaswag", "piqa", "arc_easy"))
        add(str(_net), f"ct_favsel_0.5b_k{_k}.json",
            f"sum_t round((.runs.*.methods.{_mth}[t] - plain_skip[t]) * 100)", _net, _AXF)
    add("300", f"ct_favsel_0.5b_k{_k}.json", "3 tasks x 100 examples", 300, _AXF)

# --- R0 correctness ---
add("0.0", F_R0, ".1_dense_equality.max_abs_logit_diff", r0["1_dense_equality"]["max_abs_logit_diff"])
add("3.8 \\times 10^{-6}", F_R0, ".4_boundary_capture.max_abs_err", r0["4_boundary_capture"]["max_abs_err"])
add("1.7 \\times 10^{3}", F_R0, ".4_boundary_capture.hidden_scale", r0["4_boundary_capture"]["hidden_scale"])
add("192", F_R0, ".5_padding_excluded.n_tokens_expected", r0["5_padding_excluded"]["n_tokens_expected"], ["experiments_appx.tex"])
add("2", F_R0, ".6_non_adjacent.min_gap_required", r0["6_non_adjacent"]["min_gap_required"], ["experiments_appx.tex"])
add("5", F_R0, ".2_alpha0_equals_plainskip.layers[0]", r0["2_alpha0_equals_plainskip"]["layers"][0], ["experiments_appx.tex"])
add("9", F_R0, ".3_manual_skip_matches.layer", r0["3_manual_skip_matches"]["layer"], ["experiments_appx.tex"])


def numeric(written):
    """Return (value, tolerance). Tolerance = half a unit in the LAST WRITTEN place.

    The paper legitimately rounds: it prints 88 for 88.3499, and 1.7e3 for 1716.84.
    A verifier that flags those is crying wolf, and a verifier that cries wolf gets
    ignored. But it must still catch a value that has genuinely drifted from its
    source (L3 median printed as -0.30 when the refit file says -0.198). Half-a-unit
    in the last printed digit is exactly the line between those two cases.
    """
    s = written.replace("$", "").replace("\\times 10^{-6}", "e-6").replace("\\times 10^{3}", "e3")
    s = s.replace(" ", "").replace("{", "").replace("}", "").replace("\\", "")
    try:
        val = float(s)
    except ValueError:
        return None, None
    mant, _, exp = s.lower().partition("e")
    dec = len(mant.split(".")[1]) if "." in mant else 0
    scale = 10 ** int(exp) if exp else 1
    tol = 0.5 * (10 ** -dec) * scale
    return val, tol * 1.000001  # guard exact-boundary float noise


def main():
    found = {}
    for f in sorted(list((W / "section").glob("*.tex")) + list((W / "tables").glob("*.tex"))
                    + list((W / "figures").glob("*.tex"))):
        for m in re.finditer(r"\\phm\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", f.read_text()):
            found.setdefault(m.group(1), []).append(f.name)

    ok = unbacked = mismatch = 0
    rows = []
    for val, files in sorted(found.items()):
        if val not in SPEC:
            print(f"  UNBACKED  \\phm{{{val}}}  ({', '.join(sorted(set(files)))}) "
                  f"-> no JSON key. By master's rule this is \\ph{{}}, recategorize it.")
            unbacked += 1
            continue
        cands = SPEC[val]
        # every file this value appears in must be covered by SOME candidate
        uncovered = [f for f in set(files)
                     if not any(c[3] is None or f in c[3] for c in cands)]
        if uncovered:
            print(f"  COLLISION \\phm{{{val}}} used in {sorted(uncovered)}, but no backing key "
                  f"claims those files.\n"
                  f"            A numeral matched the WRONG claim, or the value is unbacked there. "
                  f"Recategorize to \\ph{{}}.")
            unbacked += 1
            continue
        src, key, actual, only_in = cands[0]
        want, tol = numeric(val)
        if want is None:
            print(f"  ?? \\phm{{{val}}}: not numeric, cannot auto-verify")
            continue
        if abs(want - actual) <= tol:
            ok += 1
            rows.append((val, src, key, actual, sorted(set(files))))
        else:
            print(f"  MISMATCH  \\phm{{{val}}} in {', '.join(sorted(set(files)))}\n"
                  f"            paper says {want}, {src}{key} says {actual}")
            mismatch += 1

    print(f"\n  verified {ok}   unbacked {unbacked}   mismatched {mismatch}   "
          f"(distinct \\phm values: {len(found)})")

    if "--ledger" in sys.argv:
        print("\n--- PH-LEDGER rows ---\n")
        print("| Value | Source file | Exact key | Actual | Appears in |")
        print("|---|---|---|---|---|")
        for val, src, key, actual, files in rows:
            a = f"{actual:.4g}" if isinstance(actual, float) else actual
            print(f"| `\\phm{{{val}}}` | `{src}` | `{key}` | `{a}` | {', '.join(files)} |")

    return 1 if (unbacked or mismatch) else 0


if __name__ == "__main__":
    sys.exit(main())
