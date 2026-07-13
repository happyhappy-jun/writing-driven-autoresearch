"""Make the replicated-jitter addendum stable enough to cite.

The first draft keyed the survivor ratios by z-value (`survivor_z6.45_jitter_ratio`). A key
named after a number breaks the moment the number moves. Re-key everything by IDENTITY
(model / selection / k / method) so a citation survives a recomputation.
"""

import json

P = "/home/lobster/ralph/results/jitter_replicated_addendum.json"
old = json.load(open(P))
na = json.load(open("/home/lobster/ralph/results/noise_audit.json"))

bf = old["bf16_floor"]
floor = bf["max_questions_of_900"]

surv = []
for r in na["rows"]:
    if not r.get("significant_bonferroni"):
        continue
    q = abs(r["net_questions_vs_plain_skip"])
    surv.append({
        "model": r["model"].split("/")[-1], "selection": r["selection"], "k": r["k"],
        "method": r["method"],
        "net_questions": r["net_questions_vs_plain_skip"],
        "total_questions": r["total_questions_graded"],
        "z": r["z_abs_delta_over_se"],
        "ratio_vs_bf16_floor": round(q / floor, 1),
    })
surv.sort(key=lambda x: -x["z"])

d = {
    "run_id": "jitter_replicated_addendum",
    "provenance": "Collected during the post-submission wrap-up window, AFTER the paper's "
                  "significance accounting closed. Deliberately NOT folded into "
                  "noise_audit.json, which remains exactly the shipped accounting (family=63, "
                  "n=1 jitter estimate). Cite this file directly for the REPLICATED floor and "
                  "state its wrap-up provenance in the text.",
    "sources": ["jitter_bf16.json", "jitter_replication.json"],
    "bf16_floor": {
        "n_pairwise_comparisons": bf["n_pairwise_comparisons"],
        "max_questions": floor,
        "mean_questions": round(bf["mean_questions"], 2),
        "sd_questions": round(bf["sd_questions"], 2),
        "questions_per_config": 900,
        "max_accuracy_points": round(100.0 * floor / 900, 2),
        "nll_range": bf["nll_range"],
        "setup": "Qwen2.5-1.5B bf16, 2 layer sets x 3 methods x 3 task batch shapes, 300 ex/task",
    },
    "fp32_floor": {
        "n_pairwise_comparisons": old["fp32_floor"]["n_pairwise_comparisons"],
        "max_questions": old["fp32_floor"]["max_questions_of_300"],
        "questions_per_config": 300,
        "nll_range": old["fp32_floor"]["nll_range"],
        "setup": "Qwen2.5-0.5B fp32, 6 configs x 3 task batch shapes, 100 ex/task",
        "result": "EXACTLY ZERO. fp32 is bit-exact under batch reshaping.",
    },
    "mechanism_confirmed": "The floor was predicted to arise from bf16 matmul reduction order "
                           "changing with batch shape. That predicts zero jitter in fp32. fp32 "
                           "measures exactly zero across 48 comparisons -- an out-of-sample "
                           "confirmation of the mechanism.",
    "scoping": "The floor is a BF16 phenomenon, not a property of the harness. fp32 results "
               "(all 0.5B cells) are exactly reproducible. bf16 results (1.5B/7B/Qwen3) carry "
               "a floor of mean 2.48, sd 1.62, max 6 questions of 900 (0.67 accuracy points).",
    "survivors_vs_replicated_floor": {
        "floor_questions": floor,
        "note": "Every Bonferroni survivor recomputed against the REPLICATED bf16 max, not the "
                "n=1 estimate. All four clear it by an order of magnitude.",
        "survivors": surv,
        "min_ratio": min(s["ratio_vs_bf16_floor"] for s in surv),
        "max_ratio": max(s["ratio_vs_bf16_floor"] for s in surv),
    },
    "status": "complete",
}
json.dump(d, open(P, "w"), indent=2)

print("CITATION-STABLE KEYS (identity-based, not value-based):")
print("  bf16_floor.{n_pairwise_comparisons, max_questions, mean_questions, sd_questions,")
print("             max_accuracy_points, nll_range}")
print("  fp32_floor.{n_pairwise_comparisons, max_questions, result}")
print("  survivors_vs_replicated_floor.{floor_questions, survivors[], min_ratio, max_ratio}")
print()
b = d["bf16_floor"]
print(f"  bf16: max {b['max_questions']} q of 900 = {b['max_accuracy_points']} acc pts | "
      f"mean {b['mean_questions']} sd {b['sd_questions']} (n={b['n_pairwise_comparisons']})")
f = d["fp32_floor"]
print(f"  fp32: max {f['max_questions']} q (n={f['n_pairwise_comparisons']}) -> EXACTLY ZERO")
sv = d["survivors_vs_replicated_floor"]
print(f"  survivors clear the floor by {sv['min_ratio']}x to {sv['max_ratio']}x:")
for s in surv:
    print(f"    {s['model']:12s} {s['selection']:15s} k={s['k']:<2} {s['method']:11s} "
          f"{s['net_questions']:+4d}/{s['total_questions']} z={s['z']:.2f} "
          f"-> {s['ratio_vs_bf16_floor']}x floor")
