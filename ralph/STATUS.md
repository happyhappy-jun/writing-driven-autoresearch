# STATUS — Depth-AR sprint — ✅ FINAL: e5a3b37 (record: d034a8b at T+2:27; user-directed addendum chain through T+3:47)

## CLOSING ENTRY
**Shipped**: "Depth-AR: Skipping Transformer Layers Without Dropping Their Updates" —
4pp body + refs + appendix, pushed to Overleaf at d034a8b. THESIS (measured, ρ=0.820,
p=9.0e-08, 28 runs): prediction pays off in proportion to what skipping destroys —
negligible at light budgets (below the eval's own measured noise floor), large and
Bonferroni-significant where damage is severe (4 survivors / 63-comparison family, incl.
+89/900 z=4.31 AT THE DEPLOYABLE RULE on 7B), with the depth-only predictor's breakdown
at 43% skipped and the cross-token extension surviving it. Cost: +0.64% prefill (7B).
**Every number**: measured, key-verified against 15+ result JSONs (281/281 pre-unwrap),
generated tables (byte-identical regen), figures byte-identical to their data, 652
integrity checks green. **Cut/declined**: Qwen3 family (shared-venv risk — future work),
32B (download physics), k=12 CT accuracy claim (z=1.26), favsel accuracy claim
(under-powered) — all with logged reasons. **The one allowed repair: never needed.**
**Method**: 11 accumulated rulings in master.md; ~12 worker-catches-master and
master-catches-worker corrections, all upward; every instrument made to fail at least
once before being trusted. DECISIONS.md is the full audit trail.



## Run facts
- **T0**: set (see `~/ralph/T0`); deadline T+3:00. Check: `~/ralph/clock.sh`
- **Phase**: post-Gate-B/C — **STORY LOCKED (Pivot E, two scales): \mname recovers LIKELIHOOD,
  not FUNCTION.** Gate B = FAIL on deployment criterion (k=4 tasks 0/3, self-verified);
  Gate C = GO for 7B on fallback letter. Constructive core intact: per-channel ≫ scalar
  (amplifies with scale) + selection ≫ predictor + P energy-blindness.
- **Hard rules for the paper**: NO downstream-improvement claim anywhere. The former "1.5B
  k=2 +18.5%" is RETRACTED as ratio inflation (= +5 correct/900, piqa exactly tied, denom
  0.030, inside n=300 noise) — canonical sentence: "no reliable downstream improvement at any
  budget or scale; largest measured accuracy delta is +5/900". Fractions on noise-level gaps
  → absolute counts (rule 10). +66% recovery_top quoted ONLY inside the selection table next
  to absolute quality. Title committed: "…Recovering the Likelihood…, Not Their Function".
- **Method (frozen after R4+latency)**: per-channel diagonal AR(1), closed-form, ridge 0.01
  (dev-split), O(d) params/layer, O(Td) compute. Primary selection = residual_damage
  (min damage×(1−recovery)), gap≥2. Scalar AR(1) = ablation; AR(2)/A/D dead.
- **In flight**: R4 7B (job jeqntln, alin14 GPU1, auto-pull armed) → makes Pivot E
  three-scale; latency (residual_damage k=4 set, 3090 BF16) fires when 7B set known;
  Fig 2 = two-panel dissociation figure (NLL vs ACC frontier) ordered.
- **Key numbers (self-verified + audit v2, 2-SE/95% + Bonferroni/16)**: dense — 0.5B
  2.7626/0.5867 · 1.5B 2.3298/0.7133 · 7B 1.9784/0.7944. Deployable NLL recovery: 5–18%
  (0.5B/1.5B), **+23.3% at 7B k=4 (2.3818→2.2881) = strongest anywhere**. Accuracy:
  **2/16 deltas significant, BOTH 1.5B recovery_top (+132/900 z=6.45; +90/900 z=4.37,
  survive Bonferroni z≈2.95); ALL deployable rows n.s. at all scales (7B best +22/900,
  z=1.18)**. Canonical sentence = v4 (see DECISIONS). Latency: +0.23/+0.18% prefill (1.5B;
  7B version auto-firing). Science freezes on 7B-latency landing — ahead of T+2:05.
- Permission mode: **live**; watcher Monitor task `b080g870k` (persistent)
- Master rethink loop: harness cron `f92558fe`, every 10 min, prompt `rethink master.md`
- System cron: `*/10 * * * * ~/ralph/clock.sh --cron` → appends to `CLOCK.md`

## ⚠ ENV v3 (T+0:19) — supersedes plan §6/§8 and the T+0:03 note
- **Two GPU tiers.** Local: 4× TITAN X Pascal 12GB (FP32, discovery — R1 running here).
  Fleet via lobroster gpu skills: 31 FREE; **alin14 = 7 usable RTX 3090 24GB, BF16**
  (GPU0 there permanently STALE — off-limits). No SLURM; fleet queue is the scheduler.
- **Ladder v3: 0.5B local FP32 → 1.5B (alin14 BF16 pref) → 7B HEADLINE (single 3090, BF16)**;
  3B fallback; 1.5B last resort. alin14 prep (env-setup, code-sync, 7B+1.5B downloads)
  ordered T+0:19, parallel to R1 — download is the long pole.
- Rules: never touch OTHER/STALE; no sudo; `$HOME` not shared → results rsync back to
  `~/ralph/results/`; one comparison row = one host + one precision; latency = single 3090.
- Paper: `\topscale` macro (=7B now, one-line pivot at Gate C); captions per-tier.

## Workers
| Agent | Task | Deadline | Last known |
|---|---|---|---|
| experiment | **R1 DONE early** → GATE A marginal-fail (master+worker converged) → variants A/C/D scans (GPU0+1) ∥ R2-lite probe 3 selection rules (GPU2+3) ∥ fig1a/b plot agent ∥ alin14 prep (**status OVERDUE — escalated**) | variant+probe JSONs by T+0:40; A2 verdict T+0:45 (hard T+1:00) | working |
| writing | Full draft pushed 8e68e7c (105 \ph, headline ×5 consistent) → PH-LEDGER.md done (Groups A/C/D) → audit script shipped+ratified → pivot_drafts.md (B vs C/E blocks) + Fig1b caption + bib verify (18 entries, cut-if-unconfirmed) | pivot prep before T+1:00 | working; Group D live fix ordered (16-vs-32 calib seqs) |

## Gate A decision defaults (pre-committed, master.md §5)
- Ambiguous → PASS with top-k predictable layers (Pivot C fallback)
- Clear fail → variants A→C→D, max 3, hard stop T+1:00, then Pivot F
- Partial data on time beats complete data late
- If R1 squeezed by the torch slip: AR(1)-only first pass, 8 held-out seqs, AR(2) second

## Open items (check each sweep; escalate if stale)
- [ ] **r2_compose_0.5b.json** — R2-full LIVE on local GPU0 (k=1/2/4/6, both selections;
  Table 1 uses **residual-damage** rule per ruling). Gate B on landing.
- [ ] **r3_verify_1.5b.json** — R3 LIVE on alin14 GPU1 (fleet job jy53d34, BF16). Must be
  rsync'd back; check mtime + fleet `ps` if silent >20 min.
- [ ] **\phm completeness check** — writing to report count of \phm rows with JSON+key backing
  (any unbacked \phm recategorizes to \ph). Due before Gate B contact.
- [ ] fig1a/fig1b PDFs untracked — commit together with the floats that \input them.
- ✅ notes fix landed (refit + data-faithful, mechanism OPEN). ✅ pivot pushed (944482b, 14a74c8).
- Interrupt precedent (~T+0:34): Escape + superseding-summary works; use when all GPUs idle
  and orders are queued behind a mega-turn. Watcher alarms during long turns = queue artifacts;
  verify via pane + nvidia-smi/fleet before reacting.
- alin14: GPU0 STALE (never touch), GPU4 freed again → 7 usable. jingyu may return.
- **Macro split active**: \ph{}=invented (dies unmeasured, 113) · \phm{}=measured-pending-
  supersession (56; verify-100%-then-unwrap at T+2:40; protocol-truthful prose required).

## Watch notes
- T+0:12 — watcher auto-nudged both agents (#1/3, 10min idle). Benign: both produced minutes
  prior; "idle" here usually = agent waiting on its own background GPU jobs/subagents. Act
  only on STALLED (nudges exhausted).
- Worker self-reported timestamps are unreliable (writing said T+0:22 when clock read T+0:11).
  Gate timing uses `~/ralph/clock.sh` ONLY, never a worker's self-clock.

## Verified-stat registry (master-recomputed, exact match w/ writing; 3rd computation ordered)
- spearman(P_ar1, recovery_ar1) = **−0.0152** (n=22) — predictability ⟂ recoverability
- alpha_ar1 < 0 in L4–16: **13/13** — unanimous middle-layer anti-correlation
- mean(AR2−AR1 recovery) = **+0.0009** — AR(2) buys nothing → appendix-only
- Eval-corpus ruling: R2-final/R3/R4 NLL on **WikiText-2 test**; calib stays wikitext-103;
  R1 stays wikitext-103 (caption must say so). Bib: 18/18 verified real (2 errors fixed).

## Phase log
- T+0:00 — Run started. Clock armed, mode live, watcher up, both workers dispatched.
- T+0:03 — ENV DEVIATION (Pascal 4×12GB, no torch). Ladder revised to 0.5B→1.5B→3B; 7B stretch. R0→~T+0:18, Gate A holds.
- T+0:09 — writing on track: main.tex gutted, ENV ACK'd, build+push imminent. experiment installing torch ∥ downloading models.
