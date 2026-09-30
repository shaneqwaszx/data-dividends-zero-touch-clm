# Recoverable Onboarding and Final Review - Evidence

- Pre-flight Git baseline: `3d6e7b560b8062daeb93c31cf91b0df957797e9c` for HEAD,
  fetched `origin/main`, and merge base; clean before branch/work records.
- Model/profile: `gpt-5.6-sol`; reasoning `high`; repository workflow
  `fyp-phase-execution`.
- Runtime preflight: Python 3.12.10, Node 22.23.3, npm 10.9.9; Mongo mode configured
  and reachable; ACRA `api_marketplace_mock`; GoldTier `sandbox`.
- Provider requests: ACRA 12/12 authorized operation reads; GoldTier Search 4/6;
  provider writes 0. The official connector performed entity, officer, and shareholder
  reads for Garden, OPQ, and RRR. All three identities/addresses/officer sets matched the
  documented samples; all three returned zero ownership parties/percentages. OPQ and RRR
  currently map to `UNKNOWN` entity type, and LLP Highlights is not implemented.
- Honest sample classification: Garden `PROFILE_VERIFIED` for basic profile only;
  OPQ and RRR `NOT_HAPPY_PATH_READY`; no entirely-official complete profile/evidence set
  and no two additional happy paths were proved.
- GoldTier read-only Search outcomes with a process-scoped
  `GOLDTIER_SANDBOX_ALLOW_WRITES=false` safety override: Garden returned one exact-name
  candidate but remained `REVIEW_REQUIRED` because Search did not prove registration
  identity/jurisdiction; OPQ and RRR returned `NO_MATCH`. The first safety check found
  writes enabled and aborted before any request. The single ignored local setting
  `GOLDTIER_SANDBOX_ALLOW_WRITES` was then changed to `false` without reading or printing
  any other `.env` value, and `Settings` validation passed. Any running backend must be
  restarted to load that change.
- The final composed disposable Garden smoke asserted official ACRA Mock, GoldTier
  Sandbox, in-memory persistence, and writes disabled; `create_staged_case` returned only
  after one Search plus the three registry reads. Its reporting expression then accessed
  obsolete `target_search_checkpoint` instead of `initial_target_search`, so the process
  exited nonzero after the reads. It was not retried because ACRA had reached 12/12. This
  is recorded as bounded external-read evidence with a harness-output failure, not as a
  clean configured-smoke PASS.
- Backend pre-gate evidence: 1,555 collected = 1,518 passed and 37 expected skips, 0 failed;
  exact-preview/orchestration/Garden 87/87; Ruff passed; mypy passed for 112 files;
  compileall passed. Contract tests passed 44/44. Architecture, project-state,
  policy-authority, provider-readiness, secret, and diff checks passed.
- Physical Mongo: the focused schema-v7 restart/identity-repair/pending-confirmation guard
  passed 1/1 in 63.50s against a generated allowlisted disposable database. Two earlier
  full-suite processes also exited, but their wrapper output was lost and is not claimed.
- Frontend final evidence: focused 37/37 and full 31 files/364 tests passed; typecheck and
  production build passed; focused Playwright ordinary-RM journey passed 1/1 in 7.4s.
  Existing non-failing React SSR/`act` warnings remain.
- Browser evidence: 320/360 default, hover, keyboard-focus and context captures plus the
  1440 final review were inspected. The current PDF is Chromium-generated A4, six
  meaningful pages, and all pages were rendered and inspected for readable wrapping,
  operations, provenance, warnings, and unclipped page numbers.
- Final review exposes exact Mock Search/Shell/Policy/Amend DTO fields. Confirmation was
  enabled but not clicked; no target mutation was made. DTO parity, material-preview
  invalidation, confirmation-time Search recheck, canonical drift, and zero-write tests
  passed.
- UI source inspection proved no retained identity form/final review/ACRA console and
  found duplicate registry focus plus failing static tile-hover contrast.
- Provider source/sample inspection proved current supported operations and documented
  sample IDs without printing raw payloads or secrets.
- Fresh independent Quality Gate evidence will be appended only after it is executed
  against the frozen current content.

## First independent gate and remediation

- First gate report: `.ai-pipeline/reports/RECOVERABLE_ONBOARDING_FINAL_REVIEW_QUALITY_GATE.md`,
  verdict `FAIL`, frozen-content SHA-256
  `283e3757f3eb10641ae657bdb6cf0887b966ea4ed8c3c864686b9c1a707e2eb3`.
- QG-001 HIGH reproduced a concrete `sourceContext.acceptedAt` mismatch between the
  displayed preview and later snapshot while the digest excluded that field. The probe
  made only `search,search`; writes remained zero.
- Remediation uses `case.created_at` as the stable case-acceptance timestamp for both
  request preview and immutable dispatch snapshot and includes every preview field in
  the digest. The new value-for-value parity test proves the mapper preview derived from
  the snapshot equals the displayed review, including `acceptedAt`, before any write.
- Post-repair backend: focused parity/confirmation/drift/recheck 4/4; orchestration plus
  Garden 88/88; full suite 1,556 collected = 1,519 passed, 37 expected skips, 0 failed;
  Ruff, strict mypy (112 files), and compileall passed.
- Post-repair physical Mongo: schema-v7 restart/identity-repair/pending-confirmation
  guard 1/1 passed in 71.40s against a fresh generated allowlisted disposable database.
- Post-repair browser: ordinary-RM UI journey 1/1 passed in 7.3s; it regenerated the
  current six-page A4 PDF and screenshots without clicking confirmation or performing
  target writes. All six pages were rendered and inspected again. The unchanged
  frontend source was also revalidated: 31 files/364 tests, typecheck, and production
  build passed; the existing non-failing React SSR/`act` warnings remain.
- QG-002 LOW was remediated by removing the two explicit stale untracked render
  directories. Only current screenshots and `review-and-send-a4.pdf` remain under the
  operator-route artifact directory.
- A fresh independent re-gate on the changed bytes is pending. The failed report is
  preserved and will not be overwritten.

## Second independent gate and remediation

- Second gate report:
  `.ai-pipeline/reports/RECOVERABLE_ONBOARDING_FINAL_REVIEW_QUALITY_REGATE.md`,
  verdict `FAIL`, frozen-content SHA-256
  `c4f8a0fcb5a44b92019df2fb52af7563985751351d9a10b49899b4584b0e1de0`.
  It independently closed first-gate QG-001 and QG-002.
- QRG-001 HIGH found that the final review omitted legal form and owning team and had no
  section-level edit controls. Its component coverage also did not assert those required
  fields or controls.
- Remediation adds legal form and owning team to the server-backed review, gives identity,
  classification, documents, and ownership explicit section actions, and routes each to
  its existing real correction/review owner. Edit actions disappear after confirmation.
  Identity remains editable on the same unconfirmed pre-submission case; the backend
  reruns bounded read-only Search, cancels the stale confirmation decision, invalidates
  dependent evidence, and still performs zero Shell/Policy/Amend calls.
- Post-remediation focused evidence: backend confirmation/identity-edit 2/2; Review and
  Send component 10/10. Full backend is 1,557 collected = 1,520 passed and 37 expected
  skips, 0 failed; full frontend is 31 files/364 tests. Ruff, strict mypy (112 files),
  compileall, frontend typecheck/build (124 modules), contracts 44/44, project-state,
  architecture, policy-authority, provider-readiness, tooling, and secret checks pass.
- The schema-v7 physical restart/identity-repair/pending-confirmation guard passed 1/1
  in 70.07s against a fresh generated allowlisted disposable Mongo database.
- The ordinary-RM Playwright journey passed 1/1 in 11.3s after checking all four edit
  actions focus their real owners. It regenerated a review-only screenshot, the complete
  1440 journey, and the six-page A4 PDF without clicking confirmation or making a target
  write. The latest review screenshot and every PDF page were visually inspected; legal
  form, owning team, exact Search/Shell/Policy/Amend fields, warnings, provenance, and
  unclipped page numbers are visible.
- A third fresh independent gate on these changed bytes is pending. Both earlier failed
  reports remain immutable.

## Third independent gate and remediation

- Third gate report:
  `.ai-pipeline/reports/RECOVERABLE_ONBOARDING_FINAL_REVIEW_QUALITY_REGATE_2.md`,
  verdict `FAIL`, frozen-content SHA-256
  `ac7332c36bf007f6281a9100a93508c71d77a0b00e62db1f303fda011e0328c4`.
  It independently closed both earlier gate cycles.
- QRG2-001 HIGH found that `Edit ownership` was rendered for every editable review but
  only focused the read-only ownership explorer. The review now derives this affordance
  from the server-authored `manual_evidence_action`: authorized cases focus the real
  manual-evidence form and its submit action, while ordinary cases show an explicit
  review-only explanation and no ownership edit control.
- QRG2-002 LOW found that the retained 360px default and hover captures inherited focus
  from the preceding 320px keyboard capture. Artifact generation now blurs the active
  element and moves the pointer before every viewport's default capture, so default,
  hover, and focus evidence are distinct.
- Post-remediation frontend evidence: Review and Send 11/11; full frontend 31 files and
  365/365 tests; typecheck; production build with 124 modules; focused ownership backend
  regression 22/22; and the two coherent ordinary/authorized Playwright journeys 2/2.
  The existing non-failing React SSR/`act` warnings remain.
- The regenerated Chromium PDF remains six A4 pages. All six pages were rendered and
  inspected; the review-only ownership explanation, legal form, owning team, exact
  target operations, warnings, provenance, and page numbers are readable and unclipped.
  Responsive 360px default/hover/focus evidence was also visually inspected and is now
  distinct.
- A fourth fresh independent gate on these changed bytes is pending. All three earlier
  failed reports remain immutable.
