#!/usr/bin/env bash
set -euo pipefail

font_dir="$(cd "$(dirname "$0")/.." && pwd)/eval/datasets/.font-cache"
mkdir -p "$font_dir"
curl -L --fail --silent --show-error \
  'https://raw.githubusercontent.com/google/fonts/51303ca9e8ac9dcea7b12d307ba568fd0e6fcfca/ofl/notosansdevanagari/NotoSansDevanagari%5Bwdth,wght%5D.ttf' \
  -o "$font_dir/NotoSansDevanagari.ttf"
echo "Downloaded OFL Noto Sans Devanagari to $font_dir/NotoSansDevanagari.ttf"
