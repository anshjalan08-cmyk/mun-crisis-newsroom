#!/usr/bin/env python3
"""
Builds the chair bible from content/articles.json.

Generates chair_bible.html — one article per page, each followed by its chair
note, plus the contested-claims matrix for every multi-source incident.

Upload that file to Google Drive and it converts to a Doc. Regenerate and
re-upload whenever the arc changes, so the doc can never drift from the site.

    python3 make_chair_doc.py
"""

import json
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent
ART = ROOT / "content" / "articles.json"
OUTLETS = ROOT / "data" / "outlets.json"
INCIDENTS = ROOT / "data" / "incidents.json"
OUT = ROOT / "chair-tools" / "chair_bible.html"


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def main():
    articles = json.loads(ART.read_text(encoding="utf-8"))
    outlets = json.loads(OUTLETS.read_text(encoding="utf-8"))
    incidents = json.loads(INCIDENTS.read_text(encoding="utf-8")) if INCIDENTS.exists() else {}
    articles.sort(key=lambda a: a["published"])

    def oname(oid):
        return outlets.get(oid, {}).get("name", oid)

    p = []
    p.append(
        "<html><head><meta charset='utf-8'><style>"
        "body{font-family:Georgia,serif;line-height:1.5;color:#111}"
        "h1{font-size:26pt}h2{font-size:17pt;margin-bottom:2pt}h3{font-size:12pt;color:#444}"
        ".pg{page-break-before:always}"
        ".warn{background:#fde8e6;border-left:4px solid #b3261e;padding:10pt;margin:10pt 0}"
        ".note{background:#fff6db;border-left:4px solid #c9a227;padding:10pt;margin:12pt 0}"
        ".meta{font-family:Arial,sans-serif;font-size:9pt;color:#666;margin-bottom:10pt}"
        "blockquote{border-left:3px solid #b3261e;margin:10pt 0;padding-left:12pt;font-style:italic}"
        "table{border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:9pt;margin:10pt 0}"
        "td,th{border:1px solid #ccc;padding:6pt;vertical-align:top;text-align:left}"
        "th{background:#f1efe8}tr.c td,tr.c th{background:#fdf2ee}"
        "</style></head><body>"
    )

    p.append("<h1>MERIDIAN — Chair Bible</h1>")
    p.append("<p class='meta'>Specialised Emergency Session on the Taiwan Strait<br>"
             f"Generated {datetime.now(timezone.utc).strftime('%d %B %Y, %H:%M UTC')}</p>")
    p.append(
        "<div class='warn'><b>Do not share this document with delegates.</b> "
        "It contains the chair notes, the intended reading of every article, and the "
        "solutions to every clue. The delegate-facing version is the website. "
        "If you need to send delegates something, send them the site link.</div>"
    )

    # index
    p.append("<h2>Running order</h2><ol>")
    for a in articles:
        p.append(f"<li>{esc(a['published'][11:16])} &mdash; [{esc(oname(a['outlet']))}] {esc(a['headline'])}</li>")
    p.append("</ol>")

    # contested matrices
    groups = {}
    for a in articles:
        if a.get("incident"):
            groups.setdefault(a["incident"], []).append(a)

    multi = {k: v for k, v in groups.items() if len(v) > 1}
    if multi:
        p.append("<div class='pg'></div><h2>Contested facts by incident</h2>")
        p.append("<p class='meta'>What each outlet asserts. Highlighted rows are where they conflict "
                 "&mdash; these are your debate hooks.</p>")
        for iid, members in multi.items():
            meta = incidents.get(iid, {})
            p.append(f"<h3>{esc(meta.get('label', iid))}</h3>")
            keys = []
            for a in members:
                for k in (a.get("claims") or {}):
                    if k not in keys:
                        keys.append(k)
            p.append("<table><tr><th></th>" + "".join(
                f"<th>{esc(outlets.get(a['outlet'],{}).get('short',a['outlet']))}</th>" for a in members
            ) + "</tr>")
            for k in keys:
                cells = [(a.get("claims") or {}).get(k) for a in members]
                stated = [c for c in cells if c]
                contested = len({c.lower().strip() for c in stated}) > 1 or len(stated) != len(cells)
                p.append(f"<tr class='{'c' if contested else ''}'><th>{esc(k)}</th>" + "".join(
                    f"<td>{esc(c) if c else '<i>not mentioned</i>'}</td>" for c in cells
                ) + "</tr>")
            p.append("</table>")

    # one article per page
    for a in articles:
        p.append("<div class='pg'></div>")
        p.append(f"<h2>{esc(a['headline'])}</h2>")
        bits = [oname(a["outlet"])]
        if a.get("byline") and a["byline"] != oname(a["outlet"]):
            bits.append(a["byline"])
        if a.get("dateline"):
            bits.append(a["dateline"])
        bits.append(a["published"][11:16] + " UTC")
        bits.append("id: " + a["id"])
        if a.get("incident"):
            bits.append("incident: " + a["incident"])
        p.append("<p class='meta'>" + esc(" · ".join(bits)) + "</p>")
        if a.get("standfirst"):
            p.append(f"<p><i>{esc(a['standfirst'])}</i></p>")
        for b in a.get("body", []):
            if isinstance(b, str):
                p.append(f"<p>{esc(b)}</p>")
            elif b.get("type") == "quote":
                cite = f"<br>&mdash; {esc(b['cite'])}" if b.get("cite") else ""
                p.append(f"<blockquote>{esc(b['text'])}{cite}</blockquote>")
        if a.get("chairNote"):
            p.append(f"<div class='note'><b>CHAIR NOTE</b><br>{esc(a['chairNote'])}</div>")

    p.append("</body></html>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(p), encoding="utf-8")
    print(f"wrote {OUT.name} — {len(articles)} articles, {len(multi)} multi-source incidents")


if __name__ == "__main__":
    main()
