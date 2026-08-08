#!/usr/bin/env python3
"""
Release queued batches to the website.

    python3 release.py 1        release batch 1
    python3 release.py 1 2      release batches 1 and 2
    python3 release.py next     release the next unreleased batch
    python3 release.py --status show the queue without changing anything
    python3 release.py --pull 3 take batch 3 back down

Then run publish.py (or just let autopush.sh do it).
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).parent
ART = ROOT / "content" / "articles.json"
REL = ROOT / "content" / "released.json"


def load():
    arts = json.loads(ART.read_text(encoding="utf-8"))
    rel = set(json.loads(REL.read_text(encoding="utf-8")).get("released", []))
    return arts, rel


def save(rel):
    REL.write_text(json.dumps({"released": sorted(rel)}, indent=2), encoding="utf-8")


def status(arts, rel):
    batches = sorted({a["batch"] for a in arts})
    print()
    for b in batches:
        items = [a for a in arts if a["batch"] == b]
        mark = "LIVE " if b in rel else "  .  "
        print(f"  {mark} batch {b}")
        for a in items:
            print(f"          {a['outlet']:10} {a['headline'][:64]}")
    live = len([a for a in arts if a["batch"] in rel])
    print(f"\n  {live} live / {len(arts)} total\n")


def main():
    args = sys.argv[1:]
    arts, rel = load()

    if not args or args[0] in ("--status", "-s", "status"):
        status(arts, rel)
        return 0

    if args[0] == "--pull":
        for b in args[1:]:
            rel.discard(int(b))
        save(rel)
        print(f"pulled batch(es) {', '.join(args[1:])}")
    elif args[0] == "next":
        remaining = sorted({a["batch"] for a in arts} - rel)
        if not remaining:
            print("nothing left to release")
            return 0
        rel.add(remaining[0])
        save(rel)
        print(f"released batch {remaining[0]}")
    else:
        for b in args:
            rel.add(int(b))
        save(rel)
        print(f"released batch(es) {', '.join(args)}")

    subprocess.run([sys.executable, str(ROOT / "publish.py")], check=False)
    arts, rel = load()
    status(arts, rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
