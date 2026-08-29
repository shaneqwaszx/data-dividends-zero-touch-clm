# Phase 00 Architecture

> **Current implementation note (Phase 11):** this file preserves the Phase 00
> baseline. The implemented pipeline now includes the source-aware jurisdiction gateway,
> Singapore-only registry router, ACRA adapter, canonical entity, IDP, ownership/UBO,
> source-neutral reconciliation/human resume, CLM readiness, and Mock GoldTier
> orchestration described in
> [PHASE_11_RECONCILIATION_REVIEW_RESUME.md](PHASE_11_RECONCILIATION_REVIEW_RESUME.md) and
> [FINAL_POC_ARCHITECTURE.md](FINAL_POC_ARCHITECTURE.md). Statements below that label
> these components “future” are historical, not current code truth.

## Purpose

This document fixes the initial boundaries for the Singapore new-to-bank proof of concept without implementing business workflows prematurely.

## System context

The target flow is:

`ACRA Singapore -> EDS/orchestration layer -> GoldTier -> Ready-for-Approval / human review gate`

The Phase 00 repository implements only the frontend shell and backend health endpoint. External systems are shown as future boundaries, not active connections.

```text
React UI
   |
FastAPI application / orchestration boundary
   |-- canonical internal entity model (future phase)
   |-- deterministic business services (future phase)
   |-- ACRA connector interface --> mock or authorised ACRA connector (future phase)
   `-- GoldTier connector interface --> mock or PingFed-authenticated connector (future phase)
```

## Initial components

### Frontend

React with TypeScript and Vite provides a minimal status page. It contains no onboarding stages, customer data, approval actions, or external requests in Phase 00.

### Backend

FastAPI provides a typed `GET /health` endpoint. Configuration is loaded from environment variables through `pydantic-settings`. The response exposes only service status and a non-sensitive environment label.

### External connector boundary

All ACRA and GoldTier access must be introduced behind connector/service interfaces. Business logic must consume canonical internal models rather than source or target HTTP payloads. Mock and real connectors must be selectable through configuration without changing business logic.

No connector implementation belongs to Phase 00. PingFed details, token material, PII/KYC payloads, and sponsor documents must not enter normal logs or tracked fixtures.

### Data and persistence

Phase 00 adds no database. SQLite remains the preferred initial option if a later phase demonstrates a persistence need. Introducing another database requires an explicit decision.

## Safety boundaries

- `.env` and credential/key patterns are ignored; `.env.example` contains names and safe empty values only.
- `private/` is gitignored and is the only local location for confidential sponsor artefacts.
- Normal application logs must contain safe identifiers, statuses, correlation IDs, and sanitised summaries only.
- TLS 1.3 is required when sponsor sandbox connectivity is introduced.
- AI must never be the autonomous approval authority.
- Low-confidence, inconsistent, or exceptional cases must be routed to a human review path in later phases.

## Deferred decisions

- The canonical entity model and connector protocols belong to the phase that implements the first vertical slice.
- Database schema and persistence lifetime remain undecided until workflow requirements justify them.
- The seven-operation GoldTier EDS interface is a provisional mock-development contract
  in `docs/contracts/GOLDTIER_CONTRACT_BASELINE.md`; connector implementation remains
  deferred. Its catalogued artefact conflicts and unresolved environment,
  relationship-link, hierarchy, authentication, and Singapore mapping details must not
  be guessed.
- The Ready-for-Approval transition and seeded hierarchy retrieval contract remain sponsor questions.

## Phase boundary

Phase 00 deliberately excludes live ACRA/GoldTier calls, IDP, UBO calculation, onboarding orchestration, approval workflow, dashboards, exception workbenches, and additional jurisdictions.
