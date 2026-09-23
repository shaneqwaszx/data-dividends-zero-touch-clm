# Token-Efficiency Governance — Implementation

## Outcome

Implementation and remediation evidence is green and ready to freeze for fresh
independent re-QG. This is a
`DOCS_ONLY` + `CI_TOOLING` change. It changes no product/runtime behavior, provider,
API/model/type, schema, mapping, business rule, auth/security owner, persistence owner,
or product architecture. Phase 22 remains on hold.

## Identity

- Branch: `chore/token-efficiency-governance`
- `BASE_SHA` and benchmark base:
  `83f46e20a9ad36ae61aacb0f470c1404c4732d64`
- Initial accepted tree: `3a7fa0a1f99a97bbade13d3c1434896000660125`
- Tested content: uncommitted task-owned working-tree candidate; final frozen identity
  is recorded separately before QG.

## Root causes and measurement

The fixed mandatory canonical start set was 4 full documents, 67 headings, 84,891
characters, 84,999 LF-normalized UTF-8 bytes, and 1,366 lines before task-specific
skills, source/tests, planners, or reports. The previous `dev_context.py` output was
1,534 bytes / 22 lines but did not select task sections. A representative prior
governance planner/report was 17,567 / 13,332 bytes. Sampled governance concepts
occurred across 4–8 surfaces, confirming overlap; raw keyword counts were not used as a
reduction target because safety-critical repetition is sometimes deliberate.

The benchmark freezes the exact base proxy above and measures the current deterministic
canonical section union. Task-variable skills, planner, source, and tests are excluded
from the percentage because this change does not reduce their necessary content.

| Scenario | Before chars/bytes/lines | After chars/bytes/lines | Sections | Byte reduction |
|---|---:|---:|---:|---:|
| `DOCS_ONLY` | 84,891 / 84,999 / 1,366 | 44,078 / 44,178 / 762 | 37 | 48.0% |
| `FRONTEND_UI` | 84,891 / 84,999 / 1,366 | 55,215 / 55,315 / 871 | 41 | 34.9% |
| `CI_TOOLING` | 84,891 / 84,999 / 1,366 | 45,850 / 45,950 / 796 | 40 | 45.9% |
| High-risk control (each) | 84,891 / 84,999 / 1,366 | 88,583 / 88,701 / 1,420 | 68 | full current set (+4.4%) |

Routine mean reduction is **43.0%**, above the 30% target. Current selector output is
3,231–3,502 bytes / 43–50 lines across representative modes; its modest increase over
the old summary is included in the result rather than hidden.

## Delta

- `AGENTS.md` and `docs/DEVELOPMENT_WORKFLOW.md` now own Tier 0/1/2 loading,
  fail-closed escalation, delta-only handoffs, compact reports, summary-first evidence,
  and falsified-hypothesis retirement.
- `scripts/dev_context.py` extends the existing read-only owner with deterministic
  multi-class section manifests, exact heading validation, conservative full expansion,
  bounded output, `--full`, and the frozen-base `--benchmark`.
- `tests/test_dev_context.py` covers ordering, headings, unknown and explicitly empty
  input across API/CLI, high-risk expansion, bounded output, policy references,
  deterministic CLI modes, and the target.
- Codex/pipeline/phase skill surfaces reference the canonical owner. Detailed model
  routing was removed from `CODEX_WORKFLOW.md`; Git/publication safety repetition remains
  where omission would be unsafe.
- No new checker framework or CI job was added: the existing security job already owns
  the expanded dev-context unittest suite.

## Safety invariants

TEG-01 through TEG-16 are preserved: current source/contracts/decisions still outrank
summaries; sponsor questions remain triggered authority and are full for high-risk work;
Git/destructive/protected-data/provider-label rules remain in the full constitution;
tests and independent QG are unchanged; reviewers must inspect actual content; unknown
and explicitly empty selection fails closed; high-risk work widens automatically; no RAG/vector database,
agent framework, product/runtime change, provider activation, or Phase 22 was added.

## Verification summary

- Focused `tests.test_dev_context`: PASS, 18/18 in 6.629s.
- Affected governance/tooling modules: PASS, 136/136 in 59.936s.
- Direct project-state, architecture, tooling-config, policy-authority,
  external-provider-readiness, and secret checks: six PASS.
- Ruff on affected Python: PASS. Backend mypy scope is `app`, so this repository script
  is outside its configured target.
- Representative CLI modes: deterministic PASS; unknown and empty classes exit 1;
  output bounded.
- Tracked diff whitespace, five task-owned new-file hygiene checks, and final secret
  scan: PASS. Exact content identity is recorded in the independent-QG handoff.

## Files and limitations

Changed surfaces are limited to the constitution/workflow, Codex/pipeline role
references, the bounded phase skill, existing context script/tests, planner/Aegis
records, and this report. Exact LLM tokens, billing, cache behavior, and proprietary
model context compression are not measured. The proxy measures LF-normalized repository
text; task-variable source/tests and required specialist material remain mandatory.

## Next action

The first independent gate returned `FAIL` solely because whitespace-only class input
was discarded before validation. The canonical selector now rejects every explicitly
empty/whitespace-only element; strict RED/GREEN API+CLI regression evidence is recorded
in the Aegis evidence artifact. Freeze the remediated identity and dispatch a fresh
independent `fyp-quality-gate` reviewer. Publication remains blocked until the exact
verdict is `PASS` on the remediated frozen content.
