# NYF Behavioral Funnel v1

## Objective

Build an editorial intelligence loop without asking subscribers demographic profiling questions. The front end asks for the minimum needed to deliver the requested product. The backend learns from consented first-party behavior tied to content, source and return engagement.

## The pipeline

Research / investigation
→ canonical editorial record
→ East Corner investigation + YouTube episode
→ Shorts / clips / social fragments
→ discovery
→ article or video
→ Evidence File request
→ email capture
→ newsletter relationship
→ return engagement
→ editorial intelligence
→ next investigation

The newsletter is the relationship layer, not the sole origin of content. The canonical editorial record is the source object from which newsletter, East Corner, YouTube and social derivatives are generated.

## What the reader sees

At first conversion, request only email. Do not ask age, gender, income, occupation, location, ethnicity, political identity, or interest-survey questions.

The Evidence File is the lead magnet. Its promise is simple: the source trail, timeline, key numbers, evidence classifications and unresolved questions behind the investigation.

## What the system captures

### Acquisition context

- content_id: canonical investigation identifier
- entry_asset_id: Short, social fragment, video, newsletter link or direct entry
- source: first-party source label or UTM source when supplied
- medium: organic_social, video, email, referral, direct, search
- campaign_id: editorial campaign / investigation
- referrer_host: host only; avoid retaining full external URLs containing user-specific query strings
- landing_path: first NYF path in the session
- first_seen_at

### Engagement context

- page_view
- article_engaged: meaningful dwell threshold, not raw time surveillance
- article_depth: coarse buckets only: 25, 50, 75, 100
- video_outbound
- evidence_cta_view
- evidence_request
- newsletter_signup
- newsletter_click
- return_visit
- next_investigation_click

### Relationship context

- subscriber_id: random internal identifier
- email: stored only in the subscriber system required for delivery
- consent_version
- consented_at
- acquisition_content_id
- acquisition_asset_id
- first_source
- current_status: active, unsubscribed, suppressed

Do not copy email into the behavioral event stream. Join subscriber behavior through the random subscriber_id only where consent and the delivery platform permit it.

## What we deliberately do not capture

No inferred race, ethnicity, gender, sexuality, religion, health status, political affiliation, income, precise location, device fingerprint, cross-site browsing history, or purchased third-party audience profile.

No demographic enrichment vendor in v1.

## Event envelope

Every event uses the same minimal envelope:

```json
{
  "event_id": "uuid",
  "event_name": "evidence_request",
  "occurred_at": "ISO-8601",
  "anonymous_id": "random first-party id",
  "subscriber_id": null,
  "session_id": "random session id",
  "content_id": "ec-2026-001",
  "asset_id": "short-ec-2026-001-a",
  "campaign_id": "ec-2026-001",
  "source": "youtube",
  "medium": "short",
  "landing_path": "/east-corner/example/",
  "properties": {
    "cta": "evidence-file"
  },
  "consent_version": "v1"
}
```

## Editorial intelligence generated from this data

The backend should answer editorial questions, not profile people.

### Acquisition
Which investigation and which derivative asset created qualified visits?

### Conversion
Which investigations caused Evidence File requests or newsletter signups?

### Retention
Which acquisition cohorts returned for a second investigation?

### Depth
Which stories produced meaningful reading, source-file requests and movement into long-form video?

### Cross-surface movement
Do Shorts create YouTube viewers? Do YouTube viewers enter East Corner? Do newsletter readers return to investigations?

### Editorial compounding
Which themes repeatedly produce both acquisition and retention, rather than one-off traffic?

## Core metrics

Do not optimize primarily for pageviews.

- Qualified visit rate
- Evidence CTA conversion
- Subscriber conversion
- Investigation-to-investigation return rate
- Seven-day and thirty-day reader return
- Source-to-long-form conversion
- Long-form-to-Evidence-File conversion
- Subscriber-to-next-investigation conversion
- Asset yield: qualified readers per derivative asset

## Cohorts

Cohorts are behavioral and editorial, never demographic.

Examples:

- acquired_by_investigation
- acquired_by_youtube
- acquired_by_short
- evidence_seekers
- long_form_readers
- returning_readers
- newsletter_returners
- cross_surface_readers

A reader can belong to multiple cohorts. Cohorts describe interaction with NYF, not identity.

## Data model

### investigations
content_id, title, desk, thesis, published_at, status

### assets
asset_id, content_id, platform, format, canonical_url, published_at

### subscribers
subscriber_id, email, status, consent_version, consented_at, acquisition_content_id, acquisition_asset_id

### sessions
session_id, anonymous_id, started_at, source, medium, campaign_id, landing_path

### events
event_id, session_id, anonymous_id, subscriber_id nullable, content_id, asset_id nullable, event_name, occurred_at, properties

### evidence_requests
request_id, subscriber_id, content_id, requested_at, delivered_at

### newsletter_deliveries
message_id, subscriber_id, content_id, delivered_at, opened_at nullable, clicked_at nullable

## Privacy boundary

Collection should be first-party, purpose-limited and disclosed. A consent state gates non-essential behavioral events. Essential subscription records remain limited to delivery, consent, suppression and audit requirements. Unsubscribing must stop marketing delivery; analytics retention rules should be separately documented and enforced.

## Funnel states

DISCOVERED → ENGAGED → EVIDENCE_REQUESTED → SUBSCRIBED → RETURNED → MULTI_INVESTIGATION

These are state transitions based on observable interactions, not lead scores based on personal characteristics.

## Implementation order

First wire the event contract and consent state. Then replace the current mailto newsletter request with a real email-only subscription endpoint. Then add Evidence File requests to East Corner investigations. Then tag every derivative asset with content_id / asset_id campaign parameters. Then build the editorial dashboard from aggregated events.

## Acceptance test

A person should be able to encounter an NYF Short, follow it to a full investigation, request its Evidence File with only an email address, receive the file, return from a newsletter link to a second investigation, and appear in reporting as a returning evidence-seeking reader without NYF ever asking who they are demographically.
