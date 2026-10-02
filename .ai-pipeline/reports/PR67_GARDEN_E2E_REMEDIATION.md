# PR #67 Garden E2E diagnosis and bounded remediation — 2026-10-02

## Scope and identity

Assigned task: diagnose the repeated Garden discrepancy heading failure, repair only
its proven owner, verify, independently review, and conditionally publish one small
fast-forward commit. No CI rerun before diagnosis, main integration, merge, or Phase 25.

Task-requested coordinator route: GPT-6.1 Sol / High; the coordinator's API model ID is
not separately exposed. The fresh reviewer was explicitly dispatched on that route.
Isolated managed worktree:
`C:/Users/shane/.codex-clean2/worktrees/pr67-garden-e2e-sync/data-dividends-zero-touch-clm`.
Branch: `codex/pr67-garden-e2e-sync`. Starting source/published PR head:
`0d3b88af9ac65f7ae1af8df6d175b07f77842613`; inspected tree:
`5cd032147f9333e34f09815beedd2394102bf93b`. Initial integration base and fetched
`origin/main`: `039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`. The user supplied the identical
synthetic merge tree; that merge object was not available locally. No merge-content
hypothesis was investigated. The primary and old Phase 24 checkouts were preserved.

Classes: CI_TOOLING and FRONTEND_UI verification scope; retained executable change is
E2E-only. No frontend cache policy or product rendering change. Existing source,
requested owner files, selected development context, relevant Phase 24 planner/gate,
and only the requested PR #52 document synchronization sections were read.

Current-session capabilities: shell/file tools, managed worktree lifecycle, GitHub CLI,
configured Playwright harness, and fresh independent subagent review. Python 3.12.10,
Node 22.23.3, pinned Playwright 1.56.1/Chromium. Task-local virtualenv and locked npm
dependencies installed; no manifest or lockfile change. Windows local execution,
Ubuntu GitHub failure evidence. Harness-owned loopback ports only; memory persistence,
offline synthetic ACRA protocol and Mock GoldTier; no external provider or Mongo work.
No `.env`, credential, confidential sponsor artefact, body, or provider payload read.
Diagnostic logs are task-owned ignored `.log` files, excluded from publication.

## Diagnosis

Existing GitHub evidence was read, not rerun: PR workflow
`36975135420`, attempts 1 and 2, both fail at original Garden line 116 with the same
15,000 ms accessible-heading absence. Push workflow `36975109505` passed. The second
failed E2E job is `110742572676`. Other PR lanes passed. The Node action and runner
future notices do not explain this failure.

The panel heading renders unconditionally with `documents=[]`. `StageDisclosure`
keeps its body mounted and hides it when closed. `CaseDetail` derives identity conflict
from current document evidence plus an open registration discrepancy. Initially the
fresh cached summary points at DOCUMENT, so Documents is active. When the document
query commits its conflicting UEN, Registry identity becomes active and Documents
becomes inactive. The existing `active` effect then closes Documents, as its component
test explicitly requires. `openStage` can have already returned on expanded=true.
The following accessible heading assertion sees no matching accessible element because
the ancestor is hidden, even though `#documents-heading` remains mounted.

Deepest confirmed boundary: **J — query-derived active-stage transition closes the
disclosure after the test observed expansion**. This is a test readiness race across
document-query publication and existing disclosure semantics. It is not an unmounted
child, failed selector, stale document value, or incorrectly advanced backend state.
The exact CI runs have no internal milestones; attribution to this mechanism is
supported by source, repeated local transitions, and the exact controlled symptom,
not a claim to have observed CI's internal query state.

## Reproduction

Ten fresh baseline lifecycles used the exact discrepancy title, Garden protocol,
60-second lifecycle deadline, ports 9210–9219 / 5210–5219. Nine whole-selector PASS;
one later failure on a disabled legal-name review control. The original heading
assertion passed in all ten uncontrolled runs. All ten showed successful document GET,
mounted heading, and expanded -> collapsed -> reopened Documents. The later disabled
control failure is separate unresolved baseline evidence, not assigned as this root.
One preceding exploratory run also passed. An anchored grep initially discovered no
tests and is excluded from all reproduction counts.

Times below are milliseconds. Route/first expansion/heading mount and closure use
browser monotonic time since document bootstrap; document completion uses the Node
observer's monotonic time since beforeEach. These clocks are separate and must not be
subtracted. Route and initial heading/expansion share the first committed DOM event.

| Run | Route / heading / first expansion | Document dispatch | Document completed 200 | Documents closes | Whole selector |
|---:|---:|---:|---:|---:|---|
| 1 | 1132 | 1145 | 1206 | 1235 | PASS |
| 2 | 1079 | 1091 | 1140 | 1161 | PASS |
| 3 | 1087 | 1101 | 1136 | 1157 | FAIL: later review disabled |
| 4 | 1070 | 1082 | 1151 | 1164 | PASS |
| 5 | 1140 | 1156 | 1221 | 1224 | PASS |
| 6 | 1141 | 1156 | 1193 | 1214 | PASS |
| 7 | 1254 | 1267 | 1328 | 1347 | PASS |
| 8 | 1077 | 1089 | 1159 | 1171 | PASS |
| 9 | 1148 | 1160 | 1216 | 1240 | PASS |
| 10 | 1051 | 1072 | 1124 | 1142 | PASS |

No browser detail GET was dispatched on initial CaseDetail entry in these runs: App
already published the authoritative case summary into the actor/case cache, within
the configured 45-second stale time. CaseDetail rendered that summary. This expected
cache reuse does not explain a missing child heading. Documents requests were
dispatched; transient StrictMode generation aborts were followed by completed 200
responses. Query commitment is evidenced by rendered current document cards and UEN
choices, not inferred merely from response headers. Successful final backend state
was WAITING_FOR_REVIEW / READINESS; the separate disabled-review run remained DOCUMENT.
The clean Garden neighboring selector passed in its own lifecycle on 9230 / 5230.

Failing-first controlled reproduction, before the fix, on 9240 / 5240:
hold the real browser documents GET; navigate; await unchanged openStage; prove expanded;
release GET; observe Use document UEN and Documents collapsed; prove heading DOM count=1;
run the original visible heading assertion. **FAIL at 15,000 ms, element(s) not found**.
Direct backend summary remained WAITING_FOR_REVIEW / DOCUMENT. This reproduces the
exact synchronization defect without sleeps, timeout inflation, reloads, or retries.

Executed failing-first command (temporary diagnostic selector, prior to repair):
`.venv/Scripts/python.exe scripts/run_e2e.py --grep 'Garden document arrival after expansion reproduces hidden heading' --garden-protocol --timeout-seconds 60 --backend-port 9240 --frontend-port 5240`.
Execution session 88317 completed with exit 1; retained tool-output excerpt:

```text
PR67_CONTROLLED {"status":"WAITING_FOR_REVIEW","current_stage":"DOCUMENT","expanded":"false","heading_mounted":true}
Locator: getByRole('heading', { name: 'Document evidence and review' })
Expected: visible
Timeout: 15000ms
Error: element(s) not found
1 failed
```

The temporary selector asserted heading DOM count=1 before this safe projection and
visible-heading assertion. It became the retained controlled regression after diagnosis;
temporary diagnostic instrumentation was removed. This excerpt is transcribed from the
actual tool output, not a second run or a manufactured passing/failing log.

Historical comparison: **DIFFERENT CLASS** from PR #52's backend-reviewed-count advances
while frontend state remains stale. Here current documents commit correctly and cause
a supported UI stage transition. PR #52's generic initial-data-readiness lesson is
relevant, but its refresh head-of-line/stale-overwrite repairs are not this owner.

## Minimum repair and preserved boundaries

Decision: **code-change, E2E-only**. A fixed delay or CI rerun cannot establish the
prerequisite; changing product stage behavior would contradict the existing tested
contract. The minimum owner is Garden's fixture-specific case inspection helper.
Architecture review required: no; no owner, API, framework, or dependency replacement.
Failing-first route: controlled real-browser reproduction above.

Extract startGarden so delayed-response regressions can hold document evidence without
deadlocking case creation. Preserve every original acquisition assertion in that shared
setup. openGardenDocuments waits for one current document card (query data committed)
and, for the conflicting fixture, visible Use document UEN (derived active-stage effect
settled). It then uses unchanged openStage and the unchanged heading assertion.
The retained controlled test demonstrates automatic closure when conflicting evidence
arrives after expansion, followed by explicit inspection after readiness. The existing
delayed-field-review test retains all four accepted-field/event/state assertions.

No added timeout, sleep, reload, test retry, catch-and-ignore, skip, or weakened heading
assertion. Generic openStage and StageDisclosure are unchanged. The invalid assumption
that expanded=true guarantees stable visibility across pending document data is retired
only in the Garden helper; legitimate automatic active-stage behavior is preserved.

Product API/type, schema, connector, configuration, business rule, mapping, auth/security,
architecture, provider classification, and runtime behavior: **UNCHANGED**. Browser test
orchestration/readiness and regression coverage: **CHANGED**.

## Verification and publication

Frozen executable path: `apps/frontend/e2e/garden-happy-path.e2e.ts`.
Byte SHA256: `2bf540448fc457d34d9821390aa760cfb855d99686e5e6d44761db626696a525`.
Git diff SHA256: `b66c00c90d66b84bd85bd98392a4c08593b7c3435bb69e9f670c543e54752072`.
Source, tested content and independent review are recorded separately; independent
review and publication are distinct stages; this implementation evidence supplies no
independent verdict. Publication receipts are returned after the gate in the final chat.

| Check | Current evidence |
|---|---|
| Controlled race after fix | PASS on 9241 / 5241; retained regression also PASS on final content |
| Initial post-fix exact matrix | 10/10 consecutive isolated PASS, 9250–9259 / 5250–5259 |
| Final-content exact matrix | 10/10 consecutive isolated PASS, 9300–9309 / 5300–5309 |
| All Garden selectors | 5 selectors / 5 instances PASS, isolated lifecycles |
| Phase 24 identity | 3 selectors / 4 instances PASS, isolated lifecycles |
| Phase 24C policy | 2 selectors / 7 instances PASS, isolated lifecycles |
| Full configured E2E twice | Both PASS: 32 selectors / 39 instances each, 351.062 and 348.203 seconds |
| Affected frontend components | 4 files / 65 tests PASS |
| Full frontend | 35 files / 388 tests PASS; existing act/layout-effect warnings |
| Typecheck / build | PASS; existing large-chunk build warning |
| npm dependency integrity | PASS; platform/feature optional dependencies not installed |
| Ruff scripts/tests | PASS |
| Project-state / architecture / tooling / policy / provider-readiness / secrets / tracked and new-report whitespace | PASS |
| Runner/security/pre-PR unit regressions | 96 executed: 95 PASS / 1 baseline Windows fixture FAIL; see limitation below |
| Independent gate | Separate fresh reviewer report; implementer does not issue PASS |
| Official clean committed pre-PR | Publication-stage receipt in final chat, after independent acceptance and the single scoped commit |

Backend product, physical Mongo, external providers and Windows demo lifecycle are
unaffected and were not rerun. Existing CI evidence is not substituted for fresh affected
acceptance. Conditional publication requires independent PASS on unchanged reviewed
content, exact original remote PR head, official clean-state pre-PR, and one scoped
fast-forward commit. Human merge remains required.

Additional tooling-unit limitation: the first sandbox execution had eight fixture-write
permission errors and one fixture failure; it was not passing evidence. The narrowly
elevated rerun removed those permission errors but still failed
`test_exact_three_historical_patches_pass_committed_checker`. That unchanged test copies
three historical patch files from the CRLF Windows checkout into a `core.autocrlf=false`
temporary repository, where their pinned LF hashes and whitespace check fail. Each
checkout file normalized from CRLF to LF exactly equals its unchanged HEAD Git blob.
The checker, historical files and test were not modified to accommodate this unrelated
fixture issue. This optional broader unit aggregate is reported FAIL, not PASS; official
clean-state pre-PR must still independently pass using the actual committed Git blobs.

## Publication checklist handoff

The executable and supporting diagnosis report are frozen for independent review.
No implementation changes are authorized during publication. The published Phase 24
delta is pre-existing reviewed content; the bounded repair adds only this E2E file,
this supporting report, and the independent gate report. Dependencies and CI jobs are
preserved. Current product contracts and main behavior are unchanged.

After exact independent PASS, the coordinator must verify hashes and scoped staging,
create the one authorized commit, fetch again, check latest-main ancestry and original
PR head, run the official clean committed pre-PR, then fast-forward push HEAD to
`feat/phase24-registry-identity-ownership-ubo` only if the head remains
`0d3b88af9ac65f7ae1af8df6d175b07f77842613`. No force push or merge. The clean committed
state requirement in the official workflow/checker determines this ordering; running
the official checker on intentionally uncommitted implementation would fail its gate.
Final chat must include commit/remote identity, actual pre-PR outcome, separate push/PR
workflow receipts and pending CI truth. It must not transfer this local evidence to
remote execution or claim human merge has occurred.
