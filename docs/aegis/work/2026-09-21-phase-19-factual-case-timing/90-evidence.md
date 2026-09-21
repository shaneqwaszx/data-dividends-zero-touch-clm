# Phase 19 factual case timing - Evidence


## EvidenceBundleDraft: verification

- Artifact key: focused-and-broad
- Slice ID: verification
- Type: test
- Source: local current uncommitted candidate
- Summary: Backend 1106 passed/28 env skips; frontend 262 passed; focused timing/portfolio passes; Ruff, mypy, typecheck, build, contracts, governance and security checks pass.
- Verifier: Phase 19 implementer
- Evidence status: evidence-finalized

## EvidenceBundleDraft: physical

- Artifact key: physical-mongo
- Slice ID: physical
- Type: physical-test
- Source: disposable MongoDB 7 container on port 27029
- Summary: Eight suites, 28 collected/28 passed, zero failed/errors/skips; generated databases and owned container/volume absent after cleanup.
- Verifier: Phase 19 implementer
- Evidence status: evidence-finalized

## EvidenceBundleDraft: browser

- Artifact key: guarded-browser
- Slice ID: browser
- Type: e2e
- Source: guarded Playwright on ports 8799/4199
- Summary: 6/6 authenticated browser scenarios pass, including active/completed/detail/stage wording, no-action request stability, and newer observed_at after manual reload; ports free afterward.
- Verifier: Phase 19 implementer
- Evidence status: evidence-finalized
