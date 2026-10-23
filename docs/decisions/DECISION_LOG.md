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
