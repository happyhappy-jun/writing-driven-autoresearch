"""Ridge selection, take 2 -- on the metric that actually matters.

Sweep 1 selected lambda by held-out predictability P and chose ~0, leaving |a_c| = 42 and
layer 2's NLL at 11.01. P is an ENERGY-WEIGHTED fit metric, so it is nearly blind to
low-energy channels -- exactly the ones whose unregularized coefficients blow up the model.
(This is the paper's own dissociation, in miniature: geometric fit quality is not functional
quality.)

So select lambda on NLL instead, and keep the split honest:
    DEV  = wikitext-103 held-out   -> selects lambda (one global scalar)
    TEST = wikitext-2 test         -> every number reported in the paper
Tuning one hyperparameter on dev and reporting on test is standard; tuning it on the
reported metric would not be.
"""

from __future__ import annotations

import argparse
import json

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import DepthARModel, SkipPlan, collect_stats, eval_nll, recovery_nll

ap = argparse.ArgumentParser()
ap.add_argument("--shard", type=int, default=0)
ap.add_argument("--n-shards", type=int, default=1)
ap.add_argument("--out", required=True)
a = ap.parse_args()

RIDGES = [0.0, 1e-2, 1e-1, 1.0, 10.0]
MODEL = "Qwen/Qwen2.5-0.5B"

torch.manual_seed(42)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).cuda().eval()
dm = DepthARModel(model)
from data import blocks
calib, dev = blocks(tok, 16, 16, 512)          # DEV = wikitext-103 held-out

acc_c = collect_stats(dm, calib)
elig = dm.eligible_layers()
mine = [l for i, l in enumerate(elig) if i % a.n_shards == a.shard]

dm.plan = SkipPlan()
dense = eval_nll(dm, dev)

out = {}
for l in mine:
    dm.plan = SkipPlan("plain_skip", (l,))
    n_plain = eval_nll(dm, dev)                # ridge-independent, so measure once
    per_ridge = {}
    for r in RIDGES:
        coef = acc_c.fit_diag(l, ridge=r).cuda()
        dm.plan = SkipPlan("var_c_diag", (l,), {l: coef})
        n_d = eval_nll(dm, dev)
        per_ridge[str(r)] = {
            "nll_diag_dev": n_d,
            "recovery_dev": recovery_nll(n_d, dense, n_plain),
            "max_abs_a": coef.abs().max().item(),
        }
    out[str(l)] = {"nll_plain_dev": n_plain, "damage": n_plain - dense, "ridges": per_ridge}
    print(f"L{l:2d} " + " ".join(
        f"r={r}:{per_ridge[str(r)]['recovery_dev']:+.3f}" for r in RIDGES), flush=True)

json.dump({"dense_dev_nll": dense, "ridges": RIDGES, "layers": out},
          open(a.out, "w"), indent=2)
print(f"shard {a.shard} done -> {a.out}", flush=True)
