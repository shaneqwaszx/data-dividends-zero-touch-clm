# AI Assistant explanations (D-090, ADR-012 Amendment 2) - independent quality gate, recheck R6 (R5 remediation)

Reviewer: fresh independent QG subagent. It did not author or remediate the reviewed content
and did not run the first gate or R1-R5. Date: 2026-10-26. Skill:
`.agents/skills/fyp-quality-gate/SKILL.md` and `references/report-template.md`, read in full;
AGENTS.md invariants, secrets, Git and verification sections read. R5 report read in full
(FAIL on `64e3f57`: R5-B1, R5-M1, R5-M2, notes N13, N14).

Scope agreed with the owner (option (a): redact in records, no wider ADR-012 section A
relaxation): commit `f6a64a4` only, i.e. `git diff 64e3f57 f6a64a4`, plus the evidence it
invalidates.

## Reviewed content identity

| Item | Value |
| --- | --- |
| Checkout | `/Users/tasha/Documents/GitHub/dd-clm-qg-explanations`, detached, clean at start and end (apart from this report) |
| HEAD | `f6a64a4ab0a8f85ce957f1014c5ba9a2a3cd89d0` |
| Tree | `c5b7eae709ebccb6593cc553da7eaef146e21e98` |
| Recheck delta | `git diff 64e3f57 f6a64a4 --stat`: `answer_records.py` (+14/-3), `main.py` (+9/-9), `test_answer_records.py` (+43), `RequestPage.tsx` (1 line), ADR-012 (+5), DECISION_LOG (1 line), R5 report (new). Nothing else changed since R5's review. |

## 1. Executive result

**PASS WITH MINOR FIXES.** R5-B1 is fixed: on both paths (model and case data, streamed and
not) no ACRA or document value, UEN, company name, address part or case-valued blocker title
reaches any record field other than the question (allowed by D-084 D1), nor any Director or RM
record endpoint, nor the fix-start lines. Chosen lines still map to their allowed sources and
"start a fix" still treats chosen allowed lines as allowed. The new tests fail on the pre-fix
code and pass now. R5-M1 and R5-M2 are fixed. All assistant checks and the two assistant E2E
tests pass. One minor remains: three durable descriptions of the record still say only "a
case-data answer" is redacted (R6-M1), which understates, not overstates, the redaction.

## 2. Acceptance checklist

| Claim | Result | Evidence |
| --- | --- | --- |
| R5-B1: every non-policy allowed line (case and knowledge) stored redacted; policy lines kept | VERIFIED | `answer_records.py:63-86`; `main.py:438`. Probe on Merlion and Garden facts: no raw value in any `allowed_lines` text; difference line stored as `Registered address: ACRA says "[ADDRESS]", the document says "[ADDRESS]".` |
| R5-B1: `chosen_lines` and `shown_answer` redacted for model and case-data answers | VERIFIED | `main.py:440-447`; API probe (below), 12 cases, 0 leaks. |
| Knowledge lines carrying case values | VERIFIED | Unit probe: a knowledge line naming `MERLION CIRCULAR LABS PTE. LTD.`, `25 Robinson Road`, `048547` (Merlion) and `Garden Business at 18 garden  walk` (Garden, odd case and spacing) stored without the values. |
| Who-resolves template with a case value in the title | VERIFIED | Probe: title `Address 25 ROBINSON ROAD review` stored as `Address [ADDRESS] review: this is for the document reviewer.` |
| Director/RM endpoints and request page carry no values | VERIFIED | API probe calls `/assistant/knowledge/feedback/{id}/answer`, `/fix-start` (Director) and `/assistant/answers/{id}` (asking RM): 0 leaks outside `question`. `RequestPage.tsx` renders only these fields. |
| `fix_start_lines` still treats chosen allowed lines as allowed | VERIFIED | Same `redact` instance for both (`main.py:417`); new test asserts `fix_start_lines(stored, identity) == []`; API probe: fix-start is empty for catalog-only answers and holds only the non-allowed model sentences (redacted) otherwise. |
| Redactor deterministic/idempotent for the comparison | VERIFIED | Pure regex substitution with a fixed, length-ordered pattern list per request; probe: `redact(redact(x)) == redact(x)` for every allowed line on Merlion and Garden, and `redact(p) == p` for all 13 `POLICY_LINES` on both. See N16 for the general (non-fixture) caveat. |
| RequestPage `sources.get(line)` still maps | VERIFIED | API probe: every stored chosen line is a key of the stored allowed lines (0 unmapped) in all catalog-answer cases. |
| Nothing relying on raw record text silently weakened | VERIFIED | Only consumers: `knowledge_api.py:273-277` (pass-through), `fix_start_lines`, `RequestPage.tsx`. `test_fix_prefill.py` and all `test_answer_records.py` assertions unchanged and passing (`allowed_line()` returns line 0, a policy line, still raw). |
| New tests fail without the fix | VERIFIED | Scratch copy of `f6a64a4`'s `apps/assistant` with `answer_records.py` and `main.py` from `64e3f57`: both new tests FAIL (`test_a_record_keeps_no_acra_or_document_values_from_catalog_lines`, `test_a_case_data_record_keeps_no_values_from_catalog_lines`), other 75 pass. |
| R5-M1: topic question record keeps the added lines | VERIFIED | `test_answer_records.py:797-818`: `added_lines == [0, 1, 2]`, 4 chosen lines == answer lines, no values. |
| R5-M2 wording | VERIFIED | `RequestPage.tsx:195`: "only allowed lines are shown, in the catalog's own words", consistent with ADR-012:616 and DECISION_LOG:1127. |
| ADR-012 Amendment 2 and D-090 E2 accurate | VERIFIED | `ADR-012:558-561`, `DECISION_LOG.md:1121` match the code; section A relaxation stays the D-084 D1 one (question + case-state snapshot). |
| Other durable descriptions current | **NOT FULLY (R6-M1)** | Section 5. |

## 3. Contract and integration findings

- No contract, schema, connector, configuration or backend change. Record JSON shape is
  unchanged (same fields, same tags); only the text is redacted. D-084 and D-090 remain
  PROPOSED; no live ACRA, GoldTier or sponsor claim.
- R5-B1 closed under option (a); section A is not widened.

## 4. Tester and adversarial findings

Run by this reviewer on HEAD `f6a64a4` / tree `c5b7eae`, local macOS, repository venv,
`PYTHONDONTWRITEBYTECODE=1`, caches off or in the scratchpad:

| Check | Result |
| --- | --- |
| `cd apps/assistant && python -m pytest -q -o addopts="" -p no:cacheprovider` | **1763 passed** in 77 s |
| `ruff check --no-cache .`; `ruff format --check --no-cache .` | All checks passed; 82 files already formatted |
| `mypy ai_assistant`; `mypy assistant_eval` (cache in scratchpad) | no issues in 28 files; no issues in 9 files |
| `python scripts/evaluate_answers.py check` | snapshots are current (84 turns, sha256 1421eedb7fd536ea) |
| `npx vitest run src/pages/KnowledgeReview.test.tsx src/pages/AiAssistantPanel.test.tsx` | 2 files, 55 passed (no RequestPage-specific test file exists) |
| `npx tsc -b --noEmit` | exit 0 |
| `scripts/run_e2e.py --backend-port 49265 --frontend-port 45673 --selectors-file` (`assistant-answer-records.e2e.ts:12`, `assistant-streaming.e2e.ts:10`) | **PASS 2/2** (`scratchpad/qg-r6/e2e-r6.json`); no other `run_e2e` was running |
| `git diff --check 64e3f57 f6a64a4`; `scripts/check_secrets.py` | clean; no supported secret patterns |
| Probe `scratchpad/qg-r6/probe/test_r6_probe.py` | 19 passed, 3 "failed" by design (N15) |

Probe detail (API level, Garden fixture, question "Explain the registered address
difference", each streamed and not): model answers (a) the raw D-090 difference line,
(b) the same lower-cased in Markdown, (c) a non-allowed who-resolves line, (d) the difference
line plus a sentence naming the company, address and UEN, (e) model down, (f) nothing allowed
(case-data fallback). For each, the stored record minus `question`, the Director `/answer`,
Director `/fix-start` and RM `/assistant/answers/{id}` responses were scanned for
`OFFICIAL MOCK STREET`, `GARDEN WALK`, `123456`, `018919`, `11111999A`, `GARDEN BUSINESS`,
`#01-01`: **0 hits**. Unit level: same scan with the Merlion values (`INNOVATION WAY`,
`ROBINSON ROAD`, `018956`, `048547`, `202400001A`, `MERLION`, `#04-01`): 0 hits.

Reused, not rerun: full frontend vitest 1109/1110 (macOS-only `ViteHistoryFallback.test.ts`)
and `npm run build` (developer, on `f6a64a4`). `pre_pr_check.py` not run (publication step).
CI has no `apps/assistant` job and is billing-blocked; all evidence is local, not hosted CI.
The reviewer's imports created the ignored `apps/assistant/data/` (born 15:08 in this session);
it was removed.

## 5. Code and architecture review

- **R6-M1 (minor, durable docs):** three descriptions still say the shown answer is stored
  "with a case-data answer redacted", implying a model answer is stored as is:
  `apps/assistant/ai_assistant/answer_records.py:7`, `apps/assistant/README.md:194-195`,
  `docs/ARCHITECTURE.md:988-989`. They should say all record copies of non-policy lines and the
  shown answer are redacted (as ADR-012:558-561 now does). Errs on the safe side, so not
  blocking.
- **N15 (note):** `Redactor` only knows values of 3+ characters (`redaction.py` `add`, `len(text)
  >= 3`), while `_safe_template_text` accepts 1-2 character values; the probe shows a document
  value `AB`, `X` or `Q7` stays in the stored difference line. Such a value cannot identify a
  client in practice, so this is recorded, not required.
- **N16 (note):** policy lines are stored unredacted in `allowed_lines` but chosen lines are
  always redacted. `_flexible` has no word boundaries, so if a case's known value (3+ chars,
  e.g. a party name) happened to occur inside a policy line, the chosen copy would be redacted,
  would no longer map to its `policy` source on the request page, and would appear as a
  fix-start line. Over-redaction only (no leak); not observed on Merlion or Garden.
- **N17 (note):** redaction can make two distinct allowed or chosen lines identical (e.g. two
  who-resolves lines whose titles differ only by a case value); `RequestPage.tsx:182` uses
  `key={line}`, giving a React duplicate-key warning. Cosmetic.
- R5 notes N13 and N14 and earlier notes N1, N4, N5, N7, N11, N12 stand.

## 6. Security review

- R5-B1's exposure (registry and document values in clear in the local record store and on
  the request page) is closed; the remaining unredacted record field is the RM's question, as
  D-084 D1 states. Redaction is the existing case `Redactor`, applied once per request with one
  instance. No secret, `.env`, token or tracked protected data involved.

## 7. Required fixes

1. **R6-M1 (minor):** update the three "case-data answer redacted" descriptions
   (`answer_records.py:7`, `apps/assistant/README.md:194-195`, `docs/ARCHITECTURE.md:988-989`).
   Comment/doc only; a recheck needs only `git diff` review plus `ruff format --check`.

## 8. Readiness

- Branch quality gate: **PASS WITH MINOR FIXES** on `f6a64a4` / `c5b7eae`, for R6-M1 only.
- Unchanged from R4/R5: before a PR the branch still needs Shane's acceptance of D-090 (incl.
  E2) and D-084, his review of the #115 runner and fixture changes, an owner decision on the
  not-green full E2E (pre-existing failures on main), his manual-CI exception, and
  `python scripts/pre_pr_check.py` on the clean committed tree.
- No live ACRA verification or real GoldTier integration readiness is claimed or affected.

## 9. Git status

- Checkout detached at `f6a64a4ab0a8f85ce957f1014c5ba9a2a3cd89d0`, tree
  `c5b7eae709ebccb6593cc553da7eaef146e21e98`; nothing staged or modified. This report is the
  only new file (untracked).
- No implementation, test or doc fix, commit, push, merge, rebase, reset or stash was made.

Reviewed HEAD: f6a64a4ab0a8f85ce957f1014c5ba9a2a3cd89d0
Reviewed tree: c5b7eae709ebccb6593cc553da7eaef146e21e98

PASS WITH MINOR FIXES
