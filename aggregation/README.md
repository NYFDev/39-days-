# NYF canonical aggregation layer

The website is a projection. Normalized source batches and the public route inventory are the inputs; generated files under `/data` are projections, never inputs.

## Flow

`source -> ingest -> canonical record -> enrich/verify -> projection -> publication`

Sources may be public web material or private NYF operating data. Every item is normalized into the same record envelope before any publication surface uses it.

## Rules

1. Ingest once. Reuse by canonical source URL and stable record ID everywhere.
2. Preserve provenance: canonical URL or external source ID, source date, retrieval date, and verification state.
3. Visibility is explicit. Only `public` records may enter public projections.
4. Publication is a relationship, not ownership. A record can feed East Corner, the newsletter, RSS, 39 Days, activity, or the main site without duplication.
5. Generated projections never become the canonical source or a later build input.
6. Private Gmail, Calendar, Drive, CRM, or note records remain excluded unless deliberately promoted to `public`.

## Layout

- `record.schema.json` — normalized ingest contract.
- `sources/*.json` — normalized records grouped by ingestion batch/source.
- `build.mjs` — the only projection builder and owner of `/data/records.json`.
- `/data/records.json` — generated public record collection.
- `/data/public-index.json` — generated compact discovery index for site surfaces.
- `/data/public-records.json` — compatibility copy of the public projection.
- `/search-index.json` — the single canonical inventory of indexable public routes.
- `/scripts/sync_discovery.py` — keeps `sitemap.xml` identical to that route inventory.
- `/scripts/audit_public_site.py` — fails on route, sitemap, schema, count or privacy drift.

## Build

```bash
node aggregation/build.mjs
```

The build fails on duplicate IDs or duplicate canonical URLs. This prevents separate publications from silently creating copies of the same source item.

`scripts/aggregate_records.py` remains only as a compatibility entrypoint; it calls this same builder and does not write a second schema.

## Next ingestion adapters

Adapters should emit schema-v2 records only. Planned source adapters are Google Calendar, Google Drive, Gmail, CRM/repository events, and selected public web/RSS sources. Authentication credentials must never be stored in this repository.
