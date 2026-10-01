# Official Garden Evidence — Independent Quality Gate

Date: 2026-10-01 (Asia/Singapore). Exact verdict: **FAIL**.

Current official ACRA Marketplace Mock acquisition is **VERIFIED**. The original
network-backed browser journey did not complete. A subsequent local replay of the
captured normalized entity completed with explicit confirmation to local Mock
GoldTier; officer data was deliberately omitted. Physical Mongo remains pending.
No new application defect was established in this evidence-completion review.

## Reviewed identity and authority

Independent reviewer had no implementation role. Authority is the explicit user
request in attachment `f2871954-0de1-4bf7-8489-1a6d8e587474/Pasted text.txt`, repository
AGENTS instructions and the `fyp-quality-gate`, external-provider integration and
integration-security review workflows. Prior Garden gates remain unchanged.

| Item | Frozen identity |
| --- | --- |
| Branch | `fix/demo-happy-path-stabilization` |
| Base / HEAD / local origin/main | `efc31f450f0103766fa812bc0aa80754f801dbe9` |
| Implementation | 46 paths; `3cc6d9bd753b825450e9618a4e9f7b44604cc0bc12debf1ea6079a2bfed17a5b` |
| Evidence | Seven receipt/harness paths; `a23a331a8133c2a99c6c4c90c8e8b8166021ce1acdfc0113c2da0881cd86f41e` |
| Path inventories | `tmp/GARDEN_REVIEW_MANIFEST.json`; `tmp/OFFICIAL_GARDEN_EVIDENCE_MANIFEST.json` |
| Git state | Intentional task-owned uncommitted changes; index empty |

Both inventories and every constituent hash matched before and after this review.
No source, contract, instruction, configuration or test change occurred in this
continuation. Reporting files are outside the implementation identity. This reviewer
performed no external requests, credential/configuration inspection or Git mutations;
the only repository edit was this assigned report.

## Official observation and budget

The bounded runner used normal `create_app` composition with the production
Marketplace connector, token authorizer, strict decoders and original HTTPX
transports. Pass-through guards restricted HTTPS to `api-sandbox.bizfile.gov.sg`,
the exact authorized paths/verbs/query and Garden UEN. Certificate verification,
no redirects and `trust_env=False` remained enabled. Basic client authentication
was checked after HTTPX auth processing; downstream requests used the raw `token`
header without Bearer replacement. No synthetic transport supplied these responses.

| External operation | Authorized maximum | Actual |
| --- | ---: | ---: |
| Successful token acquisition | 1 | 1 |
| entityBasicInformation | 2 | 2 |
| coShareholdersDetails | 1 | 1 |
| LLP / Capital / Relationships | 0 | 0 |
| GoldTier reads / writes | 0 | 0 |
| Other external requests | 0 | 0 |

All four dispatched requests returned HTTP 200 during 2026-09-30
18:32:02–18:32:07 UTC. Strict decoding and request identity binding succeeded.
The evidence is official **MOCK**, not Production/Live. The complete entity and
shareholder budget is consumed; no further external call occurred in follow-ups.

The initial preserved `OFFICIAL_GARDEN_LOCAL_HARNESS_RECEIPT.json` is a separate
pre-dispatch harness failure. Its original counters reserved a token request before
the Basic-header assertion. Independent AST extraction with inert HTTPX 0.28.1
objects reproduced zero underlying dispatches before authentication processing.
The corrected post-auth guard reached inert transport once and blocked an
unauthorized path before dispatch. Actual external requests for that initial run
were **zero**; it was neither a provider failure nor an external retry.

## Returned, derived and separate evidence

The sanitized network receipt retained a normalized company DTO and field-presence
names, not raw bodies, auth headers, token values or officer identities.

| Classification | Observed values / meaning |
| --- | --- |
| Returned and decoded | UEN `11111999A`; name `GARDEN BUSINESS`; legal form `PARTNERSHIP`; registration date `1974-09-28` |
| Returned address components | Block `306C`; street `XYZ LINK`; unit `#03-21`; building `ABC GARDEN`; postal code `333333` |
| Derived | Singapore `SG` country defaults from this registry lane; joined canonical address lines; retrieval time and evidence references |
| No normalized value | `entity_status=null`; no status value may be inferred |
| Official officers | COMPLETE, four records; personal record contents not retained |
| Official shareholders | EMPTY, zero records; this does not establish ownership completeness or absence of beneficial owners |
| Relationships | UNSUPPORTED, zero records, null provenance; no fabricated endpoint or retrieval timestamp |
| Client/manual | Synthetic uploaded PDF and reviewed direct economic interests; LOCAL / USER_SUPPLIED_DECLARATION / MANUAL_DECLARATION_POC, never ACRA |

Acquisition was truthfully PARTIAL while ENTITY_PROFILE was COMPLETE. The initial
current-official case had DOCUMENT_SOURCE_CONFLICT and no REGISTRY_NOT_READY.
The canonical address differed from the synthetic client document; reconciliation
retained the registry value. No provider data was fabricated to make the documents
match. The normalized replay explicitly omits the four official officers and uses
local replay timestamps for its own supplementary slots; these are not new official
observations.

## Browser and diagnostic evidence

`OFFICIAL_GARDEN_NETWORK_RECEIPT.json` proves normal UI case creation, actual
acquisition, document decisions, reconciliation and target classification. Its
browser stopped at manual ownership because document review remained incomplete.
The temporary browser loop could skip fields during query refresh; subsequent local
review completed every pending field. The original network-backed case was not
confirmed or completed, and its result remains FAILED.

`OFFICIAL_GARDEN_NORMALIZED_REPLAY_RECEIPT.json` proves the captured entity can
continue through normal services: all four document fields ACCEPTED and document
REVIEWED; reconciliation RESOLVED; Ownership review with truthful empty source;
document-bound manual declaration; Decimal analysis; TARGET_CONFIRMATION_REQUIRED;
explicit confirmation; local Mock GoldTier COMPLETED with no active exceptions,
registry COMPLETE and canonical entity unchanged. This browser later failed at its
HR navigation action; the completed local case is still verified. It is not proof
that the original network-backed case completed, or that the complete official
officer graph was replayed.

`OFFICIAL_GARDEN_HR_ZERO_CALL_RECEIPT.json` separately passed the actual official
connector configuration UI and diagnostics with external dispatch prohibited.
Provider/mode/classification/configured/client-present/secret-present were correct;
the UI asserted “Not applicable for API Marketplace Mock.” LLP, Capital and
Relationships each returned UNSUPPORTED, `provider_called=false`, record count zero.
No additional entity-profile diagnostic was run after budget consumption.

## Verification and safety

| Evidence | Result / ownership |
| --- | --- |
| Marketplace auth, connector, diagnostics service/API, registry acquisition | 128 tests passed; independently executed with ordinary-test guard, dotenv disabled and ephemeral synthetic login hashes |
| Diagnostics and case state frontend tests | 31 passed; independently executed offline |
| Inert guard ordering/path reproduction | Passed; independently executed, no network |
| Manifest verification and Git whitespace | Passed; independently executed |
| Fresh local clean/discrepancy Garden browser regression | Two passed, 12.2 seconds; coordinator execution |
| Broader focused backend / frontend | 233 / 43 passed; coordinator execution |
| Ruff / configured mypy / typecheck / build | Passed; coordinator execution; mypy 112 files |
| Contracts | Unchanged; not rerun in this continuation; prior guarded 44-test evidence remains scoped to unchanged candidate |
| Physical Mongo | NOT EXECUTED; pending authorized GitHub CI `mongo:7` |

An initial independent unittest invocation collected zero pytest-style tests and
provided no passing evidence; the corrected guarded pytest run supplied the 128
executed tests. Frontend startup first encountered the known esbuild ancestor-read
sandbox denial, then passed under approved scoped offline escalation.

Memory persistence, `mongo_uri=None`, forbidden MongoClient construction and local
Mock GoldTier with external writes disabled protected the provider session. The
replay and HR follow-ups prohibited every external request. Reviewed receipts contain
no credentials, tokens, raw provider bodies or personal officer/shareholder content.
Existing ignored configuration was resolved by the authorized runner only; this is
not a claim that no dotenv resolution occurred. Ephemeral login hashes were not
persisted. No normal Atlas connection/cleanup, external GoldTier submission or
provider mutation occurred.

## Findings and final gate

All previously reproducible local Garden implementation findings remain resolved.
Temporary harness failures and skipped operator decisions are evidence limitations,
not demonstrated connector or domain compatibility defects. Production/Live ACRA
and external GoldTier readiness are not implied by this official Mock observation.

| Acceptance | Independent conclusion |
| --- | --- |
| Current official ACRA Mock identity/shareholder acquisition | VERIFIED |
| Unsupported operations and safety budget | VERIFIED |
| Actual network-backed full Garden completion | NOT VERIFIED; original case stopped before declaration/confirmation |
| Captured normalized entity compatibility through local completion | VERIFIED, with officer omission and replay classification |
| Existing local clean and human-review paths | PASS evidence retained; fresh coordinator regression passed |
| Physical Mongo restart acceptance | PENDING CI; not waived |
| External GoldTier submission | NOT EXECUTED; Sandbox remains SANDBOX_PARTIAL |
| Publication | NOT REQUESTED / NOT READY |

**FAIL** under the exact quality-gate rule for unverified required criteria. The
user permits a single provider observation plus deterministic regression after the
budget is consumed; that supports the verified acquisition and scoped replay results,
but does not retrospectively complete the original network-backed case. Physical
Mongo is independently still pending. No application implementation remediation is
required by an established finding here; remaining acceptance needs truthful bounded
evidence and the separately authorized CI lane. No publication or next phase begins.
