# Recoverable Onboarding and Final Review - Reflection

## Pre-gate reflection

The implementation now covers the requested local recovery, independent-evidence,
classification, manual-ownership, HR-diagnostic, final-review, confirmation, and
responsive-operator paths. The most important late correction came from rendered
evidence: the first Mock final review showed Search only even though dispatch would also
send Shell, Policy, and Amend. The mapper now derives the review from those actual DTOs,
and the confirmation digest binds the material preview. This confirms why visual and
contract-level inspection were both necessary.

The external evidence remains deliberately narrower than local implementation evidence.
Official Mock reads did not prove two complete alternative happy paths, no Garden upload
pack or supplied screenshots were present, and no GoldTier business mutation was
authorized or executed. The final configured read used the remaining ACRA budget and
completed case construction, but its reporting expression failed afterward; it is not a
clean smoke result and was not retried.

Completion authority remains with a fresh independent Quality Gate on the exact frozen
bytes. Any remediation changes will require affected re-verification and a fresh gate.

## First-gate lesson

The first independent gate found that operation presence and mapper-DTO parity were not
enough: the preview and immutable snapshot were built from different timestamps, and an
exclusion in the digest hid that difference. The repair establishes one stable source
for that transmitted value and tests preview-to-snapshot equality directly. This is the
kind of authorization-integrity defect that broad green suites and a visually correct
PDF can miss unless the reviewer compares the reviewed bytes with the actual retained
dispatch input.

## Second-gate lesson

The second reviewer confirmed the authorization-integrity repair but caught a product
acceptance gap in the visible handoff surface: exact target DTOs are insufficient when
the operator cannot see required case identity context or reach the real correction
owners from final review. The remediation keeps those controls as navigation into the
existing backend-validated owners rather than creating frontend-only edits. The added
same-case final-review identity test is intentionally adverse: changing identity
cancels the stale confirmation decision, reruns only Search, exposes the resulting
document conflicts, and proves that Shell, Policy, and Amend remain unattempted.

This reinforces that independent re-gates are not duplicate ceremony. The first gate
found a reviewed-bytes/digest flaw; the second found an operator-completeness flaw. A
third reviewer must now assess the exact combined remediation without inheriting either
implementation path.

## Third-gate lesson

The third reviewer separated visible navigation from an authorized recovery action.
Merely focusing a related section did not make `Edit ownership` truthful: the ordinary
case had no server-authorized ownership mutation. The correction now treats the typed
recovery projection as the affordance contract, directs an authorized action to the
actual manual-evidence form, and otherwise states the review-only limit. The paired
browser tests deliberately prove both halves. The same review also showed why visual
evidence must reset interaction state between viewports; default, hover, and focus
captures are useful only when each begins from a controlled state. A fourth independent
review must assess these changed bytes.
