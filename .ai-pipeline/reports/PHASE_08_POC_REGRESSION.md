# Phase 08 POC Regression Check

## Result

Backend accepted scenarios and contract assertions are preserved: `pytest
apps/backend/tests` passed 502 tests after the remediation and contract discovery passed
44 tests.

## Phase 08 exercised paths

| Input | Observed result | Call-stopping invariant |
|---|---|---|
| Matching UEN/PDF | `COMPLETED / MOCK_GOLDTIER_SUBMITTED` | Mock target proceeds only after document, ownership, readiness |
| Address-mismatch PDF | `WAITING_FOR_REVIEW / DOCUMENT_SOURCE_CONFLICT` | No later stage before resolution/replacement |
| Clean replacement | Prior document superseded; automatic completion | Superseded blocker excluded; current evidence re-evaluated |
| No-text PDF | `WAITING_FOR_REVIEW / DOCUMENT_TEXT_UNAVAILABLE` | No fabricated extraction or target call |
| UEN `202400006F` | `WAITING_FOR_REVIEW / OWNERSHIP_CYCLE` | No target call |
| UEN `202400005E` | existing-party review | Mock SEARCH only; no shell/policy/amend |

The supported normal composition regression now proves that the Windows launcher selects
`LOCAL_PDF_TEXT`: the same UEN with clean, address-mismatch, and ambiguous actual PDF
bytes produces completion, `DOCUMENT_SOURCE_CONFLICT`, and `DOCUMENT_LOW_CONFIDENCE`
respectively. Renaming clean bytes to `low_confidence.pdf` remains clean; renaming
mismatch bytes to `clean.pdf` remains a mismatch. The delivered `cycle-uen-clean.pdf`
passes the document stage before input-driven ownership returns `OWNERSHIP_CYCLE`.

Normal start does not send a scenario. Developer/Test routes stay gated and scenario
selection remains confined to their provider boundary. Mock/local labels and
Ready-for-Approval/live-interoperability claim boundaries remain unchanged.

## Catalogue treatment

The Phase 01–07 catalogue was not rewritten. New Phase 08 cases are recorded in
`docs/uat/PHASE_08_UAT_CATALOGUE.md`; they are additive, verified input-driven cases.

## Windows lifecycle completion

With clean ports, the launcher completed start, backend/frontend health verification,
and exact owned-process shutdown, leaving no runtime metadata or listeners. The
`Path`/`PATH` normalization and the CIM-denied identity fallback were exercised without
changing machine environment variables or selecting processes by image name. Occupied
ports remain a preflight failure and are never terminated by the launcher.
