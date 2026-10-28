# AI Assistant D-094 in-app OpenRouter test mode - Independent Quality Gate R3 (recheck)

Date: 2026-10-28. Reviewer: a fresh, independent QG. This reviewer did not author or remediate
the candidate and did not run R1 or R2.
Scope: the remediation of R2 findings R2-1 to R2-4
(`AI_ASSISTANT_D094_IN_APP_OPENROUTER_QUALITY_GATE_R2.md`, FAIL on CONTENT ID `9a13e4a2…`),
plus the evidence that remediation invalidated. Unchanged R1/R2-verified evidence is reused
only where it was re-confirmed below.

## Verdict

**PASS WITH MINOR FIXES**

R2-1 is closed. The text screen is now an allow-list: printable ASCII, `\n`, `\r`, `\t` and
nine named typographic marks. Every R1 and R2 bypass class is refused, both directly and end
to end. **0** requests reached the mock OpenRouter on `/chat` and `/chat/stream`.

R2-2 and R2-3 are implemented as described:
- user turns may hold at most three number groups per request, never two side by side;
- assistant turns use conversation plus prompt vocabulary, with no run of more than three.

R2-4 is improved.

The owner's intended Garden questions pass. So does a multi-turn conversation that sends the
model's real allowed-line answers back as history: an 8-turn end-to-end run was answered by
the model on every turn, and all 2,567 distinct service lines from every fixture scenario
passed when sent back as assistant history.

One Low documentation finding remains (R3-1). The known-limits text says the screen refuses
"split numbers". In fact, deliberate ASCII-only encodings still pass: Morse or punctuation
codes, spelled-out number words, and a hand-built assistant turn carrying digit runs. The
code does what T4 states. Only the summary of the limits overclaims, and every vector needs
deliberate encoding or forging by the owner, the only authorised user. The fix is a bounded
wording correction, with optional code hardening.

## Frozen content identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-openrouter-local-test-20261027`,
  branch `feat/assistant-openrouter-local-test-20261027`. HEAD, base and origin/main are all
  `c36b8aff5213037d9ed0710e69f8b9afc7c8c614`.
- Uncommitted: 18 modified tracked files and 6 new product files. The only other untracked
  files are the R1 and R2 reports, which are not product. Nothing is staged.
- Tracked diff sha256 `f7ede4961062f84778f654f0a5bdf5d860c1dbe4efccb35de8f52ef594d46058`.
  `diff --stat`: 18 files, +731/−477, identical with `--ignore-cr-at-eol`.
- CONTENT ID at START: `967024b414c9198d19777818ad0c9cf738286d3ba4ce31c0079419a41ac48fe1`
  (matches the brief).
- CONTENT ID at END: see the last line. It was re-computed after all checks and before and
  after writing this report.

## Findings

| # | Severity | Location | Finding |
| --- | --- | --- | --- |
| R3-1 | Low (docs: known-limit precision) | `docs/decisions/DECISION_LOG.md:1283-1291`; `docs/integration/AI_MODEL_CONFIGURATION.md:182-183`; `apps/assistant/README.md:539-540`; `docs/PROJECT_STATE.md:1150-1153`; `apps/assistant/ai_assistant/synthetic_boundary.py:25-26` | **The known limits say the screen refuses "unapproved numbers and split numbers". Deliberate ASCII-only encodings still pass**, and the docs do not name them. Reproduced through `check()`, where each returns `None`. **(a)** Punctuation-only codes produce no tokens. Examples: Morse `... .---- ..--- ...--` and `- .- -. / .- .... / -.- --- .--` (TAN AH KOW), tally marks `! !! !!!`, and `a`/`i` binary. **(b)** Number words `zero one two four` are in `conversation_vocabulary` and do not count as number groups, so `s one two four zero one two four` passes. `seven` is in the prompt vocabulary for assistant turns. **(c)** A forged assistant turn may hold unlimited number groups in runs of up to three, separated by a word. `S 1 2 3 the 4 5 6 the 7` passes, and so does `1 a 2 a 3 a 4 a 5 a 6 a 7 a 8 a 9`. Combined with three user groups, this also passes. **(d)** The cap of three user number groups applies per request, not per conversation, so separate requests can each carry three. **End to end** (Journey, mock OpenRouter), the Morse question (`/chat`), the number-word question (`/chat/stream`) and the forged-assistant digit run (`/chat`) were all `answered_by: model`, and all three texts reached the mock (3 requests). T4 and section 9 describe the rule correctly ("no run of more than three number groups" for assistant history). The overclaim is only the Known-limits bullet and the missing statement that deliberate encodings and hand-built history are not detectable. Rated Low and not Medium, consistent with R2-2 and R2-3, because: no accidental paste reaches the model (other scripts, symbols, invisible characters, dates, ids, NRIC/UEN shapes, emails, phone groups and unapproved numbers are all refused); every vector needs deliberate encoding or crafting an HTTP request outside the panel; and D-094 limits use to the owner on their own machine. **Expected fix (not applied):** state in the five places that the screen guards against accidental entry, not deliberate encoding (punctuation or Morse codes, spelled-out numbers, a hand-built assistant history turn with separated digit runs), and that the number cap is per request. Optional hardening: count number words as number groups, apply the total cap to assistant turns as well, and refuse long punctuation-only runs. |
| R3-A1 | Advisory (over-blocking, fail-closed) | `synthetic_boundary.py:143-145`; fixture `tests/fixtures/eval/scenarios.json:289` | The fixture question `Is a score of 0.97 a probability?` (scenario C05) is refused, because `0.97` tokenises to two adjacent number groups. Because user history is screened, the rest of the C05 conversation is refused too. 99 of the 101 fixture questions pass; the 2 refused are this one and the C05 follow-up. |
| R3-A2 | Advisory (over-blocking, fail-closed) | `synthetic_boundary.py:134-140` (no time stripping for assistant turns) | **A case-data answer that contains a readable time** (`… 04 Oct 2026, 18:04 UTC`) is refused when it is sent back as assistant history (`2026`, `oct`, `utc`). This happened for 9 of the 202 answer/history combinations, including the case-data answer to the owner's question "Which registry was used for this company, and is that registry live?". If a remote call falls back (failure, budget, breaker), the thread then sends nothing until the history window (2,400 characters) drops that turn. Model answers are not affected: all 2,567 allowed lines, topic lines, knowledge lines and opening messages pass as assistant history. |
| R3-A3 | Advisory (over-blocking, fail-closed) | `scripts/build_synthetic_boundary.py` `EVERYDAY_WORDS` | Some ordinary follow-ups are still refused: `Who needs to fix it?`, `OK, thanks.`, `What is blocking this case?` (`blocking` is prompt-only) and `How long will this take?`. 24 of 28 sampled follow-ups pass, including `What does that mean?`, `Can you explain that?`, `Tell me more.`, `What's next?` and `Summarise this case for me.`. |
| R2-5 | Advisory (carried, no action) | new files | The new files are LF and `remote_checks.py` is CRLF, as R2 recorded. `docs/PROJECT_STATE.md` is mixed CRLF/LF in the HEAD blob too (655 CRLF / 474 LF). The working copy adds exactly 24 CRLF lines, and the stat equals `--ignore-cr-at-eol`. |

## R2 findings - recheck

| R2 | Status | Evidence |
| --- | --- | --- |
| R2-1 Medium | **Closed** | `_unchecked_characters` (`synthetic_boundary.py:86-92`) allows only `" " <= c <= "~"`, `\n\r\t` and `_TYPOGRAPHIC` = `‘’“”–—…·•` (line 71). It runs for every message and every role before tokenising (line 124). Refused, all 30 probes: tag characters (Cf) with a hidden `TAN AH KOW S1234567D`, circled, parenthesised and squared letters, Braille, regional indicators, private use, emoji, ZWSP/ZWJ, the math-bold S, superscripts, the fraction slash, NBSP, U+202F, U+2011 non-breaking hyphen, ideographic space, soft hyphen, combining acute, bidi override U+202E, variation selector, DEL, VT, FF, NUL and a lone surrogate. The nine typographic marks each pass as separators and are never tokenised, so they carry no letters. **End to end**: 7 question probes (the R1 probe, tag, circled, Braille, emoji, ZWSP and `s 85 12 17`) × 2 routes, plus 2 history-borne probes (a forged assistant turn in circled letters, user history with tag characters) × 2 routes. All gave `case_data … Reason: SYNTHETIC_TEXT_NOT_APPROVED.`, and **0** requests reached the mock OpenRouter. The service's own system messages still pass: the full fixture sweep and the journeys answered normally. |
| R2-2 Low | **Closed (code and docs); residual in R3-1** | `user_numbers` accumulates across user turns (`:143`), and `_longest_number_run(words) > 1` is refused (`:144`). Verified: 3 separated groups pass; 4 are refused; `18 01` is refused; `s 85 12 17` and `s 123456 7` are refused; 2+2 across turns is refused; 2+1 passes. `1-2`, `1.2`, `1_2`, `1…2`, and digits split by `\n`, `\t` or `\r` are all refused (adjacent). |
| R2-3 Low | **Closed (code and docs); residual in R3-1** | `Boundary.assistant = conversation ∪ prompt` (`:184`), with code vocabulary only for system messages. A forged `Ryan Tan` is refused, ISO and readable dates are refused, and a run of 4 adjacent numbers is refused. `Maya Lim` passes, as documented. The docs state the assistant-history rule. |
| R2-4 Advisory | **Improved** | `EVERYDAY_WORDS` and guide.py screen terms were added. `What is the status of this case?` and `Can you summarise the discrepancy, please?` now pass. I read all 366 alphabetic guide.py terms and all 91 `EVERYDAY_WORDS`: neither has a personal name, place or identifier. The only name-like words in `conversation_vocabulary` are `mark` and `may` (ordinary English). The remaining gaps are R3-A1 to R3-A3. |
| R2-5 Advisory | Carried | See above. |

## Owner requirements - re-verification

| Requirement | Result | Evidence |
| --- | --- | --- |
| Default off; behaviour unchanged without D-094 | Verified (re-run) | The default-off, every-condition and without-decision tests pass. The `main.py` diff contains only the `remote_gate` and notice additions (re-read). |
| (1), (2), (5) decision, development environment, provider/endpoint/credential/budget checks | Verified (reused from R2; `remote_test.py` invariants re-read) | `_ready` runs `check_messages` first (`remote_test.py:292`). The call count includes open calls (`:299`). `stream` runs `_ready` off the loop (`:366`). The R2 refactor-equivalence evidence is reused. |
| (3) case verified server-side | Verified | `check()` case, document, viewer, value and knowledge logic is unchanged. The tests pass. |
| (4) everything sent is inside the boundary | **Met for accidental entry; deliberate-encoding limit to document (R3-1)** | Non-ASCII, dates, ids and identifier shapes are refused in every role. No system message embeds question or history text: `build_messages`, `topic_message` and `terms_for_question` take only fact and knowledge content, re-read and unchanged from `c36b8af`. History roles are restricted to `user`/`assistant` (`main.py:109`). |
| (6) explicit HR activation | Verified | The journey test passes (4 runs). |
| No over-blocking of intended use | Verified, with advisories | **8-turn end-to-end conversation** (alternating `/chat` and `/chat/stream`, real accumulated history): the four owner questions, then `What is the status of this case?`, `Can you summarise the discrepancy, please?`, `What does that mean?` and `Can you explain that?`. All 8 were `answered_by: model`. In the fixture sweep (`scenarios.json` and `phase_b_questions.json`), 2,567/2,567 service lines pass as assistant history, as do 99/101 questions and 191/202 answer-in-history combinations (R3-A1, R3-A2). A 4,000-character question of approved words passes, and so do long and trimmed (`…`) history turns. |
| No paid call | Verified | Mock transports, a fake listing and a sentinel key only. No network, no `.env`, no Mongo. |

## Checks run (this session, on the frozen content)

| Check | Result |
| --- | --- |
| Content ID start / end | `967024b4…48fe1` at start, before the report, and at end |
| `tests/test_remote_test.py` ×4 (`-p no:cacheprovider`, `-B`) | 62 passed each run (4/4) |
| Full assistant suite (`-p no:cacheprovider`, `-B`, `faulthandler_timeout=300`, junitxml in scratch) | 2437 tests, 2423 passed, 14 failed. All 14 are `OSError: [Errno 24] Too many open files` (junit-verified), in test_model_factory 1, test_phase_b_live 1, test_required_p2 5 and test_streaming_resources 7. Those 4 files in isolation: **288 passed**. This matches the implementer's evidence and the R1/R2 pattern |
| ruff check / ruff format --check (`--no-cache`) | All checks passed; 111 files already formatted |
| mypy `ai_assistant assistant_eval scripts tests/test_remote_test.py` (cache in scratch) | Success: no issues in 59 source files |
| `scripts/build_synthetic_boundary.py --check` | synthetic boundary is current |
| `check_project_state`, `check_architecture`, `check_policy_authority`, `check_secrets`, `check_external_provider_readiness`, `check_tooling_config` | all PASS |
| Frontend `npx tsc -b --pretty false` | exit 0 |
| Frontend vitest `AiModelManagement.test.tsx` + `AiAssistantPanel.test.tsx` | 31/31 passed |
| `git diff --check c36b8af` | clean |
| Byte-level trailing-whitespace, final-newline and EOL check, 18 modified + 6 new files | clean, except PROJECT_STATE mixed EOL, which is inherited from HEAD (R2-5) |
| `diff --stat` vs `--ignore-cr-at-eol` | identical (18 files, +731/−477) |
| Boundary probes (`check()`/`check_messages`) | 30 R1/R2 hidden-character and number probes refused. 24 new ASCII-encoding probes: R3-1 vectors pass, digit-splitting tricks refused. 10 forged-assistant probes. 3 long-input probes. 9 typographic marks. 5 role/system probes |
| Over-blocking sweep (all Garden fixture scenarios) | 2,567/2,567 lines as history; 99/101 questions; 191/202 answers as history |
| End-to-end probes (Journey, mock OpenRouter) | R1/R2 probes: 0 requests (18 calls). 8-turn owner conversation: 8/8 model. Case-data answer as assistant history: model. R3-1 vectors: 3 requests carrying the text |
| Event-loop stall probe (R2's, re-run) | max loop gap 0.032 s (slow preflight) and 0.047 s (lock held 1.5 s) |

Probes are in
`C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane--claude-spares-spare-6YcPey\583f9cb6-22ae-4b09-9725-20ab186f8738\scratchpad\qg094r3\`
(`probe_boundary3.py`, `probe_overblock3.py`, `test_probe_journey3.py`, `full.log`,
`full.xml`). No real OpenRouter call was made, and no non-loopback host was contacted. No
`.env` was read, Mongo was not used, and no real `OPENROUTER_API_KEY` was set or read.

## Not evidenced (carried, not a finding)

- No real CLM backend Garden case was run through the boundary (fixture snapshots only).
- No real provider call was made, correctly: the owner has not yet authorised the manifest,
  call count and cap.

## Minor fixes required for PASS

1. R3-1: correct the known-limits wording in the five listed places, as described above.
   Code hardening is optional.

R3-A1 to R3-A3 are advisory and fail closed; addressing them is optional.

## Readiness

The bounded change is ready once the R3-1 wording is corrected. Under the workflow, changed
reviewed content needs a fresh independent check of that delta. A docs-only change can reuse
all the code evidence above, provided the six product files keep their per-file hashes
(`synthetic_boundary.py` `8c7817e0…`, `.json` `54e84604…`, `remote_test.py` `fc57406e…`,
`remote_checks.py` `f874bab4…`, `build_synthetic_boundary.py` `941b0586…`,
`test_remote_test.py` `dbac4793…`). If the optional code hardening is applied, the boundary
probes and the test file must be re-run. No commit, push or PR is authorised, and none was
made. Publication also needs `pre_pr_check.py` on a committed state and the owner's
authorisation.

CONTENT ID at END: `967024b414c9198d19777818ad0c9cf738286d3ba4ce31c0079419a41ac48fe1` (unchanged; the verdict applies to this content).
