"""Turn the harness-jitter estimate from n=1 into a DISTRIBUTION.

The noise floor currently rests on ONE duplicated config (1.5B k=2, batch rows 32 vs 8):
NLL bit-identical, accuracy moved 4 questions of 900. That is enough to prove the effect
exists, and NOT enough to state its spread. This replicates it properly.

For each of several 0.5B fp32 configs, evaluate the SAME layer set and the SAME methods at
several task batch shapes. Everything else is held fixed (model, dtype, layers, seed,
examples). Any accuracy movement is therefore pure harness jitter.

Reports per-config and pooled: max |delta| in questions, the sd of the deltas, and how the
NLL behaves (it should not move at all).
"""

from __future__ import annotations

import argparse
import itertools
import json
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import DepthARModel, SkipPlan, collect_stats, eval_nll, write_result


def load_model(name, dt):
    """transformers >=5 takes `dtype=`; 4.x takes `torch_dtype=`. The fleet runs both."""
    try:
        return AutoModelForCausalLM.from_pretrained(name, dtype=dt)
    except TypeError:
        return AutoModelForCausalLM.from_pretrained(name, torch_dtype=dt)

PRESETS = {
    # fp32 0.5B: the floor turned out to be exactly zero (48 comparisons)
    "qwen25_05b_fp32": ("Qwen/Qwen2.5-0.5B", "float32", [
        ("rd_k2", (10, 13)), ("rd_k4", (8, 10, 13, 18)),
        ("rd_k6", (6, 8, 10, 13, 15, 18)), ("rt_k2", (1, 21)),
        ("rt_k4", (1, 5, 7, 21)), ("dense", ())]),
    # bf16 1.5B: this is where the jitter actually lives. Same layer sets as r3_verify.
    "qwen25_15b_bf16": ("Qwen/Qwen2.5-1.5B", "bfloat16", [
        ("rd_k2", (14, 16)), ("rd_k4", (10, 12, 14, 16)), ("dense", ())]),
}
BATCH_SHAPES = [(16384, 32), (8192, 16), (4096, 8)]   # (max_batch_tokens, max_batch_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-examples", type=int, default=100)
    ap.add_argument("--preset", default="qwen25_05b_fp32", choices=list(PRESETS))
    ap.add_argument("--nll", action="store_true",
                    help="also time NLL (it is ulp-deterministic; off by default to save time)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    MODEL, DT, CONFIGS = PRESETS[a.preset]
    dt = {"float32": torch.float32, "bfloat16": torch.bfloat16}[DT]
    torch.manual_seed(42)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = load_model(MODEL, dt).cuda().eval()
    dm = DepthARModel(model)

    from data import blocks
    from tasks import eval_tasks
    SL = 512 if DT == "float32" else 1024
    calib, _ = blocks(tok, 16, 1, SL, config="wikitext-103-raw-v1", split="train",
                      batch_size=4 if DT == "float32" else 2)
    _, held = blocks(tok, 1, 8, SL, config="wikitext-2-raw-v1", split="test",
                     batch_size=4 if DT == "float32" else 2)

    acc = collect_stats(dm, calib)
    coef = {}
    for l in dm.eligible_layers():
        ct = acc.fit_crosstoken(l)
        coef[l] = {"var_c_diag": acc.fit_diag(l).cuda(),
                   "var_ct_diag": (ct[0].cuda(), ct[1].cuda())}

    n = a.n_examples
    results, all_dq = {}, []
    for cname, layers in CONFIGS:
        plans = {"dense": SkipPlan()} if not layers else {
            "plain_skip": SkipPlan("plain_skip", layers),
            "depth_ar": SkipPlan("var_c_diag", layers,
                                 {l: coef[l]["var_c_diag"] for l in layers}),
            "depth_ar_ct": SkipPlan("var_ct_diag", layers,
                                    {l: coef[l]["var_ct_diag"] for l in layers}),
        }
        for mname, plan in plans.items():
            key = f"{cname}:{mname}"
            per_shape = {}
            for (tb, rows) in BATCH_SHAPES:
                dm.plan = plan
                # NLL is ulp-deterministic; the jitter lives in the task scorer. Skip it by
                # default so the bf16 run fits its time box.
                nll = eval_nll(dm, held) if a.nll else 0.0
                t = eval_tasks(dm, tok, n_examples=n, seed=42,
                               max_batch_tokens=tb, max_batch_rows=rows)
                per_shape[f"tok{tb}_rows{rows}"] = {
                    "wikitext2_nll": nll, "avg_acc": t["avg_acc"],
                    "hellaswag": t["hellaswag"], "piqa": t["piqa"], "arc_easy": t["arc_easy"],
                }
            accs = [v["avg_acc"] for v in per_shape.values()]
            nlls = [v["wikitext2_nll"] for v in per_shape.values()]
            # pairwise deltas across batch shapes, in questions out of 3n
            dqs = [round((x - y) * 3 * n) for x, y in itertools.combinations(accs, 2)]
            all_dq.extend(abs(d) for d in dqs)
            results[key] = {
                "layers": list(layers), "method": mname,
                "by_batch_shape": per_shape,
                "acc_range_questions": round((max(accs) - min(accs)) * 3 * n),
                "acc_range_points": 100.0 * (max(accs) - min(accs)),
                "pairwise_delta_questions": dqs,
                "nll_range": max(nlls) - min(nlls),
            }
            print(f"{key:22s} acc range {results[key]['acc_range_questions']:>2d} questions "
                  f"of {3*n} | nll range {results[key]['nll_range']:.2e}", flush=True)

    import statistics
    pooled = {
        "n_pairwise_comparisons": len(all_dq),
        "max_abs_delta_questions": max(all_dq) if all_dq else 0,
        "mean_abs_delta_questions": statistics.mean(all_dq) if all_dq else 0,
        "sd_abs_delta_questions": statistics.pstdev(all_dq) if len(all_dq) > 1 else 0.0,
        "questions_per_config": 3 * n,
        "max_nll_range_over_all_configs": max(v["nll_range"] for v in results.values()),
    }
    write_result(a.out, {
        "run_id": f"jitter_{a.preset}", "round": 6, "model": MODEL,
        "config": {"dtype": DT, "gpu": torch.cuda.get_device_name(0), "seed": 42,
                   "n_examples_per_task": n, "batch_shapes": [list(b) for b in BATCH_SHAPES],
                   "selection_rule": "fixed explicit layer sets (see per-config `layers`)"},
        "eval": {"corpus": "wikitext-2-raw-v1", "split": "test"},
        "purpose": "Replicate the harness-jitter measurement across configs and batch shapes "
                   "so the noise floor is a DISTRIBUTION, not an n=1 estimate.",
        "per_config": results, "pooled": pooled, "status": "complete",
        "notes": "Only the task batch shape varies within a config. Model, dtype, layer set, "
                 "seed and examples are all held fixed, so any accuracy movement is harness "
                 "jitter by construction. NLL should not move at all.",
        "elapsed_sec": time.time() - t0,
    })
    print(f"\nPOOLED: max {pooled['max_abs_delta_questions']} questions, "
          f"mean {pooled['mean_abs_delta_questions']:.2f}, "
          f"sd {pooled['sd_abs_delta_questions']:.2f} (of {3*n}) over "
          f"{pooled['n_pairwise_comparisons']} comparisons")
    print(f"max NLL range across all configs: {pooled['max_nll_range_over_all_configs']:.2e}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
