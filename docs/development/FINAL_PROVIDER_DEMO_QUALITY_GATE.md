# Final provider demo independent Quality Gate

Date: 2026-10-01. Independent reviewer; no implementation role.

**Overall verdict: FAIL.** Required external GoldTier submission acceptance is not
proved: the one authorized Shell transport attempt timed out, leaving an unresolved
durable operation. It is neither confirmed creation success nor confirmed absence
of provider-side creation. No local fix or offline test can substitute that evidence.

| Reviewed scope | Verdict |
|---|---|
| Local implementation | PASS; no remaining reproducible in-scope defect found |
| Fresh sanitized contract | PASS; historical incident FAIL remains preserved |
| Pre-mutation prerequisites and actual stopping/no-replay safety | PASS |
| Fresh actual ACRA Garden same-case acceptance | PASS, Local Mock target |
| External GoldTier full POC submission | FAIL / BLOCKED, unresolved Shell |
| Normal demo | PARTIAL |
| Publication / Production / Live | Not authorized / not claimed |

## Exact frozen review

Branch `fix/demo-happy-path-stabilization`; base, HEAD and local `origin/main`
`efc31f450f0103766fa812bc0aa80754f801dbe9`; index empty. No remote freshness claim.

Final reviewed manifest: `tmp/FINAL_PROVIDER_FINAL_REVIEW_MANIFEST.json`, 105 paths,
SHA256 `682688c67d83e3d6d1ce1d9fa759391d3a581142217df0c2ba517fb3a791b9a1`.
Source/harness V3: 86 paths,
`ac1bdbfd1bc344d0f609c5bbfaeadf0642fd24740346d79c4914db387ff4141d`.
Source/evidence freeze: 103 paths,
`b4f0ff802eb019e851efcffaf6624295f995bfabc7f0d4150011003180b52d71`.
All three raw path maps independently matched before and after review: zero drift.
The final acceptance report is included in the 105-path freeze. This gate is excluded.
Prior reports/manifests remain unchanged.

Reviewed authority: current user continuation
`23695e14-88d1-40c6-b3c3-6add6e9479ac`, repository guidance, independent quality/security
review workflow, current owning source/tests, sanitized contract, acceptance plan,
exact pre-mutation PASS, frozen payloads, final report and external/runtime receipts.
No private original/PDF/authentication value or `.env` was reopened.

## Actual GoldTier result and safety

Target case `9d9c2542-5dfa-4343-bc73-2f65126b4a2c`; submission
`b26fdb74-6b81-4b0d-ae55-e22d80d05163`. This is a separate visibly synthetic customer
with Local Mock source evidence; it is not Garden or the actual ACRA case.

The exact pre-mutation approval binds V3 and report SHA256
`52d9a072b4974bd1618906de73527ef3e437ebf277024cd9cb41426e2aa71a7a`.
That binding was independently verified. One initial Search returned HTTP 200
NO_MATCH; one Shell attempted normal transport after PASS. The recorded exception
and connector timeout branch support `GoldTierMutationOutcomeUncertainError`.
No confirmed Shell HTTP response or provider-issued ID was retained. The timeout
does not establish which network/provider component failed or whether creation applied.

Actual budget: SEARCH 1, SHELL 1, POLICY 0, AMEND 0, READBACK 0. Related-party,
Garden, Production/PingFed and deletion calls are zero. Initial Search and Shell
allowances are consumed. Policy, successful-Shell restart proof, KYC initiation and
readback were not executed. Although this zero-enrichment case planned
`AMEND_NOT_REQUIRED`, the skip stage was never reached; its actual amend status is null.

Independent read of only the receipt-owned active loopback Mongo7/generated
`clm_p12_*` database confirms the exact main case remains VALIDATED and its ledger:

- IN_PROGRESS; attempted SEARCH,SHELL; completed/resolved SEARCH only.
- No resolved provider ID, Shell/Policy/Amend success status, terminal outcome or receipt.
- The unresolved Shell history remains retained after the application process exited.

Independent additional execution used the normal owning onboarding service with the
existing Mongo repositories, explicit dotenv-disabled settings, writes disabled and
an inert transport that rejects any request. It raised MutationOutcomeUncertainError
before transport: zero calls and exact durable document unchanged. Mongo store
initialization, administration bootstrap and index creation were deliberately not
invoked. The first settings-only invocation lacked the explicit nonsecret environment
and failed locally; the corrected explicit configuration completed this proof.

The actual stopping behavior matches the reviewed one-intent/one-dispatch/no-blind-replay
design. No subsequent write, fallback, retry, code change to overcome the timeout or
external cleanup occurred. Missing upstream XPI idempotency is not invented or borrowed
from EDS. The retained service must preserve the unresolved ledger, not be discarded
as ordinary test cleanup.

## Actual ACRA same-case result

Session `3a0a3bbf6fae4cfb`, exact case
`42fa93fe-8e44-4b9d-bc25-6b5536cdeb6a`, Garden `11111999A`.
Receipt, browser checkpoints and owning harness show actual certificate-verifying
HTTP transport, post-auth dispatch guard and bounded exact operation/query allowlist:
token 1, entityBasicInformation 2, coShareholdersDetails 1, all HTTP 200; other registry
operations and external GoldTier calls zero. This session is actual official API
Marketplace Mock, not replay or Live registry evidence.

The same case proceeds through actual registry acquisition, real synthetic client PDF,
four accepted document fields, document version 9/REVIEWED, KEEP_REGISTRY_VALUE
reconciliation, document/version-bound USER_SUPPLIED_DECLARATION, existing Decimal
ownership/UBO logic with inclusive >=25%, classification, Review & Send and explicit
Local Mock confirmation. The completed case has no active blockers, unchanged
canonical registry identity and exact case-ID links in Cases and Onboarded. It does
not imply that the separate GoldTier synthetic customer completed.

Underlying acquisition remains PARTIAL: one entity, four officers, empty ownership
and unsupported relationships. Officers were reviewed only as counts, not records.
The workflow's completed registry-identity stage is not complete ownership evidence.
The supplementary 60/40 interests and two provisional candidates are Local reviewed
declaration evidence, not ACRA ownership or a legal/controller determination.

All six exact-session Review & Send images were independently inspected at
360/768/1280/1440/1920 widths and 200% CSS zoom. Mobile and zoom captures were also
viewed at original detail. Content stacks/wraps, confirmation remains visible,
Local Mock destination and evidence limitations remain explicit, and no reproducible
clipping/overlap was found. Harness scroll-extent assertions support no horizontal
overflow. This proves CSS content zoom, not native browser-chrome zoom. Screenshot
scope is Review & Send and excludes officer records; no broader visual claim follows.

The Partnership/KYC-type advisory remains visible, non-blocking and truthful about
unknown project/sponsor compatibility. No business incompatibility or approval rule
was invented to force this case through.

## Local implementation and verification

Source V3 is unchanged from the independently reviewed pre-mutation candidate.
Conditional Amend remains in both target executors, valid no-Amend ledger prefixes
retain historical decoding, the mapper/preview omits unneeded Amend, and readback
compares every safe available identity field with exact retained ID. Shell/Policy
uncertainty remains fail-closed. Completion language separates Sandbox submission
and documented KYC initiation from KYC completion, screening clearance, risk approval,
Ready-for-Approval, regulatory approval and Production onboarding.

Same-byte independently executed evidence retained: XPI 102 PASS, strict configured
mypy 112 PASS, exact frozen Shell/preview/Policy provenance PASS, pre-mutation active
Mongo retention read PASS. This final gate independently adds exact uncertain-ledger
read/no-dispatch proof, manifest/approval binding checks and actual-session receipt,
harness/checkpoint/screenshot inspection. No ceremonial broad rerun or new provider
session was performed.

Coordinator frozen local evidence remains backend 1,513 PASS, 38 physical opt-in skips,
zero failures/errors; contracts 44 PASS; frontend 382 PASS; offline Garden browser 5
PASS; tooling 134 PASS; Ruff, strict mypy, type/build, policy, architecture, provider
readiness and ordinary hygiene PASS. Separate retained physical Mongo 38/38 PASS
is distinct from ordinary skips and the additional active acceptance runtime proof.
No repository/CAS/envelope/physical-runner source change requires another physical run.
The pre-existing project-state historical-main ancestry failure remains separately
reported; it was not refreshed arbitrarily or counted as PASS.

## Hygiene and remaining blocker

Explicit scan of the 105 frozen paths found one sensitive-assignment flag in the
task-owned Garden harness: an ephemeral `secrets.token_urlsafe` password generator.
It is runtime generation, not a persisted credential value. The source and sanitized
receipts contain no literal generated password/token/hash. The flag is adjudicated,
not suppressed or rewritten. Explicit text whitespace checks, including task-owned
new Markdown, passed. Historical private example-header incident remains disclosed;
this continuation does not certify that earlier session as zero exposure.

No reproducible in-scope local defect remains. The required external acceptance
blocker is unresolved Shell application, with no retained provider ID. Safe future
progress requires separately authorized read-only provider recovery for this exact
intent and authoritative identity evidence; do not replay Shell, create another
customer, infer unapplied state from timeout, dispatch Policy/Amend, delete an external
record or discard the acceptance database. This gate makes no new provider-call
authorization and no publication authorization.

Only this assigned report was written. Reviewer made no external provider call,
normal Atlas access, Mongo mutation, Docker operation or source/configuration/Git edit.
Overall FAIL preserves the successful local/safety/ACRA evidence while accurately
withholding the unproved GoldTier lifecycle acceptance.
