# Final POC Architecture

## Sponsor flow

```text
UEN + synthetic PDF + Start
             |
             v
    ZeroTouchOrchestrator
      |       |       |
      |       |       +------------------------------+
      |       |                                      |
      v       v                                      v
 Registry  Document / IDP                      Ownership / UBO
 adapter   adapter + comparison               adapter + Decimal paths
      \       |                                      /
       \      +------------------+------------------+
        \                        v
         +----------------> CLM Readiness
                                  |
                                  v
                    GoldTier connector + Phase 05 ledger
                                  |
              +-------------------+-------------------+
              |                                       |
              v                                       v
    automatic safe continuation             exception-only HITL
              |                              then automatic resume
              +-------------------+-------------------+
                                  v
                COMPLETED / MOCK_GOLDTIER_SUBMITTED
```

## Responsibility boundaries

- `ZeroTouchOrchestrator`: stage/checkpoint order, typed exceptions, metrics, safe
  timeline, bounded transitions, automatic resume.
- Onboarding/Registry: four project-owned Mock operations, strict external DTO
  validation, requested-UEN binding, normalized acquisition bundle, and canonical map.
- Document service: transient upload, provider validation, comparison/evidence history.
- Ownership service: graph validation, Decimal traversal/aggregation, review diagnostics.
- CLM service: current-evidence readiness, immutable submission snapshot, terminal
  target translation.
- Onboarding target ledger: safe operation prefix, retained outcome, rich receipt, and
  replay-free finalization recovery.
- React: read-only presentation after Start; renders only server-authored actions and
  classifications.

## Replacement architecture

```text
Provider protocol         Current                         Future after decision gate
------------------        ----------------------------    ---------------------------
AcraConnector        -->  Mock / sandbox-shaped ACRA  --> approved subscriber adapter
IdpProvider          -->  deterministic Mock IDP      --> approved OCR/IDP adapter
OwnershipProvider    -->  synthetic graph provider    --> approved hierarchy adapter
GoldTierConnector    -->  Mock EDS behavior           --> PingFed/GoldTier adapter
```

Every replacement occurs in connector DTO/transport/decoder and composition. Generic
orchestration, document comparison, ownership arithmetic, readiness, and target
call-stopping do not require rewrite.

For normal Phase 10 Mock Singapore cases, `OwnershipProvider` is the
registry-acquisition adapter over the retained bundle. Explicit synthetic graph
providers remain developer/test fault seams. Both feed the same authoritative
`OwnershipAnalysisService`; no parallel UBO engine exists.

## State and trust

All repositories, locks, events, provider bindings, metrics, target ledgers, and
idempotency evidence are process-local and reset on backend restart. External payloads
cross a fresh-validation boundary before domain use. Browser/export surfaces omit raw
provider objects, PDF bytes, endpoints, secrets, authority digests, and target payloads.

## Claim boundary

Current executions are `MOCK`, except a configured local ACRA HTTP seam may be labeled
`SANDBOX`. No adapter is labeled `LIVE`. `MOCK_GOLDTIER_SUBMITTED` is not approval,
Ready-for-Approval, legal UBO determination, or real system acceptance.
