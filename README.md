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
- `/EAST_CORNER_EDITORIAL.md` — canonical East Corner product, voice, editorial and deadline contract
- `/` — NYF Holdings corporate landing page
- `/east-corner/` — East Corner editorial desk; reads its public feed from canonical records
- `/39-days/` — 39 DAYS public documentary page

A record is ingested once, retains provenance and taxonomy, and can then appear on one or more publication surfaces such as East Corner, Journal, newsletter, RSS, activity or 39 DAYS. Private/internal records must never be placed in the public static data file; future Gmail, Calendar, Drive and CRM ingest should normalize into the same schema in a private store and promote only explicitly public records into the static projection.

## East Corner production rule

East Corner is an authored editorial product, not the output of the aggregation layer. The collector discovers and preserves source material; it does not define the voice or decide that a successful source fetch equals a finished edition. Anyone or any agent producing East Corner must read `EAST_CORNER_EDITORIAL.md` first and preserve its founding frame: look where the centre does not; follow receipts, not proximity to power.

The scheduled collector runs as preflight before the reader-facing deadline. Four a.m. America/Edmonton is the publication deadline, not the time to begin building. The principal edition must contain original editorial framing; the source-linked Morning Wire is supporting infrastructure, not a substitute for authorship.

After reviewed editorial work and normalized source batches are promoted, the production writer regenerates the public projection. The release audit requires the HTML canonicals, search inventory and sitemap to contain exactly the same indexable routes.

The private operational hub is intentionally not part of this public build.

## Deployment

GitHub Pages publishes the repository root from `main`. The `CNAME` file binds the deployment to `nyfholdings.ca`.
