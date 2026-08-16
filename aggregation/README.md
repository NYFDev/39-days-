# NYF next-generation aggregation layer

The website is a projection. The canonical record store is the source of truth.

## Flow

`source -> ingest -> canonical record -> enrich/verify -> projection -> publication`

Sources may be public web material or private NYF operating data. Every item is normalized into the same record envelope before any publication surface uses it.

## Rules

1. Ingest once. Reuse by record ID everywhere.
2. Preserve provenance: canonical URL or external source ID, source date, retrieval date, and verification state.
3. Visibility is explicit. Only `public` records may enter public projections.
4. Publication is a relationship, not ownership. A record can feed East Corner, the newsletter, RSS, 39 Days, activity, or the main site without duplication.
5. Generated projections never become the canonical source.
6. Private Gmail, Calendar, Drive, CRM, or note records remain excluded unless deliberately promoted to `public`.

## Layout

- `record.schema.json` — canonical record contract.
- `sources/*.json` — normalized records grouped by ingestion batch/source.
- `build.mjs` — deterministic projection builder and duplicate guard.
- `/data/records.json` — generated public record collection.
- `/data/public-index.json` — generated compact discovery index for site surfaces.

## Build

```bash
node aggregation/build.mjs
```

The build fails on duplicate IDs or duplicate canonical URLs. This prevents separate publications from silently creating copies of the same source item.

## Next ingestion adapters

Adapters should emit schema-v2 records only. Planned source adapters are Google Calendar, Google Drive, Gmail, CRM/repository events, and selected public web/RSS sources. Authentication credentials must never be stored in this repository.
