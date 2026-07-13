#!/usr/bin/env python3
"""
herdr_sync.py — manage a herdr multi-agent topology. Two topology shapes are
first-class:

  * LOCAL-ONLY: several agents in panes on ONE herdr server, no ssh. The watcher
    can read prompts, auto-judge them, nudge wedged agents, and act on them
    directly (no ssh).
  * REMOTE-BRIDGE: persistent agents on remote hosts (over ssh) mirrored into the
    LOCAL herdr agents tab — herdr has no cross-machine federation, so we bridge
    it by polling each remote's authoritative agent_status and reporting it onto a
    matching LOCAL pane (`pane report-agent`), plus clean per-agent attach views.

WHY THIS EXISTS (the gotchas it encapsulates):
  * herdr is single-server with NO cross-machine agent federation (see above).
  * `report-agent --state` accepts only idle|working|blocked|unknown. herdr also
    derives a "done" state -> we map done -> idle (herdr re-derives the display).
  * Pane/tab numbers RENUMBER when panes/tabs close, so everything is discovered
    BY LABEL (stable intent), never by a hardcoded -N id.
  * NEVER send keystrokes to an attach-view pane (they pass into the live agent).
  * The mirror dies with the Claude session that starts it -> run it as a daemon
    (`install`) so it self-heals across sessions and reboots.
  * When auto-approving a prompt, always pick the plain "Yes" — NEVER a
    "Yes, and don't ask again" option (it would suppress future prompts and blind
    the watcher). See _pick_option().

CONFIG IS NOT HARDCODED. Topology lives in a JSON file (default
~/.config/herdr-mgr/topology.json, override with $HERDR_MGR_HOME). Run
`herdr_sync.py init` to scaffold one, or let the /alin:herdr skill discover and
write it. See `herdr_sync.py schema` for the format.

USAGE
  herdr_sync.py status            show every remote vs local sync + what's alive
  herdr_sync.py revive            idempotently rebuild the remote bridge (servers,
                                  agent panes, local layout, attach views, mirror);
                                  a no-op for a local-only topology
  herdr_sync.py mirror            run the sync loop in the foreground (daemon runs this)
  herdr_sync.py install           provision stable allowlistable script copies, and
                                  (remote-bridge only) install the self-healing daemon
  herdr_sync.py uninstall         stop + remove the daemon
  --- permission watching ---
  herdr_sync.py watch             loop; print a line when an agent NEWLY blocks,
                                  stalls, or gets nudged (run under the Monitor tool)
  herdr_sync.py pending           print the permission prompt of every blocked agent
  herdr_sync.py mode [dryrun|live]   show or set the permission mode
  herdr_sync.py approve <agent>   send the plain "Yes" to a blocked agent
  herdr_sync.py deny <agent>      send "No" to a blocked agent
  herdr_sync.py dismiss <agent>   send Escape to a blocked agent (e.g. feedback prompt)
  herdr_sync.py read <agent> [N]  print the agent's last N visible lines (default 40)
  herdr_sync.py nudge <agent> ["text"]  send the idle-nudge prompt to an agent
  herdr_sync.py send <agent> "<text>"   send literal text to an agent
  herdr_sync.py note "<text>"     append a decision to the decision log
  --- setup helpers ---
  herdr_sync.py init              write a template topology.json (does not overwrite)
  herdr_sync.py schema            print the topology.json schema + an example
"""
import json, os, re, shutil, subprocess, sys, threading, time, platform

HERDR = "herdr"  # assumed on PATH (the skill ensures this)
HOME = os.path.expanduser("~")
STATE_HOME = os.environ.get("HERDR_MGR_HOME", os.path.join(HOME, ".config", "herdr-mgr"))
CONFIG_FILE = os.path.join(STATE_HOME, "topology.json")
MODE_FILE = os.path.join(STATE_HOME, "permission-mode")
POLICY_FILE = os.path.join(STATE_HOME, "permission-policy.md")
DECISIONS_LOG = os.path.join(STATE_HOME, "decisions.log")
MIRROR_LOG = os.path.join(STATE_HOME, "mirror.log")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ATTACH_SH = os.path.join(SCRIPT_DIR, "attach-herdr-agent.sh")
WRAPPER_SH = os.path.join(SCRIPT_DIR, "herdr-act.sh")
SELF = os.path.abspath(__file__)

POLL_SEC = 2
IDLE_TIMEOUT_SEC = 15 * 60
DEFAULT_NUDGE_TEXT = "is everything going well? if there's a bug, fix it"
DAEMON_LABEL = "dev.herdr.mgr-mirror"


# ------------------------------- shell helpers -------------------------------
def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def jrun(cmd, timeout=30):
    """Run a herdr command and return the first JSON object on stdout, or None.

    Tolerant by design: a stopped session, a missing socket, or any non-JSON
    chatter just yields None (callers skip), never an exception."""
    try:
        _, out, _ = run(cmd, timeout)
    except Exception:
        return None
    for line in (out or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except Exception:
                pass
    return None


def die(msg, code=2):
    print(msg)
    sys.exit(code)


def _shq(text):
    """Quote text for safe embedding inside a double-quoted shell argument."""
    return str(text).replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")


# --------------------------------- config ----------------------------------
SCHEMA_EXAMPLE = {
    "local_workspace": "agents",
    "local_sessions": ["default"],
    "monitor": {"local_label": "monitor", "command": None},
    "watch_targets": [],
    "watch_ignore": [],
    "idle_nudge": {
        "enabled": False,
        "after_sec": 900,
        "max_nudges": 2,
        "text": DEFAULT_NUDGE_TEXT,
    },
    "local_agents": [
        {"name": "main", "label": "main", "resume_cmd": None}
    ],
    "remotes": [
        {
            "host": "<ssh-target>",
            "session": "main",
            "project_dir": None,
            "agents": [
                {
                    "name": "agent-a",
                    "remote_label": "agent-a",
                    "local_label": "A1",
                    "resume_cmd": None,
                }
            ],
        }
    ],
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        die(f"no topology config at {CONFIG_FILE}\n"
            f"run `{os.path.basename(SELF)} init` and edit it, or let the /alin:herdr "
            f"skill discover and write it. See `{os.path.basename(SELF)} schema`.")
    try:
        cfg = json.load(open(CONFIG_FILE))
    except Exception as e:
        die(f"topology config {CONFIG_FILE} is not valid JSON: {e}")
    cfg.setdefault("local_workspace", "agents")
    cfg.setdefault("local_sessions", ["default"])
    cfg.setdefault("monitor", None)
    cfg.setdefault("watch_targets", [])
    cfg.setdefault("watch_ignore", [])
    cfg.setdefault("local_agents", [])
    cfg.setdefault("remotes", [])
    nudge = cfg.get("idle_nudge") or {}
    nudge.setdefault("enabled", False)
    nudge.setdefault("after_sec", IDLE_TIMEOUT_SEC)
    nudge.setdefault("max_nudges", 2)
    nudge.setdefault("text", DEFAULT_NUDGE_TEXT)
    cfg["idle_nudge"] = nudge
    for a in cfg["local_agents"]:
        a.setdefault("label", a["name"])
        a.setdefault("resume_cmd", None)
    for r in cfg["remotes"]:
        r.setdefault("session", "main")
        r.setdefault("project_dir", None)
        r.setdefault("agents", [])
        for a in r["agents"]:
            a.setdefault("remote_label", a["name"])
            a.setdefault("local_label", a["name"])
            a.setdefault("resume_cmd", None)
    return cfg


def iter_agents(cfg):
    """Yield (remote, agent) for every REMOTE agent (used by the bridge layout)."""
    for r in cfg["remotes"]:
        for a in r["agents"]:
            yield r, a


def iter_all_agents(cfg):
    """Yield (scope, agent) for every agent, remote and local.
    scope is the remote dict for a remote agent, or None for a local agent."""
    for r in cfg["remotes"]:
        for a in r["agents"]:
            yield r, a
    for a in cfg.get("local_agents", []):
        yield None, a


def find_agent(cfg, name):
    """Return (scope, agent). scope is the remote dict, or None for a local
    agent. (None, None) means not found — disambiguate via the agent being None."""
    for scope, a in iter_all_agents(cfg):
        if a["name"] == name:
            return scope, a
    return None, None


def remote_cmd(r, args):
    return f"ssh {r['host']} 'herdr --session {r['session']} {args}'"


def local_cmd(args):
    return f"{HERDR} {args}"


def local_sessions(cfg):
    return cfg.get("local_sessions") or ["default"]


def local_session_cmd(session, args):
    """A local herdr command scoped to a session. The default session takes no
    --session flag; named sessions do."""
    if session and session != "default":
        return f"{HERDR} --session {session} {args}"
    return f"{HERDR} {args}"


# ----------------------------- discovery helpers -----------------------------
def local_ws_id(cfg):
    d = jrun(local_cmd("workspace list"))
    if not d:
        return None
    for w in d["result"]["workspaces"]:
        if w.get("label") == cfg["local_workspace"]:
            return w["workspace_id"]
    return None


def local_panes_by_label(cfg):
    """Attach-view panes in the bridge workspace (REMOTE-BRIDGE use only)."""
    ws = local_ws_id(cfg)
    if not ws:
        return {}, None
    d = jrun(local_cmd(f"pane list --workspace {ws}"))
    if not d:
        return {}, ws
    return {p.get("label"): p for p in d["result"]["panes"]}, ws


def iter_local_panes(cfg):
    """Yield (session, pane) across every configured local session. Honors
    local_workspace when it resolves in a session; otherwise scans all panes in
    that session. Tolerates stopped / non-JSON sessions (they just yield nothing)."""
    want_ws = cfg.get("local_workspace")
    out = []
    for s in local_sessions(cfg):
        ws_arg = ""
        if want_ws:
            wd = jrun(local_session_cmd(s, "workspace list"))
            if wd:
                for w in wd.get("result", {}).get("workspaces", []):
                    if w.get("label") == want_ws:
                        ws_arg = f" --workspace {w['workspace_id']}"
                        break
        d = jrun(local_session_cmd(s, f"pane list{ws_arg}"))
        if not d:
            continue
        for p in d.get("result", {}).get("panes", []):
            out.append((s, p))
    return out


def local_panes_map(cfg):
    """{label: (session, pane)} across configured local sessions (first match wins)."""
    m = {}
    for s, p in iter_local_panes(cfg):
        lbl = p.get("label")
        if lbl and lbl not in m:
            m[lbl] = (s, p)
    return m


def remote_panes_by_label(r):
    d = jrun(remote_cmd(r, "pane list"))
    if not d:
        return {}
    return {p.get("label"): p for p in d["result"]["panes"]}


def remote_reachable(r):
    _, out, _ = run(f"ssh -o ConnectTimeout=12 {r['host']} 'echo ok' 2>/dev/null", timeout=18)
    return "ok" in out


def remote_server_running(r):
    _, out, _ = run(f"ssh {r['host']} 'herdr session list 2>/dev/null'", timeout=15)
    for line in out.splitlines():
        parts = line.split()
        if parts[:1] == [r["session"]] and "running" in line:
            return True
    return False


def pgrep_attach(remote_pane_id):
    # -f matches full argv; bracket first char so this pattern doesn't self-match.
    _, out, _ = run(f"pgrep -f '[a]ttach-herdr-agent.sh {remote_pane_id}'")
    return bool(out.strip())


# --------------------------------- status -----------------------------------
def cmd_status():
    cfg = load_config()
    # local agents (always shown when configured)
    if cfg.get("local_agents"):
        pm = local_panes_map(cfg)
        print(f"local agents (sessions {local_sessions(cfg)}):")
        print("    agent        label/status                 session")
        for a in cfg["local_agents"]:
            lbl = a.get("label", a["name"])
            sp = pm.get(lbl)
            if sp:
                sess, p = sp
                st = p.get("agent_status", "no-agent") if p.get("agent") else "no-agent"
                print(f"    {a['name']:<12} {lbl + '/' + st:<28} {sess}")
            else:
                print(f"    {a['name']:<12} {lbl + '/MISSING':<28} -")
        print()
    # remote bridge (only meaningful when remotes exist)
    if not cfg["remotes"]:
        if not cfg.get("local_agents"):
            print("no agents configured (set local_agents and/or remotes in topology.json)")
        else:
            print("local-only topology: no remotes, no mirror/attach bridge needed.")
        return
    lp, ws = local_panes_by_label(cfg)
    print(f"local bridge workspace `{cfg['local_workspace']}`: {ws or 'MISSING'}")
    print(f"mirror daemon ({DAEMON_LABEL}): {'loaded' if daemon_loaded() else 'not loaded'}; "
          f"process: {'alive' if mirror_proc_alive() else 'dead'}")
    for r in cfg["remotes"]:
        print(f"\nremote `{r['host']}` session `{r['session']}`:")
        if not remote_reachable(r):
            print("  host UNREACHABLE (down / rebooting / network) — cannot revive until it answers ssh")
            continue
        print(f"  server: {'RUNNING' if remote_server_running(r) else 'STOPPED'}")
        bp = remote_panes_by_label(r)
        print("    agent        remote(label/status)       local(label/status)        attach")
        for a in r["agents"]:
            b = bp.get(a["remote_label"])
            l = lp.get(a["local_label"])
            bstat = f"{a['remote_label']}/{b['agent_status']}" if b else f"{a['remote_label']}/MISSING"
            lstat = f"{a['local_label']}/{l['agent_status']}" if l else f"{a['local_label']}/MISSING"
            at = "up" if (b and pgrep_attach(b["pane_id"])) else "DOWN"
            print(f"    {a['name']:<12} {bstat:<26} {lstat:<26} {at}")


# ---------------------------------- watch -----------------------------------
def _collect_agents(cfg):
    """Return [(display, src, state, pane_id, label, session)] across all remote
    agents + configured local agents. Only CONFIGURED local agents are reported,
    so unrelated/new local panes (and the monitor's own pane) never leak in."""
    out_agents = []
    for r in cfg["remotes"]:
        d = jrun(remote_cmd(r, "pane list"), timeout=20)
        if not d:
            continue
        name_by_label = {a["remote_label"]: a["name"] for a in r["agents"]}
        for p in d.get("result", {}).get("panes", []):
            if not p.get("agent"):
                continue
            lbl = p.get("label") or p.get("pane_id", "unknown")
            display = name_by_label.get(lbl, f"{r['host']}:{lbl}")
            out_agents.append((display, r["host"], p.get("agent_status", "unknown"),
                               p.get("pane_id", lbl), lbl, r["session"]))
    if cfg.get("local_agents"):
        pm = local_panes_map(cfg)
        for a in cfg["local_agents"]:
            lbl = a.get("label", a["name"])
            sp = pm.get(lbl)
            if not sp:
                continue
            sess, p = sp
            if not p.get("agent"):
                continue
            out_agents.append((a["name"], "local", p.get("agent_status", "unknown"),
                               p.get("pane_id", lbl), lbl, sess))
    return out_agents


def _watch_allowed(cfg, display, label):
    """Apply monitor self-exclusion, watch_ignore, and (if set) watch_targets."""
    mon = (cfg.get("monitor") or {}).get("local_label")
    if mon and (label == mon or display == mon):
        return False
    ignore = set(cfg.get("watch_ignore") or [])
    if display in ignore or label in ignore:
        return False
    targets = cfg.get("watch_targets") or []
    if targets:
        return display in targets or label in targets
    return True


def cmd_watch():
    """Loop forever; print one line on a meaningful change. Run under the Monitor
    tool — each printed line becomes an event.

    Emits:
      BLOCKED: <agent> ...   on a new permission prompt
      NUDGED:  <agent> ...   when idle-nudge fires (live mode, nudge enabled)
      STALLED: <agent> ...   when an agent has held a non-terminal state too long;
                             RE-FIRES every idle window while it stays stuck
    """
    cfg = load_config()
    nudge_cfg = cfg.get("idle_nudge") or {}
    idle_after = int(nudge_cfg.get("after_sec") or IDLE_TIMEOUT_SEC)
    nudge_enabled = bool(nudge_cfg.get("enabled"))
    max_nudges = int(nudge_cfg.get("max_nudges") or 0)
    nudge_text = nudge_cfg.get("text") or DEFAULT_NUDGE_TEXT
    mins = max(1, int(idle_after // 60))

    prev_blocked = set()
    state_since = {}      # key -> (state, first_seen_ts)
    last_action = {}      # key -> ts of last STALLED/NUDGE action
    nudge_count = {}      # key -> int
    while True:
        now = time.time()
        agents = [t for t in _collect_agents(cfg) if _watch_allowed(cfg, t[0], t[4])]
        live = get_mode() == "live"

        cur_blocked = {(d, s) for d, s, st, _, _, _ in agents if st == "blocked"}
        for d, s in sorted(cur_blocked - prev_blocked):
            print(f"BLOCKED: {d} ({s}) is waiting on a permission prompt", flush=True)
        prev_blocked = cur_blocked

        seen_keys = set()
        for d, s, st, pid, lbl, sess in agents:
            key = (d, s)
            seen_keys.add(key)
            if st in ("done", "unknown"):
                state_since.pop(key, None)
                last_action.pop(key, None)
                nudge_count.pop(key, None)
                continue
            prev_state, first_seen = state_since.get(key, (None, now))
            if prev_state != st:
                state_since[key] = (st, now)
                last_action.pop(key, None)
                nudge_count.pop(key, None)
                continue
            held = now - first_seen
            if held < idle_after:
                continue
            since_action = now - last_action.get(key, first_seen)
            if since_action < idle_after:
                continue
            last_action[key] = now
            # Nudge (prod the agent) only for non-blocked agents, in live mode,
            # while nudges remain. A blocked agent is a permission prompt — never
            # type a prod into it; surface it as STALLED instead.
            if (nudge_enabled and live and st != "blocked"
                    and nudge_count.get(key, 0) < max_nudges):
                n = nudge_count.get(key, 0) + 1
                nudge_count[key] = n
                ok = _agent_send_by_display(cfg, d, nudge_text)
                tag = "NUDGED" if ok else "NUDGE-FAILED"
                print(f"{tag}: {d} ({s}) idle {mins}+ min — prod #{n}/{max_nudges} sent", flush=True)
            else:
                print(f"STALLED: {d} ({s}) has been {st} for {mins}+ min — check pane {pid}", flush=True)
        # forget agents that disappeared
        for key in list(state_since):
            if key not in seen_keys:
                state_since.pop(key, None)
                last_action.pop(key, None)
                nudge_count.pop(key, None)
        time.sleep(5)


# --------------------------- permission judging -----------------------------
def cmd_pending():
    cfg = load_config()
    any_blocked = False
    for r in cfg["remotes"]:
        d = jrun(remote_cmd(r, "pane list"))
        if not d:
            print(f"({r['host']} unreachable)")
            continue
        name_by_label = {a["remote_label"]: a["name"] for a in r["agents"]}
        for p in d.get("result", {}).get("panes", []):
            if p.get("agent") and p.get("agent_status") == "blocked":
                any_blocked = True
                pid = p["pane_id"]
                _, out, _ = run(remote_cmd(r, f"pane read {pid} --source visible --lines 35"))
                disp = name_by_label.get(p.get("label"), p.get("label") or pid)
                print(f"===== BLOCKED: {disp} ({r['host']} {pid}) =====")
                print(out.strip())
                print()
    if cfg.get("local_agents"):
        pm = local_panes_map(cfg)
        for a in cfg["local_agents"]:
            lbl = a.get("label", a["name"])
            sp = pm.get(lbl)
            if not sp:
                continue
            sess, p = sp
            if p.get("agent") and p.get("agent_status") == "blocked":
                any_blocked = True
                pid = p["pane_id"]
                _, out, _ = run(local_session_cmd(sess, f"pane read {pid} --source visible --lines 35"))
                print(f"===== BLOCKED: {a['name']} (local {sess} {pid}) =====")
                print(out.strip())
                print()
    if not any_blocked:
        print("no blocked agents")


def get_mode():
    try:
        return open(MODE_FILE).read().strip() or "dryrun"
    except Exception:
        return "dryrun"


def cmd_mode():
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if arg in ("dryrun", "live"):
        os.makedirs(os.path.dirname(MODE_FILE), exist_ok=True)
        open(MODE_FILE, "w").write(arg + "\n")
        print(f"permission mode set: {arg}")
    else:
        print(f"permission mode: {get_mode()}   (change with: mode dryrun|live)")


def cmd_note():
    msg = " ".join(sys.argv[2:])
    os.makedirs(os.path.dirname(DECISIONS_LOG), exist_ok=True)
    with open(DECISIONS_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
    print("logged.")


def _parse_options(text):
    """Extract [(num, label)] from a permission prompt's visible text."""
    opts = []
    for line in text.splitlines():
        m = re.search(r"(\d+)\.\s+(.*\S)", line)
        if m:
            opts.append((m.group(1), m.group(2).strip()))
    return opts


def _pick_option(text, want):
    """Pick the option number for an approve/deny decision.
    approve -> the plain 'Yes' (NEVER 'Yes, don't ask again' / 'Yes to all').
    deny    -> the plain 'No'."""
    for num, label in _parse_options(text):
        ll = label.lower()
        if want == "approve" and ll.startswith("yes") and "don't ask" not in ll and "all" not in ll:
            return num
        if want == "deny" and ll.startswith("no"):
            return num
    return None


# --- pane resolution + raw actions (local or remote) ---
def _resolve_agent_pane(cfg, scope, a):
    """Return (kind, ctx, pane) where kind is 'local'|'remote', ctx is the local
    session string or the remote dict. None if the pane can't be found."""
    if scope is None:
        sp = local_panes_map(cfg).get(a.get("label", a["name"]))
        if not sp:
            return None
        sess, p = sp
        return ("local", sess, p)
    p = remote_panes_by_label(scope).get(a["remote_label"])
    if not p:
        return None
    return ("remote", scope, p)


def _pane_read(kind, ctx, pid, lines=100):
    if kind == "local":
        _, out, _ = run(local_session_cmd(ctx, f"pane read {pid} --source visible --lines {lines}"))
    else:
        _, out, _ = run(remote_cmd(ctx, f"pane read {pid} --source visible --lines {lines}"))
    return out


def _pane_send_keys(kind, ctx, pid, keys):
    if kind == "local":
        run(local_session_cmd(ctx, f"pane send-keys {pid} {keys}"))
    else:
        run(remote_cmd(ctx, f"pane send-keys {pid} {keys}"))


def _agent_send_text(kind, ctx, pid, text):
    """Type literal text into an agent AND submit it. `agent send` only writes
    the text (it does NOT press Enter — that is herdr's documented behavior), so
    we follow it with an explicit `send-keys enter` to actually deliver."""
    if kind == "local":
        run(local_session_cmd(ctx, f'agent send {pid} "{_shq(text)}"'))
        time.sleep(0.3)
        run(local_session_cmd(ctx, f"pane send-keys {pid} enter"))
    else:
        run(f"""ssh {ctx['host']} 'herdr --session {ctx['session']} agent send {pid} "{_shq(text)}"'""")
        time.sleep(0.3)
        run(remote_cmd(ctx, f"pane send-keys {pid} enter"))


def _agent_send_by_display(cfg, display, text):
    """Send text to an agent identified by its watch display name. Returns True
    if the agent resolved and a send was issued."""
    scope, a = find_agent(cfg, display)
    if not a:
        return False
    res = _resolve_agent_pane(cfg, scope, a)
    if not res:
        return False
    kind, ctx, p = res
    _agent_send_text(kind, ctx, p["pane_id"], text)
    return True


def _decide(name, want):
    """want: 'approve' -> pick the plain Yes; 'deny' -> pick No. Sends the option key."""
    cfg = load_config()
    scope, a = find_agent(cfg, name)
    if not a:
        print(f"unknown agent '{name}' (known: {[ag['name'] for _, ag in iter_all_agents(cfg)]})")
        return
    res = _resolve_agent_pane(cfg, scope, a)
    if not res:
        where = f"sessions {local_sessions(cfg)}" if scope is None else scope["host"]
        lbl = a.get("label", a["name"]) if scope is None else a["remote_label"]
        print(f"no pane labelled {lbl} ({where})")
        return
    kind, ctx, p = res
    if p.get("agent_status") != "blocked":
        print(f"{name} is not blocked (status={p.get('agent_status')}); nothing to send")
        return
    pid = p["pane_id"]
    out = _pane_read(kind, ctx, pid, lines=100)
    target = _pick_option(out, want)
    if not target:
        print(f"could not locate a '{want}' option; read the pane and act manually:\n{out.strip()[-700:]}")
        print("(if the prompt scrolled off, increase --lines in _pane_read())")
        return
    _pane_send_keys(kind, ctx, pid, f"{target} enter")
    loc = f"local {ctx} {pid}" if kind == "local" else f"{ctx['host']} {pid}"
    print(f"{want}: sent option {target} to {name} ({loc}). VERIFY with `pending`.")


def cmd_approve():
    _decide(sys.argv[2] if len(sys.argv) > 2 else "", "approve")


def cmd_deny():
    _decide(sys.argv[2] if len(sys.argv) > 2 else "", "deny")


def cmd_dismiss():
    """Send Escape to a blocked agent — e.g. to dismiss a feedback prompt."""
    name = sys.argv[2] if len(sys.argv) > 2 else ""
    cfg = load_config()
    scope, a = find_agent(cfg, name)
    if not a:
        print(f"unknown agent '{name}' (known: {[ag['name'] for _, ag in iter_all_agents(cfg)]})")
        return
    res = _resolve_agent_pane(cfg, scope, a)
    if not res:
        print(f"could not resolve a pane for {name}")
        return
    kind, ctx, p = res
    _pane_send_keys(kind, ctx, p["pane_id"], "esc")
    print(f"dismiss: sent esc to {name}. VERIFY with `pending`.")


def cmd_read():
    name = sys.argv[2] if len(sys.argv) > 2 else ""
    lines = sys.argv[3] if len(sys.argv) > 3 else "40"
    cfg = load_config()
    scope, a = find_agent(cfg, name)
    if not a:
        print(f"unknown agent '{name}' (known: {[ag['name'] for _, ag in iter_all_agents(cfg)]})")
        return
    res = _resolve_agent_pane(cfg, scope, a)
    if not res:
        print(f"could not resolve a pane for {name}")
        return
    kind, ctx, p = res
    out = _pane_read(kind, ctx, p["pane_id"], lines=lines)
    print(out.strip())


def cmd_nudge():
    name = sys.argv[2] if len(sys.argv) > 2 else ""
    cfg = load_config()
    scope, a = find_agent(cfg, name)
    if not a:
        print(f"unknown agent '{name}' (known: {[ag['name'] for _, ag in iter_all_agents(cfg)]})")
        return
    text = sys.argv[3] if len(sys.argv) > 3 else (cfg.get("idle_nudge") or {}).get("text") or DEFAULT_NUDGE_TEXT
    if _agent_send_by_display(cfg, name, text):
        print(f"nudge: sent to {name}: {text!r}")
    else:
        print(f"could not resolve a pane for {name}")


def cmd_send():
    name = sys.argv[2] if len(sys.argv) > 2 else ""
    text = " ".join(sys.argv[3:])
    if not text:
        print("usage: send <agent> \"<text>\"")
        return
    cfg = load_config()
    if _agent_send_by_display(cfg, name, text):
        print(f"send: delivered to {name}: {text!r}")
    else:
        print(f"unknown agent '{name}' or no pane (known: {[ag['name'] for _, ag in iter_all_agents(cfg)]})")


# ---------------------------------- mirror ----------------------------------
def resolve_targets(cfg, r):
    """remote pane label -> local pane id, re-resolved each (re)connect."""
    lp, _ = local_panes_by_label(cfg)
    t = {}
    for a in r["agents"]:
        l = lp.get(a["local_label"])
        if l:
            t[a["remote_label"]] = l["pane_id"]
    return t


def mirror_one_remote(cfg, r):
    """One self-reconnecting status-stream loop for a single remote (one thread)."""
    src = f"mirror:{r['host']}"
    while True:
        targets = resolve_targets(cfg, r)
        if not targets:
            log(f"[mirror {r['host']}] no local panes for labels yet; retry in 5s")
            time.sleep(5)
            continue
        rcmd = (f"while true; do herdr --session {r['session']} pane list 2>/dev/null; "
                f"sleep {POLL_SEC}; done")
        proc = subprocess.Popen(
            ["ssh", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3", r["host"], rcmd],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    panes = json.loads(line)["result"]["panes"]
                except Exception:
                    continue
                by_label = {p.get("label"): p for p in panes}
                for blabel, lpid in targets.items():
                    p = by_label.get(blabel)
                    if not p or not p.get("agent"):
                        continue
                    st = p["agent_status"]
                    st = "idle" if st == "done" else st          # API rejects "done"
                    if st in ("idle", "working", "blocked"):
                        agent_kind = p.get("agent", "claude")
                        run(local_cmd(f"pane report-agent {lpid} --source {src} "
                                      f"--agent {agent_kind} --state {st}") + " >/dev/null 2>&1")
        except Exception as e:
            log(f"[mirror {r['host']}] stream error: {e}")
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
        log(f"[mirror {r['host']}] ssh dropped; reconnecting in 3s")
        time.sleep(3)


def cmd_mirror():
    cfg = load_config()
    if not cfg["remotes"]:
        log("[mirror] no remotes configured; nothing to do (local-only topology)")
        return
    log(f"[mirror] start: {[r['host'] for r in cfg['remotes']]}")
    threads = []
    for r in cfg["remotes"]:
        t = threading.Thread(target=mirror_one_remote, args=(cfg, r), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


# ---------------------------------- revive ----------------------------------
def cmd_revive():
    cfg = load_config()
    if not cfg["remotes"]:
        print("local-only topology — no remote bridge to revive.")
        # Best-effort: restart any local agent whose pane exists but has no agent.
        if cfg.get("local_agents"):
            pm = local_panes_map(cfg)
            for a in cfg["local_agents"]:
                lbl = a.get("label", a["name"])
                sp = pm.get(lbl)
                if not sp:
                    print(f"  · {a['name']}: no pane labelled {lbl} (create it, then re-run)")
                    continue
                sess, p = sp
                if p.get("agent"):
                    print(f"  · {a['name']}: already running ({p.get('agent')})")
                elif a.get("resume_cmd"):
                    print(f"  · {a['name']}: starting -> {a['resume_cmd']}")
                    run(local_session_cmd(sess, f"pane run {p['pane_id']} \"{a['resume_cmd']}\""))
                else:
                    print(f"  · {a['name']}: pane ready (no resume_cmd; start it yourself)")
        print("\nrevive complete — run `status` to verify.")
        return

    # 1) per-remote: server + agent panes + resume
    for r in cfg["remotes"]:
        print(f"\n· remote {r['host']} (session {r['session']})")
        if not remote_reachable(r):
            print("  UNREACHABLE — skipping; re-run revive once it answers ssh")
            continue
        if not remote_server_running(r):
            print("  · server down -> starting headless")
            run(f"ssh {r['host']} 'nohup setsid herdr --session {r['session']} server "
                f">~/.herdr/{r['session']}-server.log 2>&1 </dev/null & sleep 3'", timeout=20)
            time.sleep(2)
        if not remote_server_running(r):
            print("  ! server STILL DOWN — skipping this remote")
            continue
        bp = remote_panes_by_label(r)
        # ensure a labelled pane per agent (build a workspace of tabs if missing)
        if not all(a["remote_label"] in bp for a in r["agents"]):
            print("  · agent panes missing -> building workspace")
            d = jrun(remote_cmd(r, "workspace create --label agents --focus"))
            if d and r["agents"]:
                run(remote_cmd(r, f"tab rename {d['result']['workspace']['workspace_id']}:1 "
                                  f"{r['agents'][0]['remote_label']}"))
                for a in r["agents"][1:]:
                    run(remote_cmd(r, f"tab create --label {a['remote_label']} --no-focus"))
            bp = remote_panes_by_label(r)
        for a in r["agents"]:
            p = bp.get(a["remote_label"])
            if not p:
                print(f"    ! {a['name']}: no pane labelled {a['remote_label']}, skipping")
                continue
            if p.get("agent"):
                print(f"    · {a['name']}: already running ({p['agent']})")
                continue
            if a["resume_cmd"]:
                cd = f"cd {r['project_dir']} && " if r.get("project_dir") else ""
                print(f"    · {a['name']}: starting -> {a['resume_cmd']}")
                run(remote_cmd(r, f"pane run {p['pane_id']} \"{cd}{a['resume_cmd']}\""))
            else:
                print(f"    · {a['name']}: pane ready (no resume_cmd set; start it yourself)")

    # 2) local layout (deterministic: split + label by returned pane id)
    lp, ws = local_panes_by_label(cfg)
    want = {a["local_label"] for _, a in iter_agents(cfg)}
    if cfg.get("monitor"):
        want.add(cfg["monitor"]["local_label"])
    if not ws or not want.issubset(set(lp)):
        print("\n· local layout missing/incomplete -> rebuilding workspace")
        build_local_layout(cfg)
        lp, ws = local_panes_by_label(cfg)

    # 3) attach views per agent (relaunch only if down; never send keys to them)
    print()
    for r in cfg["remotes"]:
        bp = remote_panes_by_label(r)
        for a in r["agents"]:
            bpid = bp.get(a["remote_label"], {}).get("pane_id")
            lpane = lp.get(a["local_label"])
            if not bpid or not lpane:
                continue
            if pgrep_attach(bpid):
                print(f"· {a['name']} attach: already up")
            else:
                print(f"· {a['name']} attach: launching in {a['local_label']}")
                run(local_cmd(f"pane run {lpane['pane_id']} "
                              f"\"clear; bash {ATTACH_SH} {bpid} {r['host']} {r['session']}\""))

    # 4) optional monitor pane
    mon = cfg.get("monitor")
    if mon and mon.get("command") and lp.get(mon["local_label"]):
        run(local_cmd(f"pane run {lp[mon['local_label']]['pane_id']} \"clear; {mon['command']}\""))

    # 5) mirror daemon
    if daemon_loaded():
        print("\n· mirror: managed by the daemon (self-healing) ✓")
    elif mirror_proc_alive():
        print("\n· mirror: already running (foreground)")
    else:
        print("\n· mirror: not running -> `install` for self-healing, or run `mirror &`")
    print("\nrevive complete — run `status` to verify.")


def build_local_layout(cfg):
    """Create the local workspace and one labelled pane per REMOTE agent (+ optional
    monitor), labelling each pane by the id the split returns (deterministic)."""
    d = jrun(local_cmd(f"workspace create --label {cfg['local_workspace']} --focus"))
    if not d:
        return None
    root = d["result"]["root_pane"]["pane_id"]
    labels = [a["local_label"] for _, a in iter_agents(cfg)]
    if not labels:
        return d["result"]["workspace"]["workspace_id"]
    # optional monitor strip on the bottom
    mon = cfg.get("monitor")
    if mon:
        md = jrun(local_cmd(f"pane split {root} --direction down --no-focus"))
        if md:
            run(local_cmd(f"pane rename {md['result']['pane']['pane_id']} {mon['local_label']}"))
    # first agent = root; remaining agents split off to the right
    run(local_cmd(f"pane rename {root} {labels[0]}"))
    for lbl in labels[1:]:
        sd = jrun(local_cmd(f"pane split {root} --direction right --no-focus"))
        if sd:
            run(local_cmd(f"pane rename {sd['result']['pane']['pane_id']} {lbl}"))
    return d["result"]["workspace"]["workspace_id"]


# ----------------------------- daemon (self-heal) ----------------------------
def _py():
    return sys.executable or "python3"


def daemon_loaded():
    if platform.system() == "Darwin":
        rc, out, _ = run(f"launchctl list 2>/dev/null | grep {DAEMON_LABEL}")
        return rc == 0 and DAEMON_LABEL in out
    if platform.system() == "Linux":
        rc, out, _ = run(f"systemctl --user is-active {DAEMON_LABEL}.service 2>/dev/null")
        return "active" in out
    return False


def mirror_proc_alive():
    _, out, _ = run("pgrep -f '[h]erdr_sync.py mirror'")
    return bool(out.strip())


LAUNCHD_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key>
  <array><string>{python}</string><string>{self}</string><string>mirror</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>{path}</string>
    <key>HERDR_MGR_HOME</key><string>{home}</string></dict>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict></plist>
"""

SYSTEMD_UNIT = """[Unit]
Description=herdr-mgr status mirror
After=network-online.target

[Service]
Type=simple
Environment=HERDR_MGR_HOME={home}
ExecStart={python} {self} mirror
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""


def _provision_scripts():
    """Copy herdr_sync.py + herdr-act.sh to STABLE paths under STATE_HOME so the
    long-running daemon and any Bash allowlist entry never point into the
    versioned plugin cache (which moves on every plugin update). Returns the
    stable herdr_sync.py path (falls back to SELF on failure)."""
    os.makedirs(STATE_HOME, exist_ok=True)
    daemon_script = os.path.join(STATE_HOME, "herdr_sync.py")
    try:
        shutil.copy2(SELF, daemon_script)
        os.chmod(daemon_script, 0o755)
    except Exception as e:
        print(f"warn: could not copy mirror script to {daemon_script} ({e}); "
              f"daemon will reference the plugin cache and may break on update.")
        daemon_script = SELF
    if os.path.exists(WRAPPER_SH):
        try:
            dst = os.path.join(STATE_HOME, "herdr-act.sh")
            shutil.copy2(WRAPPER_SH, dst)
            os.chmod(dst, 0o755)
        except Exception as e:
            print(f"warn: could not copy action wrapper to {STATE_HOME} ({e}).")
    return daemon_script


def cmd_install():
    cfg = load_config()
    sysname = platform.system()
    path_env = os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin")
    daemon_script = _provision_scripts()
    print(f"provisioned stable scripts under {STATE_HOME}:")
    print(f"  {os.path.join(STATE_HOME, 'herdr_sync.py')}")
    if os.path.exists(os.path.join(STATE_HOME, "herdr-act.sh")):
        print(f"  {os.path.join(STATE_HOME, 'herdr-act.sh')}")
    print("allowlist these stable paths in the monitor session so it never trips its own prompts:")
    print(f"  Bash({_py()} {os.path.join(STATE_HOME, 'herdr_sync.py')}:*)")
    if os.path.exists(os.path.join(STATE_HOME, "herdr-act.sh")):
        print(f"  Bash({os.path.join(STATE_HOME, 'herdr-act.sh')}:*)")

    if not cfg["remotes"]:
        print("\nlocal-only topology: the mirror daemon only bridges remote agents — "
              "nothing more to install.")
        return

    if sysname == "Darwin":
        plist_path = os.path.join(HOME, "Library", "LaunchAgents", DAEMON_LABEL + ".plist")
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        open(plist_path, "w").write(LAUNCHD_PLIST.format(
            label=DAEMON_LABEL, python=_py(), self=daemon_script, path=path_env,
            home=STATE_HOME, log=MIRROR_LOG))
        run(f"launchctl unload {plist_path} 2>/dev/null")
        rc, _, err = run(f"launchctl load {plist_path}")
        print(f"\ninstalled {plist_path}")
        print(f"loaded: {daemon_loaded()}  (logs: {MIRROR_LOG})")
        if err.strip():
            print("launchctl:", err.strip())
    elif sysname == "Linux":
        unit_dir = os.path.join(HOME, ".config", "systemd", "user")
        os.makedirs(unit_dir, exist_ok=True)
        unit_path = os.path.join(unit_dir, DAEMON_LABEL + ".service")
        open(unit_path, "w").write(SYSTEMD_UNIT.format(python=_py(), self=daemon_script, home=STATE_HOME))
        run("systemctl --user daemon-reload")
        rc, _, err = run(f"systemctl --user enable --now {DAEMON_LABEL}.service")
        print(f"\ninstalled {unit_path}")
        print(f"active: {daemon_loaded()}  (logs: journalctl --user -u {DAEMON_LABEL})")
        if err.strip():
            print("systemctl:", err.strip())
        print("tip: `loginctl enable-linger $USER` keeps it running while you're logged out.")
    else:
        print(f"\nno managed-daemon support for {sysname}. Run the mirror yourself, e.g.:")
        print(f"  nohup {_py()} {daemon_script} mirror >{MIRROR_LOG} 2>&1 &")


def cmd_uninstall():
    sysname = platform.system()
    if sysname == "Darwin":
        plist_path = os.path.join(HOME, "Library", "LaunchAgents", DAEMON_LABEL + ".plist")
        run(f"launchctl unload {plist_path} 2>/dev/null")
        if os.path.exists(plist_path):
            os.remove(plist_path)
        print("launchd agent removed.")
    elif sysname == "Linux":
        run(f"systemctl --user disable --now {DAEMON_LABEL}.service 2>/dev/null")
        unit_path = os.path.join(HOME, ".config", "systemd", "user", DAEMON_LABEL + ".service")
        if os.path.exists(unit_path):
            os.remove(unit_path)
        run("systemctl --user daemon-reload")
        print("systemd user unit removed.")
    else:
        print("nothing managed to remove; kill any `herdr_sync.py mirror` you started by hand.")
    copy = os.path.join(STATE_HOME, "herdr_sync.py")
    if os.path.exists(copy):
        os.remove(copy)


def log(msg):
    line = f"{int(time.time())} {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(MIRROR_LOG), exist_ok=True)
        with open(MIRROR_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# --------------------------------- setup ------------------------------------
def cmd_init():
    if os.path.exists(CONFIG_FILE):
        print(f"{CONFIG_FILE} already exists — not overwriting. Edit it by hand.")
        return
    os.makedirs(STATE_HOME, exist_ok=True)
    json.dump(SCHEMA_EXAMPLE, open(CONFIG_FILE, "w"), indent=2)
    print(f"wrote template {CONFIG_FILE} — edit it (or let the /alin:herdr skill fill it in).")


def cmd_schema():
    print("topology.json schema. A LOCAL-only setup needs only `local_agents`; a "
          "REMOTE bridge uses `remotes[]` (each agent maps a remote pane label -> a "
          "local pane label). Both may coexist.\n")
    print(json.dumps(SCHEMA_EXAMPLE, indent=2))
    print(f"\nlives at: {CONFIG_FILE}  (override dir with $HERDR_MGR_HOME)")
    print("fields:")
    print("  local_workspace   label of the local herdr workspace (bridge view / local-agent scope)")
    print("  local_sessions    herdr sessions to watch locally (default ['default'])")
    print("  monitor           optional {local_label, command}; its pane is auto-excluded from watch")
    print("  watch_targets     optional allowlist of agent names/labels to watch (empty = all)")
    print("  watch_ignore      optional denylist of agent names/labels to skip")
    print("  idle_nudge        {enabled, after_sec, max_nudges, text}: prod a wedged agent on idle")
    print("  local_agents[]    LOCAL agents: {name, label (pane label), resume_cmd?}")
    print("  remotes[].host    ssh target (a host alias in ~/.ssh/config is ideal)")
    print("  remotes[].session herdr session name on that remote (default 'main')")
    print("  remotes[].project_dir  optional cwd prepended to resume_cmd")
    print("  agents[].name         unique handle used by approve/deny/status")
    print("  agents[].remote_label herdr pane label on the remote")
    print("  agents[].local_label  herdr pane label locally (the attach view)")
    print("  agents[].resume_cmd   optional command to (re)start the agent, e.g. 'claude --resume <id>'")


# --------------------------------- dispatch ---------------------------------
CMDS = {
    "status": cmd_status, "revive": cmd_revive, "mirror": cmd_mirror,
    "install": cmd_install, "uninstall": cmd_uninstall,
    "watch": cmd_watch, "pending": cmd_pending, "mode": cmd_mode, "note": cmd_note,
    "approve": cmd_approve, "deny": cmd_deny, "dismiss": cmd_dismiss,
    "read": cmd_read, "nudge": cmd_nudge, "send": cmd_send,
    "init": cmd_init, "schema": cmd_schema,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd not in CMDS:
        print(__doc__)
        sys.exit(2)
    CMDS[cmd]()
