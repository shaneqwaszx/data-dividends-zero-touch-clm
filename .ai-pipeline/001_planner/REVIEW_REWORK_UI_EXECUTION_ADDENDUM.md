# Review/Rework UI Follow-up — Execution Addendum

Date: 2026-09-20<br>
Role: bounded implementation clarification<br>
Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`<br>
Branch: `followup/review-rework-ui`<br>
`BASE_SHA`: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`

## Scope and classification

This addendum resolves only the interrupted field-review checkpoint edge authorized by
the governing `REVIEW_REWORK_UI_FOLLOWUP.md` handoff. Change classes remain
`FRONTEND_UI` and `FRONTEND_STATE_CACHE`. `CaseDetail` remains the only mutation,
identity-generation, query-cache, and authoritative-refresh owner.
`DocumentEvidencePanel` owns presentation and ephemeral inline-form state only.

No backend, API, shared type, cache-key, authentication, configuration, dependency,
provider, persistence, business-rule, or architecture owner changes. Strict TDD is not
authorized or required; the posture is test-with-behavior plus focused adverse-path
verification.

## Contract evidence

The current `IDP_REVIEW_CONTRACT.md` and backend owners establish that:

- a review decision is durable before later reconciliation/automation checkpoints;
- an exact repeated final decision is idempotent;
- a different second final decision is rejected with
  `DOCUMENT_FIELD_REVIEW_CONFLICT`;
- only current evidence is reviewable; superseded evidence is rejected before mutation;
- an exact repeat re-enters the existing document checkpoint and does not create a
  second review event; and
- ordinary successful review already performs checkpoint progression, so the browser
  must not issue an additional `/resume` call.

The public `DocumentProcessingRecord` retains the exact typed decision identity needed
for an exact repeat: `field_key`, final `review_status`, raw `reviewed_value`, and raw
`review_note`. No formatted display value or prose is parsed. The public
`ZeroTouchCaseSummary` retains the authoritative automation status/stage. No new API
field such as `is_current_evidence` is required.

## Explicit repair eligibility

The UI may offer `Retry saved review checkpoint` only when all of the following are
true in one authoritative render:

1. the document is current: `superseded_by_document_id` is null or absent;
2. the document state is `REVIEWED` and every field has a non-`PENDING` final decision;
3. the case remains `WAITING_FOR_REVIEW` at the `DOCUMENT` stage; and
4. the selected field itself has one of the existing final decision enums
   `ACCEPTED`, `REJECTED`, or `CORRECTED`; a correction also has a nonblank retained
   `reviewed_value`.

The action is distinct from editing. Final values and notes remain read-only and normal
Accept/Reject/Correct controls remain absent for final fields. Superseded, malformed,
partial, failed, or non-document-stage evidence cannot expose this repair action.

This predicate is deliberately conservative. A case may still have a legitimate
independent blocker after an exact repeat; the control promises only to re-enter the
saved checkpoint, never completion, approval, blocker removal, or target execution.

## Exact request and identity binding

The retry request is constructed directly from the retained typed record, without
normalization or display formatting:

- `field_key` is the retained field enum;
- `decision` is the retained final `review_status` enum;
- `corrected_value` is included only for `CORRECTED` and is the exact retained
  `reviewed_value`;
- `note` is the exact retained `review_note` when non-null.

Before dispatch, `CaseDetail` captures generation, case ID, and actor user ID. It checks
that identity immediately before the request and after every awaited mutation/refresh
step. A result from an old route, case, actor, logout/login generation, or unmounted
component cannot publish cache data, errors, pending state, focus, dialogs, or
navigation. A synchronous ref lock rejects same-tick duplicate submissions before React
can render `disabled`.

## Settlement and authoritative refresh

Normal decisions and exact repair repeats use the existing non-retrying API helper.
They never automatically replay after any error and never call `/resume`.

For a current identity, success, `409`, `503`, and an ambiguous transport failure each
trigger one bounded read-only refresh of case summary, all documents, and ownership.
The three results publish together only after the complete refresh succeeds and the
identity is still current. If refresh fails, the last-confirmed React Query data remains
visible, the UI states that the outcome/evidence reload could not be confirmed, normal
mutation controls remain blocked behind an explicit read-only `Refresh case evidence`
recovery action, and no mutation success or failure is inferred. Existing global 401
session clearing and safe inaccessible-case 404 behavior remain authoritative.

An explicit refresh repeats only GETs. It cannot become a business mutation or blindly
resubmit the saved decision.

## Regression obligations

Focused tests must prove:

- exact accepted/rejected/corrected payload identity and one call;
- no repair action for pending, partial, superseded, malformed, or wrong-stage state;
- final values remain read-only;
- a different second decision cannot be created by the UI;
- successful normal review and successful repair each perform one authoritative
  refresh and no browser `/resume`;
- `409`, `503`, and ambiguous outcomes refresh once without mutation replay;
- mutation failure plus refresh failure preserves last-confirmed data, blocks mutation,
  and exposes only the read-only refresh recovery;
- same-tick duplicate dispatch is rejected;
- stale case/actor generations publish no result; and
- deep-link/remount eligibility is reconstructed only from typed backend responses.

## Complexity and owner fit

`CaseDetail` is already the identity and mutation/cache owner and is under pressure.
The minimum safe edit keeps only wiring, settlement, and generation checks there while
extracting document rendering/form state to the new planner-authorized
`DocumentEvidencePanel`. No second store, query client, fetch owner, mutation retry
policy, workflow owner, or compatibility path is introduced.
