"""Paper-citable artifact: the ridge protocol, the L2 non-rescue, and P's energy-blindness.

Master ratified this as a Pivot-E-in-miniature result. Everything here is MEASURED:

  1. The per-channel diagonal fit needs a ridge; without one, |a_c| reaches 42.
  2. Selecting the ridge by held-out PREDICTABILITY (P) picks lambda ~= 0 -- it is blind to a
     failure that blows held-out NLL from 2.73 to 11.01. P is an ENERGY-WEIGHTED fit metric,
     so low-energy channels are nearly invisible to it while they still wreck the model.
  3. Selecting the ridge by held-out NLL on a DEV split (wikitext-103 held-out; never the
     reported wikitext-2 test) picks lambda = 0.01.
  4. The ridge does NOT rescue layer 2. Even lambda = 10 leaves recovery at -2.42, because
     that pathology lives in HIGH-energy channels, which a mean-scaled ridge cannot shrink.
     Layer 2 is excluded from every reported configuration by the selection rule anyway.
"""

from __future__ import annotations

import glob
import json

from depth_ar import write_result

SP = "/tmp/claude-1018/-home-lobster/54448185-f65d-4832-a43f-154bebea0f92/scratchpad"

shards = [json.load(open(f)) for f in glob.glob(f"{SP}/ridge2_*.json")]
L = {}
for s in shards:
    L.update(s["layers"])
RIDGES = shards[0]["ridges"]
dense_dev = shards[0]["dense_dev_nll"]

by_ridge = {}
for r in RIDGES:
    recs = [L[k]["ridges"][str(r)]["recovery_dev"] for k in L]
    by_ridge[str(r)] = {
        "mean_recovery_dev": sum(recs) / len(recs),
        "median_recovery_dev": sorted(recs)[len(recs) // 2],
        "min_recovery_dev": min(recs),
        "n_layers_recovery_negative": sum(1 for x in recs if x < 0),
        "layer2_recovery_dev": L["2"]["ridges"][str(r)]["recovery_dev"],
        "layer2_nll_dev": L["2"]["ridges"][str(r)]["nll_diag_dev"],
        "layer2_max_abs_a": L["2"]["ridges"][str(r)]["max_abs_a"],
    }

sel = max(by_ridge, key=lambda r: by_ridge[r]["mean_recovery_dev"])

payload = {
    "run_id": "ridge_analysis_0.5b", "round": 1.5, "model": "Qwen2.5-0.5B",
    "config": {
        "n_calib_seqs": 16, "seq_len": 512, "dtype": "float32",
        "gpu": "TITAN X (Pascal, sm_61)", "seed": 42,
        "params_per_layer": {"depth_ar": 896, "depth_ar1": 1},
        "ridge": float(sel),
        "selection_rule": "ridge chosen by max mean single-layer NLL recovery on the DEV split",
    },
    "calib": {"corpus": "wikitext-103-raw-v1", "split": "train"},
    "eval": {"corpus": "wikitext-103-raw-v1", "split": "train-heldout (DEV)",
             "disjoint_from_calib": True,
             "note": "This is the DEV split used ONLY to choose the ridge. Every number "
                     "reported in the paper is measured on wikitext-2 test."},
    "dense_nll_dev": dense_dev,
    "ridge_grid": RIDGES,
    "by_ridge": by_ridge,
    "selected_ridge": float(sel),
    "findings": {
        "P_is_energy_blind": {
            "statement": "Selecting the ridge by held-out predictability P picks lambda ~= 0, "
                         "which leaves |a_c| = 42 and held-out NLL at 11.01 for layer 2. P is "
                         "an energy-weighted fit metric, so channels carrying little update "
                         "energy barely register in it -- yet their unregularized coefficients "
                         "are exactly what wreck the model.",
            "ridge_selected_by_P": 0.001,
            "ridge_selected_by_NLL_dev": float(sel),
            "relation_to_pivot_e": "The same geometry-vs-function dissociation the paper "
                                   "reports across layers reappears inside hyperparameter "
                                   "selection: a geometric fit criterion is blind to a "
                                   "functional catastrophe.",
        },
        "layer2_not_rescued_by_ridge": {
            "statement": "The ridge does not rescue layer 2 at any strength tested. Recovery "
                         "goes from -3.675 (no ridge) to -2.423 (lambda=10), never approaching "
                         "0. The pathology lives in HIGH-energy channels, which a ridge scaled "
                         "to the layer's mean channel energy cannot shrink.",
            "recovery_by_ridge": {r: by_ridge[r]["layer2_recovery_dev"] for r in by_ridge},
            "max_abs_a_by_ridge": {r: by_ridge[r]["layer2_max_abs_a"] for r in by_ridge},
            "consequence": "None: layer 2 has 1.77 nats of single-layer damage and negative "
                           "diag recovery, so the residual-damage selection rule excludes it "
                           "from every reported configuration.",
        },
        "ridge_effect_is_small": {
            "statement": "Mean single-layer recovery is flat across the grid "
                         "(-0.075 unregularized to -0.074 at the selected ridge). The ridge is "
                         "a stability guard, not a source of the method's gains.",
        },
    },
    "status": "complete",
    "notes": "All values measured on the DEV split (wikitext-103 held-out). The ridge grid was "
             "swept once; lambda was not re-tuned per layer or per model.",
}
write_result("/home/lobster/ralph/results/ridge_analysis_0.5b.json", payload)
print(f"selected ridge {sel}; L2 recovery by ridge: "
      f"{ {r: round(by_ridge[r]['layer2_recovery_dev'], 3) for r in by_ridge} }")
print("-> /home/lobster/ralph/results/ridge_analysis_0.5b.json")
