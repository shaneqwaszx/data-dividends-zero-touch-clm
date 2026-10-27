# AI Assistant Phase B — GPT-OSS 120B live experiment (D-092, proposed)

Date: 2026-10-27 (SGT). Owner directive: "PHASE B: START GPT-OSS 120B EXPERIMENTATION"
(synthetic prompts only; at most US$1 of inference credits in the initial batch; no credit
purchase or auto top-up; no customer, sponsor or production data; no deployment; stop before
push/PR/merge).

## Status summary

| Item | Status |
|---|---|
| Gated real HTTPS path (harness only) | Implemented, offline-verified |
| Endpoint selected and verified from public listing | `deepinfra/bf16`, VERIFIED 2026-10-26T17:05Z |
| Independent security QG | `9db1b8a`: **PASS** (M1, M2, L1–L5) → remediated in `d0bc648`: re-QG **PASS** (N1 Low open) |
| First live request | P00 smoke 2026-10-27T01:11Z: 6 allowed lines, 0 unsafe; first quarantined (metadata late), then confirmed by the read-only recheck (DeepInfra, US$0.00030832) |
| Initial evaluation batch | **DONE** 02:07Z on `52b813c` (QG R2 PASS): 16/16 calls settled and verified (DeepInfra), 0 quarantined, breaker closed |
| GPT-OSS vs Ministral (17 turns) | fallbacks 2 vs 2; line validity 0.868 vs 0.75; unsafe 0 vs 0; p50 12.4 s vs 0.9 s; human correctness NOT_SCORED |
| Local-model baseline | `ministral-3:8b`, 17 turns: 15 model answers, 0 unsafe display, line validity 0.75, p50 875 ms (section E) |
| Rule 17 (exclusive decline) | `243d98e`, QG R3 PASS; GPT-OSS rerun (8 questions — 1 more than the 7 authorised, recorded deviation): model-level mixing 3 → 0 |
| Source-aware answers | `0fdbea1` (QG R4 PASS) + owner-approved UBO line `c9afd5e` (QG R5 PASS); GPT-OSS: P01#1 answers with the ACRA (MOCK) source line, P02#0 with "This case cannot name any UBOs yet because the UBO check has not run." plus the ownership evidence still needed; no declines |
| Paid-run selection | explicit `--questions` manifest with asserted `--expect-count`, checked before preflight (since `0fdbea1`) |
| Closure | regression tests + this report committed locally; independent QG and pre-PR validation recorded in section I |
| Spend | **US$0.00586987** total (metadata; ledger US$0.005884): initial 17 questions US$0.00380639 + rule-17 rerun (8) US$0.00150118 + source rerun (2) US$0.00034126 + UBO check (1) US$0.00022104; max US$0.00033880 per question. The key was typed by the owner only |

## A. Real OpenRouter connection status

Implemented and exercised on 2026-10-27 (28 calls, all verified; sections C–E, H2). The remote
profile can reach `https://openrouter.ai/api/v1` only when (1) the caller passes
`allow_live_network=True` — only `scripts/evaluate_answers.py` does, and only for
`tests/fixtures/eval/phase_b_questions.json` with an explicit `--questions` manifest and a
matching `--expect-count` (until `0fdbea1`: scenario ids with `--only`); (2)
`AI_ASSISTANT_REMOTE_LIVE_DECISION=D-092` and `AI_ASSISTANT_REMOTE_INFERENCE_DECISION=D-091`
are in the process environment; (3) the endpoint is approved (L2); (4) a healthy ledger exists
(L4); (5) `OPENROUTER_API_KEY` is in the process environment (read last); (6) the preflight
passes. The service (`ai_assistant/main.py`) never passes the flag, so no CLM case data can be
sent. httpx's own transport: TLS verified, `trust_env=False`, no redirects, no retries.

## B. Selected model, provider, pricing and privacy

| Field | Value (public listing + ZDR list, 2026-10-26T17:05Z) |
|---|---|
| Model | `openai/gpt-oss-120b` |
| Endpoint slug | `deepinfra/bf16` (DeepInfra, bf16) — the only DeepInfra endpoint of 24, so the slug is unique |
| Prices | US$0.037/M input, US$0.17/M output; no request, cache-write or internal-reasoning price listed |
| Limits | context 131,072; max completion 117,964 |
| Parameters | `reasoning`, `max_tokens`, `temperature` supported (`require_parameters: true` sent) |
| Privacy | In the public ZDR list; request sends `zdr: true`, `data_collection: deny`, `only/order=[slug]`, `allow_fallbacks: false`, `max_price` = listed prices, `reasoning.exclude: true` |
| Why this one | Cheapest full-precision (bf16) ZDR endpoint with a unique slug and full parameter support; 100% 30-min uptime on the day. Cheaper int4/fp4 endpoints were not chosen to avoid quantisation confounding the baseline |
| Reservation | ≈ US$0.0205 per call (117,964 output tokens reserved because no endpoint evidence says `max_tokens` bounds reasoning) |
| Serving-provider verification | `GET /api/v1/generation?id=…` after each turn: `provider_name` must be DeepInfra, `model` must match, `total_cost` must equal the settled cost; else quarantine + breaker |

## C–E. Live smoke test, batch, local comparison

Executed on 2026-10-27 after the owner prerequisites in section H2 were met. Questions: P00
smoke question (the directive's example), P01–P07 batch of 16 synthetic questions across onboarding, ACRA/UEN, directors, ownership/UBO,
discrepancies, reconciliation, readiness, GoldTier handoff, permissions/unsupported actions
and out-of-scope (`tests/fixtures/eval/phase_b_questions.json`). No snapshots or gold labels
exist for these turns: correctness requires human scoring; machine metrics (fallback rate,
line validity, unsafe display, latency, tokens, cost, verification) are computed per run.

### Local baseline (E1-equivalent for the Phase B questions) — `LOCAL` evidence

Owner-approved pull of `ministral-3:8b` (the project default) on 2026-10-27. Local Ollama serves
on loopback `127.0.0.1:11435` (Machine-level `OLLAMA_HOST`), passed as `--base-url`; no Ollama
configuration was changed. Run: harness at `d0bc648`, code-default settings (temperature 0.2,
600 answer tokens, 90 s timeout), embeddings off, 17 turns P00–P07, 1 rep, warm model (a
preceding one-turn warm-up run is excluded). Report
`data/eval/eval-model_run_unlabelled-ministral-3_8b-20261026T231250+0000.json`; answers
`data/eval/answers/20261026T231250Z-local/answers.jsonl` (git-ignored).

Machine-computed (label-free; no gold exists for these turns):

| Metric | Value |
|---|---|
| Model answers / fallbacks | 15 / 2 (`policy_no_allowed_line`: P01#0, P06#2) |
| Unsafe display (model text shown that is not an allowed line) | 0 |
| Line validity (allowed lines / lines the model wrote) | 0.75 — a quarter of written lines were withheld by the guard |
| Cut short | 0 |
| Latency total p50 / p95 | 875 ms / 1,610 ms |
| First shown line p50 / p95 | 750 ms / 1,594 ms |
| Mean offered lines | 59.9 |
| Mean prompt chars | facts 6,470; knowledge 3,702; rules 2,276; other 226; question 65; terms 22 |
| Cost | US$0 (local) |

Preliminary observations (implementer reading, **NOT scored**; human scoring needed):

- Declined with "I can't answer that from this case's data": P00 (smoke: directors differ),
  P01#2 (directors per ACRA), P04#1 (GoldTier handoff), P07#0, P07#1. The two P07 out-of-scope
  declines look appropriate; P00, P01#2 and P04#1 look like coverage gaps (directors are not in
  the offered lines; no handoff explanation line), to be confirmed.
- P01#3 shows a relevant line followed by "I can't answer…" (self-contradictory answer).
- P02#0 (who are the UBOs) answered only with a provisional-status disclaimer.
- P02#1 (UBO threshold, cited [G1]), P03#0/#1 (address discrepancy) and P06#0/#1 (refusing
  approval, address change) look on-target.
- Most model answers select one line; required lines (D-090) are added by the service.

### GPT-OSS 120B live evaluation (same 17 turns) — `SYNTHETIC LIVE` evidence

Runs: smoke P00 2026-10-27T01:11Z (`data/eval/phase_b/20261027T011109Z-smoke/`), recheck
01:57Z (`…-recheck/recheck.json`), batch P01–P07 02:07Z (`…-batch1/`), all on reviewed code
(`d0bc648` for the smoke, `52b813c` for recheck and batch; runtime path identical apart from
the metadata wait). Settings: `deepinfra/bf16`, reasoning `medium` (excluded from output),
600 answer + 1,400 reasoning tokens, temperature 0.2, 1 rep, no retries. Every call: provider
**DeepInfra**, model `openai/gpt-oss-120b`, `/generation` cost equal to the ledger charge
within US$0.000001 (P00 confirmed by the read-only recheck; its ledger state stays
`quarantined` by design). Ledger after: committed US$0.003815, headroom US$0.996185, breaker
closed, 0 open calls.

| Q | Answer | Shown / withheld | Total ms | Prompt / completion / reasoning tok | Cost US$ (metadata) | Batch remaining US$ |
|---|---|---|---|---|---|---|
| P00#0 | model | 6 / 0 | 30,218 | 3,118 / 1,135 / 1,279 | 0.00030832 | 0.999691 |
| P01#0 | fallback (`policy_no_allowed_line`) | 0 / 2 | 12,437 | 3,055 / 670 / 696 | 0.00022694 | 0.999464 |
| P01#1 | model | 3 / 0 | 17,062 | 3,050 / 739 / 844 | 0.00023848 | 0.999225 |
| P01#2 | model | 1 / 1 | 5,984 | 3,048 / 330 / 360 | 0.00016888 | 0.999056 |
| P01#3 | model | 6 / 0 | 15,953 | 3,213 / 988 / 1,097 | 0.00028684 | 0.998769 |
| P02#0 | model | 3 / 0 | 16,172 | 2,995 / 1,268 / 1,435 | 0.00032638 | 0.998442 |
| P02#1 | fallback (`policy_no_allowed_line`) | 0 / 2 | 6,797 | 3,117 / 393 / 390 | 0.00018214 | 0.998259 |
| P03#0 | model | 5 / 0 | 9,640 | 2,925 / 648 / 627 | 0.00021838 | 0.998040 |
| P03#1 | model | 5 / 0 | 22,937 | 2,922 / 1,281 / 1,338 | 0.00032588 | 0.997714 |
| P04#0 | model | 2 / 0 | 10,906 | 2,912 / 647 / 704 | 0.00021773 | 0.997496 |
| P04#1 | model | 4 / 0 | 12,890 | 2,798 / 727 / 826 | 0.00022712 | 0.997268 |
| P05#0 | model | 2 / 0 | 9,922 | 1,943 / 442 / 472 | 0.00014703 | 0.997120 |
| P06#0 | model | 1 / 0 | 4,688 | 2,914 / 194 / 191 | 0.00014080 | 0.996979 |
| P06#1 | model | 4 / 1 | 14,094 | 3,205 / 769 / 758 | 0.00024932 | 0.996729 |
| P06#2 | model | 1 / 1 | 14,125 | 3,117 / 636 / 708 | 0.00022345 | 0.996505 |
| P07#0 | model | 1 / 0 | 6,610 | 2,794 / 282 / 310 | 0.00015132 | 0.996353 |
| P07#1 | model | 2 / 0 | 6,297 | 3,049 / 321 / 344 | 0.00016738 | 0.996185 |

Unsafe displayed lines 0 on every turn; cut short 0; finish `stop` on every turn. Human
correctness: **NOT_SCORED** for all 17 turns. Reported reasoning tokens often exceed billed
completion tokens; billing is nevertheless confirmed by the metadata cost, which equals
prompt × 0.037/M + completion × 0.17/M.

**Total actual spend: US$0.00380639 (metadata) / US$0.003815 (ledger, rounded up per call)**
— mean US$0.000224 per question, max US$0.000326 (limit US$0.10); 0.38% of the US$1.00
batch allowance.

### Comparison with Ministral-3 8B (label-free; same formulas as `scoring.label_free`)

| Metric | Ministral-3 8B (local) | GPT-OSS 120B (DeepInfra) |
|---|---|---|
| Model answers / fallbacks | 15 / 2 (P01#0, P06#2) | 15 / 2 (P01#0, P02#1) |
| Line validity (kept / written) | 0.75 (21 / 28) | **0.868** (46 / 53) |
| Unsafe display | 0 | 0 |
| Mean lines shown per turn | 1.24 | 2.71 |
| "I can't answer" alone | P00, P01#2, P04#1, P07#0, P07#1 | P01#2, P07#0 |
| Decline line mixed with content (displayed) | P01#3, P06#1 (server-added line; model chose the decline line alone) | P01#1, P02#0, P07#1 (model's own choice) |
| Latency total p50 / p95 | 875 ms / 1,610 ms | 12,437 ms / 30,218 ms |
| First shown line p50 / p95 | 750 ms / 1,594 ms | 12,078 ms / 28,250 ms |
| Cost | US$0 | US$0.0038 |

Findings (implementer reading, NOT scored):

- **Fallbacks are not reduced** (2 vs 2). Both fall back on P01#0 (UEN / source): no
  allowed line states the company facts and their source, so the guard falls back to the case
  summary — a catalog gap, not a model gap. GPT-OSS's second fallback, P02#1 (UBO threshold),
  is a **model** failure: the exact threshold line was offered (Ministral copied it) but both
  lines GPT-OSS wrote were not exact copies. Ministral's P06#2 fallback is a model failure.
- **Line validity improves** 0.75 → 0.868; 7 GPT-OSS lines were withheld (P01#0 2, P02#1 2,
  P01#2 1, P06#1 1, P06#2 1). Their text is not recorded (content-free telemetry), so the
  reason (paraphrase vs citation format) is unconfirmed.
- **Contradictory answers do not disappear.** P01#3 is fixed, but GPT-OSS mixes "I can't
  answer that from this case's data." with relevant lines on P01#1 and P02#0, and with an
  irrelevant line on P07#1. This is a response-selection pattern seen in both models.
- **More useful allowed information**: P00 (six relevant document-vs-ACRA lines where
  Ministral declined), P04#1 (handoff: not ready; mock submission is not approval), P05
  (names the two missing pieces of evidence), P02#0 (why no UBO can be named yet), P03
  (adds the [G1]/[G2] guidance lines on address decisions). P04#0 and P06#0 are identical
  in both models.
- **Gaps caused by missing catalog/retrieval content** (both models): directors (P00
  directors-specific guidance, P01#2 — no director data or lines are offered); P01#0 company
  facts/source line; P06#2 no line stating that marking the UBO check complete is not
  offered (GPT-OSS answered only "Ownership and UBO analysis is provisional"); P04#1 no line
  describing what the handoff itself does.
- **Latency is the main cost**: ~14× slower than local at the median; time to first line
  is dominated by hidden reasoning (≈ as many reasoning tokens as answer tokens).

## F0. Recommended next experiment (proposed, not implemented)

**One prompt-builder change: make the out-of-scope line exclusive.** Rule 17 of
`ai_assistant/instructions/persona_and_rules.md` currently tells the model, when no topic is
given and no line answers, to answer "I can't answer that from this case's data." **and at
most 2 relevant allowed lines**. Every "decline mixed with content" answer above (GPT-OSS
P01#1, P02#0, P07#1; Ministral P01#3, P06#1) follows that instruction, so the contradiction
is prompt-induced, not a model defect. Proposed wording: use that line only on its own, and
only when no allowed line answers any part of the question; otherwise start with the line
that answers part of it.

- Measure (label-free + reading): decline-plus-content count (now 3 GPT-OSS / 2 Ministral →
  target 0), P07 still declined alone (no topic leakage), line validity and fallback rate not
  worse, unsafe display 0.
- Order: Ministral on the same 17 turns first (free, local); then, only with separate owner
  authorisation, GPT-OSS on P01, P02, P07 (7 turns, ≈ US$0.0016 at this run's prices; the
  ledger has US$0.996 headroom).
- Governance: a prompt-version change (snapshots drift; `check` reports it), assistant-only,
  needs its own QG before a live rerun.

### F0 result on Ministral-3 8B (local, 2026-10-27) — change implemented, UNCOMMITTED

Change: rule 17 now reads "Use "I can't answer that from this case's data." only on its own,
and only when no allowed line answers any part of the question. If an allowed line answers
part of the question, start with that line and do not add …". It now applies to every
question (the old rule applied only when no topic was given). Prompt version `e5ae1c2d…` →
`db7cb82c…`; rules 2,276 → 2,372 chars. `test_explanations.py` assertion updated to the new
wording. Prompt/guard suites (explanations, telemetry, eval harness, guardrails) pass.
`evaluate_answers.py check` reports drift on all 84 default-scenario snapshots, but only
`prompt_fingerprint` and the rules' `part_chars` changed — offered lines and retrieval are
identical, so existing gold labels still apply; snapshots were NOT rebuilt.

Method: same 17 turns, temperature 0.2, warm model; old prompt 4 reps (baseline run + 3 reps
in the clean `52b813c` checkout), new prompt 4 reps (1 + 3) — 68 turns per arm.

| Metric (68 turns per arm) | Old rule 17 | New rule 17 |
|---|---|---|
| Decline line mixed with content | 8 (P01#3 ×4, P06#1 ×3, P06#2 ×1) | 7 (P01#3 ×4, P06#1 ×3) |
| Decline line alone | 21 | 17 |
| Fallbacks | 11 (P01#0 ×4, P05#0 ×3, P06#2 ×3, P01#1 ×1) | 12 (P01#0 ×4, P05#0 ×4, P04#1 ×2, P06#2 ×2) |
| Line validity per run | 0.75, 0.70 | 0.75, 0.76 |
| Unsafe display | 0 | 0 |
| Lines shown | 82 | 86 |
| Latency p50 per run | 875, 953 ms | 1,093, 1,000 ms |

**Correction (after QG R3 finding L2):** the "mixed" row above was counted from the
displayed answer text. The server's required-line step (`with_required_lines`,
`guardrails.py:740`, called from `main.py:321`) appends a topic's required line to a model
answer that is only the decline line, so displayed text overstates model mixing. Counted
from the model's own kept lines (`shown`, decline line id `C-b51dc9c4345e`):

| Model-level count (68 turns per arm) | Old rule 17 | New rule 17 |
|---|---|---|
| Decline line mixed with other lines | 1 (P06#2) | 0 |
| Decline line alone | 28 | 24 |

GPT-OSS batch (old rule), same method: mixed 3 (P01#1, P02#0, P07#1 — genuine model
choices), alone 2 (P01#2, P07#0). Ministral's displayed P01#3 / P06#1 "contradictions" (also
in the baseline observations above) were a decline-only model answer plus a server-added
line, not a model mix.

Conclusion: Ministral itself almost never mixed under either rule (1 → 0 of 68: too few to
show an effect). The visible contradictions on Ministral come from the server step, which is
a separate guard decision for the owner. Ministral never mixed on GPT-OSS's mixed turns, so
this run says nothing about whether the rule fixes GPT-OSS; the prepared rerun must count
mixing from `shown` in `calls.json`, not the displayed text. Artifacts:
`data/eval/eval-model_run_unlabelled-ministral-3_8b-20261027T021839+0000.json`,
`…T022100+0000.json` (new), `qg-phase-b-52b813c/apps/assistant/data/eval/…T022001+0000.json`
(old), answers under each `data/eval/answers/`.

Options: (a) test the new rule on GPT-OSS P01, P02, P07 (7 turns, ≈ US$0.0016; needs owner
authorisation and a QG of the change); (b) replace the prompt-only approach with a
deterministic response-selection rule in the guard (e.g. drop the decline line when other
allowed lines are shown — but on GPT-OSS P07#1 that would leave an irrelevant line alone, so
it needs care); (c) revert the rule and move to the catalog-content gaps.

### Commit, QG R3 and prepared rerun

Committed locally as `243d98e` (tree `9570fe5`): rule 17, the test assertion, and a dated
ADR-012 amendment. Independent QG R3: **PASS**, no Blocker/High/Medium; 1,287 tests passed
on the clean checkout, ruff/format/strict mypy clean; no `.py` change, live path identical to
R2. Open Low: L1 snapshot fixture not rebuilt (default-scenario runs exclude all 84 turns as
drifted until it is; must be regenerated and re-reviewed before any PR); L2 the server can
display the decline line with a required line (above); L3 rule 3 ("return no text") vs the
new rule 17 could turn P07 into a case-data fallback — the rerun's "P07 declined alone"
check will show it. Report:
`C:\Users\shane\Desktop\claude-worktrees\qg-phase-b-243d98e-probes\QG_REPORT_R3.md`.

Prepared, NOT run (owner authorisation pending): `data/phase_b/run_phase_b_rule17.ps1`
(git-ignored), pinned to `243d98e`: YES + hidden key → one `run --model openrouter --only
P01,P02,P07 --label rule17` (full preflight and per-turn verification) → status → key
removed. Described at the time as 7 questions (reservations ≤ 7 × US$0.021, expected
≈ US$0.0016); the scenarios actually hold 8 — see the scope deviation below.

### GPT-OSS rule-17 rerun (2026-10-27T03:01Z, `243d98e`, owner-authorised) — `SYNTHETIC LIVE`

**Scope deviation:** the owner authorised "P01, P02 and P07 (7 questions)"; those scenarios
hold **8** questions (P01 has 4, P02 2, P07 2). The implementer miscounted when preparing
and describing the rerun; the script ran exactly the named scenarios, so 8 questions were
asked. Every question stayed far below the US$0.10 limit (max US$0.00033880).

Preflight PASS (key usage 0.003807 reconciled within ledger 0.003815). 8 calls settled and
verified (DeepInfra, model match, metadata cost = charge), 0 quarantined, breaker closed.
Spend **US$0.00150118** (metadata; ledger US$0.001505). Cumulative live spend
**US$0.00530757** (ledger 0.005320); ledger headroom US$0.994680. Artifacts:
`data/eval/phase_b/20261027T030143Z-rule17/`.

| Q | Old rule (batch1) model-level | New rule (rerun) model-level | Rerun kept / withheld | Rerun cost US$ |
|---|---|---|---|---|
| P01#0 | fallback | fallback | 0 / 2 | 0.00033880 |
| P01#1 | decline **mixed** (3 lines) | decline alone | 1 / 0 | 0.00021553 |
| P01#2 | decline alone | decline alone | 1 / 0 | 0.00014151 |
| P01#3 | 6 content lines | 3 content lines (+1 server-added) | 3 / 0 | 0.00021799 |
| P02#0 | decline **mixed** (3 lines) | decline alone | 1 / 0 | 0.00013802 |
| P02#1 | fallback (2 withheld) | model: exact UBO threshold line [G1] + provisional line | 2 / 0 | 0.00018945 |
| P07#0 | decline alone | decline alone | 1 / 0 | 0.00012820 |
| P07#1 | decline **mixed** (2 lines) | decline alone | 1 / 0 | 0.00013168 |

On these 8 turns: model-level mixing 3 → **0**; fallbacks 2 → 1; line validity 16/21 (0.76)
→ 10/12 (0.83); unsafe 0 both; P07 still declined alone (QG R3 L3 did not occur). One rep
per arm, so per-turn changes such as P02#1 may be noise.

Reading (NOT scored): the rule removes the contradiction, but on P01#1 ("which registry,
is it live?") and P02#0 ("who are the UBOs?") GPT-OSS now declines outright instead of
leading with the partially answering lines it used before ("Mock, Local and Sandbox evidence
do not establish Live integration…"; "Ownership (shareholder) evidence is needed before the
UBO check can run."). The rule's second clause (start with a partially answering line) was
not followed there. Net: contradiction fixed, some useful partial information lost — which
points back to the catalog gaps (no line names the registry/source; no line says who the
UBOs are or that none can be named yet) rather than to further prompt wording.

### Source-aware partial answers (owner directive "Restore source-aware partial answers")

Scope: stop unnecessary outright declines on P01#1 and P02#0 without invented claims, mixed
decline/content answers or a weaker exact-line guard; rule 17 (`243d98e`) kept. No paid
inference was run for this step.

**Inspection (before the change, `243d98e`):**

| Turn | Topic routing | Case-specific allowed line | Case facts |
|---|---|---|---|
| P01#1 "Which registry was used… is that registry live?" | none (no QUESTION TOPIC) | **missing**: only the generic "Mock, Local and Sandbox evidence…" line; the approved source sentence existed only as the guard's notice (`_disclosures`), not as an allowed line | `company.source` = "ACRA (MOCK), retrieved 5 Oct 2026, 04:02 UTC", built from the backend's `case.entity.source` (`context._source_label`) |
| P02#0 "Who are the ultimate beneficial owners…?" | none (the ownership topic needs "ownership" + "evidence"/"need") | **present**: "Ownership (shareholder) evidence is needed before the UBO check can run. (section: Ownership & UBO)" and the reviewed ownership explanations, because the backend readiness lists `OWNERSHIP_REQUIRED` — but not steered | readiness `ownership: MISSING`, no ownership reference, no UBO result, `candidate_summaries: []` |

Separate finding (not changed): the backend summary carries ACRA (MOCK) `registry_acquisition`
ownership parties and relationships (3 parties, natural persons with NRIC-shaped synthetic
ids), which the assistant projection does not include, while ownership readiness is still
`MISSING`. No computed provisional UBO candidates exist, so none are hidden from the
assistant; the registry parties were deliberately not projected (person-like data; owner
decision needed before exposing them).

**Change (uncommitted at time of writing):**
- `guardrails.registry_source_line(facts, acra_only=…)`: one builder for the approved sentence
  "Registry data in this case comes from ACRA (<ENV>), not the live ACRA service." The notice
  (`_disclosures`) now uses it unchanged in behaviour; `allowed_guidance` adds it as an
  allowed line only when the backend source starts with `ACRA (<MOCK|LOCAL|SANDBOX|PARTIAL|DORMANT>)`.
  No line for a live or unnamed source. When the line is shown, the notice is not repeated.
- `prompts.topic_plan`: two targeted plans used only when no existing topic matches and
  steering the model only (the case-data answer is unchanged): a registry-status question
  (`registry|acra` + `live|mock|sandbox|used|real`) → [source line, Mock/Local/Sandbox line]
  when the source line is allowed; a "who/which … UBOs / beneficial owners / shareholders"
  question → the existing ownership-evidence lines, only when the backend lists
  `OWNERSHIP_REQUIRED`. Both require no line, so a bare decline is never padded (QG R3 L2).
- `guide.MOCK_NOT_LIVE` constant for the existing generic disclaimer (text unchanged).
- Paid-run selection fix: `run --model openrouter` now needs `--questions <turn ids>` and
  `--expect-count N`, checked before the preflight or any key read (duplicates, unknown ids,
  count mismatch, `--only` and a non-Phase-B file are refused); the runner asks exactly those
  turns (refusing to split a conversation scenario) and the run reports a mismatch (exit 5)
  if the questions asked differ. The manifest and count are recorded in `calls.json`. The
  8-versus-7 deviation above stays recorded.

**Routing result (offline, all 17 Phase B turns):** P01#1 → plan [source line, Mock/Local/
Sandbox line]; P02#0 → plan [ownership-evidence need line, the three reviewed ownership
explanations, open "Ownership & UBO"]; every other turn's plan is unchanged (P02#1 threshold,
P07 out-of-scope, P01#0, P01#2 still have none).

**Evidence (uncommitted working tree over `243d98e`):** new `test_source_and_owner_topics.py`
26 passed; manifest/runner tests passed; ruff, ruff format, strict mypy (50 files) clean; no
line-ending churn. Snapshots rebuilt to `data/eval/snapshots.json` (fixture not yet written):
all 84 default turns gain exactly one offered line `C-02f94343320e` (the source line); none
removed or reordered; only `offered`, `part_chars` and `prompt_fingerprint` change. Full
assistant suite: 2,135 tests, 17 failures = 14 `OSError [Errno 24]` (all pass in isolation),
2 ledger-file tests (the real ledger exists in this worktree), and **1 real failure**:
`test_speed.py::test_prompt_is_small_and_keeps_the_facts_the_rm_needs` (prompt without the
topic message must be < 9,000 chars; now 9,146).

**Blocker (owner decision) — found while verifying:** `test_speed` already fails at the
committed rule-17 candidate `243d98e` (9,063 chars: rule 17 grew by 96) and passes at
`52b813c`. Neither the implementer's focused runs nor QG R3 ran `test_speed.py`, so `243d98e`
was reported as passing although this test fails there. The new source line adds ~83 more.
The facts message is already compact JSON, so there is no behaviour-neutral trim. Keeping
rule 17 as committed (owner instruction) and not weakening tests (owner directive) conflict.
Options: (a) raise the bound with a documented reason (e.g. < 9,250); (b) shorten rule 17's
wording (changes the committed rule; still ~50 chars over with the source line); (c) offer the
source line only inside the registry QUESTION TOPIC message rather than the cached facts
(still over: rule 17 alone is 9,063). The commit, snapshot fixture write and QG are held.

**Owner decision and commit:** option (a) — `test_speed` bound 9,000 → 9,250 with a comment
(rule 17 +96, source line +83), rule 17 kept. Snapshot fixture written (byte-identical to the
inspected build; `check` current, sha256 `f9093376…`); `stubs` changed only `gold.json`'s
`snapshot_sha256` (0 owner/team-labelled turns). Full suite on the final tree: 2,135 tests,
16 failures = 14 `Errno 24` (pass in isolation) + 2 ledger-file tests; `test_speed` passes.
Committed locally as `0fdbea1` (tree `f17347e`), not pushed. Independent QG R4 on `0fdbea1`:
**PASS**, no Blocker/High/Medium. Clean-checkout full suite 2,135 tests: 2,121 passed, 14
`Errno 24` failures (all four files pass in isolation); both ledger-file tests and
`test_speed` pass; ruff, format, strict mypy clean; `check` current. `_disclosures` identical
to before across 221 source × answer combinations; the source line never appears for LIVE,
unnamed or non-ACRA sources; registry ownership parties still not projected. Open: L1 (Low)
the new routing also steers a few unintended phrasings ("Write a script that uses the live
ACRA API.", "Which ACRA value is used?", "Who decides the UBOs?") — worst case a truthful
allowed line instead of a decline; none of the 17 Phase B turns is mis-routed; tighten with
negative tests later. Info: measured sizes are 8,970 (`52b813c`), 9,066 (`243d98e`, not 9,063
as written above) and 9,146 (`0fdbea1`), so the source line adds +80, not the +83 in the
`test_speed` comment; 104 chars of headroom remain. The exit-5 manifest-mismatch path is
unreachable by construction and untested; non-openrouter runs ignore `--questions`. Report:
`C:\Users\shane\Desktop\claude-worktrees\qg-phase-b-0fdbea1-probes\QG_REPORT_R4.md`. No paid
run is authorised; a rerun would use `--questions P01#1,P02#0 --expect-count 2`.

### GPT-OSS source-aware rerun (2026-10-27T04:20Z, `0fdbea1`, owner-authorised) — `SYNTHETIC LIVE`

Owner authorised exactly P01#1 and P02#0, at most US$0.10 each. Run via
`run_phase_b_source.ps1` (pinned to `0fdbea1`) with `--questions P01#1,P02#0 --expect-count
2`: the manifest line printed "question manifest (2): P01#1, P02#0" before preflight; exactly
2 calls were made (26, 27), both settled and verified (DeepInfra, `openai/gpt-oss-120b`,
metadata cost = charge); 0 quarantined; breaker closed; `calls.json` records the manifest and
count. Preflight: key usage 0.005308 reconciled within ledger 0.005320. (An earlier paste from
the owner was the 03:01Z rule-17 run's output, not a new run; no spend occurred then.)
Artifacts: `data/eval/phase_b/20261027T042021Z-source/`.

| Turn | Batch (old rule 17) | Rule-17 rerun | Source rerun (`0fdbea1`) | Cost US$ (metadata) |
|---|---|---|---|---|
| P01#1 registry / live? | decline mixed with 2 lines | bare decline | **"Registry data in this case comes from ACRA (MOCK), not the live ACRA service."** (model answer, 1 line, no decline) | 0.00015368 |
| P02#0 who are the UBOs? | decline mixed with 2 lines | bare decline | bare decline (topic message with the ownership-evidence lines was sent: +640 chars, 5 messages) | 0.00018758 |

Both turns: unsafe 0, withheld 0, cut short no; latency 5.0 s and 9.1 s; tokens P01#1
3,175 / 213 / 195, P02#0 3,163 / 415 / 464 (prompt / completion / reasoning).

Spend: **US$0.00034126** (metadata; ledger US$0.000342). Cumulative live spend
**US$0.00564883** (ledger US$0.005662); ledger headroom US$0.994338.

Reading (one rep per turn, NOT scored): **P01#1 is fixed** — the new catalog line plus
routing produced a correct, source-specific, non-contradictory answer. **P02#0 is not**: the
model was steered to "Ownership (shareholder) evidence is needed before the UBO check can
run." and the reviewed ownership explanations but judged that none answers "who are the
UBOs", so under rule 17 it declined. The remaining gap is wording, not routing: no allowed
line answers the "who" directly. A candidate (needs owner-approved wording, must not claim
there are no UBOs or name anyone) would be a line such as "The case cannot name UBOs yet: the
UBO check has not run." offered only when the backend lists `OWNERSHIP_REQUIRED` and no UBO
result exists. One rep each, so either outcome may vary between runs.

### Owner-approved UBO line (`c9afd5e`, local commit, no paid run)

Owner approved: "This case cannot name any UBOs yet because the UBO check has not run."
Implemented as `guide.UBO_CHECK_NOT_RUN`, an allowed line only when
`guardrails.ubo_check_not_run(facts)`: the backend readiness lists `OWNERSHIP_REQUIRED` **and**
ownership readiness is `MISSING` (the backend sets both together only when the case has no
ownership analysis, `clm_orchestration.py` ~1625–1627). Never for READY, REVIEW_REQUIRED,
FAILED or IN_PROGRESS ownership, nor when only one signal is present. It leads the UBO
steering plan (then the existing ownership-evidence lines), is not required, and is not added
to the "what ownership evidence is needed" topic. Tests cover every ownership state, the
both-signal rule, verbatim display, a withheld paraphrase ("This case has no UBOs.") and the
absence of names or "no UBOs" claims.

Snapshots rebuilt: 76 of 84 default turns gain the line (the 8 without are the `completed`
variants S06/C03, which list no `OWNERSHIP_REQUIRED`); nothing removed or reordered; `gold.json`
changes only `snapshot_sha256` (0 labelled turns). Prompt without the topic message 9,218
chars (bound 9,250; 32 left). Full suite 2,146 tests: 16 failures = 14 `Errno 24` (pass in
isolation) + 2 ledger-file tests; ruff, format, strict mypy clean. Independent QG R5 on
`c9afd5e` (tree `6c9e4e0`): **PASS**, no Blocker/High/Medium. Backend claim verified (no
other path sets ownership MISSING or the OWNERSHIP_REQUIRED readiness blocker); across all
101 turns only P02#0's topic message changed; five deliberate mutations each failed a test.
Clean-checkout full suite 2,146: 2,131 passed, 15 environmental failures (14 `Errno 24`, 1
ChromaDB "Nothing found on disk" in `test_knowledge_answers`), all 309 tests of the failing
files pass in isolation; ledger-file tests pass. Open: L1 (Low, carried) routing over-match
now leads with the line on e.g. "Who decides the UBOs?" — truthful; Info: 32 chars of prompt
headroom left; helper raises only on shapes the projection never produces. Report:
`C:\Users\shane\Desktop\claude-worktrees\qg-phase-b-r5-probes\QG_REPORT_R5.md`. A paid check
of P02#0 would need separate authorisation (`--questions P02#0 --expect-count 1`).

### GPT-OSS UBO-line check (2026-10-27T04:59Z, `c9afd5e`, owner-authorised) — `SYNTHETIC LIVE`

Owner authorised exactly P02#0, at most US$0.10. `run_phase_b_ubo.ps1` (pinned to
`c9afd5e`), `--questions P02#0 --expect-count 1`; manifest recorded (P02#0, 1); exactly one
call (28): settled and verified (DeepInfra, `openai/gpt-oss-120b`, metadata cost
US$0.00022104 = charge US$0.000222 within 1 µUSD); 0 quarantined; breaker closed. Artifacts:
`data/eval/phase_b/20261027T045921Z-ubo/`.

P02#0 "Who are the ultimate beneficial owners of this company?" — model answer, 6 lines kept,
0 withheld, 0 unsafe, no decline line; 8.3 s; tokens 3,199 / 604 / 584:

1. This case cannot name any UBOs yet because the UBO check has not run.
2. Ownership (shareholder) evidence is needed before the UBO check can run. (section: Ownership & UBO)
3. The UBO check needs the company's owners and each owner's economic interest in percent.
4. Ownership evidence can come from the registry, an uploaded ownership document or a manual ownership declaration.
5. A manual ownership declaration needs a reviewed current document first.
6. Open the "Ownership & UBO" section to inspect the current case evidence.

| P02#0 run | Answer |
|---|---|
| Batch (old rule 17) | decline mixed with 2 lines |
| Rule-17 rerun | bare decline |
| Source rerun (`0fdbea1`) | bare decline (steered to ownership-evidence lines) |
| **UBO check (`c9afd5e`)** | **direct answer + why + what is needed; no decline** |

Reading (one rep, NOT scored): the approved line fixes the outright decline and leads the
answer as intended. The model copied the whole steering list (6 lines, the rule-16 maximum);
lines 3–5 are general process detail, so a shorter answer may be preferable — a possible
later trim of the UBO plan, not needed for correctness.

Spend: **US$0.00022104** (metadata; ledger US$0.000222). Cumulative live spend
**US$0.00586987** (ledger US$0.005884); ledger headroom US$0.994116.

Next candidates after that (one at a time): (2) catalog content for the both-model gaps —
a company-facts/source line (P01#0), directors (P00, P01#2), "marking the UBO check
complete is not offered" (P06#2), a handoff explanation (P04#1); wording needs owner
approval because these are user-facing statements; (3) reasoning effort `low` vs `medium`
for latency (12.4 s median), checked against line validity.

## F. Prioritised improvements (hypotheses to test, not yet measured on GPT-OSS)

Measured on the offline harness for P00 (same prompt the remote model would receive): facts
6,672 chars, knowledge 4,169, rules 2,276, terms 233, question 154; 65 allowed lines offered.

1. Reasoning effort `low` vs `medium` — latency/cost driver; check line-validity is unchanged.
2. Fewer offered lines per question (65 now) via topic steering — exact-line selection accuracy.
3. Facts context selection (≈49% of the prompt) — tokens and latency without losing grounding.
4. System/role instruction wording for refusal and out-of-scope turns (P06/P07).
5. Retrieval relevance for directors/ownership questions (guidance coverage gap).
Method per item: baseline → one controlled change → rerun same turns → compare.

## G. Security, QG and test evidence

- QG on `9db1b8a`: PASS (no Blocker/High). Report:
  `C:\Users\shane\Desktop\claude-worktrees\qg-phase-b-9db1b8a-probes\QG_REPORT.md`.
- R1 `d0bc648` closes M1 (earlier unverified calls verified by preflight; `finish()` in
  `finally`), M2 (ref kept on post-start stream failures; no-ref calls quarantined), L1 (key
  limit ≤ allocation + one reservation), L2, L3 (live runs only on the Phase B file with
  `--only`), L4 (marker/provider-path containment tests), L5 (odd listings fail closed).
- Re-QG on `d0bc648` (tree `4951548`): **PASS**, no Blocker/High/Medium; M1, M2, L1–L4
  closed, L5 partly closed (Info: `fetch_public` has no overall deadline/body bound). New
  N1 (Low, open): a usage chunk with cost before finish followed by a stream error settles at
  the reported cost, not the reservation (under-count ≤ one reservation ≈ US$0.02; caught by
  the per-call `/generation` cost check → `reconcile_drift`, and by preflight reconciliation).
  S1 (owner script) addressed: the script refuses unless HEAD is exactly `d0bc648` and clean.
  Report: `C:\Users\shane\Desktop\claude-worktrees\qg-phase-b-d0bc648-probes\QG_REPORT_R1.md`.
- Focused suites on `d0bc648`: 392 passed. Full assistant suite: 2,087 tests, 15 failures =
  14 `OSError [Errno 24]` + 1 ChromaDB internal error, all passing in isolation (276 passed);
  same environmental class as A2. ruff, ruff format, strict mypy (49 files), secret scan: pass.
- Later independent QGs (reports under `C:\Users\shane\Desktop\claude-worktrees\`):
  R2 `52b813c` PASS (`qg-phase-b-52b813c-probes`), R3 `243d98e` PASS
  (`qg-phase-b-243d98e-probes`; it did not run `test_speed.py`, which failed there — found
  later, owner raised the bound to 9,250), R4 `0fdbea1` PASS with the full suite
  (`qg-phase-b-0fdbea1-probes`), R5 `c9afd5e` PASS with the full suite (`qg-phase-b-r5-probes`).
- Not run: full backend/frontend suites, E2E, hosted CI (assistant-only change).

## H. Commit, branch, worktree

Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-phase-b-20261027`, branch
`feat/assistant-phase-b-gptoss-20261027`, base origin/main `3dcd5cc`. Commits (local, not
pushed): `9db1b8a` → `d0bc648` → `52b813c` (metadata wait + recheck) → `243d98e` (rule 17)
→ `0fdbea1` (source-aware answers, manifest) → `c9afd5e` (UBO line) → closure commits
(regression tests + this report; their SHAs are in the handoff, since a commit cannot name
itself).

## H2. Pre-run verification for the authorised live evaluation (2026-10-27)

Owner authorisation "PHASE B — AUTHORISED GPT-OSS 120B LIVE EVALUATION": US$0.10 per
question, US$1.00 for the 17-question batch, reviewed commit `d0bc648`, no retries, top-ups
or extra batches.

- Worktree HEAD `d0bc648`, no tracked edits; the owner script's reviewed-commit guard passed.
- Ministral-3 8B baseline files untouched; Ollama confirmed at `127.0.0.1:11435` (Machine
  `OLLAMA_HOST`).
- Offline preview (MockTransport, real endpoint record, CLI default settings, no network): 17
  requests, one identical envelope — `openai/gpt-oss-120b`, `max_tokens` 2000 (600 answer +
  1400 reasoning), reasoning `medium` with `exclude: true`, provider `only`/`order`
  `deepinfra/bf16`, `allow_fallbacks: false`, `require_parameters: true`,
  `data_collection: deny`, `zdr: true`, `quantizations: [bf16]`, `max_price` = listed
  prices. Message payloads 9,136–14,588 bytes (limit 32,768).
- Outbound content scan: company "GARDEN BUSINESS", UEN `11111999A`, addresses
  "18 OFFICIAL MOCK STREET" / "18 GARDEN WALK", synthetic document ids; no NRIC-like
  ids, emails or phone numbers. The only person-like name is the viewer "Maya Lim", one of
  the five fixed synthetic profiles (`docs/PROJECT_CONTEXT.md`, `access.py`); already a
  fictional alias, so not replaced (replacing would change the reviewed commit and break
  comparability with the baseline).
- Public listing re-verified 2026-10-27: `deepinfra/bf16` unique of 25 endpoints, US$0.037/M
  in, US$0.17/M out, no other prices, max completion 117,964, DeepInfra bf16, parameters
  supported, in the ZDR list, 30-min uptime 100%.
- Spend bounds: one call per question; the reservation ≈ US$0.021 (prompt bound + 117,964
  output tokens) is below the US$0.10 per-question cap; 17 reservations ≈ US$0.35 within
  the ledger cap (opening usage + US$1.00). A reported cost above the reservation opens the
  breaker (`cost_above_reservation`) and stops every later call; `/generation` cost and
  provider are checked per call. The reservation estimate is not a proof of an absolute
  spend bound.
- Not verifiable through the API: workspace association, auto top-up and prompt logging —
  owner attestation in the script (YES prompt).

### First owner run (2026-10-27): preflight FAIL, no inference request

Owner ran `run_phase_b.ps1` (YES attested, key typed hidden). Preflight: every check PASS
except `key.limit_within_allocation` — key limit remaining US$10.000000 (usage 0.000000,
reset never) is above the allowed US$1.00 + one reservation (US$1.021278). The script created
the ledger (opening usage 0.000000, cap 1.000000, alias key-01), re-ran preflight (all
ledger checks PASS, same single FAIL), stopped with "Preflight FAILED: no inference request
was made" and removed the key. Ledger after: charged 0, open calls 0, breaker closed. Spend
US$0.00. The check was not relaxed: the US$10 workspace budget may stay, but the key's own
limit must be at most US$1.02 (set it to US$1.00 while usage is 0).

### Second owner run (2026-10-27): preflight FAIL, no inference request

After the owner set the key limit to US$1.00: `key.limit_within_allocation` PASS (remaining
1.000000), but `key.limit_never_resets` FAIL — `/api/v1/key` now reports a non-null
`limit_reset` (a periodic reset; the first run reported null). All other checks PASS; the
ledger was reused (no new init). Key removed; spend US$0.00, ledger unchanged. The check
was not relaxed.

Third run: `gate.account` refused `CREDENTIAL_MISSING` before any network call (the pasted
key had one extra non-printable/space character; the shape check accepts printable ASCII
only). Spend US$0.00.

### Fourth owner run (2026-10-27T01:11Z): smoke answered, call QUARANTINED, batch NOT run

Preflight PASS on every check (key limit US$1.00, reset never, usage 0; ledger reconciled).
Smoke P00 was sent once. Artifacts: `data/eval/phase_b/20261027T011109Z-smoke/`
(`answers.jsonl`, content-free `calls.json`).

| Field | P00 (GPT-OSS 120B) |
|---|---|
| Model / serving provider | `openai/gpt-oss-120b` requested on `deepinfra/bf16`; provider **NOT VERIFIED** (no metadata) |
| Model response vs fallback | model answer, 6 allowed lines shown |
| Line validity | 1.00 (6 kept, 0 left out, 0 unmapped) of 65 offered |
| Unsafe displayed lines | 0 |
| Latency | first model piece 28.1 s, first shown line 28.3 s, total 30.2 s |
| Tokens | prompt 3,118; completion 1,135; reasoning 1,279 (reported); cached 0 |
| Cost | US$0.000309 from the stream's usage chunk (= 3,118 × 0.037/M + 1,135 × 0.17/M); **not verified** against `/generation` |
| Reserved | US$0.020596 (≤ US$0.10 per-question cap) |
| Remaining batch budget | US$0.999691 (ledger cap 1.000000) |
| Ledger | settled, verification `quarantined`, breaker **OPEN** (`routing_anomaly`) |
| Human correctness | NOT_SCORED |

Why it stopped: `GET /api/v1/generation?id=…` returned 404 on all 8 bounded attempts (~14 s
of waiting), so verification recorded `metadata not_published`. The reviewed design treats
unverifiable provider/cost as a routing anomaly: the call is quarantined and the breaker
opens, which refused the batch. Behaviour is as designed (fail closed); nothing was retried.

Open questions: (1) is generation metadata delayed beyond ~14 s, or never published for
ZDR / no-logging requests? (2) the reported reasoning tokens (1,279) exceed the billed
completion tokens (1,135) — whether reasoning is billed inside completion is exactly what
the metadata check was meant to confirm.

Answer comparison on P00 (implementer reading, NOT scored): Ministral declined ("I can't
answer that from this case's data"); GPT-OSS gave six relevant generic lines (document vs
ACRA comparison, causes of a difference, check against the document, choosing a value is
not verification, ownership provisional) but nothing specific to directors — consistent
with the catalog gap (no director lines are offered).

### Metadata-gap fix `52b813c` (tree `7e5da38`), local commit, not pushed

Owner request: smallest fix (longer bounded wait, then re-check the smoke generation), fresh
independent QG, no batch before PASS.

- Per-call verification waits at most two minutes for `/generation` (25 attempts, 5 s
  apart; was 8 × 2 s), then still fails closed (quarantine + breaker).
- `evaluate_answers.py recheck` (same live gate and decisions, no inference): re-reads
  quarantined calls' metadata and the key's usage; read-only (no verification or breaker
  change); PASS only if each quarantined call now matches, the breaker is open for
  `routing_anomaly` alone and the key's usage is within the ledger. Writes content-free
  `data/eval/phase_b/<stamp>-recheck/recheck.json`.
- Owner script `data/phase_b/run_phase_b_batch.ps1` (git-ignored), pinned to `52b813c`:
  YES + hidden key → recheck → reconcile on the key's usage → `reset-breaker --code
  routing_anomaly` → batch P01–P07 only (P00 is not asked again) → status → key removed.
- Evidence (implementation worktree): `test_phase_b_live.py` 67 passed; focused suites 547
  passed, 2 failed only because the real ledger now exists in this worktree (both tests
  assert no ledger file at the default path); ruff, ruff format, strict mypy (49 files) clean.
- Independent QG R2 on `52b813c` (tree `7e5da38`): **PASS**, no Blocker/High/Medium.
  Clean review checkout: focused suites 549 passed (the 2 ledger-path tests pass there), ruff,
  format, strict mypy clean, 28 offline probes passed; refactor equivalent across 581 cases;
  recheck leaves the ledger byte-identical on every path. Open Low: L-1 an unexpected
  exception or Ctrl-C inside the recheck loop prints `RECHECK PASS` / writes all-ok checks
  although the process exits non-zero (the owner script still stops; no spend or breaker
  effect); L-2 no committed test of the CLI PASS path or usage lower bound (probed OK).
  Report: `C:\Users\shane\Desktop\claude-worktrees\qg-phase-b-52b813c-probes\QG_REPORT_R2.md`.
  The batch may run via `run_phase_b_batch.ps1`; it proceeds only if the live recheck passes.

## I. Status and remaining owner decisions

Iteration closed (owner directive "PHASE B — CLOSE SOURCE-AWARE ANSWER IMPROVEMENT"). The
owner is satisfied with the P01#1 and P02#0 live results; no further paid inference.

Live evidence summary (all `SYNTHETIC LIVE`, DeepInfra-verified, 28 calls): spend
US$0.00586987 by generation metadata (ledger US$0.005884, cap US$1.00, headroom US$0.994116);
no question above US$0.00033880 (limit US$0.10). The 8-versus-7 rerun deviation is recorded
above; paid runs now require an explicit counted question manifest. Raw answers, call
records and the budget ledger stay in the git-ignored `apps/assistant/data/` and are not
committed; keys were typed by the owner only and never stored.

Closure regression tests (`tests/test_source_and_owner_topics.py`, offline): registry MOCK vs
LIVE/SANDBOX source wording and live-claim rejection; UBO analysis not yet run; analysed
ownership (provisional candidates) gets no "not run"/"missing" lines; missing vs disputed
ownership evidence get different lines; out-of-scope questions get no steering; through the
service on the Phase B case a bare decline is shown alone (no padding) and the source/UBO
lines verbatim; injected or prose model text shows no unsafe line on any of the 17
questions; unsupported authority or "no UBOs" claims are withheld.

Outstanding Low findings (none blocking): N1 (R1) usage-before-finish under-count, caught by
the `/generation` cost check; R2 L-1/L-2 (recheck message on interruption; CLI PASS path
untested); R3 L1 snapshots — closed by the rebuild; R3 L2 server required-line padding on
other topics (not on the new ones); R3 L3 rule 3 vs rule 17 (did not occur); R4/R5 L1 the
new routing also steers a few unintended phrasings (truthful lines only). Info: prompt
headroom 32 chars under the 9,250 bound.

Not done and not authorised: human correctness scoring (all NOT_SCORED); push, PR, merge.

API/type, schema, connector, configuration (one new setting), business-rule, mapping,
auth/security (credential path unchanged; new read-only account calls), architecture, provider
status (remote profile stays DORMANT in the service; harness-only live path) and runtime
behaviour of the running service: unchanged except as listed.
