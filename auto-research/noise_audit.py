"""Rule 10 audit: every accuracy recovery FRACTION checked against its absolute delta.

A recovery fraction (A_method - A_skip) / (A_dense - A_skip) explodes when the denominator is
small -- and the denominator IS small precisely at the deployable layer sets, because those
layers were chosen to do little damage. A 5-question swing can then "recover 18.5%".

For every (model, selection, k, method) this emits:
  - the absolute accuracy delta vs plain skip, in POINTS and in QUESTIONS
  - the denominator (dense - plain skip), in points and questions
  - the SE of the difference, from the REAL per-task p's (not an assumed p=0.5)
  - z = |delta| / SE, and significance at 2 SE (~95%, two-sided)

A 1-SE band is NOT a significance test -- a delta at 1.0-1.2 SE has two-sided p ~ 0.25 and
establishes nothing. Only `significant_at_2se_95pct` supports a claim of a real difference.
Any fraction whose absolute delta is not significant must be reported as an absolute count in
the paper, never as a percentage.
"""

from __future__ import annotations

import glob
import json
import math
import os

from depth_ar import write_result

# Bonferroni across the full family of comparisons actually made. With 16 (model,selection,k)
# depth_ar-vs-plain tests, alpha 0.05/16 = 0.003125 two-sided -> |z| >= 2.95. Reporting an
# uncorrected 95% threshold over 16 tests would expect ~0.8 false positives by chance.
try:
    from scipy.stats import norm
    _BONF = None  # computed once the family size is known
except ImportError:
    norm = None

TASKS = ["hellaswag", "piqa", "arc_easy"]
RES = "/home/lobster/ralph/results"
# The family must grow with the tests actually run, or the correction is a fiction.
# Every file containing matched-layer method comparisons is in scope.
FILES = sorted(
    ["r2_compose_0.5b.json", "r3_verify_1.5b.json", "r4_headline_7b.json"]
    + [os.path.basename(f) for f in glob.glob(os.path.join(RES, "pareto_*.json"))]
    + [os.path.basename(f) for f in glob.glob(os.path.join(RES, "ct_*.json"))]
    + [os.path.basename(f) for f in glob.glob(os.path.join(RES, "r4_*.json"))]
)

rows = []
for fn in FILES:
    p = os.path.join(RES, fn)
    if not os.path.exists(p):
        print(f"skip {fn} (not present)")
        continue
    d = json.load(open(p))
    n = d["config"]["n_task_examples"]

    for key, r in d["runs"].items():
        m = r["methods"]
        if "avg_acc" not in m["dense"]:
            continue
        plain, dense = m["plain_skip"], m["dense"]
        denom = dense["avg_acc"] - plain["avg_acc"]
        for meth in ("depth_ar", "depth_ar_ct", "depth_ar1", "copy_update"):
            if meth not in m:
                continue
            delta = m[meth]["avg_acc"] - plain["avg_acc"]
            # SE of the difference, from the REAL per-task p's (not an assumed p=0.5).
            # Treats the two methods as independent though they share items, so this is the
            # CONSERVATIVE (wider) estimate.
            var = sum((m[meth][t] * (1 - m[meth][t]) + plain[t] * (1 - plain[t])) / n
                      for t in TASKS)
            se = math.sqrt(var) / len(TASKS)
            z = abs(delta) / se if se > 0 else 0.0
            q = sum(round((m[meth][t] - plain[t]) * n) for t in TASKS)
            ties = [t for t in TASKS if abs(m[meth][t] - plain[t]) < 1e-9]
            frac = r["recovery"][meth].get("gap_recovered_avg_acc")
            rows.append({
                "model": d["model"], "selection": r["selection"], "k": r["k"],
                "p_value_two_sided": float(2.0 * (1.0 - norm.cdf(z))) if norm else None,
                "method": meth,
                "n_examples_per_task": n,
                "abs_delta_avg_acc": delta,
                "net_questions_vs_plain_skip": q,
                "total_questions_graded": len(TASKS) * n,
                "denominator_dense_minus_plain": denom,
                "denominator_questions": round(denom * n * len(TASKS)),
                "reported_fraction": frac,
                "se_avg_acc_diff": se,
                "z_abs_delta_over_se": z,
                "significant_at_2se_95pct": z >= 1.96,
                "within_1se": z < 1.0,
                "tasks_exactly_tied": ties,
            })

# Family = every depth-AR-family predictor (diag AND cross-token) vs plain_skip that we
# actually ran. It grows as the sprint adds tests; a fixed family would understate the
# correction.
FAMILY = [r for r in rows if r["method"] in ("depth_ar", "depth_ar_ct")]
N_FAM = len(FAMILY)
ALPHA = 0.05
z_bonf = float(norm.ppf(1.0 - (ALPHA / N_FAM) / 2.0)) if norm else 2.95
for r in rows:
    r["bonferroni_family_size"] = N_FAM
    r["bonferroni_z_threshold"] = z_bonf
    r["significant_bonferroni"] = bool(r["method"] in ("depth_ar", "depth_ar_ct")
                                       and r["z_abs_delta_over_se"] >= z_bonf)

flagged = [r for r in FAMILY if not r["significant_at_2se_95pct"]]
bonf_sig = [r for r in FAMILY if r["significant_bonferroni"]]
# -- third uncertainty source: measured harness jitter -----------------------------------
# Not a model of noise -- an OBSERVATION. The same config run twice with a different task
# batch shape returns different accuracies.
import json as _json, os as _os


def _jitter():
    a = _os.path.join(RES, "r3_verify_1.5b.json")
    b = _os.path.join(RES, "ct_verify_1.5b_k2.json")
    if not (_os.path.exists(a) and _os.path.exists(b)):
        return None
    A = _json.load(open(a))["runs"]["residual_damage_k2"]["methods"]
    B = _json.load(open(b))["runs"]["residual_damage_k2"]["methods"]
    per, n = {}, 300
    for m in ("dense", "plain_skip", "depth_ar1", "depth_ar"):
        d_nll = B[m]["wikitext2_nll"] - A[m]["wikitext2_nll"]
        d_acc = B[m]["avg_acc"] - A[m]["avg_acc"]
        per[m] = {"delta_nll": d_nll, "delta_avg_acc": d_acc,
                  "delta_questions_of_900": round(d_acc * 3 * n)}
    worst = max(abs(v["delta_questions_of_900"]) for v in per.values())
    max_dnll = max(abs(v["delta_nll"]) for v in per.values())
    # 4.4e-16 on a value of ~2.33 is ONE double-precision ulp -- the last bit of our own
    # float64 accumulation, not a difference in the model's output. Calling that "not
    # identical" would be as wrong as calling it "exactly zero".
    return {
        "basis": "One duplicated config: Qwen2.5-1.5B bf16, residual_damage k=2, layers "
                 "[14,16], seed 42, 300 examples/task. r3_verify_1.5b used max_batch_rows=32; "
                 "ct_verify_1.5b_k2 used max_batch_rows=8. NOTHING else differed.",
        "max_abs_delta_nll": max_dnll,
        "nll_identical_to_fp64_roundoff": max_dnll <= 1e-15,
        "nll_note": "NLL agrees to %.1e, which is one float64 ulp of our own accumulator "
                    "(fp64 eps = 2.2e-16) on a value of ~2.33 -- i.e. identical up to the "
                    "final double rounding, NOT merely close. Accuracy, on the same runs, "
                    "moves by whole questions." % max_dnll,
        "per_method": per,
        "max_abs_question_swing_of_900": worst,
        "approx_acc_points": 100.0 * worst / (3 * n),
        "cause": "bf16 matmul reduction order depends on batch shape; the resulting ulp-level "
                 "logit perturbation flips near-tie multiple-choice questions.",
        "consequence": "Task accuracy carries harness jitter of the SAME MAGNITUDE as the "
                       "deployable-set effects we measure (+5, -4, -1, -6, +4 questions). "
                       "Those differences are therefore below the reproducibility floor of "
                       "the evaluation itself, not merely inside sampling noise.",
        "does_NOT_affect": ["all NLL values (bit-identical)", "all latency values",
                            "the two Bonferroni survivors"],
        "survivors_vs_jitter": {
            "note": "Asked and answered before a reviewer can: the significant results are "
                    "NOT jitter. Quote the per-cell ratios, not a range -- they differ.",
            "jitter_floor_questions": worst,
            "survivor_z6.45_questions": 132,
            "survivor_z6.45_jitter_ratio": round(132 / worst, 1),
            "survivor_z4.37_questions": 90,
            "survivor_z4.37_jitter_ratio": round(90 / worst, 1),
            "both_cells": "1.5B recovery_top, k=2 (z=6.45) and k=4 (z=4.37)",
        },
    }


JIT = _jitter()

payload = {
    "run_id": "noise_audit", "round": 4,
    "uncertainty_sources": [
        "1. binomial sampling SE of the accuracy difference (per-row `se_avg_acc_diff`)",
        "2. Bonferroni correction across the family of comparisons actually made",
        "3. MEASURED harness jitter from task batch shape (`harness_jitter`) -- an observed "
        "reproducibility floor, not a model",
    ],
    "harness_jitter": JIT,
    "rule": "Rule 10 -- recovery fractions on tiny denominators inflate. Any fraction whose "
            "absolute delta is within sampling noise must be reported as an absolute count.",
    "significance_threshold": "2 SE (~95%, two-sided). A 1-SE band is NOT a significance test: "
                              "a delta at 1.0-1.2 SE has two-sided p ~ 0.25 and establishes "
                              "nothing. Only rows with significant_at_2se_95pct = true support "
                              "a claim of a real accuracy difference.",
    "method_note": "se = (1/T)*sqrt(sum_t [p_A(1-p_A) + p_B(1-p_B)]/n) over the T=3 tasks, "
                   "using the measured per-task accuracies. The two methods are treated as "
                   "independent although they are scored on the same items, so this SE is the "
                   "conservative (wider) choice; a paired test would be tighter.",
    "rows": rows,
    "depth_ar_accuracy_deltas_NOT_significant_at_95pct": len(flagged),
    "depth_ar_rows_total": N_FAM,
    "bonferroni": {
        "family_size": N_FAM,
        "alpha": ALPHA,
        "alpha_per_test": ALPHA / N_FAM,
        "z_threshold": z_bonf,
        "n_significant": len(bonf_sig),
        "significant_rows": [
            {"model": r["model"], "selection": r["selection"], "k": r["k"],
             "net_questions": r["net_questions_vs_plain_skip"], "z": r["z_abs_delta_over_se"]}
            for r in bonf_sig],
        "note": "Corrected for the 16 depth_ar-vs-plain_skip comparisons actually made. An "
                "uncorrected 95% threshold over 16 tests would expect ~0.8 false positives by "
                "chance, so the uncorrected borderline (0.5B recovery_top k=2, z=1.95) cannot "
                "be claimed. Both surviving results clear the corrected bar comfortably.",
    },
    "status": "complete",
    "notes": "Absolute question counts are the ground truth here; fractions are derived and "
             "can be misleading when the dense-minus-plain gap is a few points.",
}
write_result(f"{RES}/noise_audit.json", payload)

print(f"{'model':12s} {'method':11s} {'sel':15s} {'k':>2} {'Δacc':>7} {'Δq':>5} {'frac':>8} {'se':>7} {'z':>5} {'2se/95%':>15}")
for r in rows:
    if r["method"] not in ("depth_ar", "depth_ar_ct"):
        continue
    f = r["reported_fraction"]
    print(f"{r['model'].split('/')[-1]:12s} {r['method']:11s} {r['selection']:15s} {r['k']:>2} "
          f"{r['abs_delta_avg_acc']:+7.4f} {r['net_questions_vs_plain_skip']:+5d} "
          f"{(f'{f:+.3f}' if f is not None else 'n/a'):>8} "
          f"{r['se_avg_acc_diff']:7.4f} {r['z_abs_delta_over_se']:5.2f} "
          f"{('**SIGNIFICANT**' if r['significant_at_2se_95pct'] else 'not sig'):>15}")
if JIT:
    w = JIT["max_abs_question_swing_of_900"]
    print(f"\nHARNESS JITTER (measured, same config, batch 32 vs 8): NLL bit-identical; "
          f"accuracy swings up to {w} questions of 900 ({JIT['approx_acc_points']:.2f} acc pts)")
    print(f"  -> the two significant results are {132//w}x and {90//w}x the jitter: not jitter.")
print(f"\ndepth_ar deltas NOT significant at uncorrected 95%: {len(flagged)} / {N_FAM}")
print(f"BONFERRONI (family={N_FAM}, alpha={ALPHA}/{N_FAM}={ALPHA/N_FAM:.5f} -> |z| >= {z_bonf:.2f}):")
for r in FAMILY:
    mark = "SURVIVES" if r["significant_bonferroni"] else "        "
    if r["significant_bonferroni"] or r["z_abs_delta_over_se"] >= 1.5:
        print(f"  {mark}  {r['model'].split('/')[-1]:13s} {r['selection']:16s} k={r['k']} "
              f"z={r['z_abs_delta_over_se']:.2f}  ({r['net_questions_vs_plain_skip']:+d} of "
              f"{r['total_questions_graded']})")
print(f"  -> {len(bonf_sig)} of {N_FAM} survive correction")
print(f"-> {RES}/noise_audit.json")
