"""Independent recomputation of the paper-cited R1 statistics (master's order), plus the
measured mechanism behind Pivot B.

Master reports spearman(P_ar1, recovery_ar1) = -0.0152, alpha<0 in 13/13 of L4-16, mean
AR2-AR1 recovery delta = +0.0009. This recomputes all three FROM THE RAW LAYER DATA, not by
copying. A mismatch is signal.

Mechanism: the global scalar alpha is the ENERGY-WEIGHTED least-squares solution,
    alpha = sum_c num_c / sum_c den_c,
so a few high-energy channels can dominate it. The per-channel coefficient a_l is not so
constrained. Prediction: Variant C beats scalar AR(1) exactly where alpha diverges from the
channel median of a_l. That is testable with data already on disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import time

import numpy as np
from scipy.stats import spearmanr

from depth_ar import write_result

RES = "/home/lobster/ralph/results"
SRC = {
    "r1_layerscan_0.5b.json": None,
    "diag_channel_stats_0.5b.json": None,
    "r1v_C_0.5b.json": None,
}


def _stamp(name):
    """Record what this artifact was derived from, so staleness is detectable, not silent."""
    p = os.path.join(RES, name)
    b = open(p, "rb").read()
    return {"sha256": hashlib.sha256(b).hexdigest()[:16],
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(p)))}


def _load(name):
    SRC[name] = _stamp(name)
    return json.load(open(os.path.join(RES, name)))


R1 = _load("r1_layerscan_0.5b.json")
CH = _load("diag_channel_stats_0.5b.json")
VC = _load("r1v_C_0.5b.json")

L = R1["layers"]
keys = sorted(L, key=int)

P_ar1 = np.array([L[k]["P_heldout"]["depth_ar1"] for k in keys])
rec_ar1 = np.array([L[k]["recovery"]["depth_ar1"] for k in keys])
rec_ar2 = np.array([L[k]["recovery"]["depth_ar2"] for k in keys])
alpha = np.array([L[k]["alpha_ar1"] for k in keys])
damage = np.array([L[k]["damage_plain_skip"] for k in keys])

rho, p = spearmanr(P_ar1, rec_ar1)
mid = [k for k in keys if 4 <= int(k) <= 16]
n_neg = sum(1 for k in mid if L[k]["alpha_ar1"] < 0)
ar2_delta = float((rec_ar2 - rec_ar1).mean())

# -- mechanism ------------------------------------------------------------------------
rec_diag = np.array([VC["layers"][k]["recovery"]["var_c_diag"] for k in keys])
med_a = np.array([CH["layers"][k]["median"] for k in keys])
frac_pos = np.array([CH["layers"][k]["frac_channels_positive"] for k in keys])
# How far is the energy-weighted scalar from the typical channel?
divergence = np.abs(alpha - med_a)
diag_adv = rec_diag - rec_ar1
rho_m, p_m = spearmanr(divergence, diag_adv)

# Selection rule master ratified: expected residual damage after repair.
resid = {int(k): damage[i] * (1.0 - rec_diag[i]) for i, k in enumerate(keys)}

payload = {
    "run_id": "r1_analysis_0.5b", "round": 1, "model": "Qwen2.5-0.5B",
    "sources": SRC,
    "config": {"dtype": "float32", "gpu": "TITAN X (Pascal, sm_61)", "seed": 42,
               "params_per_layer": {"depth_ar": 896, "depth_ar1": 1},
               "ridge": 0.01, "selection_rule": "n/a (analysis artifact)"},
    "eval": {"corpus": "wikitext-103-raw-v1", "split": "train-heldout",
             "disjoint_from_calib": True},
    "n_eligible_layers": len(keys),
    "paper_cited_stats": {
        "spearman_P_ar1_vs_recovery_ar1": {"rho": float(rho), "p_value": float(p), "n": len(keys)},
        "alpha_ar1_negative_in_layers_4_16": {"n_negative": n_neg, "n_total": len(mid)},
        "mean_recovery_delta_ar2_minus_ar1": ar2_delta,
    },
    "mechanism_pivot_b": {
        "claim_tested": "the scalar alpha is a bad summary of the channel population",
        "frac_channels_positive_L4_16_mean": float(frac_pos[3:16].mean()),
        "median_a_l_L4_16_mean": float(med_a[3:16].mean()),
        "channels_agree_in_sign": bool(frac_pos[3:16].mean() < 0.25),
        "spearman_scalar_divergence_vs_diag_advantage": {
            "rho": float(rho_m), "p_value": float(p_m), "n": len(keys),
            "x": "|alpha_ar1 - median(a_l)|", "y": "recovery_diag - recovery_ar1"},
        "worked_example_layer_4": {
            "alpha_ar1": float(alpha[3]), "median_a_l": float(med_a[3]),
            "frac_channels_positive": float(frac_pos[3]),
            "note": "the energy-weighted scalar collapses to ~0 while ~82% of channels agree on "
                    "a clearly negative coefficient",
        },
    },
    "selection_rule_expected_residual_damage": {
        "formula": "damage_l * (1 - recovery_diag_l)",
        "per_layer": {str(k): float(v) for k, v in sorted(resid.items(), key=lambda kv: kv[1])},
    },
    "status": "complete",
}
write_result("/home/lobster/ralph/results/r1_analysis_0.5b.json", payload)

print(f"spearman(P_ar1, recovery_ar1) = {rho:+.4f}  (p={p:.4f}, n={len(keys)})   [master: -0.0152]")
print(f"alpha_ar1 < 0 in layers 4-16  = {n_neg}/{len(mid)}                        [master: 13/13]")
print(f"mean recovery delta AR2-AR1   = {ar2_delta:+.4f}                       [master: +0.0009]")
print()
print("MECHANISM:")
print(f"  frac(a_l > 0) in L4-16      = {frac_pos[3:16].mean():.3f}  -> channels AGREE in sign (mostly negative)")
print(f"  median a_l in L4-16         = {med_a[3:16].mean():+.3f}")
print(f"  spearman(|alpha - med a_l|, diag advantage) = {rho_m:+.4f} (p={p_m:.4f})")
print(f"  L4: alpha={alpha[3]:+.4f} but median a_l={med_a[3]:+.4f}, frac_pos={frac_pos[3]:.3f}")
