# Phase 20 Sponsor Policy Decision Packet

## How to answer

Please answer each numbered decision explicitly, identify any governing artefact, and
state when an answer applies only to the POC or to production. The prototype behavior
below is context, not a recommended sponsor answer. Until an item is answered, its
runtime policy remains blocked.

## 1. Ready-for-Approval and final approval (Q-001)

**Prototype today:** the Mock path can finish as
`COMPLETED / MOCK_GOLDTIER_SUBMITTED`.

**Not confirmed:** whether this is Ready-for-Approval, whether another GoldTier action
exists, prerequisites, transition owner, and final approval/rejection owner.

**Decision required:** choose and describe one: (A) automatic after a named confirmed
call sequence; (B) a distinct named GoldTier API/action; (C) a human-owned internal
transition; or (D) another explicit model. For the chosen model provide prerequisites,
failure/retry behavior, evidence, and final approval owner.

**Consequence:** only the chosen transition may be implemented. Until answered, Mock
completion remains neither Ready-for-Approval nor approval.

## 2. Validation ownership (Q-005)

**Prototype today:** orchestration applies conservative canonical, document,
reconciliation, ownership, and readiness checks before Mock target calls.

**Not confirmed:** which rules belong to orchestration/EDS and which belong to seeded
GoldTier policy.

**Decision required:** list each rule/field, its owner, failure response, and whether
the other side must revalidate it.

**Consequence:** confirmed orchestration rules may become explicit runtime policy;
GoldTier-owned rules require an authoritative target contract. Until answered, the
current split stays project-defined provisional.

## 3. Document scope, privacy, retention, and access (Q-003/Q-013)

**Prototype today:** bounded PDF/DOCX/TXT intake supports a provisional four-field
profile; raw uploads/full extracted text are not retained in the case envelope.

**Not confirmed:** required document types/fields, lawful test data, allowed
environments, retention/deletion, encryption/jurisdiction, reviewer access, malware/CDR,
and audit use.

**Decision required:** provide the required document/field matrix and the security,
access, retention, deletion, and approved-processing policy.

**Consequence:** the exact profile and storage/access controls can then be designed.
Until answered, technical support is not the final KYC document or retention contract.

## 4. Review, confidence, and separation of duties (Q-014)

**Prototype today:** deterministic provisional confidence rules and bounded authenticated
review/rework exist. Sponsor decision D-009 confirms that human exceptions are allowed
and expected.

**Not confirmed:** threshold model, review triggers, eligible roles, permitted
dispositions, self-review, four-eyes, retained reviewer evidence, and final approval.

**Decision required:** provide thresholds/triggers and select: (A) self-review allowed
for named actions; (B) four-eyes for named actions; (C) four-eyes for all dispositions;
or (D) another explicit model. Name roles/capabilities, evidence, and approval owner.

**Consequence:** only the selected role/action matrix may be enforced. Until answered,
current roles and review actions are not production policy or four-eyes approval.

## 5. Source precedence and conflict authority (Q-015)

**Prototype today:** Registry and Document observations are retained without a global
winner; narrow POC conflict dispositions exist.

**Not confirmed:** authoritative source by field/condition, who resolves conflict, what
correction/evidence is required, and restart versus resume.

**Decision required:** for each field choose Registry, Document, another source, or
explicit review; state conditions, deciding role, retained evidence, and resume rule.

**Consequence:** only confirmed per-field rules may select master/canonical data. Until
answered, there is no implicit Registry-, Document-, confidence-, or newest-wins rule.

## 6. Identity, roles, assignment, and priority (Q-016)

**Prototype today:** local bootstrap users/process sessions, backend POC capabilities,
immutable team ownership, no reassignment/sharing, and nullable P1–P10 priority affecting
ordering only.

**Not confirmed:** production IdP/session/RBAC, role mutations, assignment/reassignment,
team cardinality, reason/history, priority values/direction/mutator, and any downstream
effect.

**Decision required:** provide the production role/capability matrix and assignment
model. For priority, select values/direction (for example 1–3 with 1 highest) and mark
each effect yes/no: ordering, routing, SLA/deadline, escalation, notification, assignment,
risk.

**Consequence:** a future implementation can plan authorization and compatibility from
P1–P10. Until answered, local roles are not production RBAC and priority remains
ordering-only provisional POC behavior.

## 7. Supplied risk and workflow reaction (Q-017)

**Prototype today:** no risk input, score, calculation, persistence, or workflow effect.

**Not confirmed:** producer, LOW/MEDIUM/HIGH vocabulary, validation/provenance, update
authority, retention, readiness effect, EDD, reviewer action, and approval effect.

**Decision required:** name the authoritative producer; confirm vocabulary and invalid/
missing behavior; identify who may update it; and mark each effect yes/no with exact
transitions: readiness block, EDD, reviewer route, approval route, priority/SLA effect.

**Consequence:** a supplied value and only its confirmed reactions may be implemented.
Until answered, the system must not calculate risk or activate any risk behavior.

## 8. Final legal UBO rule (Q-004)

**Prototype today:** deterministic Decimal ownership candidates use project-defined
`aggregated ownership >= 25%` plus uncertainty handling.

**Not confirmed:** final threshold/comparator, control tests, jurisdiction variation,
and legal/reviewer authority.

**Decision required:** state the exact threshold/comparator and any control or
jurisdiction rules; identify who resolves incomplete/cyclic evidence and who owns the
legal determination.

**Consequence:** the existing single Decimal engine can be configured and verified.
Until answered, results remain provisional candidates, not legal UBO decisions.

## 9. Production Zero-Touch / GoldTier handoff (Q-018)

**Prototype today:** external POC orchestration calls Mock GoldTier with a no-replay
ledger.

**Not confirmed:** production placement, handoff point, transferred state/evidence,
continuation owner, identity, audit, and failure ownership.

**Decision required:** choose external, inside, or alongside GoldTier; name the handoff
operation/state, transferred evidence, continuation owner, identity boundary, and
failure/recovery responsibility.

**Consequence:** only then can production topology and Live integration work be scoped.
Until answered, the current external-to-Mock sequence is POC architecture only.

## 10. Dependent GoldTier details (Q-002/Q-006/Q-007/Q-009/Q-010/Q-011)

Where the decisions above depend on hierarchy retrieval, direct related-party semantics,
Singapore mappings, value casing, mandatory fields, or corrected examples, please
provide or confirm the exact operation contract and artefact authority. Those API-owner
answers remain separate from business-policy approval.
