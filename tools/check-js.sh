#!/usr/bin/env bash
# Syntax-checks every browser JavaScript file under app/static. `node --check file.js` passes broken
# ES-module code here (it isn't parsed as a module), so each file is checked as a .mjs copy.
set -u
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fail=0
while IFS= read -r f; do
  cp "$f" "$tmp/check.mjs"
  if ! out=$(node --check "$tmp/check.mjs" 2>&1); then
    echo "$f"; echo "$out" | sed -n '1,4p' | sed "s|$tmp/check.mjs|$f|"
    fail=1
  fi
done < <(find app/static -name '*.js' -not -path '*/vendor/*' -not -name '*.min.js')
exit $fail
