# Policy Decision Traceability

| Sponsor question | Policy domain | Current POC owner | Current authority | Future owner that would change | Future required verification | Blocker |
|---|---|---|---|---|---|---|
| Q-001 | Ready-for-Approval / approval owner | CLM readiness and target ledger | `UNKNOWN_BLOCKED` | CLM/target orchestration under confirmed GoldTier contract | transition, auth, idempotency, failure/recovery, Mock distinction | Exact action/state and owner absent |
| Q-003 | Document scope/fields | document intake/extraction | `UNKNOWN_BLOCKED` | document profile/IDP contract | accepted types/fields, validation, privacy, browser/API contract | Final document contract absent |
| Q-004 | Final legal UBO rule | Decimal ownership engine | `PROJECT_DEFINED_PROVISIONAL` | ownership policy configuration, not a second engine | threshold/control cases, uncertainty, legal terminology | Final rule absent |
| Q-005 | Validation responsibility | reconciliation/readiness | `PROJECT_DEFINED_PROVISIONAL` | orchestration/GoldTier validation boundary | rule ownership, rejection/failure, contract tests | Responsibility split absent |
| Q-013 | Privacy/retention/access | minimized document and case persistence | `UNKNOWN_BLOCKED` | persistence/security/governance owners | storage, encryption, access, deletion, retention, audit/recovery | Policy absent |
| Q-014 | Reviewer/confidence/separation | document review and backend capability owners | `UNKNOWN_BLOCKED` except D-009 human-exception principle | authentication/authorization plus review service | role/action matrix, self-review, four-eyes, evidence, concurrency | Exact reviewer policy absent |
| Q-015 | Source/conflict authority | reconciliation | `UNKNOWN_BLOCKED` with bounded provisional dispositions | reconciliation policy | per-field precedence, decision role, retained evidence, restart/resume | Authority absent |
| Q-016 | Identity/roles/assignment/priority | auth, authorization, team and portfolio query | `UNKNOWN_BLOCKED`; current P1–P10 is provisional | production IdP/RBAC, assignment and query policy | auth, scope, mutation, migration, ordering/effects, audit | Production policy absent |
| Q-017 | Supplied risk/workflow | no runtime owner | `UNKNOWN_BLOCKED` | existing policy/readiness owners only after architecture review | producer/vocabulary/provenance, update, workflow/EDD/readiness | Complete risk authority absent |
| Q-018 | Production handoff | Zero-Touch orchestration and Mock target boundary | `UNKNOWN_BLOCKED` | deployment/composition and target continuation | topology, handoff state/evidence, identity, failure ownership, Live proof | Production boundary absent |
| Q-002/Q-006/Q-007 | Hierarchy/related-party/mapping | provider-neutral ownership and Mock target mapping | mixed confirmed limits and unresolved details | target connector/mapper after contract authority | schema/mapping/call-stopping/response evidence | Final read/write/mapping contracts absent |
| Q-009/Q-010/Q-011 | GoldTier values/mandatory fields/examples | provisional contract validator | provisional development contract | target connector/DTO contract | corrected schemas/examples, contract/security tests | API-owner confirmation absent |

Future work must begin from the registry and this table, then re-read current source and
the authoritative sponsor evidence. This traceability is not permission to implement.

## D-064 Phase24C traceability — 2026-10-02

HR draft/edit/reset/submit and independent Director approve/reject are USER_AUTHORIZED_POC
through PolicyManagementService, existing backend capabilities and singleton repository
CAS. Frozen case policy feeds RegistryAcquisitionCoordinator, document/reconciliation,
OwnershipAnalysisService, advisory intelligence and OwnershipEvidenceTagger. Semantic
metrics/simulation use 14 labelled synthetic examples and never claim trained-model/legal
accuracy or mutate cases/providers. Runtime validation couples weights/thresholds and
forbids arbitrary/invariant proposals. Independent combined acceptance is required for
this implementation candidate. Production/sponsor activation gates stay separate.
