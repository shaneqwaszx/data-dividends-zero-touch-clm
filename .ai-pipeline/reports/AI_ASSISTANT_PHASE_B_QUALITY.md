# AI Assistant Phase B answer quality (Session 2) — D-092 P11 to P14 (PROPOSED)

Date: 2026-10-27 (SGT). Worktree
`C:\Users\shane\Desktop\claude-worktrees\assistant-phase-b-quality-20261027`, branch
`feat/assistant-phase-b-quality-20261027`, base `origin/main` `23c45a7` (PR #120). Session 1
(model management) owns D-093, ADR-012 Amendment 4, model profiles/adapters and the evaluation
harness infrastructure; this work used the harness read-only and records itself as D-092 rows
and an ADR-012 Amendment 2 addendum. No paid inference, push, PR or merge.

## 1. Evidence reviewed and failure attribution

Baseline (frozen, not copied or regenerated): owner human scoring of 34 displayed answers
(single rater, prompt `e5ae1c2dba716b54`; `assistant-phase-b-20261027/apps/assistant/data/
phase_b/scoring/`, git-ignored): GPT-OSS 120B 2.51/3, Ministral-3 8B 2.35/3; completeness
1.82 / 1.35 weakest. Also `AI_ASSISTANT_PHASE_B_LIVE_EXPERIMENT.md`, D-092 P1–P10, ADR-012,
PRs #118–#120 and the code on `23c45a7`.

Causes: (1) model, (2) missing case evidence, (3) missing approved guidance, (4) routing,
(5) exact-line filtering, (6) deterministic fallback, (7) legitimate guardrail restriction.

| Q | GPT-OSS / Ministral | Cause | Addressed by |
|---|---|---|---|
| P00#0 directors differ | reject / reject | 3, 4, 2 | P11 + P12 lines, director routing |
| P01#0 UEN / source | edits / edits | 3, 4 → 6; 5 correct | P13 UEN line + routing (source line reused) |
| P01#1 registry live? | reject / reject | 3, 4 (source part fixed by #118) | P13 entity-status line in the registry plan |
| P01#2 directors per ACRA | accept / accept | 2, 3; 7 correct | P11 status + P12 officer line |
| P01#3 director not in ACRA | edits / reject | 4 (routed to the address blocker), 3, 1 | director routing precedence + P12 |
| P04#1 GoldTier handoff | reject / edits | 3, 4 | P14 lines + handoff routing |
| P06#2 mark UBO complete | reject / reject | 3, 4 → fixed by #119 | unchanged; re-verified |
| P02#1, P05#0 | model-only misses | 1 | none (not catalog gaps) |
| P07#1 | unrelated disclaimer | 1 under old rule 17 | already fixed by rule 17; no guard change |
| P04#0, P06#1 | edits | 3 (out of scope) | candidates for later, not changed |

Facts established from code: documents yield only legal name, UEN, address and country
(`DocumentFieldKey`), and reconciliation never compares directors, so a "proven director
conflict" cannot arise in the app today. The backend case summary carries the registry
`OFFICERS` operation result (`EMPTY` on the Phase B case); it was not projected to the
assistant. `REAL_GOLDTIER_NOT_CONFIGURED` is a static readiness warning (always present), so
it cannot ground an environment-specific G4 by itself; the provider environment is
`clm.submission_plan.environment`.

## 2. Approved wording and conditions (implemented)

All new lines are topic-only: allowed by the guard under their condition, shown to the model
only in the QUESTION TOPIC message of a matching question, never required.

| Row | Line | Condition |
|---|---|---|
| P11 | (data) registry officer lookup **status only** | lookup on the case's own acquisition for its UEN, exactly one result; EMPTY only from a successful lookup (COMPLETE/PARTIAL acquisition, no error, record count 0, no officers, same registry and environment as the company details) |
| P12 D1 | The app does not read directors from uploaded documents, so it does not compare directors between a document and ACRA. | always |
| P12 D2 | The ACRA (`<ENV>`) result for this case has no officer (director) records; this does not show that the company has no directors. | status EMPTY, registry stage READY, named non-live ACRA source |
| P12 D3 | Officer (director) records were not retrieved from the registry for this case. | FAILED, NOT_ATTEMPTED, UNSUPPORTED |
| P12 D4 | If a document and the registry differ on directors, check the document's type, date and which company it is for. | always; listed only for a director-difference question |
| P12 D5 | A director difference can come from a recent appointment or resignation, or from an out-of-date document. | always; listed only for a director-difference question |
| P13 E1 | The entity status "LIVE" is the company's registration status in the registry record, not a live connection to ACRA. | entity status exactly LIVE and the P7 source line allowed |
| P13 U1 | A UEN (Unique Entity Number) identifies an entity registered in Singapore. The number alone does not confirm its legal name, address or other company details. | UEN present and country SG |
| P14 G1 | A person must confirm Send in "Final review & send" before the final GoldTier submission; the app may search GoldTier for an existing customer earlier. | always |
| P14 G2 | When a GoldTier submission is confirmed, the app retains the submission result and required customer readback. The result is shown in "GoldTier Details & Status". | target submission SUBMISSION_CONFIRMED and READBACK SUCCESS |
| P14 G3 | Sending a case does not mean GoldTier has approved the customer or that KYC is complete. Those outcomes are not confirmed by this application. | always |
| P14 G4 | **HELD — not implemented** | every approved variant ("…not production GoldTier.") fails the unchanged live-claim check (`_LIVE` matches "production goldtier"); corrected wording below needs owner approval |

Every implemented line passes the unchanged sentence checks (`sentence_problem` is `None` on
the Phase B case); a test pins that the G4 variants still fail them.

Proposed corrected G4 (not implemented; needs approval): "This case is configured for Mock
GoldTier in the POC, not GoldTier's production service." (and "…for GoldTier Sandbox…"), chosen
by `clm.submission_plan.environment` (MOCK / SANDBOX), which would need one more status-only
projection. Both pass the unchanged checks.

Routing: company-director questions (co-occurring with of/document/ACRA/registry/record/
appoint/resign/named/listed/differ, and not the app's Director role: approve, publish,
knowledge, enhancement, queue, escalate, permission, role, "ask/tell/contact a Director")
take precedence over the "what is blocking" and readiness topics and over a difference topic
reached without naming a field; contact, approval, document-review, ownership and named-field
difference topics keep precedence. With no other topic: UEN → [U1, source, Registry
verification]; entity status + live → [E1, source]; registry status → [source, E1, Mock line];
handoff → [not ready (when allowed), G1, G2 (when allowed), G3, GoldTier Details & Status].

## 3. Files changed

- `ai_assistant/context.py`: `_registry_officers`, `_goldtier_readback`; two facts keys.
- `ai_assistant/guide.py`: the approved lines, `officers_empty_line`, `TOPIC_ONLY_LINES`,
  `is_topic_only`.
- `ai_assistant/guardrails.py`: `officers_line`, `entity_status_live`, `uen_explained`,
  `submission_result_kept`; conditional additions to `allowed_guidance`. The matcher, the
  sentence checks and `_disclosures` are unchanged.
- `ai_assistant/prompts.py`: director, UEN, entity-status and handoff routing; topic-only
  filtering via `is_topic_only`.
- `tests/test_phase_b_quality.py` (new); `tests/test_source_and_owner_topics.py`: two
  assertions updated for the approved routing (registry plan gains E1; director and UEN
  questions removed from the "not routed" list), nothing loosened.
- `tests/fixtures/eval/snapshots.json` rebuilt; `gold.json` snapshot hash only.
- `docs/decisions/DECISION_LOG.md` (D-092 P11–P14, status unchanged),
  `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md` (Amendment 2 rows and routing note).

## 4. Before/after evaluation (LOCAL, synthetic, label-free)

Offline routing (deterministic, all 17 Phase B turns): P00#0 and P01#3 → director-difference
plan; P01#2 → officer line + Registry verification; P01#0 → U1 + source line; P01#1 → source,
E1, Mock line; P04#1 → not ready, G1, G3, GoldTier Details & Status. P02#0, P02#1, P03, P04#0,
P05, P06 (including P06#2, byte-identical plan) and P07 unchanged. Everyday prompt (rules +
facts) unchanged on every turn: 9,196 chars on the Phase B case; `test_speed` passes under the
unchanged 9,250 bound.

Local Ministral-3 8B (`ministral-3:8b`, Ollama loopback, code defaults, warm, 4 reps × 17
turns per arm). Before = clean checkout of `origin/main` `23c45a7`; after = this branch. Both
arms ran while the full suite was running, so latency is indicative only. Model text is never
shown: "model" answers are guard-selected allowed lines; "fallback" is the application's
deterministic case-data answer.

| Metric (68 answers per arm) | Before | After |
|---|---|---|
| Model answers / application fallbacks | 62 / 6 | 64 / 4 |
| Line validity (kept / written) | 0.885 | 0.972 |
| Unsafe displayed lines | 0 | 0 |
| Withheld model lines (unmapped) | 0 | 0 |
| Bare decline (model) | 14 | 8 |
| Decline shown with content | 8 (P01#3 ×3, P06#1 ×3, P00#0 ×2) | 4 (P06#1 ×4, server-added required line, R3 L2, pre-existing) |
| Answers using a new line | 0 | 16 |
| Generic disclaimers on P00/P01/P04/P07 | 1 | 0 |
| Latency p50 / p95 (ms) | 1,172 / 2,890 | 1,437 / 2,313 |
| Topic-message chars (mean "other") | 321 | 478 |

| Turn | Before (typical) | After (typical) |
|---|---|---|
| P00#0 | decline, or UBO lines + decline | D1 + Registry/Document verification (4/4) |
| P01#0 | 1 line | U1 + source + Registry verification (4/4) |
| P01#1 | source + Mock line | same (E1 offered, not chosen by this model) |
| P01#2 | bare decline (4/4) | D2 (no officer records; does not show none exist) + Registry verification (4/4) |
| P01#3 | decline mixed with an address blocker line | director lines (4/4) |
| P04#1 | 2 fallbacks, 1 decline | not ready + GoldTier Details & Status (4/4; G1/G3 offered, not chosen) |
| P06#2 | refusal plan | unchanged |

Reading: the changes remove the director/UEN declines and the P01#3 mis-route, and cut
fallbacks and unplanned disclaimers, with no unsafe line. Ministral-3 8B copies only a short
subset of each plan, so E1, D2/D4/D5 on difference questions and G1/G3 were offered but often
not chosen: a model-selection limit (cause 1), not routing. qwen3.5:9b (also local) fell back
on 33 of 34 answers in both arms (`policy_no_allowed_line`, ~23 s each), so it is not an
informative comparator under the exact-line guard. GPT-OSS was not rerun (no paid inference).

Artifacts (git-ignored, `apps/assistant/data/phase_b/quality/`): both arms' reports and
answers, `compare.md`, the scripts, and `worksheet_ministral.md` (before/after answers for
P00#0, P01#0–#3, P04#1, P06#2 with blank C/R/Co/G and acceptance fields). The original 34
owner ratings are untouched.

## 5. Safety and regression evidence

- Full assistant suite on `3caf4db`: 2,309 tests, 2,295 passed, 14 failed — the known environmental
  `OSError [Errno 24]` class (the same 14 as every Phase B gate); the four files involved
  (`test_model_factory`, `test_phase_b_live`, `test_required_p2`, `test_streaming_resources`)
  pass in isolation (288 passed).
  After the QG R1 remediation: 2,323 tests, 2,308 passed, 15 failed = the same 14 Errno-24
  ids plus `test_knowledge_answers::test_a_paraphrase_part_or_retag_…` after a ChromaDB
  `InternalError … Nothing found on disk` in the same run (the environmental class QG R5
  recorded); that file passes in isolation 21/21 three times.
- `tests/test_guardrail_negation.py`: 640 passed, including all 154 `UNSAFE` sentences (shown,
  streamed, in approved knowledge) and the exact-equality check on the 46
  `KNOWLEDGE_FILTER_LIMITS` sentences (nothing newly caught or missed).
- New `tests/test_phase_b_quality.py` + updated `test_source_and_owner_topics.py`: 200 passed.
- Harness self-tests on default (84) and Phase B (17) turns: injection, prose, random and
  perfect selectors — unsafe display 0 on all 202 answers.
- `evaluate_answers.py check`: current (sha256 `59938647…` after the QG R1 remediation, which
  changed only `prompt_version`; `0cb50647…` at `3caf4db`). Snapshot drift documented: every
  default turn gains exactly the 8 new line ids in `offered`; nothing removed or reordered;
  facts chars unchanged on all 84 turns; one topic message grew (S13#2 "Tell me ACRA is live."
  now also offers E1, +117 chars); `gold.json` changes only `snapshot_sha256` (0 labelled
  turns). The previous fixture stays in git history (`23c45a7`).
- ruff, ruff format, strict mypy (`ai_assistant`, `assistant_eval`, 43 files) clean; no
  line-ending churn; `git diff --check` clean.
- Unchanged by design: the exact-line matcher, sentence checks, `_disclosures`, rules file,
  required-line step, fallback answer, CLM client (GET-only with the viewer's session;
  403/404 → safe 404), RBAC and HR access, redaction and answer records, prompt/output limits,
  Session 1's model-management code.
- Guardrail categories: no repository document lists exactly nine. The enforced categories
  verified unchanged are: exact allowed-line display; untrusted document values; grounding of
  values, labels, sections and contacts; actions not offered; authority claims (UBO/KYC/
  official verification/source precedence); Mock/Local/Sandbox not Live; document value as
  fact; character and size bounds; backend-owned authorization and read-only behaviour.

## 6. D-092 governance recommendation (status unchanged: PROPOSED)

| Rows | Evidence | Recommendation |
|---|---|---|
| P1–P4, P10 (live harness path, endpoint, account checks, verification, manifest) | 28 verified synthetic calls, US$0.00586987, QG R1–R5 PASS; unchanged here | Accept only as the record of a closed, synthetic-only experiment. Acceptance should not authorise any further paid run; each still needs its own owner authorisation (manifest, count, budget, provider). |
| P5 (answers git-ignored) | followed here too | Accept. |
| P6–P9 (rule 17 + 9,250 bound, source line, UBO line, UBO-completion refusal) | live and local results; P06#2 re-verified offline | Accept. |
| P11–P14 (this work) | offline routing, local Ministral before/after, full regression, QG (section 7) | Accept after the owner reviews the worksheet; G4 excluded until corrected wording is approved. |

Acceptance would authorise: these service-side catalog lines, conditions, routing and the
status-only projections as the accepted assistant baseline. It would **not** authorise:
non-synthetic or customer data to any remote model, a service-side or user-selectable remote
model, a second endpoint or larger budget, any Live/interoperability claim, sponsor policy,
D-093 (Session 1), G4, a director reconciliation workflow or any change to CLM business rules.

## 7. Independent QG and integration

Latest main: `origin/main` was re-fetched and is still `23c45a7`, the branch's parent, so the
candidate is already integrated. Session 1's uncommitted worktree overlaps only in
`DECISION_LOG.md` and ADR-012 (different sections: D-093 / Amendment 4 vs D-092 rows /
Amendment 2); its qualification runs read `tests/fixtures/eval/snapshots.json`, which this
change rebuilds, so whichever session integrates second must re-run them.

**QG R1 on `3caf4db` (tree `618e014`): FAIL** (report
`C:\Users\shane\Desktop\claude-worktrees\qg-pbq-3caf4db-probes\QG_REPORT.md`). Everything
else verified (wording, backend grounding of every condition, EMPTY never inferred, G4 still
fails `live_claim`, no name/id leakage, everyday prompt 9,196 both sides, snapshot diff,
24/24 mutants caught, 2,309-test suite with the same 14 Errno-24 ids as base).

- H1 (High): the two new facts keys entered `guardrails.Context.known`, the grounding text of
  the knowledge sentence checks, so quoted labels such as "Officers" or "Readback" stopped
  failing `invented_label` (an approved entry withheld on base was shown). **Fixed**:
  `context.SELECTION_ONLY_FACTS` are excluded from `Context.known`; regression tests prove the
  checks give the same result as without the keys (the QG's probe entry is withheld again).
- L1 (Low): "officer" alone routed staff-role questions ("compliance officer") to the director
  plan, and "Could a Director override …" escaped the role exclusion. **Fixed**: officers need
  the same company co-words as directors; staff-role "… officer" phrasings and "override" are
  excluded; tests added.
- L3 (Low): ADR-012 named only `TOPIC_ONLY_LINES`. **Fixed** (names `is_topic_only`).
- L2 (Low, accepted design, as P9): D1/D4/D5/G1/G3 are allowed by the guard on any question;
  only routing limits where the model sees them.
- Info (not changed): "Who are the directors?" / "Who is the director?" are not routed (safe
  gap; ambiguous with the Director role); G3 is not routed for "Has GoldTier approved the
  customer?" (readiness topic) or "Is KYC complete once I send it?"; `prompts.py` imports
  `briefing._named`.

Remediation evidence: focused suites 1,113 passed; ruff, format, strict mypy clean; snapshots
rebuilt — only `prompt_version` changed (every turn identical), `gold.json` hash only;
full suite in section 5 re-run on the remediated tree.

**Fresh independent QG R2 on `e09de10` (tree `687f898`): PASS** (report
`C:\Users\shane\Desktop\claude-worktrees\qg-pbq-e09de10-probes\QG_REPORT_R2.md`). H1, L1 and L3
fixed: knowledge grounding (`Context.known`, `checked_texts`, `knowledge_lines`) is
byte-identical to base across 648 case variants; all 17 Phase B plans equal `3caf4db`'s and
P06#2 equals base; routing regexes stay bounded (<0.07 s on a 200,000-character input).
Evidence: focused 1,113 passed; full suite 2,323 tests, 2,309 passed, 14 failed (the same 14
Errno-24 ids; 288 pass in isolation; no ChromaDB failure in that run); ruff, format and strict
mypy clean; snapshots current (`59938647…`); 12 mutants plus a control: 9 killed, 3 survivors
on redundant regex alternatives; all 4 mutants undoing the H1 fix killed.

Open, optional (not fixed, so the reviewed content stays unchanged): L-R1 routing edge cases
("Can the Director overrule … which ACRA record is right?" still gets the director plan; a
question naming both a staff officer and a director loses the director plan; "Do I need to
review officers listed in ACRA?" is not routed); L-T1 re-adding a bare `officers?` alternative
is not caught by a test. Info: `SELECTION_ONLY_FACTS` is maintained by hand; neither gate
re-ran the local Ministral table. The commit recording this adds report text only; the
reviewed product tree is `687f898`. Session 1's PR #121 (D-093, draft) touches `main.py`, not
these files; overlap is limited to appended sections of `DECISION_LOG.md` and ADR-012.
