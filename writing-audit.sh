#!/usr/bin/env bash
# Definition-of-done for ~/writing, as code (writing.md §7).
# Run before every push, and at T+2:47 for the final audit.
#   ~/writing-audit.sh          # audit only
#   ~/writing-audit.sh --final  # also FAIL on any surviving \ph{}
set -uo pipefail

ROOT="$HOME/writing"
PDF="$HOME/writing-main.pdf"
LOG="$HOME/writing-build/main.log"
FINAL=0; [ "${1:-}" = "--final" ] && FINAL=1
fails=0

red()  { printf '\033[31mFAIL\033[0m %s\n' "$1"; fails=$((fails+1)); }
grn()  { printf '\033[32m ok \033[0m %s\n' "$1"; }
warn() { printf '\033[33mwarn\033[0m %s\n' "$1"; }

cd "$ROOT" || exit 1
echo "=== writing audit ==="

# 1. Build is green, no undefined citations/references.
if [ -f "$LOG" ]; then
    u=$(grep -ciE 'undefined (citation|reference)' "$LOG" || true)
    [ "$u" -eq 0 ] && grn "0 undefined citations/references" \
                   || red "$u undefined citation/reference warnings"
else
    red "no build log — run ~/build-writing.sh"
fi

# 2. No STAND / N-gram / speculative-decoding leftovers. These are false claims
#    about a project we are not running: same severity as a fabricated number.
# Word boundaries: the method name is STAND, not "stands"/"standard"/"understand".
# A substring match here fires on ordinary English and trains you to ignore the check.
STANDPAT='\b(stand|n-gram|ngram|speculative|drafting|gumbel)\b'
if grep -rniE "$STANDPAT" section/ tables/ figures/ 2>/dev/null | grep -q .; then
    red "STAND/N-gram leftovers:"
    grep -rniE "$STANDPAT" section/ tables/ figures/ 2>/dev/null | sed 's/^/       /'
else
    grn "no STAND/N-gram/speculative-decoding leftovers"
fi

# 3. Citation hygiene.
c=$(grep -ro '\\cite{' section/ tables/ 2>/dev/null | wc -l)
[ "$c" -eq 0 ] && grn "no bare \\cite{} (all \\citep/\\citet)" || red "$c bare \\cite{}"

# 4. Cross-reference hygiene.
if grep -rqE '(Figure|Table|Section)~\\ref' section/ tables/ 2>/dev/null; then
    red "hand-typed Figure~\\ref / Table~\\ref — use \\Cref"
else
    grn "all cross-refs use \\Cref"
fi

# 5. Method name is always the macro.
if grep -rn 'Depth-AR' section/ tables/ 2>/dev/null | grep -v 'mname' | grep -vE '^\s*%' | grep -q .; then
    warn "literal 'Depth-AR' in prose (should be \\mname):"
    grep -rn 'Depth-AR' section/ tables/ | grep -v 'mname' | sed 's/^/       /'
else
    grn "\\mname used everywhere (no literal method name)"
fi

# 6. Overclaims banned by plan §1.
if grep -rniE 'state[- ]of[- ]the[- ]art|SOTA|lossless|first (activation|linear|ever)|outperforms all' \
     section/ tables/ figures/ 2>/dev/null | grep -q .; then
    red "forbidden claim (SOTA / lossless / first-ever):"
    grep -rniE 'state[- ]of[- ]the[- ]art|SOTA|lossless|first (activation|linear|ever)|outperforms all' \
        section/ tables/ figures/ | sed 's/^/       /'
else
    grn "no SOTA/lossless/first-ever claims"
fi

# 6b. FALSE HARDWARE CLAIM. We never had an A100. Any surviving mention is fiction.
#     Real tiers: TITAN X (Pascal) for 0.5B/1.5B, RTX 3090 for the headline model.
#     A *negated* FlashAttention mention ("neither ... nor FlashAttention") is correct
#     text, not a claim — only an affirmative use-claim is a bug.
hwhits=$(grep -rniE 'a100|v100|h100' section/ tables/ figures/ 2>/dev/null)
# LaTeX hard-wraps prose, so a negation ("Neither configuration uses FlashAttention")
# routinely lands on the line ABOVE the keyword. A line-based grep therefore reports a
# false positive — and an audit that cries wolf is an audit that gets ignored at T+2:47.
# Flatten each file to one line before deciding.
fahits=""
for f in $(grep -rliE 'flash-?attention' section/ tables/ figures/ 2>/dev/null); do
    flat=$(tr '\n' ' ' < "$f" | tr -s ' ')
    # every FlashAttention mention must sit within a negating clause
    n_all=$(printf '%s' "$flat" | grep -oiE 'flash-?attention' | wc -l)
    n_neg=$(printf '%s' "$flat" | grep -oiE '(neither|nor|no|not|without)[^.]{0,60}flash-?attention' | wc -l)
    [ "$n_all" -gt "$n_neg" ] && fahits="$fahits$f: affirmative FlashAttention claim ($n_all mentions, $n_neg negated)"$'\n'
done
if [ -n "$hwhits$fahits" ]; then
    red "false hardware claim (A100/V100/H100, or an affirmative FlashAttention claim):"
    printf '%s\n' "$hwhits" "$fahits" | grep -v '^$' | sed 's/^/       /'
else
    grn "no false hardware claims (no A100/V100/H100; FlashAttention only ever negated)"
fi
k=$(grep -ric 'to our knowledge' section/ 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
[ "$k" -le 1 ] && grn "'to our knowledge' used $k time(s) (max 1)" \
               || red "'to our knowledge' used $k times — plan §1 allows exactly one"

# 7. Anonymity + no visible filler.
if command -v pdftotext >/dev/null && [ -f "$PDF" ]; then
    if [ "$(pdftotext "$PDF" - 2>/dev/null | grep -ciE 'amazon|kaist|woomin|bodapati|github\.com')" -gt 0 ]; then
        red "de-anonymizing string in PDF"
    else
        grn "PDF is anonymous"
    fi
    if [ "$(pdftotext "$PDF" - 2>/dev/null | grep -ciE 'placeholder|lipsum|lorem|TODO|AUTHORERR')" -gt 0 ]; then
        red "visible filler/placeholder/AUTHORERR in PDF:"
        pdftotext "$PDF" - 2>/dev/null | grep -ioE 'placeholder|lipsum|lorem|TODO|AUTHORERR' \
            | sort -u | sed 's/^/       /'
    else
        grn "no visible filler or AUTHORERR in PDF"
    fi

    # ---- 4-PAGE LIMIT ----
    # FOURTH attempt. The first three all passed while the body overflowed:
    #   v1 "References start on p5"          -> body spilled most of a column onto p5.
    #   v2 "nothing on p5 before References" -> two-column extraction emits the LEFT column
    #                                           first, so right-column body text is invisible.
    #   v3 "Conclusion HEADING on p<=4"      -> the heading fit on p4 while the conclusion's
    #                                           last sentences spilled onto p5.
    # The requirement is about the LAST WORDS OF THE BODY, so check exactly that: take the
    # final sentence of conclusion.tex and assert it renders on page <= 4.
    # last 6 words of the conclusion, stripped of LaTeX. Must render on p<=4.
    # Strip LaTeX, then drop any trailing (\Cref{...}) parenthetical -- it renders as
    # "(Appendix D)" and will never match the source text. Take the last 6 real words before it.
    tail=$(sed -e 's/%.*//' -e 's/([^)]*Cref[^)]*)//g' -e 's/\\Cref{[^}]*}//g' \
               -e 's/\\[a-zA-Z]*//g' -e 's/[{}$\\]//g' section/conclusion.tex \
           | tr '\n' ' ' | tr -s ' ' | sed 's/[[:space:]]*$//' | sed 's/[.,]*$//' \
           | awk '{for(i=NF-5;i<=NF;i++) printf "%s%s", $i, (i<NF?" ":"")}')
    if [ -z "$tail" ]; then
        red "could not extract the conclusion's final words — cannot verify the 4-page limit"
    else
        lastp=""
        for p in $(seq 1 "$(pdfinfo "$PDF" 2>/dev/null | awk '/^Pages:/{print $2}')"); do
            if pdftotext -f "$p" -l "$p" "$PDF" - 2>/dev/null | tr '\n' ' ' | tr -s ' ' \
                 | grep -qF "$tail"; then lastp=$p; fi
        done
        if [ -z "$lastp" ]; then
            warn "could not locate the conclusion's last words in the PDF (text: '$tail')"
        elif [ "$lastp" -le 4 ]; then
            grn "body ENDS on p$lastp: the conclusion's final words render on page $lastp (<= 4)"
        else
            red "BODY OVERFLOWS: the conclusion's final words render on page $lastp, not p<=4."
            echo "       The heading may fit on p4 while the text spills. Compress further."
        fi
    fi
fi

# 8. No secrets, ever.
grep -rq 'olp_' . --exclude-dir=.git 2>/dev/null && red "TOKEN IN REPO" || grn "no tokens in repo"

# 9. Provisional values. \ph{} and \phm{} mean different things and get different rules.
#      \ph{}  = invented, no measurement  -> land it or DELETE THE SENTENCE
#      \phm{} = measured, pending a same-protocol supersession -> UNWRAP, it is real
ph=$(grep -roE '\\ph\{'  section/ tables/ figures/ 2>/dev/null | wc -l)
phm=$(grep -roE '\\phm\{' section/ tables/ figures/ 2>/dev/null | wc -l)
if [ "$FINAL" -eq 1 ]; then
    if [ "$ph" -eq 0 ]; then
        grn "0 surviving \\ph{} — no unevidenced numbers"
    else
        red "$ph \\ph{} still wrapped — each is a claim with NO EVIDENCE BEHIND IT."
        echo "       Land the real number, or DELETE THE SENTENCE (writing.md §2)."
        echo "       Do NOT ship a \\ph{} value as if it were measured."
        grep -rnoE '\\ph\{[^}]*\}' section/ tables/ figures/ 2>/dev/null | head -12 | sed 's/^/       /'
    fi
    if [ "$phm" -gt 0 ]; then
        warn "$phm \\phm{} still wrapped — these ARE measured and have a result file."
        echo "       UNWRAP them (drop the macro, keep the value). Do not delete: deleting"
        echo "       a \\phm{} throws away a true, evidence-backed claim."
    else
        grn "0 surviving \\phm{}"
    fi
else
    grn "$ph \\ph{} unevidenced + $phm \\phm{} measured (see ~/ralph/PH-LEDGER.md)"
fi

# 9b. Every \phm{} must actually match the JSON it claims to come from.
if [ -x "$HOME/verify-phm.py" ]; then
    if out=$("$HOME/verify-phm.py" 2>&1); then
        grn "$(printf '%s' "$out" | tail -1 | sed 's/^ *//')"
    else
        red "\\phm{} verification failed against result JSONs:"
        printf '%s\n' "$out" | sed 's/^/       /'
    fi
fi

# 10. Pushed.
[ -z "$(git status --porcelain)" ] && grn "working tree clean" || warn "uncommitted changes"
[ -z "$(git log origin/main..HEAD --oneline 2>/dev/null)" ] && grn "pushed to origin" || warn "unpushed commits"

echo "=== $([ $fails -eq 0 ] && echo 'PASS' || echo "$fails FAILURE(S)") ==="
exit $fails
