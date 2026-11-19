# Synthetic case reasoning: local implementation handoff

Owner-authorised local implementation and mocked verification, 2026-11-19. The policy
owner is DECISION_LOG.md, D-142 amendment NL. No publication, deployment, paid calls,
activation or independent Quality Gate verdict is included.

## Identity and scope

- Branch: `codex/synthetic-case-reasoning-20261119`; uncommitted local candidate.
- HEAD / BASE_SHA / saved origin/main: `b409077aae240a04fcf57dafbdbd7c39ce3e747c`.
- Preserved primary checkout local main: `d0142d8e`; no edits to its unrelated state.
- Recorded deployed B3 assistant: `5ad86fb527f82c8c430af19ea2e2b1213d1b7407`.
  Its assistant delta is carried forward onto origin/main, retaining main backend/frontend.
  B3 UBO and D-146 Insights are prerequisites, not newly designed functionality.
- Remote refresh was unavailable during investigation (GitHub DNS failure). The saved
  integration baseline is explicit; latest-remote readiness is not claimed.

## Behavior and minimal owners

Natural in-scope questions reach the model without a canonical-intent match only after
per-answer D-095 verification of synthetic company, registry, seeded viewer, exact document
digests, values and approved knowledge. Questions remain untrusted PERSON text. Every turn
is pseudonymised and independently residual-checked before the exact, single-use cleared
wire payload can be sent. No new question-variant list is introduced.

The existing server context owner supplies at most three previous exchanges from this
user and case. Only a contiguous suffix of verified-synthetic model answers qualifies;
local/fallback answers reset it. A changed evidence digest drops old context. Browser
history is excluded. Earlier replies are not evidence; unresolved references require
clarification against current evidence.

New runtime delta from B3:

| File under apps/assistant/ai_assistant | Change |
|---|---|
| config.py | Separate synthetic-only CASE_REASONING_DECISION; broader HOSTED_PRIVACY_DECISION stays None. |
| main.py | Natural admission, real provenance check, safe fallback before spending, refreshed evidence/context binding and ownership withholding. |
| privacy_boundary.py | Exact-admission exception for protected questions/history; alternating bounded turns and residual/wire checks. |
| case_contexts.py | In-memory suffix provenance and evidence binding in the existing scoped owner. |
| copilot.py | Current-evidence/clarification instruction; strict external scope screening; type narrowing only in B3 advisory helper. |
| anthropic_chat.py | Existing reviewed system blocks may precede history; closed block/order and exact wire validation remain. |

Regenerated synthetic_eligibility.json registers the three verified PDFs. The two generated
vocabularies include only reviewed fixed service/synthetic wording. Tests update superseded
canonical-only expectations, explicitly exercise rollback, and add natural-history/adverse
boundary coverage. Other assistant changes against origin/main are B3 carry-forward.

## Authority and safeguards

D-142 NL explicitly amends P30, P31 and OD-3. The owner accepts ambiguous residual privacy
risk only for verified synthetic demonstrations, never real client or sponsor data. General
chat, Support chat and Try remain closed externally. No arbitrary question is trusted service
wording. The unadopted broader pseudonymised-data policy remains unadopted.

Original authority is distinguished from implementation: D-139 records owner-approved
architectural direction on 2026-11-15; same-day OWNER_APPROVALS explicitly records synthetic-only
Anthropic terms. D-142's 2026-11-16 approval concerned local mocked implementation; its R4
handoff quotes 2026-11-17 Option A/no-person-text/no-history approval. Current approval
supersedes that restriction only inside the verified-synthetic case-chat boundary.

B3 UBO_CALCULATION, provisional/advisory disclosures, deterministic Decimal ownership and
D-146 Insights remain. The natural path withholds ownership that fails B3 completeness.
Privacy minimisation, grounding/claim validation, RBAC/team scope, safe inaccessible-case
404, read-only behavior, human approval, spending/rate/egress limits and single-use wire
binding remain. Direct mutation requests retain their deterministic no-spend refusal.

Public API and shared types, durable schemas, backend connectors, GoldTier mappings and
onboarding/ownership business rules are unchanged. Internal admission/context fields, the
Anthropic prompt adapter, code configuration, assistant runtime and security admission policy
change. No architecture owner/dependency/store or provider-status change occurs. Evidence
remains Local/Mock; it does not establish Live interoperability or provider answer quality.

## PDF verification and registration

Existing evidence: outputs/c10-release-b7be6631/AI_ASSISTANT_AND_INSIGHTS_INVESTIGATION.md
and outputs/b3-acceptance-diag/B3_ACCEPTANCE_DIAGNOSIS.md in the preserved primary checkout.
D-119 L4 approves repaired copies as the parsing workaround. Fixture/external-use approval
is conditional in the owner's current instruction, not inferred from that workaround.

All three candidates: one page, strict PdfReader success, unencrypted, explicit synthetic
and demo/test disclaimer, expected fixture company and classification labels, no detected
embedded attachments or document-level OpenAction/AA. No document bodies are retained in
this report. Full digests match the earlier investigation's prefixes. Bytes are copied
unchanged; no parser repair or safety relaxation occurs.

| Exact fixture filename | SHA-256 |
|---|---|
| 1. OPQ_Synthetic_Onboarding_GoldTier_Details_20261104_repaired.pdf | 27d315884468d0760410122decd094fdb4628a87f0066778dbab28ba98b44b01 |
| 2. Garden_Synthetic_Onboarding_GoldTier_Details_20261104_repaired.pdf | b3871d115e50a4fec3faf4af2ad45ced553f3b5e58b7fa2f22a1b9d18eba60c6 |
| OPQ 201511222D onboarding_classification.pdf | 9adab758e9a9182ae6ee6847e056d6f9c1714bf3ee0ca7c3da8a7006f598f14f |

## Verification and limits

Final integrated assistant acceptance: **4,828 passed, 27 skipped, zero failures/errors**
across 101 isolated modules. This includes all 24 new reasoning cases, both mocked provider
transports, 62 synthetic-eligibility cases, B3 UBO intent/calculation/advisory checks and
D-146 generation/gating. Skipped cases are not represented as passing evidence. Earlier
diagnostic runs remain separate and are not represented as acceptance. No production
provider was contacted.

The runtime/test/fixture manifest stayed unchanged throughout the final run:
`d005b90c900dde14d3d11e1ef6cd0079a9bb087eade4b6594e650cffe55eb75b`.
Exact per-file hashes and per-module counts are in
`outputs/nl-acceptance/final/identity.json` and `final/summary.json`. The implementation
remains uncommitted at the BASE_SHA above; the manifest identifies tested content, not a
new Git revision. Source changes invalidating earlier results received affected reruns.

Reused valid evidence: 90 backend readonly/POC lifecycle tests, 44 contract tests and 33
secret-scanner tests pass. Backend/API/target/POC source is unchanged by later assistant
control corrections. No full backend/frontend, physical Mongo or publication pre-PR gate is
claimed for this bounded assistant-only uncommitted handoff.

Final Ruff and mypy pass (86 source files). Architecture and project-state guards pass.
Task-owned secret scan has no findings. The repository-wide scanner has two pre-existing
URI-pattern findings in unchanged test_p2_1_migration.py:592,1221; values are suppressed and
that unrelated file is not modified. Vocabulary consistency reports REVIEW_REQUIRED with
no drift. A read-only advisory reviewer examined every vocabulary delta and the focused
privacy/context/runtime changes, including refusal classification; no open finding remains.
This is implementation-stage review, not independent QG PASS.

Complete task diff review includes new files: unchanged B3 prerequisite code is verified
against its recorded revision, and the six-file reasoning delta, test updates, fixture
manifest and durable decisions are reviewed directly. No new fallback owner, service,
dependency or persistence layer is added. The retained canonical path is the explicit
exact-lines rollback and specialised B3 UBO admission, not a competing reasoning owner.
Tracked diff whitespace and task-owned new Markdown whitespace pass. Task-only scan scope
and B3 comparisons are recorded in task-secret-scan.json and b3-preservation.json under
outputs/nl-acceptance. This is bounded local evidence (confidence B); real-provider response
quality and independent QG are outside its claim.

The strict external scope screen can conservatively refuse legitimate onboarding questions
containing known everyday-topic terms. Mocked evidence proves admission, context and safety
mechanics, not natural model response quality. Existing qualifications are invalidated by
the changed basis; external activation/requalification requires separate authorisation.

Next authorised boundary: retain the local uncommitted worktree for owner review. Independent
QG is a separate assigned run; publication, deployment, paid calls and Git publication are
not authorised. No commit, staging, push, PR or merge has occurred. The task worktree remains
intentionally dirty; the primary checkout is preserved.
