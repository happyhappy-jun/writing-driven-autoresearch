"""Merge R1 shards, evaluate Gate A, write the canonical result JSON + RESULTS.md row."""

from __future__ import annotations

import glob
import json
import sys

from depth_ar import select_non_adjacent, write_result

OUT = "/home/lobster/ralph/results/r1_layerscan_0.5b.json"


def main(pattern):
    shards = [json.load(open(f)) for f in sorted(glob.glob(pattern))]
    if not shards:
        sys.exit(f"no shards matched {pattern}")

    layers = {}
    for s in shards:
        layers.update(s["layers"])

    # Every shard recomputes Dense on the same held-out set; they must agree.
    dense = [s["dense_nll"] for s in shards]
    spread = max(dense) - min(dense)
    assert spread < 1e-6, f"shards disagree on dense NLL: {dense}"
    dense_nll = dense[0]

    eligible = shards[0]["eligible_layers"]
    n_elig = len(eligible)
    P = {int(l): v["P_heldout"]["depth_ar1"] for l, v in layers.items()}
    P2 = {int(l): v["P_heldout"]["depth_ar2"] for l, v in layers.items()}
    rec1 = {int(l): v["recovery"]["depth_ar1"] for l, v in layers.items()}
    rec2 = {int(l): v["recovery"]["depth_ar2"] for l, v in layers.items()}
    dmg = {int(l): v["damage_plain_skip"] for l, v in layers.items()}

    # -- Gate A (plan section 5) --------------------------------------------------------
    c1_n = sum(1 for l in P if P[l] > 0.1)
    c1 = c1_n >= 0.25 * n_elig
    best_rec = {l: max(rec1[l], rec2[l]) for l in rec1}
    c2_n = sum(1 for l in best_rec if best_rec[l] > 0.20)
    c2 = c2_n >= 4
    # "clearly beats Plain Skip for the best several layers": among the 6 layers with the
    # highest P_l, does AR beat Plain Skip on NLL?
    top6 = sorted(P, key=lambda l: P[l], reverse=True)[:6]
    c3_n = sum(1 for l in top6
               if min(layers[str(l)]["nll"]["depth_ar1"], layers[str(l)]["nll"]["depth_ar2"])
               < layers[str(l)]["nll"]["plain_skip"])
    c3 = c3_n >= 4

    passed = c1 or c2 or c3

    # Layer sets Round 2 will use, decided here so R2 inherits them unchanged.
    sel_pred = {k: select_non_adjacent(P, k, 2) for k in (1, 2, 4, 6)}
    sel_oracle = {k: select_non_adjacent({l: -dmg[l] for l in dmg}, k, 2) for k in (1, 2, 4, 6)}

    payload = {
        "run_id": "r1_layerscan_0.5b",
        "round": 1,
        "model": "Qwen2.5-0.5B",
        "dtype": "float32",
        "hardware": "4x TITAN X Pascal 12GB (sm_61; no BF16/FA2)",
        "n_layers": shards[0]["n_layers"],
        "eligible_layers": eligible,
        "selection": "layer_scan (all eligible layers, one at a time)",
        "calib": {"n_seq": 16, "seq_len": 512, "corpus": "wikitext-103-raw-v1"},
        "eval": {"n_seq": 16, "seq_len": 512, "disjoint_from_calib": True,
                 "corpus": "wikitext-103-raw-v1"},
        "seed": 42,
        "dense_nll": dense_nll,
        "layers": dict(sorted(layers.items(), key=lambda kv: int(kv[0]))),
        "summary": {
            "P_ar1_max": max(P.values()), "P_ar1_argmax": max(P, key=P.get),
            "P_ar1_median": sorted(P.values())[len(P) // 2],
            "P_ar2_max": max(P2.values()),
            "n_layers_P_gt_0.1": c1_n,
            "best_recovery_ar1": max(rec1.values()),
            "best_recovery_ar1_layer": max(rec1, key=rec1.get),
            "n_layers_recovery_gt_20pct": c2_n,
            "mean_cos_consecutive": sum(v["cos_consecutive"] for v in layers.values()) / len(layers),
        },
        "gate_a": {
            "criterion_1_frac_P_gt_0.1": {
                "pass": c1, "n": c1_n, "n_eligible": n_elig, "threshold": "25% of eligible"},
            "criterion_2_recovery_gt_20pct": {
                "pass": c2, "n": c2_n, "threshold": ">=4 layers"},
            "criterion_3_AR_beats_plainskip_top6_P": {
                "pass": c3, "n": c3_n, "of": len(top6), "layers": top6, "threshold": ">=4 of 6"},
            "passed": passed,
        },
        "round2_layer_sets": {
            "predictability": {str(k): v for k, v in sel_pred.items()},
            "oracle_lite_low_damage": {str(k): v for k, v in sel_oracle.items()},
            "min_gap": 2,
        },
        "status": "complete",
        "notes": "Single-layer scan: only layer l is replaced, so Delta_{l-1}/Delta_{l-2} "
                 "are always real (dense) updates. Compounding is untested here -- that is R2.",
    }
    write_result(OUT, payload)

    s = payload["summary"]
    g = payload["gate_a"]
    print(f"dense NLL {dense_nll:.4f}")
    print(f"P_ar1: max {s['P_ar1_max']:+.3f} @L{s['P_ar1_argmax']}  median {s['P_ar1_median']:+.3f}")
    print(f"Gate A: C1 {c1} ({c1_n}/{n_elig} layers P>0.1) | C2 {c2} ({c2_n} layers rec>20%) | "
          f"C3 {c3} ({c3_n}/6 top-P layers AR<Plain)")
    print(f"GATE A {'PASS' if passed else 'FAIL'} -> {OUT}")

    # one row, appended
    with open("/home/lobster/ralph/RESULTS.md", "a") as f:
        f.write(
            f"| r1_layerscan_0.5b | 1 | Qwen2.5-0.5B | layer scan (22 eligible) | "
            f"dense NLL {dense_nll:.3f} | max P_l(AR1) {s['P_ar1_max']:+.3f} @L{s['P_ar1_argmax']} | "
            f"median P_l {s['P_ar1_median']:+.3f} | layers P>0.1: {c1_n}/{n_elig} | "
            f"layers recovery>20%: {c2_n} | best recovery {s['best_recovery_ar1']:+.1%} @L{s['best_recovery_ar1_layer']} | "
            f"Gate A **{'PASS' if passed else 'FAIL'}** | `results/r1_layerscan_0.5b.json` |\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         "/tmp/claude-1018/-home-lobster/54448185-f65d-4832-a43f-154bebea0f92/scratchpad/r1_shard*.json")
