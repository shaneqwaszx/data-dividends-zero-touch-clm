# Bounded GoldTier Sandbox acceptance

This runbook records the current program's single fresh synthetic parent-customer
acceptance. It does not authorize another customer, a repeated mutation, production,
unrelated customer changes, deletion, related-party creation or document transfer.

Use the ordinary case API, strict XPI mapper and existing target ledger. Keep default
Mock tests separate from explicit Sandbox composition. The HR console is read-only;
it cannot dispatch Shell, Policy or Amend independently of a case.

`scripts/run_s3_sandbox_acceptance.py` defaults to offline protocol responses. The
separately authorized external invocation is module-based with `PYTHONPATH=apps/backend`.
It requires an explicit configuration file and a fresh receipt path. Only
GOLDTIER_SANDBOX_BASE_URL, GOLDTIER_SANDBOX_ENVIRONMENT and GOLDTIER_SANDBOX_USER_ID
are consumed internally. Missing or duplicate fields fail with names only. Private
values and credentials are never copied to the browser, documents or receipts. The
private environment file is not edited; process selection explicitly enables Sandbox
writes under the owner's bounded authorization. TLS verification and the existing
no-redirect, bounded transport remain mandatory.

The runner verifies exact accepted S1/S2 gate hashes and current local mapper/ledger
evidence before provider access. It reserves one clearly synthetic legal name/UEN
on disk before Search. A process interruption retains that reservation; do not
delete it to create another identity. Normal authenticated case creation, document
processing, explicit classification, creator-reviewed ownership and the sole Decimal
engine prepare the package. Only the real Search NO_MATCH permits Shell. Ambiguity,
identity mismatch or any genuine preparation blocker stops dependent mutation.

The prepared request is held for independent review. Record an immutable preparation
receipt and exact candidate manifest. Only a fresh independent PRE_MUTATION: PASS on
those bytes can release final Review & Send. The transport reserves each authorized
operation before execution: Search at most twice, Shell at most once, required Policy
at most once, readback at most twice. Current supported parent fields require no Amend,
so the current runner refuses Amend. No name-only identity authorizes reuse.

On success, required operations, exact retained-ID readback, receipt and final
application completion establish Submission confirmed. Policy technical success does
not prove KYC, approval or Ready-for-Approval. On rejection, retain fixed sanitized
failure evidence. On an uncertain mutation, stop all subsequent writes; permit only
bounded read-only identity observation. A customer Search cannot prove an uncertain
Policy succeeded. The browser has no automatic mutation retry. Later independently
verified recovery remains under the existing case/ledger authorization boundary.

The external run uses a newly generated allowlisted disposable physical database in
the owned loopback Mongo container. It never reads or changes original clm_poc records.
Reopen the application and verify documents, reviewed ownership, target operations and
submission state without new provider calls. Preserve unresolved-attempt evidence
until owner review; clean only identified task resources when no retained uncertainty
would be lost. Do not delete an external customer as cleanup.

The [field inventory](../integration/ONBOARDING_INTELLIGENCE_S3_FIELD_MATRIX.md) separates
canonical/document business data, explicit policy, application bindings and provider
IDs. Related-party child acquisition/binding remains unsupported. The six current XPI
operations expose no original-document upload endpoint. Retained ownership and
structured document fields do not imply external RP objects or original-file transfer.

Actual acceptance receipts and the final independent gate determine whether this
program establishes external delivery or EXTERNAL_DEPENDENCY_BLOCKED. Offline browser
and unit success alone cannot establish it. No commit, push, PR or merge is authorized.

On 2026-10-04 the reserved synthetic case completed the authorized actual attempt:
Search2/Shell1/Policy1/Amend0/readback1, all dispatched calls HTTP200; retained customer
143887, POLICY_CREATED, same-ID VERIFIED readback and SUBMISSION_CONFIRMED. Restart
preserved documents, reviewed ownership and target state with no new calls. The receipt
and durable proof are archived under ONBOARDING_INTELLIGENCE_S3_* reports. The receipt
path remains reserved: do not rerun this command, delete the reservation or create a
second customer. Resource cleanup is local/disposable only; external deletion is not
authorized. Final combined review remains a separate gate.
