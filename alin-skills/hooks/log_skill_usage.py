#!/usr/bin/env python3
"""ALIN plugin skill-usage telemetry hook.

Fires on two disjoint events (see hooks/hooks.json):

  * UserPromptExpansion  -> a lab member TYPED a slash command (e.g. /alin:hwpx)
  * PreToolUse:Skill      -> the model AUTO-INVOKED a skill via the Skill tool

For each invocation of an `alin:` skill it:
  1. appends a durable JSONL line locally (never lost, even offline), and
  2. best-effort POSTs the event to a central collector (backgrounded; never
     blocks or slows the user; failures are silent).

The hook is intentionally defensive: ANY error still exits 0 so it can never
break a lab member's session. It is a no-op unless it recognizes an alin skill.

Configuration (all optional, via env vars):
  ALIN_SKILL_TELEMETRY      "0"/"off"/"false"/"no" -> fully disabled (opt-out)
  ALIN_SKILL_COLLECTOR_URL  central collector endpoint; if unset, local-log only
  ALIN_SKILL_COLLECTOR_TOKEN  bearer token sent as Authorization header
  ALIN_SKILL_LOG            local JSONL path (default ~/.claude/alin-skill-usage.jsonl)
  ALIN_SKILL_PREFIX         namespace to track (default "alin:")
  ALIN_SKILL_USER           override the reported user id (else git email / $USER)
"""

import json
import os
import sys


def _truthy_off(val: str) -> bool:
    return (val or "").strip().lower() in ("0", "off", "false", "no")


def read_event():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def extract_skill(event):
    """Return (skill_name, trigger) or (None, None) if not a skill invocation."""
    ev = event.get("hook_event_name")
    if ev == "UserPromptExpansion":
        name = event.get("skill_name") or event.get("command_name")
        return (name, "slash") if name else (None, None)
    if ev == "PreToolUse" and event.get("tool_name") == "Skill":
        name = (event.get("tool_input") or {}).get("skill")
        return (name, "tool") if name else (None, None)
    return (None, None)


def identity():
    who = os.environ.get("ALIN_SKILL_USER")
    if not who:
        try:
            import subprocess
            who = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True, text=True, timeout=2,
            ).stdout.strip()
        except Exception:
            who = ""
    if not who:
        who = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    try:
        import socket
        host = socket.gethostname()
    except Exception:
        host = "unknown"
    return who, host


def append_local(record, path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def post_remote(record, url, token):
    try:
        import urllib.request
        data = json.dumps(record).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        urllib.request.urlopen(req, timeout=3).read()
    except Exception:
        pass


def dispatch_remote(record, url, token):
    """POST without blocking the user: detach via fork; fall back to a short
    synchronous timeout on platforms without fork (e.g. Windows)."""
    if not url:
        return
    try:
        pid = os.fork()
        if pid == 0:  # child
            try:
                os.setsid()
            except Exception:
                pass
            post_remote(record, url, token)
            os._exit(0)
        # parent returns immediately
    except (AttributeError, OSError):
        post_remote(record, url, token)


def main():
    if _truthy_off(os.environ.get("ALIN_SKILL_TELEMETRY", "")):
        return
    event = read_event()
    skill, trigger = extract_skill(event)
    if not skill:
        return
    prefix = os.environ.get("ALIN_SKILL_PREFIX", "alin:")
    # Track only our plugin's namespaced skills; ignore everything else.
    if prefix and not skill.startswith(prefix):
        return

    who, host = identity()
    record = {
        "ts": _now_iso(),
        "skill": skill,
        "trigger": trigger,               # "slash" (user-typed) | "tool" (model)
        "event": event.get("hook_event_name"),
        "user": who,
        "host": host,
        "session_id": event.get("session_id"),
        "cwd": event.get("cwd"),
        "schema": 1,
    }

    log_path = os.environ.get("ALIN_SKILL_LOG") or os.path.expanduser(
        "~/.claude/alin-skill-usage.jsonl"
    )
    append_local(record, log_path)
    dispatch_remote(
        record,
        os.environ.get("ALIN_SKILL_COLLECTOR_URL", "").strip(),
        os.environ.get("ALIN_SKILL_COLLECTOR_TOKEN", "").strip(),
    )


def _now_iso():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)  # never break the user's session
