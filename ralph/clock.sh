#!/usr/bin/env bash
# Depth-AR hackathon clock. Reads T0 (epoch seconds) from ~/ralph/T0.
# Prints elapsed / remaining against the 3h deadline, plus the active phase.
# Usage: ~/ralph/clock.sh          (human-readable)
#        ~/ralph/clock.sh --cron   (append one line to ~/ralph/CLOCK.md)
set -euo pipefail

RALPH="$HOME/ralph"
T0_FILE="$RALPH/T0"
DEADLINE_SEC=$((3 * 60 * 60))

if [[ ! -f "$T0_FILE" ]]; then
  echo "CLOCK: T0 not set. Run: date +%s > $T0_FILE" >&2
  exit 1
fi

T0=$(cat "$T0_FILE")
NOW=$(date +%s)
ELAPSED=$((NOW - T0))
REMAIN=$((DEADLINE_SEC - ELAPSED))

fmt() { # seconds -> H:MM
  local s=$1 sign=""
  if (( s < 0 )); then sign="-"; s=$(( -s )); fi
  printf "%s%d:%02d" "$sign" $(( s / 3600 )) $(( (s % 3600) / 60 ))
}

E=$(fmt "$ELAPSED")
R=$(fmt "$REMAIN")
M=$(( ELAPSED / 60 ))

# Phase boundaries follow DEPTH-AR-PLAN.md §11.
if   (( M <  12 )); then PHASE="R0 correctness + paper skeleton"
elif (( M <  30 )); then PHASE="R1 layer scan + intro/method"
elif (( M <  42 )); then PHASE="GATE A (predictability)"
elif (( M <  60 )); then PHASE="R1 variants (if Gate A failed)"
elif (( M <  78 )); then PHASE="R2 composition k=1,2,4"
elif (( M <  90 )); then PHASE="GATE B (composition)"
elif (( M < 115 )); then PHASE="R3 1.5B verification"
elif (( M < 125 )); then PHASE="GATE C (transfer / scale decision)"
elif (( M < 155 )); then PHASE="R4 headline scale (7B on 3090; 3B fallback) + paper layout"
elif (( M < 167 )); then PHASE="one repair or latency run"
elif (( M < 180 )); then PHASE="FREEZE: reproduce, audit, compile"
else                    PHASE="OVERTIME - submit what compiles"
fi

# Hard deadlines from the plan.
NEXT=""
(( M < 125 )) && NEXT="method freeze at 2:05 (T+125m)"
(( M >= 125 )) && NEXT="no new direction after 2:35 (T+155m)"
(( M >= 155 )) && NEXT="submission at 3:00 (T+180m)"

LINE="T+${E} | ${R} left | ${PHASE} | ${NEXT}"

if [[ "${1:-}" == "--cron" ]]; then
  echo "$(date '+%H:%M') ${LINE}" >> "$RALPH/CLOCK.md"
else
  echo "$LINE"
fi
