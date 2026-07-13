"""Choose the per-channel ridge strength.

The unregularized diagonal fit (a_c = num_c/den_c) gives low-energy channels enormous
coefficients -- layer 2 reached |a_c| = 42 and blew held-out NLL from 2.73 to 11.01.
Master's spec said "closed-form per-channel ridge"; the implementation had none.

Selection protocol, stated so the paper can state it: lambda is chosen by mean HELD-OUT
predictability P_l -- a *fitting* metric on *held-out* data. It is NOT chosen on the
reported NLL or on any downstream task. One global constant, shared by every layer and
every model. Selecting on the reported metric would be tuning on the test set.
"""

from __future__ import annotations

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from depth_ar import DepthARModel, SkipPlan, collect_stats, eval_nll, recovery_nll

MODEL = "Qwen/Qwen2.5-0.5B"
RIDGES = [0.0, 1e-3, 1e-2, 1e-1, 1.0]

torch.manual_seed(42)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).cuda().eval()
dm = DepthARModel(model)
from data import blocks
calib, held = blocks(tok, 16, 16, 512)

acc_c = collect_stats(dm, calib)
acc_h = collect_stats(dm, held)
elig = dm.eligible_layers()

print(f"{'ridge':>7} {'mean heldout P':>15} {'median P':>9} {'min P':>8}   (selection metric)")
best, best_P = None, -1e9
for r in RIDGES:
    Ps = [acc_h.predictability_diag(l, acc_c.fit_diag(l, ridge=r).cuda()) for l in elig]
    m = sum(Ps) / len(Ps)
    print(f"{r:>7.3f} {m:>15.4f} {sorted(Ps)[len(Ps)//2]:>9.4f} {min(Ps):>8.4f}")
    if m > best_P:
        best, best_P = r, m

print(f"\nselected ridge = {best} (highest mean held-out P)\n")

# Report what it does to the pathological layer and to overall NLL recovery. These are
# consequences of the choice, not inputs to it.
dm.plan = SkipPlan()
dense = eval_nll(dm, held)
print(f"{'ridge':>7} {'L2 max|a|':>10} {'L2 NLL':>9} {'L2 rec':>8} {'mean rec':>9} {'median rec':>11}")
for r in [0.0, best]:
    recs, l2 = [], None
    for l in elig:
        a = acc_c.fit_diag(l, ridge=r).cuda()
        dm.plan = SkipPlan("plain_skip", (l,))
        n_p = eval_nll(dm, held)
        dm.plan = SkipPlan("var_c_diag", (l,), {l: a})
        n_d = eval_nll(dm, held)
        rec = recovery_nll(n_d, dense, n_p)
        recs.append(rec)
        if l == 2:
            l2 = (a.abs().max().item(), n_d, rec)
    print(f"{r:>7.3f} {l2[0]:>10.2f} {l2[1]:>9.4f} {l2[2]:>+8.3f} "
          f"{sum(recs)/len(recs):>+9.3f} {sorted(recs)[len(recs)//2]:>+11.3f}")
