---
name: herdr
description: Manage a herdr multi-agent terminal topology, local-only or with ssh remotes. Installs herdr if missing, discovers and remembers the current topology (servers, sessions, panes, agents, ssh remotes), builds/revives pane layouts, bridges persistent remote (ssh) agents into the LOCAL agents tab — which herdr does NOT do natively — relays messages between agents/panes, and watches + auto-judges (approve/deny/dismiss) AND nudges agents' permission/idle prompts against a user-defined policy, including agents running locally on one machine. Use when the user says "/herdr", "herdr", "set up herdr", "revive the panes", "bring the agents back", "wire my remote agents", "watch my local agents", "sync the agents tab", "watch the agents", "judge/approve the permission prompts", "nudge the stuck agent", "go live / dry-run", or asks to inspect or restore a herdr agent view.
license: MIT
metadata:
  category: ml-ops
---

# herdr — multi-agent terminal orchestration

[herdr](https://herdr.dev) is an open-source terminal workspace manager for AI coding
agents (panes, tabs, named persistent sessions, agent detection, `--remote` ssh attach).
This skill adds the orchestration layer herdr does **not** ship natively. It supports two
topology shapes, which can coexist:

- **Local-only** — several agents in panes on **one** herdr server, no ssh. The skill can
  watch them, read their prompts, auto-judge (approve/deny/dismiss), and **nudge** a wedged
  agent — all without ssh.
- **Remote-bridge** — agents that run persistently on a **remote host (over ssh)** mirrored
  into your local agents tab; herdr has no cross-machine federation, so the skill bridges it
  with status mirroring + clean per-agent attach views.

On top of either shape: topology discovery, idempotent revival, and policy-driven permission
and idle handling.

Everything is driven by a bundled tool: `python3 ${CLAUDE_SKILL_DIR}/scripts/herdr_sync.py <cmd>`.
It is **config-driven, not hardcoded** — the topology lives in `~/.config/herdr-mgr/topology.json`
(override the dir with `$HERDR_MGR_HOME`). Run `herdr_sync.py schema` to see the format.

## Core abilities

1. **Bootstrap** — ensure `herdr` is installed and the agent integration is active.
2. **Topology discovery & memory** — detect the live topology and persist it (to the
   config file *and* your memory) so later sessions don't re-derive it.
3. **Pane / layout management** — build and idempotently *revive* the workspace, panes,
   labels, and splits after a restart.
4. **Cross-server wiring (the non-native core, remote only)** — mirror remote agents'
   status into local panes and keep clean per-agent attach views alive over ssh.
5. **Inter-agent communication** — relay text/commands between agents and panes.
6. **Liveness & permission monitoring** — surface agents that newly block *or* stall
   (local and remote alike), scoped to configured agents.
7. **Policy-driven auto-judgment & nudging** — approve/deny/dismiss blocked agents'
   permission prompts against a user policy; prod idle/wedged agents; escalate the rest.
8. **Lifecycle** — start/resume agents; provision allowlistable scripts; install/remove the
   self-healing mirror daemon (remote only).

---

## Step 0 — ensure herdr is installed

Check first: `herdr status` (or `herdr --version`). If herdr is missing:

- **Install** (open source, see https://herdr.dev): the supported path is the install
  script from the website, or `herdr update` if a copy is already present on `$PATH`.
  Confirm the install method with the user before running a network install script.
- **Agent integration** (needed for state detection like `working`/`blocked`/`done`):
  `herdr integration install claude` (also: `codex`, `copilot`, `opencode`, …). Run on
  **every** host that runs agents — your local machine *and* each remote.

Assume the `herdr` command works once present; don't hunt for its binary path.

## Step 1 — discover the topology and remember it

If `~/.config/herdr-mgr/topology.json` already exists, load it and skip to operations.
Otherwise discover the current setup, then write **both** the config file and a memory.

**Discover** (read-only):
- Local: `herdr session list`, `herdr workspace list`, `herdr pane list` — note the
  session(s) and workspace holding the agent panes, and which panes run agents.
- **Decide the shape.** If the user has **no remote/ssh agents** (a single-machine,
  multi-agent setup), this is **local-only**: write a top-level `local_agents` array and
  leave `remotes: []`. Set `local_workspace` to the workspace the agents live in (or `null`
  to scan all), and `local_sessions` to the herdr session(s) to watch (default `["default"]`).
  For each local agent settle a unique `name`, its pane `label`, and an optional `resume_cmd`.
- If the user **does** run durable agents on remote hosts: ask the **ssh target** for each
  (a `~/.ssh/config` alias is ideal). For each: `ssh <host> 'herdr session list'` and
  `ssh <host> 'herdr --session <s> pane list'`. For each remote agent settle a unique `name`,
  its `remote_label` (pane label on the remote), its `local_label` (the local attach-view
  pane), and an optional `resume_cmd` (e.g. `claude --resume <id>`, or just `claude`).
- Optionally configure the watch scope (`watch_targets` / `watch_ignore`; the `monitor`
  pane is auto-excluded) and idle nudging (`idle_nudge`). See `herdr_sync.py schema`.

**Write the config**: `herdr_sync.py init` scaffolds a template; fill it in (or write
`topology.json` directly). Validate with `herdr_sync.py status`.

**Save it as memory** so future sessions don't re-discover: write a concise memory entry
(in this Claude memory system) recording the topology — whether it is local-only or has
remotes, the local agents (`name ↔ label`) and/or each remote host + ssh target + session
and its agent `name ↔ remote_label ↔ local_label` map, project dirs, and the path to
`topology.json` as the machine-readable source of truth. Keep the two in sync: the memory
is for recall, `topology.json` is what the tool reads.

---

## Operations (map the user's intent to a command)

Run `python3 ${CLAUDE_SKILL_DIR}/scripts/herdr_sync.py <cmd>`:

- **"status" / "is it synced?" / "check"** → `status`. This is the source of truth; show
  the table (per remote: server up?, remote vs local agent state, attach up/down, mirror alive).
- **"revive" / "bring the panes/agents back" / "panes are broken" / "fix"** → `revive`,
  then `status` to confirm. `revive` is idempotent: starts remote servers if down,
  ensures a labelled pane per agent and runs `resume_cmd`, (re)builds the local layout only
  if missing, relaunches dead attach views, and ensures the mirror. Re-running is safe.
- **"install" / "set up the self-healing mirror"** → `install`. It always provisions
  **stable copies** of `herdr_sync.py` and `herdr-act.sh` under `~/.config/herdr-mgr/`
  (so the monitor session can allowlist a path that survives plugin updates) and prints the
  allowlist entries. For a remote-bridge it then installs the self-healing mirror daemon
  (macOS launchd / Linux systemd-user / manual fallback). For a **local-only** topology it
  stops there — there is no mirror to run. **"uninstall" / "stop the mirror"** → `uninstall`.
- **"mirror"** → remote-bridge only; it's daemon-managed; do **not** run `mirror` in the
  foreground yourself. Use `status` to confirm it's alive, or `install` if it isn't.

**Local-only note:** `revive`, `mirror`, `install`'s daemon, and the attach views are all
remote-bridge machinery — they are **no-ops** when `remotes` is empty (`revive` will, as a
courtesy, restart any local agent whose pane exists but has no agent, if a `resume_cmd` is set).
Local agents live in their own panes; you watch and act on them directly.

**Always finish a `revive`/`install` by running `status` and reporting the table.**

### If a remote is UNREACHABLE
`status`/`revive` will say so. The remote server itself is down (reboot / maintenance /
network) — the agents can't be revived until it answers ssh. Tell the user, do **not**
retry in a tight loop, and note that re-running `/herdr` once it's back restores
everything (the mirror daemon also resyncs on its own).

---

## Why the wiring exists (the non-native part)

herdr is single-server with **no cross-machine agent federation**, so a remote agent never
appears in your local agents tab by itself. Two pieces bridge that gap:

- **Attach views**: each local pane runs `${CLAUDE_SKILL_DIR}/scripts/attach-herdr-agent.sh
  <remote_pane> <host> <session>` — a clean, auto-reconnecting `herdr agent attach` stream
  of one remote agent (no UI chrome, no keystrokes sent, uses `--takeover` to reclaim a
  stale terminal).
- **Status mirror**: `herdr_sync.py mirror` polls each remote agent's true `agent_status`
  and reports it onto the matching local pane (`pane report-agent`), so the local tab stays
  live. herdr's `report-agent` rejects the derived `done` state, so the mirror maps
  `done → idle`. Run it as the daemon (`install`) so it survives session ends and reboots.

---

## Inter-agent / inter-pane communication

Prefer the **static, locality-aware** wrappers in `herdr_sync.py` (they resolve the pane by
label and work for both local and remote agents) over hand-rolled herdr calls:

- Read an agent's screen: `herdr_sync.py read <agent> [N]`.
- Send literal text / a prompt to an agent: `herdr_sync.py send <agent> "<text>"`.
- Nudge a wedged agent with the configured idle prompt: `herdr_sync.py nudge <agent> ["text"]`.

Raw herdr equivalents (use only when you have a concrete pane id): `herdr agent send
<target> "<text>"`, `herdr pane run <pane_id> "<cmd>"`, `herdr pane read <pane_id>`.

⚠️ **Never** `send-keys`/`pane run` into a *local attach-view* pane while it's attached —
keystrokes pass straight through into the live remote agent. To restart a stuck attach
loop, `pkill -f attach-herdr-agent.sh` from the shell (kill orphaned `ssh … agent attach`
children too), then `pane run` once the pane is back at a shell.

---

## Permission watching & auto-judging

Watched agents frequently sit `blocked` at permission prompts. This feature watches for
that, judges each request against the user's policy, and (when live) sends the approval so
agents don't stall. It works the **same for local and remote agents** — `pending`,
`approve`, `deny`, `dismiss`, `read`, and `nudge` all resolve a local pane directly (no ssh)
or a remote pane over ssh, by label. **Mode and policy live in files, so every session
behaves identically.**

- **Policy**: `~/.config/herdr-mgr/permission-policy.md`. If it doesn't exist, copy the
  bundled template `${CLAUDE_SKILL_DIR}/scripts/permission-policy.template.md` there and
  ask the user to confirm the in-scope project dir(s). **Read the policy before judging.**
  The template ships the host-classifier false positives, an AUTO-DISMISS list, the idle
  nudge config, and the recoverable-vs-hard-delete split.
- **Mode**: `herdr_sync.py mode` → `dryrun` (log only, send nothing — start here) or
  `live` (act). Set with `herdr_sync.py mode live` / `mode dryrun`.

### Don't trip your own permission prompts (autonomy)
The monitor session must stay autonomous. **Never hand-roll dynamic shell** in it — no
`$(herdr pane list | python3 -c …)` to resolve a pane id, no inline `python3 -c` / heredocs.
The host Claude Code classifier flags those ("simple_expansion", "cannot be statically
analyzed") and prompts *you*, so the watcher blocks on its own keystrokes. Instead use only
the **static** subcommands, which hide all dynamic resolution inside the file:
`herdr_sync.py approve|deny|dismiss|read|nudge|send <agent>`, or the bundled
`herdr-act.sh <label> <subcommand>` wrapper. Run `herdr_sync.py install` once to drop stable
copies under `~/.config/herdr-mgr/` and **allowlist those stable paths** (it prints the exact
`Bash(...)` entries) so the monitor never prompts on them.

### Watch scope
`watch` reports only **configured** agents (`local_agents` + remote `agents`), so unrelated
or brand-new panes never leak in, and the `monitor` pane is **always excluded** (it would
otherwise self-detect). Narrow further with `watch_targets` (allowlist) / `watch_ignore`
(denylist) in `topology.json`.

### Start watching
Run `python3 ${CLAUDE_SKILL_DIR}/scripts/herdr_sync.py watch` under the **Monitor tool**
(event-driven; it prints a line only when an agent *newly* blocks, gets *nudged*, or
*stalls*). Each line is your wake-up. Keep this in an **interactive session** — judging and
escalation both need to be able to prompt you, which a subagent can't do.

> Cost (optional, per user): the watch/judge loop runs on whatever model your session uses.
> If you want it cheaper, manually switch the session first (e.g. `/model` to Sonnet at low
> reasoning) — but keep it interactive so escalations can still reach you.

### On each `BLOCKED:` event
1. `herdr_sync.py pending` — read the exact prompt of every blocked agent (local + remote).
2. Judge each against the policy. Watch for benign-but-scary false positives (e.g. the host
   classifier flagging harmless shell-expansion in a read-only command) — approve those.
   Some prompts aren't permission requests at all (e.g. the "How is Claude doing this
   session?" feedback nag) — `dismiss <agent>` (Escape) them; don't escalate.
3. Check `herdr_sync.py mode`:
   - **dryrun** → `herdr_sync.py note "<agent> | WOULD-APPROVE|WOULD-ESCALATE | <reason>"`
     and tell the user. Send NO input.
   - **live** → AUTO-APPROVE: `herdr_sync.py approve <agent>`, verify with `pending`, and
     `note` it silently. ESCALATE: leave the prompt waiting and **notify the user**; do not
     act. Never auto-deny — escalate instead. (`herdr_sync.py deny <agent>` exists only for
     when the user explicitly says to reject one.)

> **Always pick the plain "Yes" (option 1).** `approve` deliberately skips any "Yes, and
> don't ask again" / "Yes to all" option — selecting that would suppress future prompts and
> blind the watcher. Live prompts come in two shapes (`1.Yes / 2.No` and `1.Yes / 2.Yes,
> don't ask again / 3.No`); the plain-Yes rule handles both.

### Idle nudging & on each `STALLED:` event
When `idle_nudge.enabled` is set, an agent that holds a non-terminal (non-`blocked`) state
past `idle_nudge.after_sec` is **prodded** in live mode — the watcher sends it the configured
prompt (default *"is everything going well? if there's a bug, fix it"*), up to `max_nudges`
times, emitting a `NUDGED:` line each time. This un-sticks a wedged-but-not-crashed agent
instead of waiting blindly. If nudges are exhausted (or nudging is off / dryrun), the watcher
falls back to a `STALLED:` line that **re-fires every idle window** until you intervene.
On `STALLED:`, surface it to the user and `herdr_sync.py read <agent>` to see what it's stuck
on; don't auto-act beyond the configured nudges.

### Escalation (optional)
By default, escalate by telling the user in chat. If the user wants out-of-band alerts
(e.g. a chat webhook or an MCP-connected messenger), wire that in as the escalation channel
— it's optional and entirely up to them; this skill doesn't depend on any specific service.

---

## Guardrails

- Discover and act **by label**, never by raw `-N` pane ids — herdr renumbers them when
  panes/tabs close.
- In the monitor session, act **only** through the static subcommands (`herdr_sync.py …` /
  `herdr-act.sh …`); never hand-roll `$(...)` / `python3 -c` to resolve panes — it trips the
  host classifier and breaks autonomy. Allowlist the stable `~/.config/herdr-mgr/` paths that
  `install` prints.
- Never send keystrokes into an attached view pane (see Communication above).
- The plugin's bundled scripts are read-only; **all** state (config, mode, policy, logs,
  daemon files) lives under `~/.config/herdr-mgr/` (or `$HERDR_MGR_HOME`) — never written
  back into the skill directory.
- A full remote server restart restores the saved workspace/tab shape with fresh shells —
  watch for duplicate workspaces and close extras.
- **After updating the plugin, re-run `install`.** It copies `herdr_sync.py` and
  `herdr-act.sh` to stable paths under `~/.config/herdr-mgr/` (used by the mirror daemon and
  by your monitor-session allowlist), but a plugin update ships new script code — re-running
  `install` refreshes those copies so the daemon and the allowlisted commands run the latest.

## Reference
- CLI: https://herdr.dev/docs/cli-reference/ · Persistence & remote:
  https://herdr.dev/docs/persistence-remote/ · Agents (detection + `agent attach`):
  https://herdr.dev/docs/agents/ · Socket API: https://herdr.dev/docs/socket-api/
