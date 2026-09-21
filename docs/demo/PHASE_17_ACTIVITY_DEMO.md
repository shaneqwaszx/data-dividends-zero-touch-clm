# Phase 17 Case Activity demo

This five-minute synthetic walkthrough demonstrates a retained automation-event explorer,
not a production compliance audit.

## Setup

1. Start the supported local backend/frontend lifecycle with default synthetic Mock
   providers and memory persistence.
2. Sign in as `maya-lim` using the runtime-provided development credential.
3. Use the existing New onboarding flow to create one clean Singapore case and one case
   that pauses for document review. Do not use confidential data.

## Walkthrough

1. Open **Case activity**. Point out that the page makes one bounded activity request,
   shows retained automation events across accessible cases, and keeps native case links.
2. Select **document**, then exact `DOCUMENT` stage and `REVIEW_REQUIRED` outcome. Show
   that filters reset to page one and intersect on the server.
3. Set an explicit UTC From/To window. Explain inclusive From, exclusive To, preserved
   microseconds, and source-local sequence ordering.
4. Choose 25 events per page and use Previous/Next when available. Explain that pages are
   live, concurrent changes can move boundaries, no global total is claimed, and Refresh
   returns to page one.
5. Open **Inspect** on an event. The detail expands locally without another request and
   renders the bounded message as text. Follow its case link, then use the case-specific
   activity URL and **Clear case filter**.
6. At 480px width, tab to the filters and activity table; the page remains within the
   viewport while the table scrolls internally.

## Required narration

- Actor attribution is not recorded; no “By” value is invented.
- Priority and client scope are current case metadata, not event-time facts.
- This view covers currently retained zero-touch automation timeline events only. It does
  not include document/admin/auth streams or certify complete audit coverage.
- Case deletion removes its available activity. There is no tombstone/archive here.
- Export CSV is intentionally unavailable.
- Mock target completion is not customer, compliance, legal UBO, production, or
  Ready-for-Approval authorization.
