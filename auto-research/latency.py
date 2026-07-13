"""Prefill latency: Dense vs Plain Skip vs Depth-AR at the Table-1 layer set.

Protocol (plan section 8), stated exactly because the paper's overhead sentence rests on it:
  BF16, use_cache=False, batch 8, seq_len in {512, 2048}, 10 warm-up + 30 measured iters,
  torch.cuda.synchronize() around every timed region, median + IQR reported.
  Plain attention -- NO FlashAttention. All three methods share one identical stack, so the
  comparison is internally valid even though the absolute numbers are not FA2-competitive.

This is PREFILL latency. It is not end-to-end generation latency and must not be called that.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import DepthARModel, SkipPlan, collect_stats, write_result

DTYPES = {"float32": torch.float32, "bfloat16": torch.bfloat16, "float16": torch.float16}


def load_model(name, dt):
    try:
        return AutoModelForCausalLM.from_pretrained(name, dtype=dt)
    except TypeError:
        return AutoModelForCausalLM.from_pretrained(name, torch_dtype=dt)


@torch.no_grad()
def time_plan(dm, plan, bs, T, warmup=10, iters=30):
    dm.plan = plan
    ids = torch.randint(100, 30000, (bs, T), device="cuda")
    mask = torch.ones_like(ids)
    for _ in range(warmup):
        dm.forward(ids, mask)
    torch.cuda.synchronize()
    samples = []
    for _ in range(iters):
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        dm.forward(ids, mask)
        torch.cuda.synchronize()
        samples.append((time.perf_counter() - t0) * 1000.0)
    samples.sort()
    q1 = statistics.median(samples[: len(samples) // 2])
    q3 = statistics.median(samples[(len(samples) + 1) // 2:])
    return {"median_ms": statistics.median(samples), "iqr_ms": q3 - q1,
            "p25_ms": q1, "p75_ms": q3, "min_ms": samples[0], "max_ms": samples[-1]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dtype", default="bfloat16", choices=list(DTYPES))
    ap.add_argument("--layers", type=int, nargs="+", required=True,
                    help="the Table-1 k=4 layer set; identical across all methods")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--seq-lens", type=int, nargs="+", default=[512, 2048])
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--n-calib", type=int, default=16)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    torch.manual_seed(42)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = load_model(a.model, DTYPES[a.dtype]).cuda().eval()
    dm = DepthARModel(model)
    layers = tuple(a.layers)

    # Depth-AR needs real coefficients: a zero/garbage vector would change nothing about the
    # timing, but a paper measuring a method must measure the method it ships.
    from data import blocks
    calib, _ = blocks(tok, a.n_calib, 1, 512, config="wikitext-103-raw-v1", split="train")
    acc = collect_stats(dm, calib)
    coef = {l: acc.fit_diag(l).cuda() for l in layers}

    plans = {
        "dense": SkipPlan(),
        "plain_skip": SkipPlan("plain_skip", layers),
        "depth_ar": SkipPlan("var_c_diag", layers, coef),
    }

    results = {}
    for T in a.seq_lens:
        row = {}
        for name, plan in plans.items():
            row[name] = time_plan(dm, plan, a.batch_size, T, a.warmup, a.iters)
            print(f"seq={T:5d} {name:11s} median {row[name]['median_ms']:8.2f} ms  "
                  f"IQR {row[name]['iqr_ms']:.2f}", flush=True)
        d, p, ar = (row[m]["median_ms"] for m in ("dense", "plain_skip", "depth_ar"))
        row["derived"] = {
            "speedup_plain_vs_dense": d / p,
            "speedup_depth_ar_vs_dense": d / ar,
            "depth_ar_overhead_vs_plain_skip_pct": 100.0 * (ar - p) / p,
        }
        print(f"seq={T:5d} -> depth_ar overhead vs plain skip: "
              f"{row['derived']['depth_ar_overhead_vs_plain_skip_pct']:+.2f}%  |  "
              f"speedup vs dense: {row['derived']['speedup_depth_ar_vs_dense']:.3f}x", flush=True)
        results[str(T)] = row

    write_result(a.out, {
        "run_id": f"latency_{a.model.split('/')[-1]}", "round": 4, "model": a.model,
        "config": {"batch_size": a.batch_size, "warmup": a.warmup, "iters": a.iters,
                   "dtype": a.dtype, "seq_lens": a.seq_lens, "seed": 42,
                   "use_cache": False, "attention": "eager (no FlashAttention)",
                   "n_layers": dm.n_layers, "d_model": model.config.hidden_size,
                   "params_per_layer": {"depth_ar": model.config.hidden_size,
                                        "plain_skip": 0},
                   "selection_rule": "residual_damage (Table-1 layer set)"},
        "hardware": "NVIDIA RTX 3090 24GB, BF16, no FlashAttention",
        "eval": {"corpus": "n/a (synthetic random token IDs; timing only)"},
        "skipped_layers": list(layers),
        "metric": "prefill latency (NOT end-to-end generation latency)",
        "by_seq_len": results,
        "status": "complete",
    })
    print(f"-> {a.out}", flush=True)


if __name__ == "__main__":
    main()
