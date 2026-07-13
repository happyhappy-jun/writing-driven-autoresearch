#!/usr/bin/env python3
"""
Fig 1 (a,b) for the ICML submission.

(a) fig1a_predictability.pdf : held-out predictability P_l vs normalized depth
(b) fig1b_recovery_vs_P.pdf  : recovery-of-NLL-damage vs P_l, with Spearman rho

Pure matplotlib + scipy over existing JSON result files. CPU only, no model load.
Every number plotted is read straight from the JSON. Nothing is smoothed,
interpolated, clipped, or otherwise "fixed".

Re-run as-is when new result files land: add entries to MODELS / VARIANTS below.
Missing files are silently skipped, so 1.5B / 7B / Variant-C curves appear
automatically once their JSONs exist.
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy.stats import spearmanr

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
RESULTS_DIR = "/home/lobster/ralph/results"
OUT_DIR = "/home/lobster/writing/figures"

# The primary scan (defines the layer axis / the AR(1) numbers).
PRIMARY = os.path.join(RESULTS_DIR, "r1_layerscan_0.5b.json")

# Series to draw in panel (a). Each entry:
#   (path, key inside P_heldout / recovery, legend label, color, marker, linestyle)
# Files that do not exist are skipped without complaint.
SERIES = [
    (PRIMARY, "depth_ar1", r"AR(1)", "#0072B2", "o", "-"),
    (
        os.path.join(RESULTS_DIR, "r1v_C_0.5b.json"),
        "var_c_diag",
        r"Variant C (diag)",
        "#D55E00",
        "s",
        "--",
    ),
    # Future scans drop in here, e.g.:
    # (os.path.join(RESULTS_DIR, "r1_layerscan_1.5b.json"), "depth_ar1",
    #  r"AR(1), 1.5B", "#009E73", "^", "-."),
]

# Okabe-Ito colorblind-safe palette (subset used above):
#   #0072B2 blue, #D55E00 vermillion, #009E73 green, #CC79A7 purple

# Panel (b) is, per spec, the AR(1) scatter: X = P_l (AR(1)), Y = recovery (AR(1)),
# one point per eligible layer. Set this True to overlay the Variant-C points on
# the same axes.
#
# CAUTION before flipping it: Variant C's layer 2 has recovery = -3.675, i.e. an
# order of magnitude below every AR(1) point (which all lie in [-0.83, +0.17]).
# Sharing one linear y-axis therefore squashes the entire AR(1) cloud -- and the
# layer-3 dissociation the panel exists to show -- into a sliver. If you want
# Variant C in panel (b), it should get its own panel or a broken axis, NOT a
# silently clipped ylim (clipping would hide a real datapoint).
PANEL_B_INCLUDE_VARIANT_C = False

# --------------------------------------------------------------------------
# Style (ICML, panel placed at ~0.33-0.5\textwidth)
# --------------------------------------------------------------------------
matplotlib.rcParams.update(
    {
        "pdf.fonttype": 42,   # TrueType -> real vector text, embeddable
        "ps.fonttype": 42,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        # Sized for the PRINTED page. fig1a is placed at 0.62\linewidth and
        # fig1b at 0.78\linewidth of a 234pt ICML column, so native sizes are
        # multiplied by ~0.66 / ~0.80 on paper. The old 7.5pt ticks printed at
        # ~5pt and the mathtext subscripts (0.7x) at ~3.5pt: illegible.
        "font.size": 11,
        "axes.labelsize": 11,
        "axes.titlesize": 11,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.4,
        "grid.linewidth": 0.5,
        "grid.alpha": 0.35,
        "grid.color": "#B0B0B0",
        "axes.axisbelow": True,       # grid behind the data
        "figure.dpi": 200,
        "savefig.dpi": 200,
    }
)

# Canvas deliberately SMALLER than before. What sets legibility on paper is the
# ratio font/canvas-width, since LaTeX rescales to a fixed \linewidth fraction:
# shrinking the canvas at fixed font size raises the effective printed font.
FIGSIZE_A = (3.0, 2.35)   # 213pt native, prints at 145pt -> 6.8pt effective
FIGSIZE_B = (3.75, 2.85)  # 270pt native, prints at 183pt -> 6.8pt effective


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def load_scan(path, key, n_layers_fallback=None):
    """Return (norm_depth, P, recovery, layers) for one JSON + one predictor key.

    Returns None if the file is absent or the key is not present in it.

    NOTE: the variant files (r1v_*.json) carry `eligible_layers` but NOT the
    top-level `n_layers` that the main layer-scan has. That is a real schema
    difference in the inputs, not something to paper over: we require the depth
    normalizer to be supplied explicitly (from the primary scan) rather than
    guessing it from max(eligible_layers).
    """
    if not os.path.exists(path):
        return None
    with open(path) as f:
        d = json.load(f)

    layers = d["eligible_layers"]
    n_layers = d.get("n_layers", n_layers_fallback)
    if n_layers is None:
        raise KeyError(
            f"{os.path.basename(path)} has no 'n_layers' and no fallback was given"
        )
    lay = d["layers"]

    try:
        P = np.array([lay[str(l)]["P_heldout"][key] for l in layers], dtype=float)
        rec = np.array([lay[str(l)]["recovery"][key] for l in layers], dtype=float)
    except KeyError:
        return None

    depth = np.array(layers, dtype=float) / (n_layers - 1)
    return depth, P, rec, np.array(layers)


# --------------------------------------------------------------------------
# Panel (a): predictability vs depth
# --------------------------------------------------------------------------
def panel_a(loaded):
    fig, ax = plt.subplots(figsize=FIGSIZE_A, constrained_layout=True)

    # Plain Skip: predictability is exactly 0 by definition.
    ax.axhline(
        0.0,
        color="0.35",
        linestyle=":",
        linewidth=1.2,
        zorder=2,
        label="Plain Skip ($P \\equiv 0$)",
    )

    for (depth, P, _rec, _lay), (_p, _k, label, color, marker, ls) in loaded:
        ax.plot(
            depth,
            P,
            marker=marker,
            markersize=3.6,
            linestyle=ls,
            linewidth=1.4,
            color=color,
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=0.4,
            label=label,
            zorder=3,
        )

    # Annotate the spike (primary series only), without altering any datapoint.
    depth, P, _rec, lay = loaded[0][0]
    i3 = int(np.argmax(P))
    ax.annotate(
        f"layer {lay[i3]}",
        xy=(depth[i3] + 0.012, P[i3] - 0.02),
        xytext=(depth[i3] + 0.10, P[i3] - 0.32),
        fontsize=10,
        color="0.15",
        ha="left",
        va="top",
        arrowprops=dict(
            arrowstyle="-|>",
            color="0.35",
            linewidth=0.9,
            shrinkA=1,
            shrinkB=2,
            connectionstyle="arc3,rad=-0.2",
        ),
        zorder=5,
    )

    ax.set_xlabel(r"Normalized depth  $\ell/(L-1)$")
    ax.set_ylabel("Held-out\npredictability  $P$")
    ax.set_xlim(-0.03, 1.03)
    # Full range shown: the spike is NOT clipped away.
    ax.set_ylim(-0.08, 1.06)
    ax.grid(True, which="major", zorder=0)
    # Anchor the legend to the far upper-right. The layer-3 spike lives at
    # x ~ 0.13, so the legend must not extend left of ~0.45 in axes coords or it
    # would occlude the very datapoint this panel exists to show.
    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.005, 1.02),
        frameon=True,
        framealpha=0.95,
        edgecolor="0.8",
        handlelength=2.0,
        borderpad=0.35,
        labelspacing=0.35,
        handletextpad=0.5,
    )
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    out = os.path.join(OUT_DIR, "fig1a_predictability.pdf")
    fig.savefig(out, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------
# Panel (b): recovery vs predictability
# --------------------------------------------------------------------------
def panel_b(loaded):
    depth, P, rec, lay = loaded[0][0]  # primary = AR(1), 0.5B

    rho, pval = spearmanr(P, rec)

    if PANEL_B_INCLUDE_VARIANT_C and len(loaded) > 1:
        raise NotImplementedError(
            "Overlaying Variant C on panel (b) needs a broken/second axis; see "
            "the PANEL_B_INCLUDE_VARIANT_C comment. Refusing to clip the "
            "layer-2 recovery = -3.675 point off a shared linear axis."
        )

    fig, ax = plt.subplots(figsize=FIGSIZE_B, constrained_layout=True)

    # Plain Skip baseline: recovery = 0. Below it, "recovery" hurts.
    ax.axhline(
        0.0,
        color="0.35",
        linestyle=":",
        linewidth=1.2,
        zorder=2,
    )
    ax.text(
        0.985,
        0.012,
        "Plain Skip",
        transform=ax.get_yaxis_transform(),
        ha="right",
        va="bottom",
        fontsize=10,
        color="0.35",
        clip_on=False,
    )

    i3 = int(np.argmax(P))  # layer 3, the dissociation point
    mask = np.ones(len(P), dtype=bool)
    mask[i3] = False

    ax.scatter(
        P[mask],
        rec[mask],
        s=26,
        marker="o",
        facecolor="#0072B2",
        edgecolor="white",
        linewidth=0.5,
        alpha=0.9,
        zorder=3,
        label="AR(1) layer",
    )
    # Distinct marker + color for the annotated layer: never color alone.
    ax.scatter(
        [P[i3]],
        [rec[i3]],
        s=70,
        marker="D",
        facecolor="#D55E00",
        edgecolor="black",
        linewidth=0.7,
        zorder=4,
        label=f"layer {lay[i3]}",
    )

    ax.annotate(
        f"layer {lay[i3]}\n$P={P[i3]:+.3f}$, recovery $={rec[i3]:+.3f}$\n"
        "best predicted, worst to skip",
        xy=(P[i3], rec[i3]),
        xytext=(0.07, -0.30),
        textcoords=ax.transData,
        fontsize=10,
        color="0.12",
        ha="left",
        va="top",
        linespacing=1.25,
        bbox=dict(
            boxstyle="round,pad=0.32",
            facecolor="#FDF0E6",
            edgecolor="#D55E00",
            linewidth=0.8,
        ),
        arrowprops=dict(
            arrowstyle="-|>",
            color="#D55E00",
            linewidth=1.1,
            shrinkA=2,
            shrinkB=4,
            connectionstyle="arc3,rad=0.25",
        ),
        zorder=6,
    )

    # Spearman box: whatever it actually is.
    if pval < 1e-3:
        ptxt = f"$p={pval:.1e}$"
    else:
        ptxt = f"$p={pval:.3f}$"
    ax.text(
        0.035,
        0.03,
        f"Spearman $\\rho={rho:+.3f}$\n{ptxt}  ($n={len(P)}$)",
        transform=ax.transAxes,
        fontsize=10,
        ha="left",
        va="bottom",
        linespacing=1.3,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            edgecolor="0.6",
            linewidth=0.7,
            alpha=0.92,
        ),
        zorder=6,
    )

    ax.set_xlabel(r"Held-out predictability  $P$")
    ax.set_ylabel("Fraction of damage\nrecovered")
    ax.set_xlim(-0.06, 1.02)
    ax.set_ylim(-1.02, 0.72)
    ax.grid(True, which="major", zorder=0)
    ax.legend(
        loc="upper right",
        frameon=True,
        framealpha=0.95,
        edgecolor="0.8",
        borderpad=0.35,
        labelspacing=0.35,
        handletextpad=0.4,
    )
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    out = os.path.join(OUT_DIR, "fig1b_recovery_vs_P.pdf")
    fig.savefig(out, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return out, rho, pval


# --------------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Depth normalizer comes from the primary scan and is reused for variant
    # files, which do not carry `n_layers`.
    with open(PRIMARY) as f:
        n_layers_primary = json.load(f)["n_layers"]

    loaded = []
    for spec in SERIES:
        path, key = spec[0], spec[1]
        got = load_scan(path, key, n_layers_fallback=n_layers_primary)
        if got is None:
            print(f"[skip] {os.path.basename(path)} :: {key} (absent)")
            continue
        loaded.append((got, spec))
        print(f"[ok]   {os.path.basename(path)} :: {key} ({len(got[3])} layers)")

    if not loaded:
        raise SystemExit("No result files found.")

    a = panel_a(loaded)
    b, rho, pval = panel_b(loaded)

    _d, P, rec, _l = loaded[0][0]
    print(f"\n--- panel (b), plotted: AR(1), 0.5B ---")
    print(f"median P_l          = {np.median(P):+.4f}")
    print(f"layers with rec < 0 = {int((rec < 0).sum())} / {len(rec)}")
    print(f"Spearman rho        = {rho:+.6f}   p = {pval:.6e}   n = {len(P)}")

    # Any other loaded series: report its stats to stdout for the record. These
    # are NOT drawn in panel (b)'s stats box, which must describe only the data
    # actually plotted there.
    for (_dd, Pv, recv, _ll), spec in loaded[1:]:
        r_v, p_v = spearmanr(Pv, recv)
        print(f"\n--- not plotted in (b): {spec[2]} ---")
        print(f"median P_l          = {np.median(Pv):+.4f}")
        print(f"layers with rec < 0 = {int((recv < 0).sum())} / {len(recv)}")
        print(f"min recovery        = {recv.min():+.4f} (layer {_ll[int(np.argmin(recv))]})")
        print(f"Spearman rho        = {r_v:+.6f}   p = {p_v:.6e}   n = {len(Pv)}")

    print(f"\nwrote {a}\nwrote {b}")


if __name__ == "__main__":
    main()
