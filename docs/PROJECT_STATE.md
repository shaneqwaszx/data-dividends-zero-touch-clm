# Current Project State

This is the concise operational snapshot of what is true in the tracked repository.
It is not a sponsor contract, phase report, or substitute for current source and tests.

## Verification metadata

```json project-state
{
  "schema_version": 1,
  "case_envelope_schema_version": 3,
  "verified_date": "2026-09-20",
  "verified_main_sha": "614e9ffc36bc8f0d1a9a4674d04639ad6b2bc638",
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
  "open_sponsor_questions": ["Q-001", "Q-002", "Q-003", "Q-004", "Q-005", "Q-006", "Q-007", "Q-008", "Q-009", "Q-010", "Q-011", "Q-012", "Q-013", "Q-014", "Q-015", "Q-016", "Q-017", "Q-018"]
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
- Phase 15A: authority-labelled evidence terminology and future-policy boundaries,
  without adding runtime ageing, supplied-risk, or production-handoff behavior.
- Phase 15B: current-evidence-only review mutation, fail-closed reviewed-value
  reconciliation, partial-review blocking, failed-replacement reupload recovery, and
  bounded repeat/resume recovery under the existing target no-replay ledger.
- Development tooling: repository-only Playwright, guarded browser-network, physical
  Mongo, read-only GitHub PR/CI, and Windows lifecycle verification support. This is
  development infrastructure, not business or product functionality.
- Phase 15C: React Router URL navigation, deep-link/history-safe case identity, stale
  callback isolation, and truthful Vite development history fallback behavior.

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
  approved disposable names. `clm_poc` is never a physical test/cleanup database. The
  guarded runner owns four explicit suites and reports their dynamic collection and
  execution counts. Project acceptance requires every currently collected owned test
  to execute and pass with zero failures, errors, or skips. On this verified baseline
  that was 17 collected, 17 executed, and 17 passed; 17 is evidence for this baseline,
  not a permanent future test-count contract.

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

## Phase 15A sponsor rebaseline (provisional / authority-labelled)

**Observed current implementation:** onboarding starts when a user supplies the
onboarding package: a registration identifier and supporting corporate documents. The
POC processes that supplied package; it does not claim upstream document solicitation
or collection. ACRA is Mock by default, its generic sandbox-shaped seam is partial,
BizFile is dormant, IDP is local deterministic, and GoldTier is Mock only. No Live
ACRA, Live GoldTier, or Live PingFed connection is proved.

**Project/sponsor direction, not current runtime:** LOW/MEDIUM/HIGH is a supplied-risk
direction; the POC has no risk field, risk engine, score, or calculated risk. The
current P1–P10 ordering implementation conflicts with an emerging 1–3 direction and
remains unchanged pending Q-016. There is no ACRA cache: 90 days is only an example of
a future configurable freshness policy, not a runtime/configured rule.

**Future/KIV and open authority:** there is no ageing/SLA, OCDD, periodic refresh, or
perpetual-KYC runtime. The implemented external Zero-Touch -> Mock GoldTier sequence
is POC architecture only; its production deployment and handoff boundary remain open
pending sponsor authority.

## Phase 15B review/rework stabilization

Review mutations are limited to current evidence; superseded document records remain
historical lineage. Reviewed values enter reconciliation only through the existing
bounded decision rules, with fail-closed evidence, canonical, version, and fingerprint
checks. Partial review remains blocking and cannot silently clear another document,
reconciliation, ownership, or workflow blocker.

A failed replacement remains the current failed record and returns the case to targeted
reupload/retry rather than leaving an active exception bound to superseded evidence.
Explicit repeat/resume paths are bounded and idempotent: they repair supported
interrupted checkpoints or return the current state, while the target ledger remains
the sole owner of target ordering and no-replay behavior. This is monotonic sequential
recoverability for the single-instance POC; it is not distributed transaction
atomicity, exactly-once execution, final reviewer assignment, source precedence, or
final approval.

## Repository and development tooling

The repository includes an exact-pinned Playwright Chromium E2E harness with guarded
browser network policy, a guarded runner for the four owned physical Mongo suites,
read-only GitHub PR/CI inspection tooling, and hardened Windows demo lifecycle
verification. These capabilities support local development, CI, and verification;
they do not add a product workflow, business capability, Live provider integration, or
sponsor-approved behavior.

## Phase 15C frontend URL navigation

The frontend uses exact `react-router` 7.18.4 in declarative `BrowserRouter` mode.
Browser location is the sole page and case-navigation identity, and `NavLink`/`Link`
navigation supports direct links, refresh, new-tab links, and browser Back/Forward
without making route entry a business mutation. Case detail actions are isolated by
case/action generation so a stale action from a previously displayed case cannot be
published against the current route. Retained-intake callbacks use the same generation
principle so stale work from an earlier intake cannot alter a later intake identity.

Local development uses Vite 7.1.11 with `appType: "mpa"` and Vite-first request
handling. Only a positively admitted unresolved document-navigation request may receive
the SPA entry document; API requests, existing or missing resources/file requests, and
unsafe methods retain truthful Vite/proxy/not-found/method behavior. Equivalent
production-host history fallback remains unverified and outside Phase 15C scope.

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
- Q-017 blocks supplied LOW/MEDIUM/HIGH risk input authority: its producer/source,
  validation/provenance, update authority, workflow reactions, EDD/approval, and
  readiness-blocking semantics remain unresolved; no calculated risk score is authorized.
- Q-018 blocks the production Zero-Touch / GoldTier deployment and handoff boundary.
  The current external Zero-Touch -> Mock GoldTier sequence is POC architecture; its
  production placement (external versus inside/alongside GoldTier), handoff point,
  transferred state/evidence, and ownership remain unresolved.
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
