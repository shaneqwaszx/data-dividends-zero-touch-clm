# Post-Phase24 demo matrix - Slice B

Current sponsor entry point: [Final Sponsor Demo Runbook](FINAL_SPONSOR_DEMO_RUNBOOK.md)
and [Final UAT Acceptance Matrix](FINAL_UAT_ACCEPTANCE_MATRIX.md). The retained instructions
below preserve their historical fixture/evidence boundaries.

These are three distinct bounded POC journeys. Final human approval remains outside
the POC. No Slice C, GoldTier enhancement, autonomous approval or Live proof is included.

## Three paths

| Fact | Garden supplementary journey | Second happy path | Third cache/no-call path |
|---|---|---|---|
| Purpose | Honest partnership ownership gap and supported local remediation | Deterministic distinct company completion | Fresh complete registry reuse without a provider call |
| Classification | Official Marketplace Mock lane; current B verification uses explicitly labelled synthetic offline protocol input | SYNTHETIC MOCK, existing local registry dataset | SYNTHETIC MOCK, existing local registry dataset |
| UEN | 11111999A | 202400008H | 202400001A |
| Legal name | GARDEN BUSINESS | MULTIPLE OWNER DEMO PTE. LTD. | MERLION CIRCULAR LABS PTE. LTD. |
| Legal form | PARTNERSHIP; canonical ownership classifier BUSINESS_PARTNERSHIP | Existing private company fixture | Existing private company fixture |
| Upload PDF | garden-partnership-reviewed-client.pdf | multiple-owner-demo-client.pdf | clean-company-profile.pdf (existing) |
| Registry origin | Previously observed official Mock identity; strict decoder replay from tracked normalized entity fields, four fictional role placeholders | Project synthetic Mock provider | Owner-warmed complete project synthetic snapshot |
| Namespace | ACRA_API_MARKETPLACE_MOCK_V1 for this explicit adapter test; protocol fixture remains offline synthetic, not a new network observation | MOCK_ACRA_SYNTHETIC_V1 | MOCK_ACRA_SYNTHETIC_V1 |
| Acquisition / case binding | PARTIAL; ownership and relationships UNSUPPORTED; binding absent | COMPLETE / PROVIDER_FETCH | COMPLETE / CACHE_HIT on the new case |
| Required calls in these tests | Two data reads through injected inert transport plus one inert token response; no shareholder/relationship dispatch | Exactly profile, officers, ownership parties, relationships, in that order | Warm case: four ordered synthetic operations; new cache-hit case: exactly zero additional operations |
| Actual external ACRA HTTP | 0 | 0 | 0 |
| Ownership source | Reviewed USER_SUPPLIED_DECLARATION / LOCAL / MANUAL_DECLARATION_POC, fictional 60/40 economic interests | Synthetic registry direct 50/30/20 interests; sole Decimal engine | Synthetic registry direct 60/40 interests; sole Decimal engine |
| Blocker / remediation | OWNERSHIP input required; matching client identity auto-confirms, then operator explicitly reviews the structured declaration | No ownership/evidence intervention; operator target classification and final dispatch confirmation | No false provider-not-called blocker; operator target classification and final dispatch confirmation |
| Progression | Identity/officers -> PDF extraction/comparison -> LOCAL declaration -> automatic recalculation/blocker retirement -> explicit Mock confirmation | Profile -> matching PDF -> registry ownership -> readiness -> explicit Mock confirmation | Unsubmitted warm case -> distinct new case -> retained binding/provenance -> readiness -> explicit Mock confirmation |
| Supported end state | COMPLETED / MOCK_GOLDTIER_SUBMITTED; provisional result; no final legal approval | COMPLETED / MOCK_GOLDTIER_SUBMITTED | COMPLETED / MOCK_GOLDTIER_SUBMITTED |
| Limits | No official percentage, denominator/control/relationship or legal UBO authority; officers never become UBOs | No claim values came from official Marketplace; 20-percent interest stays below provisional threshold | Single-process single-flight; no distributed exactly-once or ACRA validity guarantee |

PDFs live under apps/backend/tests/fixtures/uat. Regenerate only the two new documents with
scripts/generate_slice_b_demo_pdfs.py. Their bytes are newly generated from safe tracked
normalized entity fields and existing fictional fixture data; no private document is copied.
Garden SG is the existing Singapore-lane default, not a returned provider fact. Its
registration date is 1974-09-28 and entity status remains absent. Source:
docs/development/OFFICIAL_ACRA_GARDEN_VERIFICATION_REPORT.md, section 5.
The old Garden Walk/company protocol pack stays intact as earlier synthetic evidence.

## Operator journey and isolated browser proof

Garden: create 11111999A using the new matching PDF. Inspect Registry identity:
identity/officers retrieved, PARTIAL and ownership/relationships UNSUPPORTED.
Choose Add structured ownership details; explicitly review the fictional client declaration,
enter Synthetic Garden Partner A / 60 and Synthetic Garden Partner B / 40, and submit.
LOCAL, USER_SUPPLIED_DECLARATION and MANUAL_DECLARATION_POC remain visible. Ownership
recalculates automatically and its current blocker retires. Select the existing POC target
classification inputs and explicitly confirm/send to unchanged Mock GoldTier.

Second: use 202400008H and its matching PDF in local synthetic mode. Inspect complete
registry acquisition and three direct interests. Confirm the current Mock target journey.

Cache: in enabled local synthetic cache mode, create Merlion once through the normal owner
and keep that warm case target-unsubmitted. Select New onboarding -> Start a new case,
create Merlion again with the existing clean PDF, and inspect CACHE_HIT. Completing the warm
target first could legitimately select Search-first target hydration instead of registry
cache reuse; those are different journeys. The cache view says:
Reused fresh registry evidence — no ACRA request required.
It retains binding time, expiry, policy ID/version/duration/comparator, and original
operation retrieval times; it does not assert present validity.

Focused browser commands (task-owned ports, ephemeral credentials, memory composition,
no .env, zero external provider dispatch):

    python scripts/run_e2e.py --registry-demo garden-partnership --grep "Slice B Garden partnership" --backend-port 8037 --frontend-port 5207
    python scripts/run_e2e.py --registry-demo synthetic-cache --grep "Slice B second synthetic" --backend-port 8037 --frontend-port 5207
    python scripts/run_e2e.py --registry-demo synthetic-cache --grep "Slice B Merlion fresh cache" --backend-port 8037 --frontend-port 5207

Run separately. The test-only count route exists solely in e2e_backend_server.py's
explicit isolated fixture composition; it is absent from ordinary app.main.

## Registry acquisition decision table

Backend RegistryAcquisitionCoordinator remains the authority; the browser projects facts.

| Decision | Required provider calls | Evidence |
|---|---|---|
| A - trusted fresh COMPLETE | 0; immutable CACHE_HIT binding | Named Merlion normal API/browser paths and physical restart/deletion cache tests |
| B - missing cache | Required ordered four synthetic operations; absent entity stops after profile | Second path and Phase16 counts |
| C - stale relevant operation | Officers only; relationships only; ownership plus dependent relationships; stale profile reacquires all four | Four exact-expiry Slice-B parameter cases; immediate repeat is zero-call |
| D - fresh definitive NOT_FOUND | 0 until exact negative TTL; profile only at expiry | Phase24C negative-cache test |
| E - timeout/malformed/unavailable uncertainty | Never a definitive negative or false hit; future acquisition remains eligible; healthy prefixes may be reused | Phase24C uncertain-result and failed-operation tests |
| F - same-UEN concurrent requests | One acquisition for the existing bounded in-process cohort; defensive copies; lock retirement | Phase16 same-key and Phase24C capacity/timeout/cancellation tests |
| G - identity/UEN correction | Current generation; one necessary acquisition without immediate replay, or 0 for fresh corrected-key cache | Phase24C corrected identity and A-B-A isolation; Phase24 identity adverse tests |

Official PARTIAL operation prefixes can suppress repeated transport while still returning
PARTIAL with no case evidence binding. This is not a whole-case official CACHE_HIT.
COMPLETE is never weakened to admit unsupported relationships. Current official whole-case
cache binding is therefore unavailable for Garden. EMPTY, UNSUPPORTED, FAILED and COMPLETE
remain distinct; historical Garden shareholder EMPTY does not mean no beneficial owners.

## Second official company authority

SECOND_OFFICIAL_COMPANY = BLOCKED_BY_SAMPLE_AUTHORITY.

The supplied seven-page catalogue was rechecked in memory as operation-candidate metadata.
Its basic-information and Business Profile lists have no same-UEN pair. Historical observed
basic records classify OTHER or BUSINESS_PARTNERSHIP, without a retained coherent full second
profile/legal-form contract suitable for this deterministic journey. Shareholder/member/group
and capital sample UENs have empty basic identities and cannot be mixed across UENs.
This does not prove the provider cannot support a second entity. It proves the bounded
supplied authority is insufficient; no exploratory network probing occurred.

Missing: a coherent same-UEN legal name/profile/legal form and required address/country
semantics, plus supported operation/EMPTY/UNSUPPORTED behavior. Quantitative ownership is
optional when truthful LOCAL supplementary remediation is used. Partnership ownership,
same-entity denominator and relationship/control contracts stay open in Q-012.

## Normal startup acceptance boundary

The user's normal development composition is the original checkout, with its existing
private configuration:

Backend terminal, original apps/backend:

    ..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Frontend terminal, original apps/frontend:

    npm.cmd run dev -- --host 127.0.0.1 --port 5173

Neither original process nor clm_poc was started/accessed during Slice B. Normal-environment
acceptance is unexecuted. start_demo_windows.bat forces synthetic Mock and certifies only
its isolated demo lifecycle. The focused commands above certify their explicit offline
test compositions, not the user's Mongo/provider configuration.
