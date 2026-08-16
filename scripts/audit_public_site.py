#!/usr/bin/env python3
"""Fail the release when canonical routes, discovery files, or public data drift."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://nyfholdings.ca"


def fail(message: str) -> None:
    raise SystemExit(f"PUBLIC AUDIT FAILED: {message}")


def route_for(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if relative == "index.html":
        return "/"
    return f"/{relative.removesuffix('index.html')}"


def is_noindex(text: str) -> bool:
    for tag in re.findall(r"<meta\b[^>]*>", text, flags=re.I):
        if re.search(r"name=[\"']robots[\"']", tag, flags=re.I) and re.search(r"noindex", tag, flags=re.I):
            return True
    return False


def canonical(text: str) -> str | None:
    patterns = [
        r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
        r'<link\b[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return match.group(1)
    return None


def json_payload(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        fail(f"{path.relative_to(ROOT)} must contain an object")
    records = payload.get("records")
    if payload.get("schemaVersion") != 2 or not isinstance(records, list):
        fail(f"{path.relative_to(ROOT)} is not a schema-v2 record collection")
    count = payload.get("count")
    if count != len(records):
        fail(f"{path.relative_to(ROOT)} says count={count}, actual={len(records)}")
    return payload


def main() -> None:
    indexable_routes: set[str] = set()
    for page in sorted(ROOT.rglob("index.html")):
        if ".git" in page.parts:
            continue
        text = page.read_text(encoding="utf-8")
        route = route_for(page)
        if is_noindex(text):
            continue
        page_canonical = canonical(text)
        expected = f"{BASE}{route}"
        if page_canonical != expected:
            fail(f"{route} canonical is {page_canonical!r}; expected {expected!r}")
        if route in indexable_routes:
            fail(f"duplicate indexable route: {route}")
        indexable_routes.add(route)

    search_entries = json.loads((ROOT / "search-index.json").read_text(encoding="utf-8"))
    search_routes = [entry.get("url") for entry in search_entries]
    if len(search_routes) != len(set(search_routes)):
        fail("search-index.json contains duplicate routes")
    if set(search_routes) != indexable_routes:
        fail(
            "search inventory drift: "
            f"missing={sorted(indexable_routes - set(search_routes))}, "
            f"extra={sorted(set(search_routes) - indexable_routes)}"
        )

    sitemap_text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    sitemap_urls = re.findall(r"<loc>([^<]+)</loc>", sitemap_text)
    sitemap_routes = {url.removeprefix(BASE) or "/" for url in sitemap_urls}
    if len(sitemap_urls) != len(sitemap_routes):
        fail("sitemap.xml contains duplicate URLs")
    if sitemap_routes != indexable_routes:
        fail(
            "sitemap drift: "
            f"missing={sorted(indexable_routes - sitemap_routes)}, "
            f"extra={sorted(sitemap_routes - indexable_routes)}"
        )

    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if "Sitemap: https://nyfholdings.ca/sitemap.xml" not in robots or "Disallow: /" in robots:
        fail("robots.txt does not expose the canonical sitemap")

    canonical_data = json_payload(ROOT / "data" / "records.json")
    compatibility_data = json_payload(ROOT / "data" / "public-records.json")
    compact_data = json_payload(ROOT / "data" / "public-index.json")
    records = canonical_data["records"]
    ids = [record.get("id") for record in records]
    if len(ids) != len(set(ids)):
        fail("data/records.json contains duplicate record IDs")
    urls = [record.get("source", {}).get("canonicalUrl") for record in records]
    urls = [url for url in urls if url]
    if len(urls) != len(set(urls)):
        fail("data/records.json contains duplicate canonical source URLs")
    for record in records:
        if record.get("schemaVersion") != 2:
            fail(f"record {record.get('id')} is not schemaVersion 2")
        if record.get("visibility") != "public" or record.get("status") != "published":
            fail(f"non-public record {record.get('id')} entered the static public projection")
    if {record.get("id") for record in compatibility_data["records"]} != set(ids):
        fail("data/public-records.json does not match the canonical projection")
    if {record.get("id") for record in compact_data["records"]} != set(ids):
        fail("data/public-index.json does not match the canonical projection")

    latest = json.loads((ROOT / "newsletter" / "latest.json").read_text(encoding="utf-8"))
    issue = latest.get("issue")
    if not issue:
        fail("newsletter/latest.json has no issue identifier")
    issue_route = f"/newsletter/{issue}/"
    if issue_route not in indexable_routes:
        fail(f"latest newsletter route {issue_route} is absent from discovery inventory")
    if not (ROOT / "aggregation" / "sources" / f"newsletter-{issue}.json").exists():
        fail(f"latest newsletter {issue} has no normalized aggregation source batch")

    print(
        f"Public audit passed: {len(indexable_routes)} canonical routes, "
        f"{len(records)} deduplicated public records, one discovery inventory."
    )


if __name__ == "__main__":
    main()
