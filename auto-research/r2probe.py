"""Round 2-lite: does the effect COMPOSE across several skipped layers? (plan section 5 R2)

NLL-only probe. Three selection rules x k in {2,4} x matched methods. Coefficients are fitted
single-layer on the dense trajectory, so this probe measures exactly what it should: whether a
predictor fitted in isolation still helps once several layers are skipped at once (compounding).

Selection rules:
  predictability  highest held-out P_l   -- includes L3, which R1 showed is recovery-TOXIC for
                                            scalar AR. Kept deliberately as a diagnostic: it
                                            separates a selection failure from a prediction failure.
  oracle_lite     lowest single-layer NLL damage (not deployable; diagnostic)
  recovery_top    highest measured single-layer AR(1) recovery, excluding damage > 1.0

All rules enforce min_gap >= 2 (>= 1 surviving layer between skips), per persona section 2.
"""

from __future__ import annotations

import argparse
import json
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import (DepthARModel, SkipPlan, collect_stats, eval_nll,
                      recovery_nll, select_non_adjacent, write_result)

MODEL = "Qwen/Qwen2.5-0.5B"
R1 = "/home/lobster/ralph/results/r1_layerscan_0.5b.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/home/lobster/ralph/results/r2probe_0.5b.json")
    a = ap.parse_args()

    torch.manual_seed(42)
    t0 = time.time()
    r1 = json.load(open(R1))
    L = r1["layers"]

    P = {int(l): v["P_heldout"]["depth_ar1"] for l, v in L.items()}
    dmg = {int(l): v["damage_plain_skip"] for l, v in L.items()}
    rec1 = {int(l): v["recovery"]["depth_ar1"] for l, v in L.items()}
    # recovery_top: rank by measured AR(1) recovery, but refuse layers whose removal is
    # catastrophic on its own (damage > 1.0 nats => L1, L2).
    rec_ok = {l: r for l, r in rec1.items() if dmg[l] <= 1.0}

    SELECTIONS = {
        "predictability":  {k: select_non_adjacent(P, k, 2) for k in (2, 4)},
        "oracle_lite":     {k: select_non_adjacent({l: -d for l, d in dmg.items()}, k, 2)
                            for k in (2, 4)},
        "recovery_top":    {k: select_non_adjacent(rec_ok, k, 2) for k in (2, 4)},
    }

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).cuda().eval()
    dm = DepthARModel(model)
    from data import blocks
    calib, held = blocks(tok, 16, 16, 512)

    acc_c = collect_stats(dm, calib)
    dm.plan = SkipPlan()
    dense_nll = eval_nll(dm, held)
    print(f"dense NLL {dense_nll:.4f}", flush=True)

    # Single-layer fits, reused unchanged at every k (that is the point of the probe).
    coef = {l: {"depth_ar1": (acc_c.fit_ar1(l),),
                "depth_ar2": acc_c.fit_ar2(l),
                "var_c_diag": acc_c.fit_diag(l).cuda()} for l in P}

    runs = {}
    for sel_name, per_k in SELECTIONS.items():
        for k, layers in per_k.items():
            key = f"{sel_name}_k{k}"
            layers = tuple(layers)
            methods = {
                "plain_skip": SkipPlan("plain_skip", layers),
                "copy_update": SkipPlan("copy", layers),
                "depth_ar1": SkipPlan("depth_ar1", layers,
                                      {l: coef[l]["depth_ar1"] for l in layers}),
                "depth_ar2": SkipPlan("depth_ar2", layers,
                                      {l: coef[l]["depth_ar2"] for l in layers}),
                "depth_ar_diag": SkipPlan("var_c_diag", layers,
                                          {l: coef[l]["var_c_diag"] for l in layers}),
            }
            nll = {"dense": dense_nll}
            for m, plan in methods.items():
                dm.plan = plan
                nll[m] = eval_nll(dm, held)
            rec = {m: recovery_nll(nll[m], dense_nll, nll["plain_skip"])
                   for m in methods if m != "plain_skip"}
            gaps = [layers[i + 1] - layers[i] for i in range(len(layers) - 1)]
            runs[key] = {
                "selection": sel_name, "k": k,
                "skipped_layers": list(layers),
                "min_gap_ok": all(g >= 2 for g in gaps),
                "wikitext_nll": nll,
                "gap_recovered_nll": rec,
            }
            best = max(rec, key=lambda m: rec[m])
            print(f"{key:22s} {list(layers)} plain {nll['plain_skip']:.4f} "
                  f"ar1 {nll['depth_ar1']:.4f} diag {nll['depth_ar_diag']:.4f} "
                  f"| rec ar1 {rec['depth_ar1']:+.3f} diag {rec['depth_ar_diag']:+.3f} "
                  f"| best {best}", flush=True)

    payload = {
        "run_id": "r2probe_0.5b", "round": 2, "model": "Qwen2.5-0.5B",
        "config": {"n_calib_seqs": 16, "n_eval_seqs": 16, "seq_len": 512,
                   "dtype": "float32", "gpu": "TITAN X (Pascal, sm_61)",
                   "corpus": "wikitext-103-raw-v1", "seed": 42,
                   "disjoint_from_calib": True, "min_gap": 2},
        "dense_nll": dense_nll,
        "coefficients_fitted": "single-layer on dense trajectory (compounding is under test)",
        "runs": runs,
        "status": "complete",
        "notes": "NLL-only (plan section 11: no downstream tasks for a method that has not "
                 "improved LM NLL). depth_ar_diag = Variant C (per-channel), added because R1b "
                 "showed the scalar predictor is the wrong model class.",
        "elapsed_sec": time.time() - t0,
    }
    write_result(a.out, payload)
    print(f"done {time.time()-t0:.0f}s -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
