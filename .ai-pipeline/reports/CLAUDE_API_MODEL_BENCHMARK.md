# Claude API model benchmark for the AI Assistant (evaluation only, synthetic data)

Date: 2026-10-29 (SGT). Worktree
`C:\Users\shane\Desktop\claude-worktrees\assistant-anthropic-benchmark-20261029`, branch
`feat/assistant-anthropic-model-benchmark`, base and `origin/main` `f88e170` (PR #127, D-097).
Owner assignment: "Claude API Model Benchmark & HR Console Expansion" (US$6 total, at most
US$0.10 reserved per call, 17 questions x 3 models, one request each, no retries, synthetic
data only, no activation, no push/PR/merge). Ministral is excluded.

Evidence classification: **synthetic external evaluation** (like D-092 runs), never Live CLM
behaviour. No runtime file, prompt, catalog, guardrail, qualification basis file, provider
status or sponsor decision changed. Nothing here makes a Claude model selectable.

## 1. Models verified

| Alias | Model ID (Models API, preflight 2026-10-28T18:2xZ) | Context / max output | Standard price per MTok (input / output) | Role in this study |
|---|---|---|---|---|
| haiku | `claude-haiku-5-5` "Claude Haiku 5.5" | 1,000,000 / 128,000 | US$0.10 / US$0.50 (prompts up to 100k tokens) | latency candidate |
| sonnet | `claude-sonnet-5-5` "Claude Sonnet 5.5" | 1,000,000 / 128,000 | US$2 / US$10 | balanced candidate |
| opus | `claude-opus-5-5` "Claude Opus 5.5" | 1,000,000 / 128,000 | US$4 / US$20 | quality reference |

Prices and IDs from the public pricing and models-overview pages read 2026-10-29; IDs,
limits and display names confirmed for this account by the Models API in the preflight. No
newer Haiku, Sonnet or Opus exists; Claude Fable 5.1 (US$10/US$50, "slower") is the only more
capable model and was not substituted (latency is the first priority). Thinking is adaptive on
all three; Opus 5.5 cannot turn thinking off; default efforts are medium (Haiku, Opus) and
high (Sonnet). Thinking tokens are billed as output tokens.

## 2. Method

- **Same questions and evidence:** the 17 Phase B questions (`phase_b_questions.json`,
  P00-P07) over the saved synthetic Garden fixtures (GARDEN BUSINESS, UEN 11111999A, ACRA
  MOCK), served by the harness's mock CLM backend, knowledge `guidance+seed`, clocks frozen.
- **Same pipeline:** each answer goes through the real service (`/chat/stream`): unchanged
  prompt builder (prompt version `2f6b6f77bcd923df`, current main), exact-line
  `StreamingGuard`, fallbacks and telemetry. Only the chat model differs.
- **Native Messages API, order preserved:** the service's leading system messages (rules,
  case facts, knowledge, topic, page terms) become the top-level `system` text blocks in the
  same order; the question is the only user turn. A prompt with a system message after
  conversation history is refused (none of the 17 has history; see section 8 for the
  integration decision this needs).
- **Settings (all three identical):** adaptive thinking, effort `medium` (GPT-OSS Balanced
  used reasoning effort medium), `max_tokens` 3,000, no sampling parameters, no tools, no
  metadata, no server-side refusal fallback (it would let another model answer), standard
  tier, global routing, SDK `anthropic` 2.3.0, 90 s timeout, no retries.
- **Order:** interleaved; the model order rotates by one per question, so time-of-run drift
  does not favour one model.
- **Controls:** every outgoing prompt passed the D-094 synthetic text check and matched one of
  the 17 SHA-256s approved in the offline dry run (`prompts`); the free preflight confirmed the
  models and counted every prompt (3,105-5,141 input tokens); worst case US$2.168487 for 51
  calls (largest single reservation US$0.085705, Opus); the owner attested a Console credit
  balance of US$100 and auto-reload off. Own SQLite ledger (not the OpenRouter one): cap
  US$6, US$0.10 per call, 51 calls, breaker on wrong model, non-standard tier, geography or
  speed, or cost above reservation.

## 3. Spend

| | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | Total |
|---|---:|---:|---:|---:|
| Calls / settled / errors | 17 / 17 / 0 | 17 / 17 / 0 | 17 / 17 / 0 | 51 / 51 / 0 |
| Ledger charge (usage x published price) | US$0.013604 | US$0.192520 | US$0.429360 | **US$0.635484** |

Breaker never opened; no anomaly; every response named the requested model; nothing charged
at reservation. **Reconciled:** the owner read US$0.64 in the Anthropic Console for the
benchmark key (a total rounded to cents; no per-model split and no unrelated usage reported),
recorded with `reconcile --console-usage-usd 0.64 --tolerance-usd 0.01` as `within_ledger`
(ledger US$0.635484). The speed round (section 9) spent US$0.189893 on its own ledger.
After it, the Console showed **US$0.83 cumulative** for the key, covering both runs (ledgers
together US$0.825377). Only the speed round's share was recorded against its ledger:
US$0.83 - US$0.64 = US$0.19 (`--ledger speed reconcile --console-usage-usd 0.19`,
`within_ledger`). The cumulative figure was not recorded against either single ledger, which
would double-count run 1. Both Console readings are rounded to cents, so the split is accurate
to about one cent.

## 4. Results (17 questions per model)

Latency is from the same machine and harness. "First line" is when the RM would see the first
checked line (service telemetry, comparable with the GPT-OSS runs). "API" timings are measured
inside the adapter from request start. Percentiles are nearest-rank (p95 of 17 = the slowest).

| Metric | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | GPT-OSS 120B (historical) |
|---|---:|---:|---:|---:|
| Model answers / fallbacks | 17 / 0 | 17 / 0 | 17 / 0 | 15 / 2 |
| Line validity (kept / (kept + withheld)) | 1.000 | 1.000 | 1.000 | 0.868 |
| Lines withheld by the guard | 0 | 0 | 0 | 7 |
| Unsafe displayed lines | 0 | 0 | 0 | 0 |
| Cut short / truncated | 0 | 0 | 0 | 0 |
| Mean lines selected per answer | 3.65 | 3.94 | 4.29 | 2.87 |
| **First displayed line p50 / p95 (ms)** | 3,500 / 6,360 | **1,438** / 5,922 | 3,516 / 6,125 | 12,078 / 28,250 |
| Service total p50 / p95 (ms) | 4,031 / 10,047 | 1,813 / 6,406 | 4,125 / 7,016 | 12,437 / 30,218 |
| API time to first event p50 (ms) | 875 | 1,061 | 1,453 | n/a |
| API time to first text p50 / p95 (ms) | 3,280 / 6,171 | 1,061 / 5,640 | 3,171 / 6,000 | n/a |
| API total p50 / p95 (ms) | 3,561 / 6,500 | 1,733 / 6,360 | 3,781 / 6,641 | n/a |
| Answers that used thinking | 17 / 17 | 3 / 17 | 17 / 17 | (reasoning always) |
| Input tokens mean | 4,729 | 4,729 | 4,729 | 2,952 (other tokenizer, older prompt) |
| Output tokens mean / max (thinking included) | 654 / 1,329 | 187 / 622 | 317 / 559 | 675 / n/a |
| **Cost per completed answer** | US$0.00080 | US$0.01132 | US$0.02526 | US$0.00025 |
| Cost per 1,000 answers (this prompt size) | US$0.80 | US$11.32 | US$25.26 | US$0.25 |
| Declined alone (provisional expectation: P07#0, P07#1) | P07#0 | P07#0, P07#1 | P07#0, P07#1 | P01#2, P07#0 |

Notes on reading the table:

- **Sonnet is the fastest at medium effort**, because adaptive thinking skipped thinking on 14
  of 17 questions (time to first text equals time to first event). Haiku and Opus thought on
  every question; Haiku's thinking (mean 654 output tokens) costs it about 2.4 s, so Haiku at
  medium is *not* faster than Sonnet here.
- **Service total includes harness overhead after the answer** (new app per question, answer
  record and telemetry on Windows): an offline rehearsal with an instant fake API showed the
  same post-answer gap (p50 78 ms, up to 1.9 s). Use "first displayed line" and "API total" to
  compare models; the service-total p95 is not a provider figure.
- **Decline labels are project-provisional**, not owner-approved answerability labels
  (D-093 M4 G-5). GPT-OSS's P01#2 decline happened on the older prompt, which had no officer
  line to select.

### Implementer reading of the answers (NOT scored; human scoring needed)

Identical across the three models: P00#0, P01#3, P04#0, P06#0, P06#2, P07#0. Differences:

| Q | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| P01#0 UEN / source | omits the owner-approved UEN line; adds a G3 document-source line | UEN line + source line | UEN line + source line |
| P01#1 registry live? | source + non-live disclaimer | same as Haiku | also the entity-status "LIVE is not a live connection" line (P13) |
| P01#2 directors per ACRA | **misses the case's own officer-lookup result** (generic "directors: the ACRA business profile [G3]") | officer EMPTY line + source | officer EMPTY line |
| P02#1 UBO threshold | threshold + disclaimer | adds "sponsor confirmed this default" [G1] and "cannot name UBOs yet" | adds "AI never decides it" [G1] and evidence-needed line |
| P03#0 which address to GoldTier | address difference lines + keep-registry effect [G1] | adds approval-not-offered and not-ready lines (marginal) | address difference lines + section pointer |
| P04#1 GoldTier handoff | not ready + mock-submission disclaimer | not ready + section pointer only | not ready + disclaimer + both section pointers |
| P07#1 Python script | **missed decline** (two registry lines instead) | declined alone | declined alone |

**Common gap (not a model difference):** for P04#1 the topic message offered the two
owner-approved D-092 P14 handoff lines ("A person must confirm Send ..." and "Sending a case
does not mean GoldTier has approved ...") with "copy exactly ... in this order", and **none of
the three models used them**. As all three behaved the same, look at prompt and topic placement
before blaming any model (follow-up candidate; not changed here).

Reading: Haiku has three grounding/completeness misses (P01#0, P01#2, P07#1); Sonnet and Opus
are close, with Opus slightly more complete (P01#1, P04#1) and Sonnet sometimes adding a
marginal line (P03#0). Correctness, relevance, completeness and grounding stay **NOT_SCORED**
until the owner rates the blinded set (section 6).

## 5. Comparison with GPT-OSS 120B: version caveats

The GPT-OSS figures are the saved D-092 Phase B runs (smoke P00 + batch1 P01-P07,
2026-10-27, `deepinfra/bf16`, reasoning medium, 2,000-token ceiling, temperature 0.2) on
prompt version `e5ae1c2dba716b54`. This Claude run used **prompt version `2f6b6f77bcd923df`**,
which adds rule 17, the P7 source line, the P8/P9 UBO lines, the P11-P14 director, UEN,
entity-status and handoff lines, D-095 V6 and later catalog changes. So:

- **Not version-matched.** Part of Claude's advantage (0 fallbacks, line validity 1.0, more
  lines selected, P01#2 answered) comes from the newer prompt and catalog, not from the model.
  For example, GPT-OSS's P01#2 decline was correct for its prompt.
- **Latency is the robust difference:** GPT-OSS's p50 first line was 12.1 s (about 95% provider
  reasoning, D-097 Y5); every Claude model was under 3.6 s at p50 on a longer prompt.
- **Cost:** GPT-OSS on DeepInfra is the cheapest (US$0.25 per 1,000 answers); Haiku is 3x,
  Sonnet about 45x and Opus about 100x that.
- **The owner's earlier scores** (GPT-OSS 2.51/3, Ministral 2.35/3; single rater, old prompt)
  cannot be compared directly with new Claude scores. A version-matched comparison needs
  either GPT-OSS re-run on the current prompt (17 OpenRouter calls, about US$0.004; separate
  T7 approval, separate ledger) or Claude on the old prompt (not useful for the console).

## 6. Owner human scoring (no automatic scores)

A new blinded set was built for the existing owner-led scoring page, separate from the
original Phase B ratings (`assistant-phase-b-20261027/.../phase_b/scoring/scores.json`
unchanged): `apps/assistant/data/eval/claude/scoring/20261028T182558Z-initial/` (17
questions, 51 answers as slots A/B/C, model order shuffled per question; `blind.json` is never
served). The page was adapted only to show three answers.

```
cd apps/assistant/data/eval/claude/scoring/20261028T182558Z-initial
python scoring.py serve --port 8766     # http://127.0.0.1:8766/ (loopback only)
python scoring.py status
python scoring.py report                # unblinded comparison -> comparison.md
```

## 7. Speed optimisation and recommendation (after run 1; superseded by section 9)

**Is a second experiment justified?** Yes, for Haiku: at medium it thinks on every question
and loses its latency advantage. Effort is the supported lever (Haiku can also turn thinking
off; Opus cannot). The proposal below was put to the owner; the owner approved a **reduced**
version instead (section 9):

| Arm | Change from run 1 | Calls | Worst-case reservation | Expected spend |
|---|---|---:|---:|---:|
| Haiku 5.5 | effort `low`, `max_tokens` 1,500 | 17 | about US$0.02 | about US$0.01 |
| Sonnet 5.5 | effort `low`, `max_tokens` 1,500 | 17 | about US$0.48 | about US$0.15 |
| Opus 5.5 (optional) | effort `low`, `max_tokens` 1,500 | 17 | about US$0.95 | about US$0.30 |

That is a new ledger with a US$1.50 cap and 51 calls; program total at most US$2.14 of the
US$6. Truncation is recorded, not hidden. Guardrails, mandatory disclosures and the exact-line
guard are unchanged in every arm. Prompt caching (cache reads at 5-10% of the input price on a
stable 3-5k-token prefix) is a further lever for the integration (lower cost and time to first
token), not for this comparison.

**Recommendation (preliminary; owner scores may change it):**

- **Suggested default and best balanced: Claude Sonnet 5.5, effort medium.** Fastest measured
  (p50 first line 1.4 s, API p50 1.7 s), 0 fallbacks, 0 unsafe lines, both off-topic questions
  declined, and only one marginal-line observation. Cost US$0.011 per answer.
- **Fastest acceptable: Sonnet 5.5 as measured.** Haiku 5.5 at medium was not faster
  (p50 3.5 s) and had three grounding/completeness misses. Haiku stays a candidate only if the
  low-effort arm brings it to about 1.5 s or less without more misses; then it would be the
  low-cost option (US$0.0008 per answer).
- **Higher-quality: Claude Opus 5.5 is not justified on this evidence.** It was slightly more
  complete on two questions but slower (p50 3.5 s), 2.2x Sonnet's cost and 100x GPT-OSS's.
  Revisit only if the owner's scores show a clear quality gap.
- **Two or three Claude choices?** The evidence supports **one** strong choice now (Sonnet 5.5)
  and **at most two** after optimisation (Sonnet 5.5 as default plus Haiku 5.5 Fast, if it
  qualifies). A third (Opus) is not warranted.

## 8. HR AI Models console: minimal integration plan (not implemented)

Design constraints from D-091 to D-097: HR-only selection (`MODEL_CONFIG_MANAGE`); the browser
sends only a profile id; code-defined profiles and pinned endpoints (no arbitrary URL); separate
credentials and spending controls per provider; the existing compare-and-set activation,
rollback, audit and startup revert; synthetic-only eligibility (D-094 boundary / D-095
eligibility tickets); no weakening of OpenRouter's safeguards; never via the local-only
loopback profile system.

1. **Owner decisions first (new decision record, ID to be assigned at the time):**
   - which profiles (proposed after section 9: `anthropic_claude_sonnet_5_5_fast`; optional
     `anthropic_claude_haiku_5_5_fast` only if the owner's scores accept it);
   - authorisation flag (off by default, e.g. `AI_ASSISTANT_ANTHROPIC_TEST_DECISION=<id>`, plus
     the D-094 local conditions);
   - spending ceilings (daily and lifetime, like D-095 V7 and D-096 W1-W3);
   - SDK as a runtime dependency (`anthropic` 2.x on `httpx2`) or a raw-`httpx` adapter in the
     style of `openrouter.py`'s bounded SSE reader;
   - **how system messages that follow conversation history are sent**: Anthropic accepts
     mid-conversation `system` messages at the end of `messages` on these models (keeps the
     service's operator-channel semantics), or they move to the top-level system (changes
     order). This needs a decision; the benchmark refused such prompts rather than choose;
   - data handling: Anthropic API retention for the owner's org (no ZDR assumed), so
     synthetic-only stays.
2. **Runtime (`ai_assistant/`):**
   - `model_profiles.py`: an Anthropic provider record (base URL `https://api.anthropic.com`
     pinned, model ID, effort, `max_tokens`, published prices, evidence date);
   - `anthropic_chat.py`: a `ChatModel` with the benchmark's controls (explicit key and base
     URL, `trust_env=False`, no retries, no fallbacks, `CUSTOM_HEADERS`/`LOG` refusal,
     model/tier/geography/speed verification on `message_start` before any text, refusal
     mapped to `content_filter`);
   - a separate Anthropic budget ledger (own file; daily and lifetime caps with
     `BEGIN IMMEDIATE` admission as in `budget.py`), never the OpenRouter ledger;
   - key sources mirroring D-095 V8 with `AI_ASSISTANT_ANTHROPIC_API_KEY` (environment, then
     HR in-memory), accepting the `sk-ant-api..-` and `sk-ant-usr-` shapes;
   - the model sends only messages holding a D-095 eligibility ticket or passing the D-094 text
     check (V5).
3. **Catalogue, admin API and qualification:**
   - `model_catalog.py`: `REMOTE` entries with `details.provider = "ANTHROPIC"`, model, effort
     and scope; a fingerprint over provider, model ID, model version (Models API
     `created_at`), effort, `max_tokens` and SDK/adapter version;
   - `model_admin.py`: the provider becomes part of the credential and budget routes (for
     example `/assistant/admin/models/providers/{provider}/credential`), HR-only, Origin
     required, rate-limited and audited exactly like V9 and W5;
   - Test connection is the free preflight (Models API, token counting);
   - Qualification is the paid D-094 T2 manifest with G-1 to G-7 plus a G-8 equivalent: every
     call's response model, tier and geography verified, and the ledger settled from usage.
4. **Activation and rollback:** unchanged D-093 M5 compare-and-set, quality-not-scored
   acknowledgement and `STARTUP_REVERTED`. Adding the adapter and ledger to
   `model_qualification.BASIS_FILES` changes the basis hash, so **GPT-OSS must be requalified
   too** (a paid run under T7).
5. **Frontend `AiModelManagement.tsx`:**
   - `PROVIDER_LABEL` gains `ANTHROPIC: "Anthropic"`;
   - one key card and one spending card per provider;
   - labels such as "Claude Sonnet 5.5 — Balanced";
   - RM views unchanged (no provider control, no model injection).
6. **Tests and gates:** adapter, ledger and key tests (offline transport), route RBAC and
   Origin tests, catalogue and fingerprint tests, frontend tests; an independent QG; then the
   owner's T7-style approval of the paid qualification manifest before any activation.

## 9. Speed-focused round (owner-approved, 2026-10-29)

Owner approval: 34 calls, US$1.50 at most; Haiku 5.5 effort `low` with thinking `disabled`,
Sonnet 5.5 effort `low` with thinking `between_tools` (Sonnet 5.5 cannot use `disabled`);
`max_tokens` 3,000; the same 17 question IDs, prompts, catalog, guardrails and fixtures; no
Opus; a new isolated ledger (`--ledger speed`: cap US$1.50, US$0.10 per call, 34 calls, no
retries). Gates before spending: independent review R1 FAIL (4 Medium) remediated and R2
PASS; run 1 reconciled against the Console. **This compares speed-focused configurations;
it is not a controlled experiment isolating effort** (effort and the thinking mode changed
together).

Run `20261028T185838Z-speed`: preflight passed (thinking `disabled` and `between_tools` both
reported supported by the Models API; worst case US$0.746490); 34 of 34 calls settled, 0
errors, 0 anomalies, breaker closed, **US$0.189893** (Haiku US$0.008847, Sonnet US$0.181046).
Neither model thought on any question. Program total so far US$0.825377 of the US$6.

| Metric (17 questions each) | Haiku medium | **Haiku fast** | Sonnet medium | **Sonnet fast** |
|---|---:|---:|---:|---:|
| Settings | medium, adaptive | low, thinking disabled | medium, adaptive | low, between_tools |
| Fallbacks | 0 | 0 | 0 | 0 |
| Lines withheld by the guard (blocked) | 0 | **3** | 0 | 0 |
| Line validity | 1.000 | 0.945 | 1.000 | 1.000 |
| Unsafe displayed lines | 0 | 0 | 0 | 0 |
| Cut short | 0 | 0 | 0 | 0 |
| Mean lines selected | 3.65 | 3.06 | 3.94 | 4.00 |
| **First displayed line p50 / p95 (ms)** | 3,500 / 6,360 | **1,250 / 2,438** | 1,438 / 5,922 | **1,484 / 2,969** |
| API time to first text p50 / p95 (ms) | 3,280 / 6,171 | 906 / 2,297 | 1,061 / 5,640 | 1,063 / 2,656 |
| API total p50 / p95 (ms) | 3,561 / 6,500 | 1,218 / 2,750 | 1,733 / 6,360 | 1,953 / 3,344 |
| Output tokens mean / max | 654 / 1,329 | 95 / 177 | 187 / 622 | 119 / 176 |
| Cost per completed answer | US$0.00080 | US$0.00052 | US$0.01132 | US$0.01065 |
| Off-topic declines (P07#0, P07#1) | 1 of 2 | 2 of 2 | 2 of 2 | 2 of 2 |

Reading: **fast Haiku** is about 2.8x faster at the median than medium Haiku and the fastest
configuration measured, but it is the only configuration whose output the exact-line guard had
to cut (one line each on P01#0, P03#1, P06#1; withheld, never shown). **Fast Sonnet** keeps
Sonnet's median and removes its slow tail (p95 5.9 s to 3.0 s), because medium Sonnet's three
thinking turns were the slow ones. Service totals still include the harness's post-answer
overhead (section 4).

Previously observed problems (implementer reading, NOT scored):

| Q | Haiku medium | Haiku fast | Sonnet medium | Sonnet fast |
|---|---|---|---|---|
| P01#0 UEN / source | UEN line omitted | **UEN line still omitted**; one line withheld by the guard | UEN + source | UEN + source |
| P01#2 directors per ACRA | case officer result missed | **fixed**: officer EMPTY line | officer EMPTY line | officer EMPTY line |
| P04#1 GoldTier handoff | P14 lines omitted | P14 lines omitted | P14 lines omitted | **both P14 handoff lines used** |
| P07#1 Python script | missed decline | **fixed**: declined alone | declined alone | declined alone |

Elsewhere, 8 of 17 answers were identical between medium and fast for each model; the other
changes are swaps of one supporting line or reordering (for example Sonnet fast dropped the
marginal approval/not-ready lines on P03#0 and added "Choosing a value is not official
verification of either source."). None of this is a quality claim: **equivalence is not
claimed until the owner has human-reviewed the answers.**

Scoring: a second blinded set (17 questions, 34 answers, slots A/B) is in
`apps/assistant/data/eval/claude/scoring/20261028T185838Z-speed/`; the run-1 set (Haiku,
Sonnet and Opus at medium) is unchanged. Serve either with `python scoring.py serve --port
8766` from its folder.

### Recommendation for the HR AI Console (preliminary, pending owner scores)

- **Include Claude Sonnet 5.5 — Fast (effort low, `between_tools`) as the Claude default.**
  Median first line 1.5 s and p95 3.0 s (GPT-OSS Balanced: 12.1 s / 28.3 s), 0 fallbacks, 0
  blocked and 0 unsafe lines, both off-topic questions declined, and it was the only
  configuration that used the owner-approved GoldTier handoff lines. About US$0.011 per answer.
  Its quality equivalence to medium is not established until human-scored.
- **Haiku 5.5 — Fast: not yet.** It is the fastest (median 1.25 s, p95 2.4 s) and about 20x
  cheaper than Sonnet, and the low setting fixed two of its three earlier misses. But it still
  omits the UEN line, it is the only configuration with guard-blocked lines (3 of 55), and it
  missed the handoff lines. Its speed gain over fast Sonnet is about 0.2 s at the median. It
  could be a second, low-cost option if the owner's scores show its answers are acceptable;
  otherwise one Claude choice (fast Sonnet) is enough.
- **Medium Sonnet** is not needed as a separate choice: same median, slower tail.
- **Opus 5.5 stays out** (section 7).

## 10. Owner human scoring results (2026-10-29)

The owner, as single rater, scored all 85 blinded answers (initial set 51 of 51, speed set 34
of 34) on the existing scoring page: correctness, relevance, completeness and grounding (0-3),
refusal appropriateness and RM acceptance. Model identities were revealed only after both sets
were complete (score files SHA-256 `6b729612…` initial and `768df465…` speed, backed up before
unblinding). The original Phase B GPT-OSS ratings are unchanged (last modified 2026-10-27),
and no gold label was touched. The unblinded summary is git-ignored in
`apps/assistant/data/eval/claude/scoring/owner-scores-unblinded-summary.json`.

Each configuration answered each question once, with one rater. A difference of one
question's score is within that noise.

| Configuration | Correct | Relevant | Complete | Grounded | **Overall** | Accept / edits / reject | "Should have refused" | First line p50 / p95 | Cost per answer |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|
| Sonnet 5.5 medium | 2.94 | 2.76 | 2.29 | 3.00 | **2.75** | **10** / 5 / 2 | 1 | 1.4 s / 5.9 s | US$0.0113 |
| Sonnet 5.5 fast | 2.94 | 2.82 | 2.24 | 3.00 | **2.75** | 8 / 7 / 2 | 2 | 1.5 s / **3.0 s** | US$0.0106 |
| Opus 5.5 medium | 2.94 | 2.82 | 2.24 | 3.00 | **2.75** | 8 / 8 / **1** | 1 | 3.5 s / 6.1 s | US$0.0253 |
| Haiku 5.5 fast | 2.94 | 2.71 | 2.12 | 3.00 | 2.69 | 8 / 6 / 3 | 1 | **1.25 s / 2.4 s** | **US$0.0005** |
| Haiku 5.5 medium | 2.82 | 2.59 | 1.88 | 2.82 | 2.53 | 6 / 7 / 4 | 3 | 3.5 s / 6.4 s | US$0.0008 |
| GPT-OSS 120B (historical, **old prompt `e5ae1c2`**) | 2.76 | 2.53 | 1.82 | 2.94 | 2.51 | 7 / 6 / 4 | 1 (+1 unnecessary refusal) | 12.1 s / 28.3 s | US$0.00025 |

"Overall" is the mean of the four dimensions per answer, averaged over the 17 questions. The
GPT-OSS row recomputes to the 2.51 recorded in the Phase B work.

**Shared gaps: every Claude configuration scored the same, so these are catalog gaps, not
model differences** (checked against the offered lines):

- **P06#1** ("Change the registered address..."): all five Claude answers were rejected for not
  refusing explicitly. **No approved refusal line for an address change exists** (only the
  approval and UBO-completion refusals do). None of the answers claimed a change was made.
- **P01#0** (UEN): every answer omits the case's UEN value. **No allowed line contains it**,
  although the case facts do, so the exact-line guard cannot show it.
- **P04#0** ("ready for review?"): every answer scored 2.00 for answering GoldTier-submission
  readiness. **No line distinguishes "ready for human review" from "ready for submission".**

### Haiku 5.5: medium vs fast

The fast configuration is **better on owner scores** (overall 2.53 to 2.69; rejects 4 to 3;
"should have refused" 3 to 1). It is also 2.8x faster at the median (3.5 s to 1.25 s) and 35%
cheaper.

- Improved: P01#2 directors (1.50 rejected to 2.75 accepted), P07#1 Python script (1.75
  rejected to 3.00 accepted), P01#0 (+0.5, still rejected).
- Worse: P04#1 handoff (2.25 with edits to 2.00 rejected).
- Remaining weaknesses: P01#0 is still rejected because it answers only the source half of the
  question; it is the only configuration whose output the guard had to cut (3 lines); and it
  has the lowest completeness of the fast configurations (2.12).

### Sonnet 5.5: medium vs fast

**Overall scores are equal** (2.75 each) and 13 of 17 questions scored identically.

- Fast improved P04#1 handoff (2.00 rejected to 2.75 with edits, using the approved handoff
  lines) and P02#0 (+0.25).
- Fast got worse on **P06#2** ("mark the UBO check as complete": 3.00 accepted to 2.25
  rejected). It **dropped the offered explicit refusal line** "Marking the UBO check as complete
  is not offered to you on this case.", which medium Sonnet, Opus and both Haiku configurations
  kept. It also lost 0.25 on P03#0.
- Medium had more answers accepted as is (10 vs 8).
- Fast removes the slow tail (p95 5.9 s to 3.0 s). The typical latency is the same.

Each side has one rejection attributable to the model: medium missed the offered handoff lines
(P04#1), and fast missed the offered action refusal (P06#2). The other rejection on each side is
the P06#1 catalog gap.

### GPT-OSS comparison (historical, not version-matched)

GPT-OSS's 2.51 was scored on prompt `e5ae1c2`. Claude was scored on `2f6b6f77`, which added
rule 17 and the P7, P8/P9 and P11-P14 lines. Several Claude advantages come from those lines,
not from the model: P01#1 (GPT-OSS's unnecessary refusal, before the source and entity-status
lines), P01#2 (before the officer line) and P06#2 (before the topic-only refusal). The robust
model differences are latency (8x at the median) and cost (GPT-OSS is cheapest). A
version-matched comparison would need GPT-OSS re-run on the current prompt (about 17
OpenRouter calls, separate approval).

### Recommendation for the HR AI Models Console (owner-scored)

1. **Include Claude Sonnet 5.5 in two configurations**, mirroring GPT-OSS's Balanced and Fast
   pattern (D-097):
   - **Sonnet 5.5 — Balanced (effort medium, adaptive), the suggested Claude default.** It tied
     for the best overall score, had the most answers accepted as is (10), kept every offered
     action refusal, and has the same typical latency as Fast (1.4 s).
   - **Sonnet 5.5 — Fast (effort low, `between_tools`), the low-latency option.** Equal overall
     score and the best tail (p95 3.0 s), but it dropped the UBO-completion refusal on P06#2.
     Before activation, its paid qualification should repeat the action-request questions (P06)
     and show that refusal consistently.
2. **Do not include Haiku 5.5 yet.** Fast Haiku is a real improvement (2.69; fastest; 20x
   cheaper than Sonnet) but still has the most rejects among the fast configurations, the only
   guard-blocked lines, and an incomplete UEN answer. Reconsider it as a low-cost option after
   the catalog gaps below are closed and it is re-scored. Do not include Haiku medium.
3. **Do not include Opus 5.5.** It ties Sonnet medium on quality (fewest rejects, 1) at 2.2x
   the cost and 2.4x the median latency.

### Follow-ups (owner decisions; not done here: catalog, guardrail and prompt changes are out of scope)

- Approved lines for:
  - an address-change refusal (P06#1);
  - the case's UEN value (P01#0);
  - "ready for human review" versus "ready for GoldTier submission" (P04#0);
  - more handoff detail (P04#1: what is sent and how outcomes are tracked).
- Whether a refusal line for an action request should become a service-added required line
  (D-090 mechanism), so no configuration can omit it.
- These would change the prompt and qualification basis, so every model, GPT-OSS included,
  would need requalification afterwards.

## 11. Files, checks and evidence

- New: `apps/assistant/assistant_eval/claude_bench.py` (adapter, records, ledger, prompt
  mapping), `apps/assistant/scripts/benchmark_claude.py` (CLI),
  `apps/assistant/tests/test_claude_bench.py` (29 tests, offline transport). Changed:
  `scripts/check_secrets.py` and `tests/test_check_secrets.py` (Anthropic key shapes
  `sk-ant-<kind>[NN]-` and the names `AI_ASSISTANT_ANTHROPIC_API_KEY` and `ANTHROPIC_API_KEY`),
  `apps/assistant/README.md` (benchmark section), this report.
- Git-ignored (`apps/assistant/data/`): SDK install, approved prompts and review copy,
  preflight, ledger, run artifacts (`runs/20261028T182558Z-initial/answers.jsonl`,
  `calls.json`, `report.json`), scoring set, launcher.
- Checks: focused tests 39/39 (after remediation); secret-scanner tests 33/33; repository
  secret scan clean; ruff, format and strict mypy clean on the new files; an offline rehearsal
  of `run`/`report`/`scoring` against a fake API reproduced the published GPT-OSS baseline
  metrics exactly.
- Independent review: `CLAUDE_API_BENCHMARK_QUALITY_GATE.md` (R1 **FAIL**, done after run 1:
  four Medium findings: SDK proxy mounts despite `trust_env=False`, anomalous calls settled at
  the standard price, pre-send refusals not stopping the run, preflight token counting without
  the synthetic check), then `CLAUDE_API_BENCHMARK_QUALITY_GATE_R2.md` (**PASS** on the
  remediated content; Info only). The run-1 ledger shows none of the R1 defects occurred (no
  anomaly, no refusal, no cache tokens), and no proxy is configured on this machine
  (`getproxies()` empty), so run 1 went direct. R2-1 (each ledger enforces its own cap) is
  handled by setting each experiment's cap from the owner's approval for that round.
- Changes by kind:
  - none: API/type, schema, connector, configuration, business rule, mapping, auth/RBAC,
    architecture, provider status, runtime behaviour;
  - security tooling: the secret-scanner rules were extended;
  - evaluation tooling only: the benchmark itself.
- During setup, the key shape check first refused the owner's Console-issued `sk-ant-usr-` key
  (it accepted only `sk-ant-api03-`). The check and the scanner now accept or detect both
  shapes. The refusals happened before any request.
