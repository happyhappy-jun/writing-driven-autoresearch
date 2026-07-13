#!/usr/bin/env bash
# Build the Overleaf project in ~/writing without touching the repo.
#
# Prefers a real pdfLaTeX build (matches Overleaf) if TeX Live is installed in
# $HOME; otherwise falls back to Tectonic, which needs a flattened staging copy
# because it resolves \input relative to the main file's directory while the
# project is laid out Overleaf-style (main.tex in icfm2024/, inputs at the root).
set -euo pipefail

ROOT="$HOME/writing"
OUT="$HOME/writing-build"
PDF="$HOME/writing-main.pdf"
TL_BIN="$HOME/texlive/2025/bin/x86_64-linux"

mkdir -p "$OUT"

if [ -x "$TL_BIN/latexmk" ]; then
    echo "==> pdfLaTeX build (TeX Live)"
    export PATH="$TL_BIN:$PATH"
    # Overleaf treats the project root as the TeX root; mirror that.
    export TEXINPUTS=".//:$ROOT//:"
    export BIBINPUTS=".:$ROOT/icfm2024:"
    export BSTINPUTS=".:$ROOT/icfm2024:"
    cd "$ROOT"
    latexmk -pdf -interaction=nonstopmode -halt-on-error \
            -outdir="$OUT" icfm2024/main.tex
    cp "$OUT/main.pdf" "$PDF"
else
    echo "==> Tectonic build (XeTeX fallback; TeX Live not installed yet)"
    STAGE="$OUT/stage"
    rm -rf "$STAGE" && mkdir -p "$STAGE"
    cp -r "$ROOT"/section "$ROOT"/tables "$ROOT"/figures "$STAGE"/
    cp "$ROOT"/icfm2024/* "$STAGE"/
    # \DeclareUnicodeCharacter is a pdfLaTeX/inputenc command, undefined in XeTeX.
    sed -i '1i \\\providecommand{\\DeclareUnicodeCharacter}[2]{}' "$STAGE/main.tex"
    cd "$STAGE"
    "$HOME/.local/bin/tectonic" -X compile main.tex --keep-logs
    cp "$STAGE/main.pdf" "$PDF"
fi

echo "==> wrote $PDF"
