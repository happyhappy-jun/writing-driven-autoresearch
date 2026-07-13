#!/usr/bin/env python3
"""
Fig 2a + 2b for the ICML submission.  CPU only, pure matplotlib over JSON.

2a  fig2a_frontier.pdf           quality-compression frontier, NLL only.
2b  fig2b_significant_gains.pdf  accuracy gain over plain skip vs plain-skip damage,
                                 with the measured noise floor drawn underneath.

(2c is the archival two-panel dissociation figure; it is re-emitted from
 plot_fig2.py under its new filename -- see the run_all shell line in the report.)

FONTS
-----
Floor is 10pt native everywhere, including tick labels and annotations, which are
set EXPLICITLY (they do not inherit).  Mathtext SUBSCRIPTS are avoided in labels:
matplotlib renders them at 0.7x, which would silently drop a 10pt label to 7pt.

NOISE FLOOR DRAWN IN 2b
-----------------------
The band is the REPLICATED bf16 harness floor:
    jitter_bf16.json -> pooled.max_abs_delta_questions = 6 of 900 = 0.667 acc pts.
The paper's SUBMITTED text instead cites the earlier n=1 estimate
    noise_audit.json -> harness_jitter.max_abs_question_swing_of_900 = 4 of 900
                        = 0.444 acc pts,
which is deliberately NOT what is drawn here.  The replicated floor is the wider,
more conservative of the two, so drawing it can only UNDERSTATE significance.
`writing` must reconcile the caption with this choice.

WHAT 2b DOES AND DOES NOT CLAIM
-------------------------------
It shows that every statistically significant gain occurs at SEVERE plain-skip
damage.  It does NOT show that gain is proportional to damage, and the figure
must not be captioned that way: the single most-damaged cell in the whole study
(7B, residual_damage, k=12, damage 41.9 pts) has a gain of just +1.22 pts
(z=0.55), and 1.5B k=12 (damage 29.3 pts) is -0.56 pts.  Severe damage is
NECESSARY for a measurable gain, not SUFFICIENT.  Those null points are plotted,
not hidden.
"""

import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

RESULTS = "/home/lobster/ralph/results"
OUTDIR = "/home/lobster/writing/figures"

# 2a and 2b must be the SAME WIDTH so they pair side by side.
# Saved at EXACT figsize (no bbox_inches="tight"): constrained_layout already
# guarantees nothing clips, and re-trimming would give 2a and 2b DIFFERENT widths
# (their legends differ), breaking the side-by-side pairing requirement.
FIG_W = 3.40
FIG_H_A = 2.95
FIG_H_B = 2.95

OKABE = {
    "plain_skip": "#E69F00",   # orange
    "depth_ar": "#0072B2",     # blue
    "depth_ar_ct": "#009E73",  # green
}
DENSE_COLOR = "#555555"
SE_COLOR = "#666666"
SIG_RING = "#000000"

MODEL_MARKER = {"0.5B": "o", "1.5B": "s", "7B": "^"}
SEL_COLOR = {"residual_damage": "#0072B2", "recovery_top": "#D55E00"}

matplotlib.rcParams.update({
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 11,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.5,
    "figure.dpi": 200,
})

RUN_PREFIX = "residual_damage_"   # 2a: deployable rule ONLY. Never recovery_top.


# ---------------------------------------------------------------------------
# 2a data: NLL frontier
# ---------------------------------------------------------------------------
# Primary files win a k for the methods they carry.  depth_ar_ct is absent from
# the primary files, so it is taken from the ct_*/pareto_* runs of the SAME cell.
# That cross-file merge is safe for THIS figure and only this figure, because NLL
# reproduces bit-exactly across duplicate runs: jitter_bf16.json records
# max_abs_delta_nll = 4.4e-16 (one float64 ulp) between two runs of an identical
# config that differ by 4 questions of accuracy.  Accuracy would NOT be safe to
# merge this way; 2a plots no accuracy.
MODELS_2A = [
    ("0.5B", ["r2_compose_0.5b.json"], ["pareto_0.5b_*.json", "ct_compose_0.5b_*.json"]),
    ("1.5B", ["r3_verify_1.5b.json"], ["pareto_1.5b_*.json", "ct_verify_1.5b_*.json"]),
    ("7B", ["r4_headline_7b.json"], ["pareto_7b_*.json", "ct_*7b*.json"]),
]


def load_frontier(primary, secondary):
    cells = {}   # k -> {method: nll}, plus frac
    dense = None
    for rank, pats in enumerate((primary, secondary)):
        paths = []
        for p in pats:
            paths.extend(sorted(glob.glob(os.path.join(RESULTS, p))))
        for path in paths:
            with open(path) as f:
                d = json.load(f)
            for rk, rv in d["runs"].items():
                if not rk.startswith(RUN_PREFIX):
                    continue                      # recovery_top dies here
                k = rv["k"]
                cell = cells.setdefault(k, {"frac": rv["frac_blocks_skipped"],
                                            "nll": {}, "src": {}})
                for m, mv in rv["methods"].items():
                    if m == "dense":
                        dense = mv["wikitext2_nll"]
                        continue
                    # first writer wins (primary files are visited first)
                    if m not in cell["nll"]:
                        cell["nll"][m] = mv["wikitext2_nll"]
                        cell["src"][m] = os.path.basename(path)
    if not cells:
        return None
    return cells, dense


def fig2a():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H_A), constrained_layout=True)
    report = []
    for mi, (label, prim, sec) in enumerate(MODELS_2A):
        got = load_frontier(prim, sec)
        if got is None:
            print(f"[2a skip] {label}")
            continue
        cells, dense = got
        ks = sorted(cells)
        marker = MODEL_MARKER[label]

        ax.axhline(dense, color=DENSE_COLOR, linewidth=1.1, alpha=0.85,
                   linestyle=[(0, (4, 2)), (0, (1, 1.5)), (0, (5, 1, 1, 1))][mi],
                   zorder=1)

        for meth, ls in (("plain_skip", "--"), ("depth_ar", "-"),
                         ("depth_ar_ct", ":")):
            xs = [cells[k]["frac"] for k in ks if meth in cells[k]["nll"]]
            ys = [cells[k]["nll"][meth] for k in ks if meth in cells[k]["nll"]]
            if not xs:
                continue
            ax.plot(xs, ys, color=OKABE[meth], linestyle=ls, linewidth=1.6,
                    marker=marker, markersize=5.0, markerfacecolor="white",
                    markeredgewidth=1.2, markeredgecolor=OKABE[meth], zorder=3)
            report.append((label, meth, [k for k in ks if meth in cells[k]["nll"]]))
        print(f"[2a] {label}: dense={dense:.4f} ks={ks}")

    ax.set_xlabel("Fraction of blocks skipped")
    # Two-line: a one-line 11pt label is taller than the axes and would be
    # clipped at the canvas edge.
    ax.set_ylabel("WikiText-2 NLL\n(lower better)")
    ax.grid(True, linewidth=0.4, alpha=0.35, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(width=0.8, length=3)
    ax.set_xlim(0.0, 0.46)

    handles = [
        Line2D([], [], color=OKABE["plain_skip"], linestyle="--", lw=1.6,
               label="Plain skip"),
        Line2D([], [], color=OKABE["depth_ar"], linestyle="-", lw=1.6,
               label="Depth-AR"),
        Line2D([], [], color=OKABE["depth_ar_ct"], linestyle=":", lw=1.6,
               label="Depth-AR-CT"),
        Line2D([], [], color=DENSE_COLOR, linestyle=(0, (4, 2)), lw=1.1,
               label="Dense"),
    ]
    handles += [Line2D([], [], color="0.25", linestyle="none", marker=MODEL_MARKER[m],
                       markersize=5.0, markerfacecolor="white", markeredgewidth=1.2,
                       markeredgecolor="0.25", label=m)
                for m in ("0.5B", "1.5B", "7B")]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False,
               handlelength=1.7, columnspacing=0.9, handletextpad=0.5,
               labelspacing=0.3)

    out = os.path.join(OUTDIR, "fig2a_frontier.pdf")
    tmp = out + ".tmp"
    fig.savefig(tmp, format="pdf")
    os.replace(tmp, out)
    plt.close(fig)
    print(f"[write] {out}")
    for r in report:
        print(f"   2a curve {r[0]:5s} {r[1]:12s} k={r[2]}")
    return out


# ---------------------------------------------------------------------------
# 2b data: gain vs damage, with noise floor
# ---------------------------------------------------------------------------
def fig2b():
    with open(os.path.join(RESULTS, "noise_audit.json")) as f:
        audit = json.load(f)
    with open(os.path.join(RESULTS, "jitter_bf16.json")) as f:
        jit = json.load(f)

    # REPLICATED floor (see module docstring).
    floor_q = jit["pooled"]["max_abs_delta_questions"]
    floor_n = jit["pooled"]["questions_per_config"]
    floor = floor_q / floor_n
    zthr = audit["bonferroni"]["z_threshold"]

    # dedupe: the audit lists some cells twice
    rows = {}
    for r in audit["rows"]:
        if r["method"] not in ("depth_ar", "depth_ar_ct"):
            continue
        if r["selection"] not in ("residual_damage", "recovery_top"):
            # ct_recovery_top duplicates recovery_top cells; excluded, see report
            continue
        rows[(r["model"], r["selection"], r["k"], r["method"])] = r
    rows = list(rows.values())

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H_B), constrained_layout=True)

    # measured harness noise floor, shaded around zero
    ax.axhspan(-floor * 100, floor * 100, color=SE_COLOR, alpha=0.20,
               linewidth=0.0, zorder=1)
    ax.axhline(0.0, color="0.4", linewidth=0.9, linestyle="-", zorder=2)

    for r in rows:
        short = r["model"].split("-")[-1]           # "Qwen/Qwen2.5-7B" -> "7B"
        x = r["denominator_dense_minus_plain"] * 100     # plain-skip damage, pts
        y = r["abs_delta_avg_acc"] * 100                 # signed gain, pts
        ci = 1.96 * r["se_avg_acc_diff"] * 100           # 95% CI
        sig = r["significant_bonferroni"]
        col = SEL_COLOR[r["selection"]]
        mk = MODEL_MARKER[short]
        # depth_ar = filled, depth_ar_ct = open
        face = col if r["method"] == "depth_ar" else "white"
        ax.errorbar(x, y, yerr=ci, color=col, ecolor=col,
                    elinewidth=1.0 if not sig else 1.6,
                    capsize=2.0, capthick=1.0, zorder=4 if not sig else 6,
                    marker=mk, markersize=6.5 if sig else 5.0,
                    markerfacecolor=face,
                    markeredgecolor=SIG_RING if sig else col,
                    markeredgewidth=1.6 if sig else 1.2,
                    linestyle="none")

    ax.set_xlabel("Plain-skip damage (acc. pts)")
    ax.set_ylabel("Gain over plain skip\n(acc. pts)")
    ax.grid(True, linewidth=0.4, alpha=0.35, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(width=0.8, length=3)
    ax.set_xlim(0, 46)

    handles = [
        Line2D([], [], color=SEL_COLOR["residual_damage"], marker="o",
               linestyle="none", markersize=5.5,
               markerfacecolor=SEL_COLOR["residual_damage"],
               label="Deployable"),
        Line2D([], [], color=SEL_COLOR["recovery_top"], marker="o",
               linestyle="none", markersize=5.5,
               markerfacecolor=SEL_COLOR["recovery_top"],
               label="Oracle"),
        Line2D([], [], color="0.25", marker="o", linestyle="none", markersize=6.5,
               markerfacecolor="0.25", markeredgecolor=SIG_RING, markeredgewidth=1.6,
               label="Bonferroni sig."),
        Line2D([], [], color="0.25", marker="o", linestyle="none", markersize=5.0,
               markerfacecolor="white", markeredgecolor="0.25",
               label="CT variant (open)"),
        Patch(facecolor=SE_COLOR, alpha=0.25, edgecolor="none",
              label=f"Noise floor {floor_q}/{floor_n}"),
    ]
    handles += [Line2D([], [], color="0.25", linestyle="none", marker=MODEL_MARKER[m],
                       markersize=5.0, markerfacecolor="white", markeredgewidth=1.2,
                       markeredgecolor="0.25", label=m)
                for m in ("0.5B", "1.5B", "7B")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False,
               handlelength=1.2, columnspacing=0.8, handletextpad=0.4,
               labelspacing=0.3)

    out = os.path.join(OUTDIR, "fig2b_significant_gains.pdf")
    tmp = out + ".tmp"
    fig.savefig(tmp, format="pdf")
    os.replace(tmp, out)
    plt.close(fig)

    print(f"[write] {out}")
    print(f"   noise floor drawn = {floor_q}/{floor_n} = {floor*100:.2f} acc pts "
          f"(REPLICATED bf16; submitted text cites 4/900 = 0.44 pts)")
    print(f"   Bonferroni z threshold = {zthr:.3f}, family = "
          f"{audit['bonferroni']['family_size']}")
    print(f"   plotted {len(rows)} depth_ar/depth_ar_ct cells")
    sig = [r for r in rows if r["significant_bonferroni"]]
    print(f"   significant: {len(sig)}")
    for r in sorted(sig, key=lambda r: -r["z_abs_delta_over_se"]):
        print(f"     {r['model']:20s} {r['selection']:16s} k={r['k']:<3} "
              f"{r['method']:12s} dmg={r['denominator_dense_minus_plain']*100:5.1f}pt "
              f"gain={r['abs_delta_avg_acc']*100:+5.1f}pt "
              f"({r['net_questions_vs_plain_skip']:+d}/900) z={r['z_abs_delta_over_se']:.2f}")
    # the honesty check: high damage that produced NOTHING
    print("   high-damage cells that are NOT significant (damage > 25 pts):")
    for r in sorted(rows, key=lambda r: -r["denominator_dense_minus_plain"]):
        if r["denominator_dense_minus_plain"] * 100 > 25 and not r["significant_bonferroni"]:
            print(f"     {r['model']:20s} {r['selection']:16s} k={r['k']:<3} "
                  f"{r['method']:12s} dmg={r['denominator_dense_minus_plain']*100:5.1f}pt "
                  f"gain={r['abs_delta_avg_acc']*100:+5.1f}pt z={r['z_abs_delta_over_se']:.2f}")
    return out


if __name__ == "__main__":
    os.makedirs(OUTDIR, exist_ok=True)
    fig2a()
    print()
    fig2b()
