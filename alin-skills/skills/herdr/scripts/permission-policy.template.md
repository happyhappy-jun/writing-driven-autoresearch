# herdr agent permission policy — MODERATE (template)

When a watched herdr agent is `blocked` at a permission prompt, judge the requested
action against this policy. Anything not clearly in AUTO-APPROVE is **escalated to the
user** — never auto-denied (leave the prompt waiting and notify).

> Copy this file to `~/.config/herdr-mgr/permission-policy.md` and tune it. The lists
> below are a safe starting point; edit them to match how much autonomy you want.
> Set `<PROJECT_DIR>` to the directory your agents are allowed to write in (or list
> several). If you run multiple projects, list each in-scope path.

In-scope project dir(s): `<PROJECT_DIR>`

## AUTO-APPROVE (act, in live mode)
- Read-only / inspection: `cat`, `ls`, `grep`, `head`/`tail`, `find`, `git status`/`diff`/`log`/`show`,
  reading files, analysis/plotting scripts, status queries (`squeue`, `nvidia-smi`, etc.).
- (Re)starting monitors / watchers: `watch`, `tail -f`, polling loops.
- File edits / writes **within** an in-scope project dir.
- Launching jobs **within** an in-scope project (training/eval/serve) that operate under it.
- **Recoverable / soft** state changes: archiving or soft-deleting (e.g. archiving a page,
  moving to a trash that can be restored, `git stash`). Recoverable ⇒ auto-approve.

## ESCALATE (do NOT act; notify the user, leave the prompt waiting)
- **Hard / irreversible** deletes: `rm -rf`, dropping files/dirs, truncating, DB drops,
  permanently removing/purging something a soft-delete would otherwise have made recoverable.
- Git writes that publish or rewrite history: `git push`, `git reset --hard`, force-push,
  rebase onto shared branches, tags/releases.
- Killing or cancelling jobs: `scancel`, `kill`, `pkill` of running work.
- `sudo` / privilege escalation / system-wide package installs.
- Anything **outside** an in-scope project dir (writes to `$HOME` elsewhere, system paths).
- External sends: network posts, emails, chat/API calls that mutate remote state,
  pushing artifacts to remote stores.
- Anything ambiguous, novel, or not clearly covered above.

> **Recoverability split** (the rule of thumb for the two lists above): if the action is
> *recoverable* — archive, soft-delete, stash, anything you can undo — auto-approve it.
> If it is a *hard delete / permanent removal*, escalate.

## FALSE POSITIVES — approve these (host-tool artifacts, not the agent's intent)
These warnings come from the **host Claude Code permission classifier**, not from anything
risky the agent is doing. They recur constantly and are safe to approve when the underlying
command is otherwise in AUTO-APPROVE:
- **"Contains simple_expansion"** — a benign `$VAR` / `$(...)` in a read-only or in-scope command.
- **"expansion obfuscation"** — brace expansion `{a,b}` or a heredoc; not obfuscation, just shell.
- **"string … cannot be statically analyzed"** — an inline `python -c '…'` / `awk` / heredoc the
  classifier can't parse; judge it by what it actually does.
- **"cd with output redirection"** — e.g. `cd dir && cmd > out`; harmless when `dir`/`out` are in scope.

Judge the *effect* of the command, not the classifier's label. If the effect is in AUTO-APPROVE,
approve despite the scary-sounding flag.

## AUTO-DISMISS (send Escape; do NOT escalate)
Some prompts are not permission requests at all and should simply be dismissed:
- The periodic **"How is Claude doing this session?"** feedback prompt → `dismiss <agent>` (Escape).
- Other non-actionable UI nags that block the agent without asking for a real decision.
Dismiss these silently (optionally `note` it); never escalate.

## IDLE WATCH (per-agent; prod a wedged agent before alerting)
A non-crashed-but-stuck agent should be *prodded*, not just reported. Configure in `topology.json`:
```json
"idle_nudge": { "enabled": true, "after_sec": 900, "max_nudges": 2,
                "text": "is everything going well? if there's a bug, fix it" }
```
- After `after_sec` of continued idle, the watcher sends `text` to the agent (live mode only),
  up to `max_nudges` times. Tune the cadence/text per how chatty you want it.
- If nudging doesn't revive it (nudges exhausted), the watcher falls back to a `STALLED:` alert
  that **re-fires** every idle window until you intervene.
- Never nudge a `blocked` agent (it's sitting at a permission prompt — judge it instead).

## Modes (persisted in `~/.config/herdr-mgr/permission-mode`)
- **dryrun**: log the would-be decision; send NO input. (Start here.)
- **live**: AUTO-APPROVE → `herdr_sync.py approve <agent>` (sends a plain "Yes",
  NEVER "Yes, and don't ask again" — that would suppress future prompts and blind the
  watcher), then verify with `herdr_sync.py pending`.
  ESCALATE → leave it waiting and notify the user. Never auto-deny (`deny` is only for
  when the user explicitly says to reject one).

Decisions are appended to `~/.config/herdr-mgr/decisions.log` via `herdr_sync.py note "..."`.
