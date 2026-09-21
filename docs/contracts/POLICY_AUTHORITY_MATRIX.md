# Policy Authority Matrix

## Purpose and status

This matrix separates current POC facts from authority to activate sponsor/production
policy. It does not answer an open sponsor question. `runtime enabled` means enabled as
sponsor/production policy, not merely present as a provisional POC mechanism.

| Policy area | Concrete decision | Current POC behavior | Authority | Exact source | Blocking question | Runtime enabled | Allowed consequence | Prohibited inference |
|---|---|---|---|---|---|---:|---|---|
| Human exception review | May a zero-touch journey stop for a human exception? | Typed review/exception paths exist. | `SPONSOR_CONFIRMED` | D-009 | — | Yes, for the narrow exception principle | Preserve human exception handling. | A particular reviewer, four-eyes rule, disposition, retention rule, or approval owner is approved. |
| Supplied risk | Producer, LOW/MEDIUM/HIGH vocabulary, validation, update, evidence, and workflow effect | No risk field, score, engine, or reaction exists. | `UNKNOWN_BLOCKED` | Q-017 | Q-017 | No | Define the decision inputs only. | Risk may be calculated, accepted, persisted, block readiness, trigger EDD, or route work. |
| Review authority | Eligible reviewer and permitted decisions | Current authenticated capabilities and bounded review/rework are POC behavior. | `UNKNOWN_BLOCKED` | Q-014 | Q-014 | No | Keep current controls explicitly provisional. | Current local roles are sponsor-approved reviewers or production RBAC. |
| Reviewer separation | Self-review and four-eyes requirements | No sponsor-approved separation-of-duties model. | `UNKNOWN_BLOCKED` | Q-014 | Q-014 | No | Define future activation prerequisites. | Existing review means four-eyes enforcement. |
| Assignment/reassignment | Who assigns, reassigns, shares, and records reason/history | Team ownership is immutable; no reassignment/sharing. | `UNKNOWN_BLOCKED` | Q-016 | Q-016 | No | Preserve current POC boundary. | Immutability or absence of reassignment is production policy. |
| Production identity/RBAC | IdP, roles, sessions, capabilities, mutation authority | Bootstrap identities and process-local sessions; backend capabilities are authoritative for the POC. | `UNKNOWN_BLOCKED` | Q-016 | Q-016 | No | Keep local behavior labelled Local/POC. | Current users, roles, sessions, or capability matrix are production-approved. |
| Priority vocabulary/order | Allowed values and which direction is highest | Nullable P1–P10; 10 sorts before 1; ordering only. | `PROJECT_DEFINED_PROVISIONAL` | D-034 | Q-016 | No | Preserve P1–P10 pending a decision. | Sponsor approval may not be inferred for values 1–3, either direction, or current P1–P10. |
| Priority workflow effect | Whether priority changes SLA, routing, escalation, notification, risk, or due dates | Ordering only. | `UNKNOWN_BLOCKED` | Q-016 | Q-016 | No | Continue to prohibit policy effects. | Ordering proves an SLA, assignment, escalation, or risk rule. |
| Source precedence | Which source wins by field and condition | Evidence is retained without a global source winner. | `UNKNOWN_BLOCKED` | Q-015 | Q-015 | No | Preserve fail-closed disagreement. | Registry, document, confidence, or recency is authoritative. |
| Conflict disposition authority | Who may keep Registry or use a document value | Narrow POC actions exist; document use is limited to a validated legal name. | `PROJECT_DEFINED_PROVISIONAL` | D-030 | Q-015 | No | Preserve bounded actions and labels. | Current actions establish final source/master-data authority. |
| Validation responsibility | Rules owned by orchestration/EDS versus GoldTier policy | Conservative POC readiness and source-conflict rules. | `PROJECT_DEFINED_PROVISIONAL` | D-023 | Q-005 | No | Keep current validation conservative and explicit. | Current split is sponsor-approved or matches seeded GoldTier policy. |
| Ready-for-Approval | Exact action/state, prerequisites, and transition owner | Success ends at `COMPLETED / MOCK_GOLDTIER_SUBMITTED`. | `UNKNOWN_BLOCKED` | Q-001 | Q-001 | No | Keep Mock completion distinct. | Mock submission is approval or Ready-for-Approval. |
| Approval owner | Human/system owner of final approval/rejection | No approval/rejection state or owner. | `UNKNOWN_BLOCKED` | Q-001/Q-014 | Q-001, Q-014 | No | Preserve unresolved approval boundary. | Automation or a current local role may approve. |
| Document scope | Required document types and target fields | Bounded PDF/DOCX/TXT technical intake and provisional four-field profile. | `UNKNOWN_BLOCKED` | Q-003 | Q-003 | No | Retain technical profile as POC-only. | Technical support defines the final KYC document contract. |
| Final legal UBO rule | Threshold, comparator, control test, and authority | Deterministic Decimal candidates use provisional `>= 25%`. | `PROJECT_DEFINED_PROVISIONAL` | D-021 | Q-004 | No | Preserve candidate terminology. | A legal/controller or compliance determination exists. |
| Retention-dependent review/audit | Retention, reviewer access, evidence, deletion, and audit use | Raw uploads are not retained; bounded state/activity exists; deletion removes case history. | `UNKNOWN_BLOCKED` | Q-013 | Q-013 | No | Keep minimization and non-audit claims. | Current storage/activity is an approved retention or compliance-audit system. |
| Production handoff ownership | Placement, handoff point, state/evidence transfer, continuation owner | External POC orchestration calls Mock GoldTier. | `UNKNOWN_BLOCKED` | Q-018 | Q-018 | No | Preserve current Mock architecture. | The production deployment/handoff boundary is approved. |

The machine-readable source for activation enforcement is
`policy_authority_registry.json`. Existing provider classifications remain governed by
`PROJECT_STATE.md` and `scripts/check_project_state.py`.
