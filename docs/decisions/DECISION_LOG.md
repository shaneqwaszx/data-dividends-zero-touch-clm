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
  it is held by the next analysis and drops out one change later;
- the separate target-dispatch confirmation required before any GoldTier target mutation.
  GoldTier Search runs earlier and is read-only.

An incomplete replacement still requires review. No runtime behavior changed.

Narrowed by D-081 (owner F1 decision, 2026-10-24) for POC-assumed equal-unit links only:
`CURRENT_EVIDENCE` cannot keep them, and a declaration cannot redeclare them unchanged.

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
  - `USER_SUPPLIED_DECLARATION` would redeclare any POC-assumed link unchanged (same parent,
    holder and percentage).

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

## D-099 - Support role: knowledge review moves from Directors to a Support tab, with read-only policy (OWNER-DIRECTED, local POC scope)

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
| S4 | **Redaction read.** Writing a fix redacts it against the request's case, loaded with the reviewer's own session. `KNOWLEDGE_CASE_READ` admits a team-less holder to exactly two GET routes, `/api/clm/zero-touch/cases/{case_id}` and `/api/onboarding/cases/{case_id}/documents` (route access `CASE_READ`), for any case. It grants no portfolio listing, no other case route (those answer as absent, 404), no mutation and no evidence-decision authority; the frontend shows Support no case pages. |
| S5 | **Frontend.** Knowledge review is the **Knowledge Review** tab (`/knowledge-review`, gated on `KNOWLEDGE_REVIEW`, Support's landing page) rendered as a page; the AI Assistant panel no longer opens it. Support's **Policy** tab is the existing read-only rendering for `POLICY_VIEW` holders (no propose, reset or decide controls). |

Not decided here: sponsor reviewer policy (Q-014); a second Support reviewer for retirement;
any change to knowledge content rules, redaction or the exact-line guard.
