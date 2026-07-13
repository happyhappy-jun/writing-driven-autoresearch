"""Round 0: prove the harness is exact before testing the idea (plan section 5 R0).

Six checks. Each is independent of the machinery it validates -- the reference path
never routes through DepthARLayer.
"""

from __future__ import annotations

import json
import sys

import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import (Accumulators, DepthARModel, SkipPlan, eval_nll,
                      select_non_adjacent, write_result)

MODEL = "Qwen/Qwen2.5-0.5B"
DEV = "cuda"
results = {}


def check(name, ok, detail):
    results[name] = {"pass": bool(ok), **detail}
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)
    return ok


class Identity(nn.Module):
    """Hand-written skip: the block contributes nothing. Reference for check 3."""
    def __init__(self, tuple_out): super().__init__(); self.tuple_out = tuple_out
    def forward(self, hidden_states, **kw):
        return (hidden_states,) if self.tuple_out else hidden_states


def main():
    torch.manual_seed(42)
    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # Two independent instances: `ref` is never wrapped.
    ref = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).to(DEV).eval()
    wrp = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).to(DEV).eval()
    dm = DepthARModel(wrp)
    L = dm.n_layers
    print(f"model: {MODEL}  layers={L}  dtype=fp32  eligible={dm.eligible_layers()}", flush=True)

    ids = torch.randint(100, 30000, (2, 128), device=DEV)
    mask = torch.ones_like(ids)

    with torch.no_grad():
        # 1 -- dense wrapper reproduces the original logits ------------------------------
        ref_logits = ref(input_ids=ids, attention_mask=mask, use_cache=False).logits
        dm.plan = SkipPlan()  # dense
        w_logits = dm.forward(ids, mask)
        d = (ref_logits - w_logits).abs().max().item()
        check("1_dense_equality", d == 0.0,
              {"max_abs_logit_diff": d, "note": "bit-exact: dense path returns the block output untouched"})

        tuple_out = dm.ctx.returns_tuple

        # 2 -- AR with alpha=0 reproduces Plain Skip exactly ------------------------------
        tgt = [5, 9, 13]
        dm.plan = SkipPlan("plain_skip", tuple(tgt))
        plain_logits = dm.forward(ids, mask)
        dm.plan = SkipPlan("depth_ar1", tuple(tgt), {i: (0.0,) for i in tgt})
        ar0_logits = dm.forward(ids, mask)
        d = (plain_logits - ar0_logits).abs().max().item()
        check("2_alpha0_equals_plainskip", d == 0.0, {"max_abs_logit_diff": d, "layers": tgt})

        # 3 -- a hand-skipped layer matches the generic skip path -------------------------
        l = 9
        keep = ref.model.layers[l]
        ref.model.layers[l] = Identity(tuple_out)
        manual_logits = ref(input_ids=ids, attention_mask=mask, use_cache=False).logits
        ref.model.layers[l] = keep
        dm.plan = SkipPlan("plain_skip", (l,))
        generic_logits = dm.forward(ids, mask)
        d = (manual_logits - generic_logits).abs().max().item()
        check("3_manual_skip_matches", d == 0.0, {"max_abs_logit_diff": d, "layer": l})

        # 4 -- Delta is captured at the block boundary: h_{l+1} = h_l + Delta_l ------------
        trace = {}
        dm.plan = SkipPlan()
        dm.forward(ids, mask, trace=trace)
        worst, worst_l = 0.0, None
        for i in range(L - 1):
            h_i, delta_i = trace[i]
            h_next, _ = trace[i + 1]
            e = (h_i + delta_i - h_next).abs().max().item()
            if e > worst:
                worst, worst_l = e, i
        scale = max(trace[i][0].abs().max().item() for i in range(L))
        # Only round-off in the reconstruction h + (out - h) is admissible; the boundary
        # itself is exact. Budget it in ULPs of the working dtype, not as a fixed constant:
        # an fp32-calibrated bound is ~39x tighter than BF16 can even represent, and would
        # "fail" a correct harness on a BF16 host. A genuine boundary bug misplaces Delta by
        # O(||Delta||) ~ O(scale), which is thousands of ULPs and still caught.
        eps = torch.finfo(next(wrp.parameters()).dtype).eps
        tol = 2.0 * eps * scale
        check("4_boundary_capture", worst <= tol,
              {"max_abs_err": worst, "at_layer": worst_l, "hidden_scale": scale,
               "tol": tol, "ulps": worst / (eps * scale), "budget_ulps": 2.0,
               "dtype_eps": eps})

        # 5 -- padding excluded from fitting and from NLL ----------------------------------
        # Invariance test: scramble the pad slots. If pads are truly excluded, every
        # accumulator and the NLL must be bit-identical no matter what sits there.
        real_len, pad_len = 96, 32
        base = torch.randint(100, 30000, (2, real_len), device=DEV)
        pmask = torch.cat([torch.ones(2, real_len, device=DEV, dtype=torch.long),
                           torch.zeros(2, pad_len, device=DEV, dtype=torch.long)], 1)

        def padded(fill):
            return torch.cat([base, fill], 1)

        pads_a = torch.full((2, pad_len), tok.pad_token_id, device=DEV, dtype=torch.long)
        pads_b = torch.randint(100, 30000, (2, pad_len), device=DEV)

        dm.plan = SkipPlan()
        acc_a, acc_b = Accumulators(L), Accumulators(L)
        nll_a = eval_nll(dm, [(padded(pads_a), pmask)], acc=acc_a)
        nll_b = eval_nll(dm, [(padded(pads_b), pmask)], acc=acc_b)

        worst_acc = 0.0
        for i in range(L):
            for k in Accumulators.SCALARS:
                va, vb = acc_a.s[i][k], acc_b.s[i][k]
                worst_acc = max(worst_acc, abs(va - vb) / (abs(va) + 1e-12))
            # Gram, cross terms, and the per-channel statistics must be invariant too.
            worst_acc = max(worst_acc, (acc_a.G[i] - acc_b.G[i]).abs().max().item())
            worst_acc = max(worst_acc, (acc_a.b[i] - acc_b.b[i]).abs().max().item())
            if acc_a.pc_num[i] is not None:
                worst_acc = max(worst_acc, (acc_a.pc_num[i] - acc_b.pc_num[i]).abs().max().item())
                worst_acc = max(worst_acc, (acc_a.pc_den[i] - acc_b.pc_den[i]).abs().max().item())
        n_ok = all(acc_a.s[i]["n"] == 2 * real_len for i in range(L))
        d_nll = abs(nll_a - nll_b)
        check("5_padding_excluded", worst_acc == 0.0 and d_nll == 0.0 and n_ok,
              {"max_rel_acc_diff": worst_acc, "abs_nll_diff": d_nll,
               "n_tokens_counted": acc_a.s[0]["n"], "n_tokens_expected": 2 * real_len,
               "note": "pad slots scrambled; accumulators and NLL must not move"})

        # 6 -- selected layers are non-adjacent in the main setting -------------------------
        fake = {i: float(-abs(i - 12)) for i in dm.eligible_layers()}  # peaks mid-network
        sel = select_non_adjacent(fake, k=4, min_gap=2)
        gaps = [sel[i + 1] - sel[i] for i in range(len(sel) - 1)]
        ok = len(sel) == 4 and all(g >= 2 for g in gaps) and \
            all(1 <= s <= L - 2 for s in sel)
        check("6_non_adjacent", ok,
              {"selected": sel, "gaps": gaps, "min_gap_required": 2,
               "excludes_layer0_and_last": True})

    n_pass = sum(r["pass"] for r in results.values())
    green = n_pass == 6
    payload = {
        "run_id": "r0_checks_0.5b", "round": 0, "model": MODEL,
        "dtype": "float32", "device": "TITAN X (Pascal, sm_61)", "n_layers": L,
        "eligible_layers": dm.eligible_layers(),
        "checks": results, "n_pass": n_pass, "n_total": 6,
        "status": "complete" if green else "failed",
        "notes": "FP32 (no BF16 on Pascal); dense/alpha0/manual-skip checks are bit-exact.",
    }
    p = write_result("/home/lobster/ralph/results/r0_checks_0.5b.json", payload)
    print(f"\n{'R0 GREEN' if green else 'R0 RED'}  {n_pass}/6 -> {p}", flush=True)
    return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main())
