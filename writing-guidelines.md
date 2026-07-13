# Overleaf writing guidelines

How we write the paper. This is the *process* guide — what to write and in what
order. For *how it should look* (macros, captions, citations, table format), see
`~/writing-style-guide.md`, which is derived from the current template.

- Project: `~/writing` (Overleaf git bridge, branch `main`)
- Build: `~/build-writing.sh` → `~/writing-main.pdf`
- Reference PDF: `~/writing-template-reference.pdf`

---

## 1. Formatting constraints

- The project follows **ICML formatting**, with a **hard 4-page limit** excluding
  references and appendix. The body must end on page 4; References start at the
  top of page 5.
- **The paper must be submittable at every stage.** Not "finished" — submittable.
  At any moment, someone should be able to compile it and send it in.
- Consequently, **the word "placeholder" must never appear in the rendered PDF.**
  Provisional numbers are written as though they were final. If a result later
  contradicts the text, revise the text then.

### Marking placeholders

Placeholders are tracked **in the source but invisible in the PDF**. Use the `\ph`
macro, which renders its argument unchanged:

```latex
% in main.tex preamble
\newcommand{\ph}[1]{#1}   % provisional value; renders normally, greppable in source
```

```latex
\mname reduces inference latency by \ph{60-65}\% compared to standard
autoregressive decoding.
```

This renders as "reduces inference latency by 60-65%" — a reader sees a finished
sentence — while `grep -rn '\\ph{' section/ tables/` lists everything still
provisional. When a real number lands, delete the `\ph{}` wrapper and keep the
value.

Do **not** use the template's existing `\placeholder` macro (gray `\lipsum`
filler): it is visible in the PDF and therefore not submittable. Remove it,
along with `\lipsum`, `\blindtext`, and `duckuments`, before the first draft.

## 2. General principles

**One research question.** The paper answers a single, specific, well-defined
question. Every section serves it. If a paragraph doesn't, cut it.

**Writing runs in parallel with experiments, not after them.** As you design and
launch experiments, write the full paper with placeholder numbers for the results
you expect.

**Write the finished paper before the results exist.** Predict the results, write
the complete 4-page draft around them, then revise iteratively as real numbers
arrive. The draft is always a full, submittable, 4-page paper with a solid
storyline — never a skeleton with gaps.

**No concept figure for this paper.** Invest that effort in high-quality
scientific figures that present the key findings and quantitative results
directly. (This changes the role of the template's `figures/method.tex` slot —
the lead figure should be a results figure, like `main_figure.tex`.)

## 3. How to write the paper

Work in this order. Steps 1–3 happen in a planning file (`~/writing-plan.md`),
not in the `.tex`.

**1. Concretize the topic and state the main message.**
Write the paper's TL;DR as a *single sentence* in the planning file. Do not open
the `.tex` yet.

**2. Write the storyline** — also in the planning file, before any LaTeX. The
standard arc:

1. **Background and problem setup.** One sentence of background (e.g. the
   prevalence of LLMs), and one sentence naming the core limitation of the
   current frontier that this paper addresses.
2. **Motivation** *(optional)*. The experimental observations that motivate the
   approach — typically simple measurements of existing patterns in the models.
3. **Method.** One sentence describing the approach at a high level: the single
   most important idea, the "killer" idea.
4. **Experiment overview.** One sentence per experiment. For each: first state
   the **claim** you want to make, then design the experiment that validates it.
   Claims come first; experiments exist to support them.
5. **Conclusion.** One sentence wrapping up the paper.

**3. Concretize the experiments.** Sharpen each claim, and pin down the specific
experiment that validates it — models, datasets, metrics, baselines.

**4. Write the Introduction.** It should tell the storyline from step 2 end to
end. (Structure to follow: `~/writing-style-guide.md` §12.)

**5. Write the Experiments section**, with tables filled in using expected values
wrapped in `\ph{}`. Write the surrounding discussion as though the numbers were
final — state what the results show.

**6. Fill in the rest of the document.** Abstract, method, conclusion, appendix.
The body must properly fill 4 pages and read as a complete paper.

**7. Iterate.** As real results arrive, update the tables and the text that
discusses them. If the results contradict the storyline, **revise the storyline**
— that is a normal outcome, not a failure. The Overleaf project stays in a
submittable state at every stage of this loop.

## 4. Definition of "submittable"

Check before ending any work session:

- [ ] Compiles cleanly: `~/build-writing.sh`, with 0 undefined citations and
      0 undefined references.
- [ ] Body ends on page 4; References start on page 5.
- [ ] No visible placeholder text, gray filler, or "TODO" in the PDF.
- [ ] Every table and figure has a caption that reads as final.
- [ ] The storyline is intact end to end: a reader gets the claim, the evidence,
      and the conclusion.

Provisional numbers are fine. Visible gaps are not.
