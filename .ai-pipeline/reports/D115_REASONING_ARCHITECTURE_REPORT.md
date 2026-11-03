# D-115 pre-merge: model-independent reasoning architecture and prompt quality (PR #155)

Date: 2026-11-04. Branch `feat/d115-copilot-case-memory-20261103` on main `2c104081d34b`.
Evidence class: Local. Synthetic data only; no paid call, no external model, no live store, no
service restart; copilot stays off by default (`AI_ASSISTANT_ANSWER_MODE=exact_lines`).
Decision log: D-115 rows C5 to C7, X1, E2 and Q1.

## 1. Request paths (traced)

| Path | Gate before the model | Prompt and answer | Changed here |
| --- | --- | --- | --- |
| Local unrestricted model (literal loopback, policy allows) | backend reads with the user's session; `copilot_for` true only when `answer_mode=copilot` | copilot: RULES + evidence package + ownership facts + chat context; free text checked by `CopilotGuard` (+ `claims.py`). Otherwise exact lines | yes (copilot only) |
| Local model the D-104 policy restricts | `data_access.SyntheticOnlyModel` (`requires_synthetic_boundary`): D-094/D-095 per-call admission | exact lines, `prompts.py` | no |
| Claude (Anthropic) | `ClaudeTestModel` (`requires_synthetic_boundary`), D-107/D-095 interlocks, ledger and limits | exact lines | no |
| GPT-OSS 120B (OpenRouter) | `RemoteTestModel` (`requires_synthetic_boundary`), D-094/D-095 | exact lines | no |
| IT-configured non-loopback model | always wrapped as `SyntheticOnlyModel(local=False)` (`model_admin.py`), whatever the policy | exact lines | no |
| Deterministic fallback | none needed | case-data lines (`answered_by: case_data`) | no |

`copilot_for` refuses any model with `requires_synthetic_boundary`, so no external or
restricted model can reach copilot mode, the evidence package, the ownership facts or the
claim checks. `prompts.py`, `guardrails.py`, `context.py`, `data_access.py` and the provider
adapters are unchanged against main.

## 2. Architecture before and after (copilot path)

Before (PR #155 at `16587d5`): scope regexes → case facts in the exact-line view
(`facts_for_model`) + ownership facts → RULES (14 rules) → model → `CopilotGuard`: word-presence
grounding (names and percentages must appear somewhere in the facts), UBO regexes, shared
`guardrails._check`.

After:

| Layer | Component | Model-independent? |
| --- | --- | --- |
| A. Understanding | `copilot.in_domain`: onboarding words, case-referring short questions, figures ("25%"), "And X?" follow-ups; everyday topics redirected without a model call | yes |
| B. Policy and access | unchanged: backend authorisation with the user's session; `copilot_for`; D-094/D-095/D-104 gates for every other provider | provider-specific by design |
| C. Evidence | `evidence.py`: the same compact case view every model gets, regrouped by source (registry, documents, conflicts, workflow, blockers and offered actions, still needed, approved explanations) with a legend; ownership facts with each holding written with its direction | yes |
| D. Reasoning | RULES: answer first, explain evidence, copy holdings exactly, classify by the application's result, offered actions only, resolve follow-ups, caveat once | yes (copilot only) |
| E. Validation | `claims.py`: ownership graph from the application's figures; relationship, classification and negation/condition checks; then the existing copilot and shared checks | yes |
| F. Response | unchanged: kept sentences shown; removed ones counted; read-only line first for change requests | yes |

## 3. Implementation

| File | Change |
| --- | --- |
| `ai_assistant/claims.py` (new) | `OwnershipGraph`, `relationship_problem` (P1), `classification_problem` (P2), `negated_sentence` (P3, closed whole-sentence forms), `canonical_name` (moved here) |
| `ai_assistant/evidence.py` (new) | source-grouped evidence package (P4/C) |
| `ai_assistant/copilot.py` | RULES rewritten (P4); evidence message; ownership relationships with direction; guard order: classification → settled/unqualified UBO → relationship → percentages/names → shared checks with the negation analysis; scope additions; earlier subject-before-phrase contradiction check replaced by the structured one |
| `ai_assistant/model_qualification.py` | `claims.py`, `evidence.py` join `BASIS_FILES` |
| `scripts/build_synthetic_boundary.py` | both new modules are local-only (no external vocabulary change; boundary file unchanged) |
| `tests/test_claims.py` (new), `tests/test_copilot.py`, `tests/test_copilot_model_eval.py` | held-out graph tests, real-model regression sentences, held-out opt-in evaluation set |
| `docs/decisions/DECISION_LOG.md` | D-115 C5, C6, C7, X1, E2; Q1 basis |

Decision authority: C5 and C7 only remove more or reword the local copilot prompt. C6 changes
what the copilot keeps (sentences the shared checks remove) and needs the owner's approval
with C5 and C7. X1 is a proposal only. Nothing changes the external boundary, qualification
procedure, retention or read-only authority.

## 4. Evidence

### 4.1 Validator (deterministic, labelled corpus on the held-out facts)

| Guard | Implementer corpus: unsafe kept | Implementer corpus: correct removed | Reviewer probes: unsafe kept | Reviewer probes: correct removed |
| --- | --- | --- | --- | --- |
| PR #155 (`16587d5`) | 15 of 31 | 10 of 23 | 42 of 82 | 7 of 23 |
| Refined (final) | 0 of 31 | 2 of 23 | 24 of 82 | 0 of 23 |

The implementer's corpus overlaps the tests. The reviewer's probes were written independently
during the quality gates; across both reviews' probe sets, every sentence kept now that the PR head removed is correct (intended negation forms, or true holdings the head removed only because it could not read a possessive name). The 24 still
kept are forms listed in section 5 and claims the shared checks never flag. The 2 correct
sentences now removed are compound negations left out on purpose (section 5).

### 4.1a Independent review of this round

The first review of `58f4544` was FAIL (blocking, potential security regression): the
clause-based negation acceptance kept current claims written around a negated or conditional
clause ("Compliance has verified the UBO so the case cannot proceed until the address is
confirmed.", "The case remains blocked until ownership is confirmed, which compliance did.",
"The registry wins; neither source automatically wins."). It was replaced by whole-sentence
closed forms (D-115 C6); all eleven reproductions are tests and are removed. A second fresh
review of that change (`c00023b`) was FAIL on one finding: a negative subject in the closed list
("No UBO status has not been officially verified." asserts the opposite). Negative subjects
were removed from that form; the reproductions, the possessive "X's N% stake in Y belongs to Z"
and "X's stake belongs to Y" forms, "Neither X nor Y is below the threshold" and claims inside
an "Unlike X who ..." phrase are now judged and tested. The review's
grounding notes (possessive names, "owned 60% by", "X, like Y, meets", "Unlike X, ...",
"Neither X nor Y ...") are fixed and tested; a false removal found afterwards in a real answer
(an elided subject: "... of Garden Business and indirectly holds 10% via Beta") is fixed too.

### 4.2 Real local model (held-out case, 13 unseen questions, 16 turns)

`ministral-3:8b`, Ollama 0.40.13 on 127.0.0.1, temperature 0.2, 600 answer tokens, RTX 4080
Laptop GPU, warm model (the first call after a model load took 32.6 s earlier).

| Run | Answered by the model | Redirected | Sentences removed | Median / max latency |
| --- | --- | --- | --- | --- |
| PR #155 (`16587d5`) | 14 of 16 | 2 ("How did the application get 25% for DANIEL KOH?", "And MERIDIAN?") | 9 | 3.1 s / 10.8 s |
| Refined (`ab85a99`; guard later tightened, see 4.1a) | 16 of 16 | 0 | 4 | 3.4 s / 6.7 s |
| Exact lines | 15 of 15 (no general chat) | 0 | 1 | 0.6 s / 1.9 s |

Re-checking the recorded raw answers with the final guard gives 5 removals on the held-out
set (8 for the PR #155 answers) and 5 on the original set. Of the 4 removals shown in the final
run, one is a genuine relationship error the old guard would
have shown ("PRIYA NAIR holds 20% of KESTREL HOLDINGS"; she holds 40% of KESTREL, 20% of the
company), one is a misquoted label, and two are over-removals in the change-request answer
after the read-only line. On the original question set the refined copilot answered 17 of 18
(weather redirected), 4 sentences removed, median 3.6 s.

### 4.3 Independent blind scores (0 to 2; 15 held-out items; scorer did not know the systems)

| Dimension | Exact lines | PR #155 copilot | Refined copilot |
| --- | --- | --- | --- |
| Factual correctness | 1.33 | 1.46 | 1.47 |
| Relationship correctness | n/a | 1.86 | 1.78 |
| Grounding | 2.00 | 1.46 | 1.60 |
| UBO classification | n/a | 1.78 | 1.60 |
| Completeness | 0.33 | 1.60 | 1.60 |
| Reasoning | 1.50 (n=2) | 1.54 | 1.60 |
| Naturalness | 1.00 (n=2) | 1.38 | 1.53 |
| Read-only and privacy | 2.00 | 1.92 | 2.00 |

Reading: copilot answers are far more complete than exact lines. Between the two copilot
versions the differences are within the noise of one run each (n = 7 to 15 per dimension): the
local 8B model's own reasoning errors dominate. Errors the scorer found in refined answers: a
relationship reversed in a form the checks do not judge ("MERIDIAN holds its 20% through DANIEL
KOH's 100% ownership"), an undetermined person reported as 0% (the synthetic fixture lists 0%
figures for that person), invented details, assumed gender, "the facts you provided", and
answers cut at the token limit. In PR #155 answers: another case's company named in case B, an
action not offered, invented documents. Not production-ready on this model.

## 5. Safety

Correctly rejected (tests, corpus and the reviewer's probes): reversed or self-holdings, a
percentage moved to another party, a wrong path ("through MERIDIAN" for PRIYA), passive and
possessive holdings, below-threshold or undetermined persons called candidates in any order or
list form, met persons called below, "verified/confirmed/approved/settled" UBO claims, every
earlier negation bypass ("had not been officially verified until today", "by anyone but
compliance"), and every claim written around a negated or conditional form (section 4.1a).

Known false negatives (kept though wrong): holdings with the object first ("Of KESTREL, AISHA
holds 40%") or with percentages in parentheses after names, a reversed causal phrasing
("MERIDIAN holds its 20% through DANIEL KOH's 100% ownership"), a surname alone, pronouns,
figures in words, lower-case company names, wrong descriptions without a figure or a
classification, and claims the shared checks never flag ("The UBO, verified by compliance,
remains blocked until the address is confirmed.", "The UBO had not been verified until today."
without "officially"; unchanged from main). Known false positives (removed though correct):
negations or conditions that are not one of the fixed whole-sentence forms ("Neither source
automatically wins—this is a case-specific decision.", past tense "had not been verified"),
quoted labels that are not word for word, refusals phrased "I cannot mark X as the verified
UBO".

## 6. Qualification

The basis moves from main's `1cb45edc5939…` to `77e50313a62c…` (main.py, copilot.py,
case_contexts.py, claims.py, evidence.py and the boundary file). Claude Balanced would become
AI unavailable after merge and restart until a separately approved paid requalification
(D-098 R6; the earlier owner authorisation was 2 billed calls, at most US$0.192 reserved, per
qualification). Continuity: schedule the merge and restart outside demos, then run the approved
requalification. Q2 (separate the basis by provider) would avoid this for future
copilot-only changes; not implemented.

## 7. Proposal X1: external synthetic-only copilot evaluation (not started)

- Providers: Claude Sonnet 5.5 Balanced (Anthropic) and GPT-OSS 120B (OpenRouter), each through
  its existing gate, synthetic Garden and held-out fixtures only (the same 31 questions as here).
- Needs: an owner decision to allow copilot answer mode for a synthetic-only evaluation run
  (a D-094/D-095 change in kind: free text instead of exact lines), a qualification decision,
  and spend approval.
- Estimated cost ceiling: Claude about 31 calls at about 4,000 input and 400 output tokens,
  well under US$1.50 with a hard ceiling of US$2.00; GPT-OSS under US$0.20. Estimates only,
  to be confirmed against the providers' current prices before any call.
- Coverage: the same blind scoring and validator statistics as section 4, per provider.

## 8. Recommendations

1. Merge with copilot disabled: acceptable after review (exact lines unchanged; external paths
   unchanged), with the Claude requalification scheduled.
2. Activate local copilot: not yet. The guard is much stronger, but answer quality on
   `ministral-3:8b` is middling (blind correctness about 1.5 of 2). Before activation: two prompt
   additions suggested by the blind errors (refer to people by name, never assume gender; the
   evidence comes from the application, not the user), a larger owner-scored evaluation, and a
   decision on C6.
3. External synthetic-only copilot evaluation: eligible to be proposed (X1), not authorised.
