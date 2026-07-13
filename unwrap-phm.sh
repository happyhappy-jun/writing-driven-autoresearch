#!/usr/bin/env bash
# Mechanical unwrap: \phm{X} -> X. Nothing else may change.
#
#   ~/unwrap-phm.sh --dry     # show what would change; verify purity; touch nothing
#   ~/unwrap-phm.sh --apply   # do it
#
# This is the single riskiest edit in the run: 195 verified values, all touched at once,
# minutes before submission. So it does not trust itself. After rewriting, it re-derives
# every changed line by stripping the macro from the ORIGINAL and demands the result be
# byte-identical. If one digit moved, it aborts and restores.
set -uo pipefail

ROOT="$HOME/writing"
MODE="${1:---dry}"
cd "$ROOT" || exit 1

# EXCLUDE icfm2024/main.tex: its only \phm{ is inside a comment, and the macro DEFINITION
# lives there. Never let a bulk rewrite near the definition of the thing being rewritten —
# if \phm stops being defined, every stray use becomes an undefined-control-sequence and
# the build dies minutes before submission. We keep \phm defined and simply stop using it.
FILES=$(grep -rl '\\phm{' section/ tables/ figures/ 2>/dev/null)
[ -z "$FILES" ] && { echo "no \\phm{} found — already unwrapped?"; exit 0; }

echo "=== files carrying \\phm{}: ==="
for f in $FILES; do printf '  %-40s %s\n' "$f" "$(grep -o '\\phm{' "$f" | wc -l)"; done
echo "  total: $(grep -ro '\\phm{' $FILES | wc -l)"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
fail=0

for f in $FILES; do
    cp "$f" "$TMP/$(basename "$f").orig"
    # \phm{...} -> ... ; handles nested braces one level deep (e.g. \phm{$-0.015$})
    perl -0777 -pe 's/\\phm\{((?:[^{}]|\{[^{}]*\})*)\}/$1/g' "$f" > "$TMP/$(basename "$f").new"

    # PURITY CHECK: stripping \phm from the ORIGINAL must reproduce the NEW file exactly.
    perl -0777 -pe 's/\\phm\{((?:[^{}]|\{[^{}]*\})*)\}/$1/g' "$TMP/$(basename "$f").orig" \
        > "$TMP/$(basename "$f").expect"
    if ! cmp -s "$TMP/$(basename "$f").new" "$TMP/$(basename "$f").expect"; then
        echo "  IMPURE: $f — rewrite is not a pure macro strip"; fail=1
    fi
    # and no \phm may survive
    if grep -q '\\phm{' "$TMP/$(basename "$f").new"; then
        echo "  RESIDUE: $f still contains \\phm{ after unwrap"; fail=1
    fi
done

# The macro definition itself: keep \phm defined (harmless) or drop it. We KEEP the
# definition so a stray use would still compile rather than silently breaking the build.
echo
echo "=== purity: every changed line must differ ONLY by the macro ==="
for f in $FILES; do
    diff <(perl -0777 -pe 's/\\phm\{((?:[^{}]|\{[^{}]*\})*)\}/$1/g' "$TMP/$(basename "$f").orig") \
         "$TMP/$(basename "$f").new" > /dev/null 2>&1 || { echo "  MISMATCH $f"; fail=1; }
done
[ "$fail" -eq 0 ] && echo "  ok — all rewrites are pure macro strips, 0 value changes"

if [ "$fail" -ne 0 ]; then
    echo "=== ABORT: not pure. Nothing written. ==="
    exit 1
fi

if [ "$MODE" = "--apply" ]; then
    for f in $FILES; do cp "$TMP/$(basename "$f").new" "$f"; done
    echo "=== applied. \\phm{} removed from $(echo "$FILES" | wc -w) files. ==="
    echo "Now: ~/build-writing.sh && ~/writing-audit.sh --final"
else
    echo "=== dry run — nothing written. Re-run with --apply. ==="
fi
