# Review/Rework UI Authentication Ordering — Independent Re-Quality Gate

Date: 2026-09-20
Role: fresh independent authentication/security re-quality-gate reviewer
Verdict: **PASS WITH MINOR FIXES**

## 1. Executive result

The authentication-ordering remediation is independently accepted. The current source,
the exact pre-fix baseline source, the real `AuthProvider`, the real authenticated
transport, the provider-owned `QueryClient`, and the guarded browser journey establish
the following bounded conclusion:

- the reproduced defect class had a source-backed cause: an old request read the
  globally current unauthorized callback at completion, so its `401` could clear a
  later accepted session;
- the historical first guarded-browser timeout remains unattributed because that run
  contains no request-order evidence proving this schedule occurred;
- request-bound transport generation now suppresses only an obsolete unauthorized side
  effect while preserving the original `ApiError(401)` and current-session fail-closed
  behavior;
- different-user and same-user later sessions survive an obsolete `401`;
- obsolete successful restoration cannot replace a later login or resurrect after
  logout through the existing `AuthProvider` effect guard;
- a genuine current-session `401` clears authentication, CSRF state, and the actual
  provider `QueryClient`;
- ordinary restoration/login and actual denied login remain correct; and
- three fresh full guarded browser runs passed sequentially without retry, reset, or
  warm-up discard.

F-01, F-02, and F-04 remain closed. F-03's required repeatability evidence is now
green for this frozen candidate. No auth, cache, security, contract, UI, browser, or
provider fix remains.

Exact `PASS` is nevertheless unavailable because the mandatory task-owned-new-file
whitespace audit found publish-blocking two-space Markdown hard breaks in three
historical untracked documents and an extra blank line at EOF in the execution
addendum. `git diff --no-index --check` reports those exact additions. The same check
performed on the files once staged would therefore fail the repository whitespace
gate. This is a bounded docs-only, non-security correction, so the warranted verdict is
`PASS WITH MINOR FIXES`, not `FAIL`. Publication remains blocked until a separate role
performs the authorized mechanical normalization and a fresh independent recheck issues
exact `PASS`.

## 2. Scope, revision, and write boundary

- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- `BASE_SHA`, `HEAD`, local `origin/main`, and merge base:
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Ahead/behind: `0/0`
- Staged paths: none
- Active Git operation: none
- Reviewed state: frozen uncommitted candidate
- Change classes: `FRONTEND_STATE_CACHE` and `AUTH_RBAC_SECURITY`; the previously
  reviewed UI implementation remains in the frozen content set
- Physical Mongo: not affected and not run; no persistence, schema, CAS, database,
  repository, or backend security owner changed
- Reviewer write boundary: exactly this report
- No implementation, test, planner, historical report, configuration, contract,
  decision, dependency, Git index/history, provider, or database remediation occurred

The task-start preflight confirmed Python 3.12.10, Node.js 22.23.2, npm 10.9.8,
Playwright 1.56.1, repository-local dependencies, guarded loopback lifecycle support,
and free ports 8867/4275. The current session exposed local shell/process execution and
repository read/write capability; no external provider, remote connector, live
database, credential source, or protected sponsor artefact was needed or accessed.

## 3. Frozen reviewed-content identity

The deterministic SHA-256 aggregate over the path-sorted `SHA256  path` manifest below
was `189a17dc3b9682beeabcacce674bbf923bb4e15b78d78e12db13807196cc4c74` before the final
browser sequence and remained the same after every check. This assigned report is
excluded from that identity.

| SHA-256 | Reviewed path |
|---|---|
| `101828e18d25eeb11fc80b9cc934b7db4dfef9666aaf394261b50951ee26e01d` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md` |
| `c303eb67da894ee16bfa5f798f7023c7d327783a725d4c1223851d60d364e247` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_FOLLOWUP.md` |
| `3adb666299ec5f596df56ae7da94d37c30367070c8fab7eebe2353aee413d71e` | `.ai-pipeline/reports/REVIEW_REWORK_UI_AUTH_DIAGNOSIS.md` |
| `1556f4b92b1460088012192a9df62b9b01e91bf48adbbd9253ff077761f2deb7` | `.ai-pipeline/reports/REVIEW_REWORK_UI_IMPLEMENTATION.md` |
| `fc3b83cde150ea11cb79803fb3585dca82ed80e8931511c661034281f7354ae5` | `.ai-pipeline/reports/REVIEW_REWORK_UI_QUALITY_GATE.md` |
| `623d040cb361d51839a51878a1402a279fbce4fbc3a434381b793d2541521fbc` | `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` |
| `49f85aa627c09134fe2f8ec8611cf59ef5187dca7d13131f390aa326665bbc0b` | `apps/frontend/src/AuthSessionOrdering.test.tsx` |
| `0faefa580f454cbda7664dde98aca27839860acca4e9df030b119a2452b248c0` | `apps/frontend/src/Phase15CNavigation.test.tsx` |
| `74c9687e321b5c84c1a4e09faa8ab577866bbce43666537574119d4470000c58` | `apps/frontend/src/UiV2Integration.test.tsx` |
| `477e06dfa2abf5ba190ab5e70842e4d23a91950787b6f8f48ff94958b5112a00` | `apps/frontend/src/api.ts` |
| `6c26e08e29190cf39bbb19c57e9905dfff8bc2b3f96b221378c3fb1db1a855ca` | `apps/frontend/src/pages/CaseDetail.tsx` |
| `edfc82f145429bddd6d94777643e019098dec0184f475b2c64d0fcba0fd18090` | `apps/frontend/src/pages/DeleteCaseDialog.tsx` |
| `cfc09fe4a083edb58013059f8b6781fee4ca93e1bc5966f915d4a9dcef17396b` | `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx` |
| `f836c47ffa0628a4ea0cfd10a4013e22b38a2fdd7185e62f039531dc4ef18c8f` | `apps/frontend/src/pages/DocumentEvidencePanel.tsx` |
| `6a1e9a27bb8411b69c4a9057a9ddf3c1443dfd41cb9c1336cc03d4275db53a81` | `apps/frontend/src/pages/PriorityControl.tsx` |
| `fed28e1a9c58eff1a203a23f342ad0bcc02702b67e4eb772240ff3a72535437e` | `apps/frontend/src/styles.css` |

The three auth-slice hashes exactly match the assignment. All previously accepted UI
hashes match the final historical gate manifest. No implementation, test, or evidence
content drifted during review.

## 4. Acceptance checklist

| Requirement | Result | Independent evidence |
|---|---|---|
| Source-backed cause, without claiming historical attribution | PASS | Exact baseline `api.ts` plus current seven-case suite reproduced A/B/C as failures while D1/D2/E/F passed; current source passes all seven. The historical browser run has no ordering timeline and remains explicitly unknown. |
| Deterministic RED before fix and GREEN after fix | PASS | Isolated exact-HEAD baseline run: 3 failed and 4 passed; frozen candidate: 7/7 passed. |
| Real provider and transport, not an owner-replacing mock | PASS | The tests mount the real `AuthProvider`, use the real `api.ts` transport, and control only `globalThis.fetch` response completion order. |
| StrictMode obsolete restoration `401` after login | PASS | Case A is RED on baseline and GREEN on candidate. |
| Old-session `401` after a different user's session | PASS | Case B is RED on baseline and GREEN on candidate. |
| Old-session `401` after a same-user new session | PASS | Case C is RED on baseline and GREEN on candidate, proving actor ID is not used as session-generation identity. |
| Obsolete successful restoration after later login/logout | PASS | D1 preserves the later login; D2 preserves logout. Existing effect-local `current` ownership remains unchanged. |
| Current-session fail-closed `401` | PASS | E proves the original request rejects with `ApiError(401)`, auth becomes anonymous, actual provider query data is cleared, and a later unsafe request carries no CSRF header. |
| Normal restoration/login and denied login | PASS | F covers successful restoration, successful later login, logout, and real denied-login response/error behavior. |
| CSRF, server authorization, and cache owners preserved | PASS | CSRF is still captured at dispatch for unsafe requests; backend sessions/origin/CSRF/RBAC are unchanged; `clearSessionQueries` remains the only query-clear owner. |
| No stale case/action or closed UI regression | PASS | Focused UI/cache suite 112/112, full frontend 212/212, three full browser runs, and unchanged UI hashes. |
| Three fresh sequential guarded browser suites | PASS | 3/3 in 9.8 s, 3/3 in 8.7 s, and 3/3 in 8.8 s; one worker, zero Playwright retries, fresh runner-owned processes, first startup included. |
| Cleanup after each browser run | PASS | Ports 8867/4275 and runner metadata were absent after every run. |
| Diagnostic/security hygiene | PASS | Secret scan and scanner tests pass; diagnostic source/report retain no real password, cookie, token, CSRF value, authorization header, body, complete URL, raw error, DOM, trace, video, screenshot, HAR, storage state, KYC/PII, or confidential provider data. |
| Task-owned-new-file whitespace hygiene | MINOR FIX REQUIRED | The historical addendum, implementation report, and quality-gate report contain additions reported by `git diff --no-index --check`; exact locations are in Finding H-01. |

## 5. Causal, code, architecture, and cache review

### Reproduced defect class

At request dispatch, the baseline transport captured neither callback identity nor a
session/transport generation. When an old request later returned `401`, it dereferenced
the then-current module-global `unauthorizedHandler`. A later successful login had
reconfigured that callback to the later session's `clearSession`, so the old response
could clear the new session before the obsolete restoration effect's local `current`
guard could help.

The recurrence generator for this frontend class is a valid overlap: an earlier request
remains in flight while the single existing auth owner accepts a later transport/session
configuration. A/B/C converge on the same late mutable callback read. D1/D2 rule out
obsolete successful restoration as an additional active mechanism in the deterministic
experiment, and E rules out globally ignoring `401` as an acceptable correction. I
classify the causal topology as one root with multiple contexts/symptoms. This validates
the reproduced frontend class only; the historical first-run failure remains unknown.

### Remediation fit

`configureAuthenticatedTransport` now increments one module-local generation. Every
transport request captures the current generation before dispatch. A `401` invokes the
centralized unauthorized handler only when the captured generation is still current.
The response is otherwise processed normally, so an obsolete `401` still rejects to
its caller; only its stale global side effect is suppressed.

This is the smallest sufficient owner-level repair. It does not create another auth
provider, session store, QueryClient, API contract, backend authorization owner,
fallback, retry, or compatibility path. The existing `AuthProvider` remains responsible
for successful session publication, logout, current-session clearing, and obsolete
successful restoration containment. Query keys, team filters, deletion behavior,
mutation effects, retries, prefetch, and persistent-browser-storage policy are unchanged.

### Architecture and contract impact

- API/model/shared type: unchanged
- backend route/session/cookie/origin/CSRF/RBAC behavior: unchanged
- persistence/schema/CAS/restart behavior: unchanged
- external connector/configuration/business rule/mapping: unchanged
- React Query keys, query functions, team scoping, and mutation effects: unchanged
- dependency/framework/architecture owner: unchanged
- provider truth: unchanged; ACRA remains Mock by default, IDP Local, ownership Local,
  GoldTier Mock, and no Live integration or approval claim was added

## 6. Security review

No active auth/security finding remains in the remediation.

- A stale request cannot clear a later session, including a later session for the same
  user.
- A current-generation unauthorized response remains fail-closed and reaches the
  existing `clearSession` owner.
- The actual provider `QueryClient`, not a replacement client, is cleared in case E.
- CSRF remains sent only on unsafe requests from the token current at dispatch. After a
  current `401`, the next unsafe request has no CSRF header.
- The backend remains authoritative for session validity, Origin/Referer, CSRF, RBAC,
  team scope, capabilities, and safe inaccessible-case behavior.
- The transport change adds no logging or telemetry and retains no sensitive material.
- The diagnostic uses synthetic placeholder values only and records no real secret or
  confidential payload.
- Browser traces, screenshots, video, HAR, service workers, storage state, and output
  preservation remain disabled by the guarded Playwright configuration.
- Browser network policy remains loopback-only with the existing neutralized font
  stylesheet exception; no guard was weakened.

The runner's inherited final text still says `2 authenticated local Mock smoke tests`
although Playwright discovers and reports 3/3. This pre-existing summary text did not
change, did not suppress discovery, and is not used as the authoritative count in this
gate. The three Playwright test records are the execution evidence.

## 7. Preserved historical findings

### F-01 — CLOSED

The fail-closed recovered-intake continuation implementation and its focused regression
remain byte-identical to the accepted historical manifest. Fresh focused/full/browser
evidence is green.

### F-02 — CLOSED

The single displayed-case mutation owner and cross-control serialization implementation
remain byte-identical. Fresh focused/full/browser evidence is green.

### F-03 — AUTH/BROWSER ACCEPTANCE NOW GREEN ON THIS CANDIDATE

The earlier final gate's `FAIL` remains preserved in
`REVIEW_REWORK_UI_QUALITY_GATE.md`. It is not rewritten or retroactively converted to a
pass. This fresh re-QG obtained the predeclared three-run sequence with no assertion
failure: 3/3, 3/3, and 3/3. The historical incident cause remains unknown even though
the independently reproduced defect class is fixed.

The failed-replacement browser-fixture limitation remains the previously documented
bounded limitation. No demo fault control or fabricated browser success was introduced.

### F-04 — CLOSED

Keyboard-operable native upload controls, focus behavior, and focused tests remain
byte-identical. Fresh focused/full/browser evidence is green.

## 8. Fresh independent execution evidence

| Check | Result |
|---|---|
| `dev_context.py` | PASS; expected branch/revision and uncommitted inventory |
| Exact baseline-copy causal suite | Expected RED confirmed: 3 failed (A/B/C), 4 passed (D1/D2/E/F), 7 collected |
| Current focused auth-ordering suite | PASS: 7/7 |
| Focused auth/cache/preserved UI suite | PASS: 112/112 across 5 files |
| Full frontend Vitest | PASS: 11 files, 212/212; existing React Router SSR warnings only |
| Frontend typecheck | PASS |
| Vite production build to task-owned system-temp output | PASS: 109 modules; JS 355.09 kB / 103.23 kB gzip; CSS 61.04 kB / 13.02 kB gzip; output removed |
| Focused backend auth/RBAC | PASS: 67/67; two existing dependency warnings |
| Full backend pytest | PASS: 953 passed, 17 skipped, 5 existing warnings in 104.30 s |
| Ruff | PASS |
| mypy | PASS: 91 source files |
| Canonical contract suite | PASS: 44/44 from its canonical `tests/contract` working directory |
| Secret scanner unit tests | PASS: 8/8 |
| Secret scanner | PASS |
| `check_project_state.py` | PASS |
| `check_architecture.py` | PASS |
| `check_tooling_config.py` | PASS |
| Governance checker units, permitted run | PASS: 37/37 |
| Windows lifecycle, permitted run | PASS: 18/18 in 316.875 s; owned processes stopped |
| Guarded browser run 1 | PASS: 3/3 in 9.8 s; cleanup verified |
| Guarded browser run 2 | PASS: 3/3 in 8.7 s; cleanup verified |
| Guarded browser run 3 | PASS: 3/3 in 8.8 s; cleanup verified |
| Tracked `git diff --check` | PASS; line-ending notices only |
| Task-owned new-file final LF | PASS except the separate extra-blank-EOF finding below; all files end in LF |
| Frozen implementation/test/report hashes | PASS; unchanged before/after checks and browser sequence |

Retained non-product/environment evidence:

- the first isolated baseline-copy Vitest attempt could not spawn esbuild in the
  sandbox (`EPERM`); the identical permitted isolated run produced the authoritative
  RED result;
- a root-level `pytest tests/contract` invocation collected from the wrong import
  context and failed to locate `phase13_contract_credentials`; the unchanged canonical
  working-directory invocation passed 44/44;
- the first governance-unit invocation was sandboxed and could not remove its own
  temporary Git directories; the identical permitted run passed 37/37, and the 35 exact
  task-created directories were removed only after parent/path/name/creation-time
  validation; and
- `pre_pr_check.py` was not run because its clean committed-tree prerequisite is absent
  and publication remains a later separately authorized role.

No physical Mongo check was run because this change cannot affect its documented
schema/repository/driver/server boundary.

## 9. Finding H-01 — untracked historical Markdown fails whitespace hygiene

**Severity:** minor, docs-only, non-security publication blocker

`git diff --no-index --check` reports the following task-owned untracked additions:

- `.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md`: two-space
  Markdown hard breaks at lines 3–6 and a new blank line at EOF (reported at line 121);
- `.ai-pipeline/reports/REVIEW_REWORK_UI_IMPLEMENTATION.md`: two-space Markdown hard
  breaks at lines 3–4; and
- `.ai-pipeline/reports/REVIEW_REWORK_UI_QUALITY_GATE.md`: two-space Markdown hard
  breaks at lines 3–4, 107, 124, 141, 163, 258–259, and 442–443.

These files are untracked, so ordinary `git diff --check` does not inspect them yet.
Once staged as new files, the same added lines become staged-diff whitespace errors and
the existing publication gate would fail. This is precisely the task's pre-QG hygiene
condition; it cannot be waived by green auth/browser evidence.

Required mechanical remediation:

1. replace only those deliberate two-space hard breaks with explicit `<br>` while
   preserving wording, dates, findings, and every historical `FAIL` verdict;
2. remove only the extra blank line at EOF in the execution addendum while retaining
   one final LF;
3. record original and normalized hashes;
4. rerun task-owned-new-file whitespace/final-newline checks; and
5. obtain a fresh independent re-QG of the normalized content.

No product, auth, test, contract, or historical finding wording change is required or
authorized by this finding.

## 10. Verdict, readiness, and next action

**INDEPENDENT AUTHENTICATION/SECURITY RE-QUALITY-GATE VERDICT: PASS WITH MINOR FIXES**

- Reproduced frontend auth defect class: **reproduced, source-backed, and remediated**.
- Historical first browser timeout attribution: **still unknown**.
- Authentication/security acceptance: **PASS**.
- Current-session fail-closed security: **PASS**.
- Frontend state/cache acceptance: **PASS**.
- Guarded browser repeatability: **PASS** for the bounded three-run sequence.
- F-01, F-02, and F-04: **closed and preserved**.
- Historical `FAIL` verdicts: **preserved**.
- Task-owned evidence hygiene: **minor fix required**.
- Exact independent `PASS`: **not issued**.
- Governance/publication readiness: **blocked**.
- Publication status: **not authorized and not ready**.

The next authorized action is a separate bounded docs-only mechanical whitespace
normalization followed by a fresh independent re-QG. This report authorizes no stage,
commit, push, PR, merge, deployment, provider work, production claim, or next phase.

## 11. Final safety and Git state

The reviewed aggregate remained unchanged throughout the gate. The only repository
write by this reviewer is this assigned report. No reviewed path was remediated. No file
was staged, committed, pushed, merged, reset, stashed, cleaned, or force-updated. No
database, external provider, remote service, credential source, `.env`, private sponsor
artefact, or sibling worktree was accessed.

All task-owned browser and lifecycle processes were stopped. No listener remained on
ports 8000, 5173, 8867, or 4275, and no lifecycle/E2E runtime metadata remained.

---

# Fresh Independent Re-Quality Gate After H-01 Markdown Remediation

Date: 2026-09-20
Role: fresh independent read-only docs/auth re-quality-gate reviewer
Verdict: **PASS**

## 12. Fresh executive result

The earlier `PASS WITH MINOR FIXES` verdict and its complete evidence history remain
unchanged above. The bounded H-01 remediation is independently accepted. It changed
only the reviewer-identified Markdown whitespace in three untracked historical
documents:

- identified terminal two-space hard breaks became explicit `<br>` markers; and
- the execution addendum's one extra blank EOF line was removed while retaining one
  final LF.

Byte-level inverse reconstruction reproduces all three supplied pre-remediation hashes
exactly. This proves that wording, findings, dates, and verdict history are unchanged.
Every task-owned new Markdown file now has no trailing whitespace and exactly one final
LF. H-01 is therefore closed, no required fix remains, and the frozen candidate receives
the exact independent `PASS` required for a separately authorized publication role.

No product, authentication, cache, security, API/model/type, schema, connector,
configuration, business rule, mapping, architecture, provider-status, test, or runtime
content changed. The prior independent behavioral evidence remains applicable to the
same executable bytes. This docs-only recheck deliberately did not consume another
guarded browser sequence.

## 13. Scope, revision, and frozen content identity

- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- `BASE_SHA`, current `HEAD`, local `origin/main`, and merge base:
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Ahead/behind: `0/0`
- Current source revision: the uncommitted working tree based on the SHA above
- Verified behavioral revision: the byte-identical executable/test candidate accepted
  by sections 3-8 above
- Independently reviewed H-01 content: the normalized documents and unchanged frozen
  candidate identified below
- Change classification: `DOCS_ONLY`
- Staged paths: none
- Active Git operation: none
- Assigned report SHA-256 immediately before this authorized append:
  `f5bb221f1a984f05a81cbb230e6dbdaf3f5f0e93ca99bd3bc3e369ab1f5139d5`
- Deterministic SHA-256 over the path-sorted `SHA256  path` manifest below:
  `1ce65896da237fc092f7b1f5a18039103f3cbc391bd1a32d670269abbb129d2a`

This report is excluded from the aggregate because it is the reviewer's sole authorized
write.

| SHA-256 | Reviewed path |
|---|---|
| `96f11d53347263af6bc89e2a67f2f2f53fefed272ad8d9bf7e06435a331da273` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md` |
| `c303eb67da894ee16bfa5f798f7023c7d327783a725d4c1223851d60d364e247` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_FOLLOWUP.md` |
| `e172b74cb3dd649eb33bddc833a933c05e6cf948da991fc20e50f693809c2e40` | `.ai-pipeline/reports/REVIEW_REWORK_UI_AUTH_DIAGNOSIS.md` |
| `fe4d52ea5bb2790f45a049de365ecff14fe4fc930c82b1aa71a68bf930280cc3` | `.ai-pipeline/reports/REVIEW_REWORK_UI_IMPLEMENTATION.md` |
| `6ff739659b46565e95071d5ae872a8ad45372692e8164eefb6968abde639b3e5` | `.ai-pipeline/reports/REVIEW_REWORK_UI_QUALITY_GATE.md` |
| `623d040cb361d51839a51878a1402a279fbce4fbc3a434381b793d2541521fbc` | `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` |
| `477e06dfa2abf5ba190ab5e70842e4d23a91950787b6f8f48ff94958b5112a00` | `apps/frontend/src/api.ts` |
| `49f85aa627c09134fe2f8ec8611cf59ef5187dca7d13131f390aa326665bbc0b` | `apps/frontend/src/AuthSessionOrdering.test.tsx` |
| `6c26e08e29190cf39bbb19c57e9905dfff8bc2b3f96b221378c3fb1db1a855ca` | `apps/frontend/src/pages/CaseDetail.tsx` |
| `edfc82f145429bddd6d94777643e019098dec0184f475b2c64d0fcba0fd18090` | `apps/frontend/src/pages/DeleteCaseDialog.tsx` |
| `cfc09fe4a083edb58013059f8b6781fee4ca93e1bc5966f915d4a9dcef17396b` | `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx` |
| `f836c47ffa0628a4ea0cfd10a4013e22b38a2fdd7185e62f039531dc4ef18c8f` | `apps/frontend/src/pages/DocumentEvidencePanel.tsx` |
| `6a1e9a27bb8411b69c4a9057a9ddf3c1443dfd41cb9c1336cc03d4275db53a81` | `apps/frontend/src/pages/PriorityControl.tsx` |
| `0faefa580f454cbda7664dde98aca27839860acca4e9df030b119a2452b248c0` | `apps/frontend/src/Phase15CNavigation.test.tsx` |
| `fed28e1a9c58eff1a203a23f342ad0bcc02702b67e4eb772240ff3a72535437e` | `apps/frontend/src/styles.css` |
| `74c9687e321b5c84c1a4e09faa8ab577866bbce43666537574119d4470000c58` | `apps/frontend/src/UiV2Integration.test.tsx` |

## 14. H-01 exact-delta and hygiene verification

The normalized hashes match the remediation handoff exactly:

| File | Original SHA-256 | Current SHA-256 | Independently verified inverse |
|---|---|---|---|
| Execution addendum | `101828e18d25eeb11fc80b9cc934b7db4dfef9666aaf394261b50951ee26e01d` | `96f11d53347263af6bc89e2a67f2f2f53fefed272ad8d9bf7e06435a331da273` | Exact original reproduced |
| Implementation report | `1556f4b92b1460088012192a9df62b9b01e91bf48adbbd9253ff077761f2deb7` | `fe4d52ea5bb2790f45a049de365ecff14fe4fc930c82b1aa71a68bf930280cc3` | Exact original reproduced |
| Historical quality gate | `fc3b83cde150ea11cb79803fb3585dca82ed80e8931511c661034281f7354ae5` | `6ff739659b46565e95071d5ae872a8ad45372692e8164eefb6968abde639b3e5` | Exact original reproduced |

The inverse reconstruction changed only these normalized terminal markers back to two
spaces: addendum lines 3-6; implementation report lines 3-4; and historical quality-gate
lines 3-4, 107, 124, 141, 163, 258-259, and 442-443. Adding one LF back to the addendum's
already final-LF-terminated content restored its former extra blank EOF line. The
resulting byte hashes are the three exact original hashes above; there is therefore no
unrecorded prose or verdict change.

Fresh hygiene evidence:

- byte/regex inspection over all six task-owned new Markdown files found zero trailing-
  whitespace lines, LF-only line endings, and exactly one final LF, including this
  assigned report after the append;
- `git diff --no-index --check -- NUL <path>` for each of the six files produced no
  whitespace error; exit `1` denotes the expected content difference from `NUL`, with
  only line-ending notices;
- tracked `git diff --check` exited `0`, with line-ending notices only; and
- no historical verdict was removed or rewritten: the earlier `FAIL` and `PASS WITH
  MINOR FIXES` sections remain byte-preserved before this clearly separated append.

The actual pre-PR checker source was inspected rather than mis-run on an intentionally
dirty uncommitted tree. It rejects unstaged, staged, and untracked publication state,
then runs `git diff --check` independently over branch, staged, and unstaged tracked
deltas. Its checklist explicitly requires a separate whitespace check for task-owned
new files before staging because plain `git diff --check` cannot cover untracked
Markdown. The fresh `--no-index --check` and byte audit above satisfy that pre-staging
condition. A later publisher must still commit the reviewed content and run the complete
checker on the clean committed tree; this re-QG does not claim that later run.

## 15. Preserved authentication, security, UI, and behavioral evidence

The frozen executable candidate remains exact:

- `api.ts`:
  `477e06dfa2abf5ba190ab5e70842e4d23a91950787b6f8f48ff94958b5112a00`;
- `AuthSessionOrdering.test.tsx`:
  `49f85aa627c09134fe2f8ec8611cf59ef5187dca7d13131f390aa326665bbc0b`;
- all nine historical UI product/test paths match the accepted hashes in section 13.

The preceding independent High gate's evidence therefore remains valid for this exact
candidate: exact baseline RED (`3` failed A/B/C and `4` passed D1/D2/E/F), current GREEN
`7/7`, full frontend `212/212`, backend `953` passed and `17` skipped, contracts `44/44`,
lifecycle `18/18`, and three fresh sequential guarded suites at `3/3` in 9.8 s, 8.7 s,
and 8.8 s with cleanup. No executable, test, configuration, dependency, or runner byte
changed after those runs. A fresh focused current-candidate run passed `7/7`; its first
sandbox attempt could not spawn esbuild (`EPERM`), and the identical permitted run was
the authoritative result. Fresh project-state, architecture, and secret checks also
passed.

No additional browser run was warranted: H-01 is docs-only, the exact frozen executable
identity is unchanged, and another sequence would not add evidence about the mechanical
Markdown delta.

Finding dispositions remain:

- F-01: **CLOSED** — recovered-intake continuation remains fail-closed for any current
  failed evidence;
- F-02: **CLOSED** — the one displayed-case mutation owner and cross-control
  serialization remain unchanged;
- F-03: **CLOSED FOR CURRENT ACCEPTANCE** — the reproduced frontend defect class has a
  source-backed cause and the bounded three-run browser requirement is green; the
  historical first browser timeout remains **unknown/unattributed** and is not
  retroactively assigned to that race;
- F-04: **CLOSED** — keyboard-operable native upload controls and focus behavior remain
  unchanged; and
- H-01: **CLOSED** — exact mechanical normalization and all-new-file hygiene are proved.

The failed-replacement guarded-browser fixture limitation also remains honestly bounded:
no demo fault control, product-only setup route, interception, or fabricated success was
introduced. Its accepted deterministic evidence classification is unchanged.

## 16. Fresh focused execution evidence

| Check | Result |
|---|---|
| Inverse byte reconstruction of all three H-01 files | PASS — all supplied original SHA-256 values reproduced exactly |
| Frozen executable and historical UI hash reconciliation | PASS — 11/11 paths exact |
| Current focused auth-ordering suite | PASS — 7/7 in the permitted run |
| `check_project_state.py` | PASS |
| `check_architecture.py` | PASS |
| `check_secrets.py` | PASS |
| Tracked `git diff --check` | PASS — line-ending notices only |
| Six task-owned new Markdown `--no-index --check` audits | PASS — no whitespace errors; expected difference exit plus line-ending notices only |
| Six task-owned new Markdown byte/final-LF audits | PASS — zero trailing whitespace, LF-only, exactly one final LF |
| Browser suite | Not rerun by design — executable identity is unchanged and prior three-run evidence applies |
| Full frontend/backend/contract/lifecycle suites | Not rerun by design — exact executable/test identity is unchanged; prior independent results remain applicable |
| `pre_pr_check.py` | Not run by design — clean committed-tree publication prerequisite is absent |

## 17. Verdict and readiness

**INDEPENDENT AUTHENTICATION/SECURITY H-01 RE-QUALITY-GATE VERDICT: PASS**

- Authentication/security acceptance: **PASS**.
- Frontend state/cache acceptance: **PASS**.
- Current guarded-browser repeatability acceptance: **PASS**.
- F-01, F-02, F-03, F-04, and H-01: **closed for current acceptance**.
- Historical browser incident attribution: **unknown**, preserved without overclaim.
- Historical verdict history: **preserved**.
- Required fixes: **none**.
- Governance/publication readiness: **ready for a separate authorized publication
  role**, subject to unchanged-content verification, safe latest-main handling, and the
  clean committed-tree pre-PR process.
- Publication status: **not performed and not authorized by this review**.

This verdict authorizes no stage, commit, push, PR, merge, deployment, provider work,
production claim, or next phase. A publisher must prove that the reviewed content and
this report remain unchanged before acting under separate publication authority.

## 18. Reviewer safety and final Git state

The reviewer appended only sections 12-18 to this assigned report. No implementation,
test, planner, historical report, diagnosis report, contract, decision, configuration,
dependency, or Git index/history content was modified by this gate. No file was staged,
committed, pushed, merged, reset, stashed, cleaned, or force-updated. No browser,
database, external provider, remote service, credential source, `.env`, private sponsor
artefact, or sibling worktree was accessed.

The working tree remains the expected uncommitted candidate with eight modified tracked
paths, nine task-owned untracked paths, and no staged path. This docs-only gate started
no browser or lifecycle service. The focused test process exited, and no listener was
present on ports 8000, 5173, 8867, or 4275 at final inspection.
