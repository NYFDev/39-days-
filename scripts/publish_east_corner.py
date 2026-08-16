#!/usr/bin/env python3
import datetime as dt
import hashlib
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
AGGREGATION_SOURCES = ROOT / "aggregation" / "sources"
SEARCH_INDEX = ROOT / "search-index.json"
TZ = ZoneInfo("America/Edmonton")
BASE = "https://nyfholdings.ca"
UA = "NYF-Holdings-East-Corner/1.0 (+https://nyfholdings.ca/newsletter/)"

QUERIES = [
    ("capital", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania) AND (finance OR investment OR bond OR bank OR market OR trade))'),
    ("enterprise", '((Kenya OR Ethiopia OR Somalia OR Rwanda OR Uganda OR Tanzania) AND (startup OR company OR entrepreneur OR infrastructure OR technology))'),
    ("culture", '((East Africa OR Horn of Africa OR African diaspora) AND (culture OR music OR film OR art OR fashion))'),
    ("record", '((East Africa OR Horn of Africa) AND (government OR development OR public OR policy OR project))'),
]
BLOCKED_DOMAINS = {"facebook.com", "x.com", "twitter.com", "instagram.com", "tiktok.com", "youtube.com"}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def get_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        ctype = r.headers.get("content-type", "")
        if "html" not in ctype:
            return ""
        return r.read(500_000).decode("utf-8", "ignore")


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
    for p in patterns:
        m = re.search(p, text, re.I | re.S)
        if m:
            s = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
            return s[:700]
    return ""


def domain(url):
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def discover():
    seen = set()
    rows = []
    for lane, query in QUERIES:
        params = urllib.parse.urlencode({
            "query": query,
            "mode": "ArtList",
            "maxrecords": 20,
            "format": "json",
            "sort": "HybridRel",
            "timespan": "2days",
        })
        try:
            data = get_json("https://api.gdeltproject.org/api/v2/doc/doc?" + params)
        except Exception as e:
            print(f"GDELT query failed for {lane}: {e}", file=sys.stderr)
            continue
        for a in data.get("articles", []):
            url = a.get("url", "")
            title = re.sub(r"\s+", " ", a.get("title", "")).strip()
            d = domain(url)
            if not url or not title or not d or d in BLOCKED_DOMAINS or url in seen:
                continue
            seen.add(url)
            desc = description_from_page(url)
            when = a.get("seendate", "")[:8]
            pub = f"{when[:4]}-{when[4:6]}-{when[6:8]}" if len(when) == 8 else dt.date.today().isoformat()
            rows.append({
                "lane": lane,
                "source": d,
                "sourcePublishedAt": pub,
                "headline": title[:180],
                "sourceUrl": url,
                "summary": desc or f"Source report: {title}",
                "whyItMatters": why_it_matters(lane),
            })
            if sum(1 for r in rows if r["lane"] == lane) >= 2:
                break
    return rows[:8]


def why_it_matters(lane):
    return {
        "capital": "Track how money, ownership, financing costs and market access are changing across the region.",
        "enterprise": "Track whether new businesses and infrastructure are creating durable operating capacity rather than one-off headlines.",
        "culture": "Track where cultural attention is becoming a platform for durable networks, markets and institutions.",
        "record": "Keep a source-linked public record so promises can later be compared with delivery.",
    }[lane]


def next_signal():
    nums = []
    for p in NEWS.glob("signal-*"):
        m = re.fullmatch(r"signal-(\d+)", p.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def stable_record_id(url):
    digest = hashlib.sha256(f"web:{url}".encode()).hexdigest()[:20]
    return f"record:web:{digest}"


def normalized_source_records(number, now, items):
    issue = f"signal-{number:03d}"
    issue_url = f"{BASE}/newsletter/{issue}/"
    retrieved = now.isoformat(timespec="seconds")
    outputs = [
        {"surface": surface, "slug": issue, "publishedUrl": issue_url, "publishedAt": retrieved}
        for surface in ["newsletter", "east-corner", "feed", "activity"]
    ]
    return [
        {
            "id": stable_record_id(item["sourceUrl"]),
            "schemaVersion": 2,
            "visibility": "public",
            "kind": "article",
            "source": {
                "name": item["source"],
                "type": "web",
                "canonicalUrl": item["sourceUrl"],
                "publishedAt": item["sourcePublishedAt"],
                "retrievedAt": retrieved,
            },
            "title": item["headline"],
            "summary": item["summary"],
            "context": item["whyItMatters"],
            "observedAt": item["sourcePublishedAt"],
            "entities": [item["source"]],
            "geography": item.get("geography", []),
            "lanes": [item["lane"]],
            "topics": item.get("topics", []),
            "projects": ["east-corner"],
            "status": "published",
            "verification": {
                "state": "source-checked",
                "checkedAt": retrieved,
                "notes": "Direct publisher URL retained; automated summary requires source review before reliance.",
            },
            "outputs": outputs,
            "payload": {"whyItMatters": item["whyItMatters"], "issue": issue},
        }
        for item in items
    ]


def write_source_batch(number, now, items):
    AGGREGATION_SOURCES.mkdir(parents=True, exist_ok=True)
    issue = f"signal-{number:03d}"
    path = AGGREGATION_SOURCES / f"newsletter-{issue}.json"
    path.write_text(
        json.dumps(normalized_source_records(number, now, items), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def update_search_index(number, now, items):
    entries = json.loads(SEARCH_INDEX.read_text(encoding="utf-8"))
    issue = f"signal-{number:03d}"
    route = f"/newsletter/{issue}/"
    description = f"{len(items)} source-linked signals across enterprise, capital, culture and the public record."
    record = {
        "url": route,
        "title": f"NYF Signal {number:03d}: East Corner daily signal",
        "section": "Newsletter",
        "description": description,
        "keywords": ["East Corner", "newsletter", "enterprise", "capital", "culture", "source aggregation"],
        "lastModified": now.date().isoformat(),
    }

    entries = [entry for entry in entries if entry.get("url") != route]
    newsletter_position = next(
        (index + 1 for index, entry in enumerate(entries) if entry.get("url") == "/newsletter/"),
        len(entries),
    )
    entries.insert(newsletter_position, record)
    for entry in entries:
        if entry.get("url") == "/newsletter/":
            entry["lastModified"] = now.date().isoformat()
    SEARCH_INDEX.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def esc(s):
    return html.escape(str(s), quote=True)


def render_page(number, now, items):
    issue = f"signal-{number:03d}"
    title = "East Corner: the daily signal"
    lane_order = ["capital", "enterprise", "culture", "record"]
    blocks = []
    for lane in lane_order:
        lane_items = [x for x in items if x["lane"] == lane]
        if not lane_items:
            continue
        cards = []
        for x in lane_items:
            cards.append(f'''<article class="signal-item"><div class="signal-item-meta"><span>{esc(x['source'])}</span><time datetime="{esc(x['sourcePublishedAt'])}">{esc(x['sourcePublishedAt'])}</time></div><div><h3>{esc(x['headline'])}</h3><p>{esc(x['summary'])}</p><p class="signal-why"><strong>Why it matters:</strong> {esc(x['whyItMatters'])}</p><a class="signal-source" href="{esc(x['sourceUrl'])}" target="_blank" rel="noopener noreferrer">Read the source ↗</a></div></article>''')
        blocks.append(f'''<section class="signal-lane" id="{lane}"><div class="signal-lane-head"><h2>{lane.title()}</h2><span>{len(lane_items)} signals</span></div>{''.join(cards)}</section>''')
    published = now.isoformat(timespec="seconds")
    pretty = now.strftime("%d %B %Y · %H:%M %Z")
    return f'''<!doctype html><html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="index, follow"><meta name="description" content="Daily source-linked East Corner signal across enterprise, capital, culture and the public record."><title>{title} — NYF Signal {number:03d}</title><link rel="canonical" href="{BASE}/newsletter/{issue}/"><link rel="alternate" type="application/rss+xml" title="NYF Holdings Dispatch" href="{BASE}/feed.xml"><link rel="stylesheet" href="/assets/nyf-public-20260814.css"><link rel="stylesheet" href="/assets/nyf-editorial-20260814.css"><link rel="stylesheet" href="/assets/nyf-mvp-20260814.css"><script src="/assets/nyf-public-20260814.js" defer></script></head><body class="article-page signal-article"><a class="skip-link" href="#article">Skip to the briefing</a><header class="site-header"><a class="wordmark" href="/"><span>NYF</span><small>Holdings</small></a><nav class="site-nav"><a href="/east-corner/">East Corner</a><a href="/newsletter/" aria-current="page">Newsletter</a><a href="/search/">Search</a></nav></header><main id="article"><header class="article-hero"><div class="article-hero-inner"><div class="article-series"><span>NYF Signal {number:03d} / Automated briefing</span><span>Enterprise · Capital · Culture · Record</span></div><h1>{title}</h1><p class="article-deck">Source-linked signals discovered automatically, with the originating publisher kept as the source of record.</p><div class="article-meta"><span>{pretty}</span><span>{len(items)} sources</span><span>Automated source synthesis</span></div></div></header><div class="article-body"><article class="prose signal-prose"><p class="signal-method"><strong>Reading rule:</strong> summaries are drawn from publisher metadata where available. Open the original source before relying on any item.</p>{''.join(blocks)}<section class="article-next"><span>Aggregation method</span><h2>Fetch broadly. Link directly. Summarize narrowly.</h2><p>East Corner automatically discovers current source material, excludes social-media domains, preserves direct links and publishes a permanent issue.</p><div class="dispatch-links"><a class="button button-light" href="/newsletter/">Return to the Dispatch</a><a class="button button-outline" href="/feed.xml">Follow by RSS</a></div></section></article></div></main></body></html>'''


def update_index(number, now, items):
    path = NEWS / "index.html"
    text = path.read_text()
    issue = f"signal-{number:03d}"
    date = now.strftime("%d %B %Y")
    title = "East Corner: the daily signal"
    counts = {lane: sum(1 for x in items if x["lane"] == lane) for lane in ["capital", "enterprise", "culture", "record"]}
    current = f'''<section class="current-signal" aria-labelledby="current-signal-title"><div class="archive-label"><span>Current issue / Signal {number:03d}</span><time datetime="{now.date().isoformat()}">{date}</time></div><h2 id="current-signal-title">{title}</h2><p>{len(items)} current source-linked signals across East Corner's four editorial lanes.</p><div class="signal-route-map" aria-label="Current issue lanes"><span><b>{counts['capital']:02d}</b>Capital</span><span><b>{counts['enterprise']:02d}</b>Enterprise</span><span><b>{counts['culture']:02d}</b>Culture</span><span><b>{counts['record']:02d}</b>Record</span></div><div class="dispatch-links"><a class="button button-light" href="/newsletter/{issue}/">Read Signal {number:03d}</a><a class="button button-outline" href="/newsletter/latest.json">Open the source data</a></div></section>'''
    text = re.sub(r'<section class="current-signal".*?</section>', current, text, count=1, flags=re.S)
    card = f'''<a class="archive-card" href="/newsletter/{issue}/"><div class="card-meta"><span>NYF Signal / {number:03d}</span><time datetime="{now.date().isoformat()}">{now.strftime('%d %b %Y')}</time></div><h2>{title}</h2><p>{len(items)} automatically discovered, source-linked signals.</p></a>'''
    text = text.replace('<div class="archive-grid" aria-label="Published dispatches">', '<div class="archive-grid" aria-label="Published dispatches">' + card, 1)
    path.write_text(text)


def update_feed(number, now, items):
    path = ROOT / "feed.xml"
    old = path.read_text() if path.exists() else ""
    issue = f"signal-{number:03d}"
    item = f'''<item><title>NYF Signal {number:03d}: East Corner daily signal</title><link>{BASE}/newsletter/{issue}/</link><guid isPermaLink="true">{BASE}/newsletter/{issue}/</guid><pubDate>{now.strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate><description>{len(items)} source-linked signals across capital, enterprise, culture and the public record.</description></item>'''
    if "<channel>" in old:
        new = old.replace("<channel>", "<channel>" + item, 1)
    else:
        new = f'''<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>NYF Holdings Dispatch</title><link>{BASE}/newsletter/</link><description>East Corner source-linked signals</description>{item}</channel></rss>'''
    path.write_text(new)


def main():
    now = dt.datetime.now(TZ)
    # Cron runs at both 14:00 and 15:00 UTC so local DST changes still land at 08:00 Edmonton.
    if os.getenv("GITHUB_EVENT_NAME") == "schedule" and now.hour != 8:
        print(f"Skipping: local time is {now:%H:%M %Z}, not 08:00.")
        return
    items = discover()
    if len(items) < 4:
        raise SystemExit(f"Publisher found only {len(items)} usable sources; refusing to publish a thin issue.")
    number = next_signal()
    issue = f"signal-{number:03d}"
    out = NEWS / issue
    out.mkdir(parents=True, exist_ok=False)
    (out / "index.html").write_text(render_page(number, now, items))
    latest = {
        "schemaVersion": 1,
        "issue": issue,
        "title": "East Corner: the daily signal",
        "url": f"{BASE}/newsletter/{issue}/",
        "publishedAt": now.isoformat(timespec="seconds"),
        "scope": ["enterprise", "capital", "culture", "record"],
        "method": "Automated source discovery with direct publisher links; summaries use publisher metadata where available.",
        "items": items,
    }
    issue_data = json.dumps(latest, indent=2, ensure_ascii=False) + "\n"
    (out / "data.json").write_text(issue_data, encoding="utf-8")
    (NEWS / "latest.json").write_text(issue_data, encoding="utf-8")
    write_source_batch(number, now, items)
    update_search_index(number, now, items)
    update_index(number, now, items)
    update_feed(number, now, items)
    print(f"Published {issue} with {len(items)} items.")

if __name__ == "__main__":
    main()
