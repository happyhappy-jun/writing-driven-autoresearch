"""Round 1: does depth-wise momentum exist? (plan section 5 R1)

Per eligible layer, on Qwen2.5-0.5B:
  - fit AR(1) and AR(2) on 16 calibration sequences (FP64 Gram accumulators)
  - held-out P_l on 16 disjoint sequences
  - consecutive-update cosine, normalized update magnitude
  - single-layer skip: Dense / Plain Skip / Copy / AR(1) / AR(2) held-out NLL
  - AR recovery of the single-layer Plain Skip damage

Shardable by layer across GPUs: --shard i --n-shards N.
"""

from __future__ import annotations

import argparse
import json
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import (Accumulators, DepthARModel, SkipPlan, collect_stats,
                      eval_nll, recovery_nll, write_result)

MODEL = "Qwen/Qwen2.5-0.5B"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--n-calib", type=int, default=16)
    ap.add_argument("--n-eval", type=int, default=16)
    ap.add_argument("--seq-len", type=int, default=512)
    a = ap.parse_args()

    torch.manual_seed(42)
    t0 = time.time()

    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.float32).cuda().eval()
    dm = DepthARModel(model)

    from data import blocks
    calib, held = blocks(tok, a.n_calib, a.n_eval, a.seq_len)

    # Fit on calibration; score on held-out. Both are single dense passes.
    acc_c = collect_stats(dm, calib)
    acc_h = collect_stats(dm, held)

    eligible = dm.eligible_layers()
    mine = [l for i, l in enumerate(eligible) if i % a.n_shards == a.shard]

    dm.plan = SkipPlan()
    dense_nll = eval_nll(dm, held)
    print(f"[shard {a.shard}] dense NLL {dense_nll:.4f}  layers {mine}", flush=True)

    out = {}
    for l in mine:
        alpha = acc_c.fit_ar1(l)
        a2, b2 = acc_c.fit_ar2(l)
        coef1, coef2 = (alpha,), (a2, b2)

        plans = {
            "plain_skip": SkipPlan("plain_skip", (l,)),
            "copy":       SkipPlan("copy", (l,)),
            "depth_ar1":  SkipPlan("depth_ar1", (l,), {l: coef1}),
            "depth_ar2":  SkipPlan("depth_ar2", (l,), {l: coef2}),
        }
        nll = {}
        for name, plan in plans.items():
            dm.plan = plan
            nll[name] = eval_nll(dm, held)

        damage = nll["plain_skip"] - dense_nll
        rec = {m: recovery_nll(nll[m], dense_nll, nll["plain_skip"])
               for m in ("copy", "depth_ar1", "depth_ar2")}

        out[str(l)] = {
            "alpha_ar1": alpha,
            "alpha_ar2": a2, "beta_ar2": b2,
            "P_heldout": {
                "copy": acc_h.predictability(l, (1.0,)),
                "depth_ar1": acc_h.predictability(l, coef1),
                "depth_ar2": acc_h.predictability(l, coef2),
            },
            "P_calib_ar1": acc_c.predictability(l, coef1),
            "cos_consecutive": acc_h.cosine(l),
            "rel_update_magnitude": acc_h.rel_magnitude(l),
            "nll": nll,
            "damage_plain_skip": damage,
            "recovery": rec,
        }
        print(f"[shard {a.shard}] L{l:2d} a={alpha:+.3f} P_ar1={out[str(l)]['P_heldout']['depth_ar1']:+.3f} "
              f"cos={out[str(l)]['cos_consecutive']:+.3f} dmg={damage:+.4f} "
              f"rec_ar1={rec['depth_ar1']:+.3f}", flush=True)

    payload = {
        "shard": a.shard, "n_shards": a.n_shards,
        "model": a.model, "dense_nll": dense_nll,
        "n_layers": dm.n_layers, "eligible_layers": eligible,
        "layers": out, "elapsed_sec": time.time() - t0,
    }
    write_result(a.out, payload)
    print(f"[shard {a.shard}] done in {time.time()-t0:.0f}s -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
