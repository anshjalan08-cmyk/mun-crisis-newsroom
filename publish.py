#!/usr/bin/env python3
"""
Build step for the MUN crisis newsroom.

Reads content/articles.json (the master file, which contains chair-only notes)
and writes:
  - data/articles.json   published feed, chairNote stripped, safe to push
  - data/bundle.js       same data as a plain script, so the site also works
                         when you just double-click index.html (no server)
  - CHAIR_NOTES.md       your private crib sheet, never committed

Run this every time you add an article, then push.
    python3 publish.py
"""

import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "content" / "articles.json"
OUT = ROOT / "data" / "articles.json"
BUNDLE = ROOT / "data" / "bundle.js"
OUTLETS = ROOT / "data" / "outlets.json"
TICKER = ROOT / "data" / "ticker.json"
INCIDENTS = ROOT / "data" / "incidents.json"
NOTES = ROOT / "CHAIR_NOTES.md"


def main() -> int:
    if not SRC.exists():
        print(f"error: {SRC} not found", file=sys.stderr)
        return 1

    articles = json.loads(SRC.read_text(encoding="utf-8"))

    seen = set()
    for a in articles:
        for field in ("id", "outlet", "headline", "published", "body"):
            if field not in a:
                print(f"error: article missing '{field}': {a.get('id', '?')}", file=sys.stderr)
                return 1
        if a["id"] in seen:
            print(f"error: duplicate article id '{a['id']}'", file=sys.stderr)
            return 1
        seen.add(a["id"])
        try:
            datetime.fromisoformat(a["published"].replace("Z", "+00:00"))
        except ValueError:
            print(f"error: bad timestamp on '{a['id']}': {a['published']}", file=sys.stderr)
            return 1

    # Claim keys must match across outlets covering one incident, or the compare
    # table silently misaligns and shows false disagreement. Warn loudly.
    groups = {}
    for a in articles:
        if a.get("incident"):
            groups.setdefault(a["incident"], []).append(a)

    for inc, members in groups.items():
        keysets = {a["id"]: set((a.get("claims") or {}).keys()) for a in members if a.get("claims")}
        if len(keysets) > 1:
            union = set().union(*keysets.values())
            for aid, ks in keysets.items():
                missing = union - ks
                if missing:
                    print(
                        f"warning: [{inc}] '{aid}' has no claim for: {', '.join(sorted(missing))}"
                        "  (it will show as 'not mentioned')",
                        file=sys.stderr,
                    )

    articles.sort(key=lambda a: a["published"], reverse=True)

    # Strip everything chair-only. 'claims' is the condensed contradiction map —
    # publishing it would hand delegates the analysis they're supposed to do.
    CHAIR_ONLY = {"chairNote", "claims"}
    published = [{k: v for k, v in a.items() if k not in CHAIR_ONLY} for a in articles]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(published, indent=2, ensure_ascii=False), encoding="utf-8")

    # bundle.js — lets the site render from file:// with no web server
    outlets = json.loads(OUTLETS.read_text(encoding="utf-8")) if OUTLETS.exists() else {}
    ticker = json.loads(TICKER.read_text(encoding="utf-8")) if TICKER.exists() else {"standing": []}
    incidents = json.loads(INCIDENTS.read_text(encoding="utf-8")) if INCIDENTS.exists() else {}
    bundle = {
        "articles": published,
        "outlets": outlets,
        "ticker": ticker,
        "incidents": incidents,
    }
    BUNDLE.write_text(
        "window.__MERIDIAN__ = " + json.dumps(bundle, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    lines = [
        "# Chair notes",
        "",
        "Private. Gitignored. Do not read this out loud.",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    for a in articles:
        lines.append(f"## {a['published']} — [{a['outlet']}] {a['headline']}")
        lines.append("")
        lines.append(a.get("chairNote", "_no note_"))
        lines.append("")
    NOTES.write_text("\n".join(lines), encoding="utf-8")

    print(f"published {len(published)} articles -> data/articles.json + data/bundle.js")
    print(f"chair notes -> CHAIR_NOTES.md (gitignored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
