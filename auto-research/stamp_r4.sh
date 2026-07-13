#!/usr/bin/env bash
P=/home/lobster/ralph/results/r4_headline_7b.json
until [ -s "$P" ]; do sleep 10; done
python3 - <<'PY'
import json
p='/home/lobster/ralph/results/r4_headline_7b.json'
d=json.load(open(p))
note=("NLL computed via chunked softmax over the sequence; verified numerically identical to "
      "the unchunked computation on 0.5B (dense NLL 2.7626 both ways). Chunking was required "
      "because Qwen's ~152k vocabulary makes a full fp32 [B,T,V] cast exceed 24GB at 7B.")
if note not in d.get('notes',''):
    d['notes'] = d.get('notes','').rstrip() + ' ' + note
d.setdefault('dense_nll', d['runs']['residual_damage_k4']['methods']['dense']['wikitext2_nll'])
d.setdefault('dtype', d['config']['dtype'])
json.dump(d, open(p,'w'), indent=2)
print('R4 stamped: chunked-softmax note + top-level mirrors')
PY
