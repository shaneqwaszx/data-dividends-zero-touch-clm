# PR95-R6 independent entry-view adversarial review

Verdict: **PASS**. No required finding remains in the bounded Dashboard entry-view/error-recovery correction. This report is an independent focused review, not the final Quality Gate or authorization to commit, publish or merge.

## Authority and reviewed content

Reviewer: fresh agent `pr95_r6_entry_adversarial`, with no implementation or Git mutation authority. The sole tracked write is this report. Read the full owner R6 attachment, root/frontend AGENTS, canonical quality-gate/cache/security skills, development workflow and merge protocol, relevant frontend architecture/access contract, implementation handoff, complete three-file delta, and surrounding query/auth/transport/navigation owners.

Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
Branch: `codex/pr95-dashboard-remediation-20261018`.
Starting and reviewed HEAD: `a2c92c871b1ba9971c28d71fe51dd8514bfcac06`.
Committed tree: `18a0ca4c0b486bdd89c21f6979b1de5cae65be61`.
Recorded origin/main: `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
The verdict binds the uncommitted frozen delta, not the committed tree alone.

Frozen input identity is `.runtime/pr95-r6-frozen.json`: raw file-map SHA-256 `8c010d515675edf7126184c6f252996fbfd90792d03805ec35e1673b152d99ef`; binary diff SHA-256 `684ae6d2a5a5514879fd7054d9a4b7fc6435a7231a5ad2cf6c70d024772bd95d` using `git -c core.autocrlf=false diff --binary a2c92c871b1ba9971c28d71fe51dd8514bfcac06 --` and the frozen path set. Raw hashes and surrounding context hashes verified before and after executions.

| Reviewed path | Raw SHA-256 |
| --- | --- |
| `apps/frontend/src/pages/Dashboard.tsx` | `ce96011b4a7581a0560e0ea2d33034cc301533ac2ec41558eb871d69bdb20ad0` |
| `apps/frontend/src/Dashboard.test.tsx` | `f5cc8acb3edd825bb23b31e1f4560c7077bab510c2e93960b0ec4cfa1615847a` |
| `apps/frontend/e2e/pr95-dashboard.e2e.ts` | `973174885ded4b993875db5d32cbb1859d3fe6274910350cda11abc92cfb7ce6` |
| `.ai-pipeline/reports/PR95_R6_IMPLEMENTATION.md` | `07ff66885abdc0e6829d07df2cbf6a6f981124d98dfa435717075c9dee380313` |

## Independent original-failure reproduction

Executed the exact published Dashboard source obtained with `git show a2c92c871b1ba9971c28d71fe51dd8514bfcac06:apps/frontend/src/pages/Dashboard.tsx`; raw SHA-256 `bb5dba6d46653535d046ea43518edfbb38d8c3eae50658f360f83d4201d66d1d`. An ignored Vite pre-load plugin returns that exact source only for the canonical Dashboard module ID, preserving relative imports and the real query/transport owners. It imports the canonical Vite configuration; no canonical file was replaced, even temporarily. This alternate loader is baseline reproduction evidence only and was not used for corrected acceptance.

Command from frontend: `npm test -- --config ../../.runtime/pr95-r6-entry-baseline.config.ts src/Dashboard.test.tsx -t PR95-R6 --reporter=verbose`.
Result: **8 FAILED / 36 intentionally unselected**, exit 1, 3.86 s. Log `.runtime/pr95-r6-entry-independent-red.log` records the exact-module override. The 503/network cases fail because the picker has no accessible alert. Retry-dependent cases fail because Try again is absent; cached refresh status is suppressed after returning to the picker. Entering the failed old Onboarding view exposes the synthetic underlying exception detail. These causal failures reproduce the reported control-flow problem rather than a broken fixture/import.

## Corrected execution and adversarial assessment

Canonical command: `npm test -- src/Dashboard.test.tsx src/Pr95DashboardCache.test.ts --reporter=verbose`.
Result: **49 PASS / 2 files**, exit 0, 6.36 s. Log `.runtime/pr95-r6-entry-independent-focused.log`. All eight new cases and the previous Dashboard/cache regressions execute. An earlier exploratory invocation used a nonmatching cache filename and executed 44 Dashboard tests; the final command above supplies the actual canonical cache path and complete 49-test evidence.

Actual browser command: `.venv/Scripts/python.exe scripts/run_e2e.py --grep PR95 --backend-port 8775 --frontend-port 4183 --timeout-seconds 120`.
Result: **2 PASS**, exit 0, 41.7 s. Log `.runtime/pr95-r6-entry-independent-browser.log`. Guarded local authenticated HTTP and Chromium were available and executed in this review. Injected 503/network faults stay inside the existing owned-loopback policy; successful recovery uses genuine local backend responses. No external provider or Mongo access occurred. The two existing selectors and their original navigation, metrics, scopes, genuine Mock completion and activity-page assertions remain present.

| Challenge | Evidence and conclusion |
| --- | --- |
| Every Dashboard entry return | The picker, no-data Onboarding and data Onboarding returns all render the same feedback fragment. No earlier return can suppress it. Success with data renders the existing DashboardView unchanged. |
| Initial unresolved request | role=status announces Loading; no fabricated zero totals. Pending picker to Onboarding and back keeps one in-flight query. |
| Initial 503 and network failure | Fixed role=alert text and native Try again button are visible on the picker; footer becomes Unavailable. Synthetic private response/exception details are absent. |
| Retry pending, success and repeated error | Existing query.refetch executes actual callbacks. Pending is announced; failed attempts return to recoverable error; success removes the error and renders response-authored totals. Repeated-error component assertions pass. |
| Cached background failure and later replacement | Existing snapshot remains visible in both views with explicit refresh-failed disclosure. Retry updates the snapshot and clears the error; component evidence checks changed counts, not just HTTP success. |
| Keyboard and card interactions | Actual Chromium Enter and Space activate the native retry. Retry is outside the category article, with no nested button. Existing card Enter navigation and native focus assertions pass. |
| Navigation during pending/error | Both directions remain available in pending and failed no-data states, preserving the single query owner. Cached failure survives view changes; recovery renders normally. |
| Actor/role/session isolation | New cases abort a pending old retry and reject its late response after actor or same-user role/session replacement. Existing auth.tsx cancels/clears before accepting the next session and remounts descendants by generation. Scope/date/team keys and AbortSignal transport are unchanged. |
| Adjacent regressions | Prior Dashboard sorting, timing, subset disclosure, pagination, scope, date, card and cache tests pass; actual PR95 journeys retain accepted functionality. No duplicate independent fetch, browser storage, mutation retry or authorization owner was introduced. |

The new component harness disables retry only on its own controlled client instance so each manual interaction has one deterministic attempt. Production retry remains 1; the actual browser run exercises that unchanged policy. No global suppression or assertion weakening was found.

## Preservation, limitations and next action

After execution, independently verified all four frozen inputs, the surrounding context map, binary diff identity, and **2,161 of 2,164** starting tracked files unchanged; the three differences are exactly the authorized frontend paths. Index remains empty. `git diff --check` passes; this new Markdown report was checked separately for trailing whitespace and final newline. Existing mixed line endings remain localized, with no mass rewrite.

API/DTO/schema, backend/persistence, connectors/providers, business calculations, configuration/dependencies, authenticated state ownership and previous R2-R5 reports remain unchanged. The runtime correction is limited to truthful Dashboard frontend state presentation, safe fixed error text and no-data return navigation. No .env access, Git mutation, hosted review, publication, PR96 change or main change occurred.

This focused run does not claim execution of all 110 browser selectors, full frontend/type/build/static checks, backend tests or physical Mongo. The coordinator's broader R6 evidence remains separately attributed until the different final independent Quality Gate assesses it. Earlier R5 backend/physical evidence is historical only; six unavailable native OCR tests and billing-refused CI remain unavailable/NOT_EXECUTED. Existing React server-render/useLayoutEffect warnings are not new failures. This review found no new required out-of-scope defect.

Next authorized action: assign a different fresh independent final Quality Gate on these unchanged exact inputs plus this report. Commit authority remains conditional on that gate's exact PASS. No remote publication or merge is authorized.
