#!/bin/bash
# Durable local pane = clean VIEW of one remote-herdr agent (no tmux, purely a
# viewport). Status is handled separately by `herdr_sync.py mirror`, so this
# carries no -R socket and sends NO keystrokes. Auto-reattaches on disconnect.
# Ctrl-C to stop.
#
# Usage: attach-herdr-agent.sh <remote_pane_id> <ssh_host> [session]
#   <remote_pane_id>  the herdr pane/agent id on the remote (e.g. wXXXX-1)
#   <ssh_host>        ssh target of the remote herdr server
#   [session]         remote herdr session name (default: main)
set -u
TARGET="${1:?usage: attach-herdr-agent.sh <remote_pane_id> <ssh_host> [session]}"
HOST="${2:?usage: attach-herdr-agent.sh <remote_pane_id> <ssh_host> [session]}"
SESS="${3:-main}"
while true; do
  # --takeover reclaims the remote terminal if a stale client still holds it
  # (otherwise the loop spins and the pane looks dead-but-process-alive).
  ssh -t "$HOST" "herdr --session $SESS agent attach '$TARGET' --takeover"
  echo "[$(date '+%H:%M:%S')] detached/dropped ($TARGET on $HOST); reattaching in 3s — Ctrl-C to stop"
  sleep 3
done
