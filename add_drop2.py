import json, pathlib, sys
SRC = pathlib.Path("content/articles.json")
INC = "c2-yangtze"
D = [
{"id":"cbn-1630","outlet":"cbn","incident":INC,
 "headline":"Japanese-owned survey vessel recorded near cable corridor, records show",
 "standfirst":"Vessel equipped for seabed mapping was operating 40 nautical miles from the Matsu corridor on 4 August. Its charter holder is not disclosed in Japanese filings.",
 "byline":"CBN Newsroom","dateline":"","published":"2026-08-05T16:30:00Z","tags":[],
 "body":["A subsea survey vessel owned by a Japanese marine engineering firm was operating approximately 40 nautical miles from the Taiwan-Matsu cable corridor on 4 August, port and positioning records confirm.",
 "The vessel is equipped for seabed mapping and cable route surveying. Its charter for the period was held by a third-party contractor whose ownership is not disclosed in Japanese corporate filings.",
 "Regional observers noted that discussion of the incident has focused exclusively on parties east of the strait, and questioned why the presence of specialist subsea capability belonging to a party with declared strategic interests in the outcome has drawn no attention whatsoever.",
 "All parties are urged to exercise restraint."],
 "chairNote":"JAPAN - CBN. TRUE, MISDIRECTING. Every fact checks out. Drags in Taiwan. If backed: they spent the session on the wrong country. Reveal what moved while they looked away."},
{"id":"signal-1900","outlet":"signal","incident":INC,
 "headline":"BLOOD GRAIN: BRAZIL CHARGED BEIJING FOUR TIMES THE MARKET RATE AS CHINA STARVED",
 "standfirst":"Bras\u00edlia lectured the world on non-intervention. The same week, it charged a starving country a premium that would embarrass a cartel.",
 "byline":"Signal Post Newsdesk","dateline":"","published":"2026-08-05T19:02:00Z","tags":["breaking"],
 "body":["Brazil sold Beijing emergency grain at four times the going rate in a staggering act of war profiteering, cashing in on a catastrophe that has left twelve million people without drinking water.",
 "The 400,000-tonne deal represents the single largest opportunistic markup in the modern grain trade, one commodities analyst said.",
 "Bras\u00edlia has spent this session lecturing the world about non-intervention and peaceful dialogue. It has spent the same week charging a starving country a premium that would embarrass a cartel.",
 "Brazil's agriculture ministry did not respond to a request for comment."],
 "chairNote":"BRAZIL - SIGNAL POST. FALSE. 'Four times the market rate' misreads tws-1410's 'four times monthly average' - volume, not price. A delegate who read China can catch it. If backed: public humiliation, debunked by TWS, Brazil owed an apology."},
{"id":"pacific-2105","outlet":"pacific","incident":INC,
 "headline":"Seoul's foundries absorbed Taiwanese orders within 72 hours of the cable severance",
 "standfirst":"Officials in two allied capitals say contracts of that size do not move in three days without preparatory contact.",
 "byline":"Pacific Herald","dateline":"TOKYO","published":"2026-08-05T21:05:00Z","tags":[],
 "body":["South Korean legacy-node foundry capacity absorbed a substantial share of orders Taiwanese fabs could not fill in the 72 hours following the cable severance, according to order-book data and three people familiar with the reallocation.",
 "The speed of the transfer has drawn attention. Officials in two allied capitals said privately that contracts of that size do not move in three days without preparatory contact, and that the question of what Seoul knew, and when, is now being asked.",
 {"type":"quote","text":"Nobody is alleging South Korea did anything. Everybody is asking why they were ready.","cite":"Official in an allied capital"},
 "South Korea's trade ministry called the suggestion baseless and said reallocation clauses are standard in supply agreements."],
 "chairNote":"SOUTH KOREA - PACIFIC HERALD. FACTS TRUE, CONCLUSION FALSE. Denial is true and buried last. Drags in Taiwan. If backed: TWS clears Seoul two sessions later, everything built on it is void. Deliver coldly."},
]
if not SRC.exists():
    sys.exit("error: content/articles.json not found - are you in the repo root?")
arts = json.loads(SRC.read_text())
have = {a["id"] for a in arts}
bs = [a.get("batch") for a in arts if isinstance(a.get("batch"), int)]
b = max(bs) + 1 if bs else 2
print("existing batches:", sorted(set(bs)) or "none", "-> using batch", b)
n = 0
for a in D:
    if a["id"] in have:
        print("  skip ", a["id"], "(already in master)")
        continue
    arts.append({**a, "batch": b}); n += 1
    print("  add  ", a["id"], "[" + a["outlet"] + "]")
if n:
    SRC.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
    print("\nadded", n, "articles as batch", b, "- QUEUED, nothing live yet.")
    print("to go live:  python3 release.py", b, "&&  ./push.sh")
else:
    print("\nall three already present. run: python3 release.py --status")
