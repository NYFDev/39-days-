#!/usr/bin/env python3
"""East Corner source collector, editorial packet builder, and public morning wire.

The scheduled collector publishes a source-linked daily wire so East Corner always
has current East Africa / Horn coverage even when a longer synthesis has not yet
been promoted into a numbered Signal issue.
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "newsletter"
QUEUE = Path(os.environ.get("NYF_EDITORIAL_QUEUE", ROOT / "data" / "editorial-queue.json"))
WIRE = NEWS / "morning-wire" / "latest.json"
TZ = ZoneInfo("America/Edmonton")
UA = "NYF-Holdings-East-Corner/3.1 (+https://nyfholdings.ca/newsletter/)"

QUERIES = [
    ("money-markets", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR Eritrea OR Djibouti OR "East Africa" OR "Horn of Africa") AND (finance OR investment OR bank OR bond OR trade OR payments OR remittance))'),
    ("infrastructure-mobility", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR Eritrea OR Djibouti OR "East Africa" OR "Horn of Africa") AND (rail OR port OR logistics OR aviation OR energy OR infrastructure OR transport))'),
    ("computing-technology", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR Eritrea OR Djibouti OR "East Africa" OR "Horn of Africa") AND (AI OR software OR telecom OR internet OR startup OR technology OR computing OR mobile))'),
    ("culture-life", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR Eritrea OR Djibouti OR "East Africa" OR "Horn of Africa" OR "African diaspora") AND (music OR film OR art OR fashion OR design OR food OR architecture OR sport OR nightlife OR creator))'),
    ("institutions-policy", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR Eritrea OR Djibouti OR "East Africa" OR "Horn of Africa") AND (government OR policy OR regulation OR development OR university OR research OR diplomacy))'),
    ("diaspora-people", '((Somali OR Ethiopian OR Eritrean OR Djiboutian OR Kenyan OR Ugandan OR Tanzanian OR Rwandan OR "East African") AND diaspora AND (business OR culture OR technology OR investment OR artist OR founder))'),
]
BLOCKED_DOMAINS = {"facebook.com", "x.com", "twitter.com", "instagram.com", "tiktok.com", "youtube.com"}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def get_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as response:
        if "html" not in response.headers.get("content-type", ""):
            return ""
        return response.read(500_000).decode("utf-8", "ignore")


def description_from_page(url):
    try:
        text = get_html(url)
    except Exception:
        return ""
    patterns = [
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:description["\']',
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()[:900]
    return ""


def domain(url):
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def discover():
    by_url = {}
    for beat, query in QUERIES:
        params = urllib.parse.urlencode({
            "query": query,
            "mode": "ArtList",
            "maxrecords": 30,
            "format": "json",
            "sort": "HybridRel",
            "timespan": "7days",
        })
        try:
            data = get_json("https://api.gdeltproject.org/api/v2/doc/doc?" + params)
        except Exception as exc:
            print(f"GDELT query failed for {beat}: {exc}", file=sys.stderr)
            continue
        for article in data.get("articles", []):
            url = article.get("url", "")
            title = re.sub(r"\s+", " ", article.get("title", "")).strip()
            host = domain(url)
            if not url or not title or not host or host in BLOCKED_DOMAINS:
                continue
            row = by_url.get(url)
            if row:
                if beat not in row["beats"]:
                    row["beats"].append(beat)
                continue
            seen = article.get("seendate", "")[:8]
            published = f"{seen[:4]}-{seen[4:6]}-{seen[6:8]}" if len(seen) == 8 else dt.date.today().isoformat()
            by_url[url] = {
                "source": host,
                "sourcePublishedAt": published,
                "sourceHeadline": title[:220],
                "sourceUrl": url,
                "sourceDescription": description_from_page(url),
                "beats": [beat],
            }
    rows = list(by_url.values())
    rows.sort(key=lambda row: (row["sourcePublishedAt"], len(row["beats"]), bool(row["sourceDescription"])), reverse=True)
    return rows[:30]


def build_packet(now, items):
    return {
        "schemaVersion": 2,
        "generatedAt": now.isoformat(timespec="seconds"),
        "status": "review",
        "publicationPolicy": {"autoPublish": False, "rule": "The numbered Signal remains reviewed synthesis. The public Morning Wire is source-linked discovery, not a synthesized editorial conclusion."},
        "editorialInstructions": ["Do not organize the reader-facing Signal into fixed taxonomy lanes.", "Do not rewrite source headlines and present them as East Corner headlines.", "Find collisions across money, infrastructure, computing, institutions, culture and diaspora life.", "Prefer a small number of developed threads over a quota of category summaries.", "Keep direct source links attached to every factual claim used in synthesis."],
        "sources": items,
    }


def build_wire(now, items):
    full = len(items) >= 6
    return {
        "schemaVersion": 1,
        "product": "East Corner Morning Wire",
        "generatedAt": now.isoformat(timespec="seconds"),
        "date": now.date().isoformat(),
        "timezone": "America/Edmonton",
        "status": "published",
        "collectionStatus": "full" if full else "limited",
        "collectionCount": len(items),
        "editorialState": "source-linked discovery",
        "note": (
            "Automatically collected public reporting. Headlines and descriptions remain attributable to the originating publishers; numbered Signal issues are separately reviewed synthesis."
            if full
            else "Limited source day. The available source-linked reporting is published rather than silently suppressing the Morning Wire; numbered Signal issues still require separate editorial review."
        ),
        "items": items[:12],
    }


def main():
    now = dt.datetime.now(TZ)
    if os.getenv("GITHUB_EVENT_NAME") == "schedule" and now.hour != 3:
        print(f"Skipping duplicate schedule: local time is {now:%H:%M %Z}; publication window is 03:00.")
        return
    items = discover()
    if not items:
        raise SystemExit("Collector found zero usable sources; preserving the previous Morning Wire instead of overwriting it with an empty edition.")
    packet = build_packet(now, items)
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    WIRE.parent.mkdir(parents=True, exist_ok=True)
    WIRE.write_text(json.dumps(build_wire(now, items), indent=2, ensure_ascii=False) + "\n")
    print(f"East Corner Morning Wire published with {min(len(items), 12)} sources; editorial queue refreshed with {len(items)} sources.")


if __name__ == "__main__":
    main()
