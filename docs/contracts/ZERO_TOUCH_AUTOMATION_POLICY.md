# Zero-Touch Automation Policy — Phase 06 POC

**Classification:** PROJECT-DEFINED / PROVISIONAL / NOT SPONSOR-APPROVED

This policy makes Phase 06 deterministic without resolving Q-003, Q-004, Q-005,
Q-013, or Q-014. D-009 permits human intervention for exceptions; it does not authorize
autonomous approval.

## Automatic continuation rules

| Boundary | Continue automatically only when | Otherwise |
|---|---|---|
| Registry | Existing canonical validation accepts the current ACRA-derived entity | Review/technical terminal as typed by the source service |
| Document | Every case-owned pending or reviewed document is semantically safe against current canonical authority; all required fields exist, confidence is `>= REVIEW_CONFIDENCE_THRESHOLD` (default `0.85`), and every conflict has an explicit allowed resolution | Typed document exception for every blocked document with all blocker codes |
| Ownership | Existing deterministic analysis reaches `ANALYZED` under the provisional configured rule | Cycle/incomplete becomes review; provider failure is technical |
| Readiness | Phase 05 server-side readiness returns ready on current evidence | Typed review blocker; no target call |
| Mock target | Phase 05 hardened submission reaches `MOCK_GOLDTIER_SUBMITTED` | Existing party/partial outcome is review; connector/validation/malformed failure is technical |

The four-field profile, confidence threshold, and inclusive ownership threshold remain
project defaults. They are not evidence of a sponsor, vendor, legal, or compliance
policy.

## Human exception policy

An exception contains a case-bound ID, type, stage, primary blocker, all blocker codes,
bounded safe evidence, evidence version, automation version, explanation, and the exact
allowed actions. The browser must not invent actions.

Implemented resolution:

- `KEEP_REGISTRY_VALUE` applies only to a current source-conflict exception. It retains
  original extraction, human-reviewed value, and captured canonical value; a separate
  field-bound journey resolution records the retained registry authority. It increments
  one human intervention and automatically re-evaluates every document. Any independent
  low-confidence/missing blocker remains review-blocking and exposes no action pending
  sponsor policy.

Not implemented:

- accepting a conflicting reviewed/document value as master data;
- approving ownership cycles or incomplete chains;
- selecting or amending an existing GoldTier party;
- treating partial target processing as complete;
- autonomous approval or Ready-for-Approval.

`REQUEST_ADDITIONAL_INFORMATION` is a reserved typed action but is not advertised by
the current server because replacement-evidence workflow semantics are unconfirmed.

## Concurrency, replay, and failure rules

Resolution is compare-and-set: case ID, exception ID, current automation version,
evidence version, and a server-recomputed fingerprint of authoritative canonical and
document evidence must all match. The digest is server-only. A duplicate, stale,
canonical-mutated, forged, or cross-case request cannot advance.
Start/resume returns the accepted checkpoint without replaying completed work. The
orchestration transition count is bounded per invocation.

`REVIEWED` records review lifecycle completion only. A reviewed value that differs from
current canonical authority remains `SOURCE_CONFLICT_REQUIRES_POLICY`/the corresponding
Phase 06 exception because Q-005 is unresolved. Reviewed low-confidence evidence remains
blocked.

Business exceptions and technical failures are distinct. Provider, transport, target
validation, malformed target response, and loop-guard failures never become reviewer
work or completion. Unexpected progression faults terminalize once with a fixed safe
error. Phase 06 performs no blind retries; it re-enters only the typed Phase 05
finalization-recovery path, which uses the retained target outcome without duplicate
target calls. Repeated typed recovery persists nonterminal `RECOVERY_PENDING` rather
than consuming the ordinary progression loop guard. A later start delegates to Phase 05
again and reconciles its actual success, match, failure, or partial-amend outcome.

All guarantees are in-process POC guarantees only.
