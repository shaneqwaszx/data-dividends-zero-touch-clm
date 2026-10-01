# Policy Authority Matrix

## Purpose and status

This matrix separates current POC facts from authority to activate sponsor/production
policy. D-062 resolves the bounded POC threshold/comparator while preserving open
legal/control and production questions. `runtime enabled` means enabled as
sponsor/production policy, not merely present as a provisional POC mechanism.

| Policy area | Concrete decision | Current POC behavior | Authority | Exact source | Blocking question | Runtime enabled | Allowed consequence | Prohibited inference |
|---|---|---|---|---|---|---:|---|---|
| Human exception review | May a zero-touch journey stop for a human exception? | Typed review/exception paths exist. | `SPONSOR_CONFIRMED` | D-009 | — | Yes, for the narrow exception principle | Preserve human exception handling. | A particular reviewer, four-eyes rule, disposition, retention rule, or approval owner is approved. |
| Supplied risk | Producer, LOW/MEDIUM/HIGH vocabulary, validation, update, evidence, and workflow effect | No supplied-risk owner exists. A separate case-bound `MOCK_ADVISORY_RISK / NOT_COMPLIANCE_DECISION` POC projection uses available local evidence; missing groups are `NOT_ASSESSED`, and its editable readiness-review flag defaults false. | `UNKNOWN_BLOCKED`; mock projection is `PROJECT_DEFINED_PROVISIONAL` | Q-017 / D-047 | Q-017 | No sponsor/production activation | Permit a visibly mock advisory demonstration and optional project-configured human review on newly bound cases. | The mock score is supplied risk, a compliance decision, sponsor risk appetite, EDD authority, approval, or production routing. |
| Review authority | Eligible reviewer and permitted decisions | Current authenticated capabilities and bounded review/rework are POC behavior. | `UNKNOWN_BLOCKED` | Q-014 | Q-014 | No | Keep current controls explicitly provisional. | Current local roles are sponsor-approved reviewers or production RBAC. |
| Reviewer separation | Self-review and four-eyes requirements | No sponsor-approved separation-of-duties model. | `UNKNOWN_BLOCKED` | Q-014 | Q-014 | No | Define future activation prerequisites. | Existing review means four-eyes enforcement. |
| Assignment/reassignment | Who assigns, reassigns, shares, and records reason/history | Team ownership is immutable; no reassignment/sharing. | `UNKNOWN_BLOCKED` | Q-016 | Q-016 | No | Preserve current POC boundary. | Immutability or absence of reassignment is production policy. |
| Production identity/RBAC | IdP, roles, sessions, capabilities, mutation authority | Bootstrap identities and process-local sessions; backend capabilities are authoritative for the POC. | `UNKNOWN_BLOCKED` | Q-016 | Q-016 | No | Keep local behavior labelled Local/POC. | Current users, roles, sessions, or capability matrix are production-approved. |
| Priority vocabulary/order | Allowed values and which direction is highest | UI uses Low/Medium/High/Unset; canonical writes are 1/5/10; legacy 1–3/4–7/8–10 reads map to the three tiers; the nullable 1–10 API/Mongo field and descending ordering remain compatible. | `PROJECT_DEFINED_PROVISIONAL` | D-045 | Q-016 | No | Preserve existing stored cases while using the bounded UAT vocabulary. | Sponsor approval, risk meaning, SLA, escalation, approval order, or regulatory significance may not be inferred. |
| Priority workflow effect | Whether priority changes SLA, routing, escalation, notification, risk, or due dates | Ordering only. | `UNKNOWN_BLOCKED` | Q-016 | Q-016 | No | Continue to prohibit policy effects. | Ordering proves an SLA, assignment, escalation, or risk rule. |
| Source precedence | Which source wins by field and condition | Evidence is retained without a global source winner. | `UNKNOWN_BLOCKED` | Q-015 | Q-015 | No | Preserve fail-closed disagreement. | Registry, document, confidence, or recency is authoritative. |
| Conflict disposition authority | Who may keep Registry or use a document value | Narrow POC actions exist; document use is limited to a validated legal name. | `PROJECT_DEFINED_PROVISIONAL` | D-030 | Q-015 | No | Preserve bounded actions and labels. | Current actions establish final source/master-data authority. |
| Validation responsibility | Rules owned by orchestration/EDS versus GoldTier policy | Conservative POC readiness and source-conflict rules. | `PROJECT_DEFINED_PROVISIONAL` | D-023 | Q-005 | No | Keep current validation conservative and explicit. | Current split is sponsor-approved or matches seeded GoldTier policy. |
| GoldTier XPI target values | Approved values/vocabularies for customer type, segment, external system, registration type, policy, booking entity, account entity type, and product type | The corrected standalone OpenAPI 1.0.0 owns exact 17-value KYC and 23-value Client Segment lists. KYC/segment remain unresolved per case until an authorized bounded selection; they are never global defaults. Fixed SG POC values are `ACRA`, `DSD`, `Singapore`, and `ANZBGL (Singapore Branch)`. Optional account/product fields serialize empty when unconfirmed. | `SPONSOR_DOCUMENTED / USER_AUTHORIZED_POC`; case selection is not sponsor/production policy | D-048, D-052, D-055, D-056, D-057 / ADR-004 | Q-006, Q-007, Q-009, Q-010 | No production activation | Validate only current vocabularies, bind one selection per case, freeze before target dispatch, and fail closed while unresolved. | One case choice applies globally; older conflicting vocabularies may be unioned; a sandbox success proves production policy. |
| Ready-for-Approval | Exact action/state, prerequisites, and transition owner | Success ends at `COMPLETED / MOCK_GOLDTIER_SUBMITTED`. | `UNKNOWN_BLOCKED` | Q-001 | Q-001 | No | Keep Mock completion distinct. | Mock submission is approval or Ready-for-Approval. |
| Approval owner | Human/system owner of final approval/rejection | No approval/rejection state or owner. | `UNKNOWN_BLOCKED` | Q-001/Q-014 | Q-001, Q-014 | No | Preserve unresolved approval boundary. | Automation or a current local role may approve. |
| Document scope | Required document types and target fields | Bounded PDF/DOCX/TXT intake defaults to a `CERTIFICATE_OF_INCORPORATION_POC` profile. Legal name, registration number, and jurisdiction are required; registered address remains optional registry-only evidence when absent from the certificate. | `USER_AUTHORIZED_POC / PROJECT_DEFINED_POC` | D-052 | Q-003 | No sponsor/production activation | Demonstrate the simplified COI journey without fabricating certificate fields. | The POC profile defines a final KYC document contract, proves certificate authenticity, or makes Registry globally authoritative. |
| Bounded POC ownership threshold | Default aggregated ownership threshold and comparator | Deterministic Decimal candidates use sponsor-confirmed `>= 25%`, `GREATER_THAN_OR_EQUAL_TO`. Existing catalogues/snapshots retain historical labels without rewrite. | `SPONSOR_CONFIRMED` for this bounded default | D-062, 2026-10-01 | — for threshold/comparator | No production activation | Use the confirmed default; review incomplete/indeterminate evidence. | An edited threshold is confirmed, or a complete legal/control or production UBO determination exists. |
| Final legal UBO rule | Complete legal/control tests, evidence and production authority | Candidate analysis remains bounded; confirmed numeric threshold alone does not settle legal/control tests. | `PROJECT_DEFINED_PROVISIONAL` | D-062; historical D-021 | Q-004 | No | Preserve candidate terminology and open legal/control authority. | Confirmation of the default activates complete production compliance policy. |
| Retention-dependent review/audit | Retention, reviewer access, evidence, deletion, and audit use | Raw uploads are not retained; bounded state/activity exists; deletion removes case history. | `UNKNOWN_BLOCKED` | Q-013 | Q-013 | No | Keep minimization and non-audit claims. | Current storage/activity is an approved retention or compliance-audit system. |
| Production handoff ownership | Placement, handoff point, state/evidence transfer, continuation owner | External POC orchestration calls Mock GoldTier by default; the optional XPI adapter is sandbox/Partial only. | `UNKNOWN_BLOCKED` | Q-018 / D-048 | Q-018 | No | Preserve the existing orchestration/ledger boundary and explicit provider labels. | The sandbox lane proves a production deployment/handoff boundary. |

The machine-readable source for activation enforcement is
`policy_authority_registry.json`. Existing provider classifications remain governed by
`PROJECT_STATE.md` and `scripts/check_project_state.py`.

## Dated POC workflow clarification — 2026-10-01

D-062 places KYC within evidence preparation. RM/onboarder Review & Send is submission
confirmation. A separate KYC analyst, compliance approver, second final approver and
mandatory four-eyes step are not required for this POC. The production reviewer and
separation rows above remain unresolved; they do not introduce local approval blockers.

Ready-for-Approval is not a local mandatory state unless the actual target API requires
it. No such requirement is established by inspected current XPI material. EDD is out
of scope absent technically mandatory target authority. Regulatory approval is not
claimed by target submission.

Local risk is advisory: LOW continues, MEDIUM warns and continues, HIGH may request
justified RM attention. A probability alone is not a hard blocker. GoldTier's reported
built-in risk capability remains separate from verified API screening ownership.
PEP/sanctions/adverse media and wealth/funds are not established mandatory current XPI
inputs; no duplicate screening or invented mapping follows from workbook presence.
See the current contract and screening reconciliation for exact evidence limitations.

The machine registry's bounded threshold entry is sponsor-confirmed but keeps
`runtime_enabled=false`: its activation scope is `SPONSOR_POLICY_PRODUCTION`, while
D-062 confirms a bounded POC default. Existing final legal/control gate remains Q-004.
