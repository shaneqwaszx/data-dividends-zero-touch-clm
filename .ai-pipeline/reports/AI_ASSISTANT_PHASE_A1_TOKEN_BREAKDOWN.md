# AI Assistant — Preliminary Context and Token Breakdown (Phase A1, offline)

| Item | Value |
|---|---|
| Date | 2026-10-26 |
| Source revision | `feat/assistant-phase-a1-20261026`, remediated content after Quality Gate finding F-1 (retrieval clock fixed in the harness) |
| Inputs | `apps/assistant/tests/fixtures/eval/snapshots.json` (84 frozen questions, sha256 `9341411d512d3beb…`, rebuilt after F-1) and harness telemetry (`MemorySink` `part_chars`) from offline runs |
| Retrieval mode | Embeddings off (keyword + case context), as recorded in the snapshots |
| Model calls / OpenRouter requests / spend | none / none (not even metadata) / US$0.00 |

**Evidence labels.** Character counts are **EXACT** (measured from the exact messages the
service builds). Token counts are **APPROXIMATE**: no Ministral or GPT-OSS tokenizer is
installed and no provider `usage` has been captured, so tokens are shown as
characters ÷ 4 (lower) and characters ÷ 3 (higher; compact JSON usually tokenizes worse than
prose). **Exact token counts are UNKNOWN** until a tokenizer or provider usage is available
(A2/Phase B). Prices are **VERIFIED** only as at 2026-10-26 (OpenRouter public endpoint
metadata, see the investigation report) and were **not re-fetched**, per owner direction.
Reasoning-token volumes are **ASSUMPTIONS**.

## 1. Where the context comes from

### 1.1 Single-question requests (64 questions, 16 scenarios)

| Source | Prompt part | Mean chars | Median | p95 | Max | Share of all input chars |
|---|---|---|---|---|---|---|
| Prompt builder instructions | rules (`persona_and_rules.md`, first system message) | 1,722 | 1,722 | 1,722 | 1,722 | **17.6%** |
| CLM case facts | `CASE FACTS` system message (includes the allowed-line catalog) | 5,443 | 6,073 | 6,329 | 6,329 | **55.7%** |
| RAG | `KNOWLEDGE` system message (header, entry headers, allowed knowledge lines) | 2,564 | 2,909 | 4,137 | 4,368 | **26.2%** |
| Page-term glossary | `CASE PAGE TERMS` (only when the question names a term) | 14 | 0 | 138 | 290 | 0.1% |
| Conversation history | earlier turns (single questions: only S15's forged turn) | 5 | 0 | 84 | 84 | 0.05% |
| User message | the question | 27 | 25 | 49 | 53 | 0.3% |
| **Total** | | **9,775** | **10,339** | **11,059** | **12,221** | 100% |

Approximate input tokens per request: median **2,585–3,446**, p95 **2,765–3,686**, max
**3,055–4,074** (÷4 – ÷3), plus a few tokens of per-message overhead (UNKNOWN per provider).

By knowledge profile (same questions where comparable):

| Knowledge in the store | Questions | Mean total chars | Mean RAG chars | Mean facts chars |
|---|---|---|---|---|
| guidance + illustrative seed (default) | 56 | 9,928 | 2,805 | 5,353 |
| guidance only (S02) | 4 | 9,584 | 1,757 | 6,073 |
| none (S03) | 4 | 7,827 | 0 | 6,073 |

On the same case and questions (S01–S03), RAG adds 1,757 characters with guidance only and
2,915 with guidance + seed: **+22% and +37% input** over catalog-only requests (7,827
characters).

Inside the case facts (address-conflict case, 6,026 characters of JSON, measured at the same
code on 2026-10-26): allowed-line catalog 1,444; document values read 1,285; blockers 863;
steps 621; recent events 366; discrepancies 306; still needed before GoldTier 289; company
244; page sections 144; overall 93; readiness 92; viewer 45; GoldTier 25.

### 1.2 Conversations (5 four-turn conversations, harness telemetry)

History is what the panel sends back: earlier questions and the answers the user saw,
trimmed by the service to 8 messages and 2,400 characters (700 per turn).

| Turn | Mean total chars (answers = 2 allowed lines) | Mean / max history chars | Mean total chars (answers = case-data fallback) | Mean / max history chars |
|---|---|---|---|---|
| 1 | 9,187 | 0 / 0 | 9,187 | 0 / 0 |
| 2 | 9,540 | 190 / 229 | 9,820 | 470 / 726 |
| 3 | 9,739 | 401 / 448 | 10,341 | 1,003 / 1,453 |
| 4 | 9,864 | 623 / 689 | 10,745 | 1,503 / 2,178 |

The two-line answers are the evaluator self-test rule's lines (the first catalog line and the
first knowledge line where one is offered), standing in for a short model selection; they
are not a model result.

History is small when answers are short allowed-line selections, and grows fastest when the
model fails and the long case-data answer is sent back as history. The 2,400-character cap
bounds it (≈600–800 tokens).

### 1.3 Output side

Answers can only be allowed lines. Allowed lines average 91 characters (catalog, max 152)
and 92 characters (knowledge with tag, max 176); a question offers 34 lines on average (12–51).
A 2–5-line answer is ≈180–460 characters, **≈45–150 tokens (APPROXIMATE)**. The request cap
is 600 tokens (`AI_ASSISTANT_LLM_MAX_ANSWER_TOKENS`). GPT-OSS reasoning tokens are billed as
output and, on most providers, share that cap (investigation report §6.3); their volume is
**UNKNOWN** and is modelled below as an assumption.

## 2. Hypothetical per-request cost (GPT-OSS 120B on OpenRouter)

Prices per million tokens, as listed on 2026-10-26 (all 24 endpoints were in the ZDR list
that day; **re-verify before any spend**):

| Assumption | Input | Output | Basis |
|---|---|---|---|
| Economical | US$0.03 | US$0.15 | Lowest listed endpoints (for example Near AI fp4, Venice int4) |
| Typical | US$0.15 | US$0.60 | Common tier (for example Together, Groq, Nebius, Amazon Bedrock) |
| Conservative ceiling | US$0.35 | US$0.95 | Highest listed input with highest listed output; no single endpoint charges both |

Output = 150 answer tokens + reasoning (none 0, low 300, medium 1,000, high 3,000:
**ASSUMPTIONS**).

| Request | Input tokens | Reasoning | Economical | Typical | Conservative |
|---|---|---|---|---|---|
| Median single question (÷4) | 2,585 | none | US$0.00010 | US$0.00048 | US$0.00105 |
| Median single question (÷4) | 2,585 | medium | US$0.00025 | US$0.00108 | US$0.00200 |
| Median single question (÷3) | 3,446 | none | US$0.00013 | US$0.00061 | US$0.00135 |
| Median single question (÷3) | 3,446 | low | US$0.00017 | US$0.00079 | US$0.00163 |
| Median single question (÷3) | 3,446 | medium | US$0.00028 | US$0.00121 | US$0.00230 |
| p95 single question (÷3) | 3,686 | medium | US$0.00028 | US$0.00124 | US$0.00238 |
| p95 single question (÷3) | 3,686 | high | US$0.00058 | US$0.00244 | US$0.00428 |
| Conversation turn 4, largest (÷3) | 4,313 | medium | US$0.00030 | US$0.00134 | US$0.00260 |
| Hard ceiling (8,000 in, 4,000 out) | 8,000 | — | US$0.00084 | US$0.00360 | US$0.00660 |

Per 1,000 median requests at medium reasoning: ≈US$0.28 (economical), US$1.21 (typical),
US$2.30 (conservative). US$10 would cover ≈36,000 / 8,300 / 4,300 such requests, or
≈11,900 / 2,800 / 1,500 at the hard ceiling. These are hypothetical: no request has been
made, provider routing and retries can change cost, and purchase fees are not included.

## 3. Observations

1. **Case facts dominate (≈56%)**, and about a quarter of them is the allowed-line catalog
   repeated inside the JSON; another fifth is document values, which the model only needs
   for value-specific questions and which are the main privacy exposure.
2. **RAG adds ≈26% of input** and fills its slots on almost every question in this mode
   (guidance + seed questions carry 2.8K characters of knowledge on average).
3. **The instructions are a fixed 1.7K characters (≈18%)**, identical for every request: the
   best candidate for provider prompt caching (with the case facts, when a case is asked
   about repeatedly).
4. **The user's own question is under 1% of input**, and conversation history stays small
   unless the model keeps failing.
5. Output is small by construction; at GPT-OSS prices **reasoning effort, not the answer, is
   likely to dominate output cost** (UNKNOWN until measured).

## 4. Future token-optimisation opportunities (not implemented)

Each needs owner approval, the A1 harness (parity plus selection scores with owner gold) and,
where it changes what the model sees, an evaluation before adoption.

| # | Opportunity | Expected effect (from the measurements above) | Main risk |
|---|---|---|---|
| T1 | Capture provider `usage` and a tokenizer count before optimising (A2/WP3) | Turns the approximations here into exact counts | None |
| T2 | Control reasoning effort and separate the answer budget from reasoning (A2/WP3) | Likely the largest output saving (UNKNOWN) | Lower effort may select worse lines |
| T3 | Data-minimised model view (drop raw document/registry values, names and event text from the model's copy only) | ≈1.8–1.9K characters (≈17–21% of input) on the address case; smaller exposure | Value-specific questions may be answered less well |
| T4 | Retrieval precision (question-specific inclusion floor, adaptive top-k) | Up to the whole RAG share (0.6–4.4K characters, median 2.9K) on questions where nothing specific applies | Missing a useful entry |
| T5 | Present the catalog once as numbered plain lines; drop duplicated page-section names | ≈150–300 characters | Minimal |
| T6 | History policy for a selection task (fewer turns, or user turns only) | Up to 2,400 characters late in conversations | Conversation coherence |
| T7 | Line-ID output instead of copied lines | ≈80–90% fewer answer tokens (ESTIMATE) | Changes the output contract (ADR-012 section C review) |
| T8 | Provider prompt caching with a stable prefix (already ordered for it) | Mostly latency; price benefit only where cache reads are discounted | Session identifiers must stay opaque |

## 5. A2 follow-up recorded

**F-A2-1 — `OPENROUTER_API_KEY` is not read by the settings loader.** The owner provisioned
the key as `OPENROUTER_API_KEY`; `AiAssistantSettings` reads only `AI_ASSISTANT_*` variables
(`env_prefix`), so the key is ignored today (verified offline with a dummy value; presence in
this session's environment scopes: MISSING; the secret was never read, printed, copied or
modified). A2/WP3 must decide how the dormant OpenRouter profile obtains its credential (for
example, read `OPENROUTER_API_KEY` only when that profile is selected) without ever sending it
to the default local model. No change is made in A1.
