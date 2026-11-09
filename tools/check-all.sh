#!/usr/bin/env bash
# The fast checks, before a push (every push to main goes live). About two minutes.
#     tools/check-all.sh
# The other games' browser smoke tests need a running server and aren't included: see each area's doc.
# Kingfall's starts its own server, and is skipped where Playwright isn't installed.
set -u
cd "$(dirname "$0")/.."
fail=0
run() {
  local name="$1"; shift
  local out
  if out=$("$@" 2>&1); then
    echo "ok    $name"
  elif [ $? -eq 77 ]; then   # the check can't run on this machine (no headless browser)
    echo "skip  $name: $(echo "$out" | tail -1)"
  else
    echo "FAIL  $name"
    echo "$out" | tail -20 | sed 's/^/      /'
    fail=1
  fi
}
run "the app imports"                python3 -c "import app.main"
run "cache versions agree"           python3 tools/bump-version.py --check
run "browser JS parses"             tools/check-js.sh
run "Saltbound: every action, mods"  python3 tools/saltbound-check.py
run "Saltbound: 12 bot runs, saves"  python3 tools/saltbound-sim.py 12 normal --saves --fast
run "Board Brawl: bot games"         python3 tools/brawl-check.py
run "Frag Arena: server checks"      python3 tools/arena-check.py
run "Song Guesser: arrangements"     node tools/song-guesser-check.js
run "Kingfall: geometry parity"      node tools/kingfall-parity.mjs
run "Kingfall: bot fights"           python3 tools/kingfall-sim.py --fast
run "Kingfall: a run in a browser"   node tools/kingfall-smoke.js --serve
exit $fail
