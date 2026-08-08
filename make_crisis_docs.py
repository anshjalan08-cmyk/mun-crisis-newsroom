#!/usr/bin/env python3
"""
Builds one editable HTML file per crisis, for upload to Google Drive as a Doc.

Each file contains every article for that crisis in a labelled, round-trippable
format. You edit the Doc; Claude reads it back and syncs content/articles.json.

    python3 make_crisis_docs.py

Output: chair-tools/crisis_<id>.html  (gitignored, never deployed)

FORMAT RULES — keep these intact when editing, or the read-back breaks:
  * Do not change the "ARTICLE — <id>" line. The id is the key.
  * Keep the FIELD: value lines. Add or remove body paragraphs freely.
  * Body paragraphs are the plain paragraphs under BODY.
  * A pull quote is a paragraph starting with "QUOTE:" and optionally " — cite".
  * CHAIR NOTE and CLAIMS are chair-only. They are never published.
"""

import json
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent
ART = ROOT / "content" / "articles.json"
OUTLETS = ROOT / "data" / "outlets.json"
INCIDENTS = ROOT / "data" / "incidents.json"
OUTDIR = ROOT / "chair-tools"

CSS = (
    "<style>"
    "body{font-family:Georgia,serif;line-height:1.5;color:#111}"
    "h1{font-size:24pt}h2{font-size:15pt;margin-bottom:2pt}"
    ".pg{page-break-before:always}"
    ".warn{background:#fde8e6;border-left:4px solid #b3261e;padding:10pt;margin:10pt 0}"
    ".note{background:#fff6db;border-left:4px solid #c9a227;padding:10pt;margin:12pt 0}"
    ".fld{font-family:Consolas,monospace;font-size:9pt;color:#555;margin:1pt 0}"
    ".lbl{font-family:Arial,sans-serif;font-size:8.5pt;letter-spacing:1pt;color:#999;margin-top:12pt}"
    "table{border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:9pt;margin:8pt 0}"
    "td,th{border:1px solid #ccc;padding:5pt;vertical-align:top;text-align:left}"
    "th{background:#f1efe8}tr.c td,tr.c th{background:#fdf2ee}"
    "</style>"
)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(iid, members, outlets, meta):
    def oname(o):
        return outlets.get(o, {}).get("name", o)

    p = [f"<html><head><meta charset='utf-8'>{CSS}</head><body>"]
    p.append(f"<h1>{esc(meta.get('label', iid))}</h1>")
    p.append(
        f"<p class='fld'>crisis id: {esc(iid)} &nbsp;|&nbsp; {len(members)} articles &nbsp;|&nbsp; "
        f"regenerated {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}</p>"
    )
    if meta.get("summary"):
        p.append(f"<p><i>{esc(meta['summary'])}</i></p>")
    p.append(
        "<div class='warn'><b>Chair document. Do not share with delegates.</b><br>"
        "Edit freely. Keep the <b>ARTICLE — id</b> lines and the <b>FIELD:</b> labels intact "
        "so the sync back to the website works. Tell Claude when you've changed something "
        "and it will pull your edits before publishing.</div>"
    )

    # contested matrix, chair-only
    if len(members) > 1:
        keys = []
        for a in members:
            for k in (a.get("claims") or {}):
                if k not in keys:
                    keys.append(k)
        if keys:
            p.append("<p class='lbl'>CONTESTED FACTS (chair reference)</p>")
            p.append("<table><tr><th></th>" + "".join(
                f"<th>{esc(outlets.get(a['outlet'], {}).get('short', a['outlet']))}</th>" for a in members
            ) + "</tr>")
            for k in keys:
                cells = [(a.get("claims") or {}).get(k) for a in members]
                stated = [c for c in cells if c]
                contested = len({c.lower().strip() for c in stated}) > 1 or len(stated) != len(cells)
                p.append(
                    f"<tr class='{'c' if contested else ''}'><th>{esc(k)}</th>"
                    + "".join(f"<td>{esc(c) if c else '<i>not mentioned</i>'}</td>" for c in cells)
                    + "</tr>"
                )
            p.append("</table>")

    for a in members:
        p.append("<div class='pg'></div>")
        p.append(f"<p class='lbl'>ARTICLE &mdash; {esc(a['id'])}</p>")
        p.append(f"<h2>{esc(a['headline'])}</h2>")
        p.append(f"<p class='fld'>OUTLET: {esc(a['outlet'])} ({esc(oname(a['outlet']))})</p>")
        p.append(f"<p class='fld'>TIME: {esc(a['published'])}</p>")
        p.append(f"<p class='fld'>BYLINE: {esc(a.get('byline', ''))}</p>")
        p.append(f"<p class='fld'>DATELINE: {esc(a.get('dateline', ''))}</p>")
        p.append(f"<p class='fld'>TAGS: {esc(', '.join(a.get('tags', [])))}</p>")
        p.append(f"<p class='fld'>HEADLINE: {esc(a['headline'])}</p>")
        p.append(f"<p class='fld'>STANDFIRST: {esc(a.get('standfirst', ''))}</p>")
        p.append("<p class='lbl'>BODY</p>")
        for b in a.get("body", []):
            if isinstance(b, str):
                p.append(f"<p>{esc(b)}</p>")
            elif b.get("type") == "quote":
                cite = f" &mdash; {esc(b['cite'])}" if b.get("cite") else ""
                p.append(f"<p>QUOTE: {esc(b['text'])}{cite}</p>")
        if a.get("claims"):
            p.append("<p class='lbl'>CLAIMS (chair-only, never published)</p>")
            for k, v in a["claims"].items():
                p.append(f"<p class='fld'>{esc(k)}: {esc(v)}</p>")
        if a.get("chairNote"):
            p.append(f"<div class='note'><b>CHAIR NOTE</b><br>{esc(a['chairNote'])}</div>")

    p.append("</body></html>")
    return "\n".join(p)


def main():
    articles = json.loads(ART.read_text(encoding="utf-8"))
    outlets = json.loads(OUTLETS.read_text(encoding="utf-8"))
    incidents = json.loads(INCIDENTS.read_text(encoding="utf-8")) if INCIDENTS.exists() else {}
    articles.sort(key=lambda a: a["published"])

    groups = {}
    for a in articles:
        groups.setdefault(a.get("incident") or "unfiled", []).append(a)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    for iid, members in groups.items():
        meta = incidents.get(iid, {"label": iid})
        path = OUTDIR / f"crisis_{iid}.html"
        path.write_text(build(iid, members, outlets, meta), encoding="utf-8")
        print(f"{path.name:34} {len(members)} articles  — {meta.get('label', iid)}")


if __name__ == "__main__":
    main()
