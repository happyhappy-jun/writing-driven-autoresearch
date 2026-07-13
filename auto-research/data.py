"""WikiText batches. Calibration and held-out slices are disjoint by construction."""

from __future__ import annotations

import glob
import os

import torch
from huggingface_hub import snapshot_download

SEED = 42


def _text(config="wikitext-103-raw-v1", split="train", max_chars=1_000_000) -> str:
    """Read just enough raw text. Tokenizing the full 500MB corpus would cost minutes."""
    root = snapshot_download(repo_id="Salesforce/wikitext", repo_type="dataset",
                             allow_patterns=[f"{config}/*"])
    files = sorted(glob.glob(os.path.join(root, config, f"{split}-*.parquet")))
    if not files:
        files = sorted(glob.glob(os.path.join(root, config, f"*{split}*.parquet")))
    if not files:
        raise FileNotFoundError(f"no parquet for {config}/{split} under {root}")
    import pyarrow.parquet as pq
    parts, total = [], 0
    for f in files:
        for batch in pq.ParquetFile(f).iter_batches(batch_size=4096, columns=["text"]):
            for t in batch.column("text").to_pylist():
                parts.append(t)
                total += len(t)
            if total >= max_chars:
                return "".join(parts)
    return "".join(parts)


def blocks(tok, n_calib=16, n_eval=16, seq_len=512, device="cuda",
           config="wikitext-103-raw-v1", split="train", batch_size=4):
    """Contiguous non-overlapping token blocks. Returns (calib_batches, eval_batches).

    The eval blocks sit strictly after the calibration blocks in the token stream, so
    they are disjoint (`disjoint_from_calib: true` in the result schema).
    """
    need = (n_calib + n_eval) * seq_len
    # ~4-5 chars/token on WikiText; 12x is a safe margin and keeps tokenization ~1s.
    ids = tok(_text(config, split, max_chars=max(200_000, need * 12)),
              return_tensors="pt").input_ids[0]
    if ids.numel() < need:
        raise ValueError(f"corpus too short: {ids.numel()} < {need}")
    chunks = ids[:need].view(n_calib + n_eval, seq_len)

    def pack(x, bs=batch_size):
        out = []
        for i in range(0, x.shape[0], bs):
            b = x[i:i + bs].to(device)
            out.append((b, torch.ones_like(b)))
        return out

    return pack(chunks[:n_calib]), pack(chunks[n_calib:])
