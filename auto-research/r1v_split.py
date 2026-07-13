"""Merge variant shards and emit one JSON per variant (A / C / D), plus the Gate-A2 criteria.

Gate A2 (plan section 5, applied by master): the winner is the SIMPLEST variant that
  - beats Plain Skip on >= 4 single-layer tests, and
  - improves mean NLL across its top-6 layers.
This script COMPUTES those criteria. It does not write a verdict -- gate calls are master's.
"""

from __future__ import annotations

import glob
import json

from depth_ar import write_result

SP = "/tmp/claude-1018/-home-lobster/54448185-f65d-4832-a43f-154bebea0f92/scratchpad"
OUT = "/home/lobster/ralph/results"

# simplest -> most complex; Gate A2 breaks ties toward the top of this list.
VARIANTS = [
    ("A", "var_a_normalized", 1, "s * Delta_{l-1}/||Delta_{l-1}||  (1 scalar/layer)"),
    ("D", "var_d_ar3", 3, "a1 D_{l-1} + a2 D_{l-2} + a3 D_{l-3}  (3 scalars/layer)"),
    ("C", "var_c_diag", 896, "a (.) Delta_{l-1}, per-channel  (d scalars/layer, still O(Td))"),
]
BASELINES = ["plain_skip", "copy", "depth_ar1", "depth_ar2"]


def main():
    shards = [json.load(open(f)) for f in sorted(glob.glob(f"{SP}/r1v_shard*.json"))]
    layers = {}
    for s in shards:
        layers.update(s["layers"])
    dense_nll = shards[0]["dense_nll"]
    assert max(s["dense_nll"] for s in shards) - min(s["dense_nll"] for s in shards) < 1e-6

    keys = sorted(layers, key=int)
    summary = {}

    for tag, method, n_params, formula in VARIANTS:
        per_layer = {}
        for l in keys:
            v = layers[l]
            per_layer[l] = {
                "coef": v["coef"].get(method, v["coef"].get("var_c_diag_summary")),
                "P_heldout": {method: v["P_heldout"][method],
                              "depth_ar1": v["P_heldout"]["depth_ar1"]},
                "nll": {m: v["nll"][m] for m in BASELINES + [method]},
                "damage_plain_skip": v["damage_plain_skip"],
                "recovery": {m: v["recovery"][m] for m in
                             ["copy", "depth_ar1", "depth_ar2", method]},
            }

        # Gate A2 criteria, computed not judged.
        beats = [int(l) for l in keys if layers[l]["nll"][method] < layers[l]["nll"]["plain_skip"]]
        top6 = sorted(keys, key=lambda l: layers[l]["P_heldout"][method], reverse=True)[:6]
        mean_nll_var = sum(layers[l]["nll"][method] for l in top6) / 6
        mean_nll_plain = sum(layers[l]["nll"]["plain_skip"] for l in top6) / 6
        recs = [layers[l]["recovery"][method] for l in keys]

        crit = {
            "beats_plain_skip_n_layers": len(beats),
            "beats_plain_skip_layers": beats,
            "criterion_beats_plain_ge4": len(beats) >= 4,
            "top6_layers_by_P": [int(l) for l in top6],
            "top6_mean_nll_variant": mean_nll_var,
            "top6_mean_nll_plain_skip": mean_nll_plain,
            "criterion_improves_top6_mean_nll": mean_nll_var < mean_nll_plain,
            "n_params_per_layer": n_params,
        }
        summary[tag] = {
            "method": method, "n_params_per_layer": n_params,
            "beats_plain_n": len(beats),
            "mean_recovery": sum(recs) / len(recs),
            "median_recovery": sorted(recs)[len(recs) // 2],
            "best_recovery": max(recs),
            "best_recovery_layer": int(keys[recs.index(max(recs))]),
            "both_criteria": crit["criterion_beats_plain_ge4"] and
                             crit["criterion_improves_top6_mean_nll"],
        }

        write_result(f"{OUT}/r1v_{tag}_0.5b.json", {
            "run_id": f"r1v_{tag}_0.5b", "round": 1.5, "model": "Qwen2.5-0.5B",
            "variant": tag, "method": method, "formula": formula,
            "config": {"n_calib_seqs": 16, "n_eval_seqs": 16, "seq_len": 512,
                       "dtype": "float32", "gpu": "TITAN X (Pascal, sm_61)",
                       "corpus": "wikitext-103-raw-v1", "seed": 42,
                       "disjoint_from_calib": True},
            "dense_nll": dense_nll,
            "eligible_layers": shards[0]["eligible_layers"],
            "layers": {l: per_layer[l] for l in keys},
            "gate_a2_criteria": crit,
            "status": "complete",
            "notes": "Single-layer replacement (only layer l skipped). Coefficients fitted on "
                     "16 calibration seqs, scored/evaluated on 16 disjoint held-out seqs.",
        })

    print(f"dense NLL {dense_nll:.4f}\n")
    print(f"{'var':>3} {'params/layer':>12} {'beats plain':>12} {'mean rec':>9} "
          f"{'median rec':>11} {'best rec':>9} {'both crit':>10}")
    for tag in ("A", "D", "C"):
        s = summary[tag]
        print(f"{tag:>3} {s['n_params_per_layer']:>12} {s['beats_plain_n']:>9}/22 "
              f"{s['mean_recovery']:>+9.3f} {s['median_recovery']:>+11.3f} "
              f"{s['best_recovery']:>+9.3f} (L{s['best_recovery_layer']}) {str(s['both_criteria']):>6}")
    json.dump(summary, open(f"{SP}/r1v_summary.json", "w"), indent=2)


if __name__ == "__main__":
    main()
