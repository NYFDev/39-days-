# NYF Holdings public site

Public-facing website for `nyfholdings.ca`.

Live site: [https://nyfholdings.ca/](https://nyfholdings.ca/)

Search discovery: [sitemap.xml](https://nyfholdings.ca/sitemap.xml) · [robots.txt](https://nyfholdings.ca/robots.txt) · [RSS feed](https://nyfholdings.ca/feed.xml)

## Architecture

The public site is a projection over a canonical record layer rather than the primary datastore.

`sources → normalized record → enrichment/review → publication surfaces`

- `/aggregation/record.schema.json` — normalized schema-v2 ingest contract
- `/aggregation/sources/` — source batches retained with provenance
- `/data/record.schema.json` — schema-v2 public projection contract
- `/data/records.json` — deterministic public record projection
- `/assets/nyf-records.js` — client projection from records into site surfaces
- `/` — NYF Holdings corporate landing page
- `/east-corner/` — East Corner editorial desk; reads its public feed from canonical records
- `/39-days/` — 39 DAYS public documentary page

A record is ingested once, retains provenance and taxonomy, and can then appear on one or more publication surfaces such as East Corner, Journal, newsletter, RSS, activity or 39 DAYS. Private/internal records must never be placed in the public static data file; future Gmail, Calendar, Drive and CRM ingest should normalize into the same schema in a private store and promote only explicitly public records into the static projection.

The production publisher has one writer. Every issue creates its permanent page and JSON issue data, a normalized source batch, a search-index route, sitemap entry, RSS item and regenerated public record projection. The release audit requires the HTML canonicals, search inventory and sitemap to contain exactly the same indexable routes.

The private operational hub is intentionally not part of this public build.

## Deployment

GitHub Pages publishes the repository root from `main`. The `CNAME` file binds the deployment to `nyfholdings.ca`.
