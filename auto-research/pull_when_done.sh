#!/usr/bin/env bash
# Auto-return a remote result the moment it appears. A JSON that only exists on alin14
# does not exist -- and a manual post-hoc rsync is a single point of failure (it did not
# run for R3 until prompted). This poller removes the human from the loop.
#
# usage: pull_when_done.sh <remote_basename> [timeout_sec]
set -u
REMOTE_FILE="$1"
TIMEOUT="${2:-3600}"
SSH_OPTS=(-i "${WORKER_SSH_KEY:?set WORKER_SSH_KEY}" -o BatchMode=yes -o IdentitiesOnly=yes
          -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)
HOST="${WORKER_HOST:?set WORKER_HOST, e.g. user@worker-ip}"
SRC="~/depthar_results/${REMOTE_FILE}"
DST="/home/lobster/ralph/results/${REMOTE_FILE}"

deadline=$(( $(date +%s) + TIMEOUT ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if ssh "${SSH_OPTS[@]}" "$HOST" "test -s ${SRC}" 2>/dev/null; then
    # Wait for the size to settle, so we never pull a half-written file.
    a=$(ssh "${SSH_OPTS[@]}" "$HOST" "stat -c %s ${SRC}" 2>/dev/null)
    sleep 3
    b=$(ssh "${SSH_OPTS[@]}" "$HOST" "stat -c %s ${SRC}" 2>/dev/null)
    if [ "$a" = "$b" ]; then
      rsync -az -e "ssh ${SSH_OPTS[*]}" "${HOST}:${SRC}" "$DST" && \
        python3 -c "import json,sys;d=json.load(open('$DST'));print('PULLED $REMOTE_FILE status=%s'%d.get('status'))" && exit 0
    fi
  fi
  sleep 10
done
echo "TIMEOUT: ${REMOTE_FILE} never appeared on alin14" >&2
exit 1
