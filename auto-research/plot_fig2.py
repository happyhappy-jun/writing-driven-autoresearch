#!/usr/bin/env python3
"""
Figure 2 -- the dissociation figure.

Depth-AR recovers language-model likelihood (left panel: NLL below plain skip)
but NOT downstream function (right panel: accuracy at or below plain skip).

Pure matplotlib over existing JSON. CPU only, no model loading.

Only `residual_damage_*` runs are used. `recovery_top_*` runs are deliberately
excluded (they select layers nobody would deploy-skip; they belong in a table).

To add the 7B model when it lands: it is already listed in MODELS below and is
skipped automatically if the file is missing. No other change needed.

UNCERTAINTY CONVENTION (accuracy panel only)
--------------------------------------------
Normal (Wald) +/-1 standard error, NOT Wilson.  Rationale: a Wilson interval is
defined for a SINGLE binomial proportion, whereas the plotted quantity `avg_acc`
is the unweighted MEAN of T=3 independent task accuracies (hellaswag, piqa,
arc_easy), each measured on n = config.n_task_examples items.  The coherent
interval for a mean-of-proportions is the normal SE of that mean, so that is what
is drawn.  Every SE is computed from the REAL per-task accuracies stored in the
JSON and the REAL n -- nothing is assumed, invented, or set to p=0.5.

    SE_binom(avg_acc) = (1/T) * sqrt( sum_t p_t (1 - p_t) / n )
    SE_binom(delta)   = (1/T) * sqrt( sum_t [ pA_t(1-pA_t) + pB_t(1-pB_t) ] / n )

SE_binom(delta) treats the two methods as independent.  They are in fact
evaluated on the SAME items, so the true paired SE is smaller; the independent
form is the CONSERVATIVE (wider) choice and is used deliberately.

HARNESS JITTER (added in quadrature, accuracy panel only)
---------------------------------------------------------
Binomial error is not the only noise source.  Re-running one IDENTICAL config
with a different task batch shape moves avg_acc by ~4/900 = 0.44 accuracy points
while the NLL stays bit-identical.  That reproducibility floor is treated as an
SD on any single accuracy measurement and folded in:

    SE(avg_acc) = sqrt( SE_binom(avg_acc)^2 + JITTER^2 )
    SE(delta)   = sqrt( SE_binom(delta)^2 + (sqrt(2)*JITTER)^2 )   # both arms jitter

This is not a guess: the figure's own inputs contain the duplicate.  1.5B k=2
appears in BOTH r3_verify_1.5b.json and ct_verify_1.5b_k2.json with bit-identical
NLL (2.4690 / 2.4576) but accuracy differing by +0.44 pt (plain_skip) and
+0.22 pt (depth_ar) -- exactly the quoted floor, measured, not assumed.

Reference magnitudes at the worst case p=0.5 (binomial -> total):
    n=100 (0.5B):  SE(avg_acc) 2.89 -> 2.92 pts,  SE(delta) 4.08 -> 4.13 pts
    n=300 (1.5B):  SE(avg_acc) 1.67 -> 1.73 pts,  SE(delta) 2.36 -> 2.43 pts
Jitter is small next to the binomial term, so the bands widen only slightly --
which is itself the honest result: accuracy is dominated by sampling error.

The NLL panel carries NO error bars: the JSON stores a single corpus-level NLL
with no per-sequence spread, so no honest SE is available.  None is invented.
(The duplicate cells above show NLL reproduces bit-exactly, so its jitter is 0.)
"""

import glob
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
# Canvas: the verified v3 asset saved to 437.1 x 242.2 pt. Held fixed.
# EXACT v3 canvas: 437.12 x 242.24 pt / 72 = inches. Held fixed, to the point.
FIGW, FIGH = 437.117 / 72.0, 242.244 / 72.0

RESULTS_DIR = "/home/lobster/ralph/results"
OUT_PDF = "/home/lobster/writing/figures/fig2_dissociation.pdf"

# (label, marker, primary files, secondary globs).
#
# Points are keyed by k.  PRIMARY files win any k they cover; SECONDARY globs
# (the aggressive-budget pareto sweep and the cross-token ct runs) only fill in
# k values the primary files do not have.  A model with no files at all is
# skipped silently, so pareto_7b_* appears automatically the moment it lands.
MODELS = [
    ("0.5B", "o", ["r2_compose_0.5b.json"],
     ["pareto_0.5b_*.json", "ct_compose_0.5b_*.json"]),
    ("1.5B", "s", ["r3_verify_1.5b.json"],
     ["pareto_1.5b_*.json", "ct_verify_1.5b_*.json"]),
    ("7B", "^", ["r4_headline_7b.json"],
     ["pareto_7b_*.json", "ct_*7b*.json"]),
]

# HARD REQUIREMENT: only residual_damage_* runs, never recovery_top_*.
# This is enforced on the RUN KEY inside each file, not on the filename, so the
# pareto_0.5b_recovery_top_*.json files are rejected by construction even though
# the glob above happily picks them up.
RUN_PREFIX = "residual_damage_"

# Okabe-Ito colorblind-safe palette.  Meaning is never carried by color alone:
# every method also gets its own linestyle, and every model its own marker.
METHODS = [
    # key,          label,                      color,      linestyle,   lw,  ms
    ("plain_skip", "Plain skip", "#E69F00", "--", 1.5, 5.5),
    ("depth_ar1", "Depth-AR (scalar)", "#009E73", ":", 1.3, 4.5),
    ("depth_ar", "Depth-AR (per-channel)", "#0072B2", "-", 1.8, 6.0),
]
DENSE_COLOR = "#555555"
DENSE_DASHES = [(0, (4, 2)), (0, (1, 1.5)), (0, (5, 1, 1, 1))]  # one per model

METRICS = [
    ("wikitext2_nll", "WikiText-2 NLL (lower better)"),
    ("avg_acc", "Avg. downstream accuracy (higher better)"),
]
ACC_METRIC = "avg_acc"
SE_COLOR = "#666666"

# Measured harness reproducibility floor: re-running one IDENTICAL config with a
# different task batch shape moves avg_acc by ~4/900 = 0.44 accuracy points while
# NLL stays bit-identical.  Treated as an SD on any single accuracy measurement
# and added in quadrature with the binomial SE (accuracy panel only).
# This figure's own inputs confirm it: 1.5B k=2 appears in both r3_verify and
# ct_verify with bit-identical NLL but accuracy differing by +0.44 pt.
HARNESS_JITTER = 0.0044


# ----------------------------------------------------------------------------
# Binomial uncertainty (see module docstring: normal +/-1 SE on a mean of T
# proportions, computed from the real per-task p_t and the real n)
# ----------------------------------------------------------------------------
def se_avg_acc(per_task, n):
    """Total SE of one avg_acc: binomial SE of a mean of T task accuracies,
    plus the measured harness jitter, added in quadrature."""
    T = len(per_task)
    var = sum(p * (1.0 - p) / n for p in per_task)
    se_binom = math.sqrt(var) / T
    return math.hypot(se_binom, HARNESS_JITTER)


def se_diff_avg_acc(per_task_a, per_task_b, n):
    """Total SE of (avg_acc A - avg_acc B).  Binomial part treats the two methods
    as independent (conservative; they are actually scored on the same items).
    Both arms carry harness jitter, so the jitter enters as sqrt(2)*JITTER."""
    T = len(per_task_a)
    var = sum(pa * (1.0 - pa) / n + pb * (1.0 - pb) / n
              for pa, pb in zip(per_task_a, per_task_b))
    se_binom = math.sqrt(var) / T
    return math.hypot(se_binom, math.sqrt(2.0) * HARNESS_JITTER)


# ----------------------------------------------------------------------------
# Load
# ----------------------------------------------------------------------------
def _collect(patterns):
    """Expand globs/filenames under RESULTS_DIR into a sorted list of paths."""
    hits = []
    for pat in patterns:
        hits.extend(sorted(glob.glob(os.path.join(RESULTS_DIR, pat))))
    return hits


def load_model(primary, secondary):
    """Merge every residual_damage_* run for one model, keyed by k.

    Primary files win any k they cover; secondary files only fill k values the
    primary files lack.  Nothing is averaged across files -- each plotted point
    comes from exactly one run in exactly one file, and its source is recorded.
    """
    cells = {}          # k -> (run_dict, n, tasks, source_filename)
    for rank, paths in enumerate((_collect(primary), _collect(secondary))):
        for path in paths:
            with open(path) as f:
                d = json.load(f)
            n = d["config"]["n_task_examples"]
            for rk, rv in d["runs"].items():
                if not rk.startswith(RUN_PREFIX):
                    continue          # <-- recovery_top_* dies here
                k = rv["k"]
                if k in cells and cells[k][3] <= rank:
                    continue          # a same-or-higher-priority file already has it
                reserved = {"wikitext2_nll", "avg_acc"}
                tasks = [t for t in rv["methods"]["dense"] if t not in reserved]
                cells[k] = (rv, n, tasks, rank, os.path.basename(path))

    if not cells:
        return None

    ks = sorted(cells)
    runs = [cells[k][0] for k in ks]
    ns = [cells[k][1] for k in ks]
    tasks = cells[ks[0]][2]
    sources = {k: cells[k][4] for k in ks}
    if len({cells[k][1] for k in ks}) > 1:
        print(f"  [warn] mixed n_task_examples across k: "
              f"{ {k: cells[k][1] for k in ks} }")

    fracs = [rv["frac_blocks_skipped"] for rv in runs]
    series, sems = {}, {}
    for metric, _ in METRICS:
        for mkey, *_ in METHODS:
            series[(mkey, metric)] = [rv["methods"][mkey][metric] for rv in runs]

    def ptasks(mkey, rv):
        return [rv["methods"][mkey][t] for t in tasks]

    for mkey, *_ in METHODS:
        sems[mkey] = [se_avg_acc(ptasks(mkey, rv), n) for rv, n in zip(runs, ns)]
    sems[("diff", "depth_ar", "plain_skip")] = [
        se_diff_avg_acc(ptasks("depth_ar", rv), ptasks("plain_skip", rv), n)
        for rv, n in zip(runs, ns)
    ]

    dense = {metric: runs[0]["methods"]["dense"][metric] for metric, _ in METRICS}

    return dict(fracs=fracs, ks=ks, series=series, sems=sems, dense=dense,
                n=ns[0], ns=ns, tasks=tasks, sources=sources)


# ----------------------------------------------------------------------------
# Style
# ----------------------------------------------------------------------------
matplotlib.rcParams.update({
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.family": "sans-serif",
    # Fonts sized for the PRINTED page: this asset is 437pt native but is placed
    # at 0.62\textwidth = 301pt, a 0.689 scale factor, so every native size is
    # multiplied by 0.689 on paper. Floor is 10pt native -> 6.9pt effective.
    "font.size": 12,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.5,
    "figure.dpi": 200,
})


def main():
    loaded = []
    for label, marker, primary, secondary in MODELS:
        data = load_model(primary, secondary)
        if data is None:
            print(f"[skip] {label}: no residual_damage runs found -- omitted")
            continue
        loaded.append((label, marker, data))
        print(f"[ok]   {label}: n={data['n']} per task")
        for k in data["ks"]:
            i = data["ks"].index(k)
            print(f"         k={k:<3} frac={data['fracs'][i]:.4f}  <- {data['sources'][k]}")

    if not loaded:
        raise SystemExit("no data files found")

    # LAYOUT NOTE (v4).
    # The asset is 437pt native but is placed at 0.62\textwidth = 301pt, a 0.689
    # scale factor, so a 7pt native glyph printed at 4.8pt -- illegible. Fonts are
    # now floored at 10pt native (6.9pt effective). At that size the old in-panel
    # insets collided with the y-labels, the dense annotations and the legend, so
    # the two delta views were MOVED OUT of the panels into their own short strips
    # directly below each panel, sharing that panel's x-axis. Same canvas, same
    # aspect, same data, same numbers -- only the arrangement changed. Nothing was
    # dropped and no font was shrunk back below the floor.
    # constrained_layout solves all spacing: it reserves room for the y-labels,
    # the x-labels, the titles AND (via loc="outside lower center") the legend,
    # so nothing can clip or overlap. figsize is tuned so the saved tight bbox
    # reproduces the verified v3 canvas of 437.1 x 242.2 pt EXACTLY.
    fig = plt.figure(figsize=(FIGW, FIGH), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[2.35, 1.0])
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    daxes = [fig.add_subplot(gs[1, 0], sharex=axes[0]),
             fig.add_subplot(gs[1, 1], sharex=axes[1])]

    # Short two-line y-labels: on an 85pt-tall axes a one-line 12pt label would
    # overflow the axes vertically and inflate the saved canvas.
    top_ylabel = ["WikiText-2 NLL\n(lower better)", "Downstream acc.\n(higher better)"]
    delta_ylabel = [r"$\Delta$NLL", r"$\Delta$Acc"]
    # dense reference lines: full width (no inset overlaps them any more)
    # Dense reference lines are labelled in-panel ONLY on the accuracy panel.
    # On the NLL panel the three dense levels are 1.98 / 2.33 / 2.76 on a 2-10.5
    # axis: about 5pt apart on the printed page. No 10pt label fits there without
    # colliding with the curves or with the other labels, so rather than shrink
    # the text below the legibility floor the labels are omitted on that panel.
    # Nothing is lost: the per-model dash patterns are IDENTICAL across the two
    # panels, so the mapping is read off the accuracy panel, and the legend
    # carries the "Dense (no skip)" entry.
    dense_lab_x = [None, [0.99, 0.99, 0.99]]

    ar_color = dict((m[0], m[2]) for m in METHODS)["depth_ar"]

    for pi, (ax, dax, (metric, _)) in enumerate(zip(axes, daxes, METRICS)):
        # ---- dense reference lines (one per model)
        for mi, (label, marker, data) in enumerate(loaded):
            y = data["dense"][metric]
            ax.axhline(y, color=DENSE_COLOR, linewidth=1.2,
                       linestyle=DENSE_DASHES[mi % len(DENSE_DASHES)],
                       zorder=1, alpha=0.9)
            if dense_lab_x[pi] is not None:
                ax.annotate(label, xy=(dense_lab_x[pi][mi], y),
                            xycoords=("axes fraction", "data"),
                            va="bottom", ha="right", fontsize=10, color=DENSE_COLOR)

        # ---- method curves. Accuracy points carry binomial+jitter +/-1 SE bars.
        for label, marker, data in loaded:
            for mkey, mlabel, color, ls, lw, ms in METHODS:
                yerr = data["sems"][mkey] if metric == ACC_METRIC else None
                ax.errorbar(data["fracs"], data["series"][(mkey, metric)],
                            yerr=yerr,
                            color=color, linestyle=ls, linewidth=lw,
                            marker=marker, markersize=ms,
                            markerfacecolor="white", markeredgewidth=1.2,
                            markeredgecolor=color,
                            ecolor=color, elinewidth=1.0, capsize=2.0,
                            capthick=1.0, zorder=3)

        ax.set_ylabel(top_ylabel[pi])
        ax.grid(True, linewidth=0.4, alpha=0.35, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(width=0.8, length=3, labelbottom=False)
        ax.set_xlim(0.0, 0.46)

        # ---- delta strip: depth_ar minus plain_skip (same numbers, differenced)
        if metric == ACC_METRIC:
            # Two-tone band: a few deltas poke past +/-1 SE, so the outer +/-1.96 SE
            # band is drawn too, showing they are still inside sampling noise.
            for label, marker, data in loaded:
                se = data["sems"][("diff", "depth_ar", "plain_skip")]
                for mult, alpha in ((1.96, 0.07), (1.0, 0.15)):
                    dax.fill_between(data["fracs"],
                                     [-mult * s for s in se], [mult * s for s in se],
                                     color=SE_COLOR, alpha=alpha, linewidth=0.0,
                                     zorder=1)
        for label, marker, data in loaded:
            delta = [a - b for a, b in zip(data["series"][("depth_ar", metric)],
                                           data["series"][("plain_skip", metric)])]
            # NLL deltas are monotone -> join them. Accuracy deltas scatter around
            # zero with no trend; joining them would invent a trajectory.
            ls = "none" if metric == ACC_METRIC else "-"
            dax.plot(data["fracs"], delta, color=ar_color, linestyle=ls, linewidth=1.4,
                     marker=marker, markersize=4.5, markerfacecolor="white",
                     markeredgewidth=1.1, markeredgecolor=ar_color, zorder=3)
        dax.axhline(0.0, color="#E69F00", linestyle="--", linewidth=1.2, zorder=2)
        dax.set_ylabel(delta_ylabel[pi])
        dax.set_xlabel("Fraction of blocks skipped")
        dax.grid(True, linewidth=0.4, alpha=0.35, zorder=0)
        dax.set_axisbelow(True)
        for s in ("top", "right"):
            dax.spines[s].set_visible(False)
        dax.tick_params(width=0.8, length=3)
        dax.margins(y=0.20)
        dax.set_xlim(0.0, 0.46)

    # Panel titles are DESCRIPTIVE, not verdicts.  With the aggressive budgets
    # added, neither old verdict holds universally:
    #   * 7B k=12 (frac 0.429): depth_ar NLL is WORSE than plain skip (+0.253).
    #   * 7B k=8  (frac 0.286): depth_ar accuracy is +9.89 pt, z=+4.16, which
    #     CLEARS the Bonferroni threshold -- a genuinely significant gain.
    # The figure must not assert a claim its own data contradicts.
    axes[0].set_title("Likelihood", fontsize=13, pad=4)
    axes[1].set_title("Downstream accuracy", fontsize=13, pad=4)

    method_handles = [
        Line2D([], [], color=c, linestyle=ls, linewidth=lw, label=lab)
        for _, lab, c, ls, lw, _ in METHODS
    ]
    method_handles.append(
        Line2D([], [], color=DENSE_COLOR, linestyle=DENSE_DASHES[0], linewidth=1.2,
               label="Dense (no skip)")
    )
    method_handles.append(
        Patch(facecolor=SE_COLOR, alpha=0.25, edgecolor=SE_COLOR, linewidth=0.6,
              label=r"$\pm$1 / $\pm$1.96 SE")
    )
    model_handles = [
        Line2D([], [], color="0.25", linestyle="none", marker=marker, markersize=5.5,
               markerfacecolor="white", markeredgewidth=1.2, markeredgecolor="0.25",
               label=label)
        for label, marker, _ in loaded
    ]
    # "outside lower center" makes constrained_layout ALLOCATE space for the
    # legend rather than letting it land on top of the x-labels.
    fig.legend(handles=method_handles + model_handles,
               loc="outside lower center", ncol=4,
               frameon=False, handlelength=1.6, columnspacing=0.8,
               handletextpad=0.5)

    os.makedirs(os.path.dirname(OUT_PDF), exist_ok=True)
    # Atomic replace: a LaTeX float already points at OUT_PDF, so never leave a
    # half-written file where a build could pick it up.
    tmp = OUT_PDF + ".tmp"
    # NB: deliberately NOT bbox_inches="tight". constrained_layout already fits
    # every label inside the canvas; re-trimming would change the locked 437x242pt
    # dimensions the LaTeX float depends on. Saving at the exact figsize keeps the
    # canvas bit-identical to v3.
    fig.savefig(tmp, format="pdf")
    os.replace(tmp, OUT_PDF)
    print(f"[write] {OUT_PDF}")

    # -------------------------------------------------------------------
    # Sanity report: is the dissociation actually there, per model, per k?
    # -------------------------------------------------------------------
    print("\ndepth_ar vs plain_skip (residual_damage runs only):")
    outside, nll_worse = [], []
    for label, _, data in loaded:
        print(f"  -- {label}: n={data['n']} per task, tasks={data['tasks']}")
        for i, k in enumerate(data["ks"]):
            dn = data["series"][("depth_ar", "wikitext2_nll")][i]
            pn = data["series"][("plain_skip", "wikitext2_nll")][i]
            da = data["series"][("depth_ar", "avg_acc")][i]
            pa = data["series"][("plain_skip", "avg_acc")][i]
            d = da - pa
            se = data["sems"][("diff", "depth_ar", "plain_skip")][i]
            inside = abs(d) <= se
            if not inside:
                outside.append((label, k, d, se))
            if dn >= pn:
                nll_worse.append((label, k, dn - pn))
            # delta expressed in raw correct answers, summed over the T tasks
            n_items = data["ns"][i] * len(data["tasks"])
            z = d / se
            print(f"     k={k:<3} frac={data['fracs'][i]:.3f}  "
                  f"dNLL={dn - pn:+.4f} ({'BETTER' if dn < pn else 'WORSE':>6})   "
                  f"dACC={d * 100:+.2f}pt ({d * n_items:+.0f}/{n_items})  "
                  f"+/-1SE={se * 100:.2f}pt  z={z:+.2f}  "
                  f"[{'inside' if inside else 'OUTSIDE'}]")

    print("\nSE composition at worst-case p=0.5 "
          f"(T={len(loaded[0][2]['tasks'])} tasks, jitter={HARNESS_JITTER*100:.2f}pt):")
    for label, _, data in loaded:
        n, T = data["n"], len(data["tasks"])
        b = 0.5 / math.sqrt(T * n)
        print(f"  {label} n={n}: binom SE(avg)={b*100:.2f}pt -> total "
              f"{math.hypot(b, HARNESS_JITTER)*100:.2f}pt | "
              f"binom SE(diff)={b*math.sqrt(2)*100:.2f}pt -> total "
              f"{math.hypot(b*math.sqrt(2), math.sqrt(2)*HARNESS_JITTER)*100:.2f}pt")

    if nll_worse:
        print("\n*** WARNING: depth_ar NLL NOT better than plain_skip at: ***")
        for label, k, d in nll_worse:
            print(f"    {label} k={k}: dNLL={d:+.4f}")
    else:
        print("\nNLL: depth_ar beats plain_skip at EVERY plotted point.")

    if outside:
        print("*** WARNING: accuracy deltas OUTSIDE +/-1 SE: ***")
        for label, k, d, se in outside:
            print(f"    {label} k={k}: {d*100:+.2f}pt vs SE {se*100:.2f}pt")
    else:
        print("Accuracy: every delta lies INSIDE +/-1 SE (binomial + harness "
              "jitter). No downstream gain -- and no loss -- is supportable.")


if __name__ == "__main__":
    # Optional output-path override, so the SAME design can be re-emitted as the
    # archival appendix figure (fig2c) without touching fig2_dissociation.pdf,
    # which writing's live float still points at.
    import sys
    if len(sys.argv) > 1:
        globals()["OUT_PDF"] = sys.argv[1]
    main()
