# AI Assistant D-094 in-app OpenRouter test mode - Independent Quality Gate R2 (recheck)

Date: 2026-10-28. Reviewer: a fresh, independent QG. This reviewer did not author or remediate
the candidate and did not run R1.
Scope: the remediation of R1 findings F-1 to F-7 and A-1
(`AI_ASSISTANT_D094_IN_APP_OPENROUTER_QUALITY_GATE.md`, FAIL on CONTENT ID `b3f96317…`), and
the evidence that remediation invalidated. Unchanged R1-verified evidence is reused where its
content was confirmed to be unchanged.

## Verdict

**FAIL**

The R1 bypasses are closed. The R1 probe and every R1 variant are now refused, and the end-to-end
R1 probe sends nothing on `/chat` or `/chat/stream`. F-3, F-4, F-6, F-7 and A-1 are fixed and
verified. F-5 is narrowed as claimed.

One Medium security finding remains (R2-1), and it is in the same class as F-1. The text screen
blocks non-ASCII characters by Unicode category, but only categories L, N and M. Every other
non-ASCII character passes untokenised and unchecked, and still reaches OpenRouter. That includes:

- symbol letters: circled, parenthesised and squared Latin letters, Braille and regional
  indicators (category So);
- invisible Unicode tag characters, which carry a full hidden ASCII copy (category Cf);
- private-use characters (category Co).

End to end, an invisible tag-character payload carrying `TAN AH KOW S1234567D` (on `/chat`) and
circled letters spelling a name (on `/chat/stream`) both came back `answered_by: model`. The mock
OpenRouter received both unchanged. The DECISION_LOG T4, AI_MODEL_CONFIGURATION section 9, the
README, PROJECT_STATE and the module docstring all promise "ASCII only" or "no letters or digits
outside ASCII", so those claims are not yet true. Under the gate rules a security-boundary fix
cannot be a minor fix. The remediation is small and bounded (see R2-1).

## Frozen content identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-openrouter-local-test-20261027`,
  branch `feat/assistant-openrouter-local-test-20261027`. HEAD, base and origin/main are all
  `c36b8aff5213037d9ed0710e69f8b9afc7c8c614`.
- The candidate is uncommitted: 18 modified tracked files and 6 new product files, matching
  the brief. Nothing is staged. The only other untracked file is the R1 report, which is not
  product.
- Tracked diff sha256 `e6bc4f4a2a4be0b29e0e949ad9d8fef13478d2807546551f0483bddec392b577`
  (R1 was `70f5dcfe…`). `diff --stat`: 18 files, +715/−477 (R1: +694/−477).
- CONTENT ID at START: `9a13e4a2e79765cebfe15922423c2dfd98332d1b04d7b1ec32f65f78ac80e671`
  (matches the brief).
- CONTENT ID at END: `9a13e4a2e79765cebfe15922423c2dfd98332d1b04d7b1ec32f65f78ac80e671` (unchanged).

## Findings

| # | Severity | Location | Finding |
| --- | --- | --- | --- |
| R2-1 | **Medium** (security boundary; false assurance) | `apps/assistant/ai_assistant/synthetic_boundary.py:76-82,102`; claims at `synthetic_boundary.py:15`, `docs/decisions/DECISION_LOG.md:1276` (T4), `docs/integration/AI_MODEL_CONFIGURATION.md:171`, `apps/assistant/README.md:534`, `docs/PROJECT_STATE.md:1150` | **The non-ASCII screen is a category deny-list (L/N/M) rather than an allow-list, so other non-ASCII text is sent unchecked.** `_TOKEN=[a-z0-9]+` never tokenises these characters, and `_foreign_letters_or_digits` refuses only L, N and M. Reproduced through `check()`, where each returns `None` (inside the boundary): circled letters `ⓉⒶⓃ ⒶⒽ ⓀⓄⓌ` (So), parenthesised letters (So), squared letters U+1F130.. (So), regional indicators (So), a Braille spelling of `S1234567` (So), invisible tag characters U+E0041.. carrying `TAN AH KOW S1234567D` (Cf, not visible on screen), private-use characters (Co) and emoji. **End to end** (the `Journey` harness: HR activates through the page, the RM asks), the tag-character question on `/chat` and the circled-letter question on `/chat/stream` were both `answered_by: model` with `REMOTE_NOTICE`, and the mock OpenRouter received both texts unchanged (2 chat requests). Owner condition (4) and the documented promise ("No message may contain letters or digits outside ASCII", "ASCII only") are therefore not fully true. This is not rated High because each vector needs deliberate encoding or a crafted paste: an ordinary mistaken paste (Chinese, Cyrillic or accented names, full-width forms, ISO dates or UUIDs) is now refused. The tag-character channel is still notable, because a paste can carry text the RM cannot see. **Expected fix (not applied):** in user and assistant messages, allow only printable ASCII and whitespace, plus at most a short, named allow-list of typographic punctuation (for example `’ “ ” – — …` and NBSP), and refuse everything else, including any Cf, Co, Cn, Cs or So character. Then confirm that the service's own system messages (rules, case facts with `ensure_ascii=False`, knowledge, the `…` added by `trim_history`) still pass, or give them their own explicit allow-list. Probe: the system messages built for the Garden fixture contain no non-ASCII characters at all, so this is feasible. Add tests for each class above, plus one end-to-end test. Then, or instead, correct the five "ASCII only" statements. |
| R2-2 | Low (docs precision) | `apps/assistant/README.md:534-535`; `docs/PROJECT_STATE.md:1150` | These say "no free or split numbers". The rule as written (correctly described in DECISION_LOG T4) is at most three approved number groups **per message**. One message can therefore carry `s 85 12 17` or `s 123456 7` (verified to pass; each group must be a vocabulary number: 0-18, 25, 40, 85, 90, 97 and a few fixture numbers), and an identifier can be spread over several user turns. Two history turns, `s 1 2 3` and then `… 4 5 6`, passed and would be re-sent together as history. Say "at most three approved number groups per message" instead. |
| R2-3 | Low (docs consistency) | `docs/integration/AI_MODEL_CONFIGURATION.md:171-173` | Section 9 says the question **and history** may use only the conversation sources. The code (`synthetic_boundary.py:113`) and DECISION_LOG T4 let **assistant** history use the wider system vocabulary, with no number-group limit. Under that rule, a forged assistant turn `S 8 5 1 2 3 4 5 A` or `Ryan Tan and Olivia Koh are the directors.` passes (verified). DECISION_LOG lists this as a known limit, but the operator guide should say it too. Assistant history from the real panel is per case and holds only the service's own answers (`AiAssistantPanel.tsx` threads are keyed by case id), so this is a forging-only path. |
| R2-4 | Advisory (usability, fail-safe) | `apps/assistant/ai_assistant/synthetic_boundary.json` `conversation_vocabulary` | The conversation vocabulary does not include common case words such as `status`, `discrepancy`, `created`, `rating`, `summarise` or `thanks`. So `What is the status of this case?` is refused (`SYNTHETIC_TEXT_NOT_APPROVED`) and gets the case-data answer. Because user history is screened, **every later question in that thread is refused too** until the history window drops the turn (verified end to end). This fails closed, and the owner's four intended questions all pass, so it is not a defect. It is worth stating in the guide or covering with more synthetic questions. |
| R2-5 | Advisory (hygiene) | the new files | `remote_test.py`, `synthetic_boundary.py/.json`, `build_synthetic_boundary.py` and `test_remote_test.py` are LF, while `remote_checks.py` and the tracked files are CRLF. `autocrlf` normalises this on commit and `git diff --check` is clean, so no action is needed. |

## R1 findings - recheck

| R1 | Status | Evidence |
| --- | --- | --- |
| F-1 High | **Closed for every R1 class; residual class open as R2-1** | `check_messages` refuses L/N/M non-ASCII characters in every message. User and assistant text is tokenised as written (no time or id stripping), and user messages use `conversation_vocabulary` with at most 3 number groups. Every R1 probe is now refused: the CJK and full-width probe, full-width digits, accented names, ISO dates, UUIDs, readable dates, split NRIC, 2-digit phone groups, "Ryan Tan … 18 Garden Walk", Cyrillic, and CJK history. Also refused: Cyrillic and Greek homoglyphs in ASCII words, a combining acute on an ASCII letter, a soft hyphen (it splits a word into non-vocabulary pieces), circled digits, superscripts, math-bold letters, roman numerals, `1.2.3.4`, `s1234567d`, email-like text, and the roles `tool` or none. The R1 end-to-end probe was re-run: `case_data` with `REMOTE_BOUNDARY_NOTICE … SYNTHETIC_TEXT_NOT_APPROVED` on both routes, and **0** requests reached the mock OpenRouter. Residual: R2-1. |
| F-2 Medium | **Largely closed; R2-1/R2-2/R2-3 wording remains** | D-094 T4 and "Known limits", section 9, README, PROJECT_STATE and the docstring now state the screen and that names made of ordinary English words cannot be recognised. The "ASCII only" and "no split numbers" wording still overstates (R2-1, R2-2). |
| F-3 Medium | **Closed** | `remote_test.py:366` `await anyio.to_thread.run_sync(self._ready, messages)`. Concrete stall probe (an asyncio ticker every 10 ms beside `model.stream()`): with a `fetch` that takes 1 s (preflight), the maximum loop gap was **0.046 s** (R1: 2.02 s). With `model._lock` held for 1.5 s by another thread (standing in for the background verifier), the gap was **0.062 s**. Both streams completed with 1 mock call. `/chat` is a sync route (threadpool), so `complete()` needs no change. |
| F-4 Medium | **Closed** | `_settle_verification()` joins the `remote-verification` threads before the ledger assertions (`test_remote_test.py:379-385,546,594,609`). `tests/test_remote_test.py` was run 6 times: 45/45 passed each time. |
| F-5 Low | **Closed as claimed; residual accepted and documented** | `system_vocabulary` now has no digit-bearing token except the knowledge tags `g1-g3` and `p1-p3`. `conversation_vocabulary` (655 words) has none of tan, lee, lim, ng, koh, ong, goh or ryan. Its digit tokens all come from the Garden fixtures and generator (postal codes `018919` and `048547`, the alternative fixture UEN `11111998B`, `123456`, and small numbers). Residual: `tan`, `lee`, `lim`, `ng`, `koh`, `ong`, `goh`, `ryan`, `opq`, `sim`, `pte` and `ltd` are still in the system vocabulary, which assistant history uses (R2-3). |
| F-6 Low | **Closed** | `_ready` counts `closed_calls_after(start) + open_calls` (`remote_test.py:299`). The docs say "open calls included", "until it is activated again or the service restarts", and "the ledger cap bounds the spend". |
| F-7 Low | **Closed** | AI_MODEL_CONFIGURATION headings run 1 to 9, with section 9 last. |
| A-1 Advisory | **Closed** | `_ready` runs `check_messages` before the lock, the preflight or any request (`remote_test.py:292`). `test_the_model_itself_refuses_text_outside_the_boundary` covers both `complete` and `stream` with zero requests. |

## Owner requirements - re-verification

| Requirement | Result | Evidence |
| --- | --- | --- |
| Default off; behaviour unchanged without D-094 | Verified (reused, re-run) | The `main.py` diff contains only the `remote_gate`/`lead_notice`/`remote_boundary` additions. `remote_gate` returns `(active.model, None)` for a non-remote model. The default-off, every-condition and without-decision tests pass, and so does the full suite (below). |
| (1) D-094, (2) development environment, (5) provider, endpoint, credential and budget checks | Verified | `readiness()` is unchanged in substance. `run_preflight` is step-for-step equal to `c36b8af` `evaluate_answers._preflight` (re-read). An AST comparison of the 22 definitions moved into `remote_checks.py` against `c36b8af` `live.py` found them identical. |
| (3) case verified server-side | Verified | `check()` case/document/viewer/value/knowledge part unchanged in logic; tests pass. |
| (4) everything sent is inside the boundary | **Not fully met (R2-1)** | Case, values, documents, viewer, knowledge, and system messages built by the service: verified. No system message embeds the question or history text: `build_messages` adds the rules, case facts, trimmed history, knowledge (from approved entries), topic lines (from facts) and page terms (from facts, chosen by the question but not containing it). History roles are restricted to `user`/`assistant` (`main.py:109`). The text screen is bypassable only by non-letter non-ASCII encodings (R2-1). |
| (6) explicit HR activation | Verified (reused) | Journey test passes; activation flow unchanged since R1 apart from documented items. |
| Existing selector, chat and stream routes; no separate page | Verified (reused) | No route, page or component was added. |
| No over-blocking of intended use | Verified | Inside the boundary: `What should I do next?`; `Who are the directors of this company?`; `Which registry was used for this company, and is that registry live?`; `What documents are still missing before this case can move on?`; `What does UEN 11111999A tell me about this company?`; and several more. End to end, a 4-turn conversation of the owner's four questions (alternating `/chat` and `/chat/stream`, each with the real accumulated history) was answered by the model on every turn. A case-data answer used as assistant history is also accepted. Some ordinary words are over-blocked (R2-4, fail-safe). |
| No paid call | Verified | Mock transports and the in-memory listing only. No network, no `.env`, no Mongo, and no real key (a test sentinel). |

## Checks run (this session, on the frozen content)

| Check | Result |
| --- | --- |
| Content ID start / end | start `9a13e4a2…80e671` = brief; end identical |
| `tests/test_remote_test.py` ×6 (`-p no:cacheprovider`, `-B`) | 45 passed each run (6/6) |
| Full assistant suite (`-p no:cacheprovider`, `-B`, junitxml in scratch) | 2420 collected, 2406 passed, 14 failed: all `OSError: [Errno 24] Too many open files` (junit check), in test_model_factory 1, test_phase_b_live 1, test_required_p2 5 and test_streaming_resources 7. Those 4 files run in isolation: 288 passed, 0 failed. The count matches the implementer's evidence |
| ruff check / ruff format --check (`--no-cache`) | All checks passed; 111 files already formatted |
| mypy `ai_assistant assistant_eval scripts tests/test_remote_test.py` (cache in scratch) | Success: no issues in 59 source files |
| `scripts/build_synthetic_boundary.py --check` | synthetic boundary is current |
| `check_project_state`, `check_architecture`, `check_policy_authority`, `check_secrets`, `check_external_provider_readiness`, `check_tooling_config` | all PASS |
| Frontend `npx tsc -b --pretty false` | exit 0 |
| Frontend vitest `AiModelManagement.test.tsx` + `AiAssistantPanel.test.tsx` | 31/31 passed |
| `git diff --check c36b8af` | clean |
| Trailing whitespace / final newline, all 18 modified + 6 new files (byte-level script) | clean |
| `diff --stat` vs `--ignore-cr-at-eol` | identical (18 files, +715/−477) |
| Refactor equivalence (AST, 22 moved definitions vs `c36b8af` live.py; `run_preflight` vs `_preflight`) | identical / equivalent |
| Boundary probes (`check()`), 14 should-pass + 12 R1 + 34 new adversarial + 8 assistant-history + 2 multi-turn + 6 `check_messages` direct | R1 classes all refused; R2-1 classes pass (bypass); see findings |
| End-to-end probes (Journey, mock OpenRouter): R1 probe; tag-character and circled-letter probes; 4-turn owner conversation and the poisoned thread | R1: 0 requests; R2-1: 2 requests carrying the hidden or encoded text; owner conversation: 4/4 model answers |
| Event-loop stall probes | 0.046 s and 0.062 s max gap (R1: 2.02 s) |

Probes are in
`C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane--claude-spares-spare-6YcPey\583f9cb6-22ae-4b09-9725-20ab186f8738\scratchpad\qg094r2\`
(`probe_boundary2.py`, `test_probe_journey2.py`, `test_probe_loop2.py`). No real OpenRouter, no
non-loopback host, no `.env`, no Mongo, and no real `OPENROUTER_API_KEY`.

## Not evidenced (carried, not a finding)

- No real CLM backend Garden case was run through the boundary (fixture snapshots only).
- No real provider call (correctly, pending the owner's authorisation of the manifest, calls
  and cap).

## Readiness

Not ready for publication. A bounded remediation of R2-1 is needed: an allow-list screen for
user and assistant text, with tests, plus truthful wording. R2-2 and R2-3 are wording fixes to
make in the same pass. A fresh independent QG of the changed delta should follow. All other
evidence above may be reused if its content is unchanged. No commit, push or PR is authorised,
and none was made.

CONTENT ID at END: `9a13e4a2e79765cebfe15922423c2dfd98332d1b04d7b1ec32f65f78ac80e671` (unchanged; the verdict applies to this content).
