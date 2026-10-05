# Zero-touch / Copilot latest-main integration — independent final recheck

Date: 2026-10-06. Reviewed round: INTEGRATION_R1_RECHECK.
Verdict: **PASS — P0/P1/P2 = 0/0/0.**
IMI-001 is independently reproduced as repaired. No current required fix remains.
This verdict applies only to the frozen payload below and permits the separately
owner-authorized pending main integration commit. No push, PR, PR merge, auto-merge,
worktree deletion, next phase, Live or production readiness is authorized.

## Final frozen identity

Branch: fix/zero-touch-registry-reuse-happy-path.
Worktree: C:/Users/shane/.codex-clean2/worktrees/zero-touch-registry-reuse-happy-path/data-dividends-zero-touch-clm.
Pre-integration HEAD: 859f21872121f437020f555169ff001c3825427f.
Accepted parent feature: ccff7471fd23e64e87bf94a087a5540762276900.
Original BASE: 771a9696e1e31e3865da4fbbb3f9b33b5959cb6a.
Fetched main / pending MERGE_HEAD: 1fc097f12c84af52b1e6d70a336cc22b03f3bef4.
Final payload Git tree: abb911a223f4833310826e60b2842e6a77909d8f.
Complete raw aggregate: 29032e482367248ab719a0294cc1fd8a0ac26c1997c794a760c7723d1d92b3d0.

All1,285 staged payload files and35 integration-delta paths are enumerated in the companion
ZERO_TOUCH_COPILOT_MAIN_INTEGRATION_REVIEW_MANIFEST.json. Reviewer independently verified
every raw/canonical SHA256, size, staged mode/blob, helper SHA and sorted-path aggregate,
and reconstructed the exact Git tree in memory. No index mismatch, extra payload path,
unmerged entry or staged whitespace defect remains. Runtime R1 freeze9f15a7b3/e52e79af
changed exactly CopilotPanel.tsx and CopilotPanel.test.tsx from initial I1. Final static
documentation closure changes only the already-owned architecture/state integration
paragraphs: remove transient uncommitted wording and record the same local404 cancellation.
Their source/authority wording was independently reviewed and all five configured static
checkers independently repeated on final content. All product/test/helper bytes retain
the runtime R1 freeze; remaining1,281 payload files are unchanged from I1. Three named integration
derivative reports alone are excluded; historic feature evidence remains inside the
payload. Root alone owns Git/source mutation; reviewer wrote only this assigned report.

## Remediation and explicit owner criteria

Initial INTEGRATION_I1 was FAIL0/1/0 for IMI-001: either a brief404 or chat404 cleared the
conversation, then the earlier peer200 restored inaccessible-case content. Both independent
arrival-order probes failed. Initial verdict and exact identity are preserved below;
the finding is not waived or attributed to the historical isolation limitation.

Round1 of the maximum2 remediation rounds reuses existing AbortControllers. One local
clearInaccessibleThread helper cancels retained brief and chat requests, empties the case
conversation and clears busy state. Existing abort guards reject late success/error
publication. Fresh explicit authorized refresh still works. No additional authorization,
query-client, source, classification, persistence or target owner is introduced.

| Explicit owner criterion | Final independent result |
|---|---|
| Both accepted feature commits remain semantically intact | PASS; accepted ancestry/history intact. Backend/classification/document/ownership/ledger/envelope/fixture and CaseDetail/query/type/CI owners retain their accepted source. Database-first/NO_MATCH/OCR/manual review/final Send/exact-ID/no-replay remain exercised by118 focused tests and unaffected broader evidence. |
| Copilot remains read-only | PASS; backend client uses GET only with the user's session; access is decided by existing backend APIs. No mutation route or case business-rule/persistence owner. Actual authenticated current-schema10 bridge preserves case/CLM bytes, provider calls and empty target attempts; unsupported mutation routes404. |
| Current-evidence classification remains correct | PASS both modes; conflict blocks, fresh same-value review restores currentness while final Send remains required, and third evidence invalidates again.31 conflict/42 continuation/29 fixture-OCR cases pass. No classification owner was altered by integration. |
| Frontend route/context/query-cache regression absent | PASS; current route/intake case context and scoped query owner retained. Existing authenticated transport handles Copilot401 with generation guard; session replacement remounts through AuthProvider. Independent43 frontend cases and both original404 peer probes pass; inaccessible content cannot reappear after either404. |
| No hidden owner environment/database access occurred | PASS within current execution boundary; explicit pre-import memory/Mock settings, forbidden dotenv reads and allowlisted subprocess environment. Independent hostile isolation passes. No owner dotenv/protected Mongo/service inspection. |
| No external provider calls occurred | PASS; current tests use Mock/fake XPI and fake CLM/model transports. Independent real HTTP proxy uses6 GET-only fake CLM reads, model calls0; both Node probes use stubbed fetch only. External ACRA/GoldTier calls0. |

## Independent execution on the final reviewed content

All runtime executions were serialized after explicit clearance that the sole quiet full
backend process had exited. No reviewer runtime overlapped that process. Python bytecode
and pytest cache writes were disabled for the independent backend checks.

- Original independently authored React/jsdom peer-response probes: **2/2 PASS**,1.29s,
  exit0; brief404->late chat200 and chat404->late brief200 both retain cleared state.
  No actual network call. These invoke runtime source compiled in memory, not a copied
  implementation. Authored regression additionally proves peer abort and fresh recovery.
- SHA-bound run_main_integration_tests.py with apps/assistant/tests and the actual
  Copilot bridge, classification-conflict, continuation and database-happy-path suites:
  **118 passed/0 skipped,36.18s,exit0**. Includes actual local OCR and both provider modes.
  One existing Starlette/httpx deprecation warning.
- Allowlisted child Vitest run for Copilot client/panel/context/text, AuthSessionOrdering
  and Phase13AuthPriority: **43 passed/6files,1.74s,exit0**. Covers current/stale401,
  session replacement, route/context, safe rendering and both404 peer orders/recovery.
  Existing SSR useLayoutEffect warnings remain visible.
- Standalone hostile test isolation: **1 passed,1.60s,exit0**. Dotenv read and protected
  Mongo construction are forbidden before app import; no protected connection occurs.
- Independent real HTTP Vite->Copilot smoke: **PASS**, forwarded cookie,6 GET-only fake
  backend reads, case/target mutation endpoints404, real model calls0. Exact owned
  process groups and18100/14173 ports cleaned before PASS.
- Five configured architecture/project-state/policy-authority/external-provider-readiness/
  secret checkers: **PASS**. Scanner stays on tracked/non-ignored task files and detects
  no supported secret pattern; it is not a claim of universal confidentiality detection.
- Exact owned Mongo container identity independently matches
  1edd370aed33666ada51fced59189a536e86b8a11e2ba6311cdbef48fd07f9ff;
  **non-system database count0**. Reviewer did not create/use a physical test database.

## Broader evidence attributed to coordinator, with revision boundaries

- Sole quiet backend: **2,477 passed/124 conditional physical skips**,4 warnings,
  936.94s pytest/939.45s wrapper,exit0. This ran on initial I1 full tree; all backend,
  assistant and test bytes are unchanged in R1. It is evidence for those exact unchanged
  bytes, not a claim that the later Panel repair was tested by that backend process.
  Physical skips are not Mongo PASS. Existing serializer/Starlette warnings remain.
- Initial integration focus118 and affected backend282 passed; reviewer independently
  reran the118 focus on final R1 above.
- Final R1 full frontend: **539 passed/46 files,7.07s**, TypeScript/build PASS;
  build133 modules/560.49KB with existing >500KB warning. This supersedes initial537.
- Backend Ruff/strict mypy126 sources and assistant Ruff/strict mypy9 sources passed on
  unchanged source. Contracts/hostile/governance/harness204 passed; direct static checker
  results independently repeated above.
- Guarded real HTTP/Playwright Alpha7.9s and conflict9.8s passed on I1, including actual
  scanned Alpha OCR and Final Send/readback, and conflict noSend/unprepared then fresh
  review/ready/prepared with pre-Send mutation/attempts0. Root/context/query/zero-touch
  fixture and pipeline bytes remain unchanged in R1; the bounded R1 repair is verified
  separately by final full frontend and independent runtime probes. Browser/allowlisted
  database cleanup was inspected. No R1 rerun of these unaffected browser selectors is
  claimed. Initial additional proxy smoke is supplemented by the independent run above.

No remote CI, complete65-lifecycle run, external model, Live provider interoperability or
production compliance/approval claim is made. Guarded physical browser evidence belongs
to owned generated databases; no integration schema/repository behavior changed.

CURRENT_TEST_ISOLATION=PASS; OWNER_ENV_READ=0; PROTECTED_DB_ACCESS=0;
EXTERNAL_ACRA_CALLS=0; EXTERNAL_GOLDTIER_CALLS=0; real model calls0.
HISTORICAL_PROTECTED_DB_NON_ACCESS=NOT_CERTIFIED;
OWNER_ACCEPTED_HISTORICAL_LIMITATION=YES.
Historical uncertainty was not re-investigated or used to waive IMI-001.

API/type: narrow frontend transport/error metadata changed; backend APIs unchanged.
Schema: unchanged10. Connector/config: incoming read-only Copilot/proxy retained and
test containment explicit; no target/registry transport adaptation. Business rule/mapping:
unchanged. Auth/security: existing session transport reused, coherent local404 cancellation
added. Architecture/provider status: existing accepted main service imported, canonical
owners and mode labels retained. Runtime: integrated Copilot composition/context/proxy
plus bounded local conversation safety. No second state/authorization/business owner.

Coordinator cleanup is independently attributed from its ignored receipt: after reviewer
runtime finished, the exact owned container was stopped/auto-removed with non-system DB
count0; owned18765/14173/18100/27185 ports are free. No owner resource was touched. One
coordinator freeze-helper default-decoding error was corrected with explicit UTF-8 before
any app/config/DB import; no passing application evidence is inferred from that failure.

Final source identity is unchanged at report completion. Reviewer runtime is finished.
Next authorized action: coordinator verifies unchanged reviewed payload, performs only the
authorized normal two-parent merge commit, verifies parents/clean tree and stops for owner
review. Worktree retained; publication remains unassigned.

---

## Preserved initial INTEGRATION_I1 report (historical, superseded by final PASS above)

# Zero-touch / Copilot latest-main integration — independent quality gate

Date: 2026-10-06. Initial round: INTEGRATION_I1.
Verdict: **FAIL — P0/P1/P2 = 0/1/0.**
The pending merge must not be committed on this reviewed content. The owner-authorized
bounded integration remediation may address IMI-001 and obtain a fresh independent recheck.
No publication or next-phase readiness is granted.

## Frozen reviewed identity

Branch: fix/zero-touch-registry-reuse-happy-path.
Worktree: C:/Users/shane/.codex-clean2/worktrees/zero-touch-registry-reuse-happy-path/data-dividends-zero-touch-clm.
Pre-integration HEAD: 859f21872121f437020f555169ff001c3825427f.
Accepted parent feature: ccff7471fd23e64e87bf94a087a5540762276900.
Original BASE: 771a9696e1e31e3865da4fbbb3f9b33b5959cb6a.
Fetched origin/main and pending MERGE_HEAD: 1fc097f12c84af52b1e6d70a336cc22b03f3bef4.
Payload Git tree: b6ab182ba42f16cac9a703a3bb1c70dc771cbe87.
Complete raw aggregate: 68b3a0e365a00129b248a9e435061ee455a4b9765e392776249c9ccc1ae11705.

The companion ZERO_TOUCH_COPILOT_MAIN_INTEGRATION_REVIEW_MANIFEST.json enumerates
all 1,285 staged payload paths, including the 35-path integration delta and historical
feature reports, plus SHA-bound ignored runtime helpers. Reviewer independently checked
all raw/canonical hashes, file sizes, staged modes/blobs, complete aggregate and helper
hashes. Recursive Git-tree reconstruction from the mode/blob/path inventory matches the
recorded payload tree without changing the index. No unmerged entry remains. Tracked
staged whitespace passes. Only the three explicitly named integration derivative
implementation/manifest/gate reports are excluded. Both accepted commits remain intact
in existing history; their backend owners, classification tests, fixture sources,
CaseDetail/query/type/CI paths have no integration delta.

Authority: newest owner integration attachment, AGENTS, selected current workflow/context,
planner/handoff, architecture/state, readiness/persistence contracts and preceding accepted
feature gate; fyp-quality-gate and integration-safe-development, with cache/security review.
The reviewer made no implementation/test/configuration/Git mutation. One attempted
git write-tree identity read failed before acquiring a lock due filesystem permissions;
subsequent independent tree reconstruction is purely in memory.

## Finding IMI-001 — P1 — peer responses restore inaccessible-case data after 404

Affected source: apps/frontend/src/pages/CopilotPanel.tsx, brief error callback lines
98–100 and chat error callback lines 152–154; success publication guards at 86 and 144.

A current backend404 clears the case's local conversation but does not abort the other
request family. A previously started chat or refresh brief can subsequently resolve200
and republish formerly accessible case content. Each success callback checks only its own
AbortController. This violates current inaccessible-case containment, cancellation and
no stale-response resurrection requirements; backend authorization remains authoritative
but the UI republishes obsolete case data after the authoritative inaccessible result.

Two independent in-memory React/jsdom probes on frozen runtime source reproduce:
1. Start chat, start Refresh, resolve Refresh404, resolve prior chat200.
2. Start Refresh, start chat, resolve chat404, resolve prior Refresh200.
Both initially remove the old conversation and then restore the late fictional case
answer. Probe exit1, 1.31s, zero real network calls, no source writes. One preceding probe
assembly syntax error occurred before any application composition and supplied no product
evidence. The corrected execution falsifies both directions.

Required bounded remediation: on a current-case inaccessible response, invalidate both
retained brief and chat controllers and clear local conversation/busy state coherently.
Retain existing session/auth/backend ownership. Add meaningful regressions for both
arrival orders, rerun affected frontend checks, freeze new content and request recheck.
The independent reviewer does not implement the repair.

## Owner's six explicit criteria

| Criterion | Initial result |
|---|---|
| Accepted feature commits remain semantically intact | PASS on source/history inspection; unchanged backend/fixture/query owners and accepted guards. |
| Copilot remains read-only | PASS on route/client inspection: authorized backend GET only; no case/target mutation endpoint or business-rule/persistence owner. |
| Current-evidence classification behavior remains correct | PASS supported by unchanged accepted owners and fresh coordinator 102-case focus plus actual authenticated two-mode Copilot bridge. |
| Frontend route/context/query-cache regression absent | FAIL due IMI-001; central current/stale401 transport and route context otherwise preserve existing owners. |
| No hidden owner environment/database access | PASS for this current review/execution boundary and inspected containment helpers. Historical limitation remains separate. |
| No external ACRA/GoldTier provider calls | PASS for scoped current evidence; independent probe uses stubbed fetch only, coordinator probes use contained Mock/Local and fake XPI. |

## Evidence and remaining independent execution

Reviewer first held all runtime until the coordinator's sole quiet full backend process
completed, then executed only the two adverse frontend probes. Broader independent focus
is intentionally pending the bounded repair rather than being attributed to changed
future content.

Fresh coordinator evidence inspected/attributed, not claimed as reviewer execution:
- Sole quiet full backend: 2,477 passed /124 conditional physical skips, four warnings,
  936.94s pytest /939.45s wrapper, exit0. No physical URI; skips are not physical PASS.
- Backend/Copilot/schema10/zero-touch focus:118 passed; affected backend282 passed.
- Frontend:537 passed, TypeScript/build passed; backend Ruff/mypy126 and assistant
  Ruff/mypy9 passed; contracts/hostile/governance/harness204 passed.
- Guarded real HTTP/Playwright Alpha7.9s and conflict9.8s passed, task allowlisted Mongo
  cleanup verified. Actual image-only Alpha OCR and current conflict/fresh review UI.
- Additional Vite/Copilot proxy smoke:6 GET-only fake CLM reads, forwarded session,
  mutation endpoints404, model calls0, owned process/port cleanup.

Existing Starlette/httpx, malformed-provider serializer and frontend/build-size warnings
remain attributed to their actual checks. No remote CI, full65-lifecycle execution,
Live interoperability, production readiness or new physical-schema claim is made.

CURRENT_TEST_ISOLATION=PASS; OWNER_ENV_READ=0; PROTECTED_DB_ACCESS=0;
EXTERNAL_ACRA_CALLS=0; EXTERNAL_GOLDTIER_CALLS=0; real model calls0.
Standard pre-import test/memory/Mock settings and Copilot env_fileNone/LLMfalse are visible
in the inspected helpers. Browser harness uses an environment allowlist and newly
generated allowlisted namespaces; no protected owner DB, owner service or owner dotenv
was inspected. Historical protected-DB non-access remains NOT_CERTIFIED;
OWNER_ACCEPTED_HISTORICAL_LIMITATION=YES. It is not reopened as this product finding.

API/type integration changes are frontend transport/error metadata only; backend API and
schema10 remain unchanged. Existing source/classification/ownership/ledger/mapping/provider
owners are retained. Copilot has no mutation authority. Current blocking issue is local
conversation cancellation. Next authorized action: coordinator's bounded IMI-001 repair,
fresh freeze and independent recheck; no commit until exact PASS0/0/0.
