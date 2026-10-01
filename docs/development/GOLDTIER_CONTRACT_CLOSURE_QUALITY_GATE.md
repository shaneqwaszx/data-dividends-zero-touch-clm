# GoldTier contract closure independent Quality Gate

Date: 2026-10-01. Independent reviewer; no implementation role or source fixes.

## Exact verdicts

- **CONTRACT / AUTH / FIELD GATE: FAIL.** The technical contract, authentication and field conclusions pass for the sanitized frozen candidate. The session-wide names-only inspection requirement was not fully met: an earlier reviewer PDF filter emitted an example `user_id` header value. This report does not repeat that value or certify zero private-value exposure.
- **LOCAL IMPLEMENTATION GATE: PASS.** The two bounded source remediations are correct, focused independent checks pass, and no remaining reproducible in-scope local defect was found.
- **PRE-MUTATION AUTHORIZING GATE: NOT RUN.** Required prerequisites remain unresolved or failed; no external write is authorized by this review.
- **COMPLETE PROVIDER / DEMO ACCEPTANCE: FAIL / BLOCKED.** Active durable lifecycle ownership, specific screening ownership, conditional Singapore Amend acceptance, meaningful Policy/Amend readback and exact network Garden completion remain unproved.

These results distinguish the local candidate from the broader requested acceptance. A local PASS does not authorize publication, a provider write, another read, a new ACRA session or Production/Live claims.

## Frozen content and authority

Branch: `fix/demo-happy-path-stabilization`. Base, HEAD and local `origin/main`:
`efc31f450f0103766fa812bc0aa80754f801dbe9`. Index empty; no Git mutations or remote freshness claim.

Reviewed source/report manifest: `tmp/GOLDTIER_CLOSURE_SOURCE_MANIFEST.json`, 64 paths,
SHA256 `349b4609c63c3894dc425a0f3dde0290479d4dbc5c98d720365b3e782d8636e0`.
Exactly five delta paths versus the preceding independently reviewed overnight candidate:

- `apps/backend/app/connectors/goldtier_xpi.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/tests/test_goldtier_xpi_sandbox.py`
- `docs/integration/GOLDTIER_CURRENT_CONTRACT_AND_SCREENING_RECONCILIATION.md`
- `docs/development/GOLDTIER_CONTRACT_CLOSURE_AND_DEMO_PROVIDER_READINESS.md`

New evidence manifest: `tmp/GOLDTIER_CLOSURE_EVIDENCE_MANIFEST.json`, three paths,
SHA256 `5ff0ddeecf050cbd9973f953500dc6114672d79d25673c3841e3554dd0f500d3`.
Retained overnight evidence: 62 paths,
SHA256 `db4c2dff77a928dc5a908daacced282bd708f344d9804290491f1e0f01c26466`.
All applicable hashes were independently checked before and after this report; no drift.
This gate report is excluded from the source freeze. Prior gates remain unchanged.

Execution was bound to source digest
`b3002c4ad9a3a3a0226abf4748a9d8b9bbd03d0aaede2926bf699bee509a3cdd`.
The coordinator subsequently updated only the closure report's results/verdict text.
That documentation delta was freshly read and independently reviewed; no runtime,
test or configuration byte changed. Evidence explicitly identifies both tested and
current candidates rather than claiming that checks executed after the report edit.
Replacing only the current closure-report hash with its recorded tested hash
`ea9f44e3bc9e455ac4a1d702851e8b9f96eda2eb1816a953ddea569e72ef98e5`
independently recomputed the exact tested `b3002c4...` digest. This verifies the
documentation-only transfer across the complete 64-path map.

Authority: current user attachment `b9015a2c-d041-4efa-a347-41d77997f3c4`, repository instructions,
the independent Quality Gate skill, current synchronized contracts/decisions, owning
source/tests, and the original-artifact structural reconciliation. The user permits
structural inspection of historical quarantined material, not credential reuse or
transferring historical examples into current mappings.

## Contract, authentication and fields

Both explicit private directories were inventoried. The newer guideline and collection
hashes match the existing current XPI mapping record. Independent structural inspection
confirms direct `/{Env}/gt-xpi/v1` customer Search/Shell/Policy/Amend paths, request-level
Postman `noauth`, and the `user_id` header name. The older PingFed collection instead
uses ANZ `/insto/oacb/gt-*-api` gateway paths, token/Bearer machinery and additional
gateway header names. It does not establish an additional Bearer requirement on the
working direct Sandbox route. Its deployment currency and Production applicability
remain unproved.

The EDS originals independently contain `/v1/eds`, OAuth2, `sourceContext` and
`Idempotency-Key`. Their distinct dialect and replay guarantees do not extend XPI.
No direct-to-EDS migration, extra token flow, invented header, write retry or provider
composition was introduced.

The newer guideline explicitly states that Policy initiates GoldTier KYC activity.
That is not KYC completion, approval, activation or proof of individual screening
execution. Current XPI customer input structures contain no PEP, sanctions,
adverse-media, risk-rating, wealth or funds fields. Their absence is accurately
classified `NOT_IN_CURRENT_XPI_CONTRACT`; specific downstream screening ownership
remains UNRESOLVED. The frozen report now preserves that distinction in prerequisite 6.

Shell minima, Policy minima and Amend identity/policy minima are source-backed.
Example-only contact/address/group/relationship-manager fields are not promoted to
mandatory inputs. ANZSIC/GCN conditional Amend behavior remains unresolved; the prior
Singapore validation failure supplies no missing-field rule. No SSIC conversion,
default industry, guessed vocabulary or duplicate local compliance workflow was added.
Existing address controls and external references are explicitly separated from
sponsor minima. Current DTO, mapper and preview retain canonical evidence and reviewed
policy provenance; no direct ACRA-to-target mapping was found.

The workbook is supporting historical/derived evidence, not an original approved
current-XPI requiredness contract. Its assisted provenance and reference to missing
`GT_DataMapping_ANZ.xlsx` are accurately disclosed. Independent bundled-openpyxl audit
verified the original workbook SHA256, all eight sheets, 112 metadata rows and 1,117
stored cell projections against their original coordinates: zero mismatches. Only
safe metadata/counts were emitted by that audit.

## Source remediation and adverse paths

The original mutation decoder treated every non-200 HTTP status as definitive
validation failure, although current XPI supplies no atomic no-application guarantee
for unexpected statuses. The new guard preserves mutation uncertainty outside the
existing documented 200/400 boundary. Independent tests cover Shell, Policy and Amend
at 302/500/503: exact attempted prefix, IN_PROGRESS retention, subsequent-write
stopping and replay rejection. HTTP 400 remains controlled validation rejection; this
does not grant retry permission or certify upstream rollback.

The identity reconstruction guard now requires a non-null canonical legal name before
building a strict prior identity. Independent memory-only exercise with both prior
identity and canonical name absent reaches the intended controlled not-editable
ValueError and retains the absent identity. It does not manufacture evidence or bypass
eligibility/locking. The explicit incomplete-identity repair path remains supported.

No persistence/schema/CAS/runner owner changed. Existing ledger intent/attempt markers,
lock/CAS, uncertainty stopping, no blind replay and read-only recovery remain the
local safety design. Absence of documented upstream XPI idempotency is not treated as
automatically fatal under the latest user instruction. An active authorized durable
runtime still must own the actual external lifecycle before mutation acceptance.

## Verification

Independent current frozen-content execution:

| Check | Result |
|---|---|
| Focused XPI mapper/connection/preview/identity/mutation plus orchestration identity selection | 29 PASS |
| Unexpected mutation HTTP status cases | 9 PASS; included in the 29, not additional unique tests |
| Nullable prior-identity controlled rejection | PASS, inert memory-only exercise |
| Configured strict mypy, `--no-incremental`, OS-temp cache | PASS, 112 source files |
| Canonical secret scanner across explicit 64 source paths | Zero findings |
| Explicit text whitespace including untracked Markdown | Zero issues |
| Source/evidence manifest checks | Zero differing paths |

The first mypy invocation used Windows `NUL` as cache directory and produced a tool
internal error; directing cache to OS temp passed without source changes. The secret
scanner's first dynamic-import invocation also failed locally; normal module import
completed successfully. Neither failed invocation is represented as passing evidence.

Coordinator evidence independently checked against the frozen manifest and JUnit:
1,541 backend cases collected, 1,503 PASS, 38 physical opt-in skips, zero errors/failures.
Contracts 44 PASS; XPI suite 92 PASS; Ruff, architecture, external-provider readiness,
configured strict mypy and ordinary secret/whitespace checks PASS. The ordinary backend
run disables dotenv, selects memory/mock and forbids Mongo construction.

Retained unchanged evidence: frontend 381 PASS, five configured offline Garden browser
paths PASS, typecheck/build PASS and separate physical Mongo 38/38 PASS. Those physical
passes do not convert the ordinary 38 skips into executions and do not establish an
active target-acceptance database. No physical rerun was required by the unchanged
persistence boundaries. Previous independent screenshot/browser findings remain resolved.

The project-state checker still fails its pre-existing historical verified-main
ancestry condition. No fetch or invented snapshot refresh was performed. This is
pre-existing governance, separately recorded rather than counted as a current product
defect or falsely reported PASS.

## Security and remaining acceptance limits

The PDF filter incident exposed an example authentication-related identifier value in
tool output. It was reported promptly and not repeated in this report or copied into
tracked/evidence artifacts. Later private reads used name/structure projection.
No token, client secret, password or customer payload was emitted by the reviewed
structural outputs; historical credentials were not reused. This does not erase the
names-only violation or justify a session-wide zero-exposure claim. It is the reason
the complete CONTRACT / AUTH / FIELD gate is FAIL despite passing technical conclusions.

Frozen candidate/evidence artifacts are sanitized. TLS certificate verification,
TLS 1.3, disabled redirects, bounded timeout/body, backend-only metadata, write opt-in,
no Sandbox Mock fallback and safe public errors remain intact. Reviewer made no
external call, accessed no `.env`/Atlas/database, ran no Docker, changed no source and
performed no Git mutation. No provider budget or write authorization was inferred.

Required external limits remain:

- Specific downstream screening ownership is unresolved; input absence is proved.
- Active durable acceptance ledger is not established.
- Singapore Amend conditional acceptance remains unresolved.
- Same-ID Search readback proves identity existence, not Policy/Amend business state.
- A fresh synthetic durable case/allowlist and required reviewed inputs are not bound
  to an accepted external lifecycle plan.
- Exact same-case network ACRA Garden completion remains unproved and no fresh session
  authority exists. Captured replay is not substitute network evidence.

No newly reproducible local product defect remains. The safe next action is to resolve
these factual prerequisites and obtain the separately required authority/evidence;
until then, stop external mutation. No publication or subsequent phase is authorized.
