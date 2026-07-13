#!/usr/bin/env bash
# Auto-return a remote result from ANY fleet host, reading ~/.gpufleet/config.json.
# pull_when_done.sh was alin14-only; the 2080Ti hosts would have stranded their JSONs
# exactly the way R3 did. usage: pull_from.sh <host> <remote_basename> [timeout_sec]
set -u
HOST="$1"; FILE="$2"; TIMEOUT="${3:-3600}"
IP=$(python3 -c "import json;print(json.load(open('$HOME/.gpufleet/config.json'))['hosts']['$HOST']['ip'])")
USER=$(python3 -c "import json;print(json.load(open('$HOME/.gpufleet/config.json'))['user'])")
KEY=$(python3 -c "import json;print(json.load(open('$HOME/.gpufleet/config.json'))['key'])")
SSH=(-i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)
SRC="~/depthar_results/${FILE}"; DST="/home/lobster/ralph/results/${FILE}"
deadline=$(( $(date +%s) + TIMEOUT ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if ssh "${SSH[@]}" "${USER}@${IP}" "test -s ${SRC}" 2>/dev/null; then
    a=$(ssh "${SSH[@]}" "${USER}@${IP}" "stat -c %s ${SRC}" 2>/dev/null); sleep 3
    b=$(ssh "${SSH[@]}" "${USER}@${IP}" "stat -c %s ${SRC}" 2>/dev/null)
    if [ "$a" = "$b" ]; then
      rsync -az -e "ssh ${SSH[*]}" "${USER}@${IP}:${SRC}" "$DST" && { echo "PULLED $FILE from $HOST"; exit 0; }
    fi
  fi
  sleep 10
done
echo "TIMEOUT: ${FILE} never appeared on $HOST" >&2; exit 1
