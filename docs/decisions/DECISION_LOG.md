# Decision Log

Use this file for requirements that have been explicitly resolved.

| ID | Decision | Source / reason | Status |
|---|---|---|---|
| D-001 | Main project flow is ACRA Singapore -> EDS/orchestration -> GoldTier using Singapore NTB. | Latest sponsor clarification | Confirmed |
| D-002 | ACRA is the sole live external corporate registry source for the FYP. | Latest sponsor clarification | Confirmed |
| D-003 | Canonical amendParty endpoint is `POST /v1/eds/parties/{partyId}/amend`. | Latest sponsor clarification | Confirmed |
| D-004 | `createRelatedParty` creates/supports direct first-level related-party relationships only. | Latest sponsor clarification | Confirmed |
| D-005 | Multi-level hierarchy creation is not supported via the current API; seeded GoldTier hierarchy is to be retrieved/displayed. | Latest sponsor clarification | Confirmed |
| D-006 | ACRA `registrySourceLink` should reference ACRA and the corresponding API endpoint; UTC ISO-8601 sourcing time is acceptable/recommended. | Latest sponsor clarification | Confirmed |
| D-007 | GoldTier sandbox authentication target is PingFed; exact connection details will be provided when Nutmeg is ready. | Latest sponsor clarification | Confirmed |
| D-008 | TLS 1.3 is required for sponsor sandbox connectivity. | Latest sponsor clarification | Confirmed |
| D-009 | Human-in-the-loop review is allowed/expected; “zero touch” does not mean no human exceptions. | Sponsor Q&A | Confirmed |
| D-010 | UBO calculation should be deterministic in the POC; AI may assist extraction but should not autonomously decide approval. | Project risk/safety design | Working decision |
