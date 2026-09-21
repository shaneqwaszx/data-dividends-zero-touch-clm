# Phase 18 Case Portfolio demo

This five-minute synthetic walkthrough demonstrates bounded current-case exploration,
not a workflow queue, risk engine, SLA monitor, approval surface, or production search.

## Setup

1. Start the supported local backend/frontend lifecycle with default synthetic Mock
   providers and memory persistence.
2. Sign in using a synthetic case-capable account. Create enough non-confidential cases
   to show two pages, or use the guarded test application whose test-only fixture seeds
   105 Team Alpha cases through the canonical orchestration owner.
3. Open **Cases**. Keep browser developer tools on the Network panel if request evidence
   is part of the demonstration.

## Walkthrough

1. Show `Showing 1–50 on page 1` and explain that no total is calculated. The first
   page is one bounded portfolio request and does not issue a detail request per row.
2. Search for a registration ID, a case UUID fragment, and a legal-name fragment. Type
   a regex-shaped value such as `.*[$where]`; it remains literal. Point out the exact
   300 ms debounce and that old rows are hidden under the new search label.
3. Compose Status, Priority, Priority order, Open business exception type,
   Jurisdiction, and—when signed in as a Director—Team. Each change resets to page one;
   the backend intersects every selected dimension.
4. Use **Next** and **Previous**. Explain that this is a live offset view: concurrent
   updates may move rows, and no frozen traversal or global total is claimed.
5. Open a case and return. As an authorized relationship manager, change priority and
   show the refreshed row. Delete a synthetic case, confirm it does not reappear from a
   late cached response, and show that an active short page refills.
6. At 480px width, tab to filters, paging buttons, row actions, and the focusable Cases
   table. The table scrolls internally without widening the viewport.

## Required narration

- Authorization and team scope are backend-owned; UI visibility is not authority.
- AU/MY/HK labels are portfolio observations only and do not activate registry routes.
- Prioritised rows precede unset rows; recency and UUID provide deterministic ties.
- Mongo performs one bounded read-only aggregation per page. Bounded output does not
  prove constant scan cost or a production performance SLA.
- The old array endpoint remains for compatibility; the Cases UI uses the new page route.
- Providers remain Mock/Local/Partial/Dormant exactly as recorded in project state.
- Mock target completion is not customer, compliance, legal UBO, production, or
  Ready-for-Approval authorization.
