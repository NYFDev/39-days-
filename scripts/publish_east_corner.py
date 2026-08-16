#!/usr/bin/env python3
"""East Corner source collector and editorial packet builder.

The collector does not publish a newsletter. It gathers a broad source packet for
editorial synthesis. Taxonomy is retrieval metadata, never the reader-facing
structure. A reviewed synthesis must be promoted separately before it is public.
"""
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "newsletter"
QUEUE = ROOT / "data" / "editorial-queue.json"
TZ = ZoneInfo("America/Edmonton")
UA = "NYF-Holdings-East-Corner/2.0 (+https://nyfholdings.ca/newsletter/)"

# Broad beats are discovery inputs, not newsletter sections. A source may carry
# several beats and the final issue should be organized around an editorial thesis.
QUERIES = [
    ("money-markets", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR "East Africa" OR "Horn of Africa") AND (finance OR investment OR bank OR bond OR trade OR payments OR remittance))'),
    ("infrastructure-mobility", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR "East Africa" OR "Horn of Africa") AND (rail OR port OR logistics OR aviation OR energy OR infrastructure OR transport))'),
    ("computing-technology", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR "East Africa" OR "Horn of Africa") AND (AI OR software OR telecom OR internet OR startup OR technology OR computing OR mobile))'),
    ("culture-life", '(("East Africa" OR "Horn of Africa" OR "African diaspora") AND (music OR film OR art OR fashion OR design OR food OR architecture OR sport OR nightlife OR creator))'),
    ("institutions-policy", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania OR "East Africa" OR "Horn of Africa") AND (government OR policy OR regulation OR development OR university OR research OR diplomacy))'),
    ("diaspora-people", '((Somali OR Ethiopian OR Eritrean OR Kenyan OR Ugandan OR Tanzanian OR Rwandan OR "East African") AND diaspora AND (business OR culture OR technology OR investment OR artist OR founder))'),
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
    """Build a diverse raw packet. Do not force equal counts per category."""
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
    # Keep enough breadth for collisions to emerge without dumping a firehose on review.
    rows = list(by_url.values())
    rows.sort(key=lambda row: (row["sourcePublishedAt"], len(row["beats"])), reverse=True)
    return rows[:30]


def build_packet(now, items):
    return {
        "schemaVersion": 2,
        "generatedAt": now.isoformat(timespec="seconds"),
        "status": "review",
        "publicationPolicy": {
            "autoPublish": False,
            "rule": "Sources are evidence, not the newsletter. Publish only after a reviewed synthesis identifies a thesis and connects multiple records.",
        },
        "editorialInstructions": [
            "Do not organize the reader-facing issue into fixed taxonomy lanes.",
            "Do not rewrite source headlines and present them as East Corner headlines.",
            "Find collisions across money, infrastructure, computing, institutions, culture and diaspora life.",
            "Prefer a small number of developed threads over a quota of category summaries.",
            "Keep direct source links attached to every factual claim used in synthesis.",
            "Allow culture and technology to lead when the reporting supports it; neither is filler.",
        ],
        "sources": items,
    }


def main():
    now = dt.datetime.now(TZ)
    items = discover()
    if len(items) < 6:
        raise SystemExit(f"Collector found only {len(items)} usable sources; refusing to create a thin editorial packet.")
    packet = build_packet(now, items)
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    print(f"Editorial queue refreshed with {len(items)} sources. Nothing was auto-published.")


if __name__ == "__main__":
    main()
