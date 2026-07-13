"""R5: cross-token variant -- does the PREVIOUS TOKEN's update help predict this one?

    Delta_l(t) ~ a (.) Delta_{l-1}(t) + b (.) Delta_{l-1}(t-1)      (per channel, closed form)

Motivation: every predictor so far is strictly within-token -- it looks only down the depth
axis at the same position. Attention mixes across tokens, so the update a block produces at
token t may be partly forecast by what the previous block did at t-1. This is the first
predictor that uses the sequence axis at all, and it stays O(Td): one extra shifted
elementwise product.

Fitted per channel by a 2x2 closed-form ridge on FP64 accumulators. Position t=0 has no
predecessor and is excluded from the fit (not fed a zero it would learn from); at inference
t=0 falls back to the within-token term.

Baselines carried at matched layers: plain_skip, var_c_diag (the current winner).
"""

from __future__ import annotations

import argparse
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import (DepthARModel, SkipPlan, collect_stats, eval_nll,
                      recovery_nll, write_result)


def load_model(name, dt):
    try:
        return AutoModelForCausalLM.from_pretrained(name, dtype=dt)
    except TypeError:
        return AutoModelForCausalLM.from_pretrained(name, torch_dtype=dt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--dtype", default="float32")
    ap.add_argument("--n-calib", type=int, default=16)
    ap.add_argument("--n-eval", type=int, default=32)
    ap.add_argument("--seq-len", type=int, default=512)
    ap.add_argument("--ridge", type=float, default=1e-2)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default="r5_crosstoken_0.5b")
    a = ap.parse_args()

    dt = {"float32": torch.float32, "bfloat16": torch.bfloat16}[a.dtype]
    torch.manual_seed(42)
    t0 = time.time()

    tok = AutoTokenizer.from_pretrained(a.model)
    model = load_model(a.model, dt).cuda().eval()
    dm = DepthARModel(model)
    from data import blocks
    calib, _ = blocks(tok, a.n_calib, 1, a.seq_len, config="wikitext-103-raw-v1", split="train")
    _, held = blocks(tok, 1, a.n_eval, a.seq_len, config="wikitext-2-raw-v1", split="test")

    acc_c = collect_stats(dm, calib)
    acc_h = collect_stats(dm, held)
    elig = dm.eligible_layers()

    dm.plan = SkipPlan()
    dense = eval_nll(dm, held)
    print(f"dense NLL (wikitext-2 test) {dense:.4f}", flush=True)

    # -- correctness gate: cross-token with b := 0 must reproduce the diagonal EXACTLY -----
    l0 = elig[len(elig) // 2]
    d0 = acc_c.fit_diag(l0, ridge=a.ridge).cuda()
    dm.plan = SkipPlan("var_c_diag", (l0,), {l0: d0})
    n_diag_ref = eval_nll(dm, held)
    dm.plan = SkipPlan("var_ct_diag", (l0,), {l0: (d0, torch.zeros_like(d0))})
    n_ct_b0 = eval_nll(dm, held)
    gate = abs(n_diag_ref - n_ct_b0)
    print(f"[gate] cross-token with b=0 vs diag: |dNLL| = {gate:.2e} "
          f"({'PASS' if gate < 1e-9 else 'FAIL'})", flush=True)
    if gate >= 1e-9:
        raise SystemExit("cross-token does not reduce to diag at b=0 -- harness bug")

    layers = {}
    for l in elig:
        a_v, b_v = acc_c.fit_crosstoken(l, ridge=a.ridge)
        a_v, b_v = a_v.cuda(), b_v.cuda()
        d_v = acc_c.fit_diag(l, ridge=a.ridge).cuda()

        dm.plan = SkipPlan("plain_skip", (l,))
        n_plain = eval_nll(dm, held)
        dm.plan = SkipPlan("var_c_diag", (l,), {l: d_v})
        n_diag = eval_nll(dm, held)
        dm.plan = SkipPlan("var_ct_diag", (l,), {l: (a_v, b_v)})
        n_ct = eval_nll(dm, held)

        layers[str(l)] = {
            "nll": {"plain_skip": n_plain, "var_c_diag": n_diag, "var_ct_diag": n_ct},
            "P_heldout": {
                "var_c_diag": acc_h.predictability_diag(l, d_v),
                "var_ct_diag": acc_h.predictability_crosstoken(l, (a_v, b_v)),
            },
            "damage_plain_skip": n_plain - dense,
            "recovery": {
                "var_c_diag": recovery_nll(n_diag, dense, n_plain),
                "var_ct_diag": recovery_nll(n_ct, dense, n_plain),
            },
            "ct_beats_diag": n_ct < n_diag,
            "coef_summary": {
                "a_mean": a_v.mean().item(), "a_absmean": a_v.abs().mean().item(),
                "b_mean": b_v.mean().item(), "b_absmean": b_v.abs().mean().item(),
                # if |b| is tiny relative to |a| the cross-token term carries no information
                "b_over_a_absmean": (b_v.abs().mean() / (a_v.abs().mean() + 1e-9)).item(),
                "frac_b_positive": (b_v > 0).float().mean().item(),
            },
        }
        v = layers[str(l)]
        print(f"L{l:2d} P diag {v['P_heldout']['var_c_diag']:+.3f} ct {v['P_heldout']['var_ct_diag']:+.3f}"
              f" | rec diag {v['recovery']['var_c_diag']:+.3f} ct {v['recovery']['var_ct_diag']:+.3f}"
              f" | |b|/|a| {v['coef_summary']['b_over_a_absmean']:.3f}"
              f" | {'CT WINS' if v['ct_beats_diag'] else ''}", flush=True)

    n_win = sum(1 for v in layers.values() if v["ct_beats_diag"])
    mean_ct = sum(v["nll"]["var_ct_diag"] for v in layers.values()) / len(layers)
    mean_dg = sum(v["nll"]["var_c_diag"] for v in layers.values()) / len(layers)
    rec_ct = [v["recovery"]["var_ct_diag"] for v in layers.values()]
    rec_dg = [v["recovery"]["var_c_diag"] for v in layers.values()]

    payload = {
        "run_id": a.run_id, "round": 5, "model": a.model,
        "config": {"n_calib_seqs": a.n_calib, "n_eval_seqs": a.n_eval, "seq_len": a.seq_len,
                   "dtype": a.dtype, "gpu": torch.cuda.get_device_name(0), "seed": 42,
                   "ridge": a.ridge, "d_model": model.config.hidden_size,
                   "params_per_layer": {"var_ct_diag": 2 * model.config.hidden_size,
                                        "var_c_diag": model.config.hidden_size},
                   "selection_rule": "n/a (single-layer scan, all eligible layers)"},
        "calib": {"corpus": "wikitext-103-raw-v1", "split": "train"},
        "eval": {"corpus": "wikitext-2-raw-v1", "split": "test", "disjoint_from_calib": True},
        "dense_nll": dense,
        "correctness_gate_ct_b0_equals_diag": {"abs_nll_diff": gate, "pass": gate < 1e-9},
        "eligible_layers": elig,
        "layers": layers,
        "summary": {
            "n_layers_ct_beats_diag": n_win, "n_layers": len(layers),
            "mean_nll_ct": mean_ct, "mean_nll_diag": mean_dg,
            "ct_improves_mean_nll": mean_ct < mean_dg,
            "mean_recovery_ct": sum(rec_ct) / len(rec_ct),
            "mean_recovery_diag": sum(rec_dg) / len(rec_dg),
            "median_recovery_ct": sorted(rec_ct)[len(rec_ct) // 2],
            "median_recovery_diag": sorted(rec_dg)[len(rec_dg) // 2],
        },
        "status": "complete",
        "notes": "var_ct_diag adds a per-channel coefficient on Delta_{l-1}(t-1), the previous "
                 "TOKEN's update from the preceding layer. 2d scalars/layer, still O(Td). "
                 "Correctness gate: with b=0 it reproduces var_c_diag's NLL exactly.",
        "elapsed_sec": time.time() - t0,
    }
    write_result(a.out, payload)
    s = payload["summary"]
    print(f"\nCT beats diag on {n_win}/{len(layers)} layers | mean NLL ct {mean_ct:.4f} "
          f"vs diag {mean_dg:.4f} | median rec ct {s['median_recovery_ct']:+.3f} "
          f"vs diag {s['median_recovery_diag']:+.3f}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
