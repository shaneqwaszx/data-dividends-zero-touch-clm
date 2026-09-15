# Current Project State

This is the concise operational snapshot of what is true in the tracked repository.
It is not a sponsor contract, phase report, or substitute for current source and tests.

## Verification metadata

```json project-state
{
  "schema_version": 1,
  "case_envelope_schema_version": 3,
  "verified_date": "2026-09-15",
  "verified_main_sha": "fd760e4f74019002f5f9374467cc6a701f6cf585",
  "verification_status": "verified-against-main",
  "providers": {
    "registry": {"name": "ACRA", "mode": "mock", "classification": "MOCK"},
    "registry_sandbox": {"name": "ACRA_GENERIC_SANDBOX", "mode": "sandbox", "classification": "PARTIAL"},
    "registry_bizfile": {"name": "ACRA_BIZFILE", "mode": "dormant", "classification": "DORMANT"},
    "idp": {"name": "LOCAL_PDF_TEXT", "mode": "local_pdf_text", "classification": "LOCAL"},
    "idp_fault": {"name": "MOCK_IDP", "mode": "mock", "classification": "MOCK"},
    "ownership": {"name": "DECIMAL_GRAPH_ENGINE", "mode": "local", "classification": "LOCAL"},
    "target": {"name": "GOLDTIER", "mode": "mock", "classification": "MOCK"}
  },
  "persistence": {"default": "memory", "supported": ["memory", "mongo"]},
  "identity": {
    "account_source": "bootstrap_repositories",
    "session_store": "process_local",
    "production_sso": "not_implemented"
  },
  "workflow_engine": {"camunda": "not_implemented"},
  "open_sponsor_questions": ["Q-001", "Q-002", "Q-003", "Q-004", "Q-005", "Q-006", "Q-007", "Q-008", "Q-009", "Q-010", "Q-011", "Q-012", "Q-013", "Q-014", "Q-015", "Q-016"]
}
```

`verified_main_sha` identifies the main baseline inspected for this snapshot. Feature
branch HEADs are not expected to equal it. The snapshot becomes stale when accepted
main behavior changes without a closeout refresh, not merely when a feature commit is
created. `schema_version` versions this metadata format;
`case_envelope_schema_version` is independently checked against the canonical
persistence constant.

## Current status

The repository is a synthetic, local/sandbox-shaped proof of concept for Singapore
new-to-bank corporate onboarding. The supported happy path can reach
`COMPLETED / MOCK_GOLDTIER_SUBMITTED`; that means the credential-free Mock target path
completed. It does not mean customer approval, compliance approval, legal UBO
determination, Ready-for-Approval, or live interoperability.

Major implemented phases are:

- Phase 01–02: vertical slice, Mock ACRA, strict mapping, safe failure behavior, and a
  generic sandbox-shaped ACRA seam.
- Phase 03–04: bounded document extraction/review and deterministic Decimal ownership
  graph/UBO-candidate analysis.
- Phase 05–08: staged readiness, replay-aware Mock GoldTier execution, zero-touch
  exception/resume, input-driven synthetic evidence, and demo/UAT evidence.
- Phase 09–11: source-aware jurisdiction resolution, Singapore registry routing,
  expanded Mock acquisition, and source-neutral reconciliation.
- Pre-Phase 12 and Phase 12: multi-document workspace plus explicit memory/Mongo
  durable POC persistence and restart recovery.
- Phase 13–14: local authentication/RBAC/team priority, dashboard/portfolio read model,
  permanent authorized deletion, and session-memory React Query caching.
- Phase 14.5: repository-backed synthetic team/profile administration, typed policy
  catalogue, and immutable per-case policy snapshots.

## Current runtime pipeline

```text
authenticated browser/API request
  -> current process-local session, profile, team and capabilities
  -> backend authorization and creation/portfolio scope
  -> immutable case policy snapshot
  -> jurisdiction observations and resolver
  -> closed registry router (resolved SG only)
  -> ACRA Mock or configured generic sandbox-shaped acquisition
  -> canonical legal entity and normalized registry evidence
  -> bounded document intake and local deterministic extraction
  -> source-neutral reconciliation and review/resume where required
  -> registry-fed deterministic Decimal ownership graph analysis
  -> readiness and immutable target snapshot
  -> ordered Mock GoldTier search/shell/policy/amend with retained recovery ledger
  -> authorized case portfolio/dashboard and detailed evidence views
```

Technical composition is centered in `apps/backend/app/main.py`,
`apps/backend/app/composition.py`, and `apps/backend/app/persistence/composition.py`.
Business behavior stays in domain/services; adapters stay at connector/persistence
boundaries.

## Current External Integration Truth

| Boundary | Active/default | Other implemented seam | Classification | What is proved |
|---|---|---|---|---|
| ACRA | `mock` | generic `sandbox` connector | Mock active; sandbox partial | Synthetic ACRA-shaped behavior and adapter isolation |
| ACRA BizFile | none | module exists but is not composed | Dormant | Focused adapter code/tests only, not runtime availability |
| IDP/OCR | `local_pdf_text` | Mock fault/demo provider | Local POC / Mock | Deterministic extraction from supported synthetic documents |
| Ownership | registry evidence into local engine | Mock fault/demo provider | Local / Mock support | Deterministic Decimal graph analysis, not an external service |
| GoldTier | `mock` only | none | Mock | Ordered synthetic target behavior and recovery semantics |
| PingFed | none | future placeholders only | Not implemented | No token retrieval or authenticated target connection |
| MongoDB | memory by default | explicit `mongo` mode | Optional local infrastructure | Single-instance durable POC behavior when configured |
| Camunda | none | none | Not implemented | No runtime workflow-engine integration |
| Production IdP/SSO | none | local bootstrap identities | Local POC | Process-local opaque sessions and backend RBAC |

No row classified Mock, Local, Partial, Dormant, or Not implemented may be presented as
Live. Tool or credential availability alone would not change this classification;
authorized contract and execution evidence are required.

## Evidence authority labels

- **Observed:** source, tests, configuration, or composition directly establish it.
- **Project-defined / provisional:** implemented POC behavior recorded in contracts or
  decisions, pending sponsor confirmation.
- **Sponsor-confirmed:** a direct sponsor clarification recorded in the decision log.
- **Unknown / blocked:** the sponsor/API owner has not supplied sufficient authority or
  usable access evidence.

The provider matrix above is Observed. Thresholds, role behavior, policy defaults,
reconciliation actions, and deletion governance are mostly project-defined/provisional.
GoldTier amend path, first-level related-party limit, lack of hierarchy creation,
PingFed target, TLS 1.3 requirement, ACRA proof labeling, and UTC sourcing guidance have
recorded sponsor confirmation. Live ACRA/GoldTier binding and production policy remain
unknown or blocked.

## Persistence modes

- `memory` is the default. State and sessions are process-local and a backend restart
  clears them.
- `mongo` is explicit. Missing/invalid configuration, startup validation, reads, or
  writes fail closed and never fall back to memory.
- One schema-versioned case envelope (current schema v3) owns durable case state.
  Repository adapters preserve revision compare-and-set, insert-only creation,
  update-only mutation, strict identity binding, and replay-aware recovery.
- Global team/profile/policy records use separate bounded repository owners.
- Raw uploads, full extracted text, raw external payloads, credentials, sessions, and
  connection strings are excluded from case envelopes.
- Physical tests use generated allowlisted `clm_p12_*`, `clm_p13_*`, or newer explicitly
  approved disposable names. `clm_poc` is never a physical test/cleanup database.

## Authentication, authorization and administration

- Six synthetic bootstrap identities and repository-backed profiles/teams are used.
- Authentication uses password hashes and opaque process-local sessions; this is not
  production IAM, SSO, or an external identity provider.
- Backend capabilities and case access are authoritative. Frontend visibility is only
  presentational.
- Cross-team and absent case IDs share the same safe 404 behavior.
- Team assignment is canonical server state. Director filters are validated and
  applied by backend query services.
- Sensitive mutations re-authorize within the owning case or repository lock/CAS
  boundary.
- HR administers synthetic profiles/teams and reads policies but has no case access or
  runtime policy mutation authority.

## Major current capabilities

- Controlled Singapore/ACRA routing with no implicit source precedence.
- Four-operation Mock registry acquisition with truthful complete/partial/failure
  evidence and downstream call stopping.
- PDF, DOCX and UTF-8 TXT technical intake with strict size/structure handling.
- Deterministic local extraction and field provenance.
- Source-neutral reconciliation with explicit bounded actions and resume.
- Deterministic Decimal direct/indirect ownership paths and provisional UBO candidates.
- Immutable per-case IDP/UBO policy snapshot.
- Ordered Mock target execution with no-replay recovery states.
- Memory/Mongo repository parity, case deletion, portfolio projection, dashboard, team
  filtering, priority, and session-scoped query caching.
- Safe synthetic UAT evidence and Windows demo lifecycle tooling.

## Current explicit non-capabilities

- No proven live ACRA, PingFed, GoldTier, external ownership, vendor OCR, production
  SSO/IdP, or Camunda connection.
- No ASIC/Malaysia/Hong Kong registry adapter in active runtime.
- No `createRelationship` or multi-level hierarchy creation through GoldTier.
- No sponsor-approved final UBO, document, source-authority, RBAC, retention, deletion,
  review, or Ready-for-Approval policy.
- No autonomous approval, risk/compliance engine, legal UBO determination, production
  audit repository, distributed workflow, or multi-instance exactly-once guarantee.
- No full analytics/MIS platform or full Exception Workbench.

## Current open sponsor blockers

- Q-012 blocks authoritative/live ACRA binding, operation schema, auth, errors, rate
  limits, TLS/mTLS/private-CA requirements, and sandbox proof.
- Q-008/D-018 blocks real GoldTier/PingFed authentication material and containment.
- Q-001/Q-002/Q-006/Q-007 block Ready-for-Approval, hierarchy retrieval, related-party
  semantics, and final Singapore target mappings.
- Q-003/Q-005/Q-013/Q-014/Q-015 block final document scope, validation/source authority,
  privacy/retention, confidence/reviewer policy, and jurisdiction/reconciliation authority.
- Q-004 blocks final legal UBO threshold/control policy.
- Q-016 blocks production identity, role, assignment, prioritization, and admin policy.
- Q-009/Q-010/Q-011 retain contract value/mandatory-field/corrected-artefact questions.

Consult `docs/sponsor-questions/OPEN_QUESTIONS.md` for exact wording and current status.

## Current architectural debt

- `apps/backend/app/main.py` and `apps/frontend/src/App.tsx` are composition hot spots.
- Historical phase documents repeat current-state claims and may be stale; this file and
  current source now provide the short operational route.
- `ownership_connector_mode` remains Mock-named configuration while normal ownership
  uses registry evidence and the local engine; future change must reconcile rather than
  add another engine.
- Generic ACRA sandbox behavior is only partial for expanded operations; BizFile remains
  intentionally dormant.
- Mongo and administration atomicity are single-process POC guarantees, not distributed
  guarantees.
- Audit all-cases pagination/retention and broader performance work remain intentionally
  deferred.

## Next candidate work packages

These are candidates, not authorization to implement:

1. Sponsor contract/access reconciliation for ACRA and GoldTier/PingFed.
2. Independent governance-context quality gate and any bounded remediation.
3. Sponsor-confirmed Ready-for-Approval/reviewer/retention policy design.
4. Authoritative external-provider work only after contract, security and credential
   prerequisites are satisfied.
5. Measured hotspot or portfolio/audit pagination work if evidence shows need.

Every new package requires a bounded planner handoff, change classification, relevant
skill, proportional verification, and independent quality gate.
