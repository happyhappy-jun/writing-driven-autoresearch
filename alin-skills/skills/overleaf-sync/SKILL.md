---
name: overleaf-sync
description: >
  Sync an Overleaf project via git — pull the latest state, apply generated artifacts (LaTeX
  tables, figures, prose, bib entries) into the .tex sources, commit, and push back to Overleaf.
  When writing prose, matches the tone of the existing manuscript and a cached personal "voice
  profile" learned from the user's past Overleaf projects (personal voice only — venue formatting
  always follows the current paper). Always pulls first (rebase) because the user may have edited
  on the Overleaf web UI in parallel; never force-pushes. Triggered by requests like "push to
  overleaf", "apply results to the paper", "update the draft", "overleaf에 반영해줘", "논문에 push해줘",
  "내 문체로 써서 반영해줘", "내가 평소 쓰던 톤으로 써줘". Requires the Overleaf git URL and a git auth token
  on first use; building the personal voice profile additionally requires the user to supply the
  git URLs of past Overleaf projects (one-time).
license: MIT
metadata:
  category: research
---

# Overleaf Sync

## What this skill does

Automates the **pull → edit → commit → push** loop for an Overleaf project that has been git-linked, and — when writing prose — makes the new text **read like the rest of the paper and like the user's own writing**. Typical flow:

1. The user runs an experiment and generates tables / figures / LaTeX / prose.
2. This skill **pulls from Overleaf** to pick up any edits the user made on the web UI.
3. It writes the generated artifacts into the right `.tex` files (insert or replace at section/subsection granularity; copy figure binaries into the figures directory; add `.bib` entries). **Generated prose is tone-matched** to the existing manuscript and to the user's cached personal voice profile.
4. `git commit`
5. `git push` back to Overleaf — the user sees the changes immediately on reload.

The **tone matching** has two layers, applied in this precedence:

1. **Current document (wins on format & local consistency).** The existing human-written prose in the target section/file defines terminology, notation, citation style, hedging level, and venue formatting. New prose must blend in seamlessly — especially in a section a co-author already started.
2. **Personal voice profile (fills the gaps).** A cached description of *how the user writes*, learned once from their past Overleaf projects, guides greenfield prose where the current document doesn't already constrain it. **Voice only** — sentence rhythm, person, hedging, favored phrasings, terminology preferences. **Never venue formatting**: column layout, section naming, `\citep` vs `\cite`, theorem environments, etc. always come from the current paper.

## When to use

- "overleaf에 적용해줘" / "논문에 반영해줘" / "push to overleaf"
- "이 결과 draft에 넣어줘" / "apply this table to the paper"
- "내 문체로 써서 반영해줘" / "평소 내 톤으로 결과 해석 써줘"
- "overleaf pull만 해줘" (partial — pull only)
- "내 과거 논문들로 문체 프로필 만들어줘" (build/refresh the voice profile only)
- After producing experiment outputs and asking the assistant to integrate them into the manuscript.

## When not to use

- No Overleaf git remote is configured and the user cannot provide the URL/token — instead, point them at **Overleaf → Menu → Sync → Git** and **Account Settings → Git integration**.
- The user only wants to edit `.tex` locally without syncing to Overleaf — use plain Edit.
- The user wants a deep critical review of the writing — that's `paper-reviewer`, not this skill.

## Required inputs (the user MUST supply)

### For syncing (always)

On first use (or when `.overleaf-sync.json` is missing), the user must provide **both** of:

1. **Overleaf git URL** — format `https://git.overleaf.com/<project-id>`
   - Found at: Overleaf project → **Menu → Sync → Git**
2. **Git authentication token** — a token string issued by Overleaf
   - Created at: **Account Settings → Git integration → Create token**

If `.overleaf-sync.json` already stores the URL, the URL can be skipped — but the **token is never stored by this skill**, so it must be re-supplied each session (or persisted by the user's own git credential helper).

### For building the voice profile (one-time, optional)

To learn the user's personal voice, the user must supply the **git URLs of past Overleaf projects** to learn from (plus a token, same as above — the same token works across that user's projects). This is requested only when the profile is missing/stale and the user wants voice matching. Cloning external repos and deriving a profile is **gated behind explicit user confirmation** (see Workflow step 0).

The token must **never** be written to disk, committed, or echoed into logs. Use it only for the git operations in the current invocation. Persisting it to the OS git credential helper is allowed only with the user's explicit confirmation.

## Prerequisites

- A local clone of the Overleaf project. The skill looks for one and, if not found, clones into `<project-root>/overleaf/`.
- Network access to `git.overleaf.com`.
- An up-to-date `git` on the PATH.
- For voice extraction: `python3` on the PATH (the bundled `extract_prose.py` helper is stdlib-only).

---

## The personal voice profile

A single, **global** profile describing how this user writes prose, reused across all their papers:

- **Location:** `~/.claude/overleaf-style/voice-profile.md` (a user-writable location — **not** the skill's own directory, which is a read-only plugin cache).
- **Built once** from the user's past Overleaf projects (Workflow step 0), refreshable on request.
- **Contains voice only**, recorded along a fixed checklist so it's reproducible:
  - **Person & voice** — "we" vs passive vs impersonal; how the contribution is stated.
  - **Hedging level** — assertive vs cautious; frequency of "may / might / suggests / tend to".
  - **Sentence rhythm** — typical length; short-and-punchy vs long-and-compound.
  - **Connectives & transitions** — "Moreover / Furthermore / However / In contrast" habits.
  - **Terminology preferences** — e.g. "method" vs "approach" vs "framework"; "fine-tune" vs "finetune"; "dataset" vs "data set".
  - **Math-in-prose** — how equations are introduced and referred to.
  - **Paragraph structure** — topic-sentence-first vs build-up.
  - **Signature phrasings / tics** — recurring openers and framings.
- **Explicitly excludes venue formatting.** Do not record column format, `\documentclass`, citation command choice, theorem environments, section naming, or anything that changes per conference. Those are read from the *current* paper at write time.

If the profile file is absent, the skill still works using **current-document** tone matching alone; it just offers to build the profile.

---

## Workflow

### 0. Build / refresh the voice profile (optional, one-time)

Run this when the user asks for voice matching and `~/.claude/overleaf-style/voice-profile.md` is missing or stale, **or** when the user explicitly asks to (re)build it.

1. **Confirm before cloning.** Cloning external repositories and deriving a stored profile is an explicit, user-gated action. Ask:
   > "To learn your writing voice I'll clone these past Overleaf projects, extract their prose, and save a voice profile to `~/.claude/overleaf-style/voice-profile.md`. The clones and your token are discarded afterward; only the voice description is kept. Proceed? Paste the past-project git URLs."

   Do not proceed without a clear yes and at least one URL.
2. **Clone each past project** into a throwaway temp dir (e.g. `mktemp -d`), shallow (`git clone --depth 1`). Never under the skill's own directory.
3. **Extract prose** from each clone's `.tex` files with the bundled helper:
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/extract_prose.py" <clone-dir> >> "$corpus"
   ```
   The helper strips comments, math, and table/figure environments, leaving readable prose.
4. **Analyze** the combined corpus against the fixed voice checklist above. Capture only transferable voice — **discard venue-specific formatting signals**.
5. **Write** `~/.claude/overleaf-style/voice-profile.md` (create the dir if needed). Include a short dated header noting which projects it was derived from (titles/ids only — no tokens, no URLs with secrets).
6. **Clean up**: delete the temp clones and the corpus file. Never persist tokens.

> This step is independent of any particular paper — it can be invoked on its own ("build my voice profile") without an active sync.

### 1. Locate the local Overleaf clone

Check in this order:

1. `<project-root>/.overleaf-sync.json` — read its `path` field.
2. `<project-root>/overleaf/.git/config` containing a `git.overleaf.com` remote → use `overleaf/`.
3. `<project-root>/paper/.git/config` or `<project-root>/manuscript/.git/config` — same check.
4. Otherwise, AskUserQuestion:
   - "Is there already a clone? (path)" — use that path, or
   - "Paste the Overleaf git URL" — clone into `<project-root>/overleaf/`.

After resolving, persist the settings to `<project-root>/.overleaf-sync.json` as `{"path": "overleaf", "url": "https://git.overleaf.com/..."}` so future invocations are silent. Offer to append the clone path to `.gitignore` if it isn't already ignored.

### 2. Pull — always, before editing

From the Overleaf clone path:

```bash
git status --porcelain   # surface any uncommitted local changes
git fetch
git pull --rebase
```

- If there are uncommitted changes from a prior run, show them and ask whether to proceed.
- If `pull --rebase` conflicts, **do not auto-resolve**. Show the conflict state and resolve with the user.

### 3. Inspect the manuscript layout

On first run (or when uncertain), scan the clone:

- Main `.tex` (look for `main.tex`, `paper.tex`, or a file containing `\documentclass`).
- Section files referenced by `\input{}` / `\include{}` (commonly `sections/`, `tex/`).
- Figure directory (`figures/`, `figs/`, `img/`, `images/` — use whichever exists).
- `.bib` bibliography file(s).
- **Note the venue/format signals here** (the `\documentclass`, style files, citation commands) — these define formatting for *this* paper and override any habits from the voice profile.

Use this to decide which file and which section to modify.

### 4. Apply edits (with tone matching)

Execute the original user request (insert a table, add a figure, write prose, add a citation) against the Overleaf sources:

- **Tables**: If an `exp-summary`-style `.tex` table exists, splice its content in. If a `\label{}` matches an existing table, replace; otherwise insert.
- **Figures**: Copy generated `.pdf` / `.png` into the figures directory and add an `\includegraphics{...}` block with caption and label.
- **Prose / interpretation** — this is where tone matching applies:
  1. **Read the surrounding prose first.** Before writing into a section, read the existing human-written text in that file/section. Mirror its terminology, notation, citation command, hedging, and formatting. If a co-author already wrote part of the section, blend in so the seam is invisible.
  2. **Apply the personal voice profile** (`~/.claude/overleaf-style/voice-profile.md`) for anything the surrounding text doesn't already pin down — sentence rhythm, person, favored phrasings. If the profile is missing, offer to build it (step 0) but proceed with current-document matching meanwhile.
  3. **Precedence on conflict:** the current document wins on **format, notation, terminology, and citation style**; the voice profile only shapes **voice** in genuinely new prose. Never import a past paper's formatting into this one.
  4. Prefer replacing a placeholder (`% TODO: results here`) over overwriting existing prose. Ask via AskUserQuestion if the insertion point is ambiguous.
- **Bib entries**: Append to the `.bib` file only if the key is not already present (grep `@.*{key,`).

If the edit plan touches **>3 files or >100 lines**, summarize the plan and confirm with the user before editing. For substantial new prose, show the drafted text (and note which voice cues it followed) before committing.

### 5. Commit

```bash
git add -A
git status
git commit -m "<summary>"
```

Message rules:
- 1-line summary ≤ ~50 chars (e.g., `Add Table 3: CIFAR-10 ablation results`).
- Optional body bullets for touched sections/files.
- **Do not add `Co-Authored-By` or any Claude signature.** Overleaf history stays under the user's name.

### 6. Push — only with user go-ahead

Push is externally visible, so default to confirming with the user. If the user's original request explicitly included push ("overleaf push해줘", "sync and push"), proceed without re-asking.

```bash
git push
```

On failure:
- `non-fast-forward` → `git pull --rebase` again, then retry push.
- Auth failure → tell the user to (re)generate a token at **Overleaf Account Settings → Git integration**, and pass it to the skill.
- Report the failure and leave the local commit in place; do not reset or force.

### 7. Report back

In one message, tell the user:
- Pull result (how many remote commits, brief summary of the user's web edits if any).
- What this run changed (files and sections touched).
- For prose: a note on which tone cues were followed (current-section match and/or voice profile).
- Commit hash and subject.
- Push status, plus a clickable `https://www.overleaf.com/project/<project-id>` link when the project id is known.

---

## Done when

- The Overleaf remote is up to date (push succeeded).
- The local working tree is clean.
- Any new prose matches the surrounding section and the personal voice profile (where applicable).
- The user has a summary of what was pulled, changed, and pushed.

## Notes

- **Always pull first.** The entire reason this skill exists is the "user edited on web in parallel" case — honor it every run.
- **Voice ≠ format.** The voice profile is transferable across venues; formatting is not. When in doubt about a formatting choice, copy the current paper, never a past one.
- **Profile storage.** `~/.claude/overleaf-style/voice-profile.md` is global and user-writable. Never write profile data (or any persistent state) into the skill's own directory — as a plugin it ships in a read-only cache. `${CLAUDE_SKILL_DIR}` is for *reading* the bundled helper only.
- **Privacy.** Building the profile clones the user's own past projects with their consent, extracts only a voice description, and discards the clones and token afterward. Past-project URLs and tokens are never stored; the profile records project titles/ids at most.
- Overleaf git is main-branch-only and does not accept force pushes. Any situation that looks like it needs `--force` must be escalated to the user.
- Figure binaries (`.pdf`, `.png`) go through regular git (no LFS). Warn on files >50MB.
- `.overleaf-sync.json` stores only non-secret data (path, URL). Never put tokens there.
- UTF-8 throughout. If the sources use Korean, assume `kotex`/`xelatex` is already configured and leave it alone.
- This skill is the **sync pipeline** plus prose tone-matching. The table/figure generation itself is upstream work (often by `exp-summary` or plain Edit); this skill ferries those artifacts into the Overleaf repo safely and makes new prose sound like the user.
