# Phase 21 — External Integration Activation Readiness Implementation

## Outcome and revision identity

**PROVIDER INTEGRATION: PARTIAL**

This phase creates readiness and evidence governance only. **NO NEW REAL EXTERNAL
PROVIDER WAS ACTIVATED.** No real network call, credential consumption, provider
composition, adapter, API, persistence, frontend, target-ledger, or business-policy
behavior changed.

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`
- Branch: `phase/21-external-integration-readiness`
- `BASE_SHA`: `5039c7e548dfae1eeb8ad600f128ef374e3a6f2a`
- Current source revision at implementation start: the accepted Phase 20 tree at
  `5039c7e...`.
- Tested revision: the final task-owned worktree candidate after implementation and
  remediation; the exact path manifest and commit identity must be recorded before
  independent QG/publication.
- Independently reviewed revision: not yet reviewed; the fresh QG owns that identity.

Phase 20 is accepted on the main baseline. D-009 remains limited to the human-exception
principle. Q-001 through Q-018 remain open. The project state records Phase 20 accepted
and Phase 21 candidate/pending.

## Provider integration matrix

| Provider / operation | Current mode / classification | Activation state | Contract authority | Discrepancies / gates | Port / canonical mapping | Auth / TLS / secrets | Timeout / retry / error authority | Mock parity | Sanitized evidence | Tests / reviews | Residual blockers |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ACRA Mock | `mock / MOCK` | `INTERNAL_POC_ONLY` | Current Mock source/tests | Q-012 does not govern the synthetic Mock contract | Existing ACRA port and canonical model | Credential-free POC | Existing bounded Mock behavior | Existing accepted Mock path | No sandbox evidence | Existing suites plus readiness checker | No Live claim |
| ACRA generic sandbox seam | `sandbox / PARTIAL` | `PARTIAL_SCAFFOLD_ONLY` | Q-012 incomplete | Endpoint/schema/auth/error/rate/TLS/access/test UEN unresolved | Existing `AcraSandboxConnector`; no rewrite | HTTPS/cert verification seam only; no guessed auth | Existing bounded timeout/stop behavior; no new retry | Must remain distinct from Mock | None supplied | Registry adversarial tests; no smoke run | Q-012 and authorized access |
| ACRA BizFile | `dormant / DORMANT` | `BLOCKED` | No activation authority | Dormant module is not composed | Existing dormant boundary | No auth/token lifecycle | None activated | Not applicable | None | Read-only inspection | Explicit provider reauthorization |
| Local PDF/text IDP | `local_pdf_text / LOCAL` | `INTERNAL_POC_ONLY` | Current local POC | Q-003/Q-005/Q-013/Q-014 block vendor OCR | Existing local IDP port | No vendor credentials | Existing local deterministic behavior | Local/Mock fault boundary preserved | None | Evidence validator/checker tests | No vendor authority |
| Vendor IDP/OCR | `not_implemented / NOT_IMPLEMENTED` | `BLOCKED` | Q-003/Q-005/Q-013/Q-014 | Document scope/extraction/data handling/auth/TLS unresolved | No adapter added | No secrets | No transport | No fallback | None | Registry tests | Sponsor/provider contract |
| Local Decimal ownership | `local / LOCAL` | `INTERNAL_POC_ONLY` | Current deterministic engine | Not an external hierarchy service | Existing canonical ownership owner | No external auth | Existing deterministic graph rules | Mock support preserved | None | Registry tests | No external hierarchy authority |
| Future hierarchy provider | `not_implemented / NOT_IMPLEMENTED` | `BLOCKED` | Q-002/Q-004/Q-006/Q-007 | Retrieval/write/mapping/authority unresolved | No adapter added | No secrets | No transport | No fallback | None | Registry tests | Sponsor/provider contract |
| GoldTier Mock | `mock / MOCK` | `INTERNAL_POC_ONLY` | Current Mock contract | Mock submission is not approval/Live | Existing target port and ledger | Credential-free | Existing no-replay owner | Existing ordered Mock parity | No sandbox evidence | Existing suites plus governance tests | No real target claim |
| GoldTier real | `not_implemented / NOT_IMPLEMENTED` | `BLOCKED` | Q-008/D-018, Q-001, Q-007, Q-009–Q-011, Q-018 | Auth containment, mappings, exact operations, TLS/network and handoff unresolved | No HTTP adapter added | No PingFed/token consumption; TLS 1.3 remains future requirement | No new retry/error behavior | No Mock fallback | None | Registry/evidence adversarial tests only | Explicit reauthorization and all authority |
| PingFed auth | `not_implemented / NOT_IMPLEMENTED` | `BLOCKED` | Q-008/D-018 and Q-018 | Token URL/scopes/client auth/network unresolved | No token owner/adapter | No credentials or token cache | No transport | No fallback | None | Registry/evidence adversarial tests only | Sanitized auth reference and fresh delivery |

## Deliverables

- `docs/contracts/external_provider_readiness_registry.json`
- `scripts/check_external_provider_readiness.py`
- `docs/contracts/EXTERNAL_PROVIDER_ACTIVATION_CONTRACT.md`
- `docs/integration/PHASE_21_PROVIDER_ACTIVATION_PACKET.md`
- `docs/integration/EXTERNAL_PROVIDER_SECRET_SECURITY_RUNBOOK.md`
- `docs/contracts/external_provider_evidence.schema.json`
- `scripts/validate_external_provider_evidence.py`
- `tests/test_check_external_provider_readiness.py`
- `tests/test_validate_external_provider_evidence.py`
- narrow `PROJECT_STATE`, contract index, configuration-reference, pre-PR and CI updates
- `.ai-pipeline/001_planner/PHASE_21_PLAN.md`

## Verification record

### Positive-policy remediation after repeated independent FAIL

Three fresh independent gates found the same systemic evidence-sanitizer defect: the
candidate accepted broad string grammars and tried to reject secrets by recognizing
selected labels and delimiters. The third report, P21-FQG-003, demonstrated four more
schema-valid separator variants. That complete FAIL history remains in the successive
quality-gate reports; it was not reclassified or erased.

The remediation rejects the blacklist model rather than extending it. Evidence profile
v2 accepts only these positive field languages:

| Field | Exact accepted language |
|---|---|
| `schema_version` | integer constant `2` |
| `provider_id` | exact ten-entry readiness-registry provider enum |
| `mode` | `mock`, `local`, `sandbox`, or `live` |
| `classification` | exact seven-entry evidence-classification enum |
| `operation` | exact 14-entry known operation enum |
| `observed_at` | real UTC ISO-8601 instant ending in `Z`, seconds required, optional 1–6 fractional digits |
| `safe_test_case_reference` | `SYNTHETIC-` or `AUTHORIZED-` plus one canonical lowercase UUID |
| `correlation_identifier` | one canonical lowercase UUID |
| `http_outcome_category` | exact eight-entry outcome enum |
| `contract_reference` | `Q-001` through `Q-018`, `D-009`, `D-018`, or `EXTERNAL_PROVIDER_ACTIVATION_CONTRACT` |
| `certificate_verification_result` | exact three-entry result enum |
| `auth_mechanism_label` | exact five-entry symbolic enum; no header or credential value |
| `mapping_reference` | exact five-entry canonical mapping enum |
| `sanitized_result_category` | exact six-entry result enum |
| `call_order_result` | `EXPECTED`, `STOPPED_ON_FAILURE`, or `NOT_APPLICABLE` |
| `redaction_check_result` | string constant `PASS` |

Whole-record validation then applies these current-truth profiles:

| Provider | Compatible evidence profile |
|---|---|
| `ACRA_MOCK` | `mock / MOCK`; entity, officer, ownership-party, or relationship operation; synthetic UUID case reference; non-HTTP; activation contract; no auth/certificate; ACRA mapping; expected or stopped order |
| `IDP_LOCAL_PDF_TEXT` | `local / LOCAL`; document extraction; synthetic UUID case reference; non-HTTP; activation contract; no auth/certificate; IDP mapping; order not applicable |
| `OWNERSHIP_LOCAL_ENGINE` | `local / LOCAL`; ownership analysis; synthetic UUID case reference; non-HTTP; activation contract; no auth/certificate; ownership mapping; order not applicable |
| `GOLDTIER_MOCK` | `mock / MOCK`; search, shell, policy, or amend operation; synthetic UUID case reference; non-HTTP; activation contract; no auth/certificate; GoldTier mapping; expected or stopped order |

Generic ACRA sandbox, BizFile, future vendor IDP/hierarchy, real GoldTier, and PingFed
have no current evidence profile. They remain unrepresentable until a separately
authorized schema/validator change supplies authoritative combinations.

Unknown fields remain rejected. No maps, arrays, paths, URLs, free text, bodies,
payloads, errors, headers, queries, credentials, or generic metadata containers are
accepted. The old recursive sensitive-key/value walker and both secret/delimiter
regular expressions were removed. The schema version changed because the allowed
language is intentionally narrower and semantically incompatible; no production
compatibility promise exists for this candidate profile.

Adversarial tests exercise every accepted string field against delimiter and whitespace
families, Unicode punctuation/separators, URL/header/key-value/query/path shapes,
embedded token-looking material, oversized values, control characters, and multiline
content. Every scalar field is also challenged with a nested object and array. Unknown
and duplicate fields remain rejected, diagnostics do not echo hostile values, and valid
synthetic evidence still validates. This closes the design class through the accepted
language, not through delimiter recognition.

The remediation changes no runtime provider behavior, connector, network call, mode,
credential/auth implementation, ACRA/GoldTier/PingFed/Mock behavior, persistence, API,
frontend, RBAC, business policy, or readiness classification. No provider was activated.

### Fourth fresh gate findings and remediation

The fresh Sol High gate reviewed manifest
`e56f0009ed5937cbbc3a0081b601c3ac2629f67d9a40791fbb7047cff14ecf86`
and returned `FAIL`. Its appended report remains intact. P21-FQG-004 proved that the
first positive-field candidate still allowed an impossible cross-provider combination;
P21-FQG-005 proved that duplicate arbitrary keys were echoed in diagnostics; and
P21-FQG-006 found two index rows for absent workspace artifacts.

The remediation adds synchronized JSON-schema and validator provider profiles for only
the four current credential-free providers. A table-driven test accepts one
representative per profile, rejects 236 disallowed global-enum substitutions across
every profile field, and rejects all six providers that lack a current profile. The
original cross-provider reproducer now fails closed. Duplicate-key rejection uses a
constant diagnostic and function/CLI tests prove an arbitrary hostile key is not
echoed. The two premature index rows were removed; no ceremonial artifact was created.

### Fifth fresh gate findings and remediation

The next fresh Sol High gate reviewed manifest
`87756a021bfba9e0011004e2994220692506943d1a080473e0e44497bd1cb1c9`
and returned `FAIL`. Its appended report remains intact. P21-FQG-007 proved that the
imported readiness-registry loader still echoed duplicate arbitrary keys through both
CLIs. P21-FQG-008 proved that Draft 2020-12 regular-expression end anchors accepted a
trailing line feed and that the schema did not reject calendar-impossible timestamps,
although the Python validator rejected both classes.

The remediation makes the readiness-registry duplicate-key diagnostic constant, so the
direct checker and importing evidence validator share non-echo behavior. Function and
CLI regression tests cover both entry points. The schema and Python timestamp/reference
grammars now expressly exclude carriage returns and line feeds. The timestamp grammar
also enforces real Gregorian dates, including century leap-year rules, while the schema
retains `format: date-time`. Tests validate actual Draft 2020-12 instances and prove
schema/Python agreement for trailing-line-feed references, trailing-line-feed UUIDs,
ordinary impossible dates, and invalid century leap days.

### Sixth fresh gate finding and remediation

The next fresh Sol High gate reviewed manifest
`7a46f3b19feac448a2e8e8d85a71f6ace957474d4866aa64e03587e961b5dce8`
and returned `FAIL`. Its appended report remains intact. All earlier evidence-language,
provider-profile, duplicate-key, timestamp, and non-activation defect classes passed
independent falsification. P21-FQG-009 found that the security workflow collected the
new evidence-validator test before installing its pinned `jsonschema` dependency.

The remediation moves the existing pinned contract-validation install step ahead of
the evidence-validator test while retaining it ahead of the later GoldTier validation.
A regression test asserts both orderings. A disposable Python 3.12 environment first
proved `jsonschema` absent, installed the repository-pinned requirements, and then
passed the full 14-command security-job sequence, including the 17 evidence-validator
tests and the existing GoldTier checks. The disposable environment was outside the
checkout so the repository-wide secret scanner saw the same checkout shape as CI; it
was removed after verification.

The current positive-policy candidate has fresh verification:

- 17 focused evidence-validator tests pass, including 300 hostile string-field
  combinations, 32 object/array scalar challenges, and 242 provider-profile adverse
  cases; the combined readiness/evidence suite has 28 tests;
- 134 affected Phase 21 governance/readiness/pre-PR tests pass (52 provider/policy/
  tooling/validator, 39 project-state/architecture/context, 43 pre-PR inventory);
- 44 contract tests and 8 secret-scanner tests pass;
- the exact 232-test backend ACRA/provider/zero-touch regression passes with three
  expected malformed-fixture serializer warnings;
- direct project-state, architecture, tooling, policy-authority, provider-readiness,
  and secret checks pass;
- the clean Python 3.12 security-job sequence passes all 14 commands after installing
  the pinned contract-validation requirements at the corrected point;
- Ruff passes over `scripts` and `tests`;
- strict JSON parsing passes for 10 task JSON files and the evidence schema is a valid
  Draft 2020-12 schema;
- Markdown/file hygiene passes for all 31 task-owned changed files (strict UTF-8, no
  BOM/NUL/trailing whitespace/conflict markers, final LF); and
- `git diff --check` passes with line-ending conversion warnings only.

The initial focused run was blocked by the managed Windows temporary-directory ACL;
the same suite was run with host permission and produced the recorded test result.
Task-owned repository temp directories from that failed attempt were removed. A
synthetic header-shaped test literal initially triggered the repository secret scanner;
the same hostile value is now assembled from non-sensitive source fragments at test
runtime, after which both the focused suite and direct scanner passed. No diagnostic
prints hostile values.

The remaining publication checks are recorded against the final frozen candidate
before QG/publication: `check_secrets` after the fresh QG replaces the prior report and
`pre_pr_check.py` on the clean committed tree.
Physical Mongo, Playwright and lifecycle checks are not applicable because runtime
behavior is unchanged.

## Explicit non-claims and sponsor action

Placeholder environment names do not imply readiness. No ACRA subscriber access,
GoldTier/PingFed connectivity, vendor OCR, external hierarchy, sandbox success, Live
interoperability, approval, Ready-for-Approval, or production handoff is claimed.

The sponsor/API owner must supply the sanitized contract, security/access authority,
approved synthetic test reference, and out-of-repository secret-delivery action listed
in the activation packet. A future runtime phase requires explicit reauthorization,
fresh security review, exact tests, independent QG, and separate Live evidence.
