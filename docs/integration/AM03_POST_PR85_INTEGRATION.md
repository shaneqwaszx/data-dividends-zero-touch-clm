# AM-03 post-PR85 integration

Owner-assigned integration, 15 October 2026 (Asia/Singapore).
Base: merged PR85 `75bdf7be0b8ab76abb37e4ae71a1db025db243ce`,
tree `7fdcde8df761b6a099a4da45cb12575f9a3ad0c6`.
Original local AM-03: `362bc60d9f5c1e73b9f8d6e4abcadd6a8c2cc0b6`.
Normal clean cherry-pick: `51d6655974b76357000922760e1a58f55cbe1481`,
tree `e957ca847fdbd19492d544e21a7d9ab6735f74f6`. No conflict.

The original [implementation document](AM03_SEARCH_STAGE_UX.md) and
[historical gate](../../.ai-pipeline/reports/AM03_SEARCH_STAGE_QUALITY_GATE.md)
retain their original pre-PR85 evidence and authorization context. Their local PASS
does not certify this integrated content. Current acceptance requires the separately
assigned post-PR85 independent gate and fresh mandatory browser evidence.

## Behavior and ownership

CaseDetail separates Search interventions/diagnostics from Registry evidence. Search
stays after Registry visually; backend ordering is unchanged. One identity editor
follows current projected ownership. Search navigation can reveal a Registry-owned
correction without adding an editor or changing the backend-selected endpoint.

Backend authority, expected automation/CLM/event versions, case/actor/session focus
guards, evidence currentness, explicit rationale/confirmation, freeze, and the target
ledger remain with existing owners. Navigation, disclosure and refresh do not write.
A failed Search does not prove absence; missing evidence remains unavailable; completed
Search does not create a new confirmation or edit requirement. PR85 date, timestamp,
draft/bulk review and ownership behavior remain intact.

Change class: FRONTEND_UI. Shared API/types, durable schema, connectors, configuration,
business rules, mapping, authentication/authorization semantics, architecture owners,
provider classifications and backend runtime are unchanged. Frontend presentation and
focus behavior change. Canonical browser assertion coverage changes; runner, fixtures,
selector titles, deadlines, retries and discovery policy are unchanged.

## Durable browser coverage

Existing guarded real-authenticated offline journeys are extended:

| Canonical path | Added evidence |
|---|---|
| authenticated-zero-touch.e2e.ts | Absent Search wording, Registry-owned initial identity, one editor, keyboard Search link, desktop/mobile containment and no navigation mutation |
| onboarding-recovery.e2e.ts | Actual wrong-UEN Registry correction; Search pipeline cross-stage focus; one editor; same-team denied authority; creator new-session restoration; current upload retained |
| s3-sandbox-submission.e2e.ts | Candidate identity/rationale exclusively in Search; explicit confirmation; attention/pipeline keyboard focus; desktop/mobile; reload versions/ledger unchanged; completed/frozen controls absent |
| slice-c-recovery.e2e.ts | Actual failed Search warning/diagnostic placement; Search navigation reaches the sole Registry editor; exact existing correction path and no navigation write |

Existing evidence-isolation, state/attention, Registry, PR85, actor/case/session and
no-replay regressions remain required. Each browser lifecycle uses the canonical network
guard, fresh synthetic data and owned processes/ports. Offline XPI fixture assertions
prove zero external calls; no actual GoldTier Sandbox or ACRA Live access is used.

Initial/final discovery is compared by title and fixture identity, independently of
shifted line selectors. Every discovered selector must execute in the disjoint canonical
shard pair at the unchanged 60-second lifecycle deadline and configured Playwright limits.
Database-backed existing selectors require only a newly owned disposable cached Mongo
fixture; no application persistence change or new physical backend suite is inferred.

## Explicitly authorized inherited banner correction

The owner separately authorized a markup-only repair of both offline recovery banners
in App.tsx. Unwrapped fixture text bypassed the existing constrained label styling,
producing a 1381px page at a 1280px viewport. Both variants now reuse
environment-banner__label. The full original wording remains in the status region's
accessible text; no CSS, provider disclosure, business rule or authorization changes.

The existing DemoPerformance banner tests verify the label/status/full disclosure.
Existing normal Mock, normal offline-XPI, failed-Search recovery and document-refresh
browser journeys check 1440, 1280, 900 and 360px, unchanged strict overflow limits, full
ARIA disclosure and usable navigation. Initial failing browser/unit evidence is retained
in the master register. This uses the single authorized corrective budget; another
unrelated defect requires a separate owner decision.

## Acceptance boundary

This document describes the integrated candidate, not a self-issued PASS. Fresh evidence
and the exact frozen source/test/documentation manifest are recorded in the ignored
single master integration register and versioned independent gate. Historical counts
are ATTRIBUTED. Failed probes stay failed; NOT_EXECUTED lanes stay unexecuted.

Publication requires fresh exact independent PASS, unchanged reviewed content, latest-main
reconciliation, clean committed canonical pre-PR and the owner's explicit conditional
authorization. One new AM-03 PR is authorized only after those gates. Hosted billing refusal
is NOT_EXECUTED, never passing CI; the owner alone decides and performs the merge.

AM-18, progressive disclosure and optional enrichment remain separately assigned future
work. Their research reports are not application patches or implementation acceptance.
