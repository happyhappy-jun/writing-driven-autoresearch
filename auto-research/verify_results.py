"""Self-audit of every artifact `writing` reads. Run BEFORE master's verification fan-out.

Three classes of check:
  A. SCHEMA   -- mandatory fields present (params_per_layer, eval.corpus, selection_rule, ...)
  B. INTEGRITY-- claims the JSON makes about itself are true (identical layer sets, min_gap>=2,
                 disjoint calib/eval, no NaN/inf, dense identical across methods in a row)
  C. DERIVED  -- every stored recovery fraction RECOMPUTED from the raw NLL/accuracy it
                 derives from. A stale derived value is the exact bug class that already bit
                 us once (r1_analysis vs the re-ridged fit).

Exit non-zero if anything fails. Reports, never repairs.
"""

from __future__ import annotations

import json
import math
import os

RES = "/home/lobster/ralph/results"
fails, warns, checks = [], [], 0


def ck(cond, label, detail=""):
    global checks
    checks += 1
    if not cond:
        fails.append(f"{label}: {detail}")
    return cond


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def recovery_nll(l_ar, l_dense, l_skip):
    return 1.0 - (l_ar - l_dense) / (l_skip - l_dense)


import glob as _g
COMPARISON = ["r2_compose_0.5b.json", "r3_verify_1.5b.json", "r4_headline_7b.json"] + \
    sorted(os.path.basename(f) for f in _g.glob(os.path.join(RES, "qwen3_*.json")))
LATENCY = ["latency_Qwen2.5-1.5B.json", "latency_Qwen2.5-7B.json"]

print("=" * 78)
for fn in COMPARISON:
    p = os.path.join(RES, fn)
    if not os.path.exists(p):
        warns.append(f"{fn} absent")
        continue
    d = json.load(open(p))
    print(f"{fn}")

    # -- A. schema -------------------------------------------------------------------
    c = d.get("config", {})
    ck("params_per_layer" in c, fn, "config.params_per_layer missing")
    ck(d.get("eval", {}).get("corpus") == "wikitext-2-raw-v1", fn,
       f"eval.corpus is {d.get('eval', {}).get('corpus')!r}, expected wikitext-2-raw-v1")
    ck(d["eval"].get("split") == "test", fn, "eval.split is not 'test'")
    ck(d["calib"]["corpus"] == "wikitext-103-raw-v1", fn, "calib corpus wrong")
    ck(d["eval"].get("disjoint_from_calib") is True, fn, "disjoint_from_calib not asserted")
    ck("selection" in d and "rules_run" in d["selection"], fn, "selection.rules_run missing")
    ck(d.get("status") == "complete", fn, f"status={d.get('status')}")
    ck("dense_nll" in d and "dtype" in d, fn, "top-level dense_nll/dtype mirror missing")
    ck(c.get("seed") == 42, fn, "seed != 42")

    n = c["n_task_examples"]
    has_tasks = "avg_acc" in list(d["runs"].values())[0]["methods"]["dense"]
    for key, r in d["runs"].items():
        m, rec = r["methods"], r["recovery"]

        # -- B. integrity ------------------------------------------------------------
        layers = r["skipped_layers"]
        gaps = [layers[i + 1] - layers[i] for i in range(len(layers) - 1)]
        ck(all(g >= 2 for g in gaps), f"{fn}:{key}", f"adjacent skips! layers={layers}")
        ck(len(layers) == r["k"], f"{fn}:{key}", f"k={r['k']} but {len(layers)} layers")
        ck(0 not in layers and (c["n_layers"] - 1) not in layers, f"{fn}:{key}",
           "layer 0 or final layer selected")
        # Dense must be byte-identical across every method row (same object, same run).
        for meth in m:
            for f_ in ("wikitext2_nll", "avg_acc"):
                if f_ in m[meth]:
                    ck(finite(m[meth][f_]), f"{fn}:{key}:{meth}", f"{f_} not finite")
        ck(m["dense"]["wikitext2_nll"] == d["dense_nll"], f"{fn}:{key}",
           "dense NLL differs from top-level dense_nll")
        # accuracies must be exact multiples of 1/n -- proves the denominator is real
        if has_tasks:
            for meth in m:
                for t in ("hellaswag", "piqa", "arc_easy"):
                    if t in m[meth]:
                        q = m[meth][t] * n
                        ck(abs(q - round(q)) < 1e-6, f"{fn}:{key}:{meth}",
                           f"{t}={m[meth][t]} is not a multiple of 1/{n}")

        # -- C. derived --------------------------------------------------------------
        dn = m["dense"]["wikitext2_nll"]
        pn = m["plain_skip"]["wikitext2_nll"]

        # A recovery FRACTION is uninterpretable when its denominator is <= 0: if skipping a
        # layer does not hurt, there is no gap to recover. Flag it rather than trust it.
        if pn - dn <= 0:
            warns.append(f"{fn}:{key}: plain-skip damage <= 0 ({pn - dn:.4f}); recovery "
                         f"fractions undefined here and must not be quoted")
        for meth, rr in rec.items():
            want = recovery_nll(m[meth]["wikitext2_nll"], dn, pn)
            got = rr["gap_recovered_nll"]
            ck(abs(want - got) < 1e-9, f"{fn}:{key}:{meth}",
               f"gap_recovered_nll stored {got:.6f} but recomputes to {want:.6f}")
            if "gap_recovered_avg_acc" in rr:
                den = m["dense"]["avg_acc"] - m["plain_skip"]["avg_acc"]
                want_a = (m[meth]["avg_acc"] - m["plain_skip"]["avg_acc"]) / den
                ck(abs(want_a - rr["gap_recovered_avg_acc"]) < 1e-9, f"{fn}:{key}:{meth}",
                   f"gap_recovered_avg_acc stored {rr['gap_recovered_avg_acc']:.6f} "
                   f"vs recomputed {want_a:.6f}")

for fn in LATENCY:
    p = os.path.join(RES, fn)
    if not os.path.exists(p):
        warns.append(f"{fn} absent")
        continue
    d = json.load(open(p))
    print(f"{fn}")
    ck("prefill" in d["metric"].lower(), fn, "metric must say prefill")
    ck("not end-to-end" in d["metric"].lower() or "NOT end-to-end" in d["metric"], fn,
       "metric must disclaim end-to-end generation")
    ck(d["config"]["batch_size"] == 8 and d["config"]["iters"] == 30
       and d["config"]["warmup"] == 10, fn, "latency protocol deviates from plan §8")
    ck(d["config"]["use_cache"] is False, fn, "use_cache must be False")
    ck("params_per_layer" in d["config"], fn, "params_per_layer missing")
    for T, r in d["by_seq_len"].items():
        dd = r["derived"]
        want = 100.0 * (r["depth_ar"]["median_ms"] - r["plain_skip"]["median_ms"]) \
            / r["plain_skip"]["median_ms"]
        ck(abs(want - dd["depth_ar_overhead_vs_plain_skip_pct"]) < 1e-6, f"{fn}:seq{T}",
           "overhead pct does not recompute")
        ck(r["depth_ar"]["median_ms"] < r["dense"]["median_ms"], f"{fn}:seq{T}",
           "depth_ar is not faster than dense -- efficiency claim would be false")

# noise_audit: recompute question counts from the source JSONs
na = os.path.join(RES, "noise_audit.json")
if os.path.exists(na):
    d = json.load(open(na))
    print("noise_audit.json")
    ck(d["bonferroni"]["family_size"] == d["depth_ar_rows_total"], "noise_audit",
       "bonferroni family size != number of depth_ar comparisons")
    # The threshold must be CONSISTENT with the family size, not a frozen constant -- the
    # family grows as tests are added, and a hardcoded value silently goes stale.
    from scipy.stats import norm as _n
    want = float(_n.ppf(1.0 - (d["bonferroni"]["alpha"] / d["bonferroni"]["family_size"]) / 2))
    ck(abs(d["bonferroni"]["z_threshold"] - want) < 1e-6, "noise_audit",
       f"z threshold {d['bonferroni']['z_threshold']:.4f} inconsistent with family "
       f"{d['bonferroni']['family_size']} (expected {want:.4f})")
    for r in d["rows"]:
        if r["method"] != "depth_ar":
            continue
        ck(r["significant_bonferroni"] <= r["significant_at_2se_95pct"], "noise_audit",
           "a row is Bonferroni-significant but not even uncorrected-significant")

print("=" * 78)
print(f"{checks} checks run")
if warns:
    print("WARN: " + "; ".join(warns))
if fails:
    print(f"\n{len(fails)} FAILURES:")
    for f_ in fails:
        print(f"  FAIL {f_}")
    raise SystemExit(1)
print("ALL GREEN -- every derived value recomputes from its raw measurements.")
