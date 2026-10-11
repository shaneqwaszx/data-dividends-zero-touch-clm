# Garden UEN correction and PARTIAL workflow resume

Hotfix candidate from origin/main `40c530dde5edc0c714beae764fc760c741a5fdbf`.
The intended identity is GARDEN BUSINESS / `11111999A`.

A faithful offline reproduction uses the strict Marketplace Mock Garden partnership
contract, local document extraction and XPI Sandbox Search with a name-only existing
candidate. Correcting a wrong UEN returned HTTP200 with PARTIAL registry evidence,
but automation remained WAITING_FOR_REVIEW / REGISTRY with obsolete
ACRA_ENTITY_NOT_FOUND. Original/corrected UEN selection and stale request versions
were not the cause in that reproduction. Actual external UAT is not claimed.

The correction acquired registry evidence before Search. Search review changed the
aggregate case state to REVIEW_REQUIRED; unlike normal creation, correction did not
rebind verified registry evidence afterwards. Existing orchestration therefore retained
the obsolete registry blocker. The repair reuses the already verified bundle through
the existing acquisition/validation path after Search, including review/failure.
It makes no additional ACRA fetch and keeps genuine PARTIAL operation statuses.
The CLM recheck checkpoint now emits GT_SEARCH_IDENTITY_REVIEW_REQUIRED for its
review disposition while preserving the provider's MATCH_FOUND outcome separately.

On the same case, select the document-detected UEN or choose Enter another UEN,
enter `11111999A`, and choose Verify UEN and resume. Original entered UEN and current
corrected UEN are labelled separately. Use entered UEN always selects the currently
retained case identity, not an unsaved input or superseded history. If the original
entered UEN is incorrect, selecting it still fails registry verification safely.

The original document ID, extraction values and provenance are retained. Superseded
registry blockers remain CANCELLED history. NO_MATCH can continue to normal evidence
and readiness actions. A singleton incomplete XPI identity remains a genuine Search
review with the existing authorized customer-confirmation action; document disagreement
and other genuine evidence gaps retain their own correction paths. This hotfix does not
confirm a customer or send a target package on the user's behalf.

API/request types, schemas, provider interfaces/statuses, configuration, mappings,
authorization, business/ownership rules and architecture remain unchanged. Runtime
correction ordering and presentation change inside existing owners. Creator, team,
lock/CAS/currentness, document-version, freeze and target-ledger safeguards remain.
Tests use offline allowlisted transports; no private dotenv or external writes.
Physical Mongo evidence uses generated disposable databases on a task-owned container.
Independent gate and publication evidence are recorded separately under
`.ai-pipeline/reports/GARDEN_UEN_PARTIAL_RESUME_QUALITY_GATE.md`.
