# Policy Activation Contract

## Gate

A future runtime policy may be activated only when all of the following exist:

1. an explicit sponsor-backed decision for the exact behavior;
2. a closed or superseded blocking question with a durable source reference;
3. an updated registry entry classified `SPONSOR_CONFIRMED`;
4. bounded runtime owners, API/schema/security/persistence impacts, and adverse cases;
5. implementation tests, affected regression, and fresh independent acceptance.

`OBSERVED` describes a fact. `PROJECT_DEFINED_PROVISIONAL` permits only the labelled POC
behavior. `UNKNOWN_BLOCKED` permits no activation. Public regulation, convention, a
prototype, a Mock success, or a local role never substitutes for sponsor authority.

## Supplied risk

Before adding a risk field or reaction, Q-017 must identify the authoritative producer,
accepted vocabulary, validation and rejection rules, provenance, update authority,
retained evidence, readiness effect, workflow reaction, EDD/reviewer action, and
approval implications. A supplied value must stay distinct from calculated risk. Until
then there is no risk score, risk engine, readiness block, EDD route, or risk-based
priority/SLA/escalation.

## Review authority

Before changing review behavior, Q-014/Q-015 must identify eligible role/capability,
self-review rule, separation-of-duties model, permitted dispositions, reject/rework/
resume authority, retained reviewer evidence, source/conflict authority, and final
approval owner. D-009 authorizes human exceptions only; it does not answer those items.

## Assignment

Before assignment/reassignment, Q-016 must identify who assigns and reassigns, whether
one or multiple teams may own/share a case, the required reason/history, visibility,
mutation authority, concurrency semantics, and authorization failure behavior.

## Priority

Before changing P1–P10, Q-016 must define allowed values, which direction is highest,
who may mutate, and whether priority is ordering-only or affects routing, SLA, deadlines,
escalation, notification, assignment, or risk. Current P1–P10 ordering-only behavior is
project-defined provisional and must not be migrated or reinterpreted without an
authorized compatibility plan.

## Ready-for-Approval

Before any Ready-for-Approval state or action, Q-001 must define prerequisites, internal
versus GoldTier state, transition owner, automated versus human responsibility, target
operation/API, failure/idempotency/recovery behavior, evidence, and relationship to final
approval. `COMPLETED / MOCK_GOLDTIER_SUBMITTED` remains distinct from
Ready-for-Approval.

## Related dependencies

Activation must also account for Q-003 document scope, Q-004 final legal UBO policy,
Q-005 validation ownership, Q-013 privacy/retention/access, Q-018 production handoff,
and Q-002/Q-006/Q-007/Q-009/Q-010/Q-011 where hierarchy or GoldTier contract details
affect the chosen behavior. A decision in one domain does not silently resolve another.
