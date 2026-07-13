#!/bin/bash
# herdr-act.sh — STATIC, allowlistable action wrapper for ONE LOCAL herdr agent.
#
# WHY THIS EXISTS: in the monitor session you must NEVER hand-roll dynamic shell
# like `$(herdr pane list | python3 -c …)` to resolve a pane id, then inline
# `herdr pane send-keys`. The host Claude Code permission classifier flags those
# as "Contains simple_expansion" / "cannot be statically analyzed" and PROMPTS —
# so the watcher trips its own permission prompts and autonomy breaks. This file
# hides ALL dynamic resolution inside itself, so the operator types only one
# statically-analyzable command. Allowlist it once:
#
#     Bash(/abs/path/to/herdr-act.sh:*)
#
# (Prefer the stable copy that `herdr_sync.py install` drops at
#  ~/.config/herdr-mgr/herdr-act.sh — its path survives plugin updates.)
#
# For most actions, prefer `herdr_sync.py approve|deny|dismiss|nudge|send|read
# <agent>` (also static, and remote-aware). This wrapper is the shell-native
# equivalent for a single LOCAL agent, handy for quick read/dismiss/key ops.
#
# Usage:
#   herdr-act.sh <target_label> <subcommand> [args]
#   herdr-act.sh <subcommand> [args]            # target from $HERDR_TARGET_LABEL
#
#   subcommands:
#     status            print the agent_status of the target pane
#     pid               print the resolved pane id
#     read [N]          print the last N visible lines (default 40)
#     approve           select the plain "Yes" (option 1; NEVER "don't ask again")
#     deny              select the "No" option
#     dismiss           send Escape (e.g. to clear a feedback prompt)
#     key <N>           send option number N then Enter
#     nudge [text]      type the idle-nudge prompt into the agent
#     send <text...>    type literal text into the agent
#
#   env:
#     HERDR_TARGET_LABEL   default target pane label if not given positionally
#     HERDR_SESSION        herdr session (default: the default session)
#     HERDR_NUDGE_TEXT     default text for `nudge`
set -u

DEFAULT_NUDGE="is everything going well? if there's a bug, fix it"

# ---- resolve target label + subcommand (target may be omitted -> env) ----
SUBS="status pid read approve deny dismiss key nudge send"
if [[ $# -ge 1 ]] && [[ " $SUBS " == *" $1 "* ]]; then
  TARGET="${HERDR_TARGET_LABEL:-}"
else
  TARGET="${1:-${HERDR_TARGET_LABEL:-}}"; shift || true
fi
CMD="${1:-status}"; shift || true

if [[ -z "${TARGET}" ]]; then
  echo "herdr-act.sh: no target label (pass one positionally or set HERDR_TARGET_LABEL)" >&2
  exit 2
fi

SESS="${HERDR_SESSION:-}"
herdr_cmd() {
  if [[ -n "$SESS" && "$SESS" != "default" ]]; then
    herdr --session "$SESS" "$@"
  else
    herdr "$@"
  fi
}

# ---- resolve pane id by label (the dynamic bit, kept INSIDE this file) ----
PANE_ID="$(herdr_cmd pane list 2>/dev/null | python3 - "$TARGET" <<'PY'
import json, sys
target = sys.argv[1]
pid = ""
for line in sys.stdin:
    line = line.strip()
    if not line.startswith("{"):
        continue
    try:
        panes = json.loads(line)["result"]["panes"]
    except Exception:
        continue
    for p in panes:
        if p.get("label") == target:
            pid = p.get("pane_id", "")
            break
    if pid:
        break
print(pid)
PY
)"

if [[ -z "$PANE_ID" ]]; then
  echo "herdr-act.sh: no pane labelled '$TARGET' (session: ${SESS:-default})" >&2
  exit 3
fi

# ---- pick an option number from the visible prompt (approve/deny) ----
pick_option() {
  # $1 = approve|deny
  herdr_cmd pane read "$PANE_ID" --source visible --lines 100 2>/dev/null \
    | python3 - "$1" <<'PY'
import re, sys
want = sys.argv[1]
num = ""
for line in sys.stdin:
    m = re.search(r"(\d+)\.\s+(.*\S)", line)
    if not m:
        continue
    n, label = m.group(1), m.group(2).strip().lower()
    if want == "approve" and label.startswith("yes") and "don't ask" not in label and "all" not in label:
        num = n; break
    if want == "deny" and label.startswith("no"):
        num = n; break
print(num)
PY
}

status() {
  herdr_cmd pane list 2>/dev/null | python3 - "$TARGET" <<'PY'
import json, sys
target = sys.argv[1]
st = "MISSING"
for line in sys.stdin:
    line = line.strip()
    if not line.startswith("{"):
        continue
    try:
        panes = json.loads(line)["result"]["panes"]
    except Exception:
        continue
    for p in panes:
        if p.get("label") == target:
            st = p.get("agent_status", "no-agent") if p.get("agent") else "no-agent"
            break
print(st)
PY
}

case "$CMD" in
  status)  status ;;
  pid)     echo "$PANE_ID" ;;
  read)    herdr_cmd pane read "$PANE_ID" --source visible --lines "${1:-40}" ;;
  approve)
    OPT="$(pick_option approve)"
    if [[ -z "$OPT" ]]; then echo "no 'Yes' option found; read the pane and act manually" >&2; exit 4; fi
    herdr_cmd pane send-keys "$PANE_ID" "$OPT" enter
    echo "approve: sent option $OPT to '$TARGET' ($PANE_ID). Verify with: herdr-act.sh $TARGET status" ;;
  deny)
    OPT="$(pick_option deny)"
    if [[ -z "$OPT" ]]; then echo "no 'No' option found; read the pane and act manually" >&2; exit 4; fi
    herdr_cmd pane send-keys "$PANE_ID" "$OPT" enter
    echo "deny: sent option $OPT to '$TARGET' ($PANE_ID)." ;;
  dismiss)
    herdr_cmd pane send-keys "$PANE_ID" esc
    echo "dismiss: sent esc to '$TARGET' ($PANE_ID)." ;;
  key)
    if [[ $# -lt 1 ]]; then echo "usage: herdr-act.sh $TARGET key <N>" >&2; exit 2; fi
    herdr_cmd pane send-keys "$PANE_ID" "$1" enter
    echo "key: sent option $1 to '$TARGET' ($PANE_ID)." ;;
  nudge)
    # `agent send` only types text; follow with `enter` to actually submit.
    TEXT="${1:-${HERDR_NUDGE_TEXT:-$DEFAULT_NUDGE}}"
    herdr_cmd agent send "$PANE_ID" "$TEXT"; sleep 0.3; herdr_cmd pane send-keys "$PANE_ID" enter
    echo "nudge: sent to '$TARGET' ($PANE_ID): $TEXT" ;;
  send)
    if [[ $# -lt 1 ]]; then echo "usage: herdr-act.sh $TARGET send <text...>" >&2; exit 2; fi
    herdr_cmd agent send "$PANE_ID" "$*"; sleep 0.3; herdr_cmd pane send-keys "$PANE_ID" enter
    echo "send: delivered to '$TARGET' ($PANE_ID): $*" ;;
  *)
    echo "herdr-act.sh: unknown subcommand '$CMD'" >&2
    echo "  subcommands: status | pid | read [N] | approve | deny | dismiss | key <N> | nudge [text] | send <text>" >&2
    exit 2 ;;
esac
