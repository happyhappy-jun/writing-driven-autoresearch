"""Cross-check every number the PAPER prints against the JSONs it claims to derive from.

`writing` owns the LaTeX; I own the numbers. A figure or table that disagrees with
~/ralph/results/ is a fabricated result no matter who typed it. This reads the .tex
read-only and reports mismatches. It NEVER edits anything under ~/writing.
"""

from __future__ import annotations

import glob
import json
import os
import re

RES = "/home/lobster/ralph/results"
TEX = "/home/lobster/writing"


def load(n):
    p = os.path.join(RES, n)
    return json.load(open(p)) if os.path.exists(p) else None


r2, r3, r4 = load("r2_compose_0.5b.json"), load("r3_verify_1.5b.json"), load("r4_headline_7b.json")
lat15, lat7 = load("latency_Qwen2.5-1.5B.json"), load("latency_Qwen2.5-7B.json")
na, r1 = load("noise_audit.json"), load("r1_layerscan_0.5b.json")
r1a = load("r1_analysis_0.5b.json")

# Every number the paper is entitled to print, with where it comes from.
TRUTH = {}
for tag, d in (("0.5B", r2), ("1.5B", r3), ("7B", r4)):
    if not d:
        continue
    TRUTH[f"{tag} dense nll"] = d["dense_nll"]
    for key, r in d["runs"].items():
        if r["selection"] != "residual_damage":
            continue
        m = r["methods"]
        for meth in ("dense", "plain_skip", "copy_update", "depth_ar1", "depth_ar"):
            TRUTH[f"{tag} {key} {meth} nll"] = m[meth]["wikitext2_nll"]
            if "avg_acc" in m[meth]:
                TRUTH[f"{tag} {key} {meth} avg_acc"] = m[meth]["avg_acc"]
for tag, d in (("1.5B", lat15), ("7B", lat7)):
    if not d:
        continue
    for T, r in d["by_seq_len"].items():
        TRUTH[f"{tag} lat{T} overhead_pct"] = r["derived"]["depth_ar_overhead_vs_plain_skip_pct"]
        TRUTH[f"{tag} lat{T} speedup"] = r["derived"]["speedup_depth_ar_vs_dense"]
if r1a:
    TRUTH["spearman rho"] = r1a["paper_cited_stats"]["spearman_P_ar1_vs_recovery_ar1"]["rho"]
    TRUTH["spearman p"] = r1a["paper_cited_stats"]["spearman_P_ar1_vs_recovery_ar1"]["p_value"]

# Collect the numbers actually printed in the paper.
NUM = re.compile(r"(?<![\w.])(\d+\.\d+)(?![\w])")
printed = {}
for f in glob.glob(f"{TEX}/**/*.tex", recursive=True):
    if "icfm2024" in f and "main.tex" not in f:
        continue
    txt = open(f, errors="ignore").read()
    txt = re.sub(r"%.*", "", txt)                      # strip LaTeX comments
    for mt in NUM.finditer(txt):
        v = float(mt.group(1))
        printed.setdefault(v, []).append(os.path.relpath(f, TEX))

TOL = 5e-3            # a paper rounds; 0.005 absolute is generous for 2-4 dp values
IGNORE = {0.0, 1.0, 0.5, 2.0, 3.0, 4.0, 0.9, 0.8, 0.95, 0.25, 0.75, 1.5, 0.15,
          0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 1.2, 2.5, 0.05, 0.02, 0.01, 11.0, 12.0}

unmatched = []
for v, files in sorted(printed.items()):
    if v in IGNORE or v > 5000:
        continue
    hit = [k for k, t in TRUTH.items() if abs(t - v) <= TOL]
    # a fraction may be printed as a percent
    hit += [k + " (as %)" for k, t in TRUTH.items()
            if abs(t * 100 - v) <= 0.5 and abs(t) < 1.5]
    if not hit:
        unmatched.append((v, sorted(set(files))))

print("=" * 78)
print(f"{len(TRUTH)} measured values available; {len(printed)} distinct numerals in the .tex")
print("=" * 78)
print("\nNUMBERS PRINTED IN THE PAPER THAT MATCH NO MEASURED VALUE")
print("(each is either a legitimate constant/citation/year, or a FABRICATION -- check each)\n")
for v, files in unmatched:
    print(f"  {v:>10}   in {', '.join(files)}")
print(f"\n{len(unmatched)} unmatched numerals")
print("\nKEY MEASURED VALUES AND WHETHER THE PAPER PRINTS THEM:")
for k in sorted(TRUTH):
    t = TRUTH[k]
    found = any(abs(t - v) <= TOL or (abs(t) < 1.5 and abs(t * 100 - v) <= 0.5)
                for v in printed)
    print(f"  {'printed' if found else '  --   '}  {k:42s} {t:10.4f}")
