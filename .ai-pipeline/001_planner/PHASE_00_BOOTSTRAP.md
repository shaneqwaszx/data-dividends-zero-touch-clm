# Phase 00 — Foundation and Contract Freeze

## Role

You are the execution agent for Phase 00.

Read:
1. `AGENTS.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/decisions/DECISION_LOG.md`
4. `docs/sponsor-questions/OPEN_QUESTIONS.md`
5. all relevant local sponsor artefacts under `private/sponsor-artifacts/`

Do not proceed beyond Phase 00.

## Goal

Create a safe, testable project foundation and freeze the project’s implementation contract before business features are built.

## Required work

### A. Safety and repository checks

- Confirm the current branch.
- Confirm `private/`, `.env`, credentials, tokens, and key material are ignored.
- Inspect tracked/untracked files for obvious secret exposure.
- Do not echo or copy secret values into your response.
- If sponsor files contain apparent live secrets/tokens, report only that secret material exists and identify the filename/type without reproducing the value.

### B. Contract analysis

Inspect the sponsor/API artefacts.

Reconcile:
- direct sponsor decisions already recorded
- standalone OpenAPI files
- combined OpenAPI bundle
- JSON request/response examples
- EDS-GoldTier specification
- data dictionary
- connection/Postman examples

Create:

`docs/contracts/GOLDTIER_CONTRACT_BASELINE.md`

The baseline must:
- list the seven relevant EDS operations
- document required headers/idempotency behaviour where supported
- document key response/error behaviour
- use `POST /v1/eds/parties/{partyId}/amend` as canonical
- identify stale/conflicting artefacts
- clearly distinguish confirmed behaviour from unresolved behaviour

Do not invent missing endpoint details.

### C. Initial application skeleton

Create only the minimum runnable skeleton needed to prove the repo/tooling works.

Backend:
- Python FastAPI
- health endpoint
- basic config pattern
- no real ACRA/GoldTier business integration yet

Frontend:
- React + TypeScript + Vite
- minimal application shell/status page
- no business workflow implementation yet

### D. Test/tooling foundation

Set up the minimum useful checks:
- backend unit test for health
- frontend build/test baseline
- lint/type checks where practical
- secret leakage check where practical

Create CI only if it can be done cleanly without requiring unavailable secrets.

### E. Documentation

Update/create:
- `README.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/contracts/GOLDTIER_CONTRACT_BASELINE.md`

Update decision/open-question documents only when evidence supports the change.

## Explicit non-goals

Do not implement:
- live ACRA
- IDP
- UBO calculations
- GoldTier real calls
- onboarding workflow engine
- dashboard
- exception workbench
- additional jurisdictions

## Completion report

At the end, report:

1. Branch and repo status
2. Files created/changed
3. Tests/checks run and exact outcomes
4. Contract discrepancies found
5. Security concerns found
6. Assumptions made
7. Remaining blockers/open questions
8. Recommended Phase 01 entry criteria

Do not commit, push, merge, or begin Phase 01 unless explicitly instructed.
