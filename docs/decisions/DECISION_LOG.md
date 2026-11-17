# Decision Log

## D-069 — owner-authorized post-UAT review and completion UX candidate

The 2026-10-05 owner assignment from main ae27654 permits existing-owner document
auto-confirm at independently admissible GOLDTIER_SEARCH intake. Exact normalized
agreement, sufficient frozen evidence score, unambiguous extraction, currentness
and no unresolved contradiction remain required; no target progression is granted.

Ownership reviewer rationale becomes optional; structured actor/time/source/as-of/
document/observation/graph/replacement audit remains required. Historical strings
read unchanged; absent/blank notes are null, never fabricated reviewer prose.
This supersedes only the mandatory ownership free-text rationale in D-067.
The separate existing-customer confirmation rationale remains required.

Normal official Marketplace Mock composition automatically applies the existing exact
eligible Garden11111999A local synthetic fixture. This supersedes the required runtime
Garden opt-in in D-067/ADR-009; freshness/success/no-failed-operation/provenance/
no-double-count safeguards and human conflict review remain. The legacy setting is
deprecated compatibility input and cannot disable the accepted Garden happy path.

Same legal entity retains its resolved GoldTier customer ID across distinct local
cases; different-entity definitive NO_MATCH retains new Shell. Completed Sandbox
verification is an explicit independent exact-retained-ID read-only Search with no
ledger/submission rewrite, replay or downstream approval claim. All changes are
USER_AUTHORIZED_POC candidate behavior, pending their own independent gate. This is
not sponsor production policy, external-call authority or a Live/provider upgrade.

Use this file for requirements that have been explicitly resolved.

For a new durable architecture decision, use [ADR_TEMPLATE.md](ADR_TEMPLATE.md) when the
criteria in `docs/DEVELOPMENT_WORKFLOW.md` apply, then link the accepted ADR from this
log. Do not retroactively create an ADR when the original context, alternatives or
rationale cannot be proved; retain the existing decision entry as historical evidence.

| ID | Decision | Source / reason | Status |
|---|---|---|---|
| D-001 | Main project flow is ACRA Singapore -> EDS/orchestration -> GoldTier using Singapore NTB. | Latest sponsor clarification | Confirmed |
| D-002 | ACRA is the sole live external corporate registry source for the FYP. | Latest sponsor clarification | Confirmed |
| D-003 | Canonical amendParty endpoint is `POST /v1/eds/parties/{partyId}/amend`. | Latest sponsor clarification | Confirmed |
| D-004 | `createRelatedParty` creates/supports direct first-level related-party relationships only. | Latest sponsor clarification | Confirmed |
| D-005 | Multi-level hierarchy creation is not supported via the current API; seeded GoldTier hierarchy is to be retrieved/displayed. | Latest sponsor clarification | Confirmed |
| D-006 | ACRA `registrySourceLink` should reference ACRA and the corresponding API endpoint; UTC ISO-8601 sourcing time is acceptable/recommended. | Latest sponsor clarification | Confirmed |
| D-007 | GoldTier sandbox authentication target is PingFed; exact connection details will be provided when Nutmeg is ready. | Latest sponsor clarification | Confirmed |
| D-008 | TLS 1.3 is required for sponsor sandbox connectivity. | Latest sponsor clarification | Confirmed |
| D-009 | Human-in-the-loop review is allowed/expected; “zero touch” does not mean no human exceptions. | Sponsor Q&A | Confirmed |
| D-010 | UBO calculation should be deterministic in the POC; AI may assist extraction but should not autonomously decide approval. | Project risk/safety design | Working decision |
| D-011 | The provisional seven-operation EDS contract uses OAuth2 bearer authentication and operation scopes. Every call requires `X-Correlation-Id` and `X-Source-Case-Id`; POST calls also require JSON content type, a UUID v4 `Idempotency-Key`, and matching `sourceContext.sourceCaseId`. | Corrected standalone OpenAPI files and EDS-GoldTier specification | Provisional contract |
| D-012 | A GoldTier registry-reference proof does not require a binary registry document. When proof metadata is submitted, the registry source link and sourcing timestamp must both be present; for this POC they identify the actual ACRA API endpoint and a UTC ISO-8601 sourcing time. | EDS-GoldTier specification plus D-006 | Confirmed |
| D-013 | API-field and value-list joins added by the GoldTier EDS Data Dictionary are automated candidate mappings, including rows labelled `HIGH`; they are not sponsor-confirmed mappings. | Data Dictionary “Cover & Methodology” | Confirmed artefact limitation |
| D-014 | `createRelationship` is a future extension outside the approved seven-operation catalogue and must not be implemented in the current POC scope. | EDS-GoldTier specification and future-labelled JSON examples | Confirmed |
| D-015 | For Phase 01 mock development, direct sponsor clarifications take priority; corrected standalone operation OpenAPI governs paths, schema/property shape, enums, and machine validation; explicit sponsor directions to another artefact govern that specific question; validating JSON examples are reference-only; contradictory JSON examples are quarantined; and the combined bundle is lower-confidence where it conflicts. | Phase 00 quality-gate remediation needed to make conflicting artefacts usable without hiding uncertainty | Project development decision pending sponsor/API-owner confirmation |
| D-016 | Delta Capita directed the team to the EDS-GoldTier Integration API Specification for each endpoint's minimum mandatory fields. Those explicitly listed fields therefore form a provisional mandatory-field overlay when standalone OpenAPI differs. `countryOfIncorporation` is required for `createShellCustomer` on this basis; its Singapore mapping/value-list meaning is not independently confirmed. | Latest sponsor clarification about where minimum required fields are defined | Confirmed direction; resulting contract overlay is provisional |
| D-017 | Sponsor JSON examples that fail the provisional canonical schema/rules must not be used as canonical fixtures, DTO enum sources, or contract assertions. The local Phase 00 validation result is 19 valid, 19 invalid/quarantined, and 48 not validated. | Automated validation against corrected standalone operation OpenAPI plus D-015/D-016 | Project development decision |
| D-018 | The supplied PingFed/Postman material is quarantined and must not be used, tested, copied, or sanitised in place. Real GoldTier authentication is blocked pending sponsor rotation/revocation confirmation, a sanitised reference collection, and approved delivery of fresh credentials when sandbox integration begins. Credential-free mock development is not blocked. | Phase 00 security quality-gate finding | Security containment decision |
| D-019 | Phase 02 keeps the subscribed ACRA endpoint schema and authorization behavior behind injectable decoder/authorizer interfaces. The tracked project response shape and static-header adapter are synthetic integration seams, not claims about ACRA's subscriber contract. Live verification is blocked until authoritative subscriber documentation and authorized access are supplied. | No approved ACRA endpoint/auth/response contract exists in current project artefacts; official ACRA public material confirms service/field availability but not transport details | Project development and security decision |
| D-020 | Pending Q-003/Q-005, Phase 03 implements document processing as a supplementary case-linked workflow that cannot alter the accepted onboarding terminal state or call GoldTier. Its four-field corporate profile, deterministic comparisons, all-field completion rule, synthetic Mock IDP values, 5 MiB upload limit, and 0.85 attention threshold are configurable project defaults only. Original IDP suggestions and human-reviewed values remain distinct. | Avoids inventing a final document contract, validation owner, or required NTB sequence while establishing the upload/IDP/field-review boundary | Working project and security decision pending sponsor confirmation |
| D-021 | Pending Q-002/Q-004/Q-006/Q-007, Phase 04 implements ownership analysis as an independent case-linked sub-workflow using a replaceable provider and synthetic Mock graphs. The default 25% threshold, inclusive `aggregated ownership >= threshold` comparator, root-to-owner edge orientation, cycle/incomplete review treatment, and graph/path limits are configurable project defaults only. Results are ownership-based provisional candidates, never legal/controller or compliance decisions. | Establishes deterministic Decimal path/aggregation and safe provider boundaries without inventing GoldTier hierarchy or sponsor-approved UBO rules | Working project and security decision pending sponsor confirmation |
| D-022 | Phase 04 technical integrity requires every owned/parent party to be a legal entity, fresh nested reconstruction of untrusted provider results, opaque server-only source references, expected-version terminal writes, digest path identifiers, the shared six-decimal percentage/threshold precision contract, and exact string-based browser Decimal presentation. These controls do not change D-021 or resolve a sponsor policy question. | P04-QG-001 through P04-QG-006 remediation; prevents false classifications, trust-boundary bypass, terminal overwrite, derived-bound failure, and misleading display | Project quality and security decision |
| D-023 | Pending Q-003/Q-004/Q-005/Q-006/Q-007/Q-014, Phase 05 uses a conservative staged Mock-submission policy: validated canonical ACRA data remains the base; at least one fully reviewed registry-compatible document and one terminal `ANALYZED` ownership result are required; source conflicts block without canonical overwrite; related-party writes are not executed; and Mock success is `MOCK_GOLDTIER_SUBMITTED`, never Ready-for-Approval. Readiness is re-evaluated server-side inside a per-case serialized submission boundary. | Connects the accepted Phase 01–04 foundations safely without inventing master-data authority, legal UBO policy, related-party mapping, real integration, or approval semantics | Working project and security decision pending sponsor confirmation |
| D-024 | Phase 05 technical integrity requires shared current-canonical validation for onboarding/readiness/pre-submit, current-canonical document conflict comparison without rewriting Phase 03 evidence, snapshot-sourced target mapping with stable operation identifiers, a process-local pre-receipt safe target-outcome ledger with recoverable rich receipts, and frontend invalidation/refetch after evidence mutation. | P05-QG-001 through P05-QG-004 remediation and final P05-QG-003 recovery closure; prevents false readiness, snapshot/payload divergence, duplicate recovery writes, pre-receipt outcome loss, stranded finalization, and stale UI truth | Project quality and security decision; process-local Mock guarantee only; does not alter D-023 or resolve sponsor policy |
| D-025 | Pending Q-003/Q-004/Q-005/Q-013/Q-014, Phase 06 applies a narrow provisional zero-touch policy: complete current-canonical document matches at or above the configured threshold may be auto-confirmed only in the integrated path; every pending or reviewed case document is re-evaluated semantically; mismatches/low confidence/missing fields become typed exceptions; `KEEP_REGISTRY_VALUE` records a separate journey resolution without rewriting document evidence and cannot clear an independent blocker; ownership indeterminacy and existing/partial target outcomes cannot be clicked through; technical failures remain separate. Version plus server-owned authoritative-evidence binding auto-resumes, while Phase 05 retains target replay authority and repeated finalization-only faults remain nonterminal `RECOVERY_PENDING`. Registry adapter results are freshly reconstructed and request-UEN-bound, with query-free HTTPS retained provenance pending Q-012. | Implements and remediates the assigned sponsor demo without inventing master-data, reviewer, UBO, ACRA endpoint, existing-party, partial-write, or approval policy | Working project and security decision; Mock/process-local POC only; pending sponsor confirmation |
| D-026 | Phase 07 packages the accepted process-local Mock journey for sponsor UAT without changing D-025: deterministic demo presets remain isolated behind fail-closed demo controls; a synthetic recovery preset injects only receipt-finalization faults and reuses Phase 05 retained-outcome authority; safe UAT export is a strict whitelist of synthetic identifiers, statuses, blockers, operation names, metrics, timings, warnings, environment and sanitized events; backend restart is the documented full demo reset. | Provides reproducible acceptance and handoff evidence without exposing payloads, inventing a live adapter/policy, or adding unnecessary persistence | Project delivery/security decision; Mock/demo-only and not a sponsor-policy decision |
| D-027 | Phase 08 composes normal sponsor-mode cases from UEN-keyed local synthetic Registry/Ownership/Mock GoldTier datasets and actual text extracted from a synthetic PDF. The local parser's labelled-value confidence is deterministic (`0.97` primary unique, `0.90` alternate unique, `0.40` ambiguity, `0.00` missing); replacement evidence explicitly supersedes a current case document while retaining its history. Developer/Test scenarios remain separately gated fault injection. | Addresses demo input causality without changing Phase 06 orchestration or asserting final IDP/source/reviewer policy. | Working project and security decision; input-driven bounded synthetic POC only; Q-003/Q-005/Q-013/Q-014 remain open. |
| D-028 | Phase 09 resolves jurisdiction from retained source observations without source precedence. Active evidence is optional user input plus explicit Singapore-UEN-format inference. Agreement resolves; absence is `JURISDICTION_UNRESOLVED`; disagreement is `JURISDICTION_CONFLICT`. Only resolved Singapore selects the existing ACRA adapter; recognised AU/MY/HK stop as `REGISTRY_PROVIDER_NOT_IMPLEMENTED` with no registry, IDP, ownership, or GoldTier call. | Establishes the smallest future-extensible jurisdiction foundation while preserving Singapore scope and avoiding invented evidence authority or foreign integrations. | Working project and security decision pending Q-015; process-local POC only. |
| D-029 | Phase 10 models entity profile, officers, ownership parties, and relationships as four bounded project-owned ACRA Mock operations. A valid empty officer collection may continue; missing expected ownership evidence stops as partial/review-required; malformed or unavailable operations fail safely. Registry ownership evidence is adapted into the existing ownership provider/domain and deterministic Decimal analysis, which remains the sole UBO calculation authority. | Makes Mock registry acquisition architecturally realistic without asserting the unresolved live ACRA contract, inventing missing-data policy, or creating a second ownership engine. | Working project and security decision; Mock/process-local POC only; Q-012/Q-015 and final mappings remain open. |
| D-030 | Pending Q-015, Phase 11 compares legal name, registration identifier, registered address, and country through source-neutral observations with no automatic precedence. Conflicts remain explicit until a bounded POC operator action; `KEEP_REGISTRY_VALUE` is available for usable conflicts, while `USE_DOCUMENT_VALUE` is advertised only for one unambiguous legal-name document value that the typed backend can validate and apply without mutating Registry/IDP evidence. Required missing, invalid, and unverifiable values require replacement evidence. D-052's user-authorized COI profile narrows only absent optional address to non-blocking `REGISTRY_ONLY`; a supplied address remains compared and the legacy required-address profile remains blocking. All decisions and resume guarantees remain process-local. | Establishes reusable reconciliation and safe resume without inventing master-data authority, structured-address parsing, route/identity replacement, corrected-value entry, production RBAC, or durable audit semantics. | Working project and security decision pending Q-015; process-local POC only, refined by D-052. |
| D-031 | Phase 11 technical integrity derives outcome/action/status from retained observations and current discrepancy links, permits at most one current discrepancy per field/evidence set, and commits a prepared legal-name canonical candidate plus its decision through one shared-lock in-memory unit of work. Recoverable commit faults restore both snapshots before lock release; duplicate decisions are idempotent only in the unchanged current context. | P11-QG-001 through P11-QG-004 remediation; prevents half-committed canonical selection, forged false-clear state, stale historical replay, and actions over unusable evidence. | Project quality/security decision; process-local only, not crash/restart durability or sponsor-approved authority. |
| D-032 | Pre-Phase 12 adds a read-only backend-authored process-local case index and review queue plus an explicit bounded multi-document intake-completion boundary. PDF, DOCX, and UTF-8 TXT are technical POC formats; 20 files, 5 MiB per file, and 25 MiB total are configurable safeguards. Every current document retains provenance and contributes to reconciliation; a missing field in one document does not erase a valid observation from another, while conflicting, invalid, or unverifiable observations remain visible and never create an automatic source winner. | Closes the accepted Phase 11 usability/intake gaps without adding MongoDB, production case management, source authority, OCR, or Phase 12 behavior. | Working project/security decision; process-local POC only and pending Q-003/Q-013/Q-014/Q-015. |
| D-033 | Phase 12 uses explicit memory or Mongo persistence. Mongo stores one schema-versioned structured envelope per case with revision CAS, atomic canonical/reconciliation decisions, and durable target intent/outcome/receipt checkpoints. Completed work is reused; uncertain attempted target work is not replayed. Raw document bytes/full text and raw external payloads are excluded. | Provides bounded restart recovery without adding a distributed workflow engine, retention policy, or production compliance storage. | Project quality/security decision; durable single-instance POC only; Q-012/Q-015 remain open. |
| D-034 | Phase 13 uses five fixed synthetic profiles, local scrypt password hashes, process-local opaque eight-hour sessions, session-bound CSRF, and immutable two-team case ownership. Role differences govern visibility only; every actor with case access may use existing mutations and change nullable 1–10 priority. Director has global visibility and the same mutation surface; no reassignment/sharing exists; priority changes ordering only. Exact Mongo schema-v1 reads become unassigned/null-priority in memory without rewrite, while new writes use schema v2. | The Phase 13 sponsor brief authorizes bounded provisional demo behavior while the production IdP, role matrix, assignment, priority, and governance policy remain unanswered. | Working project/security decision; local POC only; pending Q-016. |
| D-035 | The Phase 13 demo identities are Maya Lim (`maya-lim`), Ethan Tan (`ethan-tan`), Sophia Ng (`sophia-ng`), Ryan Lee (`ryan-lee`), and global Director Olivia Koh (`olivia-koh`). Persisted `TEAM_A`/`TEAM_B` remain unchanged while their browser names are DBS Corporate Onboarding and OCBC Corporate Onboarding. Development/test Origin/Referer validation trusts only configured exact backend/Vite loopback origins; request `Host` is never authoritative. Production requires an explicit exact HTTPS browser origin and receives no implicit development-origin trust. | Post-Phase-13 remediation of the demonstrated Vite-proxy CSRF failure, request-controlled Host trust defect, and technical demo account/team labels. | Project security/demo decision; local POC identity naming only; does not resolve Q-016. |
| D-036 | Phase 13 New Onboarding accepts optional strict 1–10 priority in the canonical create request and persists it on the initial team-owned case; omission/null stays null and later PATCH remains supported. The authenticated synthetic Director seeder creates ten missing cases through application APIs, then uses the existing `STRAIGHT_THROUGH` document lifecycle and accepts only canonical `COMPLETED` / `MOCK_GOLDTIER_SUBMITTED` results. Exact team/UEN reruns reuse cases and verify unique ownership, expected priority, and terminal success. | Completes a truthful sponsor-ready memory-mode RBAC portfolio without direct repository/status mutation, a fake completion route, per-user ownership, or a schema change. | Project demo/technical decision; synthetic Mock workflow only. Physical Mongo validation remains Part 2. |
| D-037 | Phase 13 Dashboard V1 is an authenticated, provider-free read model over canonical authorized cases. `CaseQueryService` applies actor/team scope before factual totals, exact `AutomationStatus` and 10..1/unset priority distributions, authorized team counts, bounded recent/top-active lists, and a 30-day UTC created/completed trend. Memory and Mongo use the same service; only Mongo provides restart durability. | Provides a useful historical sponsor view without browser-side RBAC, a second persistence owner, an analytics warehouse, provider enrichment, or invented SLA/risk/approval/KPI semantics. | Project demo/technical decision; factual POC read model only and does not resolve Q-016. |
| D-038 | When an existing shared Mongo database contains multiple historical cases for a synthetic team/UEN pair, the Phase 13 seeder reuses an exact `COMPLETED` / `MOCK_GOLDTIER_SUBMITTED` case with the expected priority and requires at least one such showcase match. It does not delete, rewrite, or hide colliding history. Physical validation selects the ten exact showcase records, while the dashboard continues to count every case authorized for the actor. | Preserves shared-data safety and deterministic demo evidence without treating the shared collection as disposable or making dashboard totals misleading. | Operational demo decision for shared test history; collisions remain visible in the authenticated historical dashboard. |
| D-039 | Ordinary backend tests force memory persistence and a non-shared database namespace before app imports, while physical Mongo tests opt in with `_env_file=None`, an explicit URI, and strict generated `clm_p12_*` / `clm_p13_*` database names. Cleanup retries and verifies deletion. Historical case priority filters and either sort direction are backend-owned and apply only after RBAC, with unset priority last; Dashboard top-active order is unchanged. | Final Phase 13 quality-gate remediation for shared-database test isolation, physical teardown safety, and requested historical-list controls. | Project test-safety and demo-query decision; does not authorize alteration or deletion of shared `clm_poc` records. |
| D-040 | Phase 14 uses one authorized lightweight portfolio projection for case lists/Dashboard, a 45-second authenticated session-memory TanStack Query cache, insert-only case creation plus update-only mutation, and revision-aware permanent deletion under the canonical case lock. The same reentrant per-case lock covers the entire initial zero-touch establishment through onboarding, CLM, automation, and applicable demo registration; an escaped required-write failure triggers bounded same-case aggregate rollback. Confirmed deletion cancels the authenticated user's in-flight list/Dashboard queries before cache removal. Director may delete any accessible case; Relationship Manager may delete own-team cases; accessible Client Onboarder deletion is forbidden; inaccessible/absent cases remain indistinguishable. Deletion/rollback removes only local case-owned state and makes no external-system call. | Removes measured frontend/Mongo N+1 reads and prevents post-delete backend orphan writes and stale in-flight browser responses from resurrecting a locally deleted case without inventing external erasure, retention, or production governance. | PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR CONFIRMATION. |
| D-041 | Phase 14.5 persists bounded team/profile/policy administration, adds synthetic HR with zero case access, renames the stable `TEAM_A`/`TEAM_B` presentations to Alpha/Beta, and permits generated canonical teams. Relationship Manager/Director alone mutate the typed policy catalogue. New cases bind its two runtime thresholds immutably in schema v3; schema-v1/v2 reads use fixed Phase 13 defaults in memory. Director portfolio filtering remains server-authoritative across Cases, Dashboard, and Onboarded. | Removes fixed browser/process owners while preventing retroactive policy reinterpretation, browser-authoritative access, password/audit disclosure, and shared Mongo test cleanup. | Working project/security decision; synthetic POC only, pending sponsor confirmation under Q-004, Q-014, and Q-016. |
| D-042 | Phase 15A rebaselines evidence terminology and future-policy boundaries. Value + Source + Evidence + Date + Confidence + Status is a descriptive evidence lens, and presence/acquisition does not itself mean verification. A 90-day freshness period is only an example configurable future policy. Cache-first registry reuse, supplied-risk workflow reactions, refresh/OCDD/perpetual-KYC, and the production Zero-Touch/GoldTier deployment boundary remain unimplemented and require sponsor authority before runtime adoption. | Phase 15A Sponsor Rebaseline and Behaviour Alignment; Q-016/Q-017/Q-018 and relevant existing open sponsor questions. | **PROVISIONAL / PROJECT WORKING DECISION** pending sponsor confirmation; does not authorize runtime implementation. |
| D-043 | Phase 15C proposes exact `react-router@7.18.4` in declarative `BrowserRouter` mode, with browser location and `frontend/src/navigation.tsx` as the sole page/case navigation owner. AuthProvider, TanStack Query, backend RBAC/workflow, and live-intake mutation handlers retain their existing responsibilities; route entry is read-only and deployment requires a safe API/static-first SPA history fallback. | [ADR-001](ADR-001_FRONTEND_URL_NAVIGATION.md) and the Phase 15C frontend navigation handoff. | Proposed project technical decision; independent quality gate and owner acceptance pending. |
| D-044 | Phase 16 may reuse complete normalized synthetic Mock ACRA acquisition snapshots through one backend-global exact-key cache that is disabled by default. Enabled mode uses exactly 7,776,000 elapsed seconds (90 24-hour periods), one current entry per key, successful-complete-refresh replacement only, expiry without deletion, and no case-deletion cascade, TTL, purge, history, scheduler, forced refresh, sandbox/live caching, or existing-case reassessment. | Explicit project-owner approval O-16-01 through O-16-04; [ADR-002](ADR-002_REGISTRY_SNAPSHOT_CACHE.md) and `REGISTRY_CACHE_FRESHNESS_PROFILE.md`. | Provisional project POC decision only; not sponsor-confirmed production validity, sharing, licensing, or retention policy. |
| D-045 | Pre-Phase 22 manual-UAT stabilization presents case priority as Low/Medium/High/Unset while preserving the nullable 1–10 API and Mongo field. Canonical UI writes are Low=`1`, Medium=`5`, High=`10`; legacy reads map `1–3` to Low, `4–7` to Medium, `8–10` to High, and null to Unset. Priority still affects ordering only; it has no risk, SLA, routing, escalation, approval, or regulatory meaning. | Owner-requested demo/UAT vocabulary with compatibility for existing durable cases and no persistence migration. | `PROJECT_DEFINED_PROVISIONAL`; local POC presentation only; Q-016 remains open and sponsor confirmation is not claimed. |
| D-046 | The active synthetic Mock ACRA dataset may include one bounded Garden Business (`11111999A`) fixture with corporate owner SIM LIM (`111111111M`). Only inside this fixture, strict positive Decimal `shareAllotted` counts are divided by the active-count total, withdrawn holders are excluded, and exact six-decimal registry relationships feed the existing ownership engine. The dormant BizFile adapter remains uncomposed; no generic share-count interpretation, OAuth, raw-response tool, or provider activation is authorized. | Explicit Pre-Phase 22 teammate-reconciliation assignment adapting the historical Garden demo into the current Mock provider boundary without reusing the historical D-034 number. | `PROJECT_DEFINED_PROVISIONAL`; synthetic POC only, not legal ownership, voting rights, control, Live ACRA, or final UBO authority; Q-004/Q-012 remain open. |
| D-047 | The pre-Phase 22 feature candidate introduces one source-neutral, case-bound advisory-intelligence owner. Exact usable identifier/country rules precede an explainable weighted entity-linkage proxy; distinct identifiers/countries cannot auto-match and generic legal form is not independent corroboration. UBO advice consumes but never replaces the Decimal ownership result; mock risk uses only available signals and permanently states `NOT_COMPLIANCE_DECISION`. Thresholds/weights are editable in the existing catalogue and immutable per case. Mock risk does not affect readiness by default; an explicitly bound flag may ask the existing workflow owner for a typed human review before target execution. Schema-v4 cases retain no intelligence projection. | Owner-authorized local POC capability expansion and accepted [ADR-003](ADR-003_ONBOARDING_INTELLIGENCE.md), model cards, synthetic adverse evaluation, and Q-017 authority boundary. | `PROJECT_DEFINED_PROVISIONAL`; not sponsor-confirmed identity, UBO, risk, compliance, approval, or production policy. Q-004/Q-017 remain open. |
| D-048 | The pre-Phase 22 candidate may compose the sponsor-supplied GoldTier XPI dialect only as explicit `SANDBOX_PARTIAL`, reusing the existing target mapper/connector/ledger, policy catalogue, entity resolver, CLM plan, and schema-v5 owners. Mock stays default; there is no fallback. The adapter uses backend-only `user_id`, TLS 1.3 with certificate verification, no redirects, bounded timeout/body, separate write opt-in, eight authority-labelled target values, exact-match-only party reuse, and no automatic replay after an uncertain mutation. Related-party writes remain blocked until child-ID lifecycle and relationship authority are proven. | [ADR-004](ADR-004_GOLDTIER_XPI_SANDBOX_ADAPTER.md), sponsor XPI guide/Postman reconciliation, and bounded read-only sandbox observations. | `PROJECT_DEFINED_PROVISIONAL` / `SANDBOX_OBSERVED`; not PingFed, production authentication, Live interoperability, sponsor-approved target values, approval, or Q-016 authority. |
| D-049 | One CLM submission has one immutable GoldTier provider identity owned by its retained submission plan. New-plan defaults may come from current configuration, but an existing plan's execution input derives from the plan; mapper and connector modes are compatibility assertions checked before target-ledger/network activity. Mock/Sandbox drift fails closed with a typed sanitized error. Schema-v5 reconstruction rejects contradictory plan/input/matching-ledger modes while retaining plan-only and older-schema compatibility; no schema v6 is introduced. | Explicit owner-authorized remediation for exact-gate finding `GT-FINAL-RQG-01`, refining ADR-004 without adding an owner or provider router. | `PROJECT_DEFINED_PROVISIONAL`; no Live/provider activation, external write, Q-016 implementation, or Phase 22 authorization. |
| D-050 | The official ACRA API Marketplace Mock is a distinct provider lane with canonical mode `api_marketplace_mock`; local synthetic `mock` remains default, generic `sandbox` remains Partial, and `ACRA_BIZFILE` remains Dormant. A bounded read-only no-auth GET to the official entity-query Mock endpoint returned HTTP `401` on 2026-09-24. This is `OFFICIAL_MOCK_OBSERVED` failure evidence only, so the lane is `BLOCKED_AUTHORITY` and runtime activation remains disabled until Q-012 supplies the exact auth/subscription and secret-delivery contract. No OAuth, guessed static header, fallback, successful-payload mapping, Sandbox, or Live claim follows from the observation. | Explicit Pre-Phase 22 provider-orchestration direction plus the sanitized 2026-09-24 official-Mock diagnostic summarized in `docs/integration/ACRA_API_MARKETPLACE_MOCK_READINESS.md`. | `USER_AUTHORIZED_POC` / `OFFICIAL_MOCK_OBSERVED`; authentication and successful contract interoperability remain unresolved under Q-012. |
| D-051 | GoldTier customer Search runs read-only immediately after canonical Singapore registry identity. Its safe checkpoint is identity-bound and feeds the existing entity-resolution owner. Exact matches retain the target ID and skip Shell; no-match cases may create Shell only after readiness; ambiguous/conflicting/failed Search blocks all target writes. Shell, Policy, and Amend then advance through separate checkpoints in the existing target ledger, whose attempted/completed evidence remains the sole no-replay authority. | Sponsor-directed Pre-Phase-22 workflow clarification and [ADR-005](ADR-005_INCREMENTAL_GOLDTIER_ORCHESTRATION.md). | `SPONSOR_CONFIRMED` workflow intent; implementation remains Mock or `SANDBOX_PARTIAL`, not Live, approval, or a target-value decision. |
| D-052 | The main demo document defaults to `CERTIFICATE_OF_INCORPORATION_POC`; legal name, registration number and jurisdiction are required while absent address remains registry-only evidence. `accountEntityType` gets one editable `PROJECT_DEFINED_PROVISIONAL` placeholder; the other seven target values remain `TBD_SPONSOR`. HR alone gains `PROVIDER_SANDBOX_TEST` without `CASE_ACCESS`; its console exposes safe status/Search/dry-run/timeline, while standalone writes remain blocked by the case-ledger boundary and related-party dispatch remains blocked by child-ID lifecycle. | Explicit user-authorized POC direction for this Pre-Phase-22 increment. | `USER_AUTHORIZED_POC / PROJECT_DEFINED_POC`; not sponsor-approved KYC policy, target vocabulary, production RBAC, customer-write proof, Q-016 authority, or Phase 22 activation. |
| D-053 | The official ACRA API Marketplace Mock request-side authentication contract is OAuth2 Client Credentials at exact endpoint `https://api-sandbox.bizfile.gov.sg/authorizeServer/oauth/token?grant_type=client_credentials`, with HTTP Basic client ID/secret-key authentication, a documented 60-minute token lifetime, and downstream header name `token`. Bearer is not established; Mock and Production token hosts are separate, and no Production token URL is represented. This authorizes only optional inert backend credentials, fixed non-secret constants, and a pure Basic-auth constructor. It does not authorize a token request, method/body or response assumptions, caching/refresh, downstream token injection, runtime activation, fallback, Sandbox, or Live claims. | Explicit current task authority reconciling official ACRA authentication facts while preserving the Q-012 and provider-readiness gates. | `PARTIALLY_RESOLVED / BLOCKED_AUTHORITY`; Q-012 remains open for token response/error and downstream semantics, access/secret delivery, successful operation contracts/test UENs, errors/rates/retries/TLS, related operations, and sanitized success evidence. |
| D-054 | The official ACRA API Marketplace Mock may run only in explicit `api_marketplace_mock` mode with the exact fixed Mock token/API hosts, HTTP Basic token request, strict observed token schema, memory-only pre-expiry cache, raw downstream `token` header, verified TLS, no redirects, bounded transport, and no provider fallback. Strict entity/shareholder decoding is authorized for the observed Mock subset. Share counts remain source evidence; no percentage or relationship is derived without same-entity denominator and compatible share-class authority. Empty Garden shareholders therefore produce the existing truthful required-data stop. | Explicit owner authorization, supplied Postman exports, and sanitized bounded official Mock observations dated 2026-09-26. | `USER_AUTHORIZED_MOCK / MOCK_INTEROPERABILITY_OBSERVED`; not generic Sandbox, Production, Live, legal ownership, or final UBO authority. Q-012 remains open for provider errors/limits, complete operation and relationship semantics, denominator authority, and all non-Mock environments. |
| D-055 | For the bounded GoldTier XPI sandbox customer-policy request, `accountEntityType` and `productType` are compatibility-optional because the supplied sponsor collection sends both keys as explicit empty strings and the guide does not list them as minimum data. Unconfirmed policy placeholders serialize as empty; only explicit sponsor-supplied or sandbox-observed non-empty values may pass through. The other six target-policy values remain fail-closed prerequisites. This exception does not define Singapore mappings or production requiredness/vocabulary. | Explicit final Pre-Phase-22 task authority plus the current sponsor guide/collection reconciliation. | `USER_AUTHORIZED_POC / COLLECTION_OBSERVED`; sandbox-only, not sponsor-approved vocabulary, Production, Live, or universal mapping. Q-006/Q-007/Q-009/Q-010 remain open. |
| D-056 | For the bounded Singapore XPI POC, canonical ACRA legal name maps to `legalName`; UEN maps unchanged to `registration.registrationNumber`; both country fields are `SG`; `registration.registrationType=ACRA`; canonical ACRA address maps to `legalRegisteredAddress`; `customerExternalSystem=DSD`; `policy=Singapore`; and `bookingEntity=ANZBGL (Singapore Branch)`. ABN and Australian example values are prohibited. | Explicit 2026-09-27 owner direction reconciled with the corrected GoldTier OpenAPI 1.0.0 and sponsor material. | `SPONSOR_DOCUMENTED / USER_AUTHORIZED_POC`; bounded Sandbox POC only, not Production, Live, or universal future Singapore policy. |
| D-057 | The corrected standalone GoldTier OpenAPI 1.0.0 controls the current 17 KYC Customer Type and 23 Client Segment machine vocabularies. Older conflicting lists are `INVALID / QUARANTINED`, never unioned. KYC and segment have no global default; an authorized case-scoped selection is validated, retained with `USER_AUTHORIZED_POC`, and frozen before target dispatch. Sandbox target success additionally requires ledger-owned post-Amend Search by retained GoldTier ID with one exact same-ID candidate. | Final Pre-Phase-22 completion authority and sponsor-contract reconciliation. | `SPONSOR_DOCUMENTED / USER_AUTHORIZED_POC / SANDBOX_PARTIAL`; no automatic ACRA-to-KYC/segment mapping, production approval, related-party activation, or Live claim. |
| D-058 | New onboarding retains bounded initial legal-name/UEN/country identity and performs eligible Singapore GoldTier Search before ACRA. Exact match requires one provider candidate plus a prior durable exact-identity/same-ID read-back, then reuses verified target state and skips ACRA/Shell; no-match alone enters ACRA; ambiguous/failed Search stops. Schema v6 extends the one case envelope/target ledger with separate definitive/lifecycle resolution and explicit `PROVIDER_VERIFIED_RECOVERY`. Garden recovery keeps the original Shell uncertain, records later exact ID `143878` evidence with no replay, and never claims the ID came from the Shell response. Garden KYC/segment remain case-only `USER_AUTHORIZED_POC`; full vocabularies remain supported. | Explicit 2026-09-28 final-completion authority and [ADR-006](ADR-006_GOLDTIER_FIRST_PROVIDER_VERIFIED_RECOVERY.md). Supersedes only D-051's Registry-first ordering and D-049's no-schema-v6 statement. | `USER_AUTHORIZED_POC / PROVIDER_VERIFIED_RECOVERY / SANDBOX_PARTIAL`; not Live, Production, sponsor-approved classification policy, general recovery attestation for unreadable operations, related-party activation, or approval. |
| D-059 | The retained uncertain Garden Policy attempt may be lifecycle-resolved without replay through the existing target-ledger owner because authenticated read-only provider evidence proves exactly one `Singapore` Policy request on ID `143878`, status `Requested`. The recovery preserves the original uncertain transport outcome, records `PROVIDER_VERIFIED_RECOVERY` and `replayed=false`, and treats `Requested` only as proof that the provider-side request exists—not as approval, completion, or activation. Wrong ID/case/Policy/status fails closed; other uncertain Policy operations and all uncertain Amend operations remain stopped pending separate evidence/authority. | Explicit 2026-09-28 Garden-only continuation authority and read-only portal evidence; [ADR-006](ADR-006_GOLDTIER_FIRST_PROVIDER_VERIFIED_RECOVERY.md). | `USER_AUTHORIZED_POC / PROVIDER_VERIFIED_RECOVERY / SANDBOX_PARTIAL`; Garden-only, not a global recovery default, provider API read-back contract, Live claim, or approval semantics. |
| D-060 | A failed initial GoldTier Search is distinct from a normal no-match. It retains a safe typed failure category and leaves target identity unresolved, but it does not invalidate independent ACRA, document, reconciliation or ownership evidence. Those case-evidence stages may continue, then the automation terminates as a technical failure at GoldTier Search rather than creating reviewer work; Shell, Policy, Amend and all other target mutations remain blocked. Ambiguous candidates continue to stop before ACRA. No read-only retry is exposed until a safe late exact-match transition is proved. | Explicit 2026-09-28 operator-blocker-resolution clarification and [ADR-006 amendment](ADR-006_GOLDTIER_FIRST_PROVIDER_VERIFIED_RECOVERY.md#amendment--2026-09-28-failed-search-does-not-invalidate-independent-evidence). | `USER_AUTHORIZED_POC / SANDBOX_PARTIAL`; no Live claim, target retry, mutation replay, approval rule, or sponsor-confirmed failure policy. |
| D-061 | The bounded recoverable-onboarding candidate keeps one case, evidence model, policy owner, ownership engine, orchestration owner, and target ledger. It adds same-case identity correction plus read-only Search recheck; independent evidence continuation for ambiguous/failed Search; D-056-only policy rebind; pre-confirm KYC/segment edits; reviewed local manual economic-interest evidence; immutable explanatory blocker-decision metadata; and a durable exact-review confirmation required under lock before every Shell/Policy/Amend path. Schema v7 retains these facts with strict v1-v6 read compatibility. HR gains a read-only ACRA diagnostic surface using the exact composed connector and no case access. It supersedes only D-060's ambiguous-Search stop-before-ACRA and no-late-recheck limitations. | Explicit 2026-09-29 owner direction and [ADR-007](ADR-007_RECOVERABLE_ONBOARDING_AND_FINAL_CONFIRMATION.md). | `USER_AUTHORIZED_POC / ACCEPTED_MAIN` through PR #65; POC acceptance, not sponsor/Production authority. Not Live, provider-write authority, sponsor-approved UBO/reviewer/approval policy, arbitrary policy editing, related-party activation, or a full Exception Workbench. |
| D-062 | On 2026-10-01 the owner relayed sponsor confirmation of aggregated ownership `>= 25%`, comparator `GREATER_THAN_OR_EQUAL_TO`. This resolves the bounded default threshold/comparator only; incomplete evidence, legal/control tests and production UBO policy remain separate. KYC is evidence preparation in this POC; no separate KYC analyst, compliance approver, second final approver or mandatory four-eyes step is required. RM/onboarder Review & Send confirms the prepared create/update submission, not regulatory approval. Ready-for-Approval is not a local mandatory state unless the actual target API requires it; no such requirement is established by the inspected current XPI material. EDD is out of scope unless technically mandatory target authority is supplied. Local risk stays advisory: LOW continues, MEDIUM warns and continues, HIGH may ask RM attention where justified; probability alone does not become a hard blocker. PEP/sanctions/adverse-media ownership and requiredness must be reconciled before adding screening. Existing snapshots, catalogues, ledger history and historical decisions are preserved. | Explicit owner clarification dated 2026-10-01; [current contract and screening reconciliation](../integration/GOLDTIER_CURRENT_CONTRACT_AND_SCREENING_RECONCILIATION.md). Supersedes D-021 and later provisional threshold descriptions only for the bounded `>=25%` default/comparator, not complete legal/control or production policy. | `SPONSOR_CONFIRMED` bounded threshold/comparator; `USER_AUTHORIZED_POC` workflow clarification. Not production RBAC, legal/controller determination, screening ownership proof, target interoperability, external-write approval or mutation replay authority. |

| D-063 | For the bounded fresh-customer GoldTier Sandbox acceptance, current direct XPI follows Search/NO_MATCH -> Shell -> Policy -> optional Amend -> exact-identity Search/readback. Amend is omitted and recorded as `AMEND_NOT_REQUIRED` when no supported reviewed enrichment exists; ANZSIC/group-company values are never fabricated. Historical Amend failures and five-operation ledgers remain unchanged and readable. Policy success proves the requested operation under current XPI semantics and initiates KYC activity according to sponsor documentation; it does not prove completed KYC, screening clearance, risk approval, Ready-for-Approval, regulatory approval or Production onboarding. Returned safe identity fields are compared independently of Policy internals. | Explicit owner continuation dated 2026-10-01; fresh sanitized contract gate. Supersedes only unconditional Amend and the corresponding acceptance prerequisite, not uncertainty stopping or no-replay controls. | `USER_AUTHORIZED_POC / SANDBOX_PARTIAL`; one reviewed synthetic lifecycle, separate actual ACRA Mock Garden journey, isolated disposable Mongo7, no Garden/Production/related-party writes. |

| D-064 | Phase24C owner explicitly authorizes the existing POC policy owner to retain HR drafts/reasons/default-reset proposals, Director approval/rejection with proposer != decider and locked reauthorization/CAS, new ACTIVE/superseded versions, frozen case parameters, real registry/document/UBO/advisory/semantic consumers, and read-only synthetic impact metrics. Registry schema2 permits exact-key successful operation reuse and definitive NOT_FOUND TTL; case schema8 preserves schema1..7 reads without historical reinterpretation. Current exact registration/UEN GoldTier query remains unsupported and is explicitly skipped. | Explicit human authorization dated 2026-10-02; Phase24C plan and current amended policy/cache/persistence contracts. Supersedes only previous direct POC policy edits/reset/showcase creation and fixed-runtime complete-only Mock cache limitations. | USER_AUTHORIZED_POC / ACCEPTED_MAIN through PR #67; later feature-branch extensions require their own exact independent gate. No production RBAC, sponsor risk/legal/approval policy, new rebind, Live calls, target replay/mutation permission, publication or Phase25. |


## D-065 — post-Phase24 required source evidence during target reuse

Explicit combined F/G owner authorization permits closure of objectively fixable integration
debt. Exact prior target proof continues to skip Shell/new Policy and preserve same-ID
readback/no-replay. It does not remove required current registry evidence from the normal
ownership composition: the existing registry/cache coordinator acquires missing/stale
supported operations or reuses fresh evidence before downstream ownership. Current acquired
identity must match the identity actually searched; conflict removes exact-target binding.
Required source failure retains technical-failure precedence rather than reviewer work.
This supersedes only D-058's source-free ACRA skip in the current normal reuse path;
Search-first ordering, frozen policies, historical ledgers, schemas and valid legacy reads remain.
Authority: USER_AUTHORIZED_POC / combined Slice-G integration closure; no new sponsor rule,
provider API/schema/retry semantics, production access, target mutation permission or approval.

## D-066 — post-merge Session 1 recovery and application submission boundary

The explicit 2026-10-04 owner program starts from merged PR #68, main baseline
`1d426e0ceddc32d80b0aaec293c62fb761f2fecf`. Session 1 extends existing document,
reconciliation, orchestration and case-query owners. Identity correction retains
structured document observations/provenance and recomputes dependent comparisons;
successful recovery advances to the next authoritative blocker without target replay.
Created-date filtering on Cases and Onboarded uses server-owned automation `created_at`,
backend actor/team scope and filtering before portfolio paging. Inclusive calendar days
use the explicit project-defined Singapore UTC+08:00 convention: from midnight inclusive
through the day after Created to at midnight exclusive, with both bounds in query identity.

D-062's `USER_AUTHORIZED_POC` workflow clarification is reaffirmed: Review & Send is
the final local human approval for reviewed submission. No second unresolved local
approval stage is required. This does not close GoldTier-internal/Ready-for-Approval,
regulatory, legal/controller or production-policy questions. See the
[ADR-007 amendment](ADR-007_RECOVERABLE_ONBOARDING_AND_FINAL_CONFIRMATION.md#amendment---2026-10-04-post-merge-session-1-candidate).

Authority: `USER_AUTHORIZED_POC` current owner program; date treatment is
`PROJECT_DEFINED_POC`. Status: Session 1 independently PASS for candidate
`acc325730273d83d1bb39bbc066a89584b21dad7eebd2f8baee0afe73aed6bff` after one
documentation remediation. Later candidates require their own gates. Sessions 2/3
remain conditional on preceding gates; current-program
external Sandbox delivery are not proved, Camunda is out of scope, and no publication,
merge, new sponsor rule or external mutation authority follows from this record.

## D-067 — bounded local OCR and creator-reviewed ownership candidate

The 2026-10-04 owner program permits the S2 extension in ADR-009 through existing
document/IDP, access, ownership Decimal, reconciliation, orchestration, policy and
persistence owners. Native-first extraction plus optional bounded local Tesseract retains
page/method/quality and nonprobability evidence scores. Proposed ownership observations
require current creator-controlled source decisions; original observations, graphs,
supplements and receipts are retained. Calculable pre-submission evidence is editable,
readiness/confirmation becomes stale, and existing progression resumes. Retained target
attempts/submissions remain frozen and no replay is added.

Explicit Garden supplementation is known-case/successful-official-Mock only, separately
LOCAL_SYNTHETIC_SUPPLEMENT, never a failure fallback or official quantity claim. Schema9
owns new creator/provenance/source bindings; strict schema1..8 remains read-compatible
without writes or metadata/creator inference. Existing 0.85 frozen extraction threshold
and D-062 inclusive >=25% remain; no new INDUSTRY_PRACTICE_POC default is introduced.
Authority: USER_AUTHORIZED_POC; parser/quality/processing limits PROJECT_DEFINED_POC.
Status: implemented S2 candidate; fresh independent round1 PASS on the recorded
147-path candidate. Later S3 changes require their own combined review.
No external OCR, current-program external Sandbox proof, Live, legal compliance,
production reviewer policy, publication or merge follows from this decision.

## D-068 — post-closeout existing-customer identity and independent document review

The 2026-10-05 owner-relayed sponsor answers permit bounded existing-customer value
precedence/user choice, synchronous Shell/Policy/Amend, the current API user, accepted
Singapore POC policy/booking entity, optional ANZSIC/group-company enrichment,
Requested/Active Policy Amend, known validation-failure no customer-field application,
a separately reviewed NEW corrected Amend, no upstream idempotency/retry, and downstream
GoldTier four-eye/KYC ownership. This is bounded POC authority, not Production/PingFed
or new external-call permission.

Supplied EDS Search supports registrationNumber and externalSystemKey; current XPI
retains its four documented aliases. Per the current explicit owner correction, EDS
replacement is FUTURE_PROVIDER_FAMILY_DELTA, with no same-artifact resend required.
One retained incomplete Sandbox candidate may be creator-confirmed under current
Search/case/CLM/automation binding as CONFIRMED_EXISTING with actor/time/rationale.
This is distinct from provider EXACT_MATCH. The server selects the retained ID; the
action makes zero provider calls and never dispatches. Sufficient singleton Sandbox
UEN/country evidence can resolve provider EXACT_MATCH; accepted Mock proof remains.
The existing ledger skips duplicate Shell/new Policy and unnecessary Amend.

Document/reconciliation review may proceed while Search stays the earliest blocker.
Schema9 retains additive evidence/receipt fields; historical absence is unknown.
Existing owners, CAS, no-replay and final Review & Send remain. This supersedes only
the blanket no-candidate-confirmation/prior-local-case Sandbox restrictions in
D-058/D-061/ADR-007 and ambiguous-Search document-review guard. Historical failures,
uncertain target attempts, legal/control UBO, related-party child lifecycle and
original-file upload remain unchanged. See
[the authoritative family note](../integration/GOLDTIER_EXISTING_CUSTOMER_RESOLUTION.md).
Status: USER_AUTHORIZED_POC / SPONSOR_CONFIRMED bounded answers; unmerged remediation
with separate exact independent review required. Provider status remains SANDBOX_PARTIAL.

## D-069 - owner-authorized database-first synthetic happy paths

The explicit 2026-10-05 post-UAT request authorizes ordinary non-production Mock-lane
reuse through the existing registry coordinator/repository, a separately named
LOCAL_SYNTHETIC_UAT_V1 dataset and four entirely fictional complete graph fixtures.
[ADR-010](ADR-010_DATABASE_FIRST_SYNTHETIC_REGISTRY_REUSE.md) records the default and
trust amendment. Exact-key/freshness/COMPLETE validation, CAS/strict decoding, frozen
case policy, Decimal >=25% provisional candidates, auth and target no-replay remain.
The seed never claims fresh external ACRA retrieval and never populates GoldTier.
Missing/expired/incomplete seed uses configured ACRA; corruption fails closed.

Successful Search with zero candidates is already NO_MATCH and completes the stage.
400/rejection/timeout/transport/malformed remain failed existence checks blocking all
target mutations; independent registry/document work may continue under D-061.
No deterministic XPI construction defect was found; the reported real rejection cause
is unproved. Marketplace sample catalogues are operation-specific: an Entity Basic
Information UEN is not a whole-company fixture. Garden retains its separate bounded
known-case authority. The four local database fixtures are the recommended controlled
happy paths. Authority: USER_AUTHORIZED_POC / PROJECT_DEFINED_POC, pending fresh
independent gate. No external call, Production, Live, legal UBO, KYC or provider approval
authority follows.

## D-070 - owner-authorized document target classification and submission readiness

The 2026-10-05 continuation authorizes existing document/IDP and case-classification
owners to bind current explicit labelled evidence for Company - Private, Partnership -
Unregulated and Government; segment is explicit sponsor-vocabulary text, never inferred.
This is USER_AUTHORIZED_POC behavior with separate DOCUMENT source evidence and
PROJECT_DERIVED_POC policy authority, not sponsor-confirmed classification or approval.
Manual fallback covers unsafe fields; deterministic private-company/Government mismatch
is rejected. Fixed DSD/ACRA/Singapore/ANZBGL constants and unsupported product/account
fields are unchanged. Submission readiness is Complete when prerequisites are ready;
final Review & Send remains the only final human gate. Classification save is local.
Current schema10 retains the separate evidence, with strict read-only schemas1..9.
Beta/Gamma use six explicit synthetic ultimate interests through the same Decimal engine;
Government has separate classification coverage without unsupported control/share rules.
True uncertain attempted operations remain frozen/no-replay; empty intents do not imply
uncertainty. Provider classifications, external-call authority and sponsor questions
are unchanged. Fresh independent acceptance is required for this separate continuation.

D-070 R1 clarification: explicit prior user choices remain auditable, but disagreement
with current trusted labels blocks readiness until explicit compatible review. This is
conflict containment, not a universal document/user source-precedence rule. Shared
currentness is enforced again before snapshot/dispatch; stale prepared copy is blocked.

D-070 R2 clarification: all provider modes enforce current retained classification.
Explicit observations/selections require a complete compatible profile in Mock as well
as Sandbox; legacy Mock without any classification input remains optional. This closes
the same owner-authorized review/currentness boundary without new sponsor mapping rules.

D-070 owner-authorized follow-up,2026-10-06: an explicit USER review is bound to the
current trusted classification evidence fingerprint and authenticated actor. No candidate
now distinguishes absence/unsafe/conflict; newly trusted evidence stales prior reviews,
and fresh explicit same-value review of the current conflict is allowed. Later trusted
changes stale it again. This is owner-authorized bounded POC behavior, not a sponsor
source-precedence/legal classification rule. Existing owners, schema10, final confirmation
and no-replay remain. The owner accepts historical TC-R2-002 as documented execution
uncertainty: historical protected DB non-access NOT_CERTIFIED, owner accepted limitation
YES. New acceptance assesses current follow-up isolation only; no protected investigation
is authorized, and historical gate reports remain unchanged.

## D-071 - owner-authorized grouped blocker review and navigation

The 2026-10-10 assignment authorizes existing owners to apply one explicit group after
local draft selection, with whole-group validation and resumable section checkpoints
where atomic persistence is unavailable. ADR-011 records the trade-off. Draft save is
explicitly current-tab memory; no confidential browser storage or durable draft schema.
Navigation consumes current backend-authorized actions and focuses enabled controls.
Native PDF/TXT/DOCX/OCR separator normalization repairs existing explicit classification
extraction; D-070 vocabulary, compatibility/currentness and source evidence still apply.
No new sponsor field, source precedence, provider claim, approval or target write authority
follows. Candidate acceptance requires the fresh assigned independent quality gate.

## D-072 - owner-authorized Final Review editing and sponsor demo expansion

The 2026-10-10 owner addendum permits current creator evidence edits before target
confirmation/intent/attempt/result. Existing document, reconciliation, classification,
ownership and orchestration owners retain authority. Final Review document replacement
requires current automation, CLM and case-event versions as well as the existing document
version. It supersedes evidence, cancels the old confirmation, re-evaluates readiness and
requires a new explicit Send. A retained target execution freezes evidence edits; no
reset or target replay is permitted. Section checkpoints remain resumable, not atomic.

Four separate sponsor PDFs contain native identity/classification labels and an explicitly
informational LOCAL_SYNTHETIC_UAT_V1 registry annex. Aurora202400019S is a new fictional
65/35 graph; Pacific, Straits and Meridian retain their exact existing seed graphs. The
annex is not an independent client ownership declaration or official ACRA evidence. The
existing parser, source precedence and single Decimal engine are unchanged. Explicit
--sponsor-demo seed/check selects four through the existing repository owner; the legacy
eight-fixture default and every Orion asset remain. The existing negative018R test remains.

Acceptance requires eight actual browser journeys, affected checks and the fresh
SPONSOR_DEMO_FINAL_QUALITY_GATE.md for the expanded frozen content. Offline XPI Sandbox
simulations do not establish real Sandbox interoperability; real Sandbox UAT is
NOT_VERIFIED. No new provider status, sponsor mapping/policy, schema or publication
authority is introduced.

## D-073 - proposed AI Assistant knowledge loop (proposed, not accepted)

PR #99 proposes a reviewed knowledge loop inside the separate AI Assistant service:
SQLite plus a rebuildable ChromaDB index, append-only versions, maker-checker over each
edit chain, decisions bound to the reviewed content hash, two-person retirement,
team-scoped review and
resolutions, redacted drafts without browser-supplied assistant text, telemetry off and
loopback-only embeddings, and an `@assistant-ui/react` panel over the existing client.
[ADR-012](ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md) records the design. Status: proposed,
not accepted. Owner direction (G6): the PR89 exact-line output catalog keeps its
deterministic guarantees and stays mandatory; sentence-level checks are an additional
safeguard. ADR-012 section C proposes adding approved knowledge only as verbatim, tagged
sentences that pass those checks, with entry titles and follow-up questions under the
same checks; that extension requires explicit owner acceptance. For knowledge content,
two-person approval is the primary control and the checks are a best-effort filter
with documented limits. Accepting the unlocked chromadb Python footprint (62 transitive
packages) is proposed and requires owner acceptance. Reusing POLICY_APPROVE and
POLICY_MUTATE for knowledge review is PROJECT_DEFINED_PROVISIONAL; review authority
stays UNKNOWN_BLOCKED (Q-014). No CLM backend write, schema, provider status or Live
claim follows.

## D-074 - owner-accepted ADR-012 section C output policy

On 2026-10-21 the repository owner accepted ADR-012 section C option 1, verbatim: "I accept
ADR-012 section C option 1: the exact-line catalog stays mandatory and approved knowledge
sentences are added as exact [Gn]/[Pn] lines, with two-person approval as the primary
control." The PR89 exact-line catalog stays the mandatory gate for model text, in whole
answers and while streaming. A sentence of a retrieved, approved entry the user may see is
offered only verbatim as `<sentence> [Gn]` or `[Pn]` and only if it passes the sentence
checks; entry titles and follow-up questions stay under the same checks. Two-person approval
bound to the reviewed content hash is the primary control for knowledge content; the
sentence checks remain a best-effort filter with the limits and residual risks recorded in
ADR-012 section C (`KNOWLEDGE_FILTER_LIMITS`). The independent architecture review of
`8457f02` (PROCEED, conditional on this acceptance and on the chromadb footprint) reviewed
the same section C. This accepts section C only and supersedes only D-073's statement that
the extension requires explicit owner acceptance. Still open: section A's unlocked chromadb
footprint (acceptance or a pinning policy), section B as proposed with PR #99, and the
real-embedding retrieval evaluation (or a waiver). Unchanged: the POLICY_APPROVE and
POLICY_MUTATE mapping stays PROJECT_DEFINED_PROVISIONAL and review authority stays
UNKNOWN_BLOCKED (Q-014). PR #99 stays Draft until the open items are settled.
`USER_AUTHORIZED_POC`; not sponsor review policy, and no CLM backend write, schema,
provider status or Live claim follows.

## D-075 - owner direction for PR #99 merge readiness

Owner direction 2026-10-21 for PR #99 merge readiness: keep ADR-012 option 1 and D-074 as
accepted; retain the SQLite plus ChromaDB implementation with the current direct ChromaDB
version pin (`chromadb==1.5.9`), with no new dependency management system or broad
dependency upgrade; the real-model embedding evaluation is
`NOT_EXECUTED — MODEL NOT INSTALLED / OWNER-DEFERRED` to a later validation phase, an
accepted scope limitation for the local POC and not a passing test or proof of semantic
retrieval quality; the local synthetic and mock embedding tests remain the functional
retrieval evidence. Q-014 review authority stays UNKNOWN_BLOCKED and no sponsor approval or
production readiness is claimed. Cycle 9 aligns the knowledge-review scope of Directors with
the CLM backend's global Director scope (a defect fix, not a new authority).

## D-076 - owner-authorized registry-driven recursive ownership discovery (candidate)

The 2026-10-23 owner assignment (Master Assignment v4) authorizes bounded Singapore Mock
recursive corporate-owner discovery: each verified-UEN corporate owner is acquired from
its own registry record through the existing coordinator, cache-first, and attached to
the one Decimal graph ([ADR-013](ADR-013_REGISTRY_DRIVEN_CORPORATE_OWNERSHIP_DISCOVERY.md)).
Garden `11111999A` and SIM LIM `111111111M` become separate synthetic Mock issuers using
the owner-supplied Garden shareholder body; D-046 equal-unit derivation stays inside
these two fixtures and the accepted Garden UBO percentages are unchanged. The local
dataset namespace becomes `MOCK_ACRA_SYNTHETIC_V2`; the official Marketplace Mock keeps
its labelled Garden supplement because it has no separate SIM LIM ownership operation.

New editable rules: trace threshold 10% (never above the D-062 UBO threshold; retrieval
priority only), corporate depth 5 (1-7), business call budget disabled (max 10, 1-32).
Fixed technical caps: 32 issuer lookups, 60 s, sequential. Unresolved branches, deferred
branches and repeated cross-issuer person identifiers keep review required. Authority:
`USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated acceptance and
independent gate. Not legal UBO policy (Q-004), real ACRA subsidiary capability (Q-012),
person identity or traversal authority (Q-019), cross-lane cache sharing or GoldTier
hierarchy writes (Q-002). A 0% UBO threshold can no longer be activated because the
positive trace threshold may not exceed it.

## D-077 - owner-authorized hybrid Marketplace Mock plus local direct overlay (candidate)

The 2026-10-23 owner assignment (Master Assignment V5) authorizes an explicitly opt-in
non-production composition for the official ACRA API Marketplace Mock lane:
`ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay` (default
`garden_legacy_supplement` keeps the accepted flattened Garden fixture unchanged). A
whitelisted catalogue (`connectors/hybrid_ownership_overlay.py`) declares per-issuer
*direct* holders only for two named scenarios: `GARDEN_DIRECT_OVERLAY_V1` (the
owner-supplied Garden body, direct rows only) and `FIVE_LAYER_MARKETPLACE_HYBRID_V1`
(root `201511222D` OPQ PTE. LTD. plus sample-catalogue UENs `200811111M`, `201688888A`,
`200811111K`, `199801111H`, `111111111K`). Declared units use a locally declared
complete same-class active denominator and the D-046 six-decimal rule; links are
`LOCAL_SYNTHETIC_RELATIONSHIP`/`LOCAL`, never ACRA or Mock provenance.

The root overlay applies only to fresh successful same-UEN official Marketplace evidence;
failure, staleness or another lane never selects it. The source classification
`OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY` may enter the existing D-076 discovery
coordinator (the flattened legacy supplement still may not). Each corporate holder gets
its own cache-first official lookup; only a definitive NOT_FOUND or an official entity
profile without quantitative rows lets the scenario attach that issuer's declared
holders (`LOCAL_SYNTHETIC_OVERLAY`, identity `LOCAL_SYNTHETIC_IDENTITY` or
`OFFICIAL_MOCK_ENTITY_PROFILE`). Provider/cache failure, identity or lane mismatch and
official shareholder rows leave the branch unresolved. Every hybrid analysis carries
`SYNTHETIC_OWNERSHIP_EVIDENCE`, so it is always REVIEW_REQUIRED with
REVIEW_REQUIRED/INDETERMINATE candidates; a separately labelled
`synthetic_basis_threshold_result` applies the same inclusive comparator to the declared
basis for demonstration only. Topology, official identity and quantitative evidence
completeness are recorded separately. A fresh definitive NOT_FOUND cache hit now counts
as a cache hit (zero provider calls) in discovery counters. Case envelope schema 12.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. Not ACRA ownership, Live or production evidence, legal
UBO policy (Q-004), Marketplace relationship/denominator capability (Q-012), person
identity authority (Q-019) or GoldTier hierarchy writes (Q-002). No live Marketplace
probe was run in the implementing session (credential access was not permitted).

## D-078 - owner decision on manual replacement of D-077 hybrid analyses

Owner decision 2026-10-24, A1 of the Garden/OPQ REVIEW_REQUIRED investigation: option 1,
keep current behavior. The existing creator source decisions from the PR #69 contract
(`USER_SUPPLIED_DECLARATION`, `CURRENT_EVIDENCE`, `DOCUMENT_OBSERVATIONS`), each subject
to its existing conditions, may replace a D-077 hybrid analysis with no new restriction.
That includes `CURRENT_EVIDENCE` retention of its `LOCAL_SYNTHETIC_RELATIONSHIP` graph.

The replacement is a `MANUAL_DECLARATION_POC`/`LOCAL` creator declaration. It drops
`SYNTHETIC_OWNERSHIP_EVIDENCE` and, because manual sources carry no registry legal form,
`OWNERSHIP_METHOD_UNSUPPORTED`. It is never ACRA, Mock or Live evidence, and never a legal
UBO determination. The creator remains accountable through three existing safeguards:
- the review receipt (actor, time, source selection, replaced analysis and version);
- the retained prior hybrid analysis, with its source classification,
  `SYNTHETIC_OWNERSHIP_EVIDENCE` and synthetic links. Retention is bounded to the latest
  four prior analyses. After four further snapshot-creating changes (manual replacements
  or document/identity reloads), the hybrid snapshot is no longer in the ownership record.
  The hybrid analysis itself carries no receipt. The `CURRENT_EVIDENCE` receipt that names
  it is held by the next analysis and drops out one change later. This bound is audit
  history only: since D-120 the D-081 restriction does not depend on it;
- the separate target-dispatch confirmation required before any GoldTier target mutation.
  GoldTier Search runs earlier and is read-only.

An incomplete replacement still requires review. No runtime behavior changed.

Narrowed by D-081 (owner F1 decision, 2026-10-24) for POC-assumed equal-unit links only:
`CURRENT_EVIDENCE` cannot keep them, and a declaration cannot redeclare them unchanged.
D-120 makes that restriction durable and compares by business identity.

Authority: `USER_AUTHORIZED_POC`. Not sponsor-confirmed reviewer authority (Q-014), legal
UBO policy (Q-004) or Marketplace ownership capability (Q-012).

## D-079 - owner-authorized official shareholder evidence without an entity profile (candidate)

The 2026-10-24 owner assignment (Sim Lim official ACRA shareholder acquisition) approved
proposal P1. It applies only in the official ACRA API Marketplace Mock composition, to an
identified corporate holder that:
- is not a scenario-overlay issuer;
- has a verified Singapore UEN discovered from its parent;
- has an entity-basic profile that is a definitive NOT_FOUND.

Such a holder gets one additional bounded `coShareholdersDetails` read through the existing
connector, and the existing strict decoder binds the returned UEN to the request. This is
an exception to the accepted rule that the company-shareholder operation dispatches only
for a recognized COMPANY legal form.

The rows are retained beside the graph as `official_shareholders` on the issuer's
discovery record, with official Marketplace Mock operation provenance. The record carries
outcome `PROVIDER_PARTIAL`, reason `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE` and a
fetched or cache-reused lookup. Under these rules:
- no canonical identity, legal form, verification, graph party, edge or percentage is
  created;
- only explicitly Active rows are current interests, and withdrawn rows remain history;
- corporate holders are not recursed without a supplied verified UEN;
- without a same-entity authoritative denominator the branch stays unresolved, an
  `OWNERSHIP_DENOMINATOR_REQUIRED` issue is added and the case stays REVIEW_REQUIRED, so
  readiness and GoldTier remain blocked;
- an empty result keeps `NOT_FOUND` (reason `OFFICIAL_SHAREHOLDERS_EMPTY`), and failures
  stop safely and are never cached.

The single registry coordinator caches the evidence in the existing cache under contract
key `MARKETPLACE_SHAREHOLDERS_V1` (registry cache schema 3). COMPLETE evidence follows the
freshness policy and EMPTY evidence the negative TTL. Case envelope schema 13; v1..v12
readers reject the new fields. Retaining `shareType`/`currency` is deferred. The unchanged frontend does not render the rows. Its discovery table shows the issuer's
outcome label ("Incomplete registry evidence") with the reason code, and the issue list
shows the new message.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. Not ACRA ownership, Live or production evidence, legal
UBO policy (Q-004), Marketplace denominator or relationship capability (Q-012), or person
identity authority (Q-019).

## D-080 - owner-authorized share-class retention on official shareholder rows (candidate)

Owner decision 2026-10-24, during the Sim Lim follow-through assignment. It lifts the
D-079 deferral of `shareType`/`currency` retention.

Evidence: an owner-authorized, bounded read-only verification against the official
Marketplace **Mock** (2 token requests and 7 GETs, verified TLS). 8 of the 9 receipts
recorded HTTP 200. The status of the first capital read was not captured. SIM LIM
`111111111M` returned four rows:

| Row | Category | Status | Units | Share type | Currency |
|---|---|---|---|---|---|
| 1 | Corporate | Withdrawn | 10000 | Ordinary | SINGAPORE DOLLAR |
| 2 | Individual | Active | 900 | Ordinary | SINGAPORE DOLLAR |
| 3 | Individual | Active | 100 | Preference | SINGAPORE DOLLAR |
| 4 | Individual | Active | 100 | Others | SINGAPORE DOLLAR |

The supported `coCapitalDetails` operation for the same UEN returned an explicit empty
collection (recorded read: HTTP 200, 0 entities). The current rows therefore span three share classes, with no same-entity
denominator, and units of different classes are not comparable.

Decision:
- **Retained.** Official rows read without an entity profile keep each row's own source
  `shareType` and `currency` as untrusted bounded text, beside the existing fields.
  - No mapping, class rule, weighting, cross-class sum, denominator or percentage is
    created. D-079's edge, identity, recursion and readiness rules are unchanged.
  - Ordinary acquisition bundles never carry a share class.
- **Issue message.** When an issuer's current rows report more than one share class
  (unreported counts as one), the `OWNERSHIP_DENOMINATOR_REQUIRED` message says that
  current rows mix share classes.
- **Persistence.**
  - The cache contract key becomes `MARKETPLACE_SHAREHOLDERS_V2` (registry cache schema 4).
    D-079 `MARKETPLACE_SHAREHOLDERS_V1` schema-3 entries stay readable without a class,
    and are never reused or rewritten.
  - Case envelope schema 14. An exact v13 reader rejects a share class, and an explicit
    null keeps the D-079 meaning. Cases analysed before D-080 are not re-analysed.
- **Local fixture.** The owner-supplied local synthetic SIM LIM fixture (D-076) declares
  every row `Ordinary`. Its accepted flattened Garden result (D-046 equal-unit
  derivation) is unchanged and remains labelled synthetic. It is not the official Mock's
  class structure.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. Mock observations only, never Live or production
evidence. This decision gives no share-class economic or control rule (Q-004),
Marketplace denominator semantics (Q-012) or person identity authority (Q-019).

## D-081 - owner scope correction: POC equal-unit distribution of official rows (candidate)

Owner decision 2026-10-24 (scope correction during the Sim Lim follow-through). The owner
restores the existing share-distribution convention, `holder active units / issuer's total
active units x 100` (the D-046 six-decimal rule), for official rows in the **opt-in
hybrid overlay lane** (`ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay`, a
whitelisted scenario root).

This is an owner-declared POC assumption: an issuer's returned current units are its
complete, equally weighted ownership units. ACRA has not verified an issued-share
denominator, and no class rights are confirmed.

When D-079 retains an issuer's official rows in that lane:
- **Denominator.** The issuer's own explicitly Active rows form its denominator; it is never
  computed across issuers.
  - Withdrawn rows stay history.
  - Classes are pooled as equal units for this labelled illustration only. Each row keeps
    its true class, status and Marketplace provenance (D-080).
- **Links.** Each active holder gets one link with the existing `quantized_unit_share`, with
  provenance `LOCAL_POC_ASSUMED_EQUAL_UNITS` / `LOCAL`.
  - Links merge through the existing discovery merge (issuer-scoped identity, limits, graph
    validation).
  - The unchanged Decimal engine computes paths, aggregation and the bound.
- **Corporate holders.** An active corporate holder without a supplied verified UEN becomes
  an unresolved `UNVERIFIED_UEN` branch; no identifier is inferred.
- **Record.** The issuer record keeps outcome `PROVIDER_PARTIAL` and its rows. Its reason
  becomes `OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS`, and it counts as topologically attached.
  `graph_complete`, official identity and quantitative completeness stay false.
- **Review.** Candidates stay `REVIEW_REQUIRED` / `INDETERMINATE`, with the existing labelled
  synthetic-basis comparison. The `OWNERSHIP_DENOMINATOR_REQUIRED` issue says the percentages
  assume equal POC units, not an ACRA denominator. Readiness and GoldTier stay blocked
  (narrowed by D-082 for eligible cases when its opt-in policy is enabled).
- **Failure.** Rows that cannot support the convention (no positive current units,
  duplicate or self identifiers) or a refused merge attach nothing. D-079's retained
  outcome is unchanged.
- **Rounding.** Six-decimal links can total slightly above 100 (at most n × 0.0000005; six
  equal holders give 100.000002). The unchanged coordinator then reports no unresolved
  bound, and review stays required.
- **Creator decisions (owner F1 decision, option B).** POC-assumed links cannot
  independently satisfy ownership-evidence or readiness requirements. The single manual
  replacement path (`replace_review_required_source`, inside the case lock, after the
  existing CAS and staleness checks) refuses with `409 OWNERSHIP_POC_EVIDENCE_REVIEW_REQUIRED`
  before any replacement, confirmation reset or readiness change when:
  - `CURRENT_EVIDENCE` would keep a graph holding POC-assumed links, directly or through an
    earlier kept copy (followed through the retained receipts);
  - `USER_SUPPLIED_DECLARATION` would redeclare any POC-assumed link unchanged. D-120
    defines "unchanged" against a durable ledger, by business identity, not party ID.

  Other D-078 decisions are unchanged. A declaration with different values, or
  `DOCUMENT_OBSERVATIONS` matching current document observations, follows the existing
  rules.
- **Presentation (owner U1–U4, 2026-10-24).** The frontend shows the backend's
  `synthetic_basis_threshold_result` as a separate "Assumed-basis matches" count and as a
  "Meets the threshold on an assumed basis — review required" list (explorer, selected
  holder, Review & Send).
  - Each entry is labelled by its link provenance (POC equal-unit assumption or local
    synthetic overlay basis).
  - Formal provisional UBO counts, highlights, client-detail owners, readiness and GoldTier
    are unchanged.
- **Scope.** The default official lane, the local synthetic lane, the Garden legacy
  supplement and the five-layer arithmetic are unchanged. Case envelope 14 (still
  unreleased) carries the links; an exact v13 reader rejects them.

Garden → SIM LIM (live-observed shape):
- 900 / 100 / 100 of 1100 gives 81.818182 / 9.090909 / 9.090909;
- through 62.5% that is ABCD123 51.13636375, TAN WEI LING and EFGH2345 5.681818125 each;
- LIM CHOON HUAT stays 37.5.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. This is not ACRA ownership, a verified denominator, a
legal UBO determination (Q-004), Marketplace denominator semantics (Q-012) or person
identity authority (Q-019).

## D-082 - opt-in POC ownership acceptance at the readiness boundary (candidate)

Owner policy direction and decisions D1–D4, 2026-10-24, with the owner's design-review
guardrails. In the approved hybrid demonstration lane, an eligible analysis whose only open
questions are its declared POC assumptions no longer needs manual ownership verification
before readiness. D-082 narrows D-081's "readiness stays blocked" for those cases only.

- **Opt-in (D3).** `ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE=accept_eligible_poc`; the
  default is `disabled`.
  - Settings reject it outside `api_marketplace_mock` with `hybrid_direct_overlay`.
  - The ownership service refuses it without the hybrid overlay owner.
- **Separate record, unchanged review (D2).** A new analysis that passes eligibility gets
  `poc_acceptance`: policy `D082_HYBRID_POC_EQUAL_UNITS_V1`, plus its case, analysis,
  version, identity and scenario binding, the accepted issue codes, the POC link ids, the
  descriptive officer-role counts (current and ceased; no identifier or digest), and a
  content fingerprint of every input.
  - State stays `REVIEW_REQUIRED`. Issues, evidence, candidates, Decimal values and formal
    classifications (`REVIEW_REQUIRED`/`INDETERMINATE`) are unchanged.
  - The ownership event code is `OWNERSHIP_POC_BASIS_ACCEPTED`.
  - Terminal analyses are never re-analysed, so enabling the flag accepts no existing case.
- **Eligibility (fail-closed).** All of these must hold:
  - the whitelisted `GARDEN_DIRECT_OVERLAY_V1` scenario, rooted at 11111999A;
  - an official Marketplace Mock provider (`ACRA_REGISTRY_ACQUISITION`/`MOCK`);
  - complete topology, with no unresolved person;
  - every retained issuer POC-distributed;
  - only overlay or POC links;
  - no document discrepancy that needs review, and no manual receipt;
  - every person's assumed-basis comparison `MET` or `NOT_MET`;
  - exactly one each of `OWNERSHIP_DENOMINATOR_REQUIRED` and `SYNTHETIC_OWNERSHIP_EVIDENCE`,
    plus `UBO_REVIEW_REQUIRED` only under D1.
- **D1 = B (descriptive officer roles), corrected by owner R1 decision (exact observed
  set).** The live Marketplace Mock returns four official `OFFICERS` `ROLE = OWNER` records
  for 11111999A: **three current and one ceased** (cessation date set). The earlier "four
  current" assumption was incorrect, and the first implementation bound only that shape
  (independent QG finding R1). The exception now applies only to that scenario, and only
  when the evidence is exactly those four records:
  - Each must be `ACRA_REGISTRY_ACQUISITION`/`MOCK`/`OFFICERS`, bound to 11111999A, with a
    distinct officer and the adapter's stable evidence id. Exactly three must be current
    and one `CEASED`.
  - Their identities and expected statuses must match, in any order, a protected
    backend-only allowlist: `ACRA_MARKETPLACE_POC_OFFICER_ROLE_KEY` and
    `ACRA_MARKETPLACE_POC_OFFICER_ROLE_ALLOWLIST` (HMAC-SHA256 digests of each stable id
    with `=CURRENT`/`=CEASED`).
  - The stable id is an unsalted hash of an officer identifier, so it is treated as
    sensitive. Only keyed digests are configured, and real values never enter the
    repository, fixtures, reports or logs.
  - An absent, malformed or duplicate allowlist, any substitution, addition, removal or
    status change, a wrong issuer, operation or provenance, or a disabled policy refuses.
  - The roles stay in the evidence with their provenance, the ceased one as history only.
    None of them contributes to percentages, UBO calculation or classification, and
    `UBO_REVIEW_REQUIRED` stays on the analysis.
  - Recognising this known Mock dataset for the demonstration does not mean the officer
    roles corroborate the synthetic shareholder relationships.

  Any other role, evidence kind, count or issue stays blocking.
- **Runtime authority (P1).** Readiness asks the ownership service, which honours a recorded
  acceptance only while its own composition enables the policy, the case identity is
  current, and recomputed eligibility equals the record.
  - Disabling the setting, or restarting outside the Mock hybrid lane, restores
    `OWNERSHIP_REVIEW_REQUIRED`, refuses target confirmation, and makes resume restore the
    ordinary ownership hold. The audit record itself is kept.
  - **F2.** On resume, an OWNERSHIP checkpoint completed on a no-longer-current acceptance is
    rebuilt: the hold is raised and every earlier target-confirmation hold is withdrawn.
    After re-enabling, a hold raised for that same analysis is obsolete, so resume returns
    to target confirmation. Nothing advances or dispatches while authority is withdrawn.
    The rebuild applies only to analyses carrying a POC acceptance; every other review
    analysis keeps the existing restoration. Until that resume, the case header shows the
    ordinary ownership-attention status, never "POC basis accepted". The UI has no
    dedicated resume control for this operator toggle; the existing resume operation
    clears it.
  - **F6.** Immediately before the first irreversible GoldTier write, a snapshot frozen on a
    POC acceptance (ownership reference `REVIEW_REQUIRED`) re-checks that authority. It
    refuses with `CLM_NOT_READY`, attempting no target operation, if the authority has been
    withdrawn. Normal (`ANALYZED`) dispatch and recovery of an already attempted write are
    unchanged. The refusal is recorded as the automation's existing terminal technical
    failure at the GoldTier stage. Re-enabling the policy does not resume it automatically,
    and no target operation was attempted.
- **Readiness.** CLM ownership readiness is READY (reference: the analysis id). Zero-touch
  completes OWNERSHIP with event code `OWNERSHIP_POC_BASIS_ACCEPTED` and raises no exception.
  - Target confirmation remains mandatory. Nothing is sent automatically.
- **GoldTier (P1).** The Mock target snapshot records the ownership reference
  (`REVIEW_REQUIRED`) and **no** provisional UBO ids (count 0), because only
  `PROVISIONAL_UBO_CANDIDATE` ids enter it. Related-party preparation is also empty. No
  target UBO payload is created, and execution idempotency/no-replay is unchanged.
- **Freshness (P2).** Any version, content, identity or document change revokes the
  acceptance. A creator replacement or reload creates a new analysis without one; the
  replaced acceptance stays in `prior_analyses`. D-081 Option B still refuses keeping or
  redeclaring the POC links.
- **Persistence (D4).** The unreleased case envelope 14 is extended (optional field). An
  exact v13 envelope rejects a non-null acceptance on current or prior analyses. A corrupted
  policy fails closed. Rollback to a v13 reader already rejects every v14 POC case.
- **UI.** Backend authority only (`poc_basis_accepted` on the ownership response):
  - the status reads "Ownership calculated — POC basis accepted", with the technical
    disclosure;
  - per the owner (2026-10-24), the POC disclosure replaces any "UBO classification remains
    review-required" warning on an accepted case. The formal classification field is
    unchanged and still shown on each candidate;
  - **F4.** On an accepted case, the assumed-basis section reads "Meets the threshold on an
    assumed basis", and its explanation drops "do not clear ownership readiness" while still
    disclosing the POC assumptions and that these are not verified legal UBO
    determinations;
  - the officer-role records are disclosed as descriptive context for this named exception
    only;
  - **F5.** Review & Send reports assessed natural persons, formal provisional UBO
    candidates and assumed-basis matches separately (Garden: 4, 0, 2). The target snapshot
    is unchanged;
  - the manual form stays available.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. This is not ownership verification, a legal UBO
determination (Q-004), Marketplace denominator semantics (Q-012) or Live evidence.

## D-083 - proposed AI Assistant feedback, enhancement requests and single-reviewer POC mode (PROPOSED)

Status: PROPOSED by the project team on 2026-10-21. **It relaxes D-074's two-person control
for the POC and needs the repository owner's (Shane's) explicit acceptance before merge**;
it is not accepted. It amends ADR-012 section A.

Feedback. "Yes, helpful" only records the rating with the case context (blocker codes,
fields, stages): it drafts nothing, adds nothing to the review queue and changes no retrieval
or ranking; the Director's stats show confidence by topic (helpful and not-helpful counts per
blocker code). "Not helpful" starts an enhancement request: a non-blank note is required (422
otherwise; the panel keeps Send disabled) and is redacted before it is stored. The panel no
longer sends the conversation.

Enhancement requests. Directors (POLICY_APPROVE) handle them end to end in the Knowledge
review window; HR does not, as it has no case access. A Director either writes the fix as a
past case or a guidance change (new guidance or a new version of existing guidance) linked to
the request, or closes the request with a required reason. The fix is redacted against the
request's own case (loaded with the Director's session) and by pattern, then waits for review
like any other entry: publishing it resolves the request, rejecting it opens the request again.
Only an open request can be handled. Both actions recheck the caller inside the SQLite write
transaction.

Single-reviewer mode (relaxes D-074). D-074 made two-person approval bound to the reviewed
content hash the primary control for knowledge content. The POC's synthetic users have only
one Director (olivia-koh), and only POLICY_APPROVE can approve knowledge, so with author ≠
approver no fix a Director writes could ever be published. The setting
`AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER` (default true for this POC) therefore lets a reviewer
approve or reject an entry they wrote or edited. An approval shows the reviewer the final
entry text and needs an explicit confirmation (`confirm_single_reviewer`, refused with 403
otherwise); every such decision, approval or rejection, is recorded as single-reviewer in
the review history (`reviews.single_reviewer`), and the Review window lists the entries
currently published that way and says so in its confirm step. With the setting false the
two-person rule applies unchanged. Unchanged in both modes: decisions bound to the content
hash, the sentence checks, redaction, team scope, and retiring an approved entry (official
guidance included) still takes two reviewers. SQLite schema v4 adds `reviews.single_reviewer`
(0 for existing rows), a `resolved` request status, a nullable `feedback.close_reason` and
`feedback.entry_version`: a request is linked to the exact version of its fix (a reviewer's
edit moves the link), so a decision on another version of the same entry leaves it alone.

The POLICY_APPROVE mapping stays PROJECT_DEFINED_PROVISIONAL and review authority stays
UNKNOWN_BLOCKED (Q-014). Not sponsor review policy; no CLM backend write, provider status or
Live claim follows.

## D-084 - proposed AI Assistant answer records, request lifecycle and document upload (PROPOSED)

Status: PROPOSED by the project team on 2026-10-25. Not accepted.
**Each of D1 to D6 below needs the repository owner's (Shane's) explicit acceptance before
code.** On Tasha's instruction, D1 and D2 (answer records) were built ahead of that
acceptance on `feat/ai-assistant-answer-records`; that PR does not merge until Shane accepts
D-084. It amends ADR-012 (Amendment 1) and builds on D-083 (still proposed; its code is on
main since PR #108). If D-083 is not accepted,
this entry is revisited with it.

All three parts stay inside the AI Assistant service and its local knowledge store (schema
v5), and the assistant stays read-only towards the CLM backend. The exact-line catalog,
maker-checker (D-074, with D-083's POC single-reviewer mode if accepted), the caller
rechecks inside the SQLite write lock and read-only CLM backend access are unchanged.

| # | Decision | Options | Recommendation |
| --- | --- | --- | --- |
| D1 | Store answer records on the assistant's machine | yes, with retention and Director-only access / no | Yes: the record is produced by the server, so it cannot be faked by the browser. Directors and the RM who asked may view it; every view is logged. **This relaxes ADR-012 section A** (no CLM case data beyond redacted drafts): the record keeps the RM's question unredacted and a snapshot of case state. |
| D2 | Retention | 7 days for every record not linked to a request (unrated or rated "Yes, helpful"), 30 days after a linked request ends as Resolved or Closed / other | That (the team's proposal; numbers to confirm). The helpful count in the stats is kept without the record. The earlier answers a Director is shown with a request (at most 2, same user and case) are kept with it and follow its 30-day rule. |
| D3 | How uploaded files are read | (a) Markdown and text only, no new library; (b) PDF and Word in the assistant, adding the backend's pinned `pypdf`, `pypdfium2` and `Pillow` and its isolated-process pattern; (c) the CLM backend extracts the text through a Director-only endpoint | (a) for the POC. (b) or (c) later, by a separate decision: (b) creates a second document parser, (c) touches the backend, a teammate's area. |
| D4 | Who can upload | Directors only / Directors and HR | Directors only, matching review rights. |
| D5 | Real sponsor documents | allowed with sponsor and owner agreement / synthetic and public only | Synthetic and public only for the POC. |
| D6 | Review of uploaded entries | the same rule as other entries | The same rule: two-person, or the POC single-reviewer mode if D-083 is accepted. Retirement always takes two reviewers. |

The question in an answer record is stored as typed, cut at 600 characters (only Directors
and the RM can see it), which is the section A relaxation in D1; the dropped model lines are redacted and
size-capped. Request states: New → In
progress (one owner) → Fix waiting → Resolved, or Closed with a required reason; a rejected
fix returns the request to In progress; one fix can resolve several requests.

As built ahead of acceptance (store schema v5, see ADR-012 Amendment 1): the queue lists
each request with the RM's question, which is not a logged view (opening the record is);
up to 2 earlier answers are kept per request in `answer_record_keeps`; a Director's fix can
start from the record (`fix-start`: the AI's left-out lines, redacted, no model call,
nothing saved) and the saved version records `started_from_answer`; a fix that keeps a
redaction placeholder is refused (422 `PLACEHOLDER_NOT_REWRITTEN`). Each is part of what
Shane accepts or rejects with D-084.

Authority: `PROJECT_DEFINED_PROVISIONAL`. Review authority stays UNKNOWN_BLOCKED (Q-014). Not
sponsor review policy; no CLM backend write, provider status or Live claim follows.

## D-085 - reusable scenario-declared POC ownership acceptance (candidate)

**Numbering note (2026-10-25).** Drafted as D-084 before PR #110 merged its AI Assistant
D-084. On integration with `origin/main` `5de7f24`, the ownership drafts were renumbered
D-084 -> D-085 (this entry) and D-085 -> D-086, and the policy literal
`D084_SCENARIO_DECLARED_POC_BASIS_V1` -> `D085_SCENARIO_DECLARED_POC_BASIS_V1` (never released,
so no stored record carries the old literal). Pre-integration QG reports keep the old numbers.

Owner assignment 2026-10-25 (Generalized POC Ownership Acceptance, Workstream A). It
replaces D-082's Garden-only eligibility for new analyses. The opt-in, default, lane,
readiness authority, F2/F6, freshness, target snapshot and D-081 Option B are unchanged.

- **Removed (owner-authorized).** `ACRA_MARKETPLACE_POC_OFFICER_ROLE_KEY`,
  `ACRA_MARKETPLACE_POC_OFFICER_ROLE_ALLOWLIST`, their parser and composition wiring. Stale
  values in an env file are ignored. Officer observations and provenance are retained and
  never become shareholdings.
- **Trusted declaration.** A scenario in the project-controlled overlay catalogue may
  declare `poc_acceptance`: `quantity_basis` (today only `OWNER_SUPPLIED_DIRECT_REGISTER`; a
  reviewed descriptor of where the declared units came from, not an eligibility input) and
  its accepted assumptions. A case field or an arbitrary UEN can never grant one. Each
  assumption accepts exactly one review cause:
  - `SIMULATED_RELATIONSHIPS`: `LOCAL_SYNTHETIC_RELATIONSHIP` links
    (`SYNTHETIC_OWNERSHIP_EVIDENCE`), mandatory for an accepting overlay scenario;
  - `EQUAL_UNIT_DENOMINATOR`: D-081 links (`OWNERSHIP_DENOMINATOR_REQUIRED`);
  - `DESCRIPTIVE_OFFICER_ROLES`: the root's official Mock `OFFICERS` ownership-like roles
    (`UBO_REVIEW_REQUIRED`);
  - `UNCLASSIFIED_LEGAL_FORM`: root legal form `OTHER` (`OWNERSHIP_METHOD_UNSUPPORTED`).

  `GARDEN_DIRECT_OVERLAY_V1` declares the first three. `FIVE_LAYER_MARKETPLACE_HYBRID_V1`
  declares nothing (fictional units, `LOCAL_SYNTHETIC_IDENTITY` names), so it always stays
  in review.
- **Eligibility (fail-closed).** The recorded scenario must resolve in the runtime's own
  catalogue to a declaring scenario rooted at the analysis's identity. Kept from D-082:
  official Mock provider, identity binding, complete topology, no unresolved person, no
  document discrepancy, every retained issuer POC-distributed (and POC links exactly on
  retained issuers), review-classified candidates with calculated assumed-basis results.
  Added: no issuer may carry a `LOCAL_SYNTHETIC_IDENTITY`, and every link kind must be a
  declared assumption. **Relaxed:** D-082's minimum of one retained official issuer and one
  equal-unit link is gone, so a future declared scenario built only from simulated links
  (owner-reviewed declared units) can qualify, as the assignment allows. Requiring
  ACRA-sourced quantities in every accepted case would need a new owner rule.
- **Causes, not codes.** The single registry review issue is chosen by priority (`OTHER`
  masks every other cause). Eligibility therefore recomputes the causes through the same
  helper the issue builder now uses (behavior-preserving extraction). Unquantified,
  contradictory, conflicting, unbound or status-unsupported evidence and non-role
  unresolved semantics always block. The issue set must equal exactly what the exercised
  assumptions imply.
- **Officer roles.** No identity allowlist: any official Mock `OFFICERS` role bound to the
  root, with the adapter's stable id, distinct, current or `CEASED`, is descriptive context
  when declared. Their counts are recorded; any change still revokes through the content
  fingerprint.
- **Record.** Policy `D085_SCENARIO_DECLARED_POC_BASIS_V1` plus `accepted_assumptions` (the
  exercised ones). A D-082 record stays readable and is never honoured again, so D-082
  accepted cases return to ordinary review until a fresh analysis.
- **Persistence.** Case envelope 15. An exact v14 reader rejects a D-085 acceptance (current
  or prior) and still reads a D-082 one.
- **Workstream B outcome.** The owner-authorized read-only Marketplace Mock probe (1 token
  + 18 GETs, all HTTP 200, 2026-10-25; sanitized report
  `.ai-pipeline/reports/ACRA_MULTI_LAYER_ENTITY_DISCOVERY_REPORT.md`) found no UEN with both
  an identity profile and shareholder rows, and no Active row whose holder is another
  identified company. Every candidate link would rewrite an official holder identity or
  category, treat a Withdrawn row as current, or read a money amount as shares:
  `INSUFFICIENT_MARKETPLACE_MOCK_DATA`. No new scenario was added; that is an owner
  decision.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. Not ownership verification, a legal UBO determination
(Q-004), Marketplace denominator or relationship semantics (Q-012), person identity
authority (Q-019) or Live evidence.

## D-086 - dual multi-layer demonstrations: simulation status and OPQ -> Garden -> SIM LIM (candidate)

Owner scope adjustment and decisions, 2026-10-25. The owner accepted
`INSUFFICIENT_MARKETPLACE_MOCK_DATA` (D-085) and directed two separate demonstrations.

- **Scenario A (historical five-layer, unchanged).** `FIVE_LAYER_MARKETPLACE_HYBRID_V1` keeps
  its fixture, names, UENs, links, units, diamond and results (BEATRICE LIM 30, DIANA KOH 25,
  ALEX TAN 20, EDWARD NG 15, CHARLES ONG 10). It stays REVIEW_REQUIRED, declares no POC
  acceptance and its readiness stays blocked.
  - **Presentation only.** The ownership response gains `simulation_calculated`. It is true
    only for a hybrid analysis whose links are all `LOCAL_SYNTHETIC_RELATIONSHIP`, with a
    complete topology, no unresolved person, every assumed-basis result MET/NOT_MET, no error,
    manual receipt, supplemental link or document discrepancy, and issues limited to
    `SYNTHETIC_OWNERSHIP_EVIDENCE`, `OWNERSHIP_METHOD_UNSUPPORTED` and a role-caused
    `UBO_REVIEW_REQUIRED`. Causes are recomputed with the D-085 helper, so a defect or an
    ownership-like role masked by the legal-form issue keeps it false, as does an
    ownership-like role retained on an intermediate issuer.
  - The UI then shows **Multi-layer ownership simulation calculated** (neutral banner) with
    the owner's copy, a separate review-required explanation, the legal-form note when
    present, and unchanged sources and classifications. The explorer reads "Simulation
    calculated — review required", and the UBO summary says the values come from a calculated
    simulation on declared synthetic relationships. Nothing grants readiness or acceptance.
- **Scenario B (`OPQ_GARDEN_SIM_LIM_V1`, explicitly selected).** OPQ `201511222D` (official
  root profile) -> GARDEN BUSINESS `11111999A` (official BUSINESS_PARTNERSHIP profile) ->
  SIM LIM `111111111M` (official shareholder-operation rows, D-081 equal units). Only the
  relationships are declared; no identity or share quantity is invented.
  - **Owner-declared 100%.** OPQ -> Garden is an owner-declared demonstration percentage,
    not an ACRA quantity, verified holding or derived percentage. It is carried as
    `LOCAL_SYNTHETIC_RELATIONSHIP` / `LOCAL` with a source reference ending
    `_OWNER_DECLARED_PERCENT`. The browser projection exposes only the boolean
    `provenance.owner_declared_percentage` (the internal reference stays server-side), and the
    UI labels the link "owner-declared percentage".
  - **Smallest model change.** The overlay could express a percentage only through declared
    units, so a new per-issuer basis `OWNER_DECLARED_COMPLETE_PERCENTAGES` holds a declared
    percentage per holder with no units and no unit evidence. Every holder must be active and
    the register must total exactly 100 (no hidden remainder). Existing unit registers,
    Garden's included, are unchanged.
  - **Garden.** Garden's owner-supplied direct register is reused unchanged (62.5 / 37.5).
    "Corporate" is the registry's non-individual holder category and maps to the graph node
    type LEGAL_ENTITY, which is not a legal form. Garden's official `BUSINESS_PARTNERSHIP`
    stays on its discovery record, and the hierarchy Type column now shows a non-company
    registry form (business partnership, LLP, LP) instead of "Company". This also applies to
    Garden as the root of its own case. Every other legal form, including OPQ's decoded
    `OTHER`, keeps the existing "Company" label (OPQ's official company type is a company).
  - **Intermediate officer roles (owner decision: fail closed, QG P1-1).** Discovery dropped an
    overlay issuer's official OFFICERS roles. They are now kept beside the graph on that
    issuer's discovery record as `official_officer_roles` (role, status and Mock provenance;
    no identity, never a party, edge, holding or analysis evidence; an official profile is
    required). Garden's four Owner roles (three current, one ceased) are retained. An
    ownership-like intermediate role is outside every declared assumption, so it blocks POC
    acceptance; a non-ownership role (for example DIRECTOR) is descriptive only.
    `DESCRIPTIVE_OFFICER_ROLES` is neither declared for Scenario B nor extended to
    intermediate issuers. Exact schema 14-and-older readers reject the observations.
  - **Selector.** `ACRA_MARKETPLACE_OPQ_SCENARIO` = `five_layer_simulation` (default) or
    `garden_sim_lim_chain`. It is an operator setting, valid only in the Marketplace Mock
    hybrid lane, and puts exactly one OPQ scenario in the catalogue. It is never a case field.
    The scenario id is recorded on the discovery audit and any acceptance. Switching back
    removes the scenario and withdraws its authority.
  - **Results** (unchanged engine): ABCD123 51.13636375, LIM CHOON HUAT 37.5, TAN WEI LING
    and EFGH2345 5.681818125 each (`100% x 62.5% x 81.818182%`). The withdrawn corporate row
    is excluded, and classes, units and statuses are retained.
  - **OPQ evidence** (one owner-authorized `entityBasicInformation` read, 1 token + 1 GET,
    HTTP 200): company type EXEMPT PRIVATE COMPANY LIMITED BY SHARES; officers 2 current and
    1 ceased DIRECTOR, plus 1 current SECRETARY; no ownership-like role. The legal-form
    decoder reads only `constitution`, so OPQ stays `OTHER` (unchanged decoder, disclosed).
  - **D-085.** Declared `SIMULATED_RELATIONSHIPS`, `EQUAL_UNIT_DENOMINATOR` and
    `UNCLASSIFIED_LEGAL_FORM` (all existing D-085 assumptions); `quantity_basis`
    `OWNER_DECLARED_PERCENTAGE_AND_DIRECT_REGISTER`. With Garden's observed Owner roles the
    chain is **not POC-ready**: it calculates and displays, stays REVIEW_REQUIRED, and
    readiness stays blocked at OWNERSHIP. Only an otherwise identical chain with no
    ownership-like intermediate role would qualify (tested as a counterfactual). An
    ownership-like root role also blocks. Formal classifications stay REVIEW_REQUIRED; target
    confirmation, no provisional UBO ids and D-081 Option B are unchanged.
  - **Open owner question (answered by D-087).** Should `DESCRIPTIVE_OFFICER_ROLES` extend
    to the official ownership-like roles of a declared intermediate issuer (Garden in
    Scenario B)? D-087 answers with a separate, scenario-declared assumption instead.
- **Entity effective interests (owner request, 2026-10-25).** Intermediate legal entities
  showed "Not calculated". On an opt-in flag (`include_entity_paths`, off for analysis,
  discovery and advice, which therefore run main's exact code path), the single engine
  traversal also records the path product it already computes when it reaches each
  intermediate legal entity (`PathCalculation.entity_paths_by_party`). Person paths,
  limits, issues, rounding and aggregation are unchanged, and nothing is stored. The
  ownership response returns `entity_effective_interests` (per entity: the exact sum of its
  path products and each path), recomputed from the analysed record with the same limits.
  It fails closed (nothing shown) on a path or depth limit, an excluded cycle, any entity
  total above 100 (over-allocation), or evidence that cannot be built. It is presentation
  only: never a candidate, classification, threshold result or readiness input. The
  hierarchy shows each entity row's path value; the selected entity shows the all-paths
  aggregate, labelled "calculated interest; not a UBO classification". Five-layer: L2 80,
  L3 50, L4A 30, L4B 20, L5 40 (30 + 10). Scenario B: Garden 100, SIM LIM 62.5.
- No rounding, comparator, connector, cache or GoldTier change; the engine change is the
  additive entity-path output above. Recursive discovery changes only to retain the overlay
  issuer's role observations. Case envelope 15 carries the new optional discovery field.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. Not ACRA ownership, a verified holding, legal UBO policy
(Q-004), Marketplace relationship or denominator semantics (Q-012), person identity (Q-019)
or Live evidence.

## D-086a - case-sticky OPQ ownership scenario (amends D-086; candidate)

Owner-approved isolated assignment (G4). The operator selector chooses the OPQ variant only at a case's first overlay analysis; that case keeps its recorded variant on every later analysis. An unknown recorded variant gives no overlay. Stickiness is bounded: the recorded variant is read from the record and its four prior-analysis snapshots, and once five or more consecutive analyses without an overlay (including manual declarations) have pushed it out, the next source load uses the current selector. A case without a durable D-120 ledger then relies on that history for POC replay refusal, so a change of the effective selector (including first applying `deploy/compose.acra-ownership.yml`) is permitted only after the pre-change checks of `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md` section 7c, and is blocked while any ledgerless OPQ case exists or that cannot be confirmed. A binding beyond that history needs a durable field (owner decision, not taken). The selector is never user-supplied and never a case field written by a user. Official-evidence gate, provenance labels and D-112 O7 unchanged.

## D-087 - declared intermediate issuer officer roles as POC descriptive context (candidate)

Owner decision, 2026-10-25, before PR #111 merges. It extends the D-085 scenario-declared
POC acceptance so the explicitly selected OPQ -> GARDEN BUSINESS -> SIM LIM scenario
(`OPQ_GARDEN_SIM_LIM_V1`) can pass the ownership readiness boundary with Garden's verified,
source-observed official OFFICERS Owner roles retained as descriptive context. It replaces
D-086's fail-closed outcome for that scenario only. This is POC workflow acceptance, not
legal ownership verification.

- **New assumption.** `DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES`. A scenario's trusted
  declaration (project code, never a case field) names each intermediate issuer and the
  ownership-like role kinds accepted for it (`descriptive_intermediate_roles`). The
  assumption exists exactly when issuers are named, and only non-root scenario issuers
  qualify. It accepts no analysis issue code: the roles stay on the issuer's discovery
  record (D-086), not in the analysis evidence.
- **Scenario B declaration.** Garden `11111999A`, role kind `OWNER` only. The Garden direct
  scenario and the historical five-layer fixture are unchanged (the five-layer fixture
  declares no acceptance).
- **Still blocking (fail closed).** An ownership-like role on an undeclared issuer, the
  root, or of an undeclared kind (for example `SHAREHOLDER`, `PARTNER` or `MEMBER` on
  Garden); an issuer without its official profile, not recorded once, or not a local overlay
  issuer of the scenario; a role record breaking the OFFICERS / ACRA / Mock / status
  contract; more than 32 such records; and every existing D-085 condition (policy disabled,
  outside the Mock hybrid lane, unknown scenario, incomplete topology, identity mismatch,
  document discrepancies, genuine evidence defects, limits, cycles, and any later change to
  the bound content, which revokes the acceptance).
- **Acceptance record.** Adds `descriptive_intermediate_current_role_count` and
  `descriptive_intermediate_ceased_role_count` (counts only; no identity or digest). The
  assumption is recorded exactly when those counts are non-zero. Case envelope 15 is
  unchanged in version (unreleased); schema 14-and-older readers reject the counts.
- **Result.** A fresh Scenario B case with the opt-in policy is accepted: assumptions
  `DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES`, `EQUAL_UNIT_DENOMINATOR`,
  `SIMULATED_RELATIONSHIPS` and `UNCLASSIFIED_LEGAL_FORM`; Garden counts 3 current and 1
  ceased. Ownership readiness is READY with no blocker, and the case waits at
  `TARGET_CONFIRMATION_REQUIRED`. The review state, issues, evidence, classifications
  (REVIEW_REQUIRED) and every percentage are unchanged. Explicit RM confirmation, Mock
  GoldTier only, no provisional UBO ids and revalidation before the first target mutation
  are unchanged.
- **Presentation.** The accepted banner adds an intermediate-role disclosure and, when an
  owner-declared percentage is present, the statement that calculations use ACRA
  Marketplace Mock observations and explicitly declared synthetic relationships and are
  not a verified legal UBO determination.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. Not ACRA ownership, a verified holding, legal UBO policy
(Q-004), Marketplace relationship semantics (Q-012) or Live evidence.

## D-088 - official Marketplace Mock businessProfile and the issued-capital POC interpretation (candidate)

Owner decisions, 2026-10-25 ("ACRA issued capital" and "Current, if capital matches").
A project-defined Marketplace Mock POC interpretation, not a production or
sponsor-approved ownership rule (Q-012 stays partially answered: Mock subset only).

- **Observation (one owner-authorized read, 1 token + 1 GET, HTTP 200).**
  `businessProfile` for ABC COMPANY PTE. LTD. `201688888A`, an exempt private company
  limited by shares and a live company. It shows one Individual shareholder holding 1000
  ORDINARY (SGD) with no row status, and issued and paid-up capital of 1000 ORDINARY (SGD).
  Its entity-basic profile and `coShareholdersDetails` are empty in the Mock.
- **Connector (new external-provider capability, Mock only).**
  - The fixed official Mock path `/entityQuery/businessProfile` is read only through the
    official Marketplace composition.
  - A strict decoder keeps the company labels, shareholder rows (category, name, count,
    class, currency and any returned status) and the issued and paid-up capital lines.
    Officer, address, nationality and activity fields are never retained.
  - A share count is accepted only as a finite whole JSON number, never a string (the
    observed `1000.0` becomes the exact count 1000). A bad count, an unknown category, a
    different UEN or more than one entity is malformed.
  - The source holder identifier is replaced by an issuer-scoped digest (`BP-...`) and
    never stored or projected. The digest is unkeyed, so it is pseudonymous rather than
    irreversible for a small identifier space; any non-Mock use needs a keyed digest under
    a server-held secret first.
- **Cache.** Cache-first under its own contract key `MARKETPLACE_BUSINESS_PROFILE_V1`
  (registry cache schema 5). The cache owner, locks and CAS are shared with the
  shareholder contract. COMPLETE results follow the freshness policy, EMPTY results the
  negative TTL, and FAILED results are never cached.
- **When it is read.** Only for a corporate holder named in the trusted scenario's
  `business_profile_issuers`, in the hybrid lane, and only after that holder's
  entity-basic profile and shareholder operation are both definitively empty. It is
  never read for any other scenario or lane.
- **Interpretation (fail closed).** Status-free rows are assumed current, and attach as
  `LOCAL_POC_ISSUED_CAPITAL_BASIS` links (units / issued x 100, the existing six-decimal
  rule), only when all of these hold:
  - every row is an individual with no returned status, a positive count and one common
    class and currency;
  - the issuer reports exactly one issued class, in that class and currency, with a
    positive count;
  - the rows total exactly that issued count;
  - any paid-up line for the class agrees.

  Otherwise the profile is retained unattached (`OFFICIAL_BUSINESS_PROFILE_RETAINED`) and
  the branch stays unresolved. Empty, failed or malformed reads retain nothing.
- **Recorded separately.** Each retained row keeps `provider_status` (what was returned)
  apart from `assumed_current` (the POC assumption). A returned status is never replaced:
  any status fails the rule closed.
- **Acceptance.** New D-085 assumption `ISSUED_CAPITAL_DENOMINATOR`. It accepts no issue
  code: the links are named by the synthetic-evidence issue. Eligibility also requires
  that the issuer is a named profile issuer, that the retained profile still satisfies
  the rule, and that the links reproduce exactly the rows' names and quantized shares.
  The acceptance records `issued_capital_relationship_ids`. Schema 14-and-older readers
  reject the new discovery and acceptance fields.
- No GoldTier, mapping, authentication or assistant change. The engine is unchanged: the
  links are ordinary graph edges.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, pending integrated
acceptance and independent gate. Not ACRA ownership, a verified holding, legal UBO policy
(Q-004), Marketplace denominator semantics (Q-012) or Live evidence.

## D-089 - OPQ multi-holder variant: GARDEN BUSINESS 50% and ABC COMPANY 50% (candidate)

Owner decision, 2026-10-25 (Option A). A separate operator-selected variant: selector
`ACRA_MARKETPLACE_OPQ_SCENARIO=garden_abc_multi_holder`, scenario `OPQ_GARDEN_ABC_V1`. The
default five-layer simulation and the OPQ -> Garden 100% variant stay unchanged and
available.

- **New synthetic declarations, exactly two.** OPQ -> GARDEN BUSINESS `11111999A` 50% and
  OPQ -> ABC COMPANY `201688888A` 50%. Both are owner-declared complete percentages
  (`LOCAL_SYNTHETIC_RELATIONSHIP`, `LOCAL`), with no share units. ABC's 1000 shares are
  never an OPQ denominator.
- **Everything else unchanged.**
  - Garden keeps its official BUSINESS_PARTNERSHIP identity and its owner-supplied
    register (SIM LIM 62.5%, LIM CHOON HUAT 37.5%).
  - SIM LIM keeps its official rows under D-081.
  - ABC's holder is 100% under D-088.
  - Garden's official Owner roles are descriptive context under D-087.
- **Results (unchanged engine, inclusive 25% comparator, no rounding before comparison).**

  | Party | Effective % | Threshold (assumed basis) |
  |---|---|---|
  | ABC's individual holder | 50 | MET |
  | ABCD123 | 25.568181875 | MET |
  | LIM CHOON HUAT | 18.75 | NOT_MET |
  | TAN WEI LING | 2.8409090625 | NOT_MET |
  | EFGH2345 | 2.8409090625 | NOT_MET |

  Entity values: Garden 50, SIM LIM 31.25, ABC COMPANY 50.
- **Acceptance.** Declared assumptions: `SIMULATED_RELATIONSHIPS`, `EQUAL_UNIT_DENOMINATOR`,
  `UNCLASSIFIED_LEGAL_FORM`, `DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES` (Garden, `OWNER`) and
  `ISSUED_CAPITAL_DENOMINATOR` (ABC). A fresh case with the opt-in policy is accepted,
  ownership readiness is READY with no blocker, and the case waits at
  `TARGET_CONFIRMATION_REQUIRED`.
- **Unchanged.** Review state, issues and classifications stay REVIEW_REQUIRED. Explicit RM
  confirmation, Mock GoldTier only and no provisional UBO ids are unchanged.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`. Simulation data, not
ACRA-verified ownership.

## D-090 - proposed AI Assistant explanations, topic steering and required lines (PROPOSED)

Status: PROPOSED by the project team on 2026-10-26, built ahead of acceptance on branch
`feat/ai-assistant-explanations`. **It needs the repository owner's (Shane's) explicit
acceptance before merge, in particular E2, which relaxes ADR-012 section C.** It amends
ADR-012 section C (Amendment 2, which lists every line and its source) and builds on D-084
(proposed).

| # | Decision | Recommendation |
| --- | --- | --- |
| E1 | Reviewed explanation sentences in the catalog: per field (registered address, legal name, UEN, any difference) when that field differs on a blocker; per readiness item (document review, ownership evidence) when it is still needed | Yes. No case values, never says which source is right or that anything is verified; each cites a backend source and passes `sentence_problem` on the Merlion case. "can" sentences are general reasons, not app behaviour. |
| E2 | **Relaxes ADR-012 section C:** `<Field>: ACRA says "<value>", the document says "<value>".` per difference | Yes, only when both values are single-line, at most 120 characters, without straight or typographic double quotes or unsupported characters, and the line passes the sentence checks; otherwise not offered. Answer records (D-084) store such lines redacted, so ADR-012 section A is unchanged. |
| E3 | Fixed lines: "This case is not ready for GoldTier submission yet." (readiness facts list a blocker, case not completed); "Approving the case is not offered to you on this case." (case not ready and no approve-type action offered; never on a ready case, where Review & Send's Send is the final human approval); `<blocker title>: this is for <owner>.` (owner named by the blocker policy, title checked like a value), else "The case data does not name a contact for this."; "I can't answer that from this case's data." (always) | Yes. Each passes the sentence checks on Merlion. |
| E4 | Topic steering in the prompt (why blocked / what next, difference, readiness, approving, contacts, document review, ownership) and answer rules (at most 6 lines, answer first, no repeats, one related disclaimer, the "can't answer" line when nothing answers) | Yes. The allowed set is unchanged. |
| E5 | Required lines: the server adds the topic's required lines the model left out, in topic order; unseen lines that are not required are dropped down to 6 lines, unseen required ones down to 8, and a line already streamed to the RM is never removed; the reply's `added_lines` gives the added lines' positions | Yes. Only allowed lines, in the catalog's words; an answer with no allowed line still gets the case-data answer. |
| E6 | Formatting-tolerant matching (ASCII case, spaces, quotes, Markdown emphasis and backticks, list marker, trailing full stop; split into allowed sentences or drop the line); a bare offered action label and an untagged knowledge sentence stand for their catalog lines | Yes. The catalog's text is shown, never the model's. |

Why this keeps G6: the RM still sees only allowed lines, in the catalog's own words. Templates
are filled from the backend projection, required lines come from the same allowed set, and
any added, removed or changed word drops a model line. Sentence checks are still never
applied to model text in place of matching.

Authority: `PROJECT_DEFINED_PROVISIONAL`. Not sponsor review policy; no CLM backend write,
provider status or Live claim follows.

## D-091 - AI Assistant dormant external inference profile and lifetime budget guard (ACCEPTED, dormant A2 scope only)

Status: ACCEPTED by the repository owner on 2026-10-26 for the offline, dormant Phase A2
implementation only. Proposed by the project team on 2026-10-26 and built offline under the
owner's Phase A2 implementation authorisation (OD-1 to OD-9). It amends ADR-012
(Amendment 3, accepted for the same scope). The owner accepted X1 to X9 and Amendment 3 "for
the dormant Phase A2 architecture and offline-only controls" in the PR #116 governance
acceptance
([comment](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/116#issuecomment-6416329653))
and reaffirmed it for the merged head
([comment](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/116#issuecomment-6417214539)).
PR #116 merged as `63cb662`. **Accepting A2 does not authorise external inference
activation**: the approved endpoint registry stays empty, the four locks stay closed, and no
remote or OpenRouter request, paid trial, real or sponsor data transmission, remote
embedding, hosted team deployment or user model switching is approved. Activation needs the
separate Phase B owner decisions below. The acceptance does not cover D-083, D-084 or D-090,
does not change the authority label below and is not sponsor policy. D-090 and ADR-012
Amendment 2 are PR #114's, merged before this one.

**What A2 does not do.** It does not enable remote inference, approve sending customer,
sponsor or case data to any external provider, approve any API spending, approve
user-configurable or user-visible model selection, authorise a shared or hosted inference
deployment, change the AI Assistant's responsibilities or use cases, or relax the exact-line
output guard. Any future remote activation needs separate owner decisions (Phase B) and the
applicable sponsor governance (Q-013) for anything beyond synthetic data.

| # | Decision | Accepted decision (dormant A2 scope) |
| --- | --- | --- |
| X1 | Dormant remote profile | `openrouter_gpt_oss_120b` refuses composition unless four locks hold: an in-memory mock transport (L1), an approved endpoint record (L2; none exists), the interlock value `D-091` (L3) and an initialised healthy ledger (L4). |
| X2 | Approved model registry | Code-defined profiles with explicit capabilities and per-endpoint records (full endpoint slug, listed prices, output ceilings, documented guarantees, uniqueness evidence). Settings select a profile and one endpoint only. |
| X3 | Credential source | `OPENROUTER_API_KEY` from the process environment only, lazily, after every other check, only for the remote profile, never sent elsewhere. |
| X4 | Fixed remote request policy | One pinned endpoint slug in `provider.order` and `provider.only`, fallbacks off, `require_parameters`, `data_collection: deny`, `zdr`, `max_price` from the record, `reasoning.exclude`; no attribution headers, user or session ids, tools, plugins or files. |
| X5 | Lifetime budget ledger | Local SQLite ledger in one key's cumulative-usage frame, anchored on its opening usage, with a labelled (not proven) worst-case reservation, conservative settlement, an accounting breaker, fail-closed integrity and an offline operator CLI. |
| X6 | Provider verification | Every remote call is `unverified` until a separately authorised Phase B capability verifies the serving provider from generation metadata; mismatching evidence quarantines the call. |
| X7 | Telemetry v2 | Content-free profile, requested endpoint, verification flag, usage, budget, finish reason, empty content and error class; off by default. |
| X8 | Multi-instance limit | A ledger enforces only its own key and instance; a global cap needs provider-side controls, partitioned statically. |
| X9 | Secret scanning | The scanner detects credential assignments to the assistant's credential names and OpenRouter-shaped keys, with documented placeholders. |

Unchanged: the exact-line catalog and `StreamingGuard`, deterministic fallbacks and notices,
GET-only CLM access with the user's session, loopback-only embeddings and warm-up, no tools,
no automatic learning from feedback. Authority: `PROJECT_DEFINED_PROVISIONAL`. The remote
profile is `DORMANT` (mock-transport tests only). Not sponsor policy; no CLM backend write,
provider status or Live claim follows.

## D-092 - AI Assistant Phase B synthetic-only live experiment (PROPOSED)

Status: PROPOSED by the project team on 2026-10-27 under the repository owner's Phase B
directive ("start GPT-OSS 120B experimentation": synthetic prompts only, at most US$1 of
inference credits in the initial batch, no credit purchase or auto top-up, no customer,
sponsor or production data, no deployment). Builds on D-091 (accepted for the dormant A2
scope). Not accepted until the owner says so; not sponsor policy.

| # | Proposed decision |
| --- | --- |
| P1 | One approved endpoint record, `deepinfra/bf16` for `openai/gpt-oss-120b`, from the public endpoint listing and ZDR list read 2026-10-26T17:05Z (prices US$0.037/M input, US$0.17/M output, no request price, maximum completion 117,964; the only DeepInfra endpoint; ZDR-listed). No evidence that `max_tokens` bounds reasoning there, so reservations use the maximum completion. |
| P2 | Lock L1 also accepts a live marker when the caller passes `allow_live_network` and `AI_ASSISTANT_REMOTE_LIVE_DECISION` names `D-092`. Only the evaluation harness passes it; the service never does, so only synthetic fixture cases served by the harness's mock CLM backend can reach OpenRouter. L2 to L4, the D-091 interlock and the request policy (one pinned slug, no fallbacks, `data_collection: deny`, `zdr`, `max_price`, reasoning excluded) are unchanged. |
| P3 | Read-only account checks: `GET /api/v1/key` (limit, reset period, usage) and `GET /api/v1/generation` (serving provider, model, total cost; no content). Every live run first passes a fail-closed preflight (public listing re-verified the same day; a non-resetting key limit leaving at most US$1.00 plus one reservation; ledger cap at most US$1.00 above the key's opening usage with that usage reconciled; calls an earlier run left unverified verified first; owner attestation that auto top-up and prompt logging are off). Live runs ask only the reviewed Phase B question file and only the listed question ids (P10). |
| P4 | Every call is verified from generation metadata after its turn; a provider, model or cost mismatch, metadata still missing after a bounded wait (at most two minutes) or a missing generation reference quarantines the call and opens the ledger breaker, which stops the batch. A stream that fails after its generation id arrived keeps the reference for verification. A read-only recheck may later confirm a quarantined call from its metadata; it changes nothing, and continuing still needs the operator reconcile and breaker reset. |
| P5 | Synthetic answers are stored only in a local evaluation artifact (`answers.jsonl`), apart from content-free telemetry, ledger and verification rows (`calls.json`), both git-ignored. |
| P6 | Rule 17 (owner-directed, 2026-10-27): "I can't answer that from this case's data." is used only on its own and only when no allowed line answers any part of the question (`instructions/persona_and_rules.md`; ADR-012 Amendment 2, Change 3). With the owner's approval the `test_speed` prompt bound moved from 9,000 to 9,250 characters (rule 17 +96, the P7 source line +80; the P8 UBO line later added +72, leaving the test prompt at 9,218). |
| P7 | Registry source line. Owner-approved wording for ACRA Mock: "Registry data in this case comes from ACRA (MOCK), not the live ACRA service.", offered "only when the trusted current case evidence confirms ACRA Mock provenance"; the same owner directive asked to "use source-correct wording for other supported environments", so the same sentence with the backend's own environment (`ACRA (LOCAL)`, `ACRA (SANDBOX)`, `ACRA (PARTIAL)`, `ACRA (DORMANT)`) is the project's application of that instruction, not separately approved wording. An allowed line only when the backend's company source starts with `ACRA (` followed by one of MOCK, LOCAL, SANDBOX, PARTIAL or DORMANT; never for a live or unnamed source. One builder (`guardrails.registry_source_line`) is shared with the existing non-live notice, which is not repeated when the line is shown. Steered only for registry-status questions. |
| P8 | UBO line, owner-approved wording: "This case cannot name any UBOs yet because the UBO check has not run." Allowed only when the backend readiness lists `OWNERSHIP_REQUIRED` and ownership is `MISSING` (set together only when the case has no ownership analysis); it leads the "who are the UBOs" steering, names no one and never says there are no UBOs. |
| P9 | UBO-completion refusal, owner-approved wording and placement (2026-10-27): "Marking the UBO check as complete is not offered to you on this case." Allowed only while ownership readiness is `MISSING`, `IN_PROGRESS`, `REVIEW_REQUIRED` or `FAILED` and no action offered to the viewer would complete or accept ownership, UBOs or beneficial owners (none exists today; the backend completes ownership itself). **Topic-only**: the guard accepts it wherever that holds, but the model sees it only in the QUESTION TOPIC message for a request to complete the check, never in the case facts, so the everyday prompt is unchanged. The owner chose this over raising the prompt bound because it avoids increasing the everyday prompt, keeps the change narrow and makes the refusal available when needed. |
| P10 | Paid runs select questions with an explicit `--questions` manifest and a matching `--expect-count`, both checked before the preflight; added after a rerun asked 8 questions where 7 were authorised (recorded in the Phase B report). |
| P11 | Owner-approved with safeguards (2026-10-27, Phase B answer quality): the assistant case facts carry only the **status** of the registry officer lookup on the case's own registry acquisition (COMPLETE, EMPTY, FAILED, NOT_ATTEMPTED, UNSUPPORTED), never officer names, roles, ids or counts. The lookup must be for the case's UEN and appear once; EMPTY is used only when the lookup succeeded with no records on a COMPLETE or PARTIAL acquisition, without error, from the same registry and environment as the company details, and is never inferred from a failed or missing lookup. The CLM backend's case access control is unchanged (no HR access added). The status and the GoldTier readback status choose lines only: they are not shown to the model and are not grounding for the knowledge sentence checks (`context.SELECTION_ONLY_FACTS`). |
| P12 | Directors, owner-approved wording (topic-only): "The app does not read directors from uploaded documents, so it does not compare directors between a document and ACRA." (always); "The ACRA (`<environment>`) result for this case has no officer (director) records; this does not show that the company has no directors." (P11 status EMPTY, registry stage READY, named non-live ACRA source); "Officer (director) records were not retrieved from the registry for this case." (FAILED, NOT_ATTEMPTED, UNSUPPORTED); and, only for a question about a director difference and never as evidence one exists, "If a document and the registry differ on directors, check the document's type, date and which company it is for." and "A director difference can come from a recent appointment or resignation, or from an out-of-date document.". Director questions are routed apart from the blocker topic and the app's Director role. No director reconciliation workflow is added. |
| P13 | Entity status and UEN, owner-approved wording (topic-only): "The entity status "LIVE" is the company's registration status in the registry record, not a live connection to ACRA." (entity status exactly LIVE and the P7 source line allowed; added to the registry-status plan); "A UEN (Unique Entity Number) identifies an entity registered in Singapore. The number alone does not confirm its legal name, address or other company details." (a UEN and country SG). |
| P14 | GoldTier handoff, owner-approved wording (topic-only): "A person must confirm Send in "Final review & send" before the final GoldTier submission; the app may search GoldTier for an existing customer earlier." (always); "When a GoldTier submission is confirmed, the app retains the submission result and required customer readback. The result is shown in "GoldTier Details & Status"." (target submission SUBMISSION_CONFIRMED and READBACK SUCCESS); "Sending a case does not mean GoldTier has approved the customer or that KYC is complete. Those outcomes are not confirmed by this application." (always). The proposed environment sentence (G4) is **held**: every approved variant containing "production GoldTier" fails the unchanged live-claim check; corrected wording awaits the owner. |

Not decided here: any non-synthetic data, a hosted or service-side remote model, user model
selection, a second endpoint, a larger budget, or changes to prompts, retrieval, the
exact-line guard or CLM rules beyond P6 to P9 and P11 to P14 (each needs its own decision).
P6 to P9 and P11 to P14 add no required line: a bare decline is never padded, and the
no-model answer is unchanged. Recording P11 to P14 does not accept D-092. Evidence classification of any
live result: `SANDBOX`-like external evaluation on synthetic data; never `LIVE` CLM behaviour.

## D-093 - AI Assistant model management: local loopback models only (ACCEPTED, local-only POC scope)

Status: ACCEPTED by the repository owner on 2026-10-27 for the local-only model-management
scope, in the Session 1 design approval (owner decisions 1 to 5 below; decision 4
conditionally). Proposed the same day (`.ai-pipeline/001_planner/AI_ASSISTANT_MODEL_MANAGEMENT_PLAN.md`).
It amends D-091's "no user model selection" statement and X2 for local loopback profiles
only, and is recorded as ADR-012 Amendment 4. D-091 (dormant remote profile and its locks)
and D-092 (PROPOSED, synthetic evaluation only) are unchanged. Not sponsor policy.

| # | Decision |
| --- | --- |
| M1 | RBAC: new backend capability `MODEL_CONFIG_MANAGE`, assigned to HR only for the POC. RM, Client Onboarder and Director do not hold it; Director knowledge publishing (`POLICY_APPROVE`) and HR policy proposals (`POLICY_MUTATE`) are unchanged and independent of it; HR still has no `CASE_ACCESS`. Every management operation is authorised server-side from the caller's own `/api/auth/me`; activation and rollback re-ask inside the change lock. Successful and refused operations are audited without secrets. The sponsor may later assign the capability to its IT/System Administrator role. |
| M2 | Profiles: the existing `AI_ASSISTANT_LLM_*` environment model stays the baseline. IT may add local profiles in a server-side JSON file named by `AI_ASSISTANT_MODEL_PROFILES_FILE` (strict schema, unknown fields refused, no literal credentials). A profile may name a key only by one variable from the reviewed allowlist `AI_ASSISTANT_MODEL_KEY_{OLLAMA,LM_STUDIO,VLLM,LOCAL}`, read from the process environment; never `OPENROUTER_API_KEY` or any other secret. The browser names a profile id only. |
| M3 | Boundary: only literal-loopback profiles reached without a proxy are selectable (the evaluation harness rule, now one shared function). Non-loopback profiles are listed as unavailable; the remote profile is listed as pending authorisation and every action on it is refused before any network call. D-091/D-092 restrictions are intact. |
| M4 | Qualification (conditional approval): provisional technical gates G-4 (model unavailable or stopped mid-answer at most 5 % of turns), G-6 (kept/written model lines at least 0.70; a zero denominator never passes) and G-7 (context capacity verified from the server's own token counts or not passed; every qualification prompt inside the verified bound; cut-short at most 10 %), plus G-1 connection, G-2 completion and G-3 zero unsafe displayed lines (mandatory). G-5 (no allowed line selected) is reported, not gated, until owner-approved answerability labels exist. Answer quality is `NOT_SCORED` while owner gold is not labelled and locked (A-6). Technical qualification is never presented as proof of answer quality; an HR administrator may activate a technically qualified local model only with an explicit acknowledgement that answer quality is unscored (audited as `QUALITY_NOT_SCORED_ACKNOWLEDGED`). |
| M5 | Runtime: one application-wide active model; each answer keeps the model it started with; activation is a compare-and-set on a stored revision that every request checks, so restarts and other processes agree. At start, a stored model that is missing, changed, unselectable, qualified against older answer code or not buildable is replaced by the baseline with an audited reason (`STARTUP_REVERTED`). Run-time model failures give the deterministic case-data answer; switching or rollback needs an administrator. A disabled or unreachable baseline fails safe to case-data answers. |

Implementation notes (project-defined, within the approved scope): qualification runs the
dev-only evaluation harness in its own process (`apps/assistant/scripts/qualify_model.py`)
so the runtime package keeps the Phase A1 invariant that it never imports `assistant_eval`;
one run at a time across processes, bounded by `AI_ASSISTANT_MODEL_QUALIFICATION_MAX_SECONDS`
and ended by the service if it overruns or ignores a cancel. An activated profile refuses a
prompt larger than its verified bound (UTF-8 bytes plus a per-message allowance, a bound the
qualification confirms for that model's tokenizer). Qualifications are tied to the profile's
settings fingerprint and to a hash of the answer code and fixtures, so a prompt, catalog or
guardrail change requires qualifying again. State and audit live in
`apps/assistant/data/models/` (SQLite, not in Git). Audit retention is per class so no class
can push out another: applied model changes and reverts are always kept, refused access by
callers without the capability keeps its newest 1,000 rows, other activity its newest 5,000.

Unchanged: prompts, the response catalog, topic routing, guardrails and the exact-line guard,
retrieval and its permissions, knowledge publishing, CLM rules, read-only CLM access. Not
decided here: remote or non-loopback activation (needs separate privacy, security, provider,
budget and governance approval), per-team models, automatic failover, answer-quality gates.
Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence from qualification
is `LOCAL` technical evidence on synthetic scenarios, never Live CLM behaviour.

## D-094 - AI Assistant local synthetic test mode: GPT-OSS 120B in the CLM chat (OWNER-AUTHORISED, local development scope only)

Status: owner-directed on 2026-10-27. The owner first asked for an explicitly enabled,
local-development-only external API test mode, and then, the same day, revised the
requirement: the model is to be selected in the existing **AI Models** page and used by the
existing AI Assistant chat. There is to be no separate test application, and the remote
profile must stay off by default. Remote routing is allowed only when all of these hold:

- the D-094 authorisation is configured;
- the machine is an authorised development environment;
- the case is verified server-side as approved synthetic fixture data;
- everything sent externally is inside that synthetic boundary;
- the provider, endpoint, credential and budget checks pass;
- an HR administrator has explicitly activated the model.

Otherwise the assistant fails closed to the deterministic case-data answer. No paid call is
made until the owner approves the test manifest, call count and cap.

It is recorded separately from the earlier decisions. D-091 (accepted, dormant A2 scope) is
unchanged except that the T3 module below is a second, reviewed opener of the live gate.
D-092 is **not** accepted (still PROPOSED). D-093 is unchanged for local profiles. Not sponsor
policy.

| # | Decision |
| --- | --- |
| T1 | Off by default. The remote profile is selectable in model management only when `AI_ASSISTANT_LOCAL_API_TEST_DECISION=D-094`, the D-091 and D-092 interlock values, the approved endpoint `deepinfra/bf16` with valid reasoning settings, a literal-loopback CLM backend URL, local `http` browser origins only, and the owner's attestation that auto top-up and prompt logging are off (`AI_ASSISTANT_LOCAL_API_TEST_OWNER_ATTESTS`) are all present. Without the decision the catalogue entry, refusals and behaviour are exactly as before (`REMOTE_NOT_AUTHORISED`). |
| T2 | HR (`MODEL_CONFIG_MANAGE`) uses the existing D-093 workflow. **Test connection** runs the Phase B preflight (D-092 P3, no inference). **Run qualification** is a paid run of only the configured, counted Phase B question manifest (D-092 P10), with the D-093 gates plus G-8 (every call verified). **Activate** requires a passing qualification on the current settings and answer-code basis, a passing preflight and the unscored-quality acknowledgement. **Roll back** returns to the previous model. |
| T3 | One runtime module, `ai_assistant/remote_test.py`, builds the remote model with the live gate open, and only when T1 holds. Every call re-checks T1, reuses a passing preflight for at most `AI_ASSISTANT_LOCAL_API_TEST_PREFLIGHT_SECONDS`, verifies earlier calls first, and is verified after it ends (D-092 P4; a mismatch or a missing generation reference opens the ledger breaker). The blocking checks run off the event loop, and the model refuses any message that fails the boundary's text check (T4) itself, whoever calls it. It is refused once it has made `AI_ASSISTANT_LOCAL_API_TEST_MAX_CALLS` calls (open calls included) since it was activated or the service restarted; the ledger cap is the money limit across restarts. The D-091 request policy, budget guard and credential rules are unchanged, and the key is read only from the process environment. The preflight and verification code moved unchanged from the evaluation harness to `ai_assistant/remote_checks.py` so the service can use them; the harness re-exports them. |
| T4 | **Synthetic boundary.** Before any remote call, the chat checks server-side, from the backend's own reply, that: the case is GARDEN BUSINESS (UEN 11111999A) with registry details from ACRA MOCK; the document list was read (an unreadable list refuses) and every document on the case, and every document the case summary names, has an approved fixture file name; every client-bearing fact is a fixture value; the viewer is a seeded POC user; every knowledge entry is unchanged repository guidance or the synthetic seed (only those are retrieved for the remote model); and the text passes a word screen. Every message may contain only printable ASCII, line breaks, tabs and a short named list of typographic marks. The question and user history are taken exactly as written: every word must come from the synthetic questions, guidance, seed, instructions, fixture values, the app's screen terms or a reviewed list of everyday words. Numbers get no free pass; the user turns may hold at most three number groups between them, never two side by side. Assistant history may also use the synthetic prompts' wording, but not the application's code strings, and no run of more than three number groups. The service's own system messages (with times and ids left out) may also use the application's alphabetic code strings. The boundary file is generated from the repository's synthetic fixtures (`scripts/build_synthetic_boundary.py`), and a test checks that it is current. Anything outside the boundary gets the deterministic case-data answer with a notice, and nothing is sent. Nothing the browser says about the case is trusted. |
| T5 | The chat shows "Answered by GPT-OSS 120B through OpenRouter (D-094 local synthetic test mode)." on model answers, and a boundary notice when the model was not used. The RM chat interface, approved-line validation, guardrails, read-only case access and HR/RM separation are unchanged. |
| T6 | The answer-code basis now includes the D-094 modules, the boundary file and the Phase B question file, so earlier qualifications become out of date and must be re-run. |
| T7 | Paid calls (qualification or chat) need the owner's separate approval of the exact manifest, maximum calls and spending cap before the first run. |

Known limits (recorded, not hidden):

- The typed question and the browser's chat history cannot be proven synthetic. The word
  screen refuses:
  - any non-ASCII character outside the named typographic marks;
  - unknown words, dates and ids;
  - numbers not in the synthetic sources, and more than three number groups (or two side
    by side) in one request's user turns.

  It guards against accidental entry, not deliberate encoding. It cannot recognise:
  - a real name made only of ordinary English words;
  - numbers spelled out as words or written as punctuation;
  - number groups spread over several requests (the cap is per request).
- A forged "assistant" history turn may also use the synthetic prompts' wording, which
  includes the fixture viewer's name, and the service's own full timestamps.

So the owner must not type real customer details. The independent Quality Gate found two
bypasses, both closed by the rules above: in R1, non-ASCII letters, dates and split digits;
in R2, non-ASCII symbols and invisible tag characters. Not decided here: any non-synthetic case, hosted or shared deployment, use
by anyone other than the owner on their own machine, another endpoint or model, or a larger
allocation. Evidence from this mode is external evaluation on synthetic data, never Live CLM
behaviour. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`.

**Merge and first paid run (2026-10-28).** This records events only; the decision text above
is unchanged.

- **Merge.** The repository owner squash-merged PR #123 to main as `9a0dcd5`, with a single
  parent, `c36b8af`. The tree equals the independently reviewed head `0f6e081`.
- **Owner's approval (T7).** Before the first paid run, the owner approved:
  - endpoint `deepinfra/bf16` only;
  - qualification `P01#1,P02#0` (2 calls) plus four listed chat questions on a fresh GARDEN
    BUSINESS case;
  - at most 6 calls;
  - a ledger cap of committed spend plus US$0.10.
- **Run.** It made exactly 6 calls, all verified for provider, model and cost, US$0.001076 in
  total.
  - The qualification passed G-1 to G-8.
  - The four chat answers came from `openai/gpt-oss-120b` with the T5 notice.
  - A negative control was refused (`SYNTHETIC_TEXT_NOT_APPROVED`) and sent nothing.
  - Rollback returned to the local baseline.
- **Hosted CI** for PR #123 was not executed: it is billing-blocked, and that is not a pass.
  The owner accepted a temporary exception for this PR, and hosted CI is to be rerun after 1
  November 2026.

D-092 stays PROPOSED. Further paid runs still need T7 approval.

## D-095 - AI Assistant development synthetic mode, OpenRouter key sources and a US$1.00 daily cap (OWNER-DIRECTED, local development scope only)

Status: owner-directed on 2026-10-28 (the D-095 assignment and its API-key addendum). The
owner then **accepted** the development direction for verified synthetic data on the owner's
own development machine, and the V6 officer-line wording for current, grounded Mock ACRA
officer records (no claim of regulatory verification or sponsor approval), and required V2's
document provenance to use a backend-computed SHA-256 (owner review of PR #126, recorded
below). Built on branch `claude/gracious-lovelace-bjvh2z`; not merged. It is recorded separately and
does not repurpose D-094: without the new flag, D-094 behaves exactly as before and stays the
known working fallback. D-091 (accepted, dormant A2 scope) and D-093 are unchanged except as
listed in V8 and V9. **D-092 stays PROPOSED.** Not sponsor policy. Authority:
`USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`.

**Why D-094 fell back with `SYNTHETIC_VALUE_NOT_APPROVED`.** D-094 admits one case and checks
every client value against 19 values generated from the saved Garden fixtures
(`synthetic_boundary.json`). A Garden case the owner creates in the app carries values the
fixtures never held: a GoldTier id issued by the Mock GoldTier connector (`GT-MOCK-<id>`, the
fixture has `GT-SYNTHETIC-0001`), IDP readings of an uploaded document that differ from the
fixture text, typed observations and decisions. Each is refused as `SYNTHETIC_VALUE_NOT_APPROVED`.
Other demo companies are refused earlier (`SYNTHETIC_CASE_NOT_APPROVED`), other documents by
file name (`SYNTHETIC_DOCUMENT_NOT_APPROVED`) and most natural questions by the word list
(`SYNTHETIC_TEXT_NOT_APPROVED`). Separately, director questions declined because the case facts
carry only the status of the registry officer lookup (P11), so no allowed line could name a
director. The provider and budget controls were not the cause.

| # | Decision |
| --- | --- |
| V1 | **Flag.** Off unless `AI_ASSISTANT_SYNTHETIC_DEV_DECISION=D-095` **and** every D-094 T1 condition holds (D-094 decision, D-091/D-092 interlocks, approved endpoint, loopback CLM backend, local `http` browser origins, owner attestations). Only then does the chat use `synthetic_eligibility.check` instead of the D-094 boundary. |
| V2 | **Which cases may be sent externally (provenance, not value lists).** Only a case whose company `(UEN, legal name)` is in the generated manifest (`synthetic_eligibility.json`: the backend Mock ACRA connector's fixtures, asked through the connector, and the project's synthetic company packs), with registry details from ACRA in MOCK mode, and whose requested UEN and registry acquisition are for that company. A Mock flag, a name or a UEN alone is not enough. Every document on the case must be a verified synthetic fixture **by content**: the backend computes the SHA-256 of the uploaded bytes at upload, stores it on the document record (case snapshot schema 16) and serves it only on the case-scoped `GET /api/onboarding/cases/{case_id}/document-digests`; the assistant reads it with the RM's session and requires it to be the digest of a synthetic fixture file the repository tracks (`apps/backend/tests/fixtures/uat/**`, hashed into the manifest), with that file's media type and size. The digest list must name exactly the listed documents (id and version). An altered byte, another file under a fixture's name, a record stored before schema 16 (no digest), or an unreadable list fails closed (`SYNTHETIC_DOCUMENT_NOT_VERIFIED` / `SYNTHETIC_DOCUMENT_DIGEST_UNAVAILABLE`) before anything is sent; so does a document the summary names that is not one of the verified ones. The viewer must be a seeded POC user. (Revised at owner review: the first version compared name, type and size only.) |
| V3 | **Values.** Values from the Mock registry record or a verified document's extraction are trusted by provenance, whatever they say. A value a person typed (case-creation input, a manual decision, a review entry) must equal a trusted value (`SYNTHETIC_VALUE_NOT_GROUNDED`). A GoldTier id must have the Mock GoldTier connector's form `GT-MOCK-...` or be the synthetic fixture id (`SYNTHETIC_TARGET_NOT_VERIFIED`). |
| V4 | **What may be in the prompt.** The unchanged prompt builder's output for an eligible case (case facts, allowed lines, topic lines), unchanged repository guidance and the synthetic seed only (no app-authored knowledge), and the question and history. Every message holds only printable ASCII, line breaks, tabs and the D-094 typographic marks. The question and history may use any words but no e-mail address, NRIC/FIN- or UEN-shaped id, date, or run of five or more digits (also split by spaces, dashes, dots, slashes or brackets) unless the case already holds it (`SYNTHETIC_TEXT_NOT_APPROVED`). |
| V5 | **Defence in depth.** A passing check gives the exact messages a single-use ticket (120 s). The remote model sends only messages holding a ticket while D-095 is on, or passing the D-094 text check (qualification, D-094 mode); a caller that skips the check sends nothing. |
| V6 | **Directors (answer coverage; project-defined wording, pending owner acceptance).** Topic-only line per current officer: "The ACRA (`<env>`) record for this case lists `<name>` as an officer (role: `<ROLE>`)." Only when the case's own officer lookup is COMPLETE for its UEN, the acquisition is COMPLETE or PARTIAL without error, the record count matches, the lookup and every officer come from the company's own non-live ACRA source, the registry stage is READY, at most 10 officers, former officers left out. The officer records are selection-only facts (never shown to the model except inside the line, never grounding). No other answer-quality change; the exact-line guard, guardrails and fallbacks are unchanged. |
| V7 | **Daily cap.** At most US$1.00 (`DAILY_CAP_CEILING_MICRO_USD`, integer micro-USD) of reserved plus settled remote spend per Asia/Singapore calendar day (UTC+8, no daylight saving), checked in the ledger's own `BEGIN IMMEDIATE` admission transaction, so across threads, processes and restarts. Today's spend = charges of closed calls reserved since the last Singapore midnight + reservations of **all** open calls. `AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD` may only lower it; an out-of-range value refuses every call. It covers qualification and chat, every credential and every activation; the preflight requires room for one large-prompt reservation. Midnight only moves the window: no row, total, reservation, event or audit record is erased, and reconciliation never resets it. No ledger schema change. The lifetime cap, reconciliation, breaker, anomaly checks, per-call verification and the key's own provider limit are unchanged and independent; the strictest applies. Nothing raises a cap or a provider limit, and auto top-up stays off (owner attestation). The daily cap is not a guarantee against provider overbilling; verification and the breaker contain it. |
| V8 | **Key sources (addendum; amends D-091 X3 and the D-094 "process environment only" statement for this local scope).** `OPENROUTER_API_KEY` from the process environment, else the git-ignored `apps/assistant/.env` (only that line, never copied into the environment), else a key an HR administrator enters on AI Models. A source holding a malformed value is reported `invalid` and nothing falls through. The HR key is held in server memory only (no OS-backed store was added: it could not be implemented and tested reliably here; no homemade encryption, no plaintext storage) and must be re-entered after a restart; the stored activation then reverts to the baseline at start (`STARTUP_REVERTED`, `CREDENTIAL_MISSING`) and HR activates again. The qualification process receives an HR key only in its environment, never on its command line. Changing the key rebuilds the model and re-runs the full preflight (the new key's limit and usage against the ledger) before the next call; the daily cap is the ledger's, so a new key never resets it. |
| V9 | **Key management (HR only).** `GET/PUT/DELETE /assistant/admin/models/credential` and `GET /assistant/admin/models/budget` under the D-093 `MODEL_CONFIG_MANAGE` checks, re-checked inside the change; RM, Client Onboarder and Director are refused (`403`, audited). A change needs an allowed Origin header (required, not only checked), JSON, a key shaped like an OpenRouter key, at most 5 attempts per administrator in 10 minutes, and no environment or `.env` key (those cannot be replaced or cleared). The key is never returned, logged, audited or shown; the page shows only source and status. |
| V10 | **Notices.** Model answers in D-095 mode: "Answered by GPT-OSS 120B through OpenRouter (D-095 development mode, verified synthetic case)." Refusals: "GPT-OSS 120B through OpenRouter is used only on verified synthetic development cases, so this answer comes straight from the case data. Reason: `<code>`." |
| V11 | **Qualification basis.** The answer-code basis adds `synthetic_eligibility.py/.json`, `key_sources.py` and `budget.py`, so earlier qualifications are out of date. The paid qualification is unchanged (the Phase B manifest under D-094 T2/T7). |

Not decided here (left disabled): any non-synthetic, real customer or sponsor data; uploads
that are not byte-identical tracked synthetic fixtures (synthetic documents generated on the
fly must be added to the fixtures and the manifest regenerated); hosted, shared or production
deployment; use by anyone but the owner on their own machine; another endpoint or model; a
lifetime allocation above D-092 P3's US$1.00 over the ledger's opening usage (see the
proposal below); names in UBO or ownership answers; and T7 approval for any paid call. Known
limits: the text screen cannot recognise a person's name or details spelled out in words, so
the owner must not type real customer details. The D-094 Garden fixture documents
(`garden-business-01..03`) were never in the repository as files, so D-095 cannot verify them;
D-094 mode is unchanged for them. Evidence from this mode is external evaluation on synthetic
data, never Live CLM behaviour.

**Owner review of PR #126 (2026-10-28).** The owner accepted the D-095 direction and the V6
wording as above, kept the PR on hold for one required correction (V2 by backend-computed
SHA-256, implemented as revised V2: domain field `DocumentProcessingRecord.content_sha256`,
backend-only like the other excluded evidence (persisted, but in no `model_dump`, so older
cases' evidence fingerprints and every browser projection are unchanged); case snapshot
schema 15 to 16 with a strict schema-15 reader that rejects a digest key, reads older
documents as digest-less, keeps every hidden field and never rewrites the stored envelope;
the narrow case-scoped digests route; fixture hashes in the manifest), kept US$1.00 per Singapore day as the desired ceiling, and asked for a separate
proposal for repeated US$1.00 days. No paid inference is authorised.

**Proposal: repeated US$1.00 days (PROPOSED, not implemented; needs the owner's decision).**

| # | Proposal |
| --- | --- |
| B1 | Keep the daily allowance (V7) as the working limit, and replace D-092 P3's fixed lifetime allocation (US$1.00 above the ledger's opening usage) with an owner-set **period allocation**: for example US$7.00 for a named seven-day test window, recorded in the decision log with its dates. The lifetime cap stays in the ledger and is raised only by the operator CLI's explicit `set-cap --raise --confirm-new-cap`, never by the service. |
| B2 | The preflight's two allocation checks (`ledger.cap_within_allocation`, `key.limit_within_allocation`) take the approved period allocation as a setting that can only be lowered at run time, so a cap raise without a matching decision still fails closed. |
| B3 | The OpenRouter key keeps a **non-resetting** limit set by the owner in the OpenRouter dashboard to at most the ledger cap plus one reservation (about US$0.021), so the provider stops spending if the ledger is ever wrong. Auto top-up stays off. |
| B4 | Before each raise: no open calls, every call verified, `budget_ledger.py reconcile --provider-usage <dashboard usage>` after the settle lag, the breaker closed, and the dashboard key usage within US$0.05 of the ledger. A drift above that keeps the breaker open until the operator investigates. |
| B5 | A ledger belongs to one key. A replacement key is first tried against the existing ledger (the preflight's usage check, then `reconcile`); if its usage cannot reconcile, the old key is revoked in the dashboard and a new ledger is initialised at the new key's current usage, keeping the old ledger file for history. So that this never restarts a day's allowance, the service would refuse a new ledger until the next Singapore day after the old ledger's last call (to be implemented and tested before use). |
| B6 | AI Models keeps showing today's spend, lifetime headroom and the key limit; a weekly read of `budget_ledger.py status` and the dashboard is the operator's reconciliation routine. |

**Amendment by D-104 A1 (owner-authorised 2026-10-30).** V1 now reads: D-095 mode is on for a
provider when `AI_ASSISTANT_SYNTHETIC_DEV_DECISION=D-095` and the **shared** interlocks hold (the
D-094, D-091 and D-092 decisions, the model switched on, a literal-loopback CLM backend and local
`http` browser origins: `synthetic_eligibility.shared_mode`), **and** that provider's own readiness
holds. GPT-OSS's own readiness is unchanged (D-094 T1: the approved endpoint, reasoning settings
and the OpenRouter attestations), so its D-095 mode is exactly as before
(`synthetic_eligibility.mode`). Claude's is D-099's (its decision, four attestations, workspace,
limits and ledger), with no OpenRouter condition. V2 to V11 are unchanged: one eligibility check
and one single-use ticket for every provider, and each model re-checks admission for the exact
messages it sends.

## D-096 - AI Assistant HR spending controls on AI Models (OWNER-AUTHORISED, local development scope only)

Status: owner-authorised on 2026-10-28 ("PR #126 — HR Budget Controls and Main Integration").
GPT-OSS 120B was already qualified and activated on the owner's machine; the internal spending
and call limits stopped further testing, and the owner asked for HR Admin → AI Models to
manage them directly. Same scope as D-094/D-095: synthetic data, the owner's own development
machine. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Not sponsor policy.
D-092 stays PROPOSED; D-095 V7 and the D-095 B1–B6 proposal are amended only as stated in W3.

| # | Decision |
| --- | --- |
| W1 | **Daily limit.** HR may set US$0.00 to US$1.00 per Singapore calendar day (integer micro-USD; the D-095 V7 ceiling stays the hard maximum). Until HR saves a value, `AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD` applies (default US$1.00); once saved, the HR value replaces it. It is stored in the model state database (`spending_controls`, one row, compare-and-set on its own revision, CHECK clauses repeating the bounds), read on every request by every service process (a request applies the values in force when it reserves its call) and when a qualification run starts, and enforced exactly as before: per reservation inside the ledger's `BEGIN IMMEDIATE` admission. Lowering it never resets spend: today's spend is still computed from the ledger's call rows. Unreadable controls fail closed (no daily allowance). |
| W2 | **Calls per activation.** HR may set 1 to 200 (the existing setting range); until then `AI_ASSISTANT_LOCAL_API_TEST_MAX_CALLS` applies. It applies to the active model on its next request without a restart, new activation or requalification, and the activation's call count (ledger calls since activation or service start, open calls included) is never reset. The paid qualification keeps the environment value, so a low chat limit cannot break a run. |
| W3 | **Lifetime cap through the application (amends D-095 B1's "never by the service").** HR may set the existing ledger's cap from its opening provider usage up to US$1.00 above it (the D-092 allocation that the preflight's `ledger.cap_within_allocation` check already enforces). A raise needs the same amount confirmed, HR capability re-checked inside the change lock, an allowed Origin, and the existing reconciliation checks against OpenRouter's reported key usage, run by the existing free preflight (public listing, GET `/key`, verification of earlier calls; no inference): breaker closed, no open call, usage accounted for (`check_ledger`); an incomplete check refuses. It uses the ledger's own confirmed `set_cap`, which records `cap_raised`/`cap_lowered`. The opening usage, every call, charge, reservation and earlier event are kept; no ledger is ever created or replaced; neither the key nor its OpenRouter limit is changed. Lowering needs no provider check. |
| W4 | **Provider limits.** AI Models shows the key's remaining OpenRouter limit, the last read time and status, and offers a read-only "Refresh OpenRouter Limits" (the existing free preflight: public listing and GET `/key`, no inference, no case data). The available allowance shown is the strictest of today's allowance, the lifetime headroom and the key limit; calls used and remaining are shown beside it. |
| W5 | **Routes and safeguards.** `PUT /assistant/admin/models/budget/controls`, `PUT /assistant/admin/models/budget/lifetime-cap`, `POST /assistant/admin/models/budget/provider-refresh` (each returns the spending view; `GET .../budget` and the overview carry the controls). HR-only (`MODEL_CONFIG_MANAGE`, re-checked), Origin required, at most 20 spending changes or refreshes per administrator in 10 minutes, every change and refusal audited (content-free; amounts as codes). The provider-side key limit, the US$1.00 daily ceiling, ledger integrity and atomic reservations, model verification and preflight, breaker and reconciliation, qualification and activation, the synthetic-data restrictions and SHA-256 document verification are unchanged. |
| W6 | **Qualifications stay valid.** None of the qualification basis files (`model_qualification.BASIS_FILES`, including `budget.py`, `remote_test.py`, `remote_checks.py` and `synthetic_boundary.json`) is changed, so the basis hash is unchanged and an existing passing qualification and activation remain current. The controls are applied to the active remote model by model management (`model_admin.py`) in place. |

Not decided here: any amount above US$1.00 a day or US$1.00 over the opening usage (D-095 B1–B6
remain a proposal for that); changing the OpenRouter key's own limit; any non-synthetic data.

## D-097 - AI Assistant GPT-OSS 120B naming, optional Fast (low reasoning) configuration, answer progress and latency (OWNER-AUTHORISED, local development scope only)

Status: owner-authorised on 2026-10-28 ("Unified GPT-OSS 120B Speed, Fast Mode, Progress UX and
Naming Improvement"); bounded implementation, offline timing simulations and independent
review; no real or paid OpenRouter call. Same scope as D-094/D-095/D-096 (synthetic data, the
owner's machine). Evidence: `.ai-pipeline/reports/D097_GPT_OSS_LATENCY_FAST_MODE_AND_NAMING.md`.
Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. D-092 stays PROPOSED.

| # | Decision |
| --- | --- |
| Y1 | **Default unchanged.** GPT-OSS 120B with reasoning effort medium on `deepinfra/bf16` stays the configured model, with the same profile id, fingerprint, prompts, token limits, endpoint, provider pinning, ZDR policy, price ceilings and qualification basis (`2bd93aeb8886…`, unchanged). |
| Y2 | **Naming.** The page shows *GPT-OSS 120B — Balanced* (medium) with Model, Provider (OpenRouter / DeepInfra), Framework (Case-grounded Assistant), Reasoning and External inference (verified synthetic cases only under D-095; the approved synthetic test case only under D-094) listed separately. The server sends closed codes; the labels live in the page, so `synthetic_boundary.json` (a basis file built from `ai_assistant` string constants) is unchanged. D-094/D-095 remain authorisation identifiers. No production-readiness claim. |
| Y3 | **Optional Fast configuration.** `AI_ASSISTANT_REMOTE_LOW_REASONING_PROFILE_ENABLED` (default off) lists *GPT-OSS 120B — Fast*: profile id `openrouter_gpt_oss_120b_low`, reasoning effort low, everything else the same (key, ledger, daily/lifetime/call limits, eligibility, guard). Its fingerprint differs, so Balanced's qualification never counts; HR must run its paid qualification (at low) before activating it. No automatic switching, no automatic qualification. Removing the setting reverts a stored Fast activation to the baseline at the next start (audited). Its speed and quality are not established. GPT-OSS 20B is a research comparison only and is not offered. |
| Y4 | **Answer progress.** The chat shows only stages the page observes (the reply starting after the case is read and checked; the first line that passed the exact-line check; the final answer) and the elapsed time; no percentage, estimate, reasoning or unapproved text. After an answer, "What this answer used" lists model or case data, the model name, the number of cited sources and the browser-measured time. OpenRouter's reasoning exclusion is unchanged. |
| Y5 | **Latency.** Measured offline, the application adds about 65 ms before the provider request; about 95% of the time to the first line is provider-side reasoning (live Medium p50 12.4 s). Implemented: generation metadata is read every second for the first 10 s within the caller's unchanged 120 s bound (`openrouter_account.py`, not a basis file): −1.9 s (−34%) for a follow-up asked while the previous call is still being verified; no other measured change. Not implemented (basis files; would need paid requalification): generation reference from the first chunk (a cancelled or timed-out call currently opens the breaker), server-side stage events, background preflight refresh. |

## D-098 - AI Assistant qualification recovery, HR self-service, GPT-OSS-only fallback and flexible spending limits (OWNER-AUTHORISED, local development scope only)

Status: owner-authorised on 2026-10-28 (investigation decisions 1-5 and 6a approved as
recommended; then "D-098 - Authorised Stacked Implementation on PR #127", which also replaces
the US$1 ceilings with flexible limits). Stacked on PR #127 (D-097). Mock and offline evidence
only; no real or paid OpenRouter call. Same scope as D-094 to D-097 (synthetic data, the
owner's machine). Evidence: `.ai-pipeline/reports/D098_AI_MODEL_RECOVERY_AND_BUDGET_CONTROLS.md`.
Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. D-092 stays PROPOSED; the
separate US$0.30 A/B authorisation is unchanged and this decision grants no paid inference.

| # | Decision |
| --- | --- |
| R1 | **Why a session ended.** A 401 for a presented session carries `X-Session-End-Reason` (`SESSION_EXPIRED`, `SESSION_REPLACED`, `SESSION_REVOKED`, `SIGNED_OUT`, `SESSION_UNKNOWN`); ended sessions are remembered by digest only (at most 1024, for one session lifetime). The 401 body, the 8-hour absolute lifetime, one session per account and in-memory sessions are unchanged; no reason is given when no session was presented. The sign-in page names the reason and says server-side work keeps running. Root cause of the reported logouts: a backend restart (in-memory sessions) or the same account signing in elsewhere, surfaced within 3 s by qualification polling; the qualification process never touches the real backend. |
| R2 | **Interrupted runs.** The supervising service stamps `supervised_at` every second; a running qualification with no stamp for 30 s is closed as `INTERRUPTED` (or `INTERRUPTED_BILLING_UNCERTAIN` when a remote call was open or abandoned), audited, never restarted; Cancel closes such a run at once. The ledger, not the run, accounts for any open call (operator reconciliation). |
| R3 | **Classification.** Each run is classified from its content-free summary (and the closed error class of each paid call) as passed, running, cancelled, technical, budget, configuration, quality or billing_uncertain, with a cause, a recommended action and whether a retry is worthwhile. Calls refused before sending are budget, not quality. |
| R4 | **Decision 6a.** Eligibility is the newest passing run for the current fingerprint and qualification basis unless a genuine quality failure (unsafe line, line validity below 0.70 on written lines, cut-short answers, unverified capacity) came after it. Technical, budget, configuration, billing and cancelled outcomes never take a pass away; a quality failure always does. Activation, Rollback, the active model, revalidation after each run and start-up apply the same rule. After a quality failure the same configuration cannot be run again from the UI. |
| R5 | **Paid runs.** A remote qualification starts only with its number of calls confirmed (`confirm_paid_calls`) and every call fitting the strictest applicable limit (daily, lifetime, the key's own as last read); an unchecked key limit or an unreconciled ledger refuses it. No automatic retry, no duplicate run (one running qualification at a time). |
| R6 | **GPT-OSS-only policy (decision 3).** A GPT-OSS configuration that can no longer serve is replaced by a stored *AI unavailable* state (`ai_unavailable`, audited), never by the local baseline or another model, and is never a rollback target; this supersedes D-097 Y3's revert to the baseline. HR activates a qualified configuration or the baseline by hand (decisions 1 and 2: no automatic preferred or backup switching). A local D-093 profile still reverts to the baseline. |
| R7 | **Labelled guidance.** An answer the model did not write is labelled *Case-data guidance, not AI-generated* where it is read. |
| R8 | **Flexible limits (supersedes the US$1 ceilings of D-095 and D-096).** US$1.00 is the default daily allowance, not a ceiling; HR may set it higher or lower. The lifetime cap has no US$1 allocation ceiling (at or above the opening usage). Only the ledger's technical bound (`MAX_MICRO_USD`, 10^12 micro-USD) applies. Raising either needs the amount confirmed and a fresh free preflight showing the key's own limit is set, never resets and is finite (`key.limit_finite`); a lifetime raise also needs the existing reconciliation checks. A key with no limit fails the preflight, so no call is sent and nothing can be raised. At every call the ledger admits only within the lifetime cap and the daily allowance, and the preflight requires room on the key: the strictest wins. The key's provider-side limit, spend history, reservations, reconciliation, the breaker and auditing are unchanged and never reset. Existing state databases keep their controls (one-time table rebuild without the US$1 CHECK). The Phase B harness keeps its D-092 allocation. |
| R9 | **Qualification impact.** R8 changes basis files (`budget.py`, `remote_checks.py`, `remote_test.py`, `synthetic_boundary.json`): the basis becomes `b4049047884e…`, so every earlier GPT-OSS qualification (Balanced and Fast) is out of date on this code. History is kept; nothing is marked qualified automatically; an active GPT-OSS configuration becomes *AI unavailable* at start-up. A paid requalification of Balanced (and of Fast if used) is needed after integration and needs its own owner approval. |
| R10 | **Safe messages.** Every fixed model-management refusal is in the browser's safe message list (two were missing), checked by a test. |
| R11 | **Lifetime-cap compare-and-set (ported from PR #128 Z7; owner Option A, 2026-10-28).** A lifetime-cap change is decided on the cap the page showed (`expected_cap_micro_usd`, required for a raise; a stale view is refused first) and the cap read at the start of the request is compared again inside the ledger's own write transaction (`BudgetLedger.set_cap(expected=…)`, `CAP_CHANGED`), so an operator's change made in between (for example during the raise's free preflight) refuses the HR change (`CONTROLS_CONFLICT`, audited) instead of being overwritten. Spend, calls, reservations, reconciliation and the daily view are unaffected. |
| R12 | **Fail-closed start-up (ported from PR #128 R4/R5 and completed).** Until the stored activation is read and usable there is no model (never the environment baseline in place of GPT-OSS). A GPT-OSS revert that cannot be stored gives no model now (revision -1) and is retried on the next request; repeated conflicts follow the last stored activation read, never a model in memory; a revert whose audit write fails is recorded once writes work again; while a revert is not yet stored, the page gets the stored revision, so HR activation is never blocked. A locked state database makes a request wait a bounded number of SQLite timeouts (10 s each: at most three revert attempts plus one audit retry) before it fails closed. An intentionally selected local profile keeps the D-093 revert to the baseline; case-data guidance stays available throughout. |
| R13 | **Key limit visibility.** The spending view shows the key's own limit, usage and reset policy as `/key` reports them; account credits are never read and are shown as such. An exhausted key limit is an owner action (`ESCALATE_KEY_OWNER`; a paid start is refused `PROVIDER_KEY_LIMIT_EXHAUSTED`), never an HR spending setting. |
| R14 | **Owner decisions confirmed (2026-10-28).** Automatic Fast→Balanced switching: not approved. An IT-configured daily limit above US$1.00 (`AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD`) is permitted under privileged deployment control and the existing ledger and key-limit safeguards (no HR confirmation applies to it). HR call-count changes keep the existing audited behaviour for this slice. Changing the key's provider limit is the owner's or operator's responsibility, never an HR budget setting. No paid requalification is authorised yet. A failed answer-quality gate (supersedes a pass) and an unresolved billing verification (operator reconciliation; never bypassed) remain distinct. PR #128's conflicting qualification-retry and fallback rules (latest-run-only activation, Z6 keeping a superseded model active) are not adopted. |

## D-099 - AI Assistant Claude Sonnet 5.5 Balanced and Fast on AI Models under Anthropic-specific safeguards (PROPOSED)

Status: PROPOSED by the project team on 2026-10-29 under the owner's "Claude Sonnet 5.5
Balanced/Fast Integration" assignment (bounded development and offline verification only; no
paid call, activation, guardrail change or merge). Stacked on PR #129 (D-098). Evidence:
`.ai-pipeline/reports/D099_CLAUDE_SONNET_CONSOLE_INTEGRATION.md` and the owner-scored benchmark
(`CLAUDE_API_MODEL_BENCHMARK.md`, local commits `7fd0e43`, `cb9b996`, `5964ea2`). Not accepted
until the owner says so; not sponsor policy. D-091 to D-098 are unchanged.

Update 2026-10-29 (Option B): the owner approved implementing Anthropic-specific alternative
spending safeguards (C6 to C9), explicitly **not** as a weakening, removal, bypass or
replacement of any OpenRouter/GPT-OSS protection. Implemented offline on the D-099 branch
(PR #130 stays draft); evidence `.ai-pipeline/reports/D099_OPTION_B_IMPLEMENTATION.md` and the
design `.ai-pipeline/001_planner/D099_ANTHROPIC_SPENDING_CONTROL_DESIGN.md`. Not authorised:
paid inference, paid qualification, real-data transmission, runtime activation, automatic
provider switching, merge or production deployment. C2 and C4 below describe the state before
Option B and are superseded where C6 to C9 say so.

| # | Proposed decision |
| --- | --- |
| C1 | **Two configurations of one model.** `claude-sonnet-5-5` on `https://api.anthropic.com` (`anthropic-version: 2026-10-21`, `max_tokens` 3,000, no sampling parameters, tools, metadata, service tier, speed, inference geography or server-side fallback): *Claude Sonnet 5.5 — Balanced* (`anthropic_claude_sonnet_5_5_medium`, effort medium, adaptive thinking; recommended) and *Claude Sonnet 5.5 — Fast* (`anthropic_claude_sonnet_5_5_low`, effort low, thinking `between_tools`). Each has its own profile id and fingerprint (provider, base URL, API version, every request field, timeout and prices), so no qualification is shared between them or with GPT-OSS. Standard prices US$2 / US$10 per million input / output tokens (pricing page read 2026-10-29). No Haiku or Opus. |
| C2 | **Listed, never usable.** AI Models lists both. Without `AI_ASSISTANT_ANTHROPIC_DECISION=D-099` they show *not authorised* (`ANTHROPIC_NOT_AUTHORISED`, refused as `REMOTE_NOT_AUTHORISED`); with it, *unavailable* (`ANTHROPIC_PROVIDER_CONTROLS_MISSING`, refused as `PROFILE_NOT_SELECTABLE`). Connection test, qualification and activation are refused and audited before any network call; a stored Claude activation becomes *AI unavailable* (D-098 R6), never another model. |
| C3 | **Why (the blocking gap).** The remote profile's spending safety rests on three provider-side controls that a direct Anthropic API key does not give: a readable finite, never-resetting key limit (D-098 R8 `key.limit_finite`); per-call verification of model and cost from a separate provider record (D-092 P4); and a ledger anchored on and reconciled against provider-reported usage (D-091 X5). Anthropic spend limits are enforced but readable only in the Console; usage and cost are readable only through the Admin API (organisation Admin key, data after about 5 minutes, cost per day). The existing `BudgetLedger` accepts only the OpenRouter profile and needs provider-reported usage, so reusing it would change `budget.py` (a budget protection and qualification-basis file). |
| C4 | **Dormant adapter.** `ai_assistant/anthropic_chat.py` is reviewed and tested but composed nowhere: it accepts only an in-memory mock transport (D-091 L1) and `build` always refuses. It applies the D-095 V5 send rule (eligibility ticket or D-094 text check), sends the leading system messages as system blocks unchanged (refusing a system message after history), pins the model at `message_start` before any text, treats a non-standard tier, geography or speed as a routing anomaly and prompt-cache tokens or missing counts as malformed usage (cost dropped, unsettled), maps provider spend limits to `payment_key_limit` and never yields thinking. |
| C5 | **Synthetic boundary vocabulary (owner-approved 2026-10-29; applied).** `synthetic_boundary.json` (a qualification-basis file) admits in the service's own system messages every alphabetic word of every string constant in `ai_assistant/`, and a test requires it to be current. Any Claude integration adds words through the model ID, profile IDs, provider code, endpoint and request fields. Reduced to the unavoidable seven (`adaptive`, `anthropic`, `claude`, `com`, `geo`, `sonnet`, `thinking`; docstrings in the new modules written as comments, ids named by effort as GPT-OSS Fast's is, labels kept in the page per D-097 Y2), the file was regenerated with its existing generator under the owner's conditions: exactly these seven words added to `code_vocabulary`, nothing removed, no other section, schema or generator change; the conversation, prompt and assistant vocabularies, case data, documents, values and knowledge are unchanged, so a question or history using the words is still refused. The qualification basis moves from `b4049047884e…` (D-098 R9) to `235030035ccc…`: every earlier GPT-OSS qualification (Balanced and Fast) is out of date once this merges and needs a paid requalification under its own owner approval. History is kept; nothing is marked qualified automatically. |

Not decided here: which equivalent provider controls are acceptable (owner options in the
report: an organisation Admin key for usage reconciliation, an owner-attested Console workspace
spend limit with manual reconciliation, or both), a Claude budget ledger, Claude key sources and
HR key entry, routing of model-management actions by provider, telemetry profile ids, adding the
adapter to the qualification basis (which would make every GPT-OSS qualification out of date),
the catalog gaps (P06#1, P01#0, P04#0) and deterministic action refusals. Evidence class: mock
and offline only; no Live, Sandbox or provider-status claim.

| # | Option B (owner-approved policy, implemented offline 2026-10-29) |
| --- | --- |
| C6 | **Policy (not equivalent to OpenRouter).** A dedicated, non-default Anthropic workspace and a workspace inference key (never an organisation Admin key; none is introduced into the runtime); a workspace monthly spend limit of at most US$5.00, set in the Console and owner-attested because it cannot be read with an API key; a separate Anthropic ledger (`anthropic_claude_sonnet_5_5`, its own file) whose cap may never exceed US$5.00 lifetime (never reset) nor the attested workspace limit; at most US$1.00 a Singapore day and 20 calls per activation or restart (policy ceilings enforced in settings and again at run time); conservative full-reservation accounting whenever billing is uncertain; the workspace (`anthropic-workspace-id` response header), the requested model and standard routing (tier, geography, speed) verified in every reply before any text; manual reconciliation against the Console's workspace usage within 24 hours before a paid qualification, an activation or a cap raise and within 7 days for chat; fail closed on stale reconciliation, provider mismatch or missing billing evidence; no automatic switch from Claude to GPT-OSS or any other model; the inference key revoked at the end of the FYP (owner attestation `key_revoked_at_fyp_end`). |
| C7 | **Scope.** Verified synthetic development cases only, exactly the cases GPT-OSS may answer: the chat applies the unchanged D-094 synthetic boundary and D-095 eligibility to a Claude configuration, and the model itself re-checks every call (D-095 V5). Development machines only (loopback CLM backend, local browser origins), behind the same D-094/D-091/D-092 interlock as GPT-OSS plus `AI_ASSISTANT_ANTHROPIC_DECISION=D-099` and the four owner attestations. Never real data. |
| C8 | **Changes P-1 to P-7 (additive, Anthropic-specific).** P-1 the owner-attested workspace limit and the ledger ceiling replace the readable key limit (R8) for Claude only. P-2 in-band verification (workspace, model, routing, complete usage) plus manual reconciliation replace the per-call generation record (P4) for Claude only. P-3 `budget.PROFILES` gains the Anthropic profile and every reservation names its profile, so neither provider's calls can be admitted by the other's ledger; neither provider's preflight recovers or verifies the other's ledger (its profile is read before the ledger is opened), the HR lifetime-cap change applies to the OpenRouter ledger only, and the two ledger paths may never name one file (`LEDGER_PATH_SHARED`); existing OpenRouter ledgers keep working unchanged. P-4 Claude key sources: `AI_ASSISTANT_ANTHROPIC_API_KEY` from the process environment, else the git-ignored `.env`; inference keys only, Admin, OAuth and session tokens refused. P-5 per-provider controls: Claude has its own fixed settings; the GPT-OSS HR spending controls never apply to it (HR key entry and HR-editable Claude limits are deferred with the D-100 UI work). P-6 R6 extended: a stored Claude activation that is no longer usable becomes *AI unavailable*. P-7 boundary regeneration with the existing generator: three identifier fragments (`ant`, `usr`, `wrkspc`, from the inference-key and workspace-id format checks) added to `code_vocabulary` only; no question, history, eligibility or client-data change. Also fixed: QG F1 (a second `message_start` ends the call unsettled) and F2 (admission decided again per call). The adapter, profiles and runtime join `BASIS_FILES`; the basis moves to `adec795f61bd…`. |
| C9 | **Residual billing risks (owner-accepted).** The workspace limit and the workspace's dedication are attested, not read; a reply's usage is Anthropic's own claim with no separate per-call record; Console usage lags and is reconciled by hand, so drift can persist up to the reconciliation window, bounded by the daily cap, the ledger ceiling and the workspace limit Anthropic itself enforces; follow-up questions whose prompt places knowledge or topic lines after history cannot be sent unchanged to the Messages API and get the case-data answer (refused before any reservation). |
| C10 | **D-099-FU1 multi-turn compatibility (PROPOSED, 2026-10-29).** Supersedes the last clause of C9. The Anthropic adapter alone converts the service's known prompt shape: its leading system messages, a strictly alternating user/assistant history (starting with the user, ending with an answer), then at most the service's own per-question system messages identified by their fixed starts and in the service's order (knowledge, question topic, case page terms), then the question. Every system message becomes a top-level system text block, unchanged and in prompt order; user and assistant turns keep their order; nothing is relabelled, merged, added or dropped. Any other shape (a system message inside the history, an unknown or reordered or repeated per-question block, another role, extra keys, non-text content, a non-alternating history) is refused before any reservation or request. The canonical messages, GPT-OSS requests, D-094 admission, D-095 single-use tickets (still bound to the exact canonical messages), reservations, G-8, ledgers and the no-switch rule are unchanged; the boundary vocabulary is unchanged. Evidence `.ai-pipeline/reports/D099_FU1_MULTI_TURN.md`; the basis moves `adec795f61bd…` → `33f602653de7…`. |

**Amendment by D-104 A1 (owner-authorised 2026-10-30).** C7's "behind the same D-094/D-091/D-092
interlock as GPT-OSS" now means the shared interlocks only (the D-094, D-091 and D-092 decisions and
the development-machine checks); Claude's D-095 mode no longer depends on OpenRouter's endpoint,
reasoning settings or attestations (`ClaudeTestModel.development_mode`, used by the chat and by the
adapter's per-call re-check). Every Anthropic safeguard is unchanged: `AI_ASSISTANT_ANTHROPIC_DECISION`,
the four owner attestations, the workspace id and limit, the D-102 limits, the separate ledger, the
reconciliation windows, the preflight and in-band verification. Claude still answers only the cases
GPT-OSS may answer, under the same eligibility check.

## D-100 - AI Assistant AI Model Console Phase 1 (PROPOSED)

Status: PROPOSED by the project team on 2026-10-29 under the owner's AI Model Console
assignment (Direction B with Direction A's side menu); draft PR #131. Presentation only:
AI Models becomes a sectioned console (Models & Overview, Providers, Spending & Limits,
Qualifications & Recovery, Audit History) on the existing capability-checked route
(`?section=`), with configuration tiles, an inspector and confirmation dialogs. No API,
qualification, gate, spending-limit, key, permission or backend change; the D-095 to D-098
controls are kept unchanged. Evidence: `.ai-pipeline/reports/D100_AI_CONSOLE_PHASE1_QUALITY_GATE.md`
(PASS WITH MINOR FIXES) and `.ai-pipeline/reports/D100_AI_CONSOLE_PHASE1_REQG.md` (re-QG PASS).
Phase 2 is not started and needs a separate go-ahead. Not accepted until the owner says so; not
sponsor policy. D-099 is unchanged by this entry.

Update 2026-10-29 (integration with D-099 and D-099-FU1): on the integration candidate the
console treats the Anthropic deployment as a second external, paid API (paid-run confirmation,
activation warning, provider-worded refusal codes, inspector details, a GPT-OSS-only note on
Spending & Limits). Both providers keep their separate spending controls and confirmations;
nothing switches between them automatically. Evidence `.ai-pipeline/reports/D099_D100_INTEGRATION.md`.

Update 2026-10-29 (Phases 2 to 4, local branch `feat/d100-ai-console-phases-2-4`, not
published): still presentation only, from the data the page already reads. Providers gains one
card per provider with who manages what; Spending & Limits separates the HR-editable GPT-OSS
limits from a read-only Claude panel showing only the server's paid-qualification figures;
Qualifications & Recovery separates technical qualification from answer quality, lists
unqualified Claude configurations (first run only through the paid confirmation) and words
codes per provider (closing the integration gate's M-1, M-2 and I-1); Audit History filters
only the loaded events and says so; dialogs make the background inert (D3) and keep focus in a
newer dialog (D5). No API, gate, limit, key, permission, routing or basis change. HR key entry
and HR-editable Claude limits remain deferred: they need new backend authority.

## D-101 - Partnership and Government entity types in the zero-touch database demo set (candidate)

Status: candidate. Authority `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`: owner approval
in chat 2026-10-29 for both plans; Shane to confirm here. Not legal UBO policy (Q-004), not ACRA
capability (Q-012), not Live, not sponsor policy.

Decision: the database demo set has one clean case per entity type. Company (Alpha `209990101A`)
is unchanged.

- **Partnership (Gamma `209990103C`).** The registry seed lists partners P1..P6 by name and role only,
  with no ownership links or percentages, because a partnership register carries no shares. The split
  comes only from a reviewed partnership agreement (`Partner Share: <name>: <n> percent[: <type>]`
  lines, exact-label extraction in `connectors/local_pdf_idp.py`). The rows are suggestions, reused
  through the existing document-ownership and manual-ownership-evidence path, and count only after
  the RM submits them. Fail-closed cross-checks (`services/partnership_agreement.py`): a current
  reviewed agreement for this entity at the frozen confidence threshold, registry and agreement
  partners equal under the existing name normalisation, no duplicates, every share > 0, a Decimal
  total of exactly 100, and the confirmed declaration equal to the agreement. Any failure keeps the
  case blocked and in review. The existing Decimal engine computes UBOs (P1 30%, P2 25%). Labels say
  "from partnership agreement, RM-confirmed", never ACRA or registry.
- **Government (DEMO PARKS FYP TEST AUTHORITY, `T99FY0105G`; renumbered `T99GB0105G` by D-114).** It replaces the classification-only
  `DEMO GOVERNMENT FYP TEST AUTHORITY`, `209990105E` fixture and its scan. The UEN is a fictional
  T-format value that passes `is_eligible_singapore_uen`; its letters are not claimed as an official
  code. Government bodies are not ACRA-registered: identity comes from the existing local synthetic
  seed (`LOCAL_SYNTHETIC_UAT_V1`), with no new `SourceSystem`, labelled "Local synthetic identity: not
  ACRA-registered; government status from reviewed document". Following MAS Notice 626 para 6.12,
  when the KYC type is Government and the legal form is `GOVERNMENT` (a new `RegistryLegalForm`
  value for that exact source value only; others stay `OTHER`), readiness and zero-touch replace the
  ownership requirement with `GOVERNMENT_STATUS_REQUIRED` (rule BPD-GOVERNMENT-STATUS-1). It is met
  only by a current reviewed government status document with the labelled fields plus an explicit,
  version-checked RM confirmation; never automatically and never from the label alone. Readiness then
  records ownership evidence `GOVERNMENT_STATUS_CONFIRMED` with 0 UBO candidates. Foreign government
  bodies are out of scope and keep normal checks.
- **Legal-form compatibility (both).** `bounded_classification_compatible` uses a small table:
  Company only on COMPANY; Partnership on BUSINESS_PARTNERSHIP, LLP or LP; Sole Trader on
  BUSINESS_PARTNERSHIP; Government only on GOVERNMENT. A known mismatch is UNSAFE and goes to manual
  review, never auto-corrected. An unknown legal form (`OTHER`) is UNSAFE for an automatic candidate,
  but a manual pick is allowed.
- **Narrowed PARTIAL local seed.** A PARTIAL bundle is used only from the `LOCAL_SYNTHETIC_UAT_V1`
  dataset with a complete entity profile, for BUSINESS_PARTNERSHIP or GOVERNMENT, fresh, and never as
  a cache hit.
- **Persistence.** Case snapshot schema v17. Older readers strictly reject the new fields; the new
  optional fields are omitted when empty, so older case fingerprints are stable.

Defaults, Shane to confirm:
- Partner shares use the existing policy UBO threshold (default 25%), the same as company shares.
- Government proof is a reviewed document showing the founding Act or Gazette, the UEN and a letter
  of authority. This is project-defined, not sponsor-confirmed.
- Authorised signatories appear only on the status document: they are not extracted, stored as an
  ownership graph or sent to GoldTier. The case page says so.
- `GOLDTIER_REGISTRATION_TYPE_POC_VALUE` stays "ACRA" for every case, including Government.
- A Partner Share line may end with an explicit owner type (for example `: NATURAL_PERSON`), so the
  existing document-ownership comparison has an owner type.
- On Government cases the Ownership & UBO stage keeps its title and holds the Government status step,
  so the AI Assistant's section links match.
- The D-094 synthetic boundary and eligibility manifests were regenerated with the existing
  generators: `code_vocabulary` +9/-1; eligibility adds the two new fictional PDFs and drops the
  retired one. The company list is unchanged, so remote AI use on the Government case stays refused.

Out of scope: LLP- or LP-specific rules, `Partnership - Regulated`, foreign government bodies,
GoldTier hierarchy or related-party writes, and the Garden and Marketplace Mock lanes (apart from
the compatibility table: Garden tests now use "Partnership - Unregulated", and four classification
tests use "Company - Public").

## D-102 - AI Assistant Claude spending ceiling US$30.00 and HR-editable Claude limits (ACCEPTED, synthetic-only FYP development)

Status: ACCEPTED by the repository owner on 2026-10-30 for synthetic-only FYP development,
including the revised spending limits, the HR controls, the tightened call-limit raise (E3)
and the documented residual risks (update below). Not sponsor policy.

Proposal record (2026-10-29): PROPOSED by the project team on 2026-10-29 at the owner's direction during D-099
runtime set-up: the owner set the dedicated Anthropic workspace's monthly limit to US$30.00
and asked for Claude's limits to be changeable from the HR AI Model Console. Implemented
offline on branch `feat/claude-hr-spending-d102` (not committed or published). Not accepted
until the owner says so; not sponsor policy. Amends D-099 C6 (the US$5.00 ceilings) and the
deferral of HR-editable Claude limits in D-099 and D-100; every other D-099 safeguard and every
OpenRouter/GPT-OSS protection is unchanged.

| # | Proposed decision |
| --- | --- |
| E1 | **Ceilings.** Claude's code ceilings become US$30.00 lifetime (ledger cap and attested workspace limit; was US$5.00) and US$5.00 per Singapore day (was US$1.00). 20 calls per activation and 32 KiB prompts are unchanged. The ledger cap stays at most the lower of the lifetime ceiling and the owner-attested workspace limit, re-checked on every call. |
| E2 | **HR controls.** An HR administrator (MODEL_CONFIG_MANAGE) may set Claude's daily allowance (US$0.000001 to US$5.00), calls per activation (1 to 20) and the Anthropic ledger's lifetime cap (above its opening usage, at most the lower of US$30.00 and the workspace limit) on Spending & Limits, on Claude's own routes (`PUT /assistant/admin/models/budget/claude/controls`, `.../budget/claude/lifetime-cap`). Claude's controls are a separate row, table and revision from GPT-OSS's; neither ever applies to the other. Until HR sets them, the environment defaults apply (US$1.00 a day, 20 calls). |
| E3 | **Raises.** Raising the daily allowance, the calls per activation (owner-approved after QG L1) or the lifetime cap needs the new value confirmed, Claude fully configured (D-099 readiness) and the Anthropic ledger reconciled with the Console within 24 hours, with the breaker closed and no open call; the lifetime cap also needs the cap the page showed (compare-and-set, re-checked in the ledger's write transaction). Lowering never needs a confirmation or reconciliation; a strictly lower lifetime cap (still above the opening usage) is allowed even when no workspace limit is attested (QG L2), and never enables Claude. Spend, calls and ledger history are never reset. |
| E4 | **Unchanged.** The workspace id, its monthly limit and the four owner attestations remain operator/owner settings (not HR-editable). The same Origin requirement, per-administrator rate limit, audit (content-free closed codes), fail-closed unreadable controls (no Claude call), in-band verification, no automatic switching and synthetic-cases-only scope apply. HR controls reach an active Claude configuration in place and the paid qualification's daily allowance. |
| E5 | **Qualification.** `anthropic_runtime.py` is in the qualification basis, so the basis moves `33f602653de7…` → `4c54e4dd9dbd…`: every earlier qualification is out of date once this merges, and GPT-OSS and both Claude configurations each need a new, separately approved paid qualification. |

Independent Quality Gate (2026-10-29, candidate `f1d32387…`): CONDITIONAL PASS, Low findings
only. L1 (call-limit raises ungated) and L2 (a reduction refused without an attested workspace
limit) were remediated as above at the owner's direction; L3 (the GPT-OSS view counted an active
Claude configuration's calls) was fixed so each provider's view counts only its own calls. L4
(recorded, not changed): the raise checks (reconciliation, breaker, open calls) are read just
before the change rather than inside the ledger's write transaction, and readiness does not
require the key to be present. The impact is negligible because the ledger admits every call
under its own transaction and the cap change is compare-and-set; changing it needs a separate
finding or approval.

Residual risk (owner-accepted by the direction above, to be confirmed on review): up to US$30.00
lifetime and US$5.00 a day may be spent on Claude instead of US$5.00 and US$1.00; the workspace
limit is still attested, not read, and Anthropic's own workspace limit remains the outer bound.

Update 2026-10-30 (owner acceptance, integration and evidence): the owner accepted D-102 as
recorded in the status line, after the independent re-QG PASS on the remediated candidate
`e4f58e36e17c…` (committed unchanged as `93d154d`, cherry-picked onto main `2911b54` with
byte-identical application code and tests). Accepted limitations, unchanged: L4 (the raise
checks are read just before the change, outside the ledger's write transaction; readiness does
not require the key), N1 (the lifetime help text's "lowering it is always allowed" omits that a
lower cap must stay above the opening usage and match the shown cap; the inline validation is
exact) and I1 (with unreadable Claude controls, a direct API call that passes every gate ends in
an unaudited HTTP 500 with nothing written, as on the GPT-OSS route). Evidence:
`.ai-pipeline/reports/D102_QUALITY_GATE.md` (CONDITIONAL PASS, `f1d32387…`),
`.ai-pipeline/reports/D102_REQG.md` (PASS, `e4f58e36…`) and
`.ai-pipeline/reports/D102_INTEGRATION.md`. The full assistant suite on this Windows machine is
not a clean PASS: 14 tests fail with `OSError: [Errno 24] Too many open files` in a full run
(identically on unmodified main) and pass when run alone; that is an environmental limitation.

## D-104 - AI Assistant data access policy on AI Models and provider-neutral synthetic eligibility (OWNER-AUTHORISED direction; A1 implemented offline)

Status: the project team proposed this on 2026-10-30 ("Provider-Independent Data Access &
Synthetic Mode"). The owner then accepted the HR Data Access & Privacy design direction and
authorised the bounded A1 implementation the same day ("D-104 - Owner Direction: Complete
Provider-Neutral Synthetic Eligibility"). Built offline on branch
`feat/assistant-data-access-policy`, which is not committed or published. No paid call,
qualification, activation, UAT request or live inference was made, and the running service and its
state were not touched. D-101 and D-103 are used by other work. Not sponsor policy. Authority:
`USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence:
`.ai-pipeline/reports/D104_DATA_ACCESS_POLICY.md`.

**Root causes (before A1).**

- *Provider coupling.* D-095 mode was `synthetic_eligibility.mode`, which requires the D-094
  OpenRouter readiness: the endpoint, the reasoning settings and the OpenRouter attestations. The
  Claude runtime used the same function. So a fully ready Claude without the OpenRouter
  attestations ran in D-094 mode only.
- *The `v1` refusal.* A live onboarding adds this timeline event: "Advisory onboarding intelligence
  was evaluated under policy catalogue v1." The case facts put it in the system prompt, and D-094's
  word screen refuses `v1` (`SYNTHETIC_TEXT_NOT_APPROVED`, nothing sent). This is an admission
  refusal, not a model reasoning failure. The D-094 fixtures predate the event. D-094 is unchanged
  and still refuses it, so it stays the fixed-fixture regression mode.

| # | Decision |
| --- | --- |
| A1 | **Provider-neutral D-095 mode (implemented).** `synthetic_eligibility.shared_mode` holds the shared conditions. GPT-OSS keeps `mode` (shared conditions plus its unchanged D-094 T1 readiness). Claude (`ClaudeTestModel.development_mode`) and a policy-restricted model use the shared conditions, each under its own readiness. The chat asks the active model for its mode; a model without one keeps GPT-OSS's. The eligibility check, the single-use ticket and the adapter's per-call re-check are the same for every provider. D-095 V1 and D-099 C7 are amended as recorded under them. |
| Z1 | **Control.** AI Models has a *Data Access & Privacy* section, "Restrict AI to verified synthetic cases", showing the server's effective policy (`GET /assistant/admin/models/data-access`, also in the overview) and the verification in force for the active model. |
| Z2 | **Locked classes.** GPT-OSS through OpenRouter and Claude through Anthropic are restricted in their own code, whatever the stored policy says. So is a model IT configured on an endpoint that is not a literal loopback address (`it_configured`), with or without model management. It is never treated as local; `localhost` and the machine's own LAN address count as non-loopback too, which fails closed. Only a model passed in by tests or the evaluation harness is exempt (re-QG M1). `PUT` refuses `restrict_external: false` (`EXTERNAL_DATA_POLICY_LOCKED`, audited). Real customer data on an external provider needs a separately approved external-data decision and deployment controls. |
| Z3 | **Local models (literal loopback).** Every authorised case by default (D-093 unchanged). HR may restrict them; letting a restricted local model answer every case again needs `confirm_widen` (`WIDEN_CONFIRMATION_REQUIRED`). A restricted model, or one under an unreadable policy (fail closed), is wrapped by the selector (`data_access.SyntheticOnlyModel`). It gets the same gate as the external models, re-checks every call and never warms up. A refusal shows its own notice (QG L1). |
| Z4 | **Change rules.** HR only (`MODEL_CONFIG_MANAGE`, re-checked inside the change lock). Origin is required. Data access changes have their own per-administrator limit (`DATA_ACCESS_RATE_LIMITED`, QG L3). The request is strict JSON. Changes are compare-and-set on the policy's revision (`DATA_ACCESS_POLICY_CONFLICT`); an unreadable policy refuses changes (`DATA_ACCESS_POLICY_UNAVAILABLE`). The policy row and its audit row are written in one transaction, so a change never exists without its record (QG L4). The audit row holds the actor, the time and the old and new setting as a closed code, for example `LOCAL_DEFAULT_ALL_CASES_TO_LOCAL_SYNTHETIC_ONLY`. One row (`data_access_policy`), kept across restarts. Without model management (no profiles file), the local setting cannot be changed and a loopback model behaves as before. |
| Z5 | **Unchanged.** The D-094 boundary and its vocabulary file, the D-095 checks and manifest, the guardrails, the knowledge rules, role separation, redaction and retention, limits, budgets, ledgers, spending controls, the activation rules and the no-switch rule. New strings use only words the D-094 boundary already holds, so `synthetic_boundary.json` is unchanged. |
| Z6 | **Display.** With Claude active, the Overview shows Claude's own figures, even without the GPT-OSS spending view (QG L2). Explained but not changed: the chat counts raw pipeline steps while the case page groups them; typed and suggested questions use the same request. |
| Q1 | **Qualification basis.** `main.py`, `anthropic_runtime.py` and `synthetic_eligibility.py` changed, and `data_access.py` joins `BASIS_FILES`, so the basis moves `65f22e46c509…` → `598cfe14753d…`. Once this runs, every earlier qualification is out of date, including Claude Balanced's. A stored activation then becomes *AI unavailable* at start-up (D-098 R6, D-099 P-6) until a new, separately approved paid qualification. History is kept, and nothing is marked qualified automatically. |

Not decided here: real or sponsor data on any external provider; approving a model on another
machine for real data (a deployment decision); paid requalification.

## D-103 - Support role: knowledge review moves from Directors to a Support tab, with read-only policy (OWNER-DIRECTED, local POC scope)

Status: owner-directed on 2026-10-29. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`.
Not sponsor policy: who reviews knowledge stays an open sponsor question (Q-014), and D-073's
reviewer-role reuse, D-083 (single reviewer) and D-084 remain PROPOSED. Amends only the
reviewer identity in D-073/D-074 and ADR-012; their exact-line, content-hash, maker-checker and
redaction rules are unchanged.

| # | Decision |
| --- | --- |
| S1 | **Role.** New backend role `SUPPORT`: team-less (like Director and HR), capabilities `POLICY_VIEW`, `KNOWLEDGE_REVIEW` and `KNOWLEDGE_CASE_READ` only. No `CASE_ACCESS`, `POLICY_MUTATE`, `POLICY_APPROVE`, identity, team, sandbox or model administration. HR may create further `SUPPORT` accounts on the Users page (12–128 character passwords, unchanged). |
| S2 | **Seeded account.** `support-user` ("Support User") is bootstrapped like the other seeded profiles from `PHASE13_SUPPORT_USER_PASSWORD_HASH` (scrypt, generated with `scripts/generate_admin_bootstrap_password_hashes.py --user support-user`). As for every seed, a missing or malformed hash stops startup; an existing persisted profile is never overwritten. The password lives only in the operator's `.env` as a hash and is never tracked. |
| S3 | **Knowledge review.** Every AI Assistant review endpoint (queue, edit, decision, retire, fix-start, draft, close, records, reindex, stats) and `/assistant/knowledge/me` `can_review` require `KNOWLEDGE_REVIEW` instead of `POLICY_APPROVE`; the cross-team reviewer is a team-less `SUPPORT` caller instead of a team-less Director. Directors keep `POLICY_APPROVE` for policy proposals only and no longer review knowledge. Single-reviewer mode (D-083) still lets the one Support user publish their own entry with confirmation; retirement still needs a second, different reviewer, so it is unavailable with one Support account. HR guidance proposals (`POLICY_MUTATE`) are unchanged. |
| S4 | **Redaction read.** Writing a fix redacts it against the request's case, loaded with the reviewer's own session. `KNOWLEDGE_CASE_READ` admits a team-less holder to exactly two GET routes, `/api/clm/zero-touch/cases/{case_id}` and `/api/onboarding/cases/{case_id}/documents` (route access `CASE_READ`), for any case. It grants no portfolio listing, no other case route (those answer as absent, 404), no mutation and no evidence-decision authority; the frontend shows Support no case pages. Support's purpose is limited to the case details logged with a feedback ticket: it reviews those on the review page or asks the AI Assistant about that case, and never needs the whole case page. The backend does not itself limit these two reads to ticket cases (tickets live in the AI Assistant service); that is owner-accepted for the POC and pending sponsor confirmation. |
| S5 | **Frontend.** Knowledge review is the **Knowledge Review** tab (`/knowledge-review`, gated on `KNOWLEDGE_REVIEW`, Support's landing page) rendered as a page; the AI Assistant panel no longer opens it. Support's **Policy** tab is the existing read-only rendering for `POLICY_VIEW` holders (no propose, reset or decide controls). |

Not decided here: sponsor reviewer policy (Q-014); a second Support reviewer for retirement;
any change to knowledge content rules, redaction or the exact-line guard.

## D-105 - Conversation feedback, chat history, Support's review list and Support's chat without a case (OWNER-DIRECTED, local POC scope)

Status: owner-directed on 2026-10-30. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`.
Not sponsor policy (Q-013 retention/privacy and Q-014 reviewer policy stay open). Supersedes the
per-answer "Yes, helpful" / "Not helpful" panel controls of D-083 and D-097 Y4's "What this
answer used" summary; the exact-line rule (D-074, ADR-012 section C), redaction, the content-hash
decision and maker-checker are unchanged. Support is the single reviewer (D-083 single-reviewer
mode, still PROPOSED).

| # | Decision |
| --- | --- |
| C1 | **Conversations.** Each answer record joins a server-side conversation (`conversations`, store schema v6; `answer_records.conversation_id`). A question joins the conversation the browser names only when it is that user's open conversation on that case; otherwise a new one starts. |
| C2 | **End conversation.** The panel's End conversation form asks "Was this issue resolved?" first. Yes offers very satisfied, satisfied or neutral and an optional "Additional comments"; No offers neutral, unsatisfied or very unsatisfied and a required "How should it be improved?". The service enforces the same rules (422 otherwise), redacts the comment against the case and rates a conversation once. |
| C3 | **Priority and review.** Neutral is low, unsatisfied medium, very unsatisfied high priority; satisfied or better has none. Ending adds one feedback row in the same write: an open enhancement request when there is a priority, otherwise a request closed as needing no review. Every record of the conversation is linked to it, so the D-084 retention applies (30 days after the request is resolved or closed; an unrated conversation's records go after 7 days, and the conversation with them). |
| C4 | **Support's list.** Knowledge Review lists rated conversations, 10 a page, filtered by resolved, satisfaction and review status (not reviewed, saved as draft, fix awaiting publish, fixed, closed, no review needed), ordered high, medium, low, then no priority. A conversation with a priority shows Review (Edit draft once a draft is saved); others show View. "Waiting for review" and "Enhancement requests" are removed; other pending knowledge (HR's guidance proposals) is listed in a collapsed section only when there is any. |
| C5 | **Drafts and publishing.** Support may save the fix as a draft (redacted, kept on the conversation until the fix is saved or the request closed) or save and publish it after confirming the final text, as the single reviewer. Fixes change only the knowledge the assistant may cite, never a case or backend logic. |
| C6 | **History.** A user lists their own conversations (newest first, 10 a page) and opens one read-only: questions and the answers as shown, redacted (client details appear as placeholders). Views are logged. |
| C7 | **Support's chat without a case.** `POST /assistant/support/chat` (KNOWLEDGE_REVIEW) answers from the approved knowledge and the active policy catalogue read with Support's session, under the exact-line rule: allowed lines are checked knowledge sentences, one line per policy rule and a fixed "couldn't find" line. No case data is read. The local model only: the D-094/D-095 remote model is never called for it (its gates admit verified synthetic case prompts only) and the answer is then built from the allowed lines; the messages use the same chat format, so another approved model needs no format change. |
| C8 | **Removed.** The per-answer helpful buttons and "What this answer used" summary are no longer shown. The `POST /assistant/cases/{id}/feedback` endpoint is kept for compatibility but no longer used by the panel. Existing ratings and enhancement requests are kept, not deleted, and are not listed. |
| C9 | **History continues the chat.** Opening a past chat from History loads it into the same chat window. An open conversation continues as itself; a rated one cannot take more answers, so new questions start a new conversation with the past exchange as context. A chat about another case opens that case's page. |
| C10 | **Review page (point 5).** "Why the AI answered this way" becomes **Information / rules used**, every part folded until opened (how it was answered, lines shown, lines the guard left out, knowledge found, all rules offered, the case at the time). **Ask the AI Assistant about this case** opens the usual AI Assistant panel on the conversation's case, with the user's question offered first (no chat card on the page); it returns to the rules chat when Support leaves the page: it reads the case with Support's read-only access, and the service keeps no answer record or conversation for callers without `CASE_ACCESS`. |
| C11 | **Edit how the AI should respond.** Support either edits an existing rule (chosen from the approved guidance, its current text loaded to edit) or adds a new rule, with optional "When it applies" blocker codes, fields and stages; fixes from a review are always guidance (no worked examples, no follow-up questions). **Try with this change** (`POST /assistant/knowledge/conversations/{id}/try`) answers the user's question with the unsaved change offered as if approved, first and in place of the version it would replace, under the same sentence checks and exact-line rule; it saves, publishes and records nothing and uses the local model only. Support changes only the knowledge the assistant may cite: no case, case data, CLM backend or answer logic. |
| C12 | **Who sees the AI Assistant.** The panel is shown only to users with `CASE_ACCESS` (case users) or `KNOWLEDGE_REVIEW` (Support). HR has neither and gets no AI Assistant; the service already answers HR with nothing (no case to load, no rules chat). |

Model qualification: `main.py` and `answer_records.py` are qualification basis files, so any
existing GPT-OSS 120B qualification is no longer current and that model cannot be activated
until it is qualified again (paid). The local model is unaffected.

## D-106 - AI Assistant HR session keys for Anthropic and OpenRouter, and qualification progress (OWNER-APPROVED, synthetic-only FYP development)

Status: the owner approved this credential-policy amendment on 2026-10-30 ("Owner Approval -
Credential Policy and Claude Activation"). It amends the key-source order of the D-095 addendum
and the "no HR key entry" rule of D-099/D-100 for the future only; the entries for those
decisions are not rewritten. Built on branch `feat/assistant-session-credentials`, integrated onto
main `1c6ec4f` as `feat/assistant-session-credentials-int`. D-103 and D-105 are PR #138's. Not sponsor policy. Authority:
`USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`.

| # | Decision |
| --- | --- |
| K1 | **Order.** For each provider (OpenRouter for GPT-OSS; Anthropic for Claude Balanced and Fast, sharing one key) the key is: (1) a key an HR administrator entered for their own signed-in session, (2) the process environment, (3) the git-ignored `apps/assistant/.env`. The first source holding a value decides; a malformed value never falls through (unchanged). |
| K2 | **Session binding.** An HR key is held in the AI Assistant's memory only, with the cookie of the HR session that entered it. Before each model call and each qualification launch, the service asks the CLM backend `/api/auth/me` with that HR session's own cookie (never an RM's). The key stays usable only while the same user is signed in and holds `MODEL_CONFIG_MANAGE`. Read-only views, the free connection test and the paid-start estimate reuse a check for at most 10 seconds. A 401, a changed user or a lost capability drops the key. It is also dropped by Clear, by a restart and, at the latest, 8 hours after entry (the backend's fixed `SESSION_TTL`; `/api/auth/me` never extends a session). If the backend cannot answer, the key is held back (`unverified`) and nothing falls through to a server key. |
| K3 | **Identity on every change.** A key change rebuilds the model and re-runs its full preflight before the next call (existing behaviour). An HR key, and any server key used after an HR key ends, must therefore pass the provider's existing identity checks before any message is sent: Anthropic, the attested workspace in the reply header and the Claude ledger's profile and reconciliation; OpenRouter, the usage reconciliation against its ledger and the key's own limit. Otherwise the call is refused. The ledgers, caps, daily allowances, call limits and HR spending controls apply unchanged whatever the source. Nothing switches model automatically. |
| K4 | **Protection.** The key is never returned, logged, audited, written to SQLite or browser storage, or put in a telemetry or audit payload. Audit rows name only the action and provider (`CREDENTIAL_SET` / `CREDENTIAL_CLEARED`, `profile_id` `openrouter` or `anthropic`). Entry is HR only, Origin-checked, strict JSON and rate limited (unchanged). Anthropic accepts inference keys only (`sk-ant-api…` / `sk-ant-usr-…`); an Admin key is refused. |
| K5 | **Qualification process.** The service sends only the qualified provider's HR key (none for a local model) to `scripts/qualify_model.py` as one JSON object on its standard input. Keys are never put on the command line or in the child's environment (the earlier `qualification_environment` is removed). A held-back key refuses the start (`CREDENTIAL_SESSION_UNVERIFIED`), so a run never falls back to a server key in its place. The supervisor ends the run, recorded as `error` / `CREDENTIAL_REVOKED`, once the key it handed over is cleared or replaced, dropped with its session, or its session cannot be checked. Recovery is to enter a key or rely on the server key, then Test connection. |
| P1 | **Qualification progress.** Qualifications & Recovery (and the overview) show the running run with a spinner, a progress bar from the server's `done_turns`/`total_turns` (indeterminate when no total is reported), the provider, the server-reported stage (running, or cancel requested), the start time and the active model. When the followed run ends, the page shows passed, failed, cancelled, interrupted or stopped, with the turn counts, the server's recovery text and the technical results. Polling stays the existing 3 seconds; no ETA is shown. Cancellation, reservations and qualification state are unchanged. |
| Q1 | **Qualification basis.** `key_sources.py`, `anthropic_runtime.py`, `remote_test.py` and the generated `synthetic_boundary.json` changed: the basis moves from main's `2c9d72cf0ae4…` (after PR #138) to `7e386b8a69e1…`. Every earlier qualification becomes out of date. Claude Balanced needs one new technical qualification on the merged code (2 billed calls, at most US$0.192 reserved, authorised by the owner on 2026-10-30) before it can be activated. The boundary's code vocabulary gains `amended`, `clears`, `inherits`, `releases`, `revocation` and `unchecked`, and loses `command` and `inherited` (docstring wording; system messages only). |

Residual risks (owner-accepted with the approval): an OpenRouter key's account is inferred from
usage reconciliation, not read; a revoked session is detected at the next use or view, not
pushed; a run ended for revocation is killed as a cancelled run is (then recorded as
`CREDENTIAL_REVOKED`), so an open paid call stays in the ledger until it settles or an operator
reconciles it.

## D-107 - AI Assistant Claude set up by HR in AI Models, without decision or attestation settings (OWNER-APPROVED, local development deployment only)

Status: the owner approved this on 2026-10-30 ("Simplify Claude Integration - Remove
Environment Authorization Friction"). It amends, for Claude only and for the future, how
D-099 Option B is switched on (the `AI_ASSISTANT_ANTHROPIC_DECISION` and
`AI_ASSISTANT_ANTHROPIC_OWNER_ATTESTS` settings and the D-091, D-092, D-094 and D-095 decision
names it required). The entries for those decisions are not rewritten, and GPT-OSS is
unchanged. Built on branch `feat/assistant-claude-hr-enablement` from main `7e5653d`. Not
sponsor policy. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`.

| # | Decision |
| --- | --- |
| E1 | **HR enablement record.** AI Models stores one `anthropic_enablement` row in the model state database. It holds enabled or disabled, the Anthropic workspace id, the workspace's monthly limit (at most US$30.00) and the four owner confirmations (`dedicated_workspace`, `workspace_limit_set`, `inference_key_only`, `key_revoked_at_fyp_end`). Nothing in it is secret. Changes are HR only (`MODEL_CONFIG_MANAGE`, re-checked inside the change lock), need the page Origin and are rate limited. They are compare-and-set on the row's revision (`ENABLEMENT_CONFLICT`) and written with their audit row in one transaction (`ANTHROPIC_ENABLED` / `ANTHROPIC_DISABLED`). The table's CHECKs repeat the bounds. Disabling a Claude configured on the server (D-099) stores the record switched off, with the server's workspace and limit, so it decides from then on. |
| E2 | **Setup flow.** On Providers → Anthropic, HR first chooses the key (a D-106 session key, else a server key). HR then reads the workspace that key reports: a free `GET /v1/models/claude-sonnet-5-5`, with no inference and no case data, made only on the approved local deployment (`ANTHROPIC_WORKSPACE_READ` is audited). Next HR confirms the four statements and the owner's monthly limit, and enables Claude for verified synthetic cases. Enabling accepts only the workspace read with the key now in use, within the hour (`WORKSPACE_NOT_READ`). After that come Test connection, the Balanced technical qualification and activation, unchanged. Claude Fast is listed and configurable; it needs its own qualification before activation. |
| E3 | **What decides readiness.** While the row exists it replaces the decision and attestation settings: disabled means `ANTHROPIC_NOT_ENABLED` whatever the environment says, and an unreadable row or database means `ANTHROPIC_ENABLEMENT_UNREADABLE` (fail closed). The D-091, D-092 and D-094 decision names are replaced by the runtime checks they stood for: the model switched on, a literal loopback CLM backend and only local browser origins (`NOT_DEVELOPMENT_ENVIRONMENT` elsewhere, including for the workspace read). No new environment setting is added. With no row, the earlier environment configuration (D-099) applies unchanged. |
| E4 | **Workspace and billing identity.** Every preflight and every reply must name the enabled workspace (unchanged check, now on HR's workspace). Once set up, the workspace cannot be changed from the page (`WORKSPACE_CHANGE_REFUSED`: a different workspace needs an operator and its own ledger). It must also equal a workspace set on the server, if any: at enabling, and at every readiness check afterwards (`WORKSPACE_MISMATCH`, so Claude is off until they agree). Unchanged: the separate Anthropic ledger, the daily, lifetime and call limits (D-102), the ledger cap at most the lower of US$30.00 and the confirmed workspace limit, in-band reply verification, the breaker, reconciliation (24 hours for paid runs, 7 days for chat) and the no-switch rule. |
| E5 | **Owner-confirmed, not verified.** The workspace's monthly limit and the four statements cannot be read through an inference key. They are owner confirmations recorded by HR, and the page says the limit "is not read from Anthropic, and the app cannot verify it". The workspace id is the one the key itself reported. |
| E6 | **Data access.** Claude's D-095 mode under HR enablement is the approved local deployment itself, so it no longer needs the D-095 decision name. Every D-095 check still applies: provenance, document SHA-256 digests, approved case access, identifier screening and the single-use admission ticket, re-checked in the adapter. Data Access & Privacy shows two things for each external provider: whether the provider is enabled, and what it may receive ("Verified synthetic cases only", fixed). It no longer shows a disabled checkbox. Real customer data on an external provider still needs a separately approved data-governance decision. |
| E7 | **Views.** Claude's key and spending views no longer need the D-094 decision name in the overview. The overview carries `anthropic_setup` (source, readiness, record, the last workspace read, the confirmations required). |
| Q1 | **Qualification basis.** `anthropic_runtime.py`, `data_access.py` and the generated `synthetic_boundary.json` changed. The basis moves from main's `7e386b8a69e1…` to `80448c6d7d61…` on `7e5653d`; integrated onto main `c6b37f2` (PR #142, D-101, which changed `synthetic_eligibility.json` and the boundary) it moves from `5adfe7ec2c58…` to `5dc26b296026…`, so Claude Balanced needs one new technical qualification on the merged code, within the owner's existing authorisation (2 billed calls, at most US$0.192 reserved). The boundary's code vocabulary gains `disable`, `monthly`, `ro` and `setup` (system messages only). |

Residual risks (owner-accepted with the approval): the monthly limit and the dedicated-workspace
statement remain owner confirmations, as they were as environment attestations; the paid
qualification's question list (`AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_QUESTIONS` and
`..._COUNT`) is still a server setting; ledger initialisation and reconciliation remain operator
steps (`scripts/budget_ledger.py --anthropic`).

## D-108 - AI Assistant runtime data root and test isolation from live stores (OWNER-APPROVED, B0 Assignment 1)

Status: the owner approved B0 Assignment 1 on 2026-10-31 (persistent storage configuration,
automatic test isolation, CLI path handling and documentation). Built on branch
`feat/b0-storage-isolation` from main `59a4609`. Moving the owner's live stores (Assignment 2)
is a separate, separately authorised operator step and is not part of this entry. Not sponsor
policy. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`.

| # | Decision |
| --- | --- |
| S1 | **Optional data root.** `AI_ASSISTANT_DATA_DIR` (empty by default). Empty keeps every store where it was (`apps/assistant/data`, package-relative). Set, it must be an existing absolute directory; relative store paths (`budget_ledger_path`, `anthropic_ledger_path`, `model_admin_db_path`, `model_profiles_file`, `knowledge_data_dir`) resolve under it with the defaults' leading `data/` dropped, and absolute per-store paths are kept. Resolved once, in `config.py`, so every existing resolver receives an absolute path. |
| S2 | **Fail closed.** A relative, missing or non-directory root, or a store path that is drive- or root-relative or would leave the root, refuses the settings (the service does not start). Nothing is created and nothing falls back to the package-relative stores. |
| S3 | **Suggested roots (documentation only).** Windows `%LOCALAPPDATA%\DataDividendsCLM\assistant`, macOS `~/Library/Application Support/DataDividendsCLM/assistant`, containers a mounted volume. No username or machine path is in tracked code. |
| S4 | **Operator CLI.** `scripts/budget_ledger.py` honours the process environment's data root and a new `--data-dir` (`--ledger` wins), never reads `.env`, prints the ledger path it uses and refuses an invalid root (`DATA_DIR_INVALID`) or other invalid settings, naming the fields but never their values (`SETTINGS_INVALID`). Ledger rules (no creation on `status`, init only where none exists, reconcile, reset) are unchanged. |
| S5 | **Test isolation.** `tests/conftest.py` runs before any test module imports `ai_assistant.main`: it removes the developer's store settings and Anthropic key variable, puts the knowledge store, the Claude ledger and the model state database in a session temporary folder, and refuses (PermissionError) to open any SQLite or Chroma file under `apps/assistant/data`, the suggested data roots or a store the developer's environment named, subject to the limits listed in `docs/integration/AI_MODEL_CONFIGURATION.md` section 7.1. |

Unchanged: the qualification basis (no basis file changes; `config.py`, the CLI and tests are
outside it, and store paths are not fingerprint inputs), model selection and activation,
credentials and key order, ledgers and spending controls, D-095, guardrails, RBAC and the CLM
backend.

## D-109 - AI Assistant storage cutover closure: persistent data root in use, operator tools and recovery limits (OWNER-APPROVED, B0 Assignments 2 and 3)

Status: on 2026-10-31 the owner approved and verified the cutover of the owner's local AI
Assistant stores to a persistent data root (B0 Assignment 2) and approved this closure and
hardening (Assignment 3). This is a local operator change recorded for traceability. Not
sponsor policy. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Sanitised
evidence: `docs/evidence/B0_STORAGE_CUTOVER_2026-10-31.md`.

| # | Decision |
| --- | --- |
| C1 | **Authoritative stores.** The owner's assistant runs with `AI_ASSISTANT_DATA_DIR` set to a per-user root outside the repository (D-108 S3), protected so only the owner, SYSTEM and Administrators can read or write it. Layout: `models/model_admin.sqlite3` (model state and audit), `models/profiles.json`, `budget/anthropic_fyp_ledger.sqlite3` (the active Claude ledger), `budget/ledger.sqlite3` (the GPT-OSS ledger), `knowledge/` (knowledge SQLite and Chroma), and `archive/` (the earlier Claude ledger, kept read-only by convention and reachable by no default). Every store setting is relative and set explicitly by the launcher, so `.env` or an inherited absolute value cannot redirect it. |
| C2 | **Launcher.** The live launcher is an owner-only file outside the repository (it holds machine paths and the workspace pin, so it is never tracked). `apps/assistant/scripts/storage/start_assistant.example.ps1` is the tracked, parameterised template: the workspace pin, repository root and data root are parameters, it refuses code without the data root, checks that every store already exists and resolves under the root (`check_data_root.py`), and keeps the model, spending, key-order and D-095 settings unchanged. |
| C3 | **Operator tools.** `scripts/storage/backup_stores.py` (SQLite backup API from read-only sources; nothing is published unless every copy verifies; never overwrites), `scripts/storage/store_fingerprint.py` (read-only logical fingerprint with every table counted; no key material or case text, but it does print key aliases, ledger ids and the last four characters of the workspace id, so its output stays in the owner-only evidence folder and is never pasted into tracked files) and `scripts/storage/check_data_root.py`. They were independently reviewed before the cutover; the tracked copies differ from the reviewed ones by formatting and docstrings only. |
| C4 | **Recovery is forward only.** After the cutover the new stores received ledger, audit and answer records, so starting a service on the earlier stores would undercount spend and lose audit history. The earlier stores and launchers are retained unchanged as history; returning to them needs a separately approved, data-preserving procedure. |
| C5 | **Legacy hardening (local).** The package-relative data folder in the owner's checkout no longer grants write access to sandbox accounts; the obsolete launchers are retired by a reversible rename; the worktrees that hold historical stores are locked against removal. The historical SQLite files are not modified (a read-only attribute was deferred). |
| C6 | **Recorded deviation.** During the post-cutover smoke test an HR administrator explicitly ran an unapproved Claude Fast technical requalification (2 paid calls, verified, charged to the active Claude ledger). Its records and charges are kept; it was not activated. The approved single paid case question then passed. |

Unchanged: the qualification basis, model activation and qualifications in force, credentials
and key order, ledgers, breakers and spending controls (no reset, reconcile or cap change),
D-095, guardrails, RBAC and the CLM backend. The Claude ledger still needs its scheduled
reconciliation (the 7-day freshness rule) under a separate authorisation.

## D-110 - AI Assistant Claude ledger reconciliation by HR in the AI Models Console (OWNER-APPROVED for development 2026-10-31; first live use gated on S1 to S3 and P1)

Status: the owner approved D-110 for development on 2026-10-31 (Q1 to Q11 and Q13 to Q15 as
recommended; Q12 clarified by the owner; Q4's fallback conditional). Built on branch
`feat/b1b-hr-reconciliation` from main `11d2202`. It amends D-099 C6 and C9 and D-107 E4 only in
that an HR administrator may now perform the reconciliation they describe; D-102 and D-109 are
unchanged. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence class: Local
(offline tests on disposable ledgers). Not sponsor policy; no Live, Sandbox or provider-status
claim. The full design, its four independent design reviews and the owner's decisions are in the
B1-B specification (rev 9).

| # | Decision |
| --- | --- |
| R1 | **Scope.** The Claude ledger is reconciled against the Anthropic Console's cumulative cost of the HR-enabled FYP workspace, in USD, since the workspace was created (D-099 C6, D-107 E4). The generic ledger's "key's cumulative usage" wording reads as this scope; no accounting scope changes. |
| R2 | **Authority.** HR administrators holding `MODEL_CONFIG_MANAGE` (re-checked inside the change lock, page Origin required, rate limited) may reconcile in AI Models → Spending & Limits. One approver, who types the figure again. No new capability and no backend RBAC change. |
| R3 | **Flow.** Preview (cumulative cost, the Console's refresh time or HR's viewing time, three scope confirmations), then a confirmation dialog, then the existing `BudgetLedger.reconcile(release=False)`. |
| R4 | **Consistency.** The apply commits only if the ledger is exactly the previewed state (a token over every ledger column, the calls' high-water id, open, last-close, unverified and uncovered-quarantine counts and the operator event sequence), checked inside reconcile's own write transaction by a subclass in non-basis code; afterwards, still inside it, exactly the predicted events (P+1 `reconciled`, and P+2 `breaker_opened` only when predicted) and every ledger column are checked, and the apply deadline (intent + 30 s) is checked before and after. Any difference rolls back. HR never recovers expired calls. |
| R5 | **Lock and marker.** A cross-process reconcile lock beside the ledger (per handle on Windows, `flock` elsewhere; never deleted, never created at start-up) and a durable intent marker written before the ledger step. The operator's script takes the same lock for `reconcile`, `reset-breaker`, `set-cap` and `verify` and refuses while a marker exists; only `reconcile --override-intent RUN` passes, recording the override on the marker first. CLI reconciliation stays available. |
| R6 | **Freshness.** `settle lag = (now − as_of) + margin`, margin at least the configured lag: 600 s from the Console's own refresh time; only when the Console shows no refresh time, 3600 s from HR's viewing time (Q4, with the reporting-lag risk disclosed). A reading at most 2 h old, never in the future (60 s skew), lag at most 86,400 s. |
| R7 | **Refusals.** Breaker open, an open call, an unverified closed call or a quarantined call not yet covered by a reconciliation (R10), an open or unresolved run or a marker, a falling figure, a figure that leaves the ledger more than US$0.05 ahead of the increment since the last reconciliation, missing scope confirmations, a stale or future reading, or a call closed after the reading minus the margin. An undercount above US$0.05 may be applied after a warning: it opens the breaker, and chat stays stopped until the owner reconciles again and resets it with the script. |
| R8 | **No release, reset or extension by HR.** HR cannot release an overcount, reset the breaker or extend a deadline; the 7-day chat and 24-hour paid windows renew only as a consequence of a successful reconcile. Renewal starts nothing: no paid call, no limit change, no activation (Q14: HR may afterwards raise limits within D-102 or start a paid run, each with its own confirmation). |
| R9 | **Audit and recovery (Q12 as the owner clarified it).** An intent row (insert-only, never trimmed, with its audit row) is written before the ledger step. A run is `applied` only when commit and attribution are proven (the apply returned, or resolve finds P+1 matching with the run's own intact marker and the recorded P1 attestation); `failed` only when non-commit is proven (P+1 absent, another event or amount, or a release at P+2); otherwise `unresolved` for the owner, including an overridden marker (X1). `LEDGER_BUSY` never decides a run. Resolve is an explicit audited HR action after the bound; listing and start-up write nothing. Owner close (script only) records an acknowledgement, never `applied`, and never changes the ledger. |
| R10 | **Unverified or quarantined calls block** HR reconciliation until the free preflight or the script's `verify` checks them, and a quarantine is covered by an owner reconciliation. |
| R11 | **Basis.** No qualification-basis file changes; new backend strings use the existing boundary vocabulary (`build_synthetic_boundary.py --check` passes; basis `5dc26b296026…` unchanged). |
| R12 | **Deadline fallback.** If this is not rolled out by 2026-11-05 18:00 SGT, the owner runs or authorises a CLI reconciliation before 2026-11-07 09:42:37 SGT. |
| R13 | **P1 prerequisite.** HR reconciliation is refused until the owner records with `budget_ledger.py attest-legacy-retired` that every earlier copy of the script and every earlier launcher is retired. |

Before the first live HR reconciliation (owner): S1 which figure (workspace or key) set the FYP
ledger's opening usage and its 2026-10-31 reconciliation; S2 that `key-02` is the only key ever in
the FYP workspace and whether Workbench was used; S3 the Console screen and range for "cumulative
since creation" and whether it shows a refresh time; and the P1 attestation. Residual risks
accepted with the approval: the Console figure is typed by a person; Console completeness is the
provider's claim (bounded masking, never more than the existing undercount); the X1 case needs an
owner acknowledgement; the subclass depends on `BudgetLedger._transaction` (pinned by tests, fails
closed); the scope rests on owner attestations.
## D-111 - AI Assistant answer quality: catalog lines, required action refusals and requalification (PROPOSED, needs owner approval; nothing here is implemented)

Status: drafted 2026-10-31 from the B2-0 measurement (`.ai-pipeline/reports/B2_0_MEASUREMENT.md`)
and the owner's blinded scores of 85 Claude answers (`CLAUDE_API_MODEL_BENCHMARK.md` §10).
Every change below edits a qualification-basis file (`guide.py`, `guardrails.py`,
`prompts.py`) or the paid qualification's question list, so none is made until the owner
approves the exact wording, the basis change and the paid steps. Authority:
`USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence class: Local (offline
measurement plus earlier paid answers already scored); no Live claim.

What the measurement attributes (Claude Sonnet 5.5 Fast, 17 Phase B questions, owner scores):
the two rejected answers are P06#1 (catalog gap: no approved address-change refusal) and P06#2
(model weakness: the offered UBO-completion refusal line was dropped); the 2.00 answer is P04#0
(catalog gap: no line separates human review from GoldTier submission); P01#0 omits the UEN
value (catalog gap: no allowed line carries it); P04#1 lacks handoff detail (catalog gap).
Completeness (2.24) is the weakest dimension; the six-line cap (rule 16) is a legitimate
guardrail and is not proposed for change. Retrieval in the degraded mode is at recall@3 0.96
with every off-topic question retrieving nothing, and the service adds about 82 ms around an
instant model (both measured offline): neither needs a change.

| # | Proposed change (exact; wording for owner approval) | Fixes | File (basis) |
| --- | --- | --- | --- |
| Q1 | New topic-only refusal line, offered only for a request to change the registered address while no such action is offered to the viewer: `ADDRESS_CHANGE_NOT_OFFERED = "Changing the registered address is not offered to you on this case."` (the "<action> is not offered" form the sentence checks already accept), with a routing pattern in `topic_plan` for address-change requests. | P06#1 reject | `guide.py`, `guardrails.py` (allowed_guidance), `prompts.py` (topic_plan) |
| Q2 | A registry value line for the company's UEN, offered only when the case facts hold an ACRA UEN, quoted the same way as the D-090 value lines: `f"The UEN in the ACRA ({environment}) record for this case is {uen}."` | P01#0 completeness | `guide.py`, `guardrails.py` |
| Q3 | A topic-only line for "ready for review" questions: `REVIEW_IS_NOT_SUBMISSION = "A person can review this case at any time; the app's readiness check is for GoldTier submission only."` | P04#0 2.00 | `guide.py`, `guardrails.py`, `prompts.py` |
| Q4 | A handoff detail line under the P14 topic: `SUBMISSION_CONTENT = "The GoldTier submission sends the company details reviewed in this case; GoldTier's decision is not shown in this application."` | P04#1 completeness | `guide.py`, `guardrails.py` |
| Q5 | Action refusals become service-added required lines through the existing D-090 mechanism (`with_required_lines`): when the topic is an action request the viewer is not offered (approve, mark the UBO check complete, change the address), its refusal line is always shown, whatever the model wrote. | P06#2 model weakness (dropped refusal); protects every configuration | `guardrails.py`, `main.py` (topic's required lines) |
| Q6 | The paid technical qualification's question list adds the action requests (`AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_QUESTIONS=P01#1,P02#0,P06#1,P06#2`, count 4), so Fast must show the refusals before activation. | Fast's P06#2 risk | server setting (paid: 4 calls instead of 2) |
| Q7 | Requalification and evaluation, each step approved separately: (a) after the merge the basis moves and the active Claude Fast becomes AI unavailable at the next start, so schedule it outside demos; (b) one Claude Fast qualification, at most 4 paid calls (about US$0.05); (c) optional Claude Balanced, same bound; (d) one paid re-run of the 17 Phase B questions on Fast (about US$0.19) and the owner's blinded re-scoring; (e) GPT-OSS stays unqualified unless separately decided. Envelope at most US$0.60 for (b) to (d); stop at the first failure; no retries. | measures Q1 to Q5 | none (operations) |
| Q8 | Not proposed: raising the six-line cap, history limits or retrieval weights (no measured need), and any change to G4 (held), `SELECTION_ONLY_FACTS`, the live-claim, authority and confirmation checks, D-095, D-104 or D-105. | — | — |

Acceptance after approval (targets for the re-scored 17 questions on Fast): overall at least
2.85 (from 2.75), completeness at least 2.60 (from 2.24), grounding 3.00, correctness at least
2.94, rejects at most 1 (from 2) with P06#1 and P06#2 accepted, no unsafe line, prompt under
9,250 characters, every earlier guardrail test passing. Until then these are NOT EXECUTED.

## D-112 - evidence-based POC ownership basis for every company on the official Mock lane (OWNER-APPROVED 2026-11-01, O1 to O8)

Owner approval 2026-11-01 of the O1 to O8 proposal. D-085's acceptance is extended from catalogue scenarios to any company, using one rule in code and no per-company code or configuration.

- **Calculation (O1).** When no compatible ACRA quantity produced a graph, an official Mock root register is converted at `holder current units / issuer's total current units x 100` (the existing six-decimal `quantized_unit_share`). Each link has `LOCAL_POC_ASSUMED_EQUAL_UNITS` / `LOCAL` provenance (`quantify_poc_equal_units`). The source evidence is retained unchanged. Withdrawn or ceased rows stay history and never enter the denominator. Any other status, a non-positive unit count, a duplicate holder, an ACRA denominator, a percentage scalar or a conflict means no POC link.
- **Classes (O2).** The untrusted D-080 class and currency now label root unit evidence (`share_class`). Current units of more than one class, or with no reported class, are never combined: the analysis stays in review with a precise mixed-class message. This narrows D-081's labelled pooling for the generic basis only; hybrid scenarios are unchanged.
- **Acceptance (O1, O3, O4).** The code-level declaration `EVIDENCE_POC_BASIS_V1` (recorded in `overlay_scenario_id` under the D-085 policy literal, so API and frontend types are unchanged) accepts only `EQUAL_UNIT_DENOMINATOR` and the root's official Mock officer roles as descriptive context. It requires:
  - identity binding and a supported legal form (`OTHER` and `GOVERNMENT` never qualify);
  - only POC links from the root to natural persons, each matching its recomputed share;
  - complete discovery, if run;
  - no unquantified, contradictory, conflicting, unbound, unsupported, unresolved, document-discrepant or supplemental cause;
  - review-classified candidates with calculated assumed-basis results (the inclusive 25% threshold).
  Classifications and issues are unchanged, and POC percentages are never verified UBO ownership.
- **Indirect.** A corporate holder is never accepted on the generic basis; it stays in review until its own register is resolved. Generic indirect POC discovery is NOT implemented.
- **Switch (O5).** `ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE` is one official Mock lane switch, now defaulting to `accept_eligible_poc`. It has no effect off that lane and is never configured per company.
- **Excluded (O6).** Sandbox and Live never receive an assumption-based quantity or acceptance.
- **Demo scenarios (O7).** NOT changed in this slice: the hybrid scenario declarations still apply in `hybrid_direct_overlay`.
- **Existing cases (O8).** Only new analyses are affected; operators re-run analyses for existing cases. There is no migration.
- **Unchanged.** Explicit Mock GoldTier submission confirmation, reviewer controls, the manual review receipt, provenance and audit events.
- **Remaining gap.** `_review_causes` still names the legacy Garden fixture UEN for its supplement lane.
- **Completion (owner follow-up, 2026-11-01).**
  - **Each issuer.** The same rule now runs for every issuer: at the root before discovery, and inside discovery for each corporate holder's own register. The existing Decimal path engine then gives direct, indirect and aggregated interests against the inclusive 25% threshold (for example, 80% x 50% = 40%).
  - **Corporate holders.** A corporate holder is accepted once its own register resolved and the discovery graph is complete. Every edge must be an official Mock registry link or a POC link that matches its issuer's own recomputed single-class basis.
  - **Collection completeness.** This is judged separately from totals (`ownership_collection_complete`): the shareholder operation must be `COMPLETE` and every returned row kept. The provider never asserts that its register is the issuer's complete legal register; that stays the labelled O1 assumption.
  - **Discovery outcomes.** A `PARTIAL` issuer bundle whose other operations are only `EMPTY` (a definitive answer) is judged on its evidence. Issuers whose units cannot be combined get precise discovery reasons: `ISSUER_SHARE_CLASSES_MIXED` or `ISSUER_UNITS_NOT_QUANTIFIED`.
  - **D-080 narrowed.** Ownership parties now keep the untrusted source class and currency, which O2 needs. Stored bundles without classes stay unquantified until they are refreshed (fail-closed).
  - **Garden UEN removed** from the review-cause path; the legacy supplement lane is recognised by its classification alone.
  - **Not done here (owner step).** Retiring the hybrid scenario declarations (O7), about 52 test assertions plus the demo lane. Removing the default-lane Garden fixture supplement, whose eligibility is Garden-specific.

- **Review notes (2026-11-01).**
  - **Sandbox and Live.** Keeping the class label on ownership parties applies in every environment, but it only stops units of different classes being combined. Verified paths are unchanged: provider percentages, and an authoritative denominator with one class. No POC basis or acceptance exists outside Mock (tested in `test_sandbox_and_live_keep_verified_paths_and_never_pool_classes`).
  - **Rollback.** A bundle stored with a class label fails validation under code older than D-112.
  - **Completeness.** It rests on the provider's own `COMPLETE` status, because the row-count check mirrors the bundle validator. A provider that silently truncates its collection is not detectable, and a 100% total never counts as completeness.
  - **Owner step still open (O7 and Garden supplement; O7 superseded by the entry below).** Retiring the scenario declarations breaks 82 existing tests across 4 modules (D-085/D-086/D-087/D-089), about 35 of them defect cases to re-derive against the generic rule, so it is deferred rather than weakened. The default-lane Garden fixture supplement is also unchanged.

- **O7 retired (owner approval 2026-11-01).**
  - **Catalogue.** No catalogue scenario declares POC acceptance any more (Garden direct, OPQ Garden/SIM LIM, OPQ Garden/ABC).
  - **One rule.** `eligible_poc_acceptance` ignores any scenario argument and applies the code-level evidence rule. An analysis whose discovery records an overlay scenario never qualifies, so the hybrid demonstrations stay usable as labelled evidence but are held for ownership review. The deleted helper code was the scenario-only declaration and guard logic (`_undeclared_intermediate_roles`, `_issued_capital_links_disagree` and the edge-assumption map).
  - **Role-integrity guards carried over.** The generic rule now holds the role guards the scenario path enforced:
    - every root role is the adapter's own record, with an evidence id derived from its officer id, once, with a supported status;
    - a role at another entity that is ownership-like blocks;
    - evidence ids are unique.
  - **Generic baseline.** The D-085 suite now runs on an ordinary company with no scenario (`tests/evidence_poc_fixture.py`), over the real Marketplace Mock protocol path. Its defect cases, readiness, toggling, confirmation, document-binding, persistence and schema tests are kept and re-pointed to it.
  - **Obsolete expectations** (recorded in `RETIRED_D087_EXPECTATIONS` / `RETIRED_D089_EXPECTATIONS` and `OBSOLETE_HYBRID_ONLY`), each asserted against a scenario's own acceptance that no longer exists:
    - the D-087 intermediate-role declaration and its validators and runtime guards;
    - revoking a recorded scenario acceptance;
    - tampered issued-capital links;
    - locally named or non-distributed hybrid issuer records.
    The hybrid-only defect cases are still asserted against the hybrid Garden case, which can no longer qualify. The live guards from the retired D-087 round-trip test are kept in `test_hybrid_records_round_trip_and_older_readers_still_reject_their_fields`: older schemas reject D-086 role observations and legacy intermediate counts, roles require an official entity profile, and a D-082 acceptance never carries intermediate counts.

- **Declaration plus official discovery (owner priority, 2026-11-01).**
  - **Discovery after a declaration.** A reviewed creator declaration (`MANUAL_DECLARATION_POC`) may name corporate holders with a verified UEN and no declared owners of their own. Those holders are discovered through the same official Mock lookups as any issuer. Discovery runs after every receipt check, and post-discovery validation admits only official Mock registry links, labelled equal-unit links and official Mock evidence attached by discovery. Declared links keep the declaration's own provenance.
  - **Entity-less official rows outside a scenario.** An issuer's entity-less official Mock rows (D-079) are distributed on the equal-unit basis without a scenario overlay only when every current row reports one class and currency (O2). The discovery audit then carries the same explicit evidence separation as a hybrid analysis, and is never `COMPLETE` certainty.
  - **What this gives.** With a single-class SIM LIM register, a declaration of only Garden's own owners reproduces the original graph and percentages, with each link's true source. It stays in review because SIM LIM's level rests on the equal-unit assumption, and no POC acceptance exists for a declared analysis (an owner policy decision).
  - **What it does not do.** SIM LIM's observed Mock rows mix Ordinary, Preference and Others, so they are never pooled below a declaration. OPQ -> Garden still blocks: Garden is a partnership with no official ownership register (`PROVIDER_UNSUPPORTED`). ABC's register is a scenario-only D-088 business profile (`NOT_FOUND`). Nothing is reused across onboardings.
  - **Unchanged.** Full declarations and the supplement-on lane.
  - **Changed official-only behaviour.** An ACRA-root analysis whose corporate holder has entity-less, single-class official rows now gets labelled equal-unit links for that holder, with explicit evidence separation and UNCERTAIN certainty. It is still never accepted, because the holder stays `PROVIDER_PARTIAL` and the graph is incomplete.
  - **QG remediation.**
    - Official evidence that discovery attaches below a declaration is retained on the declared analysis, so its review causes are never dropped. The declared analysis stays in review; its cause there is the units' unresolved status, because the per-issuer POC basis applies only to official-lane analyses.
    - The load path's currentness recheck now also runs after discovery under a declaration.
  - **Limitations.**
    - On the Marketplace Mock transport the relationships operation is unsupported, so a corporate holder that has an entity profile is `PROVIDER_UNSUPPORTED` and never attached. Only entity-less registers, such as SIM LIM's, combine there.
    - The schema stays 17. A schema-17 reader older than this change rejects an audit with POC records but no overlay, which is fail-closed on rollback.
- **Legal-form observation (investigation only, nothing changed).**
  - **The rule.** D-101: the registry legal forms `OTHER` and `GOVERNMENT` have no supported ownership method and raise `OWNERSHIP_METHOD_UNSUPPORTED`.
  - **Why a declaration skips it.** A declared source carries no `legal_form` (`manual_ownership_evidence.py`, `OwnershipSourceResult` without it), so the check never runs and a declared `OTHER` company can reach `ANALYZED` and readiness. GoldTier confirmation is still required.
  - **Options for the owner:**
    - (a) keep it: the declaration is the reviewer's attestation;
    - (b) carry the case's registry legal form into the declared analysis and keep the issue blocking;
    - (c) carry it as a visible, non-blocking review note.

- **Garden cutover (owner decision, 2026-11-01).**
  - **The setting.** `garden_supplement_enabled` now actually controls the legacy flattened Garden fixture: an explicit opt-in, default off. It is off outside the official Marketplace Mock lane and off in the hybrid lane.
  - **Garden's happy path.** The reviewed creator declaration of the full D-076 register (`MANUAL_DECLARATION_POC`), bound to the labelled synthetic client document `garden-d076-ownership-declaration-client.pdf`. The document's content is not automatically verified against the declaration.
  - **Legacy flows that opt in, labelled:** the Garden protocol fixture flows, the hybrid legacy-lane test, and the existing Garden E2E server lanes (`garden-partnership`, the Garden protocol fixture, `garden-existing-customer`, and the sponsor fixture).
  - **Operator note.** A retained `GARDEN_SUPPLEMENT_ENABLED=true` in an operator `.env` now turns the fixture on; it is inert in the hybrid lane.
  - **Correction.** The earlier "Unchanged: the supplement-on lane" line is superseded: the supplement is now off unless opted in.
  - **Not done.** The browser E2E specs were not migrated to the declaration flow, nor executed (no Docker daemon or frontend `node_modules` in this environment).

- **Clarification (PR #149 review note, 2026-11-03; records existing behaviour, nothing changed).**
  - **A declared corporate holder with no UEN and no owners of its own.** When official discovery is composed, it visits the holder, makes no registry call (no verified UEN to look up) and records `UNVERIFIED_UEN`. That branch is unresolved, so the analysis also reports `CORPORATE_OWNERSHIP_UNRESOLVED` beside `INCOMPLETE_LEGAL_ENTITY`, and the case stays in ownership review (`409 ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED`). Without discovery the same declaration reports `INCOMPLETE_LEGAL_ENTITY` only. Both block; neither accepts the holder.
  - **Tests.** `test_final_review_editing_real_mongo.py` asserts the discovery record and both codes; `test_am18_ownership_checkpoint.py` asserts that no discovery ran there. The earlier test comment saying the holder was looked up in the Mock registry was inaccurate and is corrected.

## D-113 - Marketplace Mock partnerships: registry partners from current partner officers (candidate, amends D-101)

Status: candidate. Owner approval in chat 2026-11-02 to build M1 to M4; Shane to confirm here
(he reviews at the PR). Drafted after a Local test of the synthetic XYZ ACCOUNTING documents
(`T19PF1111A`, ACRA API Marketplace Mock sample record). Amends D-101's out-of-scope line for the
Marketplace Mock lane, for `BUSINESS_PARTNERSHIP` only. Authority:
`USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence class: `OBSERVED_MOCK_INTEROPERABILITY`
(read-only Mock GETs through the backend's own connector, no case written). Not Live, not sponsor
policy, not legal UBO policy (Q-004); Q-012 stays open.

**Observed (Mock, 2026-11-02).** The case fails at the Registry stage, before any document is
used: entity profile COMPLETE (`PARTNERSHIP`), officers FAILED, ownership parties and
relationships NOT_ATTEMPTED; bundle FAILED, case FAILED, blocker `REGISTRY_FAILED`, event code
`REGISTRY_OPERATION_MALFORMED_RESPONSE`. Cause: LILY's position
`PARTNER UNDER SECTION 18(3)(C) OF THE ACCOUNTANTS ACT` fails the officer role pattern
(`^[A-Za-z0-9][A-Za-z0-9 _.-]*$`), and one bad row fails the whole officers operation. With that
row simulated as `PARTNER` (scratch only), the bundle is PARTIAL (`REGISTRY_EXPECTED_DATA_MISSING`,
shareholder lookups UNSUPPORTED for a non-company), the case continues to VALIDATED, but
`registry_partner_names()` returns no partners: it reads only `ownership_parties`, never officers.
So none of the D-101 agreement checks run.

| Officer (Mock) | Position | Status | Withdrawal date | Registry partner under D-113 |
| --- | --- | --- | --- | --- |
| TAN WEI LING | Partner | Active | none | Yes |
| LILY | PARTNER UNDER SECTION 18(3)(C) OF THE ACCOUNTANTS ACT | Active | none | Yes |
| RAIN JORDON | PUBLIC ACCOUNTANT EMPLOYEE | Active | none | No: not a partner position |
| ALLIE | Partner | Withdrawn | 2019-12-31 | No: withdrawn |

The synthetic agreement lists exactly TAN WEI LING 60% and LILY 40% (`Partner Share:` lines,
extracted cleanly); the onboarding form matches the registry identity.

| # | Change (smallest; candidate, Shane to confirm) | File |
| --- | --- | --- |
| M1 | **Partner positions, Marketplace Mock connector only.** Before validation, an officer position that equals, ignoring case and surrounding spaces, one entry of a closed list (`PARTNER`; `PARTNER UNDER SECTION 18(3)(C) OF THE ACCOUNTANTS ACT`) is stored as role `PARTNER`. Every other position is kept and validated exactly as today, so an unlisted position with parentheses still fails the operation. The shared role pattern (`SourceCodeText`) is not widened, and the shared `BizfileMockOfficersDecoder` and the dormant BizFile lane are unchanged. | `connectors/acra_api_marketplace_mock.py` |
| M2 | **Active means no withdrawal date.** In the same mapping, a listed partner row whose source `status` is present and is not `Active` but has no `withdrawalDate` is rejected as malformed (fail closed). Non-partner rows keep today's handling. So for this lane "no cessation date" reliably means Active, with no new stored field and no snapshot schema change. | `connectors/acra_api_marketplace_mock.py` |
| M3 | **Registry partners from officers.** `registry_partner_names()` keeps the D-101 seed path unchanged (PARTNER `ownership_parties`). Only when there are none, the legal form is `BUSINESS_PARTNERSHIP`, there are no relationships, and the bundle's `OWNERSHIP_PARTIES` operation is `UNSUPPORTED` (only the Marketplace company-only dispatch sets this) and the officer has Mock provenance, it returns officers with role `PARTNER` (ignoring case, so an earlier cached `Partner` row still counts) and no cessation date. LLP and LP stay out of scope (D-101). | `services/partnership_agreement.py` |
| M4 | **Unchanged.** Every D-101 cross-check (current reviewed agreement at the frozen confidence threshold, registry and agreement partners equal, no duplicates, shares > 0, Decimal total exactly 100, declaration equal to the agreement), RM confirmation, maker-checker, the 25% UBO threshold and the "from partnership agreement, RM-confirmed" labels. An agreement naming ALLIE or RAIN JORDON blocks with `PARTNERSHIP_EXTRA_PARTNER_IN_AGREEMENT`. | — |

M1 and M3 ship together or not at all: M1 alone would let a Mock partnership pass Registry with
no registry partners, and readiness skips every D-101 check when the partner list is empty.

Result (Local, real Mock GETs plus the API tests): Registry PARTIAL and VALIDATED; registry
partners TAN WEI LING and LILY; with the reviewed agreement and the RM's confirmed declaration,
UBOs TAN WEI LING (60%) and LILY (40%) and no `OWNERSHIP_REVIEW_REQUIRED`. Any mismatch keeps
the case blocked in review.

Checked, no change needed: the `hybrid_direct_overlay` scenarios are whitelisted by root UEN
(Garden and OPQ) and do not include `T19PF1111A`. Garden (`11111999A`, `BUSINESS_PARTNERSHIP` on
this lane) has only `Owner` officers, so M3 gives it no registry partners and its flows are
unchanged.

Relation to D-112 (#149, merged first; this entry was renumbered from D-112 to D-113): D-112's
equal-unit POC basis and acceptance are for companies with an official register; a Mock
partnership has none (`PROVIDER_UNSUPPORTED`), so D-113 does not use it. A partnership's shares
still come only from the RM-confirmed agreement declaration under the D-101 checks. Re-run on
the merged code (`ae5946b` plus this branch): the D-113, D-101, D-112 and hybrid suites pass,
and the real Mock run with both XYZ documents gives the same result as above.

Tests (`tests/test_marketplace_mock_partnerships.py`, new; no existing test changed): the four
Mock officer rows give exactly TAN WEI LING and LILY; an unlisted position with brackets still
fails the officers operation; an inconsistent status row fails; an agreement naming ALLIE or
RAIN JORDON fails, at service and API level; Garden-style `Owner` officers give no partners;
officers never stand in when the shareholder lookup ran, or for a company; the XYZ case reaches
RM-confirmed shares on the Mock lane through the API. The D-101 seed (Gamma) tests are unchanged
and pass.

Synthetic boundary: main's `synthetic_boundary.json` is already stale before this change
(`--check` fails on `origin/main`: 14 words added, 4 removed). D-113 adds `accountants` and
`position` to `code_vocabulary` (from the exact position list). The file is not regenerated
here: it is a qualification-basis file (D-107 Q1), so regenerating it is Shane's decision.

For Shane to confirm:
1. Marketplace Mock `BUSINESS_PARTNERSHIP` cases in D-101's scope (M1 to M4).
2. The exact partner-position list. The section 18(3)(c) wording comes from the Mock sample only;
   whether Live ACRA uses the same text is part of Q-012.
3. "Active" as no withdrawal date plus the M2 rejection (built), rather than storing the source
   `status` on the officer record (would need a case snapshot schema version).
4. When to regenerate the synthetic boundary (main's existing drift plus the two words above).

## D-114 - Government cases never call ACRA: the UEN's entity type picks the register (candidate, Shane to confirm)

Status: candidate. Owner approval in chat 2026-11-02 to build; Shane to confirm here (he reviews
at the PR). Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Not sponsor policy,
not legal policy, not Live. D-101's Government rules are unchanged. Numbered D-114 because D-113
(Marketplace Mock partnerships) is on its own branch. An earlier draft of this entry let the RM
choose an "Entity type"; it never reached main and is replaced by routing on the UEN itself.

**Problem.** A Government UEN avoided ACRA only when its local seed existed. Without the seed,
or with the registry cache off, acquisition fell through to the ACRA provider
(`registry_acquisition.py` after the seed branch; directly from `onboarding.py` without a
coordinator). The RM's own correction verification (`_verify_registry_correction`) also called
the provider.

**Source for the UEN codes** (provisional, not sponsor-confirmed): "Annex 1 - Information on
Singapore's Unique Entity Number (UEN) system" (PQ table: GA and GB issued by the Smart Nation and
Digital Government Office; LL, LP, FC and PF by ACRA). The code lists live in one place,
`app/domain/uen_route.py`.

| # | Decision |
| --- | --- |
| E1 | **The UEN picks the route** (`route_uen`, rule `UEN-ROUTE-1`; the RM types only UEN, name and country, as before). Format A (8 digits + letter) and Format B (9 digits + letter): ACRA, unchanged. Format C `[TSR]yy` + PQ + 4 digits + letter with PQ `LL`, `LP`, `FC`, `PF`: ACRA, unchanged (`T19PF1111A` still goes to the Marketplace Mock). PQ `GA` (organs of state, ministries, departments) or `GB` (statutory boards): the government register only, never the ACRA provider. Any other PQ (for example GS schools, DP/CP embassies and consulates, NR international organisations, RF, SS societies, CC charities, TU trade unions, MC management corporations): new blocker `UEN_ENTITY_TYPE_UNSUPPORTED`, no registry call, guidance "This UEN belongs to an entity type this POC doesn't onboard (<type>). Check the UEN." Foreign government bodies stay out of scope (D-101). A UEN failing `is_eligible_singapore_uen` is unchanged. The route never decides Company vs Partnership: ACRA's legal form and the D-101 compatibility table still do. |
| E2 | **Government register only.** `RegistryAcquisitionCoordinator.read_government_register` reads only the approved local synthetic dataset (`LOCAL_SYNTHETIC_UAT_V1`) and takes no provider, so it cannot call ACRA. A GA/GB UEN uses it at creation, after a correction and when verifying a correction. A missing, expired, unusable or non-GOVERNMENT record, or no registry cache, stops the case with `GOVERNMENT_IDENTITY_NOT_FOUND` ("No current government register record was found for this UEN. Check the UEN against the authority's letter."). The PQ code only says what the UEN claims to be; the register record is still required. |
| E3 | **Safety check on the ACRA route.** An ACRA-route UEN that has a GOVERNMENT record in the register stops with `ENTITY_CATEGORY_MISMATCH` before any ACRA call. With the current seeds this cannot happen (Demo Parks is GB); it guards against misfiled register data. |
| E4 | **Correction.** The RM corrects the UEN through the existing identity correction (rules `BPD-GOVERNMENT-IDENTITY-1` for the two register codes and `BPD-UEN-ENTITY-TYPE-1` for unsupported types, both `CORRECT_INITIAL_IDENTITY` with a Search recheck). The corrected UEN is routed again by E1; when the route changes, the case records it with that correction as the timeline event `UEN_ROUTE_CHANGED` (for example "Route changed from ACRA to government register (UEN type GB)."). There is no category input: a request carrying `entity_category` is rejected (422, `extra="forbid"`). |
| E5 | **Unchanged (D-101).** The Government KYC label, the legal-form compatibility table, `GOVERNMENT_STATUS_REQUIRED` and the RM's version-checked status confirmation, 0 UBO candidates, labels and the GoldTier registration value. |
| E6 | **Persistence.** Case snapshot schema 18 adds `OnboardingCase.uen_route` (route, format, PQ code, entity type, description, rule version), set by the system from the UEN and never from a request. It is the audit record of how the case was routed, kept even though it can be recomputed, so a later change to the code lists never rewrites history. It is omitted from `model_dump` while unset, so fingerprints of existing cases are unchanged; the Mongo document stores every declared field, as before. A strict schema-17 reader (`DurableCaseSnapshotV17`) and the store reject `uen_route` in schema 1 to 17 envelopes, even null; a schema-17 case reads with no recorded route and is not rewritten. Older code rejects schema 18 (rollback is fail-closed). |
| E7 | **Display.** The case page's Registry verification section shows the backend's stored description, for example "Entity type from UEN: Government body (statutory board, code GB) · checked against the government register, not ACRA". The browser never works it out. |
| E8 | **Demo Parks renumbered.** `T99FY0105G` used a made-up code (FY) and would now be unsupported. It is `T99GB0105G` (a parks authority is a statutory board; year 2099 keeps it fictional) in the seed, `demo-parks-government-status.pdf` (regenerated; new SHA-256 in the fixture README), the UAT guide and the project state. |

Scope (QG F1): E1 to E3 govern the case's own identity (creation, correction and its
verification). Corporate shareholders reached by recursive ownership discovery still use the
existing read-only Mock lookups (`acquire_subsidiary_registry_evidence` and the shareholder and
business-profile readers), which fail closed; routing those by UEN is a follow-up for Shane.
When a UEN correction is not followed by a registry re-read, the recorded route still
describes the corrected UEN (QG F2).

Follow-ups (not done here): the shared `is_eligible_singapore_uen` regex rejects a Format C UEN
whose PQ "Q" is a digit (for example `T99G10105G`); flagging a contradiction between the UEN
format and ACRA's legal form was considered and deferred by the owner.

Tests: `tests/test_uen_route.py` (every row of the routing table),
`tests/test_government_no_acra.py` (GB with the record completes with zero ACRA calls; GB without
the record and with the cache off; an unsupported code; a misfiled government record under an
ACRA UEN; Alpha and Gamma unchanged; corrections from ACRA to GB and back, visible and without
ACRA; refused corrections to a GB UEN without a record or an unsupported UEN; `entity_category`
rejected; the coordinator read), `tests/test_uen_route_persistence.py` (schema 18 round trip,
strict schema-17 reads, upgrade without rewrite, stable dumps) and `src/pages/UenRoute.test.tsx`.

Synthetic manifests: the D-094 boundary vocabulary is already stale on main and is not
regenerated here. `synthetic_eligibility.json` lists the Demo Parks PDF by SHA-256 and is a
qualification-basis file, so its regeneration is a separate commit for Shane to accept or drop.

## D-115 - AI Assistant copilot answers (PROPOSED, default off) and case memory lifecycle (OWNER-DIRECTED 2026-11-03)

Status: proposed on 2026-11-03 from the owner's assignment "Unified Post-Merge, HR Recovery &
Intelligent AI Assistant Development", which directs a free-form, onboarding-focused assistant
but does not approve removing established safeguards. Built on branch
`feat/hr-rectification-assistant-copilot` from main `c233ecd`; nothing is merged, published or
switched on. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence class:
Local (offline tests with scripted models; no model run, no paid call). It would amend ADR-012
section C (exact lines) for copilot mode only; D-111 stays PROPOSED and unimplemented. M1 and M2 implement the assignment's own direction ("Leaving Case A: clear active
Case A context and conversational memory"), so they apply in both answer modes; A1 to A4, C1 to C4, R1, Q1
Q2, C5 to C7 and X1 need the owner's decision. Refined on 2026-11-03 after PRs #153 and #154 merged (C1 to C4,
Q2, E1; owner assignment "PR #155 AI Copilot Finalisation").

| # | Proposal |
| --- | --- |
| A1 | **Setting.** `AI_ASSISTANT_ANSWER_MODE`: `exact_lines` (default, unchanged) or `copilot`. Copilot mode is used only with an unrestricted local model; an external model (GPT-OSS, Claude) or a model the D-104 policy restricts keeps exact lines and its D-094/D-095 gates unchanged. Real customer data never reaches an external provider through this change. |
| A2 | **Layers.** Scope (`copilot.in_domain`: an unrelated question gets a fixed redirection and no model call), access (the CLM backend with the user's own session, unchanged), retrieval (case facts and approved knowledge, unchanged), reasoning (the model under `copilot.RULES`: guidelines, not sentences), checking (`CopilotGuard`: every sentence goes through `guardrails._check`, the same grounding, action, authority, Live and document-value checks approved knowledge passes, plus a new check that removes any claim by the assistant that it did or will change something), and the read-only reply (`READ_ONLY_LINE`, added by the service first whenever a user asks the assistant itself to change something). |
| A3 | **What stays.** Values (3+ digit numbers, decimals, identifiers), contacts, labels and section names must appear in the case facts. In a case chat, copilot also requires every percentage and every name (a run of capitalised words, or a company name ending in a recognised suffix in any capitalisation) to appear in the facts, unless the sentence is plainly an illustration ("for example", "if a ..."). Percentages are compared as numbers with facts whose key names a percentage (`percent`, `threshold`, `effective_interest`, `ownership_interest`, `stake`); share counts never ground one. Company names are compared word for word after setting aside capitals, punctuation, spacing and the spelling of a recognised suffix (C2); identifiers still decide identity. A UBO conclusion is kept only when presented as provisional or as what the records or the application show (C3). Actions the viewer is not offered, verification or approval claims (including a UBO or ownership result presented as verified, confirmed or approved), Live claims and document values presented as confirmed are removed; citations must name a tag that was given. Removed sentences are counted and the user is told. Known limits (refinement QG 4.3, 5.1): title-case person names, single capitalised words, short counts, company names written in lower case and percentages written in words or other forms ("45pct", "forty-five percent", "3/5") are not grounded; the checks do not judge relations between grounded values (a model can still misstate who holds what along a path, seen in E1); some correctly negated sentences are over-removed, for example "Neither source automatically wins" (inherited, fail closed). |
| A4 | **General chat.** `POST /assistant/general/chat/stream` for `CASE_ACCESS` or `KNOWLEDGE_REVIEW` holders, copilot mode only: no case is read, approved knowledge and general reasoning only, the local model only, and no answer record is written. |
| M1 | **Chat contexts.** `POST /assistant/contexts` opens a context for one user and one case (the backend checks access with the user's session) or the general chat; `POST /assistant/contexts/{id}/close` drops it (always 204). Turns live in process memory only, bounded (`AI_ASSISTANT_CONTEXT_MAX_TURNS`, default 16), and expire after `AI_ASSISTANT_CONTEXT_IDLE_SECONDS` (default 1800) or `AI_ASSISTANT_CONTEXT_MAX_SECONDS` (default 28800, the backend session lifetime); a restart drops every context. A question naming a context uses only its server-held turns: the browser's history text is ignored, and a context of another user or another case is refused (`CONTEXT_UNKNOWN`, `CONTEXT_SCOPE_MISMATCH`). An answer finishing after its context closed is never added to any context. This lifecycle applies in both answer modes. |
| M2 | **Panel.** The context opens on the first question; leaving the case (another case, no case), unmounting (sign-out or a user change: the panel is keyed by user) and `pagehide` close it with a keep-alive request, and the panel forgets the thread: coming back to a case starts afresh (this replaces "coming back to a case shows its chat again"). A late reply for a chat that was left is ignored. History (D-105) still reopens a past chat only on the user's explicit action. Consequence (QG F2): a chat left without End conversation can no longer be rated from the case page; reopening it from History restores its conversation so it can still be ended and rated. Its redacted records stay under D-105 retention. |
| R1 | **Retention conflict (owner decision).** D-105 answer records (the question and the shown answer, redacted) and conversations are kept for Support's review under the D-084 retention (7 days unrated, 30 days after review). Deleting them when a case is left would break D-105's End conversation, History and Support review, so this change does not delete them. Options: (a) keep D-105 retention as is (recommended for the POC); (b) stop recording answers in copilot mode unless the user ends the conversation with a rating; (c) shorten unrated retention. |
| Q1 | **Qualification basis.** `main.py` changed and `copilot.py`, `case_contexts.py`, `claims.py` and `evidence.py` join `BASIS_FILES`; the regenerated `synthetic_boundary.json` adds 16 everyday system-message (`code_vocabulary`) words against main (C4), with the conversation and prompt vocabularies unchanged. The basis moves from main's `1cb45edc5939…` (main `2c10408`, after PRs #153 and #154) to `77e50313a62c…`. Once merged and restarted, every earlier qualification is out of date and a stored Claude activation becomes AI unavailable (D-098 R6) until a separately approved paid requalification; schedule outside demos. Q2 proposes how future copilot-only changes could avoid this. |
| C1 | **Context-sensitive scope (refinement, 2026-11-03).** With a case open or a chat ongoing, a short question made only of words that bring no topic of their own ("Status?", "Why?", "Which one?", "How did you calculate that?", "What should I do next?") and a question naming something on its own ("What about NG MEI LING?") are in scope; the model answers from the case and the chat or asks one clarifying question (RULES 11). Any onboarding word still places a question in scope; "holds", "held" and "holder" count only with a case open. Known limits: with a case open some unrelated short questions ("What time is it?", "What about Taylor Swift?") reach the model, which redirects them under RULES 12; and a party named in another form than "what about X" ("Who is LIM CHOON HUAT?") is redirected unless the question has an onboarding word. A question naming an everyday topic (weather, flights, food, sport, crypto prices, programming and similar) with no onboarding word is redirected without a model call, in a case chat too; without a case or a chat, a contextless question is redirected. Fixes re-QG 3 R1 and R2. |
| C2 | **Company names (refinement).** `copilot.canonical_name` compares names word for word after setting aside capitals, punctuation, spacing and the spelling of a recognised suffix (Pte/Private, Ltd/Limited, Bhd/Berhad, Inc/Incorporated, Corp/Corporation): "Example Pte Ltd" matches "EXAMPLE PTE. LTD.". No fuzzy matching: "ACME HOLDING PTE LTD" never matches "ACME HOLDINGS PTE LTD", an invented company name (now also in title case) is removed, and an identifier in the sentence must still be in the facts. Sentences are no longer split after "Pte.", "Co.", "No.", "e.g." and similar abbreviations, which cut "X PTE. LTD." in two. |
| C3 | **UBO explanations (refinement).** In copilot mode only (a local model), the case chat also reads the application's ownership analysis through the backend's case-scoped `GET /api/onboarding/cases/{case_id}/ownership` with the user's own session (`clm_client.load_ownership`; the backend decides access; an error or a missing analysis gives "not available", never a failure). `copilot.ownership_facts` passes each person's direct, indirect and aggregated interest, each path's links and the application's own calculation text, the threshold and its inclusive rule, the result and classification, and the open issues, unchanged and bounded (12 people, 6 paths, 8 links, 10 issues), as a separate OWNERSHIP FACTS message; nothing is recalculated. The model may explain direct, indirect (80% x 50% = 40%) and aggregated (15% + 10% = 25%) interests and threshold results; every figure it states must be one of the application's. RULES 4 replaces the blanket UBO prohibition: a UBO conclusion is kept when hedged or, in its own clause, presented as provisional or as what the records or the application show ("appears to be", "provisional UBO candidate", "based on the available ownership records"); an unqualified conclusion, in either word order ("LIM is definitively the UBO", "The UBO is LIM") is still removed (`ubo_determination`); a statement naming a person the application found below the threshold as a UBO is removed (`ubo_contradicts_calculation`) when the full name comes before the claim ("TAN WEI LING appears to be a UBO") or is listed after it with up to five words before is/are/include ("The UBOs, per the calculation, are LIM CHOON HUAT and TAN WEI LING"); known gaps (re-QG 2): a longer subject, a hedged list verb ("The UBOs ... appear to be LIM and TAN"), "not just ... but ... too" and a surname alone are not caught, and "The UBO result for X is MET" or "The UBO section ... is Ownership & UBO" is left out (fail closed); and a UBO or ownership result presented as verified, confirmed, approved, certified or settled ("Compliance confirmed that ...", "... and this is final") is removed (`authority_claim`). A negation the shared checks do not recognise ("No, the UBO has not been officially verified.") is still left out, fail closed: rewriting it was tried and withdrawn because it also kept claims that are now true ("had not been verified until today", re-QG F1). Known limits (fail closed): a conditional "final only after review" and a contrast list ("The UBOs are LIM and NG, unlike TAN") are left out unless hedged. External models never read the analysis. |
| C4 | **External system-message vocabulary narrowed (refinement).** `scripts/build_synthetic_boundary.py` no longer takes words from `copilot.py` (`LOCAL_ONLY_MODULES`): its text reaches only a local model, since copilot mode never runs with an external model. The regenerated boundary drops 72 `code_vocabulary` words (including passport, telephone, nominee, sanction and screening, QG F7); against main it now gains only 16 everyday words from `case_contexts.py` and `main.py` (arrives, bit, contexts, copilot, disk, drops, exchange, idle, lands, late, remembered, reopened, restricts, tab, tells, unrestricted). Conversation and prompt vocabularies and every D-094, D-095 and D-104 gate are unchanged. This narrows what an external model's system message may contain and widens nothing. |
| Q2 | **Separating the basis by provider (proposal, not implemented).** Qualification runs exact-line scenarios only, and copilot code runs only with a local model, so a change to `copilot.py` cannot change what a Claude or GPT-OSS qualification measured. The smallest change would compute the external models' basis without `copilot.py` (keeping it in the local models' basis), with a test that the external path never calls copilot code. It would not help this PR: `main.py` and `case_contexts.py` change the external path too (server-held history in both modes), so Claude needs requalification on merge regardless. It would spare future copilot-only changes a paid requalification. Changing the basis calculation needs the owner's approval and an independent review; it is not part of this change. |
| E1 | **Local-model evaluation (refinement, 2026-11-03).** Evidence class: Local. `tests/test_copilot_model_eval.py` (opt-in, never in CI) asks 16 synthetic-case and general questions through the real routes with the project's default local model `ministral-3:8b` (Ollama 0.40.13, temperature 0.2, 600 answer tokens, RTX 4080 Laptop GPU), in copilot mode before and after this refinement and in exact-line mode. Results, scores, examples and latency are in `.ai-pipeline/reports/D115_COPILOT_REFINEMENT_REPORT.md`. No paid call, no external model, synthetic data only. |
| C5 | **Structured claim checks (refinement 2, 2026-11-04).** `claims.py` (model-independent) checks free-form answers against the application's ownership graph built from the OWNERSHIP FACTS, not word presence: a stated holding ("X holds N% of Y", "Y is N% owned by X", "Y is owned N% by X", "N% of Y is held by X", "X's N% stake (in Z) belongs to Y", "X's stake belongs to Y" (no figure, the two names side by side: the holding must exist), "X holds N% through Y", and a second clause with its subject left out) must be a link or an interest in that direction with that percentage, and a path named with "via"/"through" must run through that party (`unsupported_relationship`); a person said to be a UBO candidate or to meet the threshold, or said to be below it or not to be one, must agree with the application's result whatever the sentence order, including lists, "X, like Y, meets ...", "Neither X nor Y is ..." and "Unlike X, Y is ..." (`ubo_contradicts_calculation`; for a result the application could not determine only a positive or a threshold claim contradicts it). Parties are matched by exact canonical name (possessive "'s" set aside), the name without its suffix, a unique distinctive first word of a company, or "the company". These checks only remove sentences. Known limits (independent re-QG probes: 24 of 82 unsafe sentences still kept, against 42 of 82 on the PR head; across both reviews' probes every sentence kept now that the PR head removed is correct; a third review's new probes found wrong possessive forms with no figure kept, which the head removed only because it could not read a possessive name: "KESTREL's stake in GARDEN belongs to DANIEL", "... stake ultimately belongs to ..."; and "Neither X nor Y is a candidate because they fall below the threshold" is misread, as on the head): holdings with the object first ("Of KESTREL, AISHA holds 40%"), percentages in parentheses after names, a surname alone, pronouns, figures in words, lower-case company names, and claims the shared checks never flag ("The UBO, verified by compliance, remains blocked ..."). |
| C6 | **Negations and conditions (refinement 2; changes what the copilot keeps).** A sentence the shared checks remove for an authority or Live claim is kept only when the whole sentence is one of a few fixed forms with a fixed subject from a closed list (the UBO, the ownership result, the case, the document, ...) and nothing else: "The UBO has not been officially verified (yet).", "No UBO status is verified yet.", "Neither source automatically wins.", "It does not mean she is officially verified (or approved).", "It is not a final KYC or regulatory approval.", "The case remains blocked until ownership is confirmed.", "The check has not run in a live environment." Nothing is split, rewritten or judged in part. A first design that accepted negated clauses inside longer sentences failed independent review (a current claim in front of "... until X is confirmed" or after it, "which compliance did", was kept) and was withdrawn; every such sentence is now removed and tested. Correct compound or past-tense negations ("Neither source automatically wins—this is a case-specific decision.", "The UBO had not been verified.") stay left out (fail closed). The shared guardrails and exact-line mode are unchanged. |
| C7 | **Evidence package and reasoning rules (refinement 2).** `evidence.py` gives the copilot the same compact case view every model gets (`prompts.facts_for_model`), regrouped by source with a legend: registry (the ACRA identity record, not Live), documents (values read from uploads, may be misread), conflicts, workflow, blockers with the actions this user is offered, still needed, approved explanations. The ownership facts state each holding with its direction ("X holds N% of Y"). RULES (14, shorter) ask the model to answer first, then explain the evidence, copy holdings exactly, classify by the application's result, suggest only offered actions, resolve short follow-ups from the chat and state a caveat once. External and restricted models keep exact lines and their own prompt (`prompts.py`, unchanged); they never receive the evidence package, the ownership facts or these rules. |
| X1 | **External synthetic-only copilot evaluation (proposal, not implemented).** `claims.py` and `evidence.py` would work unchanged for Claude or GPT-OSS answers, but copilot mode with an external model would change D-094/D-095/D-104 behaviour (free text instead of exact lines) and needs its own decision, qualification and a paid evaluation. The proposal, data plan and cost ceiling are in `.ai-pipeline/reports/D115_REASONING_ARCHITECTURE_REPORT.md`; nothing is enabled. |
| E2 | **Refinement 2 evaluation (2026-11-04).** Evidence class: Local. A held-out synthetic ownership case (two-path boundary holder, same percentage for two parties, below-threshold and undetermined persons, a loop) with 13 unseen questions, run with `ministral-3:8b` on the PR head before this change, after it, and in exact-line mode, plus a labelled sentence corpus for the guard; results and independent blind scores are in `.ai-pipeline/reports/D115_REASONING_ARCHITECTURE_REPORT.md`. |
| X2 | **Conversational contract for external models (implemented, OFF until the owner approves; owner direction "PRIORITY CORRECTION — Deliver Conversational AI", 2026-11-04).** Supersedes A1's "local model only" and X1 for external models, and supersedes the held answer-side extraction branch. `answer_mode` gains `auto` (the new default): exact lines until `config.CONVERSATIONAL_DECISION` (a reviewed constant, `None` here) is set, then conversational answers for every model; `exact_lines` is the rollback. External models answer in their own words only when that decision is recorded (`config.external_conversational`): `AI_ASSISTANT_ANSWER_MODE=copilot` alone keeps them on exact lines, as before (QG10 H2), and no HR field or switch turns it on. An external model (Claude Sonnet 5.5 Balanced/Fast, GPT-OSS 120B Balanced/Fast) answers in its own words only in D-095 development mode: `remote_gate` runs the unchanged per-call eligibility check (synthetic company, Mock ACRA, document digests of tracked fixture files, values, viewer, text screen) on the copilot prompt and issues its single-use ticket; the adapters still refuse a call without it. An external model never receives the ownership analysis (`OWNERSHIP FACTS`: names and holdings the D-095 check does not ground; QG10 H1); it answers from the checked case facts, so UBO detail stays with a local model or exact lines. A refused external call records `remote_boundary` (or `model_disabled`) as in exact lines (QG10 M4). A D-094-only external model, an ineligible case and the general chat (local model only) keep their current behaviour. `CopilotCheck.usable` (from the answer-side extraction) also applies to the local copilot: when more sentences are removed than kept, the case-data answer is shown. Unrelated questions are refused before any call (`copilot.in_domain`, plus arithmetic-only questions such as "What is 1+1?"). The Claude adapter is unchanged. Read-only policy, RBAC, case isolation, approvals, spending caps, credentials and audit are unchanged. Evidence class: Local (mock Anthropic and OpenRouter APIs, synthetic fixtures, disposable stores; no paid call). |
| X3 | **Qualification identity (with X2).** Once conversational answers are on, an external model's catalogue fingerprint becomes `fingerprint({configuration, "answers": "free text"})`, so an exact-line qualification never counts for conversational answers; `exact_lines` brings the old identity and its qualification back. A conversational qualification asks the same two approved questions as the chat will: the harness passes the service's answer mode and D-095 decision, the harness model reports itself as the external model it wraps, and the eval case's document is the tracked synthetic Garden fixture file (`variants.verified_fixture_documents`; the recorded documents' bytes are not in the repository, so D-095 rightly refuses them). The document keeps the recorded document's extracted values (all synthetic), so the harness exercises the conversational path; it is not itself a test of eligibility, which `test_synthetic_eligibility.py` covers (QG10 M5). Harness only; no runtime gate changes. The basis moves from main's `17a3172e1607…` to `49bc0541fa40…`; the regenerated `synthetic_boundary.json` changes two `code_vocabulary` words each way (adds aiassistantsettings, conversational; drops restricts, unrestricted). |
| C8 | **Status claims in conditions (QG9 findings, fixed once).** A resolved, ready or completed claim made inside a condition or time clause of its own ("Once the blockers are resolved, ...", "when the case is ready for GoldTier") is no longer removed; "the next (previous, following) stage is X" is not read as the current stage; "nothing" negates a claim ("Nothing has been submitted to GoldTier yet."). Claims outside such a clause are still removed. After QG10: the condition word must start its own clause that is followed by the main clause, or stand just before the claim after the main clause ("Before lunch the blockers were all resolved." and "If you ask me the case is ready for GoldTier." are claims), and a negation inside a longer claim counts only next to its verb ("the blockers that could not be cleared earlier are now resolved" is a claim). |
| X4 | **Owner approval for PR publication (2026-11-05).** The owner approved the bounded X2 conversational contract for verified synthetic cases only ("D-115 X2 — Owner Approval for PR Publication"), for Claude Sonnet 5.5 Balanced/Fast and GPT-OSS 120B Balanced/Fast, on these conditions: D-094/D-095/D-104 synthetic-only restrictions and per-call verification stay; RBAC, read-only controls, case isolation, spending limits, key handling and audit stay; no real customer information reaches an external model; the ownership analysis is not sent to an external model without a separate approval; exact lines stay as the rollback; no HR setup steps are added and the D-118 guided setup is kept; exact-line qualifications never authorise conversational mode; no paid call and no activation. Conversational mode stays default-off: `CONVERSATIONAL_DECISION` remains `None` in this change, and turning it on, the paid requalification of each configuration and activation each need further owner approval. Blocking before merge (owner): the two GoldTier-readiness phrasings from the delta review, now corrected narrowly (C9), with a focused independent delta review. |
| C9 | **Two readiness phrasings (owner-blocking, delta QG notes).** A condition exempts a claim only when it introduces the claim's own clause (at most three words before it), so "When you open the case you will see it is ready for GoldTier, so submit it." is a claim; a past-tense claim (was, were, had been) after a condition other than if/unless says it happened, and `_READY` now also matches "was/were ready", so "The case moved on once it was ready for GoldTier." is a claim. "Once the blockers have been resolved, ..." and "If it were ready for GoldTier, ..." stay hypothetical. Regression tests in `tests/test_answer_side_checks.py`. |

Owner decisions needed: approve or reject A1 to A4 and C1 to C4 (and whether copilot mode may ever extend to an
external model, which would need its own data-governance decision and requalification); R1 (a),
(b) or (c); the basis move and the requalification spend; Q2 (separate the basis by provider or not); C5 to C7 (refinement 2); X1 (an external synthetic-only copilot evaluation, with its spend). Until approved, `answer_mode` stays
`exact_lines` and the general chat is not offered. X2/X3/C8: the owner's security and data-boundary approval of X2 (recorded by
setting `CONVERSATIONAL_DECISION` in a reviewed change), then a paid requalification of each external configuration to be used.

## D-116 - HR recovery centre in the AI Model Console (PROJECT-DEFINED, within D-098, D-102, D-106 and D-110)

Status: built on 2026-11-03 on branch `feat/hr-rectification-assistant-copilot` from main
`c233ecd`. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence class: Local
(disposable ledgers and state databases). No new HR capability, no backend RBAC change and no
change to any ledger, limit, credential or reconciliation rule.

| # | Decision |
| --- | --- |
| H1 | **Diagnosis.** `GET /assistant/admin/models/recovery` (HR, `MODEL_CONFIG_MANAGE`) lists every current problem from the views the console already serves (`recovery.diagnose`, read-only): reconciliation windows, breaker, open, unverified and quarantined calls, reconciliation runs and markers, the P1 prerequisite, daily and lifetime limits, keys (HR session key missing, invalid, unverified or ending; server key unavailable), qualification out of date or failed, model unavailable, configuration changed and a failed connection test. Each problem names its cause, evidence (codes, counts, amounts, times; never a key) and the action that fixes it, with who may act and what to check afterwards. |
| H2 | **Actions.** HR actions are the existing guarded endpoints: reconcile (D-110), resolve a finished run, enter or replace a key (D-106), Test connection (free; it also verifies unverified calls in-band), edit the daily or lifetime limit (D-102, D-098), qualify, activate or roll back. Test connection and Resolve run start from the recovery centre after a confirmation, which then checks again whether the problem is still reported; the others open their own section's existing preview and confirmation. An action whose prerequisites are not met is shown with the problems that block it (for example reconciliation while the breaker is open). |
| H3 | **Owner requests.** For problems only the owner or an operator may fix (breaker reset, quarantined or stuck calls, unresolved runs, an intent marker, the P1 attestation, the first reconciliation, an unreadable ledger, a server key, the US$30.00 ceiling), HR records an owner recovery request: the server's own evidence at the time and an optional note (at most 280 characters; key-like text refused). One open request per problem, at most 20 open; Origin required, rate limited, the capability re-checked inside the change lock, written with its audit row (`RECOVERY_REQUESTED`) in one transaction. A request can be withdrawn, or marked resolved only once the server no longer reports its problem (`RECOVERY_PROBLEM_STILL_PRESENT` otherwise). A request changes nothing else. |
| H4 | **Separate deadlines.** The recovery centre shows the Claude chat window (7 days), the paid-operation window (24 hours), each HR session key's end, the daily reset and each configuration's qualification state apart; renewing one never extends another. |
| H5 | **Unchanged (D-110 R8).** HR still cannot reset the breaker, release an overcount, extend a deadline or settle an unknown charge. The 2026-11-07 09:42:37 SGT chat deadline renews only through a reconciliation; R12's fallback (owner CLI reconciliation if HR reconciliation is not rolled out by 2026-11-05 18:00 SGT) still applies. |
| H6 | **Qualification basis (correction, 2026-11-03).** `recovery.py` and `model_admin*.py` are not basis files, but the D-094 boundary generator collects every assistant string constant into `code_vocabulary` (system messages only). D-116's strings add 31 such words (for example deadlines, renews, requalify, centre; `secrets` from "without keys or secrets"); no conversation or prompt vocabulary, value or document changes. The regenerated `synthetic_boundary.json` moves the basis from PR #153's `bcd6afc2b454…` to `1cb45edc5939…`, so an external-model qualification is out of date after this merges and the service restarts. |

## D-117 - Optional GoldTier enrichment: Group Company Name in GoldTier Details & Status (candidate, nothing implemented)

Status: candidate. The owner approved the UX direction (Option B) and the revised plan in principle on
2026-11-03 and assigned this decision and contract-correction record (PR0) only. Authority for the
design: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Sponsor statements quoted below are
`SPONSOR_CONFIRMED` only to the extent written. Not Live, not provider-verified, not production policy.
Numbered D-117 because D-115 and D-116 are reserved on `feat/hr-rectification-assistant-copilot`.
Nothing in this entry is implemented: no code, model, schema, API, mapping, configuration or
provider call changes with it.

**Sponsor source.** The owner-supplied private sponsor response document
`DC&Data_Dividends_Queries_Responses.docx`, SHA-256
`74b6c7cdc22da4d2fb128ecc06cb0976fc99f830eb588c36aa9b8178364ba72e`. Its document properties
record creation 2026-10-15T10:07Z and last modification 2026-10-22T02:02Z (revision 2); no
separate publication or delivery date is established. It stays outside the repository; only the
bounded facts below are recorded. Its EDS statements are context only: EDS is out of scope (a
sponsor-described in-design enhancement of XPI with no current endpoints or field specifications).
A second round of sponsor answers was relayed by the owner on 2026-11-03 (O1 to O4 below); several
of them restate answers already recorded in D-068.

**Sponsor facts recorded (enrichment scope only).**

| # | Sponsor statement | Effect on this project |
| --- | --- | --- |
| S1 | `groupCompanyName` is free text. If the supplied name does not exist in GoldTier, GoldTier creates a new Group Company Name (GCN) record; if it matches an existing one, GoldTier associates the customer with it. | The create-or-associate consequence is known and must be shown to the RM. Open: the matching rule (exact, case or whitespace handling, scope) is not stated. |
| S2 | The current XPI Amend supports only `rmUserLogin`, `anzsic`, `groupCompanyName` and External System / External System Key details. Contact, RM email, address and similar fields belong to the in-design EDS enhancement. | Amend field categories are confirmed. Open: our `XpiAmendCustomerRequest` has no `rmUserLogin` and no External System/Key fields, and the supplied contract artefacts give no request alias, type or format for them. |
| S3 | Amend requires a valid GoldTier ID and a GoldTier-generated Policy ID. `Singapore` in sample payloads is not a Policy ID. Existing customers should obtain the Policy ID from prior onboarding records, customer search results or other approved GoldTier retrieval mechanisms. | The current Amend shape (`goldTierId` + `policy=Singapore`, `mappers/goldtier_xpi.py` `build_amend_request`) does not conform. Open: no current case retains a Policy ID (S3 Policy create returned none), and the XPI Search response field carrying a Policy ID is not established. |
| S4 | Expected flow: Search; if a match exists, Amend; otherwise Shell, then Policy, then Amend for additional information not captured during Shell creation. | The sponsor-described route for additional fields is a post-Policy Amend. The sponsor did not answer whether Shell may carry `groupCompanyName`; Shell carriage rests only on the supplied collection example. |
| S5 | Product type, account entity type, contact and RM email specifications belong to the EDS enhancement and are not finalized. | No non-empty `productType` / `accountEntityType` vocabulary exists; current empty-string serialization is unchanged. |
| S6 | Unprocessed additional fields are listed in the response; persisted values can be checked with the Search API. The verification mechanism is also stated as not finalized. | Search-based readback is a candidate check, not an established acceptance proof. |

**Owner-relayed sponsor answers (2026-11-03).**

| # | Answer | Effect on this project |
| --- | --- | --- |
| O1 | `Singapore` is a Policy selection value, not the generated Policy ID required for Amend; Amend needs both the GoldTier ID and a genuine GoldTier-generated Policy ID. | Confirms S3. See the D-056 note below. |
| O2 | Group Company Name and ANZSIC are optional Amend fields. GoldTier supports Singapore SSIC, but the current Amend does not support SSIC updates. | No SSIC value is sent through Amend and no SSIC-to-ANZSIC conversion is made. |
| O3 | Restated from D-068: GTAPICONNECTUSER is the API service user; Requested/Active policies may be amended subject to workflow validation; a Validation Failed amendment does not update customer records; GoldTier has no API-level idempotency or retry; the External System Key is not a unique GoldTier customer identifier. | Existing ledger, no-replay and correlation-only key handling are unchanged. |
| O4 | Contact and address enhancements and other EDS capabilities are outside current XPI scope; non-empty `productType` / `accountEntityType` vocabularies are not established for the current XPI implementation. | Current empty-string serialization of `accountEntityType` and `productType` is unchanged. |

None of these answers is to be asked of the sponsor again. ANZSIC: no code list was supplied and
none is inferred. RM identity: no mapping from a local user to a GoldTier login was supplied (Q-016).

**D-056 note.** D-056 `policy=Singapore` remains valid for Create Customer Policy. For Amend it is
superseded by S3/O1: Amend requires a genuine GoldTier-generated Policy ID. No such identifier is
retained today and none may be generated, guessed or derived locally; no retrieval mechanism is
invented. Until a genuine Policy ID can be bound, XPI Amend stays disabled.

**Design decisions (candidate; each later PR needs its own review).**

| # | Decision |
| --- | --- |
| E1 | **Placement (Option B).** A collapsed "Additional GoldTier details (optional)" disclosure inside the existing GoldTier Details & Status stage, directly below Target classification. No new stage, pipeline node, rail entry, exception, intervention or readiness blocker. |
| E2 | **v1 scope.** Group Company Name is the only editable field. ANZSIC, product type, account entity type and RM login stay out of the editable scope until their values or identity semantics are established. External system, external key, RM login status, `accountEntityType` and `productType` (both keep their current empty values) may appear read-only. No dropdown values are introduced. |
| E3 | **Entry.** The RM may leave it empty, type a value, or review an explicit document suggestion and accept, correct or reject it. Saving requires an explicit acknowledgement that GoldTier will associate an existing GCN on a match or create a new one, and that the matching rule is not yet confirmed. The name is never inferred from ownership, shareholders or unrelated text. |
| E4 | **Document suggestions.** Only an explicit labelled line (for example `Group Company Name:`) captured during normal document processing, in the same page pass as the existing classification labels. No OCR re-run; documents processed before the feature show no suggestion. Provenance: document, version, event count, page, `PAGE_n_LINE_m` reference, method, quality and evidence score (not a probability). The exact label set is fixed in the implementing PR and tested on synthetic fixtures only. |
| E5 | **Currency.** Accepting a suggestion requires current evidence (document not superseded or deleted, unchanged event count, exact value); otherwise `DOCUMENT_REVIEW_STALE`. After replacement or deletion a saved document-sourced value is retained, marked "evidence no longer current, re-confirm", is ineligible for transmission and is not a blocker. |
| E6 | **Statuses.** Collected locally, Prepared for XPI, Eligible for submission, Transmitted, Provider-confirmed. A later status is never shown before it is reached; provider-confirmed requires an exact readback of the same value. |
| E7 | **Transmission, default disabled.** Any later mapping is Shell-only for new customers and must not set an Amend field, so it cannot trigger Customer Amend. Eligibility is a composition-root allowlist that is empty by default (no HR-editable policy, no environment flag); opening it is a separately reviewed `EXTERNAL_PROVIDER` change. Given S4, opening it also needs provider qualification of Shell carriage (a verified contract detail or separately authorized Sandbox evidence); Shell acceptance is not asserted before then. The exact GCN matching algorithm is provider behaviour shown to the RM as a consequence; it is not needed to build the feature. No Sandbox write is authorized by this decision. |
| E8 | **Existing customers.** The value is retained in the case and shown as not transmitted until Amend is qualified (S3 Policy ID retrieval and binding, request schema, provider acceptance). Enrichment never turns `AMEND_NOT_REQUIRED` into an Amend and no Policy ID is invented. |
| E9 | **Review & Send.** A populated value appears in an "Optional GoldTier details" card with source, provenance and status; the card is omitted when empty. A value appears in "What will be sent" only when eligible; otherwise it is listed as saved in the case and not transmitted. |
| E10 | **Persistence plan.** (D-120 took schema 19; this plan moves to the next free version when implemented, and its "schema-18 readers" become readers of the version before it.) One case snapshot schema bump (19) declares both the optional case field and the optional document observation field, so the later suggestion work needs no second revision. Strict schema-18 readers reject either key even when null or empty; schema-18 records read without rewrite. Both fields are omitted from `model_dump` while unset. The Mongo document stores every declared field (`_persistence_value`), so newly saved documents gain the null or empty keys and `schema_version: 19`. |
| E11 | **Unchanged onboarding when unused.** For a case with no enrichment, business fingerprints and review digests stay byte-identical: case dumps, document evidence fingerprints, `_target_review_digest` (enrichment added only when present), `GoldTierSubmissionInput` and its submission/idempotency fingerprints (enrichment populated only when eligible), XPI and Mock payloads, and `requires_amend`. Golden tests captured from the base revision prove this in the implementing PRs, including a direct check of the Mongo encoding rather than relying on `exclude_if`. |

**Verified documentation inconsistencies.**
- `GOLDTIER_XPI_MAPPING_MATRIX.md` described the Shell and Policy `customerExternalSystemKey`
  source as the registration number. Current XPI code uses `FYP-<case id hex>` in Sandbox mode and
  none otherwise (`services/onboarding.py` `build_submission_input`); only the Mock mapper uses the
  UEN with `ACRA`. Corrected there.
- The XPI preview labels the Amend industry field `ANZSIC` while the request alias is `anzsic`
  (`mappers/goldtier_xpi.py` preview). Recorded only; a code fix belongs to a later PR.
- `GOLDTIER_EXISTING_CUSTOMER_RESOLUTION.md`, `GOLDTIER_CURRENT_CONTRACT_AND_SCREENING_RECONCILIATION.md`
  (fresh synthetic customer plan, Amend row) and the matrix Amend `policy` row treat `Singapore`
  as the Amend policy value. The reconciliation plan's Amend row is corrected in place to require a
  genuine GoldTier-generated Policy ID; the other two carry dated D-117 notes and their historical
  rows are not rewritten. Create Customer Policy keeps `policy=Singapore` everywhere.

**Dependency classification.** None of these is a blocker for the optional frontend feature, and
none is a new sponsor question.

| Item | Class | Treatment |
| --- | --- | --- |
| GCN free text, associate-or-create; Amend field categories; Policy ID required for Amend; `Singapore` is a selection value; SSIC not updatable through Amend; O3 restatements; empty `accountEntityType` / `productType` | `CONFIRMED_BY_SPONSOR` | Available for implementation decisions now. |
| Group Company Name capture, manual correction, explicit-label document suggestion, acknowledgement, persistence (schema 19), Review & Send card; Shell mapping behind the empty allowlist; XPI Amend fail-closed Policy-ID safeguard | `IMPLEMENTATION_READY_LOCAL` | Built and tested with local and Mock behaviour; no further sponsor reply needed. |
| Shell acceptance of `groupCompanyName`; GCN matching outcome and readback evidence; Policy-ID retrieval and Amend request binding; Amend request schema for `rmUserLogin` and External System / Key; RM-to-`rmUserLogin` identity mapping; ANZSIC values; non-empty `accountEntityType` / `productType` | `PROVIDER_QUALIFICATION_PENDING` | Transmission stays disabled and current behaviour is preserved until a verified API contract detail, approved readback evidence or a separately authorized Sandbox operation exists. No speculative enum, identifier, request field or identity mapping. |

**Planned implementation sequence (each a separate assignment, independent QG and owner merge).**
PR1 optional model, schema 19, API, RBAC and CAS; PR2 frontend section and Review & Send card;
PR3 document-assisted suggestion; PR4 gated Shell-only mapping (allowlist empty); PR5 Amend Policy-ID
safeguard (XPI Amend fails closed without a bound provider-generated Policy ID). PR4 does not
depend on PR5; PR5 may land independently.

The deferred provider-qualification dependencies are listed in
`docs/sponsor-questions/OPEN_QUESTIONS.md` under "XPI optional enrichment (D-117)".

## D-118 - AI Assistant paid-model sessions (US$5) and a simplified AI Models Console (OWNER-APPROVED Option B with mandatory corrections; synthetic-only FYP development)

Status: the owner conditionally accepted the revised D-118 architecture on 2026-11-03 ("D-118 —
Approve Option B with Mandatory Corrections"). The six mandatory corrections are written into the
rules below. Built on branch `feat/d118-paid-sessions` from main `058e91b`. Authority:
`USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence class: Local (mock transports,
disposable ledgers and state databases). Not sponsor policy; no Live, Sandbox or provider-status
claim. Not authorised by this entry: migrating the owner's existing stores, a paid
requalification, a restart of the running demo, any paid call, merge.

Goal: a teammate's journey is *select provider → enter API key → test & qualify → activate &
chat*. US$5.00 is the automatic default and maximum session allowance; lowering it is optional and
nothing about it must be edited or confirmed to activate. Local Ollama needs no key and no
session. The existing `BudgetLedger` engine stays (atomic worst-case admission, conservative
settlement, breaker, verification); the routine operator procedures built around it are replaced.

| # | Decision |
| --- | --- |
| S1 | *Superseded by the 2026-11-04 amendment (P2 and P3: a format-1 ledger is now a legacy store, never migrated; the `migrated` origin and event and `auto_reconciled` were removed); kept as the record of the first approval.* **Ledger format 2 (additive).** A ledger is format 2 when `PRAGMA user_version = 2`. The v1 tables, rows and events are kept unchanged. Added: `calls.purpose` (`chat` or `qualification`), `calls.session_id`, `ledger_meta.write_token`; tables `ledger_profile` (one row: origin `fresh` or `migrated`, accounting mode, opening basis), `sessions` and `ledger_events` (insert-only: `fresh_init`, `migrated`, `session_started`, `session_allowance_changed`, `breaker_resumed`, `auto_reconciled`, `trip_while_open`). Every new code path bumps `write_token` when it changes the ledger header. Two triggers fence earlier code: an inserted call without a purpose and a header update that leaves `write_token` unchanged are refused, so an earlier process still running cannot admit a call or change the header of a format-2 ledger; earlier code and scripts also refuse to open it (`user_version`). A format-1 ledger is refused (`LEDGER_MIGRATION_REQUIRED`) and never migrated at start-up. |
| S2 | **Sessions.** A session belongs to one provider ledger (Claude Balanced and Fast share Anthropic's; GPT-OSS has OpenRouter's). At most one is open. Allowance: 1 to 5,000,000 micro-USD, default 5,000,000 (US$5.00, also the code maximum). Every call admitted on a format-2 ledger names its session. Admission, in one `BEGIN IMMEDIATE` transaction: profile, breaker, calls in flight, lifetime cap, daily cap (both unchanged), then the session: committed = charges of its closed calls + reservations of its open calls; refused (`refused_session_allowance`) if committed + this reservation > allowance; chat calls in the session refused (`refused_session_calls`) at the HR calls limit, which now counts per session and persists. Qualification and chat share the money allowance; qualification calls are not chat calls (as before). The free connection test and workspace read are not calls. |
| S3 | **Lifecycle.** The first session is opened by the first explicit paid action (a confirmed qualification or a chat answer) only when the ledger has never had a session. A restart, reconnect, key change, connection test, activation, re-activation or rollback never opens or resets one: consumption is computed from the call rows. An exhausted session stays open and refuses paid calls; it is never renewed automatically. HR starts a new session explicitly (`MODEL_CONFIG_MANAGE`, Origin, rate limit, re-checked in the change lock, compare-and-set on the current session, audited); the old one is closed as `replaced`. HR may change the open session's allowance within 1 micro-USD to US$5.00 (compare-and-set on its revision, audited). The daily (default now US$5.00 for both providers in the environment defaults; stored HR values are kept) and lifetime caps still bound every session together. |
| S4 | *Partly superseded by the 2026-11-04 amendment (P5: the opening-usage rule; a session store opens at zero). The rest stands.* **Claude: provider-capped accounting (correction 2).** The 24-hour and 7-day reconciliation windows no longer gate chat, qualification or activation on a `provider_capped` ledger. Kept: inference keys only, the workspace read and its pin, the workspace named in every reply, in-band verification, the separate ledger, the D-102 limits, the lifetime cap at most the lower of US$30.00 and the stated workspace limit, the breaker. A fresh Claude ledger is created at enabling, after the setup record is stored and only when none exists, with an opening usage of zero **only** when the key's workspace is non-default (the free read names a workspace id) and the owner confirms in the one-time setup record that it is a new, dedicated workspace with no earlier usage and a provider spending limit; otherwise HR must enter the workspace's cumulative cost from the Console as the opening usage. The setup record keeps the four D-107 statements, including `key_revoked_at_fyp_end`; `inference_key_only` is also enforced by the key format. Residual risk (owner-accepted with this option): without an Admin key the app cannot read Anthropic billing, so drift between the ledger and billing, or spend outside the app in the workspace, is detected late; the bound is Anthropic's own workspace limit, which is monthly and resets, so it never bounds a session and bounds N months at N times the limit. HR reconciliation (D-110) remains available but is never required on this path. |
| S5 | *Superseded by the 2026-11-04 amendment (P4: GPT-OSS session stores are provider-capped and automatic reconciliation was removed; the fresh-ledger rule stands); kept as the record of the first approval.* **GPT-OSS: provider-anchored accounting with automatic reconciliation.** At each free preflight that reads `GET /api/v1/key`, when no call is open, the last call closed at least the settle lag ago and the provider's usage is between the last provider usage and the ledger estimate plus US$0.05, the service applies the existing `BudgetLedger.reconcile` itself (audited `auto_reconciled`). Anything outside that range is not adopted: the preflight fails as before, and a drift above tolerance opens the breaker. The key's finite, never-resetting provider limit is still required. A fresh OpenRouter ledger is created at the first connection test, only when none exists, with the provider-reported usage as its opening usage and a cap of opening + min(key limit remaining, US$30.00). |
| S6 | *Partly superseded by the 2026-11-04 amendment (P6 and P7: HR resumes financial stops; routing and integrity stops stay with the owner via `resume-after-review`). The masking rule and "never automatic" stand.* **Breaker recovery (correction 3).** Never automatic. HR may resume only a breaker opened as `abandoned_call` or `usage_missing`, and only when the ledger proves the condition is conservative-only: no call open, and every unverified or quarantined call since the last resume was closed `unsettled` or `abandoned`, charged its full reservation, with no anomaly and no provider refusal. The charges, call states and verification states are kept; the resume is an audited `breaker_resumed` event. A trip that happens while the breaker is already open keeps the breaker's code but is recorded (`trip_while_open`); any such genuine trip since the last resume refuses the resume (`MASKED_ANOMALY`), so a resumable code never hides a later drift or quarantine (QG F1). Routing anomalies, provider or model mismatches, cost or token bounds exceeded, reconciliation drift, provider refusals, a failed ledger write and any other unverified or quarantined charge stay stopped for the owner (D-110 R8 and D-116 H3 unchanged). Verification of a conservatively charged call with no provider record now opens the breaker as `usage_missing` instead of `reconcile_drift` or `routing_anomaly`, so it is not taken for a billing discrepancy; the call is still quarantined. On an OpenRouter ledger a quarantined call (for example one with no generation record) is a routing-evidence gap and is never resumable by HR: only unverified, conservatively charged calls pass the proof there. |
| S7 | *Superseded by the 2026-11-04 amendment (P3: `migrate-v2` and `ledger_migration.py` were removed; existing stores are archived, never migrated, and are not used by the runtime); kept as the record of the first approval.* **Migration of existing stores (corrections 1 and 5).** Only the owner, with separate approval, runs `scripts/budget_ledger.py migrate-v2` on a stopped service. It refuses unless: the D-110 reconcile lock is free and no intent marker exists; no call is open; no call, close or operator event happened within the quiet period (default 300 s); the breaker is closed or open with a resumable code; and the v1 ledger passes the same checks `verify()` makes (SQLite integrity, exact v1 tables, one v1 header with a known profile, header totals equal to the call rows, baseline not below the provider figure). The accounting mode follows the ledger's provider (Anthropic provider-capped, OpenRouter provider-anchored) and cannot be chosen otherwise, here or at creation (QG F2). It then writes a verified backup (SQLite backup API, integrity and row counts checked), migrates in one exclusive transaction, and checks that every v1 row and event is unchanged. A refusal leaves the ledger byte-identical. Ledgers, audit records, reconciliation runs, markers and owner requests are never deleted or reset. P1 (D-110 R13) is no longer on any routine path: a fresh ledger has no legacy copies, a migrated one is fenced (S1) after the quiet-period check, and chat, qualification and activation never wait for it. It still gates the optional HR reconciliation tool (D-110), unchanged. |
| S8 | **Console.** AI Models opens on *Set up AI*: choose a model, save and test the key (Claude's one-time setup record on first use), test & qualify (one confirmation naming the paid calls and the amount from the session), activate (one confirmation with the external-provider warning and the existing quality acknowledgement). A status strip shows the session allowance used, held and remaining, the worst-case cost of one answer and the HR key's expiry. Exceptions show one plain sentence and one action. The existing sections remain under Administration. |
| S9 | **Unchanged (correction 6).** D-094, D-095 and D-104 (verified synthetic cases only on external providers, the per-call re-check), RBAC, the read-only assistant, case isolation and retention, D-106 key handling, no automatic model switching. |
| Q1 | **Qualification basis.** `budget.py`, `anthropic_runtime.py`, `remote_checks.py` and `remote_test.py` change, and new strings regenerate `synthetic_boundary.json` (21 words added to `code_vocabulary` only; no conversation, prompt, value or document vocabulary changes). The basis moves from main's `77e50313a62c…` (the value is superseded by the amendment's Q2), so every external-model qualification is out of date once this runs; a paid requalification needs its own owner approval. A qualified local profile needs a free re-run; the environment baseline is unaffected. |

Overspend that remains (stated in the console and docs): no call is admitted whose labelled
worst-case reservation would take a session above its allowance, across restarts, concurrent
requests and the qualification process. Real spend can still exceed it by one in-flight call's
cost above its reservation (the breaker then opens), by spend outside the app with the same key or
workspace, or by a wrong provider figure. The only absolute ceilings are the OpenRouter key limit
(lifetime) and the Anthropic workspace limit (monthly).

**Amendment 2026-11-04: simplified for the FYP POC (owner direction "D-118 — Final Scope
Correction: Simplify for FYP POC").** The reconciliation-ledger architecture is no longer a
requirement of the AI Models Console. The provider's own spending limit is the primary financial
backstop. Inside the app, only the US$5.00 session allowance remains, with conservative charging
of pending and uncertain calls, restart protection and explicit renewal. Where this amendment
differs from S1 to S7 above, the amendment applies. S2, S3, S8, S9 and the overspend statement
are kept.

| # | Change (bounded delta on PR #156) |
| --- | --- |
| P1 | **Kept from PR #156.** The `BudgetLedger` engine. Atomic worst-case admission. Uncertain, cancelled and abandoned calls charged in full. The US$5.00 session allowance with its persistent chat-call limit. Explicit session renewal and allowance changes. The guided *Set up AI* page with its two confirmations. The setup view. The daily and lifetime caps and their HR controls. |
| P2 | **Fresh session stores, never the old ledgers.** The runtime's default stores are new files: `data/budget/sessions/anthropic.sqlite3` and `data/budget/sessions/openrouter.sqlite3`. Each is created on first use from the console (Claude at enabling; GPT-OSS at its first connection test). A store from the earlier design, if a launcher still names one, is refused as `LEGACY_STORE` and never migrated. The service never reads, writes or depends on it. |
| P3 | **Removed: migration.** `ledger_migration.py` and `budget_ledger.py migrate-v2` are removed. Existing stores are archived instead with `scripts/storage/archive_accounting_stores.py`. It copies each legacy ledger with the SQLite backup API into a new archive folder, checks that each copy's rows equal its source's, writes a SHA-256 manifest, and never changes, moves or deletes a source. Starting the simplified runtime on an existing deployment means pointing the launcher at the session stores (template updated). That is an owner step with its own approval. Ledgers, audit events, reconciliation runs and qualification history are kept as they are. |
| P4 | **Removed: reconciliation as a dependency (owner-approved retirement).** Every session store is `provider_capped`. On it:<br>• the Claude 24-hour and 7-day windows gate nothing (S4);<br>• OpenRouter's preflight no longer requires provider usage to match the ledger (`ledger.usage_reconciled`), and S5's automatic reconciliation is removed;<br>• raising a Claude limit no longer needs a reconciliation;<br>• P1 (D-110 R13) and HR reconciliation (D-110) are never on the routine path. D-110 stays available, as an optional tool, for a store that uses it.<br>*Trade-off:* drift between the app's figures and provider billing, or spend outside the app, is no longer detected by the app. It is bounded only by the provider's own limit: the OpenRouter key limit (lifetime) or the Anthropic workspace limit (monthly). The session allowance is not a billing guarantee. |
| P5 | **Removed: opening usage for Claude (owner-approved retirement; supersedes correction 2's opening rule).** A session store counts only calls this deployment admits. It always opens at zero, with the basis `session_store`. *Trade-off:* the lifetime cap is deployment-scoped. Earlier workspace spend is bounded by the Anthropic workspace limit, not by the app. Kept: the one-time setup record, including the four owner statements, `key_revoked_at_fyp_end`, the workspace read and its pin. |
| P6 | **Recovery in the console (owner-approved retirement of routine owner CLI resets).** A breaker on a session store pauses paid calls and never retries anything. HR may resume it from the console, keeping every charge, for financial conditions only: `abandoned_call`, `usage_missing`, `provider_error` (a refused key, payment or limit, after HR fixes the cause), `cost_above_reservation`, `token_bound_exceeded`, and a cost mismatch (`reconcile_drift`). *Trade-off:* the owner no longer reviews these routine financial pauses. The charges stay conservative, and the provider's limit bounds them. |
| P7 | **Unchanged and kept with the owner: routing and integrity.** These stay blocked for HR:<br>• a model, provider or workspace mismatch (`routing_anomaly`), including any such trip recorded while the breaker was already open;<br>• a failed ledger write (`ledger_write_failed`);<br>• on OpenRouter, a call quarantined for a missing generation record.<br>The owner clears them after review with `budget_ledger.py resume-after-review --code CODE --confirm-reviewed`. That is a non-routine command and an audited ledger event. Making them HR-resumable would weaken a data-protection guardrail and is not proposed. |
| P8 | **Console.** *Run qualification* runs the free connection check, then the paid run. Its one confirmation states the calls and the most they can cost from the session, and is the consent `confirm_paid_calls` already records. The Claude opening question is removed. A legacy store shows one owner sentence. After a restart HR re-enters the key (D-106, unchanged), and the flow is otherwise the same. |
| P9 | **Unchanged.** Synthetic-only external models (D-094, D-095, D-104), RBAC and the change lock, key handling (D-106), the read-only assistant, case access and isolation, the qualification gates and basis rule, audit, and no automatic model switching. |
| Q2 | **Basis.** `budget.py`, `remote_checks.py` and `anthropic_runtime.py` change again, and the boundary is regenerated. The basis moves from main's `77e50313a62c…` to `17a3172e1607…` (17 words added to `code_vocabulary` only). |

**Owner commands on a session store (clarified 2026-11-04).** For a routing or integrity stop
the owner runs `budget_ledger.py resume-after-review --code CODE --confirm-reviewed`: it records
the review as a `breaker_resumed` event, keeps every charge and lets HR resume later financial
stops. The earlier design's `reset-breaker` needs a reconciliation newer than the stop and records
no review event, so on a session store a stop it closed would still block later HR resumes; the
script therefore refuses `reset-breaker` on a session store and names `resume-after-review`
(nothing is written). No ledger rule changes.

Reported for the owner, not changed (non-financial guardrails or separate approvals):
- **Accepted limitation (owner, 2026-11-04): GPT-OSS stops on a missing generation record.** An interrupted or cancelled GPT-OSS stream has no generation record, so it is quarantined as a routing-evidence gap and waits for the owner (P7). Treating it as financial would weaken routing verification.
- **GPT-OSS attestations are launcher settings.** The OpenRouter owner attestations (`auto_topup_off`, `prompt_logging_off`) and the D-094/D-095 decision names remain launcher settings. A teammate sets them when starting the stack, not in the console.
- **Keys end with the session.** HR keys stay in memory only and end with the session or a restart (D-106).
- **The owner's own deployment.** Switching the owner's deployment to the session stores, archiving its old ledgers, a paid requalification, a restart and a merge each need separate approval.

**Usability remediation 2026-11-04 (owner direction "D-118 — Final Usability Remediation: Make AI
Setup Actually Work"; PROJECT-DEFINED within D-118, no new authority).** Root cause of the
refused US$1.00 qualification: the paid question list defaulted to empty. The example `.env`
ships it blank with count 0, so the call count was unknown, the estimate showed "—" and the page
fell back to a generic "no room" message. The session (US$1.00, no calls) was never the blocker.

| # | Change |
| --- | --- |
| U1 | **Approved default.** `AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_QUESTIONS` defaults to the approved `P01#1,P02#0` with count 2 (D-092 P10, D-107 Q1). Both blank with count 0 means "unset" and gets that default. Any other inconsistent value is kept and refused by name (`REMOTE_MANIFEST_MISSING`). The question set is unchanged; D-111 Q6 stays a proposal. |
| U2 | **Named limits.** The paid estimate lists each limit (session, daily, lifetime, provider key) and names the one that blocks. The session's remaining amount now counts, so a run that the session cannot complete is refused before any call (`SESSION_ALLOWANCE_INSUFFICIENT`). Admission is unchanged. |
| U3 | **No false budget refusals.** A missing, earlier-design or unhealthy store is `SPENDING_STORE_NOT_READY`, and any other missing setup step keeps its own code. The budget refusal is returned only for a daily, lifetime or zero daily limit. |
| U4 | **Wizard.** Step 3 opens only after a passed connection check. A failed check never opens the paid confirmation. The cost and every limit are shown. An enablement record with no session store can create the store by confirming the setup again. A deliberate allowance is never reset or raised. |

Unchanged: the qualification basis (`synthetic_boundary.json` stays current; `config.py` and
`model_admin.py` are not basis files), admission and conservative charging, the caps, RBAC,
D-094/D-095/D-104, D-106 key handling, audit, and the paid-call consent. Evidence class: Local
(mock providers, disposable stores, real assistant service in real Chromium).

## D-119 - Layout-tolerant classification labels in the local document reader (OWNER-DIRECTED 2026-11-05)

Status: owner-directed on 2026-11-05 ("Layout-tolerant document field labels"), after synthetic
onboarding PDFs labelled `KYC Customer Type (suggested):` with the value on the next line were
not read. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence class: Local.
Supersedes the project-defined rule (earlier quality-gate reports, not a decision) that a
classification value on the next line is never read.

| # | Decision |
| --- | --- |
| L1 | **Qualifier.** `KYC Customer Type` and `Client Segment` labels may carry one short parenthesised qualifier before the colon (up to 40 characters, e.g. `(suggested)`). The qualifier carries no meaning: `KYC Customer Type (suggested): Company - Private` is read exactly as `KYC Customer Type: Company - Private`. |
| L2 | **Next-line value.** When nothing follows the colon, the value is the very next line, unless that line is blank, is itself a `Label:` line, is a numbered heading or a bullet, or is longer than 160 characters (such a line is skipped, never an error). Nothing is read without its label, and a value is never taken from further away. Provenance (`PAGE_n_LINE_m`) names the line the value came from. |
| L3 | **Unchanged.** Rule-based and local only (no model, no external call). The same evidence scores, observation limits and D-070 handling apply. As with the single-line form, a trusted value that is in the approved vocabulary and unambiguous is bound automatically as the case's DOCUMENT selection (a document labelled "suggested" therefore pre-fills the GoldTier classification); a value outside the vocabulary, or a second differing value, is not bound (manual selection or conflict review), and the RM changes a document-bound value through document review. Final Review & Send remains the human gate. A capture from an unusual layout (for example two labels followed by two values) can only produce a non-vocabulary value or a conflict, both of which fail closed. Identity fields, Group Company Name (D-117) and every other field are unchanged. |
| L4 | **Malformed PDFs stay rejected (owner decision, 2026-11-05).** Strict PDF validation is unchanged: the local document worker keeps `PdfReader(..., strict=True)`, and a structurally malformed upload (for example a broken cross-reference table) is still refused with `DOCUMENT_STRUCTURE_INVALID` before any text is read. Uploads are never repaired automatically and no structural check is bypassed. For the owner's two synthetic UAT PDFs (`Garden_Synthetic_Onboarding_GoldTier_Details_20261104.pdf` and `OPQ_Synthetic_Onboarding_GoldTier_Details_20261104.pdf`), re-saved repaired copies are the approved workaround; the originals are kept for comparison. No further PDF parser remediation is authorised. |

## D-120 - Durable POC-assumed interests: the D-081 restriction outlives the analysis history (OWNER-DIRECTED 2026-11-05)

Status: owner-directed on 2026-11-05 ("Durable POC Evidence Protection", Option 2), after three
independent reviews failed a rolling four-snapshot approach. Authority: `USER_AUTHORIZED_POC`.
Evidence class: Local. Not sponsor-confirmed, and not verified ownership. Refines D-081 option B
and D-078; it changes no percentage, UBO calculation or GoldTier gate.

Defect: D-081 compared a declaration with the current analysis by generated party IDs, so the
same POC values passed under new IDs, or once an intervening decision or the four-snapshot
retention removed the POC analysis from view.

| # | Decision |
| --- | --- |
| P1 | **Durable record.** `OwnershipAnalysisRecord.poc_interest_ledger` keeps each POC-assumed interest (`LOCAL_POC_ASSUMED_EQUAL_UNITS`): case identity, issuer and holder parties, percentage, provenance and source analysis. It is independent of `prior_analyses`, which keeps its plain latest-four bound and stays audit history only. No declaration history is kept. |
| P2 | **Append-only.** Every ownership write passes through one owner, which appends new interests. Both repositories refuse a write that shrinks, reorders or drops an established ledger, under the existing CAS and case lock. Two entries are one interest only when their case and percentage match and their issuers and holders are certainly the same parties: a registration decides whenever either party has one, so a shared name never merges different registrations and a registered party never merges into an unregistered one, and only two unregistered parties compare by name. Re-keyed links, and a renamed party with an unchanged registration, therefore add nothing; any doubt keeps both entries. It is bounded to 512 entries: a full ledger stops growing without an error, and every manual declaration is then refused before anything is saved, because an unrecorded interest may exist. Selected document observations stay available, so a full ledger never stalls the case. No separate store exists. |
| P3 | **Evidence route.** No decision clears a ledger entry. `DOCUMENT_OBSERVATIONS` is the evidence route: its existing checks (current case-bound document, version bindings, selected rows, every link covered, every row matching) are unchanged, and it may state the POC values. A later manual declaration of those values is refused; the observations are selected again instead. Such ownership stays labelled `MANUAL_DECLARATION_POC` / `LOCAL` and is never verified corporate ownership. |
| P4 | **Identity.** A declared link replays an interest when the percentage equals it and the issuer or the holder matches, by party ID, normalized registration or normalized name. So a same-percentage holder replacement on a POC issuer, or a lone 100% holder, needs evidence or a corrected value. A non-root company declared with no registration cannot be told from a renamed issuer, so a POC percentage under it is refused for review. Interests are scoped to the case identity they came from. |
| P5 | **Corrected declarations.** A declaration whose values differ from the ledger keeps its existing authorisation and needs no document. D-081's scope is unchanged: equal-unit links only, not `LOCAL_SYNTHETIC_RELATIONSHIP` or `LOCAL_POC_ISSUED_CAPITAL_BASIS`. |
| P6 | **Schema 19.** The ledger is backend-only (excluded from dumps, browser payloads and digests) and stored by `_persistence_value`. `DurableCaseSnapshotV18` and older readers reject the key even when null. Reads do not rewrite. |
| P7 | **Legacy cases.** A record with no ledger is unknown, never empty. If nothing can have been trimmed, or a source load is still retained, the interests are derived from the retained history, enforced, and recorded by the next permitted decision. Otherwise a manual declaration is refused (`409 OWNERSHIP_POC_EVIDENCE_REVIEW_REQUIRED`), corrected declarations included, because the interests cannot be known. Selecting current document observations remains available but does not establish the history; only a source reload does. Ownership already accepted before D-120 is not reopened. |
| P8 | **Rollback.** A schema-18 build rejects schema-19 envelopes (fail closed). |

Recorded residuals, accepted by the owner: a value moved by the smallest amount is a corrected
declaration, and renaming both issuer and holder while also supplying a different registration
for the issuer is indistinguishable from a different company. Both are visible in the review
receipt. Owner note: D-117's planned schema 19 moves to the next free version.

## D-121 - A UBO review never blocks readiness on the official Mock lane (OWNER-DIRECTED 2026-11-05)

Status: owner-directed on 2026-11-05 ("ensure no blocker for OPQ and garden as well as in general
for UBO"). Authority: `USER_AUTHORIZED_POC`. Evidence class: Mock. Not sponsor-confirmed. It
supersedes D-112 O7 and narrows D-081's "readiness stays blocked" on this lane only.

| # | Decision |
| --- | --- |
| U1 | **Advisory review.** `ACRA_MARKETPLACE_UBO_REVIEW_MODE` defaults to `advisory`. On the official Mock lane a current `REVIEW_REQUIRED` ownership analysis no longer blocks readiness, for every company, whatever its review causes. |
| U2 | **What does not change.** The analysis keeps its review state, issues and classifications, and it is never verified ownership. No percentage or UBO calculation changes. A failed or unfinished analysis still blocks, and so does an analysis made stale by an identity or document change. **Consequence:** partnership share problems are advisory too. Shares that do not total 100%, a missing or extra partner and unconfirmed agreement shares show as issues but no longer stop the case. |
| U3 | **Sandbox and Live** never qualify (D-112 O6): the switch needs both the official Mock registry and Mock GoldTier. With GoldTier in Sandbox a review still blocks. |
| U4 | **GoldTier and audit.** The explicit target confirmation is unchanged, and nothing is sent before it. An advisory review is never reported as accepted: `poc_basis_accepted` stays false, the review warning stays on screen, and the audit code is `OWNERSHIP_REVIEW_ADVISORY`. |
| U5 | **Rollback.** Set the switch to `blocking`. D-081 and D-120 protection of manual declarations is unchanged and still applies when a declaration is made. |

## D-122 - Conversational answers from external models on any case, bounded by scope and guardrails (OWNER-DIRECTED 2026-11-05)

Status: owner-directed on 2026-11-05 ("should not be restricted to verified synthetic cases only").
Authority: `USER_AUTHORIZED_POC`. It records `CONVERSATIONAL_DECISION` and widens D-115 X2, and
it supersedes the D-095 case-eligibility limit for conversational answers.

| # | Decision |
| --- | --- |
| A1 | **Any case.** Claude, GPT-OSS and any local or IT-configured model answer in their own words on any case the signed-in user may read, so the console's data access restriction no longer limits answers. The D-095 eligibility check no longer gates them; the per-call ticket stays, so only the exact checked messages are sent. |
| A2 | **Scope.** Questions outside corporate onboarding are redirected without calling a model, whichever model is active and even with a case open. Examples: arithmetic, public figures, homework. |
| A3 | **Guardrails kept.** Case context, RAG knowledge, the sentence-by-sentence claim checks, the read-only rule, spending limits and audit are unchanged. |
| A4 | **Data consequence.** External models now receive case facts and the ownership analysis, including people's names and holdings, for any case. That is acceptable only while this POC holds synthetic data. **It must not be used with real client data** without a new decision on the provider boundary. |
| A5 | **Requalification.** The qualification basis changes, so every external configuration needs a new paid qualification before it can answer. |

## D-123 - Director-managed workflows as an add-on (OWNER-DIRECTED 2026-11-05)

Status: `USER_AUTHORIZED_POC`. Not sponsor-confirmed. Design in
[ADR-014](ADR-014_DIRECTOR_MANAGED_WORKFLOWS.md).

| # | Decision |
|---|---|
| W1 | **Roles.** Only the Director (`POLICY_APPROVE`) sees and edits workflows, and activates them without a second approver. HR has no part. An active non-onboarding workflow appears as a tab for the RM or onboarder, who starts it on an existing case, fills in and confirms its stages. The Director cannot do those. |
| W2 | **Use cases.** A workflow's name is its use case. Onboarding has one workflow and its eleven existing stages are locked. Case refresh, other countries and similar use cases are separate workflows that onboarding cases never join. |
| W10 | **Case source.** The Director marks a workflow as using an existing or a new case. Existing-case workflows run for a company that finished onboarding, once per company per workflow, so a repeat run is not possible. New-case workflows hold their own company details as a workflow-only case: no onboarding case exists, no registry or onboarding check runs, and nothing appears in Cases, Dashboard or Audit. Uploads are read for suggestions and not kept. Access follows the owning team, and an RM may delete one. Either way the workflow has its own page and a "(name) cases" tab, and adds nothing to the onboarding case page. |
| W3 | **Stages.** A stage is a name plus the fields it collects, and it completes when a person confirms it. No new business rule, threshold or evidence test is introduced. |
| W4 | **Versions.** An open onboarding case follows the latest active version, including a new required stage, and keeps answers to anything unchanged. A case sent or being sent stays as it was. A run freezes its version when started. This is an owner-directed exception to the original frozen-snapshot invariant. |
| W5 | **Send check.** A required added stage must be confirmed before the zero-touch Final review & send. Any failure of the check refuses the send. Limit, accepted by the owner: the older `/api/clm/cases/{case_id}/target-confirmation` and `/submit` routes predate this work and do not pass the check. No current screen reaches them, but a signed-in onboarder or RM calling them directly can write to GoldTier with a required stage unconfirmed, and the case then still counts as not sent. |
| W6 | **Autofill.** Uploads may suggest values for labelled fields. A suggestion is never final until a person confirms the stage, and never overwrites a typed value. |
| W7 | **Boundary.** Collected data does not reach GoldTier, ownership or reconciliation, and new workflows do not write to GoldTier. No registry for another country is added. |
| W9 | **Full stage list.** Every case now always shows Initial identity, so the count matches the full pipeline. This is the one deliberate change to an existing screen and applies to all cases, including those with no added stage. |
| W8 | **On by default, inert until used.** Case flows are unchanged until a Director activates a stage. `WORKFLOW_MANAGER_ENABLED=false` and `VITE_WORKFLOW_MANAGER_ENABLED=false` remove the feature entirely. |

Periodic review remains an extension: this provides a way to define such a workflow, not
an ageing, scheduling or OCDD engine. Q-014 reviewer separation is unchanged.

Superseded in part (2026-11-15): W5 and W8 by D-136. The rows above are kept as the
historical record.

## D-124 - The advisory UBO review applies with GoldTier Sandbox (OWNER-DIRECTED 2026-11-05)

Numbering: drafted in PR 163 as D-123, and renumbered because main took D-123 for Director-managed workflows.

Status: owner-directed on 2026-11-05 ("goldtier must always be in sandbox and mock acra live marketplace, nothing will be completely mock"). Authority: `USER_AUTHORIZED_POC`. Evidence class: Sandbox for GoldTier, Mock for ACRA. Not sponsor-confirmed. It supersedes D-121 U3, and D-112 O6 for GoldTier Sandbox only.

| # | Decision |
| --- | --- |
| S1 | **Standing lane.** The POC runs ACRA Marketplace Mock with GoldTier Sandbox. Advisory applies there and with Mock GoldTier. Any other ACRA mode, and any Live target, still blocks. |
| S2 | **Consequence.** After an explicit target confirmation, a case with an open ownership review is written to GoldTier Sandbox, with provisional ownership. Nothing is sent before that confirmation. The confirmation records `OWNERSHIP_REVIEW_ADVISORY`. GoldTier receives no ownership fields. |
| S3 | **Unchanged.** D-121 U2, U4 and U5 stand: the review stays visible, nothing is reported as accepted, and `blocking` is the rollback, within the limits in S8. |
| S4 | **Reads are read-only.** Opening a case never changes it, runs recovery or calls a provider, for any actor. This keeps D-103: Support may read a held case and nothing more. The earlier projection of an interrupted existing-customer decision moved from the read to `/resume`. |
| S5 | **Explicit continuation.** A case held before its review became advisory continues only through `POST /resume`, with the case's current version headers. The creating onboarding user is reauthorized inside the case lock, as for document recovery. The case then waits for target confirmation. A legacy stage-order record may run its read-only Search here, never on a read. The direct `/api/clm/cases/{id}/target-confirmation` and `/submit` routes refuse a case with a continuation pending, inside the CLM lock. No other route retires an advisory hold, with one exception: changed evidence makes a new analysis under the normal rules, and that replaces the hold. A creator's complete declaration does this, and so does a document uploaded by any case actor that changes the analysed evidence. |
| S6 | **Failed continuation.** A continuation that fails before it raised anything, and before anything is frozen for send, can be retried through the same `/resume`. A failed Search is repeated. Any other failure, including one after the attempt raised a blocker or after confirmation, keeps its existing behaviour. |
| S7 | **Who confirms.** Accepted policy is unchanged: any case actor with access may confirm the target write, and that is checked inside the lock. Support and other teams are refused. Creator-only confirmation would be a separate owner decision. |
| S8 | **Rollback limits of `blocking`.** New cases hold at Ownership. Previously held cases stay held and no continuation is offered. A failed continuation can still be retried, and it returns safely to the Ownership hold. A case waiting for confirmation refuses confirmation (`CLM_NOT_READY`), with no write. A case confirmed but not yet written ends in technical failure on resume, with no write, and is not reversible. Once `customers/create` has succeeded, resume still completes `createPolicy` by design (D-082 F6). Nothing is reversed or retried automatically. |
| S9 | **Automatic release (owner-directed 2026-11-06, "i want automatic approval even for this step").** An advisory ownership hold no longer needs anyone to continue it. At backend startup, with no user involved, each advisory hold that S5 could continue moves on by itself to wait for target confirmation, and its event says so. This supersedes S5 for those holds: `/resume` is no longer the only route and no longer needs the creator's action in the normal path. S5's `/resume` stays as the fallback. S4 stands: reads still change nothing. A case makes a read-only Search at startup only when its Search checkpoint is missing or its identity changed, for example a legacy stage-order record. **The target confirmation in S2 is unchanged: it stays a human action, and nothing is written to GoldTier without it.** **Limits.** A case already in technical failure is not retried at startup (S6). A case with a failed current document cannot continue, and it cannot replace that document at Ownership, so startup and `/resume` both return it to document intake (`DOCUMENT_REUPLOAD_REQUIRED`). Someone must upload the document again, and onboarding then re-evaluates the case. A release that fails in the pipeline usually ends in technical failure, and `/resume` can retry it where S6 allows. A release that fails during recovery leaves the hold in place, and each later startup tries again, adding an event each time. Neither stops other cases or the backend from starting. If the backend stops mid-pipeline on a case that has had a continuation, unless the case is frozen or had a later document replacement, the next startup finishes that pipeline and restores any entity-resolution or mock-risk review that Ownership had not yet raised. If it stops between the two saves of an intake reopen, the next startup completes the reopen, and so can `/resume`, `/start` or `/intake/complete`; this only finishes a reopen already saved. Startup treats a running case as stopped, so this assumes one backend process on the store. An interrupted existing-customer decision is not an ownership hold, so it stays on `/resume`. Holds the S5 test excludes (stale analysis, frozen evidence, a government gate) keep their existing behaviour. The release runs before the backend accepts requests, so a case needing a Search adds up to one connector timeout to startup. |

## D-125 - The RM records the founding statute when confirming Government status (sponsor-requested, project-designed; candidate, Shane to confirm)

Status: sponsor feedback on 2026-11-05 asked that the RM record the legal basis when confirming
Government status, because that confirmation is what lets the case skip the ownership/UBO
analysis (MAS Notice 626 para 6.12, D-101). The rule below is project-designed, not
sponsor-confirmed. Authority: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`. Evidence
class: Local. It amends D-101's Government confirmation only; UEN routing (D-114), the
government register seed and the extractor labels are unchanged. Number note: D-120 and D-124
were already taken (#161, #163), so this is D-125.

| # | Decision |
| --- | --- |
| G1 | **RM input.** With the confirmation, the case creator keys in the **founding statute** (required, 3 to 200 characters after trimming, no control characters), an optional **section** (up to 40 characters; blank means none) and the **type of body**, `MINISTRY_OR_ORGAN_OF_STATE` or `STATUTORY_BOARD` (required). A missing or invalid value is the usual 422. The extracted Founding Instrument stays on screen so the RM can compare. |
| G2 | **Check.** After the existing evidence check (one current reviewed document, exact version), the server compares `normalise(statute)` with `normalise(Founding Instrument)`. `normalise` casefolds, removes text in round brackets, turns punctuation into spaces, collapses whitespace, strips, then drops one trailing four-digit year token, so "Monetary Authority of Singapore Act 1970" equals "monetary authority of singapore act". Only exact equality is accepted: no fuzzy or partial matching and no AI. **Bracketed text is accepted only when it matches the document** (quality gate L1): every bracketed group the RM enters must also be a bracketed group of the Founding Instrument after the same normalisation, so "... Act (fictional FYP test instrument)" matches the demo letter but "... Act (any note)" is a mismatch (G3). The document's own bracketed text need not be typed. One pure function (`services/government_status.py`) with unit tests. |
| G3 | **Mismatch.** Anything else is refused with `409 GOVERNMENT_STATUTE_MISMATCH`. Nothing is saved, no event is appended and the CLM record is not refreshed; the screen keeps the RM's inputs and names the document's Founding Instrument. |
| G4 | **Stored (schema 20).** `GovernmentStatusConfirmation` gains `founding_statute`, `statute_section`, `government_body_type` and `statute_match = MATCHED_AFTER_NORMALISATION`. They are recorded together (a half-recorded statute is refused) and omitted from dumps when absent, so older digests are unchanged. The event code stays `GOVERNMENT_STATUS_CONFIRMED`; its message names the statute and section. The RM-entered statute is **not** part of the evidence fingerprint: the confirmation stays bound to the document version, and a changed document invalidates it as before. |
| G5 | **Older confirmations.** A schema-19 confirmation (no statute) still loads, unchanged, but no longer counts: the step shows "confirmation required" again and the RM confirms with the statute. If the case had already moved past the Government hold (for example to target confirmation), there is no open hold to resolve, so the projection sets `resume_required` and the panel offers **Continue onboarding** (the existing resume) instead of the form; the resume's existing recovery reopens `GOVERNMENT_STATUS_REQUIRED` with no target write, and the RM then confirms with the statute (quality gate M1). Once a submission snapshot or target write exists the case cannot be re-confirmed, and dispatch stays refused (fails safe). `DurableCaseSnapshotV19` and older readers reject the new keys even when null; a schema-19 build rejects schema-20 envelopes. D-117's planned schema moves to the next free version. |
| G6 | **Body type is RM-asserted, not verified.** It is not inferred from or checked against the UEN entity-type code (GA/GB), because that mapping is not confirmed. |
| G7 | **Unchanged.** Creator-only, document binding, automation and case-event concurrency, the open hold, and no revision once a target submission exists. The confirmation is still not approval and claims no ACRA verification. |

Follow-ups (not implemented): section-level verification against the document; a GA/GB to
body-type cross-check once the mapping is confirmed.

## D-126 - AWS staging provider lanes: evidence-bound GoldTier Sandbox access, read-only by default (OWNER-DIRECTED 2026-11-07)

Number note: D-126 was free on 2026-11-07 on `origin/main` (2698ea4, after #170), every remote
branch, every local branch and the open PRs. #170 shipped the ACRA parts of P4 to P6: the
Marketplace credential check, provider acquisition without local seeds, and the official-root
allowances. Everything else ships with this record.

Status: owner-directed on 2026-11-07 for the AWS staging integration. Authority:
`USER_AUTHORIZED_POC`. Evidence classes: GoldTier Sandbox `SANDBOX_PARTIAL`, ACRA Marketplace Mock
`MOCK`. Not sponsor-confirmed. No provider classification changes. D-121, D-124 and D-125
are unchanged, except that P4 limits the staging official lane.

| # | Decision |
| --- | --- |
| P1 | **Read-only Sandbox in staging.** `GOLDTIER_SANDBOX_ALLOW_WRITES=true` is refused at startup when `APP_ENV=staging`. With writes off, Final Review & Send is refused with `CLM_TARGET_WRITES_DISABLED` before the ledger marks any attempt and before the case changes. If writes are switched off after some steps, the next mutation is refused, automation pauses in `RECOVERY_PENDING`, and the same submission continues once writes return. Writes need a separately reviewed write qualification. |
| P2 | **Evidence-bound Sandbox access.** In staging with GoldTier Sandbox, no Sandbox request is made unless the case holds identity evidence from an accepted source: Search, recheck, existing-customer confirmation, Send, and provider-verified Shell and Policy recovery are all covered. A typed name is unverified and is never sent; Search uses the accepted registry identity. The HR console accepts only an exact GoldTier ID. Refusals record `CLM_TARGET_REGISTRY_PROVENANCE_UNSUPPORTED` (or `REGISTRY_PROVENANCE_UNSUPPORTED` on a recheck); the HR console returns `GOLDTIER_SANDBOX_SEARCH_IDENTITY_UNVERIFIED`. |
| P3 | **Provenance, not entity type.** `TargetIdentityEvidencePolicy` lists reviewed sources by provider, environment and reference boundary, and an empty list accepts nothing. The case's name, UEN and country must still equal what the source returned, so an edited identity loses acceptance. Today only the official ACRA Marketplace Mock is listed; it is not the authority for every legal-entity type. A future source joins through its own reviewed provider contract. No entity type, UEN, case or company name is hard-coded. |
| P4 | **Government and seeded identities.** Neither is excluded as a category. Both are local synthetic evidence, have no accepted source, and so reach no Sandbox operation in staging. They are never promoted to official provenance. On the staging official lane, provider acquisition reads no local seeds. The Government register keeps its own labelled route. Local Mock onboarding and Mock GoldTier keep working for both. |
| P5 | **Official-lane allowances need an official root.** In staging, D-121's advisory review and the POC acceptance apply only to cases whose identity is official Marketplace Mock evidence. A case retained from the local Mock lane keeps its review blocking. |
| P6 | **Startup.** Staging on `api_marketplace_mock` requires both Marketplace credentials. A blank or whitespace `GOLDTIER_SANDBOX_USER_ID` is refused. ACRA and GoldTier modes stay independently selectable, and both default to Mock. |
| P7 | **Recheck outcomes.** A same-identity recheck whose Search fails ends in a recoverable technical failure at GoldTier Search. One that ends in review waits for review. Neither raises a rejected transition or creates a ledger entry. |
| P8 | **Unchanged.** The target ledger, no-replay and recovery, existing-customer confirmation, RM confirmation, TLS 1.3 verification and backend-only credentials. The AI Assistant is not restricted by these controls. |

Open before any write qualification: paused-state wording; Sandbox prior-case ledger proof; the
stale `initial_target_search` read model after a void; whether `check_uncertain_target_status` and
`verify_completed_target` keep a deliberate recovery exception; an approved way to populate the
Government register in staging.

## D-127 - Provisional dashboard SLA and attention rules (OWNER-DIRECTED 2026-11-12)

Status: `PROJECT_DEFINED_PROVISIONAL`. Chosen by the owner on 2026-11-12 from defaults the
implementer proposed. Not sponsor-confirmed. It narrows D-037's exclusion of invented SLA/risk
semantics only for these display rules on the Dashboard. Q-016 stays open.

| # | Decision |
|---|---|
| S1 | **Target.** A case's dashboard SLA target is 10 calendar days from case creation to completion, measured with the existing `case_elapsed_ms`. |
| S2 | **SLA status.** Open: `OVERDUE` past the target, `AT_RISK` within 2 days of it, else `ON_TRACK`. Completed: `MET` within the target, else `MISSED`. Compliance is `MET` / completed cases in the selected cohort; with no completions it is not calculated. |
| S3 | **Attention level** (named so it is not confused with the D-047 advisory risk rating). For open cases only: `HIGH` when overdue, when a blocker has been open more than 7 days, or when the case has not been updated for 5 days. `MEDIUM` when at risk, or waiting for review, recovery, inputs or after a technical failure. `LOW` otherwise. Every level lists the reasons that produced it. |
| S4 | **Rework.** A case counts as rework when it has two or more retained blockers at the same pipeline step. |
| S5 | **Boundary.** These rules are display and ordering aids only. They do not change workflow state, readiness, priority, routing, approval, escalation, notifications or GoldTier behaviour. They are not a compliance, regulatory or staff-performance measure. |

## D-128 - Read-only AI insights on the Onboarding Dashboard (OWNER-DIRECTED 2026-11-13)

Status: `USER_AUTHORIZED_POC`. Not sponsor-confirmed. Design in
[ADR-015](ADR-015_DASHBOARD_AI_INSIGHTS.md).

| # | Decision |
|---|---|
| I1 | **Display only.** The Manager view shows an "AI insights" panel with a summary, "What to note" and "What to do". There is no chat, question box, regenerate button or per-case recommendation. |
| I2 | **Source.** Fixed browser rules build findings from the dashboard as shown, including the demo sample. Severity, numbers and case links come from those rules. The model only writes the wording. |
| I3 | **Model.** The existing local Ollama baseline in the AI Assistant service, through a separate module and endpoint. Remote and test profiles are refused, and the chat assistant is unchanged. |
| I4 | **Checks.** Text may only use numbers from its finding and must avoid approval, rejection, deletion, closure or override wording. Failing items are dropped. |
| I5 | **Failure.** When the model is unavailable, slow or fully rejected, the panel is hidden, with no message or rule-based substitute. |
| I6 | **Privacy.** No customer names, registration numbers, documents or case identifiers are sent to the model, and prompt and answer text are not stored. |
| I7 | **API-key models (owner-directed 2026-11-13, "when i connect to the api key i can use both the dashboard ai and ai assistant ai chatbot"; "fall back to local model if one is available").** This supersedes I3's refusal of remote profiles. When the active model is an API-key model (Claude, GPT-OSS) and external models may answer in their own words (D-122), it writes the insights. Each call gets the single-use ticket for exactly its messages and passes that model's own readiness, spending limits and ledger, unchanged. A paid model gets one try. If it refuses, fails or its reply is rejected, the local baseline model writes them, when one is configured on a loopback URL; otherwise the panel is hidden (I5). Without D-122 only the local model is used. An IT-configured model on another endpoint is never used. **Shared allowance (owner-accepted 2026-11-13, "share the API key"):** a paid dashboard call is recorded in that provider's ledger as a chat call, so it counts against the same call limit and spending allowance as the chatbot. Claude runs one paid call at a time, so a chatbot question sent while a dashboard call runs may be refused as busy; the reverse falls back to the local model. The chatbot's code is unchanged. I4 and I6 are unchanged: only findings are sent, never customer data. D-122 A4 applies: synthetic POC data only. |

## D-129 - Hosted Claude data transmission (ACCEPTED 2026-11-15, Anthropic only)

Status: `ACCEPTED` by the owner on 2026-11-15 for Anthropic, terms (a) to (f) of
`outputs/real-inference-20261115/OWNER_APPROVAL_PACKAGE.md` section 9:

| Term | Accepted |
|---|---|
| a | Recipient Anthropic, `claude-sonnet-5-5` only |
| b | The r3.1 section 2 payloads of eligible synthetic cases (under D-139, cases that pass its R3 check) and the enabled D-130 paths |
| c | Never sent: user id and display name, staff-written knowledge, raw documents, Mongo data outside the facts, cookies, keys, telemetry, ineligible or unauthorised cases |
| d | Hosted lifetime ceiling US$5.00, daily cap US$5.00, 20 calls per paid session, hosted workspace limit US$5.00 |
| e | Synthetic-only input with the visible notice; standard Anthropic retention, no ZDR |
| f | Egress E1 (`clm_r22`, single pin) |

The owner also accepted C1 to C6 for the first restricted staging qualification (synthetic-only use, existing containment). OpenRouter and GPT-OSS are not covered: they need a D-129 amendment (`HOSTED_OPENROUTER_TRANSMISSION_DECISION`, D-138 A1). Recorded in code as `config.HOSTED_TRANSMISSION_DECISION = "D-129"` (D-138 R1). Before this, nothing was sent to Anthropic from the hosted
service. This supersedes D-138 R1's and A1's "ships as `None`" statements for Anthropic only; `HOSTED_OPENROUTER_TRANSMISSION_DECISION` still ships as `None`. Recording D-129 does not close release-readiness item R-7: it stays OPEN until the owner's K-9, the C7 activation, and the hosted 5-call qualification on the integrated image. Draft: `outputs/r22-d130r2-20261113/D129_DRAFT_R3_1_HOSTED_CLAUDE_DATA_TRANSMISSION.md`
(not tracked). It defines the exact payloads of the four hosted Claude chat paths, the OD-G8
identity rule, the synthetic-only input restriction and the spending caps.

## D-130 - Hosted Claude on the general chat, Support chat and "Try with this change" (OWNER-APPROVED FOR LOCAL IMPLEMENTATION 2026-11-13)

Status: `USER_AUTHORIZED_POC`, approved for local implementation and testing only. Not activated.
Not sponsor-confirmed. On the registered hosted Claude deployment only, the general chat, Support
chat and "Try with this change" may use the activated Claude configuration under every control
the case chat has. It amends D-115 and D-105 for that deployment only.

Owner decisions:
- OD-G1: all three paths.
- OD-G2: approved lines only for Support and "Try".
- OD-G3: repository-approved knowledge only.
- OD-G4: redacted synthetic draft rules.
- OD-G5: browser history as untrusted input.
- OD-G6: a five-call Balanced qualification.
- OD-G7: one combined release.
- OD-G8: no user identifiers to Anthropic, role only.

In code: `config.HOSTED_CHAT_DECISION` and `HOSTED_CHAT_PATHS`. Dashboard insights (D-128 I7)
are not among the hosted paths: on the hosted deployment the hosting layer refuses the insights
route outright (503 `DASHBOARD_INSIGHTS_UNAVAILABLE`), so no model of any kind is reached there.

Amendment (DRAFT, owner-directed 2026-11-14, local preparation only; not active): dashboard AI
insights as a fifth hosted Claude path. In code it is prepared and disabled
(`config.HOSTED_INSIGHTS_DECISION = None`); it is set only in a reviewed change after the D-129
fifth-path amendment, the notice, the independent QG, egress, the six-call qualification and the
owner's activation. When enabled: generation only on an explicit request
(`POST /assistant/dashboard/insights/generate`), never on load; the service derives enumerated
counts and labels itself from R2.1-eligible cases (no names, teams, case identifiers or case
text); Claude only, no fallback; 3 calls per user and 10 site-wide per Singapore day, inside the
shared spending cap. The merged `POST /assistant/dashboard/insights` stays refused on the hosted
deployment. Draft: `outputs/r22-integration-c2-20261114/D129_D130_FIFTH_PATH_AMENDMENT_DRAFT.md`
(not tracked).

## D-131 - R3 GoldTier secure egress: restricted CONNECT egress for the staging backend (OWNER-DIRECTED 2026-11-12; drafted as D-127)

Number note (alias): this decision was drafted and implemented as **D-127** on 2026-11-12, before `origin/main` assigned D-127 to the provisional dashboard SLA rules (#178). It is renumbered **D-131** in documentation only. Every `D-127` reference in the R3 product, deployment, test, image and host files (`apps/backend/app/config.py`, `apps/backend/app/connectors/goldtier_xpi.py`, `deploy/compose.goldtier-egress.yml`, `deploy/egress/**`, `deploy/LIGHTSAIL_RUNTIME.md`, `deploy/README.md`, `tests/deploy/**` and the R3 backend tests) means **D-131**. Those files are deliberately left byte-identical to the reviewed `68e621d` content and the published images. Text from `R3_G1_DECISION_RECORD.md` section 5, with the G2 owner decisions recorded below it.

Status: owner-directed G1 approval with amendments A-C, authority `USER_AUTHORIZED_POC`. Not sponsor-confirmed. Q-020 (endpoint, allowlisting, addressing, TLS, proxy, read-only scope) is open. `GOLDTIER_XPI` stays `SANDBOX_PARTIAL`. D-126 is unchanged.

| # | Decision |
| --- | --- |
| E1 | The backend reaches GoldTier only through an explicit HTTPX proxy (`trust_env=False`, TLS 1.3 verified, no direct fallback). Staging Sandbox refuses to start without it. The base-URL host must equal the egress FQDN |
| E2 | The egress proxy is Smokescreen at a pinned commit, subject to hard conformance gates. A failure needs a separate decision |
| E3 | Networks: `goldtier-control` (internal) and `goldtier-uplink`. The overlay is applied last. ICC stays on. Mode defaults to `mock` |
| E4 | Host enforcement uses a dedicated `inet clm_r3` table under its own unit. `nftables.service`, ufw and `DOCKER-USER` are not used |
| E5 | DNS goes through an exact-name `A`-only resolver |
| E6 | Exactly two outbound flows are allowed (Amendment C). All others are blocked |
| E7 | Runtime firewall loss must be prevented or promptly terminated, with measured windows (Amendment A) |
| E8 | The SNI or shared-address residual is unresolved and needs a separate decision before production (Amendment B) |

G2 owner decisions (2026-11-12, after the G2 S2 STOP; G2 LOCAL only, not production-accepted):

| # | Decision |
| --- | --- |
| G2-P2 | Option B. The R3 Smokescreen entrypoint accepts only the exact lowercase ASCII request `CONNECT <fqdn>:443 HTTP/1.1` with one exact `Host`, validated on the raw request head before any parsing, IDNA mapping, ACL or DNS, and re-checked after Smokescreen's own decision. It uses a fixed role and can only narrow what Smokescreen accepts. Smokescreen's ACL and private-address denial stay independent. The earlier failed S2 evidence is kept unchanged |
| G2-LN | Option A. Each R3 container's root guard (PID 1) holds `NET_ADMIN`, `SETUID`, `SETGID` and `SETPCAP`, installs and verifies Layer N before starting the child, and keeps only `NET_ADMIN` once the child runs. The child runs as uid/gid 65532 with empty effective, permitted, inheritable, ambient and bounding sets and `NoNewPrivs`. This replaces the handoff's one-capability wording for G2 LOCAL only; the independent QG must rule on the increased guard privilege |

Fast-track staging owner decisions (2026-11-13, A1 and A2; a temporary academic staging demo, not production):

| # | Decision |
| --- | --- |
| FT-A1 | Read-only exact GoldTier ID lookup only, with at most three authorised Sandbox test calls. The tested G2-LN root guard is reused; there is no `NET_ADMIN` sidecar. Backend `:8000` isolation on `goldtier-control` relies on Layer N alone, which is accepted for this bounded design (G2 note N9). Mongo isolation, authentication, provenance (D-126), the R2 assistant safeguards and the rollback protections are unchanged |
| D-cert | `certifi` is declared and pinned in `apps/backend/pyproject.toml` at the version in the tested G2 backend image. Normal TLS verification is unchanged |
| FT-A2 / R-1 | O-1 is pinned to a validated GoldTier IPv4 set: the `goldtier_dst_v4` set in `inet clm_r3` (`GOLDTIER_DST_V4` in `clm_r3.vars`) and the proxy's required `CLM_EGRESS_DST_V4` in Layer N. There is no unpinned mode and no fallback to any public IPv4 |
| R-1b (A3) | **Accepted by the owner (2026-11-13) only for the temporary, read-only FYP staging demonstration.** The residual is reachability of other virtual hosts on the two pinned addresses by a compromised backend changing SNI/Host inside the tunnel. Conditions: the independently reviewed IPv4 pin (QG PASS WITH NOTES, candidate `c2f7e467`), unchanged TLS verification, the exact-hostname `CONNECT` restriction, fail-closed behaviour and the rollback stay in place. If any of them is weakened, or the use goes beyond that demonstration (writes, production, a longer period), this acceptance lapses. Not sponsor-confirmed. Whether the addresses are dedicated is unknown (Q-020 part 3) |
| FT-CRED | The owner authorises reuse of the existing locally tested Sandbox endpoint, `user_id` header method and connector from AWS staging (authority `USER_AUTHORIZED_POC`). No new credential is requested. **This is the owner's authorisation, not sponsor permission.** Any sponsor-specific permission for hosted-origin use, and source-IP allow-listing, are **UNVERIFIED** (Q-020 parts 2 and 6). A provider 401/403 or a refused connection on the first call is treated as that permission being absent: stop and roll back to Mock |

Not authorised by this record: G3a, G3b, G3c and G4; any AWS, host or production change; image publication; GoldTier calls; commit, push, PR or merge.

## D-132 - R2.1 hosted assistant case eligibility (RD-1): an exact approved case list and a creation cutoff (OWNER-DIRECTED 2026-11-13)

Number note: drafted as D-128 on 2026-11-13, when the last number on `origin/main` (b7cb6a7) was D-126.
PR #178 (3f9f6f4) then used D-127 (dashboard SLA) and D-128 (dashboard AI insights). D-129 and D-130
are reserved for the hosted Claude work (R2.2) and D-131 for the GoldTier R3 secure-egress
documentation (PR #177), so this decision is D-132 (no change of substance). Earlier R2.1
handoffs and evidence that say "D-128" for the case gate mean this decision.

Dashboard insights (D-128) on the hosted service: the hosting layer refuses the insights route
outright (503 `DASHBOARD_INSIGHTS_UNAVAILABLE`) before any session, origin or route check, so no
model is reached there; the browser hides the panel (D-128 I5).

Status: owner-directed on 2026-11-13 for the R2.1 assistant-only release (approvals A1 to A4 on
the RD-1 I-0 finding). Authority: `USER_AUTHORIZED_POC`. Not sponsor-confirmed. It applies only
when the hosted service (`assistant_hosting`) is running. Local and development use are
unchanged, and so are D-095, D-099, D-107 and D-126. It does not enable hosted inference.

| # | Decision |
| --- | --- |
| E1 | **Backend first.** The backend's 401, 404, roles and team scope are unchanged. The gate runs only on a case summary the backend returned to this user. |
| E2 | **Exact approved cases.** The summary's own `case.case_id` must equal the requested id, and `sha256(case_id)[:12]` must be in `ASSISTANT_HOSTING_ELIGIBLE_CASE_REFS`. |
| E3 | **Created before the cutoff.** `case.created_at` must be timezone-aware and strictly before `ASSISTANT_HOSTING_ELIGIBLE_CREATED_BEFORE` (UTC). |
| E4 | **ACRA in MOCK.** `case.entity.source` must be `ACRA` / `MOCK`; a missing entity or source refuses. |
| E5 | **Marketplace tokens refuse.** The exact tokens `ACRA_API_MARKETPLACE_MOCK` and `api_marketplace_mock` refuse. Their absence is not treated as provenance. |
| E6 | **Not provenance.** `registry_evidence_binding` is not required, and `freshness_policy_id` is not a provenance marker; either lane can produce both. |
| E7 | **Refusal.** `403 ASSISTANT_CASE_NOT_ELIGIBLE` ("The assistant is not available for this case."), raised in the one `load_case()` every case-bearing route uses, before any context, answer, conversation, feedback or view record is written. The reason is logged with the case reference only. |
| E8 | **Startup.** A missing value gives `CASE_ELIGIBILITY_REQUIRED`. A malformed or duplicate reference, or a cutoff that is not UTC, gives `CASE_ELIGIBILITY_INVALID`. Either exits with code 78. The overlay requires both values, with no fallback. |

Basis (I-0 finding, `outputs/rd1-assistant-eligibility-20261113/RD1_I0_FINDING.md`): the browser
summary cannot tell Mock ACRA from ACRA Marketplace Mock. Both serve ACRA / MOCK, and the
data-set namespace is dropped in `OnboardingCaseResponse.from_domain`. So Marketplace exclusion
rests on E2 and E3. **This is a bounded FYP POC rule, not a general source-provenance check.**

Approved references: `0ff73a514d12`, `125743b9c5e0`, `fa1aab4d6f68`. The cutoff
`2026-11-12T05:07:25Z` is provisional, for local implementation and tests only.

Open before the R2.1 AWS release: the release lead must verify, read-only on the host, that the
backend ran `acra_connector_mode=mock` up to the cutoff, and must confirm the exact creation
boundary. If either cannot be established, the release stops; the rule is not weakened. No ACRA
window that can create cases runs before R2.1 is deployed and accepted.

Side effect: `ai_assistant/main.py` is a model-qualification basis file, so the local paid-model
qualification basis changes. Local Claude or GPT-OSS use from a checkout with this change needs
requalification first; the hosted service has no model.

## D-136 - Every send path enforces stored required workflow stages (C1/C2; OWNER-APPROVED 2026-11-15)

Status: `USER_AUTHORIZED_POC`, owner-approved on 2026-11-15 for the isolated C1/C2 fix.
Not sponsor-confirmed, not production-qualified. Numbering is provisional: D-133 to
D-135 are held by open proposals, so renumber at integration if another entry lands
first. It supersedes D-123 W5 and W8. Those rows stay above as history. Design:
[ADR-014](ADR-014_DIRECTOR_MANAGED_WORKFLOWS.md).

Review provenance: the independent Quality Gate result PASS WITH NOTES (2026-11-15)
applies only to the original frozen six-file C1/C2 implementation candidate
`1d25f23b77a0a0c2a4cba645b4a0061574cae8503189f9c2c8c57bfe0029c4b8`. It does not cover
this entry or the related ADR-014 and ARCHITECTURE.md wording. That documentation delta
needs its own independent review.

| # | Decision |
|---|---|
| E1 | **Three send paths, one check.** The zero-touch target confirmation, the legacy `/api/clm/cases/{case_id}/target-confirmation` and the legacy `/submit` each refuse while a stored required added stage is not confirmed. On the legacy routes the check runs inside the CLM case lock, after reauthorization and the D-124 continuation check, and before any Search, snapshot, confirmation or GoldTier call. It returns `WORKFLOW_STAGE_INCOMPLETE`. Supersedes W5's accepted limit. |
| E2 | **Fail closed.** An empty workflow store (no definition, or no active version) holds nothing. An unavailable or corrupt store refuses every send path with `WORKFLOW_STAGE_CHECK_UNAVAILABLE`, except the E3 continuation of a legacy Submit whose GoldTier write is already recorded. No new send starts when the check cannot be read. |
| E3 | **In-flight exception, legacy Submit only.** Submit continues a send only when the persisted target-execution ledger already shows a GoldTier write for its frozen submission: an attempted Shell, Policy or Amend, or a retained target outcome or receipt. This keeps ledger ordering and no-replay recovery. A frozen snapshot alone, a Search-only entry, a missing CLM record or anything in the request never qualifies. Target confirmation has no in-flight exception. |
| E4 | **Manager switch.** `WORKFLOW_MANAGER_ENABLED=false` and `VITE_WORKFLOW_MANAGER_ENABLED=false` remove the workflow routes, screens, upload suggestions and workflow-data deletion. They do not disable enforcement of previously stored required stages. Supersedes W8's "remove the feature entirely". While the switch is off, every stored required stage that is not yet confirmed keeps blocking every send path, and it cannot be filled, confirmed or changed. A required stage that is already confirmed does not block. To proceed, switch it back on and restart, then have the RM or onboarder complete and confirm the outstanding stages. An unconfirmed required stage is never bypassed. |
| E5 | **Governance unchanged by this entry.** The owner's workflow governance policy stands: HR may edit workflow proposals; exactly one Director approves or rejects each workflow change; workflow stages are never removed or skipped; reordering is allowed only where dependencies permit; incomplete required stages are completed, not bypassed. It is recorded in the provisional D-135 draft and is not yet implemented. Removing or skipping workflow stages is prohibited by owner policy. The current code follows D-123 W1: a Director edits and activates alone, and the code does not technically stop a Director from activating a version that drops an added stage, which would remove it from open cases (W4). That is a known implementation gap, not permission to remove stages. No technical enforcement of the prohibition exists yet. Until the governance fix is implemented, no workflow publication that removes an existing stage is authorised. This fix does not change that behaviour. Existing onboarding stages stay locked in the orchestrator. |
| E6 | **Residual risks, accepted for the isolated FYP staging POC only, and OPEN.** R1: a workflow publish does not take the case lock, so a required stage activated after the last check and before a target step is not seen. The window is narrowed on legacy Submit, not closed, and the zero-touch route has the same window. R2: a case sent through the legacy routes is not counted as sent for workflow versions. N3: in Mongo mode the backend now needs the workflow store reachable at startup, whatever the switch says. None of these is fixed or production-qualified. This acceptance does not extend to the stage-removal governance gap (E5), production readiness or any race-free enforcement claim. |
| E7 | **Conditions.** R1 needs a separate decision before any claim of race-free enforcement. R2 must be fixed, or the legacy routes retired, before broader reliance on them. N3 is a deployment and availability dependency of staging: the workflow store must be reachable for the backend to start. |

Also disclosed by the gate and fail-closed: inside the R1 window, legacy Submit can answer
`503 CLM_SUBMISSION_UNEXPECTED_FAILURE` instead of the 409 hold code (N1), and a
persistence error while reading the in-flight state surfaces as a 500 (N4). In both
cases nothing is written to GoldTier.

## D-135 - Workflow authoring, single-Director approval and the required-obligation ratchet (OWNER-APPROVED DESIGN 2026-11-15; not implemented)

**Status:**
- `USER_AUTHORIZED_POC`. The owner approved this as the P2/P3 design on 2026-11-15: revision R1,
  RD-1 to RD-6, the G0 conditions, the conditional-write dispatch fence as the revised D10
  mechanism, the G0 remediation rulings, and the G0 R3 and R4 rulings of 2026-11-16 (including
  RD-5 counts as maxima).
- It is a design decision only. **Nothing here is implemented**, and current behaviour is
  unchanged until the phases are separately approved and merged.
- Not sponsor-confirmed. Design: [ADR-017](ADR-017_WORKFLOW_AUTHORING_AND_GOVERNANCE.md)
  (Proposed).
- Numbering: D-135 was held for this record by the earlier provisional draft.

**Relationship to other decisions:**
- When implemented, it supersedes D-123 W1 (roles) and, in part, W4 (versions), and the owner's
  interim F2 publication restriction.
- When P2-0 ships, it amends D-136 E2 (row G15). D-136 is otherwise preserved in full.
- Until P2-1 enforces G7 technically, D-136 E5's interim rule stands: no publication may remove or
  weaken an existing required stage.

| # | Decision |
|---|---|
| G1 | **Authoring.** HR (`POLICY_MUTATE`) creates, edits, validates, simulates, submits and withdraws workflow proposals. Directors do not author ordinary workflow changes. |
| G2 | **Approval.** Exactly one Director (`POLICY_APPROVE`) approves or rejects each pending proposal, with a reason. The author never decides their own proposal. A decision is final, immutable and published atomically as a new version. One open proposal per workflow. Abandoned drafts may be released by another HR user after 14 days of inactivity, or when the author's account is gone. Release never publishes. |
| G3 | **Scope.** G1 and G2 apply to every workflow. |
| G4 | **Unchanged.** Role capabilities, case access and team scope, policy authority, ACRA identity provenance and the staging identity policy, AI Assistant safeguards, the code-owned mandatory engine order, no-replay recovery, D-136 E1, E3 and E4, and the single-backend-process deployment. |
| G5 | **Policy values** stay owned by the policy catalogue. The designer proposes policy changes only through the existing policy proposals, and workflow proposals hold references, not values. |
| G6 | **Legacy provenance.** Versions activated under D-123 are recorded as pre-governance single-Director activations, not as approved. The required baseline is seeded from each workflow's currently active version only. Obligations a Director dropped under D-123 are not resurrected without a separate approved proposal. |
| G7 | **Required-obligation ratchet** (RR-1 to RR-10, ADR-017 §2). Each required obligation keeps its strictest published signature in a stored baseline. Kind and wording are fixed beyond normalisation. CHOICE options are the intersection of every published set, so a removed option can never return. Case-data prefill stays absent. Applicability is never narrowed. Every publication kind is checked against both the active version and the baseline, for new and existing cases. Deactivation keeps the baseline, and reactivation must satisfy it. **No in-product path removes or weakens a required obligation** (RD-2). Restore, reset and emergency fallback publish the base plus the baseline. Before approving a new or tightened obligation, the Director must acknowledge that it is permanent. |
| G8 | **Emergency fallback.** A Director alone, with a mandatory reason, may publish the safe target immediately. It writes an immutable record and raises a persisted HR notice that is kept until acknowledged. It cannot bypass G7, the mandatory stages or send enforcement. |
| G9 | **Send dispatch fence** (ADR-017 §3). A first GoldTier write needs four things in order. First, a leased claim on the case document. Second, a durable modifying conditional write on the workflow definition document that succeeds only while the evaluated version is still active; this is the linearisation point, and its anonymous counter is not dispatch evidence. Third, a leased, token-bound authorisation on the case document. Fourth, a durably acknowledged write attempt marker. Every writer of the case snapshot and the workflow definition documents matches both the revision and the per-write nonce it read, and sets a new nonce. Ledger and fence writes also assert their predicate (own token, state, no marker for the operation) in the write filter. A reused revision number therefore never matches another history. Ambiguous outcomes never authorise a GoldTier call, and a modified-document count never does either. Only a durably acknowledged post-image of the same write, showing the worker's own write attempt marker and receipt, does. The lease condition governs the marker, nonce and revision atomically, and the fence fails closed if the database cannot guarantee that. Expired leases never authorise the replay of an attempted write. A newly published requirement holds every case not yet authorised; a confirmed one must then re-confirm the dispatch (RD-3). A case is **sent** when it has a SHELL, POLICY or AMEND write attempt marker, a retained target outcome or receipt, or automation COMPLETE. |
| G10 | **Storage guarantees.** Supported MongoDB topologies are a standalone server with journaling (staging, to be confirmed in P2-0) or a replica-set primary. Safety-critical writes use `w: "majority", j: true` with a `wtimeout`, and count only when durably acknowledged. No read concern is relied on, and majority reads are not treated as linearizable. An unsupported topology or an unavailable guarantee refuses dispatches and governance writes. |
| G11 | **History.** Governance history is never silently deleted. The archive's content is insert-only; the only permitted exceptions are one `archive_confirmations` marker field and attempt-suffixed re-inserts. It is fed by a crash-safe, idempotent outbox, and records leave the outbox only after a durably acknowledged archived copy exists. Byte limits are enforced, and RD-5 counts are maxima (owner-approved 2026-11-16) within them. Version numbers stay monotonic after archival. Unacknowledged notices are never discarded. Referenced versions stay readable. |
| G12 | **Legacy send routes.** The legacy CLM target-confirmation route, which has no frontend caller, is retired. Legacy `/submit` becomes recovery-only, accepted under the full D-136 E3 predicate (a recorded write attempt, or a retained target outcome or receipt). Both are gated on a caller inventory and a read-only staging count. |
| G13 | **Deactivation and reactivation** (non-onboarding only). Deactivation stops new runs and never modifies an existing run; existing runs stay completable. It is refused while any run is inside a required-stage confirmation (one shared gate lock). Reactivation must satisfy the kept baseline. |
| G14 | **P2-0 transition.** P2-0 freezes legacy activation at the backend, backfills top-level `active_version` and `latest_version` in a one-time reviewed, idempotent, verified backfill (never reused after P2-1), provisions the onboarding definition document at startup, corrects the ledger repository's compare-and-set, and keeps every existing D-136 safeguard throughout. Conditional steps get their own phase and ADR: deterministic, add-only and fail closed. Added steps keep blocking only the final send. The staging inventory and migration are future, separately approved gates. |
| G15 | **D-136 E2 amendment, effective with P2-0.** No active version still holds nothing. A **missing expected onboarding definition document** is refused, because a provisioning or backfill gap is treated as unavailability. This is a deliberate fail-closed narrowing. |

**Out of scope:**
- reordering mandatory stages
- engine pauses
- multi-instance runtime
- any new registry or country
- autonomous approval
- AI-authored workflows
- AWS changes

## D-137 - GoldTier Sandbox write qualification: one bounded write window, disabled by default (OWNER-APPROVED 2026-11-15, NOT ACTIVE)

Status: owner-approved on 2026-11-15 as the controlled GoldTier Sandbox write capability for
the FYP staging environment. Authority: `USER_AUTHORIZED_POC`. **Not active and not
sponsor-confirmed. It authorises no Sandbox write:** the deployment and each write window
are authorised separately. Numbering: D-133 to D-135 are held by open proposals. It narrows
D-126 P1. All other D-126 rows stand. It also leaves D-131 (R3 egress) and D-136 (workflow
send hold) unchanged.

D-126 open items, as decided by the owner on 2026-11-15:
- Item 2 (Sandbox prior-case ledger proof) is closed by W6.
- Items 1 (paused-state wording), 3 (stale `initial_target_search` read model after a void) and
  4 (the read-only recovery exception for `check_uncertain_target_status` and
  `verify_completed_target`) are accepted under the stated staging limitations. Item 4 keeps
  the exception: one read-only Search, bound to the case's own ledger entry.
- Related-party Policy and Amend stay blocked (`BLOCKED_CHILD_ID_LIFECYCLE`, Q-006 open) until
  the `childId` contract is established from existing evidence or authoritative documentation.

| # | Decision |
|---|---|
| W1 | **One window, four parts.** In staging, a Sandbox write needs all four: `GOLDTIER_SANDBOX_ALLOW_WRITES=true`; `GOLDTIER_SANDBOX_WRITE_OPERATIONS`, set explicitly (a subset of `SHELL`, `POLICY`, `AMEND`); `GOLDTIER_SANDBOX_WRITE_CASE_REFERENCES`, 1 to 10 exact `source_case_id` values; and `GOLDTIER_SANDBOX_WRITES_NOT_AFTER`, a time-zoned end no more than 24 hours after startup. A missing or malformed part refuses startup. Related-party operations are not admitted. Outside staging, the plain switch behaves exactly as before. |
| W2 | **Default off.** Every default keeps writes off. In addition, `deploy/compose.yml` and `deploy/compose.goldtier-egress.yml` pin `GOLDTIER_SANDBOX_ALLOW_WRITES: "false"` in the backend environment. Opening a window on the host therefore also needs the window overlay `deploy/compose.goldtier-write-window.yml`, applied only for that window with the `dcgw` helper. That overlay changes only these four backend values; its three window values are required and come from a separate window env file, never from `compose.env`. Closing the window recreates the backend through `dcg`, which restores the literal `"false"`. |
| W3 | **Checked before the ledger.** The window is checked before any confirmation is recorded and before the ledger marks an attempt. That covers the two orchestration send checks and every incremental Shell, Policy and Amend step. The legacy one-shot path cannot pause between steps, so it starts only when the window admits all three operations for the case. An unlisted case is refused with `CLM_TARGET_WRITES_DISABLED`; nothing is recorded or burned and no request leaves. The connector repeats the case and operation check as defence in depth. It does not repeat the end-time check, so an expiry between the two checks can never become a burned, failed operation. |
| W4 | **Ending is a pause, not a failure.** When the window ends, or the next operation is outside it, the next mutation is refused and the submission pauses in `RECOVERY_PENDING`, exactly as in D-126 P1. The same submission resumes without replay in a later window. Search, exact-ID readback, recheck and uncertain-outcome reconciliation stay read-only and are never limited by the window. A window that has already ended is accepted at startup, so a restart never takes the site down; it simply keeps writes off. An empty end-time variable means no end time in every environment, so staging still refuses it. |
| W5 | **Unchanged.** The target ledger, idempotency keys, no-replay, uncertain-outcome handling, D-126 P2 evidence binding (only official Marketplace Mock identities reach Sandbox), RM and HR/Director governance, D-136 and backend-only credentials. The HR console status now reports the live window. |
| W6 | **Prior-case reuse needs ledger proof in every mode** (closes D-126 open item 2). Sandbox previously reused a prior case on accepted evidence alone. Now a prior case is reused only when it holds a finalized, read-back-verified ledger entry for the *current* provider mode, bound to that case and party. That is the same proof Mock already required. Otherwise the case follows the normal Search outcome. |

Before any window is opened, all of the following are required:
- the read-only A7 proof succeeds;
- the sponsor's written write permission and the exact test operation and case are recorded;
- every listed case is a synthetic test case whose identity is official Marketplace Mock evidence;
- the D-126 open items are closed or owner-accepted (paused-state wording, Sandbox prior-case ledger proof, the
  stale `initial_target_search` read model after a void, the recovery exception);
- the reviewed compose change for the window;
- explicit owner authorisation for that window;
- a closing step: the backend is recreated through `dcg` without the window overlay (restoring
  `"false"`), the window env file is removed, and each write's ledger outcome and readback are
  recorded.

## D-134 - Hosted model registry: GPT-OSS 120B as a second independently qualified hosted model, with a hard US$3.00 daily ceiling (PROPOSED, NOT ACTIVE)

Status: `PROPOSED`. Local candidate only, mocked providers only, **not independently reviewed**. Nothing here is active: the hosted OpenRouter mode does not exist in the shipped code (`config.HOSTED_OPENROUTER_DECISION = None`, and `assistant_hosting/provider.py` records no pinned address range for `openrouter.ai`). No data was sent to any provider, no key was entered, no paid call was made and no egress file was changed. The owner approved OpenRouter `openai/gpt-oss-120b` for local adapter engineering and mocked tests only. What the owner must approve before any real use is in `outputs/gptoss-registry-20261114/OPENROUTER_RECIPIENT_AND_EGRESS_DECISION.md` (not tracked). D-133 is reserved by the pending eligibility provenance proposal, so this is D-134.

Unchanged: D-091 to D-098 and D-118 on a development machine (decision names, attestations, preflight, per-call verification, ledger, session allowance, the per-session chat-call count); D-099, D-102, D-106, D-107 and D-110 for Claude (US$30.00 lifetime ceiling, US$5.00 daily ceiling, 20 chat calls a session); D-129 and D-130 (hosted Claude and its four chat paths); the dashboard-insights limits; D-132 (case eligibility); RBAC, the safe `404`, provenance and audit. D-098 decision 6a already keeps one active model and never replaces it automatically; that is the no-fallback rule this decision relies on.

| # | Proposal |
| --- | --- |
| M1 | **A closed set of hosted provider modes.** `ASSISTANT_HOSTING_PROVIDER` names `anthropic`, `openrouter`, or both separated by a comma. Any other value, a repeated name or an empty part refuses the start (`PROVIDER_MODE_INVALID`). While `config.HOSTED_OPENROUTER_DECISION` is `None` the name `openrouter` is not a known mode at all, so today's behaviour is unchanged. The Anthropic mode's checks are the same conditions as before, and its existing tests pass unchanged |
| M2 | **The OpenRouter mode starts only when fully configured.** Required, each with its own closed refusal code: the owner's hosted daily ceiling `ASSISTANT_HOSTING_GPTOSS_DAILY_CAP_MICRO_USD` (1 to 3,000,000); exactly one HTTPS origin; the whole remote profile named exactly (D-091, D-092, D-094, the two owner attestations, the approved endpoint `deepinfra/bf16`, valid reasoning settings); and `openrouter.ai` resolving only inside a pinned range recorded in the code. That range is empty, so the mode cannot start until a reviewed change supplies one or replaces the check with the exact-host proxy check. Every other remote, Anthropic, key, proxy and `.env` refusal still applies in this mode |
| M3 | **One active model, independently qualified, no fallback.** GPT-OSS is selected in the existing AI Models console like any model. It is usable only with its own passing qualification for its current configuration fingerprint and the current qualification basis. Naming both modes never joins them: each keeps its own adapter, key, ledger, limits and qualification. On failure, refusal, a limit or an outage the answer is the existing case-data answer. Nothing calls the other provider |
| M4 | **Scope: the case chat only.** Hosted GPT-OSS answers the case chat of an approved case (D-132), under D-122. The general chat, Support's chat, "Try with this change" and dashboard insights stay as they are (hosted Claude only where D-130 allows; otherwise no model) |
| M5 | **No user identifier in a hosted GPT-OSS prompt.** The D-130 OD-G8 rule (`provider_payload.py`) applies to hosted GPT-OSS as to Claude: the viewer is reduced to the role, and the user id and display name are removed from the written turns |
| B1 | **A hard daily ceiling in the ledger.** The hosting layer registers the ceiling once per process (`budget.register_daily_ceiling`, at most US$3.00, never replaced or raised). Every admission of an OpenRouter-profile ledger in that process then needs: charges of calls closed since the last Singapore midnight + the reservations of all open calls + this call's reservation times its attempts <= min(configured daily cap, ceiling), inside the same `BEGIN IMMEDIATE` transaction as the lifetime, session and one-at-a-time checks. An uncertain outcome is charged its whole reservation, as before. The Anthropic ledger has no such ceiling |
| B2 | **HR may lower, never raise above the ceiling.** `PUT /budget/controls` refuses a daily limit above the ceiling (`DAILY_CEILING_EXCEEDED`, audited); a stored or configured value above it is never applied |
| B3 | **The fixed chat-call count is replaced by the budget rule on the hosted deployment only.** There the per-session chat-call count (D-096, D-118) is not applied. The daily ceiling, the US$5.00 session allowance, the lifetime cap, the per-call token caps and one paid call at a time remain. A per-user request rate is added in the chat: 6 requests a minute, and per hour one quarter of the calls a worst-case day admits (ceiling // worst-case reservation // 4 = 3,000,000 // 21,278 // 4 = 35). Over the rate, nothing is sent or reserved and the answer is the case-data one. The rate numbers are a proposal for the owner to confirm; the minute figure is an engineering figure, not a cost figure |
| C1 | **Console.** The existing GPT-OSS spending view also reports the ceiling, an exhausted day and that no call count applies. It already showed settled today, in flight, remaining today and the next reset (00:00 Asia/Singapore) |
| Q1 | **Conversation quality, one bounded change.** A request to be told something that only starts with a change verb ("Update me on this case", "Confirm whether the UBO check has run") no longer gets the fixed "I can't make that change" reply. Every request to change, approve, submit or record something still gets it, including one placed behind an informational opening. The scope gate is not changed; its rigidity is recorded as a proposal only |

Owner decisions open before any real use (O-1 to O-9 in the decision paper): the two recipients and the data sent; the egress restriction (no published fixed address range for `openrouter.ai` is recorded in this repository, and none was looked up); key handling; the hosted daily ceiling value; whether the ceiling should also apply on development machines; the rate numbers; the paid requalification; the user notice; activation.

Side effect: `budget.py`, `config.py`, `copilot.py`, `main.py`, `provider_payload.py`, `remote_test.py` and the new `request_rate.py` are model-qualification basis files, so the basis changes from the c2r1 candidate's to `c834755ab5cf0646482638de034ce635d735e4736e50b2e4ad14f58f4ff3f317`. Every earlier Claude or GPT-OSS qualification is out of date on a checkout with this change and must be repeated before activation. The synthetic boundary file is unchanged. (Superseded by D-138 on its candidate: the basis there is `06f0b36248260c7f7da7726d18d1b4664b8da65aad5371d56d7df0c9f0732fcb` and the boundary file gains six benign words.)

## D-138 - Real-inference controls: a D-129 code gate on every hosted provider mode and a standing US$3.00 GPT-OSS day on every deployment (PROPOSED, owner-directed 2026-11-15; renumbered from D-137, which is reserved for GoldTier writes)

Status: `PROPOSED`. Local candidate only, mocked providers only, not yet independently reviewed.
Owner directive 2026-11-15 ("PROCEED - REAL CLAUDE AND GPT-OSS INFERENCE"), carried on the D-134
candidate. Not sponsor-confirmed; no provider status changes (nothing is Live).

| # | Rule |
|---|---|
| R1 | `config.HOSTED_TRANSMISSION_DECISION` records the owner's acceptance of D-129. It ships as `None`: every hosted provider mode (Anthropic and OpenRouter) refuses the start with `TRANSMISSION_DECISION_REQUIRED`, and both hosted runtimes refuse a registration, so no case content can leave the hosted service. It is set only in a reviewed change that records the acceptance, never by a setting. The model-free hosted service is unaffected |
| R2 | The GPT-OSS ledger profile has a standing hard ceiling of US$3.00 per Singapore calendar day on every deployment, development machines included (`budget.STANDING_DAILY_CEILINGS`). A deployment may register only a lower one. Admission counts settled spend today, every open reservation and this call's worst case times its attempts, in one `BEGIN IMMEDIATE` transaction (D-134), so on one ledger file concurrency, retries, restarts and a second process cannot exceed it (two launchers with different `BUDGET_LEDGER_PATH` values, or a ledger replaced mid-day by the owner, each count their own day; the provider key's own daily limit is the backstop). HR may lower the daily limit, never raise it above US$3.00. This supersedes D-134's hosted-only scope (its question O-6) and D-098's unbounded daily value for GPT-OSS |
| R3 | Unchanged and re-asserted by tests: the model can neither change a case nor move money. The CLM backend client sends GET requests only, and no model request offers tools or functions. D-132's case gate, H5 permissions, team scope, the safe `404`, deterministic refusals and the model-free case-data fallback are unchanged. Claude's limits (D-102 US$30.00 lifetime ceiling, US$5.00 daily ceiling, at most 20 calls, the hosted lifetime ceiling) are unchanged |
| R4 | **Spending-store health (owner request 2026-11-15).** A hosted provider mode starts only when each named provider's D-118 session store is usable or absent. The check is read-only (`assistant_hosting/ledger_health.py`, in `profile.refusals`): it never creates, recovers, migrates or resets a store. Absent is a genuine first start, and the store is created on first use by the existing guarded action (Enable Claude, or the first passing GPT-OSS Test Connection), because its cap needs HR's confirmed workspace limit. A store absent although the append-only model-admin audit shows a passed connection test for that provider is `LEDGER_MISSING_AFTER_USE`, which blocks, so a vanished store is never silently replaced at zero. Blocking codes (unwritable folder or file, corrupt, inconsistent, format-1 `LEGACY_STORE`, unsupported schema, another provider's store, unreadable) refuse the start with exit 78. An open breaker, an open call or an HR reconciliation marker is reported, never blocking. `python -m assistant_hosting.ledger_health` gives the operator the same report. Every code's recovery is in `apps/assistant/deploy/LEDGER_RECOVERY.md`, and none edits a database file. A damaged or missing store is restored alone, never the whole volume, then reconciled against the provider's own usage before paid calls resume. The image now carries `scripts/budget_ledger.py` and `scripts/storage/archive_accounting_stores.py`, so those commands run in a one-off container. The console now shows the store's own refusal behind a failed `ledger.healthy` check. Not a qualification-basis change |

On a development machine D-104 and D-095 continue to govern what may be sent (owner attestations and the
verified-synthetic eligibility check); D-129 governs the hosted service. Setting R1's constant changes
`config.py`, a qualification basis file, so the paid qualification must run after it.

### D-138 amendment A1 - Hosted GPT-OSS egress through an exact-host proxy, a provider-scoped transmission gate and a provider-naming notice (PROPOSED, local candidate 2026-11-15)

Status: `PROPOSED`. Local engineering only: mocked providers, static and unit evidence, no VM
harness run, not installed, not deployed, nothing activated. Not sponsor-confirmed; no provider
status changes (nothing is Live). Owner direction 2026-11-15: both Claude and GPT-OSS-120B on the
AWS staging assistant through AI Models, interchangeable, with every existing control kept. It
implements the design in `outputs/real-inference-20261115/OWNER_APPROVAL_PACKAGE.md` §4.2. D-139 is
not used.

| # | Rule |
|---|---|
| A1-R1 | **No address pin for OpenRouter.** OpenRouter publishes no fixed inbound range, and Cloudflare's ranges would admit any Cloudflare-fronted site, so D-134's empty `OPENROUTER_INBOUND_V4` and `OPENROUTER_PIN_REQUIRED` are removed. For the OpenRouter mode only, the start-up check is instead: `ASSISTANT_HOSTING_OPENROUTER_PROXY` exactly `http://<IPv4 inside 172.30.246.0/29>:4750`, never the network, gateway or broadcast address (`OPENROUTER_PROXY_REQUIRED`); the kernel reaches that address directly from another address on that network (`OPENROUTER_PROXY_NOT_INTERNAL`); and `openrouter.ai` does not resolve inside the container (`OPENROUTER_DIRECT_PATH_REFUSED`). Codes stay closed, exit 78, no value printed. The Anthropic mode and its E1 pin are unchanged |
| A1-R2 | **The client's one proxy.** `openrouter.register_hosted_proxy` is called by the hosting layer before the hosted deployment registers, once, with the same value only, and only while `HOSTED_OPENROUTER_DECISION`, `HOSTED_TRANSMISSION_DECISION` and `HOSTED_OPENROUTER_TRANSMISSION_DECISION` are all set. Then, and only then, every live OpenRouter request (chat, stream, account checks, public listing) uses that proxy (`CONNECT openrouter.ai:443`), with certificates verified for `openrouter.ai` (certifi, host name checked), `trust_env=False` on client and transport (no proxy variable, `.netrc` or certificate override is read) and no retries or fallback. Mock transports are never replaced. `harden` refuses a registration that differs from the configuration |
| A1-R3 | **The egress lane** (`apps/assistant/deploy/egress/`, `compose.assistant-openrouter.yml`, `compose.assistant-both.yml`). The assistant joins only the internal `clm-ao-ctl` network on top of Stage A's. A proxy container (R3's reviewed Smokescreen build and exact-head entrypoint, unchanged, same pins) admits only `CONNECT openrouter.ai:443 HTTP/1.1` from the assistant's address; an exact-name resolver forwards only `openrouter.ai. IN A`. Both run under `openrouter_egress_guard.py` (R3's guard adapted: fixed FQDN, no destination pin, its own addresses). Host table `inet clm_r22o` lets only the proxy reach a public IPv4 on tcp/443 and the resolver the VPC resolver on 53; Docker does not masquerade the uplink; boot and table or watcher loss fail closed as E1 (restart `no`, start gate `clm-r22o-egress.service`, watcher). E1 `inet clm_r22` and R3 `inet clm_r3` are unchanged. Residual (PROPOSED for the owner to accept, not accepted): the proxy relays an opaque TLS tunnel to whatever public IPv4 the VPC resolver returns for `openrouter.ai` and cannot enforce the TLS server name inside it. The reviewed client verifies the `openrouter.ai` certificate, but a buggy or compromised assistant process could reach other sites on the same Cloudflare edge through that tunnel (domain fronting) |
| A1-R4 | **A provider-scoped transmission gate.** The owner accepted D-129 for Anthropic only (2026-11-15). `config.HOSTED_OPENROUTER_TRANSMISSION_DECISION` (ships `None`) records OpenRouter's own transmission acceptance (a D-129 amendment for OpenRouter). While it is `None` the OpenRouter mode refuses the start (`OPENROUTER_TRANSMISSION_DECISION_REQUIRED`) and `remote_test` and `openrouter` refuse a hosted registration, even with `HOSTED_TRANSMISSION_DECISION = "D-129"`. The Anthropic path is unchanged when D-129 is recorded |
| A1-R5 | **The notice names the provider that can serve.** The hosted guard adds `external_ai` (registered providers, the active model's provider class and each provider's surfaces, from code constants) to `GET /assistant/health` and to a successful `GET .../cases/<id>/brief`; any other reply passes through byte for byte. `ExternalAiNotice` names Anthropic for Claude, OpenRouter (routed to the one approved GPT-OSS-120B endpoint) for GPT-OSS on the case chat, and both providers whenever both may serve the surface (the active model never narrows it, because HR can switch it while a chat is open); with no report it keeps the Anthropic wording. Display data only: no frontend authorisation, the notice is always shown on the five surfaces |
| A1-R6 | **Subnet move (owner-approved 2026-11-15, OI-1).** A1's `openrouter-control` and `openrouter-uplink` move from 172.30.244.0/29 and 172.30.245.0/29, which equal the ACRA window lane's `acra-uplink` and `acra-control`, to **172.30.246.0/29** and **172.30.247.0/29**. The move covers `openrouter.HOSTED_PROXY_NETWORK`, the overlay, `clm_r22o.vars` and `.nft`, the guard, the verify script, the README and the tests. A test now fails if any A1 network overlaps a subnet declared in the repository's compose files or a recorded host network (ACRA 244/245, R2.2 243, A6 probe 249, VPC 172.26.0.0/16). Not a qualification-basis change. The AWS host operator re-checks that 246 and 247 are free on the live host before any A1 install |

Unchanged: D-138 R1 to R3 (the D-129 code gate, the standing US$3.00 GPT-OSS Singapore day,
GET-only backend client, no tools in any model request); D-132's case gate (a temporary
qualification restriction in the owner's words of 2026-11-15, not the final staging product
requirement; not changed here); H5 RBAC and team scope; the safe `404`; deterministic refusals;
the model-free fallback; every cost limit; the agent framework. `HOSTED_OPENROUTER_DECISION`
and `HOSTED_TRANSMISSION_DECISION` stay `None`.

Side effect: `remote_checks.py`, `remote_test.py` and `config.py` are qualification basis files
(the public listing must use the proxy; the registration and the constant carry A1-R4), so the
basis changes from `06f0b36248260c7f7da7726d18d1b4664b8da65aad5371d56d7df0c9f0732fcb` to
`b4fee54456c35755cafb591bbcee261fcca4476866830efaaaf7a21462154860`. A qualification made against the earlier basis is out of date on a checkout with this
change. The synthetic boundary file is unchanged.

Before activation: the owner's OpenRouter transmission acceptance and `HOSTED_OPENROUTER_DECISION`
in a reviewed change; the owner's acceptance of the A1-R3 residual; the D-134 owner questions O-1 to O-10; an independent QG of this delta; the
E1-style VM matrices (connectivity, robustness, boot) for this lane; the AWS host operator's
preflight and install; the paid requalification.

## D-139 - Hosted assistant: model-free guidance for every authorised case, external inference by each provider's data-handling policy (PROPOSED; architectural direction owner-approved 2026-11-15)

Status: `PROPOSED`. Local candidate only, mocked providers only. The owner approved the direction on 2026-11-15:
- model-free assistance for every case the user is authorised to access;
- external inference evaluated separately for each provider;
- Marketplace Mock cases supported once they satisfy the policy;
- the allowlist and cutoff retired once the replacement is qualified;
- D-133 closed as superseded when D-139 is adopted.

Not sponsor-confirmed. No provider status changes, and nothing is Live. It supersedes D-132 (RD-1) on the hosted service.

| # | Rule |
|---|---|
| R1 | **Guidance.** The hosted assistant's model-free, deterministic answers serve every case the backend lets the signed-in user read. The backend's RBAC, team scope, `401` and safe `404` decide. The `403 ASSISTANT_CASE_NOT_ELIGIBLE` refusal and the case list are removed |
| R2 | **External inference, per answer and per provider.** A case's content goes to an external provider only when this answer's exact messages pass that provider's data-handling policy, checked before any call or reservation in `remote_gate` (case chat) and in Try with this change. Otherwise the answer comes from the case data, with a notice naming the provider and a closed reason code. Each refusal is counted by reason, with the case reference only |
| R3 | **The hosted policy, for Claude (D-129) and GPT-OSS (its amendment): verified synthetic data, by provenance.** This is the reviewed D-095 check (`synthetic_eligibility.check`), now on the hosted service. A case passes only when all of these hold:<br>• an approved synthetic company from ACRA in MOCK mode;<br>• every document a tracked synthetic fixture, by the backend's own digest;<br>• typed values grounded in those sources;<br>• a seeded viewer;<br>• approved knowledge only;<br>• a screened question.<br>A Mock ACRA or Marketplace Mock case passes once its data is eligible. On Try with this change only, the viewer rule is not applied: D-130 decides who may ask (the Support capability and team scope), and OD-G8 removes the viewer from the prompt. Every other rule applies |
| R4 | **Retired settings.** `ASSISTANT_HOSTING_ELIGIBLE_CASE_REFS` and `ASSISTANT_HOSTING_ELIGIBLE_CREATED_BEFORE` are retired. A service that still has either one refuses to start (`CASE_ALLOWLIST_RETIRED`, exit 78), so nobody believes a list still applies. A rollback to the H5 image restores them |
| R5 | **The fifth path (dashboard insights) admits no case** under this policy. It reads many cases at once and has no per-answer check. It stays off (`HOSTED_INSIGHTS_DECISION` is None, and the guard refuses the route), and enabling it needs its own eligibility design |

Unchanged:
- D-129's payload inventory, the OD-G8 identity rule and the spending limits;
- the D-138 read-only reach, the US$3.00 GPT-OSS day and the transmission gate;
- every deterministic refusal and the model-free fallback.

Owner confirmation needed at adoption. D-129 term (b) said "eligible synthetic cases" under the R2.1 list; under D-139 it means cases that pass the R3 check.

Side effect: `main.py` and `synthetic_eligibility.py` are qualification-basis files. The qualification basis changes, so the hosted 5-call qualification runs on the integrated image.

## ST-7 amendment - GoldTier Sandbox daily reads (owner-directed C9)

| Decision | Owner scope |
|---|---|
| No application-imposed daily read quota by default. Provider limits apply. | All environments. An explicit limit from 0 to 500 still applies when configured. D-137 continues to govern writes. |

## D-140 - HR password management for non-HR accounts (owner-directed, awaiting review)

The owner asked for HR password management on the deployed site using the smallest compatible change. HR could create users with a temporary password but could not reset one.

| # | Rule |
|---|---|
| P1 | **Route.** `POST /api/admin/profiles/{user_id}/password` takes `{expected_version, new_password}`. The password is 12 to 128 characters and is a `SecretStr`: it is never echoed, logged, stored, audited or returned. The response is the usual `AdminProfileResponse`. |
| P2 | **Access.** The route is `ACTOR_ONLY` with CSRF, like the other admin routes. The service requires `IDENTITY_ADMIN` (403 `ADMINISTRATION_FORBIDDEN` otherwise). The store reauthorizes the actor inside its lock, so an actor who loses HR after sign-in is refused. `ROLE_CAPABILITIES` is unchanged, and HR still has no case or dashboard access. |
| P3 | **Targets.** HR accounts are refused, including the actor's own (403). The `hr-admin` credential stays owner-managed. An unknown user gives 404. |
| P4 | **Store.** Both stores gain `replace_credential`. It does a compare-and-set on `version` (Mongo also matches `security_version`), sets a new scrypt hash from `generate_scrypt_password_hash`, and increments `version` and `security_version`. A stale version gives 409. The existing `update()` credential guard is unchanged. |
| P5 | **Sessions.** The `security_version` bump revokes every existing session of the target on its next request. The service also drops the session directly. |
| P6 | **Audit and rollback.** Both operations append the existing `PROFILE_UPDATED` event with actor, target, timestamp, resulting version, and metadata `{operation, previous_version, resulting_access_epoch}`. The operation is `PASSWORD_RESET` or `SIGN_IN_DISABLED`. Neither plaintext nor hashes enter audit metadata. Older images can decode the records. |
| P7 | **UI.** Each non-HR row in Users offers password reset. Active rows also offer confirmation before disabling sign-in. Disabled rows show their status and can be re-enabled by password reset. The two password fields clear on submission or cancellation. Version conflicts refresh the list and require a new submission. |
| P8 | **Disable (SF-006).** `POST /api/admin/profiles/{user_id}/disable` takes `{expected_version}` and uses the same access, CAS and session revocation as reset. It replaces the stored hash with the hash of a discarded random value. `AdminProfileResponse.sign_in_disabled` is derived from the latest credential operation. The profile must be reset before it can become HR so a disabled account cannot count toward the last-HR invariant or become ineligible for reset. |

Unchanged: password hashing, session validation, RBAC, the last-HR and self-demotion rules, the Mongo schema (no new fields), and every other admin route.

### C9 amendment to D-140

An authenticated HR actor may change their own password through `POST /api/admin/me/password`.
The service verifies the current password. The store rechecks HR authority and the session's
security version, then applies the existing credential CAS. The security version increments
and requires a new sign-in. The existing `PROFILE_UPDATED` action records
`PASSWORD_CHANGED_SELF` in operation metadata. Administrative reset and sign-in disabling
continue to apply only to non-HR target accounts.

## D-129A - Hosted GPT-OSS-120B (OpenRouter) data transmission and the A1-R3 residual (ACCEPTED 2026-11-16 by the owner)

Status: `ACCEPTED` on 2026-11-16 by the owner (in chat: "Signing it now", after G-6 passed in run 272fc723). The signed text is in `outputs/real-inference-20261115/OPENROUTER_OWNER_DECISION.md`.
It extends D-129 to OpenRouter for GPT-OSS-120B, under the same synthetic-only data categories and D-139 provider policy.
It also accepts D-138 A1-R3: the CONNECT proxy admits only `openrouter.ai:443` but cannot inspect TLS.

Recorded in code as `HOSTED_OPENROUTER_TRANSMISSION_DECISION = "D-129A"` and `HOSTED_OPENROUTER_DECISION = "D-134"`.
The OpenRouter mode still starts only with all of these in place:
- its daily cap (at most US$3.00 per Singapore day);
- the registered egress proxy on 172.30.246.0/29;
- the exact remote settings;
- the host's `clm_r22o` install.

`config.py` is a qualification-basis file. Every GPT-OSS and Claude qualification must run on the resulting fingerprint.

## SF-002 amendment - Worker memory cap platforms (security patch #188; needs owner acceptance)

The worker memory cap applies on Linux, where the worker is deployed; it is skipped on Windows and macOS development machines.

## D-141 - An advisory ownership review is shown as "Review advised", not green "Complete" (PROPOSED 2026-11-15; amends D-121 display only)

Status: proposed by Tasha on 2026-11-15; needs Shane's acceptance. Authority: `USER_AUTHORIZED_POC`.
Evidence class: Mock. It amends the D-121 presentation only. No status, readiness rule, audit
code or switch changes.

| # | Decision |
| --- | --- |
| A1 | **Problem.** Under D-121 a current `REVIEW_REQUIRED` analysis that `review_is_advisory` clears makes ownership readiness `READY`, so the `OWNERSHIP_UBO` node is `COMPLETE` and showed a green "Complete" chip beside "Ownership: REVIEW REQUIRED". |
| A2 | **Signal.** `BrowserProcessingNode.advisory_review` (optional, default `None`) is `true` only on `OWNERSHIP_UBO`, only when the case-detail endpoint finds the current record advisory (`review_is_advisory`) and not POC-accepted (`poc_basis_accepted`), and only when the node is `COMPLETE` with readiness referencing that same `analysis_id`. Blocking mode, an accepted basis, a failed, stale or superseded analysis and a lane that does not qualify all give `None`. |
| A3 | **Display.** The frontend shows that node as amber "Review advised" (stage header chip, sidebar marker and progress tile, each with the words, not colour alone), with the subtitle "Not blocking. Review ownership before Review & Send." Green "Complete" appears only when there is no open review. Blocking mode keeps the red "Review required". The partnership "awaiting RM confirmation" banner and the Review & Send ownership warning are unchanged. |
| A4 | **AI Assistant.** It reads the same pipeline, so it follows the same flag: the step is "review advised" (not "done", and not counted as done), readiness reports ownership as `REVIEW_ADVISED` (counted as incomplete in `_OWNERSHIP_INCOMPLETE`), and the briefing adds one catalog line, offered only in that state: "The ownership review is advised but not blocking: the case can continue, but ownership is not verified. Check it before Review & Send." A model sentence saying ownership or the UBO check is complete is dropped unless ownership readiness is `READY` (exact-line mode already drops it as off-catalog; copilot mode now leaves it out as `unsupported_status`). A confirmed case is unchanged. |
| A5 | **Unchanged.** D-121 U1 to U5 and D-124 stand: node status, readiness, `poc_basis_accepted`, the `OWNERSHIP_REVIEW_ADVISORY` audit code and the `blocking` rollback. |

## D-143 - Specific, plain reasons when an upload fails the local document checks (PROPOSED, 2026-11-16)

Status: `PROPOSED`. Needs Shane's acceptance. Every limit and rule is unchanged; only the reason reaches the RM.

Problem: the isolated worker rejected for a specific reason, but the runtime mapped every reason to `DOCUMENT_STRUCTURE_INVALID` and one fixed sentence. A Tableau "Save as PDF" with hyperlinks showed "could not pass the bounded local structure checks", and "Try upload again" re-sent the same file.

| # | Rule |
|---|---|
| R1 | **Fixed reasons only.** The worker (`local_document_worker.py`) reports a rejection only as a fixed exit code: 10 `TOO_MANY_PAGES`, 11 `ENCRYPTED`, 12 `ACTIVE_CONTENT` (the `_UNSAFE_PDF_KEYS` and `/F` filespec rule), 13 `PAGE_TOO_LARGE` (dimension, per-page pixels or Pillow's pixel guard), 14 `CONTENT_TOO_LARGE` (total pixels or text). Everything else stays exit 2 (`DOCUMENT_STRUCTURE_INVALID`). No document content, file name, object id or library text leaves the child. Exit codes 0, 1 and 2 and negative (signal) codes are not reused |
| R2 | **API codes.** The runtime maps those to `DOCUMENT_TOO_MANY_PAGES`, `DOCUMENT_ENCRYPTED`, `DOCUMENT_ACTIVE_CONTENT`, `DOCUMENT_PAGE_TOO_LARGE`, `DOCUMENT_CONTENT_TOO_LARGE`. Any unmapped non-zero exit falls back to `DOCUMENT_STRUCTURE_INVALID`. `DOCUMENT_TOO_LARGE` is not reused: it already means over the 5 MB upload limit (HTTP 413) |
| R3 | **Wording.** One backend table (`document_errors.DOCUMENT_REJECTION_MESSAGES`) gives each code a plain message with a next step, including `DOCUMENT_PROCESSING_TIMEOUT` and `DOCUMENT_RUNTIME_UNAVAILABLE` (codes and retry unchanged). A malformed file at upload says "This file isn't a readable PDF or image…" |
| R4 | **Banner.** The case page shows the plain message; the case ID, retry wording and code move into a collapsed Technical details. When every failed file was rejected for its own content before storage, the action is **Choose a different file**: the existing Discard, then focus on the case's existing "Upload required document". No new retry or replace path, and the "retry the same selection" guard is unchanged. Timeouts, runtime-unavailable and stored failed documents keep **Try upload again** |

Unchanged: every page, size, pixel, text and active-content limit; accepted file types and sizes; the wrong-document warning (#135); the stored-document retry and replace flow.
