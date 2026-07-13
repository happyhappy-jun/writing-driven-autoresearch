"""Downstream multiple-choice task evaluator for Depth-AR (plan section 11).

Protocol (the `acc_norm`-style protocol; state this verbatim in the paper)
--------------------------------------------------------------------------
For every example we build one (context, continuation) pair per candidate answer.
Each candidate is scored by the **mean per-token log-probability of the continuation
tokens given the context**, i.e.

    score(c) = ( sum_{t in continuation} log P(x_t | x_<t) ) / (number of continuation tokens)

-- the sum of the token log-probs of the continuation, divided by the number of
CONTINUATION TOKENS (token-length normalization, not character-length). The prediction
is argmax_c score(c); accuracy is the fraction of examples whose argmax equals the gold
label. Context tokens and padding tokens are never scored. Ties broken by lowest
candidate index (argmax over a fixed candidate order).

This is length-normalized-by-token accuracy. It matches lm-evaluation-harness's
`acc_norm` in spirit but normalizes by TOKEN count rather than by byte/character count
(lm-eval's `acc_norm` divides by the number of characters of the continuation string);
the two agree on ranking whenever candidates have similar tokens-per-character, and the
token-normalized variant is the one specified for this project.

Prompt formats follow lm-evaluation-harness:
  HellaSwag  ctx   = preprocess(activity_label + ": " + ctx_a + " " + ctx_b.capitalize())
             cand  = " " + preprocess(ending)
  PIQA       ctx   = "Question: {goal}\nAnswer:"      cand = " " + solution
  ARC-Easy   ctx   = "Question: {question}\nAnswer:"  cand = " " + choice_text

Data
----
  hellaswag  Rowan/hellaswag                        validation  (10042 rows)
  piqa       baber/piqa                             validation  (1838 rows)
  arc_easy   allenai/ai2_arc  config ARC-Easy       validation  (570 rows)

NOTE ON THE PIQA REPO ID: the canonical `ybisk/piqa` repo ships ONLY a loading script
(`piqa.py`); `datasets` >= 3.0 removed script execution, so `trust_remote_code` no longer
exists as an escape hatch. We therefore read the parquet mirror `baber/piqa`
(goal/sol1/sol2/label, 1838 validation rows -- the official PIQA validation size and the
identical schema the ybisk script produces).

Example selection
-----------------
Examples are drawn from the validation split with `numpy.random.default_rng(seed)`
permutation, taking the first `n_examples` and returning them in sorted index order.
The chosen indices are returned under key "indices" so any two runs can be audited as
having scored exactly the same examples. Selection depends only on (task, seed,
n_examples) -- never on the model or the SkipPlan -- so every method sees identical data.
"""

from __future__ import annotations

import argparse
import json
import re
import time

import numpy as np
import torch
from huggingface_hub import hf_hub_download

TASKS = ("hellaswag", "piqa", "arc_easy")

_REPOS = {
    "hellaswag": ("Rowan/hellaswag", "data/validation-00000-of-00001.parquet"),
    # ybisk/piqa is script-only and unloadable under datasets>=3; parquet mirror instead.
    "piqa": ("baber/piqa", "piqa_validation.parquet"),
    "arc_easy": ("allenai/ai2_arc", "ARC-Easy/validation-00000-of-00001.parquet"),
}

_CACHE: dict = {}


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------

def _hs_preprocess(text: str) -> str:
    """lm-evaluation-harness HellaSwag text normalization."""
    text = text.strip()
    text = text.replace(" [title]", ". ")
    text = re.sub(r"\[.*?\]", "", text)
    text = text.replace("  ", " ")
    return text


def load_task(task: str) -> list:
    """-> [{"context": str, "choices": [str, ...], "gold": int}, ...] in split order."""
    if task in _CACHE:
        return _CACHE[task]
    if task not in _REPOS:
        raise KeyError(f"unknown task {task!r}; known: {TASKS}")

    import pyarrow.parquet as pq
    repo, fname = _REPOS[task]
    rows = pq.read_table(hf_hub_download(repo, fname, repo_type="dataset")).to_pylist()

    out = []
    for r in rows:
        if task == "hellaswag":
            ctx = r["ctx_a"] + " " + r["ctx_b"].capitalize()
            ex = {
                "context": _hs_preprocess(r["activity_label"] + ": " + ctx),
                "choices": [" " + _hs_preprocess(e) for e in r["endings"]],
                "gold": int(r["label"]),
            }
        elif task == "piqa":
            ex = {
                "context": f"Question: {r['goal']}\nAnswer:",
                "choices": [" " + r["sol1"], " " + r["sol2"]],
                "gold": int(r["label"]),
            }
        else:  # arc_easy
            labels = list(r["choices"]["label"])
            texts = list(r["choices"]["text"])
            key = r["answerKey"]
            if key not in labels:  # a handful of ARC rows key answers as "1".."5"
                continue
            ex = {
                "context": f"Question: {r['question']}\nAnswer:",
                "choices": [" " + t for t in texts],
                "gold": labels.index(key),
            }
        assert 0 <= ex["gold"] < len(ex["choices"])
        out.append(ex)

    _CACHE[task] = out
    return out


def select_indices(task: str, n_examples: int, seed: int) -> list:
    """Deterministic, model-independent example ids. Same (task, n, seed) -> same list."""
    n_total = len(load_task(task))
    n = min(n_examples, n_total)
    perm = np.random.default_rng(seed).permutation(n_total)
    return sorted(int(i) for i in perm[:n])


# --------------------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------------------

def _encode_pair(tok, context: str, continuation: str):
    """lm-eval's boundary-safe split: encode the concatenation, then cut at len(enc(ctx)).

    Encoding context and continuation independently would mis-handle merges across the
    boundary; cutting the joint encoding cannot, because the model only ever sees the
    joint token sequence.
    """
    n_spaces = len(context) - len(context.rstrip())
    if n_spaces > 0:
        continuation = context[-n_spaces:] + continuation
        context = context[:-n_spaces]
    whole = tok(context + continuation, add_special_tokens=False).input_ids
    ctx_enc = tok(context, add_special_tokens=False).input_ids
    n_ctx = len(ctx_enc)
    cont_enc = whole[n_ctx:]
    assert n_ctx >= 1, "empty context: nothing would condition the continuation"
    assert len(cont_enc) >= 1, f"empty continuation for {continuation!r}"
    return whole[:n_ctx], cont_enc


@torch.no_grad()
def _score_requests(dm, tok, reqs, device="cuda", max_batch_tokens=16384, max_batch_rows=32):
    """reqs: [(ctx_ids, cont_ids)] -> [mean per-continuation-token logprob], same order.

    Right padding only. With a causal mask, right-padded positions sit strictly after every
    real query position, so they cannot enter any real token's ATTENTION.

    That guarantees semantic independence -- but NOT numerical independence, and an earlier
    version of this docstring wrongly claimed a row's score "is independent of what it is
    batched with". MEASURED: it is not. Re-running one identical config (Qwen2.5-1.5B, bf16,
    layers [14,16], seed 42, 300 examples/task) with `max_batch_rows` 32 vs 8 leaves NLL
    bit-identical but moves task accuracy by +/-4 questions out of 900 on every method.
    Batch shape changes the matmul reduction order, which perturbs logits at the bf16 ulp
    level, which flips near-tie multiple-choice questions.

    Consequence: task accuracy carries ~0.5 accuracy points of harness jitter, comparable to
    the effect sizes we report. Fix the batch shape when comparing methods, and treat any
    accuracy difference below ~10 questions/900 as unresolvable. See noise_audit.json.
    """
    pad_id = tok.pad_token_id
    if pad_id is None:
        pad_id = tok.eos_token_id if tok.eos_token_id is not None else 0

    order = sorted(range(len(reqs)), key=lambda i: (len(reqs[i][0]) + len(reqs[i][1]), i))
    scores = [0.0] * len(reqs)

    batch, batch_ids = [], []
    n_ctx_seen = n_cont_seen = 0

    def flush(batch, batch_ids):
        nonlocal n_ctx_seen, n_cont_seen
        if not batch:
            return
        T = max(len(c) + len(k) for c, k in batch)
        B = len(batch)
        ids = torch.full((B, T), pad_id, dtype=torch.long)
        att = torch.zeros((B, T), dtype=torch.long)
        cont = torch.zeros((B, T), dtype=torch.bool)   # True on continuation positions
        n_cont = torch.zeros(B, dtype=torch.long)
        for b, (c, k) in enumerate(batch):
            L, nc, nk = len(c) + len(k), len(c), len(k)
            ids[b, :L] = torch.tensor(c + k, dtype=torch.long)
            att[b, :L] = 1
            cont[b, nc:nc + nk] = True
            n_cont[b] = nk

        flat_cont = torch.tensor([t for _, k in batch for t in k], dtype=torch.long)

        ids, att, cont = ids.to(device), att.to(device), cont.to(device)
        logits = dm.forward(ids, att)                       # [B,T,V]

        # logits[:, t] predicts ids[:, t+1]; a continuation token at absolute position j
        # is predicted by position j-1 (j >= n_ctx >= 1, so j-1 is always a real token).
        lp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
        tgt = ids[:, 1:]
        valid = cont[:, 1:]                                 # target-side continuation mask

        # -- the load-bearing assertions ------------------------------------------------
        # (1) Exactly the continuation tokens are scored: no more, no fewer.
        assert torch.equal(valid.sum(1), n_cont.to(device)), "scored token count != n_cont"
        # (2) Never a padding token.
        assert not bool((valid & (att[:, 1:] == 0)).any()), "a padding token was scored"
        # (3) Never a context token, and the shift is not off by one: the target ids the
        #     scorer actually reads out must BE the continuation token ids, in order.
        #     An off-by-one shift, or scoring the last context token, breaks this.
        assert torch.equal(tgt[valid].cpu(), flat_cont), "scored targets != continuation ids"

        tok_lp = lp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)   # [B,T-1]
        summed = (tok_lp * valid).sum(1)                         # continuation tokens only
        mean_lp = (summed / n_cont.to(device).float()).double().cpu().tolist()
        for b, ridx in enumerate(batch_ids):
            scores[ridx] = mean_lp[b]
        n_ctx_seen += int(sum(len(c) for c, _ in batch))
        n_cont_seen += int(n_cont.sum().item())

    for i in order:
        c, k = reqs[i]
        L = len(c) + len(k)
        cand_T = max(L, max((len(a) + len(b) for a, b in batch), default=0))
        if batch and ((len(batch) + 1) * cand_T > max_batch_tokens
                      or len(batch) + 1 > max_batch_rows):
            flush(batch, batch_ids)
            batch, batch_ids = [], []
        batch.append((c, k))
        batch_ids.append(i)
    flush(batch, batch_ids)

    assert n_cont_seen > 0
    return scores


@torch.no_grad()
def eval_tasks(dm, tok, n_examples=100, seed=42, tasks=TASKS, device="cuda",
               max_batch_tokens=16384, max_batch_rows=32) -> dict:
    """Length-normalized (per continuation token) multiple-choice accuracy.

    Each candidate answer is scored by  sum(log P(continuation tokens | context)) divided
    by the number of continuation tokens; the argmax over candidates is compared with the
    gold label. Only continuation tokens contribute -- never the context, never padding
    (asserted inside `_score_requests`).

    Returns {task: acc, ..., "avg_acc": float, "n_examples": {task: int},
             "indices": {task: [int, ...]}, "seed": int, "protocol": str}
    """
    res, n_used, idx_used = {}, {}, {}

    for task in tasks:
        data = load_task(task)
        idx = select_indices(task, n_examples, seed)

        reqs, spans = [], []
        for i in idx:
            ex = data[i]
            start = len(reqs)
            for ch in ex["choices"]:
                reqs.append(_encode_pair(tok, ex["context"], ch))
            spans.append((start, len(reqs), ex["gold"]))

        scores = _score_requests(dm, tok, reqs, device=device,
                                 max_batch_tokens=max_batch_tokens,
                                 max_batch_rows=max_batch_rows)

        correct = 0
        for lo, hi, gold in spans:
            pred = max(range(lo, hi), key=lambda j: scores[j]) - lo
            correct += int(pred == gold)

        res[task] = correct / len(idx)
        n_used[task] = len(idx)
        idx_used[task] = idx

    res["avg_acc"] = sum(res[t] for t in tasks) / len(tasks)
    res["n_examples"] = n_used
    res["indices"] = idx_used
    res["seed"] = seed
    res["protocol"] = ("argmax over candidates of sum(log P(continuation | context)) / "
                       "n_continuation_tokens; continuation tokens only, padding excluded")
    return res


# --------------------------------------------------------------------------------------
# CLI: validation harness (dense / plain-skip control / determinism)
# --------------------------------------------------------------------------------------

def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from depth_ar import DepthARModel, SkipPlan

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.float32).cuda().eval()
    dm = DepthARModel(model)
    print(f"model {a.model}  n_layers {dm.n_layers}  dtype {next(model.parameters()).dtype}",
          flush=True)

    runs = {}

    def run(name, plan):
        dm.plan = plan
        t0 = time.time()
        r = eval_tasks(dm, tok, n_examples=a.n, seed=a.seed)
        dt = time.time() - t0
        print(f"{name:16s} " + "  ".join(f"{t} {r[t]:.4f}" for t in TASKS)
              + f"  avg {r['avg_acc']:.4f}   ({dt:.0f}s)", flush=True)
        runs[name] = r
        return r

    d1 = run("dense", SkipPlan())
    d2 = run("dense_repeat", SkipPlan())
    ctrl = run("plain_skip_1-22", SkipPlan("plain_skip", tuple(range(1, 23))))

    same = all(d1[t] == d2[t] for t in TASKS) and d1["avg_acc"] == d2["avg_acc"]
    idx_same = all(d1["indices"][t] == d2["indices"][t] == ctrl["indices"][t] for t in TASKS)
    print(f"\ndeterministic (bit-identical dense re-run): {same}")
    print(f"identical example ids across all plans:      {idx_same}")
    print("chance:  hellaswag 0.25  piqa 0.50  arc_easy 0.25")

    if a.out:
        from depth_ar import write_result
        write_result(a.out, {"model": a.model, "n_examples": a.n, "seed": a.seed,
                             "runs": runs, "deterministic": same,
                             "same_example_ids": idx_same})
        print("wrote", a.out)


if __name__ == "__main__":
    main()
