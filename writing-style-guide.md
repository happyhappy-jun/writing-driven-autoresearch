# Writing style guide — ICML/ES-FoMo workshop template

Derived from the STAND paper (`~/writing-template-reference.pdf`, commit `6041022`).
Rules are what the template *does*, not generic advice. Where the template is
inconsistent with itself, the rule picks one and says so.

Reference PDF: `~/writing-template-reference.pdf`
Build: `~/build-writing.sh` → `~/writing-main.pdf`

---

## 1. Hard constraints

- **Body is 4 pages.** Introduction through Conclusion must end on page 4;
  References start at the top of page 5. This is the binding limit — everything
  else in this guide follows from it.
- References and appendix are unlimited (they run pages 5–13 in the reference).
- Anonymous build: `\usepackage{icml2024}` (no `[accepted]`). The style file
  suppresses `\icmlauthorlist`, affiliations, and correspondence — leave those
  blocks in the source, they just don't render.
- Draft notice string lives in `icml2024.sty` (`\Notice@String`), not `main.tex`.

## 2. Page budget

The 4-page limit forces a specific allocation. From the reference:

| Section      | Rendered   | Rule |
|--------------|------------|------|
| Abstract     | ~200 words | One paragraph. No citations. |
| Introduction | ~1.25 pages| The longest section. Carries all motivation. |
| Motivation   | ~0.75 page | Empirical observations that justify the method. |
| Method       | ~1 page    | Mostly `\paragraph` blocks, one per component. |
| Experiments  | ~0.5 page  | Headline results only; everything else → appendix. |
| Conclusion   | ~60 words  | One paragraph. No new claims. |

**Related Works lives in the appendix**, not the body — this is a deliberate
space trade the template makes. Do the same unless you have room.

**Experiments is the compression valve.** When you run long, move detail to the
appendix and leave a pointer, exactly as the template does:

```latex
We provide further experiments and analysis in \Cref{sec:app-experiments}.
Specifically, in \Cref{sec:experiments-main-full}, we further extend the results
in \Cref{tab:main} with more baselines and models.
```

## 3. Macros — use them, always

- **Method name is a macro.** `\newcommand{\mname}{STAND\xspace}` — write
  `\mname`, never the literal name. The reference violates this 5 times in prose;
  don't copy that. Renaming the method must be a one-line change.
- First mention expands the acronym in bold:
  `\textbf{\mname (STochastic Adaptive N-gram Drafting)}`.
- `\graymidrule` separates method blocks inside tables.
- Delete `\placeholder`, `\lipsum`, `\blindtext`, `duckuments` before submitting —
  they're template scaffolding.

## 4. Citations

- **`\citep` for parenthetical, `\citet` for in-text.** Never bare `\cite`.
  The reference mixes 18 `\citep` with 22 `\cite`; standardize on `\citep`.
- Citations go at the end of the claim they support, before the period:
  `...allocating additional computational resources during inference \citep{snell2024scaling}.`
- Group related work into one call: `\citep{aggarwal2025l1, qu2025optimizing}`.
- Bibliography is `custom.bib` + `\bibliographystyle{icml2024}` (natbib).

## 5. Cross-references

- **Always `\Cref`**, never a hand-typed "Figure~\ref{...}". `\Cref` is already
  configured in `main.tex` to render "Figure 1" / "Table 2" / "Eq. (3)". The
  reference slips into manual `Figure \ref{fig:main}` twice — don't.
- Label every section, figure, and table. Naming scheme:
  - `sec:introduction`, `sec:method`, `sec:experiments`, `sec:conclusion`
  - appendix sections: `sec:app-experiments`, `sec:experiments-ablations`
  - `fig:main`, subfigures `fig:main-aime`, `fig:main-gpqa`
  - `tab:main`, `tab:treeopt`

## 6. Paragraph headers are the workhorse

Method and appendix sections are built almost entirely from run-in bold headers
(11 in the reference). Use `\paragraph` for each self-contained component; use
`\subsection` only to group several paragraphs.

```latex
\paragraph{Gumbel-Top-K sampling.} For efficient stochastic drafting, we replace
sequential sampling with a parallel approach based on the Gumbel-Top-K trick
\citep{gumbeltopk}. ...
```

Header is a noun phrase, sentence case, ends with a period, and the text starts
on the same line.

## 7. Claims must carry numbers

Every efficiency/accuracy claim in the reference is quantified, and the same
numbers repeat verbatim in abstract, intro, and experiments. Keep them in sync.

- "reduces inference latency by 60-65\%"
- "outperforms state-of-the-art methods by 14-28\% in throughput"
- "reducing inference latency by 48-58\%" (single-trajectory)

Rules: escape the percent (`60-65\%`), use a plain hyphen for ranges, always
name the baseline you improved over ("compared to standard autoregressive
decoding"). Never write "significantly" without a number next to it.

## 8. Tables

```latex
\begin{table*}[!t]
\centering
\small
\caption{\textbf{Bold lead-in sentence.} Then what the columns mean, how to read
it, and what the highlighting means. The best values are highlighted in \textbf{bold}.}
\begin{tabular}{lcc...}
\toprule
...
\midrule
\multicolumn{13}{c}{\textit{\cellcolor[HTML]{EFEFEF}DeepSeek-R1-Distill-Qwen-7B}} \\
\midrule
Plain & T & 26.63 & ... \\
\graymidrule
\multirow{2}{*}{Eagle-2} & T & ... \\
                         & A & ... \\
\graymidrule
\multirow{2}{*}{\textbf{\mname (Ours)}} & T & \textbf{82.62} & ... \\
\bottomrule
\end{tabular}
\end{table*}
```

- **Caption goes above** the tabular. Booktabs rules only — no vertical lines.
- `\toprule` / `\midrule` / `\bottomrule`; `\graymidrule` between method blocks.
- Model-group header rows: gray `\cellcolor[HTML]{EFEFEF}`, italic, spanning.
- Our method is the **last row**, bolded, labeled `\mname (Ours)`.
- Best value in each column in **bold**, and say so in the caption.
- One file per table in `tables/`, `\input` from the section.

## 9. Figures

```latex
\begin{figure*}[t]
\centering
\begin{subfigure}{0.329\textwidth}
\includegraphics[width=0.95\linewidth]{figures/q7b_aime.pdf}
\caption{AIME-2024}\label{fig:main-aime}
\end{subfigure}
... three across ...
\caption{\textbf{Bold lead-in sentence.} What is plotted, what the axes mean,
and the setup. All measurements are made on a single A100 GPU with
DeepSeek-R1-Distill-Qwen-7B.}
\label{fig:main}
\end{figure*}
```

- **Caption goes below** the figure.
- Full-width figures use `figure*` at `[t]`; three panels at `0.329\textwidth`,
  images at `width=0.95\linewidth`.
- Subfigure captions are bare benchmark names ("AIME-2024"), no sentence.
- Figures are **PDF assets** generated elsewhere; the `.tex` file in `figures/`
  is only the float wrapper. One file per float, `\input` from the section.

## 10. Captions

Every caption, table and figure, follows the same two-part shape:

> **Bold claim or subject.** Then 1–3 sentences of setup: what is reported, on
> what data, on what hardware, and how to read the highlighting.

The bold lead-in is a sentence fragment naming the thing, not a summary of the
result ("**Structure of the Optimized Tree.**", "**Speculative decoding
performance in multi-trajectory reasoning.**"). Captions are self-contained — a
reader who skips the body should still understand the table.

## 11. Prose conventions

- **First person plural, active voice**: "We introduce", "Our analysis reveals",
  "we evaluate". Never "it is shown that".
- **Present tense** for method and results ("STAND reduces", "the tree reaches").
- **Define once, then abbreviate**: "speculative decoding (SD)", "Large Reasoning
  Models (LRMs)", "out-of-domain (OOD)". Introduce the acronym at first use in
  the body and use it thereafter.
- **Capitalize "N-gram"** consistently. The reference is split 20/11 between
  "N-gram" and "n-gram" — pick "N-gram" and hold it.
- **Contributions as an inline numbered list**, not an `itemize` (it costs less
  space): "STAND introduces three key innovations: (1) a memory-efficient ...,
  (2) an optimized sampling strategy ..., and (3) a data-driven approach ...".
- **Motivating question** set centered and italic, as its own display block:

```latex
\begin{center}
\emph{How can we improve the efficiency \\ of test-time scaling and reasoning
approaches \\ without compromising their accuracy?}
\end{center}
```

## 12. Introduction structure

The reference follows a fixed 7-move arc. Reuse it:

1. **Paradigm** — what the field is doing, with citations.
2. **Cost** — why it's expensive.
3. **Existing fixes** — and the trade-off they all make.
4. **The question** — centered italic block.
5. **Our angle** — the technique you turn to, and why it fits.
6. **Key observation** — the empirical fact that makes it work.
7. **Method + numbered contributions + headline numbers.**

## 13. Pre-submission checklist

- [ ] Body ends on page 4; References start on page 5.
- [ ] `grep -c '\\cite{'` returns 0 (all `\citep`/`\citet`).
- [ ] No hand-typed `Figure~\ref` / `Table~\ref` — all `\Cref`.
- [ ] Method name is `\mname` everywhere in prose, no literal name.
- [ ] "N-gram" capitalization consistent.
- [ ] Headline numbers identical in abstract, intro, and experiments.
- [ ] No `\placeholder`, `\lipsum`, `\blindtext`, `todonotes`.
- [ ] Build has 0 undefined citations and 0 undefined references.
- [ ] Anonymous: no author names, affiliations, acknowledgements, or repo URLs
      (`pdftotext main.pdf - | grep -iE 'name|institution|github'`).
- [ ] Every table caption says how to read the bolding; every figure caption
      names the hardware and model.
