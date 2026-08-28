# 1. Executive Summary

The bounded Phase 09 quality-gate remediation addresses P09-QG-001, P09-QG-002,
and P09-QG-003 without starting Phase 10 or changing the generic foreign-identifier
intake contract. A single existing-format Singapore UEN predicate now drives
identifier-format evidence, canonical validation, the onboarding pre-provider guard,
and the ACRA adapter guard. An explicit Singapore request with an ineligible identifier
stops as a safe, retrievable, non-actionable Registry blocker before ACRA or any
downstream stage.

`JurisdictionResolution` and `RegistryRoutingDecision` now reject every contradictory
construction identified by the independent gate. The deterministic set-based resolver
and closed router remain unchanged in behavior. Final verification passed 39 focused
Phase 09 tests, 197 POC/provider regressions, 548 full backend tests, and 45 frontend
tests, plus all required static, contract, security, dependency, build, delivery, and
Windows lifecycle checks.

# 2. Quality Gate Findings Addressed

| Finding | Disposition | Evidence |
|---|---|---|
| P09-QG-001 — High: explicit SG could send a non-UEN identifier to ACRA | REMEDIATED | `AU-REG-123`, `BAD-ID`, and `123` with SG now produce `REGISTRY_IDENTIFIER_NOT_ELIGIBLE`; ACRA call count is zero for each |
| P09-QG-002 — Medium: contradictory resolution/routing objects were constructible | REMEDIATED | Complete state invariants are enforced by model validators; direct adversarial construction tests reject every gate example |
| P09-QG-003 — Low: focused tests omitted both invariant classes | REMEDIATED | Focused suite expanded from 14 to 39 tests, including provider eligibility, direct service/adapter guards, and direct model construction |
| P09-QG-004 — Low: PDF is selected before Registry decision | ACCEPTED DEBT / NOT CHANGED | The backend and frontend still prevent upload/processing after a Registry blocker; UI sequencing was explicitly outside remediation scope |

# 3. Files Changed

Files touched by this remediation only:

- `apps/backend/app/domain/jurisdiction.py` — shared Singapore UEN predicate and complete
  resolution/routing model invariants.
- `apps/backend/app/connectors/registry.py` — fail-closed ACRA adapter eligibility guard
  and fixed safe domain exception.
- `apps/backend/app/services/canonical_validation.py` — reuses the shared UEN predicate.
- `apps/backend/app/services/onboarding.py` — reuses the predicate for jurisdiction
  evidence and stops invalid SG identifiers immediately before provider invocation.
- `apps/backend/app/domain/zero_touch.py` and
  `apps/backend/app/services/zero_touch_orchestration.py` — truthful typed non-actionable
  blocker projection.
- `apps/backend/tests/test_phase09_jurisdiction_gateway.py` — focused remediation and
  adversarial regression coverage.
- `docs/contracts/ACRA_MOCK_API_PROFILE.md` and
  `docs/architecture/PHASE_09_JURISDICTION_GATEWAY.md` — repaired boundary semantics.
- `.agents/skills/poc-regression-check/references/regression-catalogue.md` — accepted
  explicit-SG ineligible-identifier scenario and cross-scenario invariant.
- `.ai-pipeline/reports/PHASE_09_REMEDIATION.md` — this report.

The pre-existing combined dirty working tree was preserved. No commit, push, merge,
rebase, stash, reset, clean, stage, dependency change, or unrelated edit was performed.

# 4. Singapore Identifier Eligibility Fix

`is_eligible_singapore_uen` in `app.domain.jurisdiction` is the one canonical predicate.
It implements the existing POC rule only: exactly nine digits followed by one uppercase
letter. It is not represented as a complete legal or live ACRA specification.

The authoritative runtime call-stopping guard is in
`OnboardingService.create_staged_case`, after jurisdiction resolution and routing but
immediately before `RegistryProvider.retrieve_company`. This preserves the deliberately
broad generic intake grammar and lets foreign-style identifiers reach AU/MY/HK routing,
while preventing a selected Singapore route from invoking its provider with an
ineligible identifier.

`AcraRegistryProviderAdapter.retrieve_company` independently applies the same shared
predicate before `AcraConnector.fetch_company`. This second placement protects direct
internal adapter calls. It is not a second regex or a divergent rule.

The same predicate also replaces the previous separate regex uses for
`IDENTIFIER_FORMAT -> SG` evidence and Singapore canonical minimum validation.

# 5. Invalid-SG Public/Domain Behaviour

The chosen behavior is a controlled retrievable case rather than HTTP request
rejection. The generic API request remains valid and returns `201`; the backend records:

```text
jurisdiction: RESOLVED / SG
route: SELECTED / ACRA
case state: REVIEW_REQUIRED
zero-touch state: WAITING_FOR_REVIEW at REGISTRY
code/type: REGISTRY_IDENTIFIER_NOT_ELIGIBLE
available actions: none
```

The fixed message is: `The identifier is not eligible for Singapore ACRA retrieval.`
No raw exception or provider detail is exposed. The outcome does not claim ACRA was
queried, does not become `ACRA_ENTITY_NOT_FOUND`, and introduces no review/resume
action. A caller must start a corrected request under the current process-local POC
contract.

# 6. JurisdictionResolution Invariants

All states still require a timezone-aware UTC `resolved_at`. State-specific invariants
are now:

- `RESOLVED`: at least one observation; selected jurisdiction present; every
  observation exactly matches it; therefore exactly one distinct observed jurisdiction.
- `UNRESOLVED`: no selected jurisdiction and no observations.
- `CONFLICT`: no selected jurisdiction; at least two observations; at least two
  distinct observed jurisdictions.

The validator rejects resolved SG supported by AU evidence, resolved SG with mixed
SG/AU evidence, resolved with no evidence, unresolved with evidence, conflict with one
observation, and conflict with multiple agreeing observations.

# 7. RegistryRoutingDecision Invariants

All decisions still require a timezone-aware UTC `decided_at`. The bounded current
contract is now encoded directly:

- `SG` must be `SELECTED / ACRA`.
- `AU`, `MY`, and `HK` must be `PROVIDER_NOT_IMPLEMENTED / provider=None`.
- selected foreign/ACRA routes are rejected.
- selected routes without a provider are rejected.
- provider-not-implemented Singapore routes are rejected.
- provider-not-implemented routes carrying any provider are rejected.

No foreign provider was added.

# 8. Regression Coverage Added

Focused coverage now includes:

- `202400001A + SG` accepted with exactly one ACRA call.
- `AU-REG-123 + SG`, `BAD-ID + SG`, and `123 + SG` stopped with zero ACRA calls.
- attempted PDF attachment to each invalid-SG case returns the unchanged blocker,
  creates no document, starts no ownership analysis, and leaves every target operation
  `NOT_ATTEMPTED`.
- direct `OnboardingService` invocation with `BAD-ID + SG` stops before ACRA.
- direct ACRA-adapter invocation with `BAD-ID` raises the fixed eligibility error before
  the underlying connector.
- accepted-format boundaries: valid 9-digit/uppercase-letter forms; invalid short,
  long, missing-letter, extra-letter, lowercase-at-the-exact-predicate, and foreign forms.
- all required invalid and valid direct `JurisdictionResolution` constructions.
- all required invalid and valid direct `RegistryRoutingDecision` constructions,
  including valid AU/MY/HK unsupported decisions.
- `AU-REG-123 + AU` remains a controlled provider-not-implemented case, not a generic
  request rejection.

# 9. Call-Stopping Results

| Scenario | Result | ACRA | IDP/document | Ownership | GoldTier |
|---|---|---:|---:|---:|---:|
| `202400001A + SG` | Document `PENDING_INPUTS` | 1 | 0 before upload | 0 | 0 |
| `AU-REG-123 + SG` | `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | 0 | 0 | 0 | 0 |
| `BAD-ID + SG` | `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | 0 | 0 | 0 | 0 |
| `123 + SG` | `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | 0 | 0 | 0 | 0 |
| direct adapter + `BAD-ID` | fixed domain error | 0 connector calls | N/A | N/A | N/A |
| `AU-REG-123 + AU` | `REGISTRY_PROVIDER_NOT_IMPLEMENTED` | 0 | 0 | 0 | 0 |
| `202400001A + AU` | `JURISDICTION_CONFLICT` | 0 | 0 | 0 | 0 |

For invalid-SG cases, the focused API tests also attempted document attachment and
verified an unchanged Registry-blocked record, an empty document list, no ownership
record, and all four GoldTier operations `NOT_ATTEMPTED`.

# 10. No-Precedence Confirmation

The resolver implementation was not changed. It remains set-based and retains input
order without source, confidence, jurisdiction, or provider-availability precedence.
`USER_INPUT=AU + IDENTIFIER_FORMAT=SG` remains `CONFLICT`, selects no route, and calls
no provider. Q-015 remains open; no user-wins, identifier-wins, SG-wins, or
provider-availability-wins policy was introduced.

# 11. ACRA Trust-Boundary Confirmation

The remediation adds an outbound eligibility guard and does not alter the inbound ACRA
trust boundary. The adapter still performs one monolithic retrieval only for eligible
requests, reconstructs fresh primitive data through strict `AcraCompanyPayload`,
validates nested DTOs, binds returned/requested normalized UENs, applies the existing
source-to-canonical mapper, retains query-free HTTPS provenance, rejects original
control characters, projects only allowlisted safe connector/mapping errors, and keeps
ACRA business source plus Mock/Sandbox environment labels truthful.

No raw payload, endpoint, credential, exception text, or new log statement was added.
No TLS, authorization, mode-selection, or live-interoperability claim changed.

# 12. Scope / Non-Goals Confirmation

This remediation did not implement Phase 10, ASIC or another foreign registry,
additional ACRA operations or fields, ACRA+, new provider modes, source precedence,
conflict resolution, document-first intake, workflow-engine redesign, Mongo application
persistence, ownership/UBO changes, GoldTier changes, related-party writes,
Ready-for-Approval, authentication/RBAC, dependency upgrades, or the PDF-before-Registry
UI redesign.

# 13. Exact Test / Quality Results

| Exact command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests\test_phase09_jurisdiction_gateway.py -q -p no:cacheprovider` | PASS — 39 passed; 1 pre-existing Starlette/httpx deprecation warning |
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests\test_zero_touch_orchestration.py apps\backend\tests\test_phase_07_uat.py apps\backend\tests\test_phase_08_input_driven.py apps\backend\tests\test_phase06_provider_conformance.py` | PASS — 197 passed; same warning |
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests` | PASS — 548 passed; same warning |
| `.\.venv\Scripts\python.exe -m ruff check apps\backend scripts tests` | PASS |
| `.\.venv\Scripts\python.exe -m mypy --no-incremental apps\backend\app` | PASS — 59 source files |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"` | PASS — 44/44; same warning |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_check_secrets.py"` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\check_secrets.py` | PASS — no supported secret patterns |
| `.\.venv\Scripts\python.exe -m unittest tests.test_validate_goldtier_examples -v` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\validate_goldtier_examples.py --if-present` | PASS — expected `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48` |
| `.\.venv\Scripts\python.exe -m pip check` | PASS — no broken requirements |
| `.\.venv\Scripts\python.exe -c "import pymongo; print(pymongo.__version__)"` | PASS — `4.15.1` |
| `npm.cmd run typecheck` in `apps/frontend` | PASS |
| `npm.cmd test` in `apps/frontend` | PASS — 45/45 on permissioned rerun; initial sandbox-only startup failed with known `esbuild spawn EPERM` |
| `npm.cmd run build -- --outDir C:\Users\shane\AppData\Local\Temp\phase09-remediation-build-20260828` in `apps/frontend` | PASS — 29 modules on permissioned rerun; initial sandbox-only startup failed with the same `spawn EPERM` |
| `npm.cmd ls --all` in `apps/frontend` | PASS — exit 0; expected optional platform/feature dependencies shown unmet |
| `.\.venv\Scripts\python.exe -m unittest tests.test_phase_07_delivery_assets -v` | PASS — 4/4 |
| `.\.venv\Scripts\python.exe -m unittest tests.test_demo_lifecycle_windows -v` | PASS — 13/13 in 170.698 seconds; final launcher-owned processes stopped |
| `git diff --check` | PASS — line-ending notices only |
| `git diff --cached --check` | PASS — no output; nothing staged |

No live ACRA or MongoDB connection was required or attempted.

# 14. Remaining Sponsor Dependencies

- **Q-012 remains open:** authoritative subscribed ACRA endpoint/schema,
  authentication, errors, limits, TLS details, authorized access, expanded operations,
  and live verification remain sponsor-blocked.
- **Q-015 remains open:** source precedence, conflict-resolution authority,
  authenticated reviewer role, correction evidence, and resume/restart policy remain
  unconfirmed.

The remediation does not claim either dependency is resolved.

# 15. Remaining Risks

- **Critical implementation findings:** none known after remediation.
- **High implementation findings:** none known after remediation; independent
  re-quality-gate confirmation is still required.
- **High sponsor dependencies:** Q-012 and Q-015 still block live ACRA binding and any
  safe jurisdiction-conflict resolution workflow.
- **Medium:** all application repositories and replay guards remain process-local;
  restart loses cases and decisions.
- **Medium:** the compatibility API property remains named `uen` while carrying a
  generic foreign registration identifier.
- **Low:** the frontend still asks for a PDF before the Registry decision, but blocked
  cases neither upload nor process it.
- **Low:** the pre-existing Starlette/httpx deprecation warning remains.
- **Low environment/repository hygiene:** Git still cannot inspect the pre-existing
  untracked `apps/frontend/pytest-cache-files-89airr88/` directory; no permissions or
  contents were changed.

# 16. Readiness

All locally remediable Phase 09 quality-gate findings are addressed and the full
required verification set is green. The branch is ready for an independent Phase 09
re-quality gate. No independent re-quality gate or next-phase work was performed here.

READY FOR PHASE 09 RE-QUALITY GATE
