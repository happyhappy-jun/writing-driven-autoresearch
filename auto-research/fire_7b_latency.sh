#!/usr/bin/env bash
# Fire the 7B latency run the moment R4's residual-damage k=4 layer set exists.
# The set is not knowable until R4's scan+selection is written to its JSON, so this waits
# on the artifact rather than on a human. The 1.5B latency JSON is already the floor; this
# only upgrades it.
set -u
R4=/home/lobster/ralph/results/r4_headline_7b.json
cd /home/lobster/auto-research

until [ -s "$R4" ]; do sleep 15; done
sleep 5   # let the stamper finish rewriting it

LAYERS=$(python3 -c "
import json
d=json.load(open('$R4'))
print(' '.join(str(x) for x in d['runs']['residual_damage_k4']['skipped_layers']))
") || { echo "could not read 7B layer set"; exit 1; }
echo "7B residual_damage k=4 layer set: $LAYERS"

python3 ~/.claude/skills/lobroster/scripts/gpufleet.py submit \
  --host alin14 --name lat-7b --gpus 1 --min-vram 22 \
  --activate 'source ~/.gpufleet/venvs/lobroster/bin/activate' \
  --cmd "cd ~/auto-research && python latency.py --model Qwen/Qwen2.5-7B --dtype bfloat16 --layers ${LAYERS} --batch-size 8 --seq-lens 512 2048 --out ~/depthar_results/latency_Qwen2.5-7B.json"

bash pull_when_done.sh latency_Qwen2.5-7B.json 2400
