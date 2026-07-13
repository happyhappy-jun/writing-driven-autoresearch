# Qwen3 addendum: staged procedure. NOT STARTED. Tree untouched.

**`d034a8b` is the submission of record either way.** Nothing below happens without master's
signal, and if the cells do not land, nothing happens at all: the future-work sentence
already in the paper is correct as written and needs no edit.

## Preconditions (all must hold before I touch the tree)

1. Master's explicit GO.
2. `qwen3_*.json` (or whatever they are actually named) **on disk** — I read the filenames
   from `ls`, not from any message.
3. The cells carry a `config` block I can diff against the prose: model, dtype, GPU,
   n_calib_seqs, seq_len, eval corpus/split. **Protocol truth comes from the config block.**
   If Qwen3 ran a different precision or corpus than Qwen2.5, the sentence must say so.

## The edit, at exact landed scope

Current sentence (already in the paper, correct as-is):
> "Translating light-budget likelihood recovery into accuracy, and extending the scale trend
> to the Qwen3 family, are the natural next steps."

If NLL-only cells land, the scale-trend sentence gains a second family **on the likelihood
axis only**:

> At a matched budget of four skipped blocks the recovery grows with scale, and the trend is
> not specific to one model family: on Qwen3 (0.6B to 8B) \mname recovers X\% to Y\% of the
> plain-skip language-modelling damage. We measure likelihood only for that family and make
> no downstream-accuracy claim for it.

**Ceiling rules that apply, hard-won and non-negotiable:**
- "Grows with scale" is a **k=4** claim. It was FALSE at k=2 on Qwen2.5 (8.4 -> 8.2 -> 7.3).
  If Qwen3's k=2 behaves the same, say so or scope the sentence to k=4 again.
- NLL-only cells support **no accuracy claim whatsoever** for Qwen3. Not "presumably", not
  "we expect". Nothing.
- Family sweep is **0.6B-8B** (14B only if it lands). **Never imply 32B ran** — it was skipped
  with a logged reason.
- Any Qwen3 task numbers, if they ever appear, enter the noise/jitter machinery and regrow the
  Bonferroni family AGAIN. That family has already regrown four times (16 -> 37 -> 41 -> 63),
  and each time it silently falsified prose that was correct when written. **Sweep on catch.**

## Mechanical sequence (~8 min)

```bash
ls ~/ralph/results/ | grep -i qwen3          # read the real filenames
python3 -c "..."                             # read config + cells MYSELF, never from a message
# 1. appendix rows via gen-table (add a Qwen3 block; NEVER hand-type a cell)
~/gen-table.py --check                       # must regenerate byte-identical
# 2. add the values to verify-phm.py with exact JSON keys
~/verify-phm.py                              # must be N/N, 0 unbacked, 0 mismatched
# 3. build + full audit
~/build-writing.sh && ~/writing-audit.sh --final    # must be 0 \ph AND 0 \phm
# 4. RENDER-CHECK BY HAND: conclusion's last words on p4, 0 hits p5
# 5. commit: "post-deadline addendum: Qwen3 cells"  (clearly separate from the submission)
```

## The unwrap problem this creates, and how it is handled

The paper is **already unwrapped** — there are no `\phm{}` markers left. New numbers therefore
cannot be tracked by the macro. Two options, and I take (b):

- (a) Re-wrap the new values in `\phm{}`, verify, then unwrap again. Two extra commits, and it
  reintroduces a macro into a frozen artifact.
- **(b) Add the values bare, but wire them into `verify-phm.py` anyway** and run it against the
  *pre-unwrap* value list plus the new keys. The verifier's job is to prove each printed number
  matches a JSON key; it does not need the macro to do that, only a spec entry. I will extend
  the spec and verify the new numbers by grepping the raw `.tex` for them.

Either way: **no number enters the paper that I have not read from a file.** That rule does not
relax because the deadline has passed.

## If NO-GO

Nothing. The future-work sentence stands, and it is true. A paper that says "extending to
Qwen3 is the natural next step" is honest; a paper that quietly implies it already did would
not be.
