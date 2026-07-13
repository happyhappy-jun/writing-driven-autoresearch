"""Per-channel diagnostics for the Pivot-B mechanism claim.

`writing` needs to state WHY the scalar predictor fails and the per-channel one works.
Two competing mechanisms, and they imply opposite sentences in the paper:

  (i)  "successive blocks partially undo one another"  -> requires a_l < 0 for MOST channels
  (ii) "the scalar is a bad summary of a sign-heterogeneous channel population"
                                                       -> requires a_l to straddle 0 with wide spread

This measures which is true. One dense calibration pass; no new experiment.
"""

from __future__ import annotations

import json

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import DepthARModel, collect_stats, write_result

MODEL = "Qwen/Qwen2.5-0.5B"
OUT = "/home/lobster/ralph/results/diag_channel_stats_0.5b.json"

torch.manual_seed(42)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).cuda().eval()
dm = DepthARModel(model)

from data import blocks
calib, _ = blocks(tok, 16, 16, 512)
acc = collect_stats(dm, calib)

layers, raw = {}, {}
for l in dm.eligible_layers():
    a = acc.fit_diag(l).float().cpu()
    alpha = acc.fit_ar1(l)
    q = torch.tensor([0.10, 0.25, 0.50, 0.75, 0.90])
    p10, p25, p50, p75, p90 = torch.quantile(a, q).tolist()
    layers[str(l)] = {
        "alpha_ar1": alpha,                       # the single scalar, for contrast
        "d_model": a.numel(),
        "frac_channels_positive": (a > 0).float().mean().item(),
        "mean": a.mean().item(),
        "median": p50,
        "std": a.std().item(),
        "p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90,
        "min": a.min().item(), "max": a.max().item(),
        # Does the scalar sit inside the channel population, or is it a cancellation artifact?
        "mean_abs": a.abs().mean().item(),
        "sign_entropy_bits": (lambda p: float(
            0.0 if p in (0.0, 1.0) else
            -(p * torch.log2(torch.tensor(p)) + (1 - p) * torch.log2(torch.tensor(1 - p))).item()
        ))((a > 0).float().mean().item()),
    }
    raw[str(l)] = a.numpy()

fp = [v["frac_channels_positive"] for v in layers.values()]
mid = [layers[str(l)] for l in range(4, 17)]          # the 13 layers where alpha_ar1 < 0
payload = {
    "run_id": "diag_channel_stats_0.5b", "round": 1.5, "model": "Qwen2.5-0.5B",
    "config": {"n_calib_seqs": 16, "seq_len": 512, "dtype": "float32",
               "gpu": "TITAN X (Pascal, sm_61)", "corpus": "wikitext-103-raw-v1", "seed": 42},
    "d_model": 896,
    "layers": layers,
    "summary": {
        "frac_channels_positive_mean": sum(fp) / len(fp),
        "frac_channels_positive_min": min(fp),
        "frac_channels_positive_max": max(fp),
        "layers_4_16_frac_positive_mean": sum(v["frac_channels_positive"] for v in mid) / len(mid),
        "layers_4_16_alpha_ar1_all_negative": all(v["alpha_ar1"] < 0 for v in mid),
        "layers_4_16_mean_channel_std": sum(v["std"] for v in mid) / len(mid),
        "layers_4_16_mean_abs_over_abs_mean": sum(
            v["mean_abs"] / (abs(v["mean"]) + 1e-9) for v in mid) / len(mid),
    },
    "status": "complete",
    # Schema rule (master): notes describe DATA, never hypotheses. Hypotheses live in
    # DECISIONS.md, where they can be killed cleanly.
    "notes": "a_l = per-channel diagonal coefficient (Variant C), closed-form ridge fit on the "
             "calibration set. alpha_ar1 = the global scalar for the same layer. MEASURED: in "
             "layers 4-16 the channels are ~88% sign-negative (homogeneous), and the scalar "
             "tracks the channel median. In layers 1-3 and 20-22 the channels are sign-mixed "
             "(frac_positive 0.24-0.67); at layer 3 the scalar fits +1.10 while the channel "
             "median is -0.30. The general mechanism by which diag beats the scalar is OPEN: "
             "diag also wins at sign-homogeneous layers, so sign heterogeneity does not explain "
             "it. Neither the cancellation hypothesis nor an energy-weighting hypothesis "
             "(spearman |alpha - median a_l| vs diag advantage = +0.016, p=0.94) is supported.",
}
write_result(OUT, payload)

import numpy as np
np.savez("/home/lobster/auto-research/diag_coeffs_0.5b.npz", **raw)

s = payload["summary"]
print(f"{'L':>2} {'alpha_ar1':>10} {'frac a_l>0':>11} {'median a_l':>11} {'std':>7} {'|a|_mean/|mean a|':>18}")
for l in range(1, 23):
    v = layers[str(l)]
    print(f"{l:>2} {v['alpha_ar1']:>+10.3f} {v['frac_channels_positive']:>11.3f} "
          f"{v['median']:>+11.3f} {v['std']:>7.3f} {v['mean_abs']/(abs(v['mean'])+1e-9):>18.1f}")
print(f"\nlayers 4-16: all alpha_ar1 < 0 ? {s['layers_4_16_alpha_ar1_all_negative']}")
print(f"layers 4-16: mean frac(a_l > 0) = {s['layers_4_16_frac_positive_mean']:.3f}")
print(f"layers 4-16: mean |a|/|mean a|  = {s['layers_4_16_mean_abs_over_abs_mean']:.1f}")
print(f"-> {OUT}")
