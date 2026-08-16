#!/usr/bin/env python3
"""Build NYF's canonical repository-backed record layer.

The canonical store is the aggregation spine. Source-specific adapters normalize into
one Record shape; public consumers receive a filtered projection only.
Adapters currently cover the public site index and the latest East Corner signal.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "records.json"
PUBLIC_STORE = ROOT / "data" / "public-records.json"
LATEST = ROOT / "newsletter" / "latest.json"
SEARCH_INDEX = ROOT / "search-index.json"
TZ = ZoneInfo("America/Edmonton")


def stable_id(system: str, locator: str) -> str:
    digest = hashlib.sha256(f"{system}:{locator}".encode()).hexdigest()[:20]
    return f"record:{system}:{digest}"


def iso_now() -> str:
    return dt.datetime.now(TZ).isoformat()


def load_json(path: Path, fallback):
    if not path.exists():
        return deepcopy(fallback)
    return json.loads(path.read_text(encoding="utf-8"))


def load_store():
    data = load_json(STORE, {"schemaVersion": 1, "updatedAt": None, "records": []})
    data.setdefault("schemaVersion", 1)
    data.setdefault("records", [])
    return data


def record_fingerprint(record: dict) -> str:
    semantic = deepcopy(record)
    semantic.pop("ingestedAt", None)
    semantic.pop("fingerprint", None)
    provenance = semantic.get("provenance", {})
    provenance.pop("recordVersion", None)
    return hashlib.sha256(
        json.dumps(semantic, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def canonicalize(record: dict, now: str, previous: dict | None = None) -> dict:
    record = deepcopy(record)
    record.setdefault("ingestedAt", now)
    record.setdefault("publishedAt", None)
    record.setdefault("publication", {"url": None, "surfaces": []})
    record.setdefault("provenance", {"recordVersion": 1, "derivedFrom": [], "verified": False})
    record["provenance"].setdefault("derivedFrom", [])
    record["provenance"].setdefault("verified", False)

    candidate = record_fingerprint(record)
    old_fingerprint = previous.get("fingerprint") if previous else None
    if previous and old_fingerprint == candidate:
        # Idempotent reruns do not manufacture a new ingestion event or version.
        record["ingestedAt"] = previous.get("ingestedAt", record["ingestedAt"])
        record["provenance"]["recordVersion"] = previous.get("provenance", {}).get("recordVersion", 1)
    else:
        prior_version = previous.get("provenance", {}).get("recordVersion", 0) if previous else 0
        record["provenance"]["recordVersion"] = prior_version + 1
    record["fingerprint"] = record_fingerprint(record)
    return record


def lane_from_section(section: str) -> list[str]:
    text = section.lower()
    if "39 days" in text or "living record" in text:
        return ["39-days", "record"]
    if "east corner" in text or "editorial" in text or "newsletter" in text:
        return ["enterprise", "capital", "culture", "record"]
    if "operation" in text or "deployment" in text:
        return ["operations", "record"]
    return ["record"]


def kind_from_url(url: str, section: str) -> str:
    if "dispatch" in url or "signal-" in url or "journal" in section.lower():
        return "article"
    if url.startswith("/39-days/day-"):
        return "activity"
    if url in {"/projects/", "/research/", "/ten-cots/", "/alchemical-ledger/"}:
        return "project"
    return "source"


def public_site_records(now: str) -> list[dict]:
    entries = load_json(SEARCH_INDEX, [])
    out = []
    for item in entries:
        locator = item.get("url")
        if not locator:
            continue
        out.append({
            "id": stable_id("github", f"search-index:{locator}"),
            "kind": kind_from_url(locator, item.get("section", "")),
            "visibility": "public",
            "status": "published",
            "title": item.get("title", "Untitled public page"),
            "summary": item.get("description", ""),
            "whyItMatters": "Public NYF artifact discoverable through the canonical record layer.",
            "occurredAt": now,
            "publishedAt": None,
            "source": {
                "system": "github",
                "type": "public-site-index",
                "locator": f"search-index.json:{locator}",
                "url": f"https://nyfholdings.ca{locator}"
            },
            "taxonomy": {
                "lanes": lane_from_section(item.get("section", "")),
                "topics": item.get("keywords", []),
                "geographies": [],
                "entities": ["NYF Holdings"]
            },
            "publication": {
                "url": locator,
                "surfaces": ["journal"]
            },
            "provenance": {
                "derivedFrom": ["search-index.json"],
                "verified": True
            }
        })
    return out


def east_corner_records(now: str) -> list[dict]:
    if not LATEST.exists():
        return []
    issue = load_json(LATEST, {})
    issue_url = issue.get("url")
    out = []
    for item in issue.get("items", []):
        locator = item.get("sourceUrl") or item.get("headline", "")
        if not locator:
            continue
        published = item.get("sourcePublishedAt")
        occurred = f"{published}T00:00:00+00:00" if published else issue.get("publishedAt") or now
        out.append({
            "id": stable_id("web", locator),
            "kind": "source",
            "visibility": "public",
            "status": "published",
            "title": item.get("headline", "Untitled source"),
            "summary": item.get("summary", ""),
            "whyItMatters": item.get("whyItMatters", ""),
            "occurredAt": occurred,
            "publishedAt": issue.get("publishedAt"),
            "source": {
                "system": "web",
                "type": "publisher-source",
                "locator": locator,
                "url": item.get("sourceUrl")
            },
            "taxonomy": {
                "lanes": [item.get("lane")] if item.get("lane") else ["record"],
                "topics": item.get("topics", []),
                "geographies": item.get("geographies", []),
                "entities": [item.get("source")] if item.get("source") else []
            },
            "publication": {
                "url": issue_url,
                "surfaces": ["newsletter", "east-corner", "rss", "activity"]
            },
            "provenance": {
                "derivedFrom": ["newsletter/latest.json"],
                "verified": bool(item.get("sourceUrl"))
            }
        })
    return out


def merge_records(existing: list[dict], incoming: list[dict], now: str) -> list[dict]:
    by_id = {r["id"]: r for r in existing if r.get("id")}
    for raw in incoming:
        previous = by_id.get(raw["id"])
        # Preserve the first observed time for index-derived records unless their source supplies one.
        if previous and raw["source"].get("type") == "public-site-index":
            raw["occurredAt"] = previous.get("occurredAt", raw["occurredAt"])
        by_id[raw["id"]] = canonicalize(raw, now, previous)
    return sorted(by_id.values(), key=lambda r: r.get("occurredAt", ""), reverse=True)


def public_projection(records: list[dict], updated_at: str) -> dict:
    public = [
        r for r in records
        if r.get("visibility") == "public" and r.get("status") == "published"
    ]
    return {
        "schemaVersion": 1,
        "updatedAt": updated_at,
        "recordCount": len(public),
        "records": public,
    }


def main():
    now = iso_now()
    store = load_store()
    incoming = [*public_site_records(now), *east_corner_records(now)]
    store["records"] = merge_records(store["records"], incoming, now)
    store["updatedAt"] = now

    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    PUBLIC_STORE.write_text(
        json.dumps(public_projection(store["records"], now), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Canonical store contains {len(store['records'])} records; "
        f"public projection contains {public_projection(store['records'], now)['recordCount']}."
    )


if __name__ == "__main__":
    main()
