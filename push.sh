#!/bin/bash
# Build + push in one go. Run from this folder: ./push.sh
set -e
cd "$(dirname "$0")"
python3 publish.py
git add .
git commit -m "wire update $(date '+%H:%M')" || { echo "nothing new to push"; exit 0; }
git push
echo "live in ~30s"
