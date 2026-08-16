#!/usr/bin/env python3
"""Normalize NYF source outputs into the canonical repository-backed record layer."""
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "records.json"
LATEST = ROOT / "newsletter" / "latest.json"
TZ = ZoneInfo("America/Edmonton")


def stable_id(system, locator):
    digest = hashlib.sha256(f"{system}:{locator}".encode()).hexdigest()[:20]
    return f"record:{system}:{digest}"


def load_store():
    if not STORE.exists():
        return {"schemaVersion": 1, "updatedAt": None, "records": []}
    data = json.loads(STORE.read_text())
    data.setdefault("schemaVersion", 1)
    data.setdefault("records", [])
    return data


def east_corner_records(now):
    if not LATEST.exists():
        return []
    issue = json.loads(LATEST.read_text())
    issue_url = issue.get("url")
    out = []
    for item in issue.get("items", []):
        locator = item.get("sourceUrl") or item.get("headline", "")
        published = item.get("sourcePublishedAt")
        occurred = f"{published}T00:00:00+00:00" if published else now.isoformat()
        out.append({
            "id": stable_id("web", locator),
            "kind": "source",
            "visibility": "public",
            "status": "published",
            "title": item.get("headline", "Untitled source"),
            "summary": item.get("summary", ""),
            "whyItMatters": item.get("whyItMatters", ""),
            "occurredAt": occurred,
            "ingestedAt": now.isoformat(),
            "publishedAt": issue.get("publishedAt"),
            "source": {
                "system": "web",
                "type": "publisher-source",
                "locator": locator,
                "url": item.get("sourceUrl")
            },
            "taxonomy": {
                "lanes": [item.get("lane")] if item.get("lane") else [],
                "topics": [],
                "geographies": [],
                "entities": [item.get("source")] if item.get("source") else []
            },
            "publication": {
                "url": issue_url,
                "surfaces": ["newsletter", "east-corner", "rss"]
            },
            "provenance": {
                "recordVersion": 1,
                "derivedFrom": ["newsletter/latest.json"],
                "verified": False
            }
        })
    return out


def main():
    now = dt.datetime.now(TZ)
    store = load_store()
    by_id = {r["id"]: r for r in store["records"] if r.get("id")}
    for record in east_corner_records(now):
        old = by_id.get(record["id"])
        if old:
            version = old.get("provenance", {}).get("recordVersion", 1) + 1
            record["provenance"]["recordVersion"] = version
        by_id[record["id"]] = record
    store["records"] = sorted(by_id.values(), key=lambda r: r.get("occurredAt", ""), reverse=True)
    store["updatedAt"] = now.isoformat()
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n")
    print(f"Canonical store contains {len(store['records'])} records.")


if __name__ == "__main__":
    main()
