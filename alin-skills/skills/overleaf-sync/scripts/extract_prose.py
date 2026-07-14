#!/usr/bin/env python3
"""Extract readable prose from LaTeX sources for writing-voice analysis.

Given a file or directory, finds .tex sources and strips the parts that carry
*formatting* rather than *voice*: comments, math, tables/figures/algorithms,
bibliography, and most control sequences. What remains is plain sentences —
enough to characterize how the author writes (rhythm, hedging, person,
phrasing), which is the only thing overleaf-sync's voice profile records.

Stdlib only. Heuristic, not a real LaTeX parser — good enough for style sampling.

Usage:
    python3 extract_prose.py PATH [PATH ...]   # files and/or directories
    python3 extract_prose.py .                 # all .tex under cwd

Prints the extracted prose to stdout. Intended to be appended into a corpus
file that is analyzed and then discarded.
"""

import os
import re
import sys

# Environments whose *contents* are formatting/figures/math, not prose.
DROP_ENVS = [
    "equation", "equation*", "align", "align*", "alignat", "alignat*",
    "gather", "gather*", "multline", "multline*", "eqnarray", "eqnarray*",
    "math", "displaymath", "array", "matrix", "bmatrix", "pmatrix",
    "table", "table*", "tabular", "tabularx", "longtable", "wraptable",
    "figure", "figure*", "wrapfigure", "subfigure",
    "algorithm", "algorithm*", "algorithmic", "lstlisting", "verbatim",
    "thebibliography", "tikzpicture",
]

# Commands to drop entirely, including any bracket/brace arguments.
DROP_CMDS_WITH_ARGS = [
    "cite", "citep", "citet", "citeauthor", "citeyear", "ref", "eqref",
    "cref", "Cref", "autoref", "pageref", "label", "includegraphics",
    "input", "include", "bibliography", "bibliographystyle", "usepackage",
    "documentclass", "newcommand", "renewcommand", "def", "DeclareMathOperator",
    "caption", "footnote", "url", "href",
]

# Commands whose text argument should be KEPT (unwrapped to its content).
KEEP_ARG_CMDS = [
    "textbf", "textit", "emph", "text", "textsc", "textrm", "texttt",
    "section", "subsection", "subsubsection", "paragraph", "title",
]


def strip_comments(s: str) -> str:
    # Remove % to end of line, but keep escaped \%
    out = []
    for line in s.splitlines():
        res, i = [], 0
        while i < len(line):
            c = line[i]
            if c == "\\" and i + 1 < len(line):
                res.append(line[i:i + 2])
                i += 2
                continue
            if c == "%":
                break
            res.append(c)
            i += 1
        out.append("".join(res))
    return "\n".join(out)


def drop_environments(s: str) -> str:
    for env in DROP_ENVS:
        pat = re.compile(
            r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{" + re.escape(env) + r"\}",
            re.DOTALL,
        )
        s = pat.sub(" ", s)
    return s


def drop_inline_math(s: str) -> str:
    s = re.sub(r"\$\$.*?\$\$", " ", s, flags=re.DOTALL)   # display $$...$$
    s = re.sub(r"\\\[.*?\\\]", " ", s, flags=re.DOTALL)   # \[ ... \]
    s = re.sub(r"\\\(.*?\\\)", " ", s, flags=re.DOTALL)   # \( ... \)
    s = re.sub(r"(?<!\\)\$.*?(?<!\\)\$", " ", s, flags=re.DOTALL)  # $...$
    return s


def drop_cmds_with_args(s: str) -> str:
    for cmd in DROP_CMDS_WITH_ARGS:
        # \cmd, optional [..], then zero or more {..}
        pat = re.compile(r"\\" + re.escape(cmd) + r"\b(\s*\[[^\]]*\])*(\s*\{[^{}]*\})*")
        s = pat.sub(" ", s)
    return s


def unwrap_keep_cmds(s: str) -> str:
    for cmd in KEEP_ARG_CMDS:
        pat = re.compile(r"\\" + re.escape(cmd) + r"\*?\s*\{([^{}]*)\}")
        # Repeat to handle simple nesting.
        prev = None
        while prev != s:
            prev = s
            s = pat.sub(r"\1", s)
    return s


def strip_remaining_commands(s: str) -> str:
    s = re.sub(r"\\[a-zA-Z@]+\*?", " ", s)   # bare control words
    s = re.sub(r"\\[^a-zA-Z]", " ", s)        # control symbols like \\ \&
    s = s.replace("{", " ").replace("}", " ")
    s = re.sub(r"~", " ", s)
    return s


def normalize_ws(s: str) -> str:
    # Collapse runs of blank lines to a single paragraph break, trim each line.
    paras, buf = [], []
    for line in s.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            buf.append(line)
        elif buf:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return "\n\n".join(paras)


def extract(tex: str) -> str:
    tex = strip_comments(tex)
    tex = drop_environments(tex)
    tex = drop_inline_math(tex)
    tex = drop_cmds_with_args(tex)
    tex = unwrap_keep_cmds(tex)
    tex = strip_remaining_commands(tex)
    return normalize_ws(tex)


def iter_tex_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                if ".git" in root.split(os.sep):
                    continue
                for fn in sorted(files):
                    if fn.endswith(".tex"):
                        yield os.path.join(root, fn)
        elif os.path.isfile(p) and p.endswith(".tex"):
            yield p


def main(argv):
    paths = argv[1:] or ["."]
    any_out = False
    for fp in iter_tex_files(paths):
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                prose = extract(fh.read())
        except OSError as e:
            print(f"% skip {fp}: {e}", file=sys.stderr)
            continue
        if prose.strip():
            print(prose)
            print()
            any_out = True
    return 0 if any_out else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
