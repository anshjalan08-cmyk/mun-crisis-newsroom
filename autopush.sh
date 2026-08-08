#!/bin/bash
# MERIDIAN autopush — run this ONCE before committee starts, then forget about it.
#
#   ./autopush.sh
#
# It watches this folder. Whenever the articles change, it rebuilds the site
# and pushes to GitHub automatically. You do not have to do anything during
# committee. Press Ctrl-C when you're done for the day.
#
# Your git credentials stay on this machine. Nothing is shared with anyone.

set -u
cd "$(dirname "$0")"

INTERVAL="${1:-5}"   # seconds between checks

log() { printf "\033[2m%s\033[0m %s\n" "$(date '+%H:%M:%S')" "$1"; }
ok()  { printf "\033[2m%s\033[0m \033[32m%s\033[0m\n" "$(date '+%H:%M:%S')" "$1"; }
err() { printf "\033[2m%s\033[0m \033[31m%s\033[0m\n" "$(date '+%H:%M:%S')" "$1"; }

# --- preflight ------------------------------------------------------------

if [ ! -d .git ]; then
  err "No git repo here. Run the setup steps in README.md first."
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  err "No 'origin' remote. Run: git remote add origin https://github.com/YOU/REPO.git"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  err "python3 not found. publish.py needs it."
  exit 1
fi

log "Checking push access to $(git remote get-url origin) ..."
if ! git ls-remote origin >/dev/null 2>&1; then
  err "Cannot reach origin. Fix your GitHub auth before committee, not during it."
  exit 1
fi

ok "Connected. Watching for new filings every ${INTERVAL}s."
log "Leave this window open. Ctrl-C to stop."
echo

trap 'echo; log "Stopped. Nothing is watching anymore."; exit 0' INT TERM

# --- watch loop -----------------------------------------------------------

LAST_HASH=""
FAILS=0

while true; do
  # Hash every source file that can change what delegates see. Watching only
  # content/articles.json missed batch releases, which live in released.json.
  HASH=$(cat \
      content/articles.json \
      content/released.json \
      data/outlets.json \
      data/ticker.json \
      data/incidents.json \
      2>/dev/null | shasum 2>/dev/null | cut -d' ' -f1)

  if [ -n "$HASH" ] && [ "$HASH" != "$LAST_HASH" ]; then
    if [ -n "$LAST_HASH" ]; then
      log "Change detected. Building..."
    fi

    if ! BUILD=$(python3 publish.py 2>&1); then
      err "publish.py failed, not pushing:"
      echo "$BUILD" | sed 's/^/    /'
      LAST_HASH="$HASH"
      sleep "$INTERVAL"
      continue
    fi

    COUNT=$(echo "$BUILD" | grep -o '^published [0-9]*' | cut -d' ' -f2)

    if [ -n "$(git status --porcelain)" ]; then
      git add -A >/dev/null 2>&1
      git commit -q -m "wire update $(date '+%Y-%m-%d %H:%M')" >/dev/null 2>&1

      if git push -q 2>/dev/null; then
        ok "Pushed. ${COUNT:-?} filings live. Visible to delegates in ~30-60s."
        FAILS=0
      else
        FAILS=$((FAILS + 1))
        err "Push failed (attempt $FAILS). Will retry on next change."
        if [ "$FAILS" -ge 3 ]; then
          err "Three failures in a row. Check your network or GitHub auth."
        fi
      fi
    fi

    LAST_HASH="$HASH"
  fi

  sleep "$INTERVAL"
done
