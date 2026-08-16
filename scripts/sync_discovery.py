#!/usr/bin/env python3
"""Keep Google's sitemap aligned with the site's canonical search inventory."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://nyfholdings.ca/"
SEARCH_INDEX = ROOT / "search-index.json"
SITEMAP = ROOT / "sitemap.xml"


def existing_metadata(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for block in re.findall(r"<url>(.*?)</url>", text, flags=re.S):
        values = {}
        for field in ["loc", "lastmod", "changefreq", "priority"]:
            match = re.search(rf"<{field}>([^<]+)</{field}>", block)
            if match:
                values[field] = match.group(1).strip()
        if values.get("loc"):
            out[values["loc"]] = values
    return out


def defaults(route: str) -> tuple[str, str]:
    if route == "/":
        return "weekly", "1.0"
    if route in {"/projects/", "/east-corner/"}:
        return "weekly", "0.9"
    if route in {"/blog/", "/39-days/"}:
        return "daily", "0.9"
    if route == "/newsletter/":
        return "daily", "0.8"
    if route in {"/east-corner/archive/", "/39-days/archive/"}:
        return "weekly", "0.8"
    if route == "/build-log/":
        return "daily", "0.8"
    if route == "/search/":
        return "weekly", "0.6"
    if route in {"/research/"}:
        return "weekly", "0.7"
    if "/signal-" in route or "/dispatch-" in route or "/day-" in route:
        return "monthly", "0.8"
    return "monthly", "0.7"


def main() -> None:
    entries = json.loads(SEARCH_INDEX.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise SystemExit("search-index.json must contain an array")

    old = existing_metadata(SITEMAP.read_text(encoding="utf-8"))
    seen: set[str] = set()
    rows: list[str] = []
    for entry in entries:
        route = entry.get("url")
        if not isinstance(route, str) or not route.startswith("/") or "?" in route or "#" in route:
            raise SystemExit(f"invalid canonical route in search-index.json: {route!r}")
        if route in seen:
            raise SystemExit(f"duplicate canonical route in search-index.json: {route}")
        seen.add(route)

        loc = urljoin(BASE, route.lstrip("/"))
        prior = old.get(loc, {})
        changefreq, priority = defaults(route)
        lastmod = entry.get("lastModified") or prior.get("lastmod") or "2026-08-14"
        changefreq = prior.get("changefreq", changefreq)
        priority = prior.get("priority", priority)
        rows.append(
            "  <url>"
            f"<loc>{escape(loc)}</loc>"
            f"<lastmod>{escape(lastmod)}</lastmod>"
            f"<changefreq>{escape(changefreq)}</changefreq>"
            f"<priority>{escape(priority)}</priority>"
            "</url>"
        )

    output = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )
    if SITEMAP.read_text(encoding="utf-8") != output:
        SITEMAP.write_text(output, encoding="utf-8")
    print(f"Discovery inventory: {len(entries)} canonical URLs synchronized.")


if __name__ == "__main__":
    main()
