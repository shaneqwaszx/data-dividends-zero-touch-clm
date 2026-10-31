# AI Assistant completion (B1-B, B2, B3): independent quality gates

Date: 2026-10-31 to 2026-11-01. Every reviewer below was a fresh agent with no part in the work
it reviewed, working read-only (no edits, no network, no `.env`, no live store). Remediation was
always a separate step, followed by a fresh review of the changed content.

## 1. D-110 design (specification rev 1 to rev 9)

| Round | Reviewed | Verdict | Key findings (all closed) |
|---|---|---|---|
| 1 | design rev 3 | FAIL | H1 the 24-hour fallback always exceeded reconcile's 86,400 s limit; M1–M10 (event id after work, deadline placement, server-side preview, audit trimming, ledger binding, lock in the worker thread, renewal effects, stale figures, month-end revisions, vocabulary) |
| 2 | rev 3 remediation | PASS WITH NOTES | N1–N9 (increment-based overcount rule, idle-window disclosure, revision recovery, single worker, uncertain classification, full post-state compare, state machine, wording, lock location) |
| 3 | consolidated rev 5 | FAIL | M1 two runs could claim one ledger event (an open run not checked at the intent step); Lows |
| 4 | rev 6 | PASS WITH NOTES | N1–N5 (release misattribution, same-P guard, post-chat meta check, owner-close path, wording) |
| delta | rev 7 with the owner's Q12 | FAIL | the test list still expected recovered `applied` against the Q12 text as first drafted |
| delta | rev 8, Q12 as the owner clarified it (intent marker) | PASS WITH NOTES | L1–L10 applied in rev 9 (marker check under the lock, P-matched clearing, recorded P1 attestation, liveness, Windows durability) |

## 2. B1-B implementation

| Review | Reviewed | Verdict | Findings |
|---|---|---|---|
| PR-1a QG | `bf3151b` | FAIL | **H1** the operator's script skipped the lock and marker rules when the ledger profile read was busy, so a CLI reconcile could be resolved as HR's `applied` (reproduced); **M1** owner close could not clear a stale marker; **M2** missing tests; L1–L5 |
| PR-1a re-QG | `2d9eff0` | PASS WITH NOTES | all closed; two wording Lows applied in `7d381a2` |
| Final integrated QG | `ed3f845` (B1-B with PR-1b and E2E, B2 merged, B3 records) | PASS WITH NOTES | **M1** the UAT and evidence records claimed PASS for the integrated full suite before its rerun finished, and referenced this report before it existed; L1–L3 page wording; L4 a local-only file cited; L5 the overhead benchmark's isolation undocumented |

## 3. Remediation of the final QG (focused re-check below)

- M1: the evidence and UAT records now give the completed integrated rerun on `ed3f845` (3159
  tests, 3145 passed, the same 14 Errno 24 failures as B1-B and B2), say what later commits
  changed and how they were re-verified, and point to this report, which now exists.
- L1–L3 (`0f4992a`): RUN_UNRESOLVED points to Resolve only where it exists, otherwise to the
  owner's close; RECONCILE_REFUSED no longer guesses a cause; owner close and the P1 attestation
  are listed under the owner. Page tests 135 / 135, typecheck and the reconcile E2E pass again.
- L4: the UAT cites the tracked evidence record's list of the 14 tests.
- L5 (`c096175`): the overhead benchmark documents the isolation it relies on.

## 4. Constant across every review

- Qualification basis `5dc26b296026…` unchanged; `build_synthetic_boundary.py --check` current;
  no basis file in any diff.
- D-111 is PROPOSED only; `guide.py`, `guardrails.py`, `prompts.py` and `main.py` are unchanged.
- No financial or security finding above Low remains open.
