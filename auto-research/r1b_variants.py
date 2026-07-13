"""Round 1b: variant search after Gate A came back substantively negative (plan section 5).

The R1 scan showed the fitted AR(1) coefficient is NEGATIVE across layers 4-16 and explains
a median of ~3% of update energy. A single global scalar is the wrong model class if the
anti-correlation is channel-structured. Three variants, hard cap (plan section 11):

  A  normalized direction   Delta_hat = s * Delta_{l-1}/||Delta_{l-1}||     (1 scalar)
  C  per-channel diagonal   Delta_hat = a (.) Delta_{l-1}                    (d scalars, O(Td))
  D  local window AR(3)     Delta_hat = a1 D_{l-1} + a2 D_{l-2} + a3 D_{l-3} (3 scalars)

Baselines carried through for a matched comparison: plain_skip, copy, depth_ar1, depth_ar2.
Fit on calibration, score and evaluate on disjoint held-out. Shardable by layer.
"""

from __future__ import annotations

import argparse
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import (DepthARModel, SkipPlan, collect_stats, eval_nll,
                      recovery_nll, write_result)

MODEL = "Qwen/Qwen2.5-0.5B"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()

    torch.manual_seed(42)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.float32).cuda().eval()
    dm = DepthARModel(model)

    from data import blocks
    calib, held = blocks(tok, 16, 16, 512)

    acc_c = collect_stats(dm, calib)   # fit here
    acc_h = collect_stats(dm, held)    # score here

    eligible = dm.eligible_layers()
    mine = [l for i, l in enumerate(eligible) if i % a.n_shards == a.shard]

    dm.plan = SkipPlan()
    dense_nll = eval_nll(dm, held)
    print(f"[s{a.shard}] dense {dense_nll:.4f} layers {mine}", flush=True)

    out = {}
    for l in mine:
        c_ar1 = (acc_c.fit_ar1(l),)
        c_ar2 = acc_c.fit_ar2(l)
        c_ar3 = acc_c.fit_ar3(l)
        c_norm = acc_c.fit_normalized(l)
        c_diag = acc_c.fit_diag(l).cuda()

        plans = {
            "plain_skip":       SkipPlan("plain_skip", (l,)),
            "copy":             SkipPlan("copy", (l,)),
            "depth_ar1":        SkipPlan("depth_ar1", (l,), {l: c_ar1}),
            "depth_ar2":        SkipPlan("depth_ar2", (l,), {l: c_ar2}),
            "var_a_normalized": SkipPlan("var_a_normalized", (l,), {l: c_norm}),
            "var_c_diag":       SkipPlan("var_c_diag", (l,), {l: c_diag}),
            "var_d_ar3":        SkipPlan("var_d_ar3", (l,), {l: c_ar3}),
        }
        nll = {}
        for name, plan in plans.items():
            dm.plan = plan
            nll[name] = eval_nll(dm, held)

        P = {
            "copy":             acc_h.predictability(l, (1.0,)),
            "depth_ar1":        acc_h.predictability(l, c_ar1),
            "depth_ar2":        acc_h.predictability(l, c_ar2),
            "var_d_ar3":        acc_h.predictability(l, c_ar3),
            "var_a_normalized": acc_h.predictability_normalized(l, c_norm),
            "var_c_diag":       acc_h.predictability_diag(l, c_diag),
        }
        rec = {m: recovery_nll(nll[m], dense_nll, nll["plain_skip"])
               for m in plans if m != "plain_skip"}

        out[str(l)] = {
            "coef": {
                "depth_ar1": list(c_ar1), "depth_ar2": list(c_ar2), "var_d_ar3": list(c_ar3),
                "var_a_normalized": list(c_norm),
                "var_c_diag_summary": {
                    "mean": c_diag.mean().item(), "std": c_diag.std().item(),
                    "frac_negative": (c_diag < 0).float().mean().item(),
                    "min": c_diag.min().item(), "max": c_diag.max().item(),
                },
            },
            "P_heldout": P,
            "nll": nll,
            "damage_plain_skip": nll["plain_skip"] - dense_nll,
            "recovery": rec,
        }
        best = max(rec, key=lambda m: rec[m])
        print(f"[s{a.shard}] L{l:2d} P_diag={P['var_c_diag']:+.3f} P_ar1={P['depth_ar1']:+.3f} "
              f"| rec: diag={rec['var_c_diag']:+.3f} ar1={rec['depth_ar1']:+.3f} "
              f"norm={rec['var_a_normalized']:+.3f} ar3={rec['var_d_ar3']:+.3f} | best={best}", flush=True)

    write_result(a.out, {
        "shard": a.shard, "n_shards": a.n_shards, "model": a.model,
        "dense_nll": dense_nll, "n_layers": dm.n_layers, "eligible_layers": eligible,
        "layers": out, "elapsed_sec": time.time() - t0,
    })
    print(f"[s{a.shard}] done {time.time()-t0:.0f}s -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
