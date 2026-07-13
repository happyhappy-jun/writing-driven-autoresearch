#!/usr/bin/env python3
"""Regenerate BOTH of the paper's tables directly from the result JSONs.

    ~/gen-table.py --check      # regenerate and diff against the committed .tex (exit 1 on drift)
    ~/gen-table.py --write      # regenerate and overwrite the committed .tex
    ~/gen-table.py t1|t2        # print one table body to stdout

Why this exists: at T+2:35 there are ~180 numbers to move from JSON into LaTeX under
deadline. Typing them is the likeliest way a wrong number reaches the PDF, and a
transcription slip is indistinguishable from a fabrication once printed. This reads the
files and emits the rows, so the number in the table IS the number that was measured.

RULE 9 (typography is a claim): emphasis is derived from the DATA, never from ownership.
There is deliberately no "bold our method" branch in this file. Bolding marks the best
value in each column, whoever attains it — which is why Plain Skip bolds the accuracy
columns and Depth-AR bolds NLL. The bolding IS the finding; faking it would be a false
claim that no numeric check could catch.

It also cross-checks every gap-recovered value against a recomputation and fails loud on
disagreement, and asserts every run's layer sets are identical across methods (the claim
both table captions make).
"""
import json, pathlib, re, subprocess, sys

R = pathlib.Path.home() / "ralph" / "results"
W = pathlib.Path.home() / "writing"
load = lambda n: json.load(open(R / n))

PH = lambda s: r"\phm{" + s + "}"


# ---------------------------------------------------------------- Table 1 (selection)
T1_SEL = [
    ("predictability",  r"\makecell[l]{Predictability $P_\ell$ \\ \footnotesize(no skipping needed)}"),
    ("oracle_lite",     r"\makecell[l]{Lowest single-layer \\ \footnotesize damage (dev set)}"),
    ("recovery_top",    r"\makecell[l]{Measured recovery \\ \footnotesize(dev set)}"),
]
T1_METH = [("copy_update", "Copy Update"),
           ("depth_ar1",   "Scalar AR(1)"),
           ("depth_ar_diag", r"\textbf{\mname (Ours)}")]


def table1():
    probe = load("r2probe_0.5b.json")["runs"]
    out = []
    for si, (sel, label) in enumerate(T1_SEL):
        if si:
            out.append(r"\graymidrule")
        vals = {m: {k: probe[f"{sel}_k{k}"]["gap_recovered_nll"][m] for k in (2, 4)}
                for m, _ in T1_METH}
        # best (highest recovery) per budget column, whoever attains it
        best = {k: max(vals[m][k] for m, _ in T1_METH) for k in (2, 4)}
        out.append(r"\multirow{3}{*}{%s}" % label)
        for m, mlabel in T1_METH:
            cells = []
            for k in (2, 4):
                v = vals[m][k]
                s = PH(f"${v:+.3f}$")
                cells.append(r"\textbf{%s}" % s if abs(v - best[k]) < 1e-12 else s)
            out.append(r"  & %-22s & %s & %s \\" % (mlabel, cells[0], cells[1]))
    return "\n".join(out)


# ---------------------------------------------------------------- Table 2 (downstream)
# (file, model, n_layers, examples-per-task) — n differs by scale; see rule 10.
T2_SRC = [("r2_compose_0.5b.json", "Qwen2.5-0.5B", 24, 100),
          ("r3_verify_1.5b.json",  "Qwen2.5-1.5B", 28, 300),
          ("r4_headline_7b.json",  "Qwen2.5-7B",   28, 300)]
TASKS = ("hellaswag", "piqa", "arc_easy")
T2_METH = [("plain_skip",  "Plain Skip"),
           ("copy_update", "Copy Update"),
           ("depth_ar1",   "Scalar AR(1)"),
           ("depth_ar",    r"\textbf{\mname (Ours)}")]
# (json key, decimals, lower_is_better, scale)
T2_COLS = [("wikitext2_nll", 2, True, 1),
           ("hellaswag", 1, False, 100),
           ("piqa",      1, False, 100),
           ("arc_easy",  1, False, 100),
           ("avg_acc",   1, False, 100)]


def table2(only=None):
    out = []
    src = [r for r in T2_SRC if only is None or r[1] in only]
    for i, (fname, model, L, NEX) in enumerate(src):
        runs = load(fname)["runs"]
        # \midrule under the column header for the first block, and between model blocks
        # after that. (The splice marker is the first \multicolumn, so the rule that used
        # to sit above it in the head is not preserved: the generator must emit it.)
        out.append(r"\midrule")
        out.append(r"\multicolumn{8}{c}{\textit{\cellcolor[HTML]{EFEFEF}%s ($L=%d$)}} \\" % (model, L))
        out.append(r"\midrule")
        dn = runs["residual_damage_k2"]["methods"]["dense"]
        cells = " & ".join(PH("%.*f" % (d, dn[k] * sc)) for k, d, _, sc in T2_COLS)
        out.append(r"Dense                  & 0/%d & %s & \\" % (L, cells))
        for k in (2, 4):
            run = runs[f"residual_damage_k{k}"]
            assert run.get("layers_identical_across_methods") is True, \
                f"{model} k={k}: layer sets are NOT identical across methods — " \
                f"both table captions claim they are."
            m, rec = run["methods"], run["recovery"]
            # best per column across the skip methods; NOT "ours" (rule 9)
            best = {}
            for key, d, lower, sc in T2_COLS:
                vs = [m[mk][key] for mk, _ in T2_METH]
                best[key] = (min if lower else max)(vs)
            out.append(r"\graymidrule")
            for mk, mlabel in T2_METH:
                v, cs = m[mk], []
                for key, d, lower, sc in T2_COLS:
                    s = PH("%.*f" % (d, v[key] * sc))
                    cs.append(r"\textbf{%s}" % s if abs(v[key] - best[key]) < 1e-12 else s)
                g = 0.0 if mk == "plain_skip" else rec[mk]["gap_recovered_avg_acc"] * 100
                # RULE 10: a recovered-gap fraction on a tiny denominator anchors a reader
                # on a number that means nothing. Carry the absolute count INLINE, not in a
                # footnote — 7B k=4's "+35.5%" is +22 correct answers of 900 (z=1.18, n.s.).
                net = sum(round((v[t] - m["plain_skip"][t]) * NEX) for t in TASKS)
                # cross-check the file's gap against a recomputation from raw accuracies
                da, pa, ma = (m["dense"]["avg_acc"], m["plain_skip"]["avg_acc"], v["avg_acc"])
                if mk != "plain_skip" and abs(da - pa) > 1e-9:
                    calc = (ma - pa) / (da - pa) * 100
                    if abs(calc - g) > 0.15:
                        print(f"!! {model} k={k} {mk}: gap_recovered in file ({g:.1f}%) "
                              f"disagrees with recomputed ({calc:.1f}%)", file=sys.stderr)
                        sys.exit(1)
                gap = ("" if mk == "plain_skip"
                       else PH(f"{g:+.1f}") + r"\%\ (" + PH(f"{net:+d}") + r")")
                out.append(r"%-22s & %d/%d & %s & %s \\"
                           % (mlabel, k, L, " & ".join(cs), gap))
    return "\n".join(out)


# ---------------------------------------------------------------- splice / check
def splice(path, body, first, last=r"\bottomrule"):
    """Replace the region between the first marker line and \\bottomrule.

    The head is normalized by stripping any trailing \\midrule, because the BODY emits its
    own leading rule. Without this the generator is not idempotent: each --write would add
    another \\midrule under the column header.
    """
    s = pathlib.Path(path).read_text()
    a = s.index(first)
    b = s.index(last, a)
    head = re.sub(r'(?:\\midrule\s*)+$', '', s[:a])
    return head + body + "\n" + s[b:]


# MAIN TABLE = 7B only (the strongest block leads). The 0.5B/1.5B light-budget blocks move to
# the KEPT appendix, not the archival one: the necessity claim and the family-of-63 accounting
# both cite them, and removing counted comparisons from the submission would be indefensible.
TARGETS = [
    (W / "tables" / "selection_table.tex", table1, r"\multirow{3}{*}{\makecell[l]{Predictability"),
    (W / "tables" / "main_table.tex", lambda: table2(only=["Qwen2.5-7B"]),
     r"\multicolumn{8}{c}{\textit{\cellcolor[HTML]{EFEFEF}Qwen2.5-"),
    (W / "tables" / "light_budget_table.tex", lambda: table2(only=["Qwen2.5-0.5B", "Qwen2.5-1.5B"]),
     r"\multicolumn{8}{c}{\textit{\cellcolor[HTML]{EFEFEF}Qwen2.5-"),
]

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if arg == "t1":
        print(table1()); sys.exit(0)
    if arg == "t2":
        print(table2()); sys.exit(0)

    drift = 0
    for path, fn, marker in TARGETS:
        new = splice(path, fn(), marker)
        old = path.read_text()
        if arg == "--write":
            path.write_text(new)
            print(f"wrote {path.name}")
        elif new != old:
            drift += 1
            print(f"DRIFT {path.name}: regenerated output differs from the committed file")
            tmp = pathlib.Path("/tmp") / (path.name + ".regen")
            tmp.write_text(new)
            subprocess.run(["diff", "-u", str(path), str(tmp)])
        else:
            print(f"  ok  {path.name}: regenerates byte-identical from the JSONs")
    sys.exit(1 if drift else 0)
