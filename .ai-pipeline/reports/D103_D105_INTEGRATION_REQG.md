# D-103 / D-105 integration quality gate: bounded recheck (PR #138)

This is an independent Stage 3 recheck (`fyp-quality-gate`) of the remediation delta that
followed `.ai-pipeline/reports/D103_D105_INTEGRATION_QUALITY_GATE.md`. The reviewer did not
write the reviewed content, the earlier gate, or the remediation. The review was read-only.
The only file created is this report.

## 1. Verdict

**PASS WITH MINOR FIXES**

The delta changes wording only and does not change behaviour. It removes the false claim in
finding L6 ("Support ... never views a case in chat"), and the new D-103 S4 sentence is
accurate. The replacement code comment introduces one new overstatement (R1, Low, comment
accuracy only). Findings L1 to L5 are described accurately in the PR description as
owner-accepted without code change.

## 2. Frozen identity

| Item | Value |
|---|---|
| Branch | `assistant-edits` |
| HEAD | `5ffaad3834b74872cb39ef2babeae3eabad59170` |
| Tree | `58d34e57d34d8b81b41d13fe5f8a22dd101ee7a5` |
| Previous reviewed HEAD / tree | `79814364cff62d3222ee5a5b7035a1a4be07c52a` / `02b5dd09305c0b1bfece5c01c4f27310de1454b0` |
| Local `origin/main` ref | `582ad666031c8f139bfc5ad254bcd03244c3d640`. Not fetched, because this review is read-only. `git rev-list --left-right --count origin/main...HEAD` gives `0 8`, so HEAD is 0 commits behind. |
| PR #138 | OPEN. `headRefOid` is `5ffaad3834b7…`, the same as HEAD. |
| Working tree | Clean apart from the untracked earlier gate report and this report. |

## 3. Delta reviewed (`git diff 7981436 5ffaad3`)

The delta touches exactly 2 files, with 4 lines added and 2 removed:

- `apps/assistant/scripts/build_synthetic_eligibility.py:118-120`: a code comment only. The
  logic is unchanged and `NON_CASE_VIEWERS` is still `{"Support User"}`.
- `docs/decisions/DECISION_LOG.md:1657` (D-103 S4): two sentences are appended. They say
  Support only needs the case details logged with a feedback ticket, and that the backend does
  not itself limit the two reads to ticket cases (owner-accepted for the POC, pending sponsor
  confirmation).

No other path changed. Neither file is a qualification-basis file. The script is a builder
and is not in `model_qualification.BASIS_FILES`, so the basis hash is unaffected.

## 4. Checks run (on `5ffaad3`)

| Check | Result |
|---|---|
| `git diff --check 7981436 5ffaad3` | Clean |
| `.venv/bin/python apps/assistant/scripts/build_synthetic_eligibility.py --check` | "synthetic eligibility is current" (exit 0) |
| `.venv/bin/ruff check --no-cache` on the script | All checks passed |
| Whitespace of this untracked report | Checked separately (no trailing whitespace) |

All other evidence comes from the earlier gate on `7981436` and is reused unchanged. The
delta touches no executable logic, test, manifest or configuration, so none of that evidence
is invalidated.

## 5. Finding 6 and the new wording, checked against the code

- **D-103 S4 (DECISION_LOG.md:1657): accurate.**
  - `CASE_READ` is applied to exactly the two GETs (`apps/backend/app/services/authorization.py:124,237`).
  - `can_read` (`authorization.py:288-296`) admits any team-less holder of
    `KNOWLEDGE_CASE_READ` for any case. This matches "the backend does not itself limit these
    two reads to ticket cases".
  - "Ask the AI Assistant about this case" matches D-105 C10.
  - The chat records nothing for a caller without `CASE_ACCESS`
    (`apps/assistant/ai_assistant/main.py:557-560`).
- **The removed false claim** (L6, "never views a case in chat") is gone.
- **R1 (new, Low, comment accuracy).** `apps/assistant/scripts/build_synthetic_eligibility.py:120`
  says: "Leaving it out keeps those ticket chats off the external models (local model only)."
  That holds only on the D-095 eligibility path:
  - On the D-095 path, `main.py:778-787` refuses with `SYNTHETIC_VIEWER_NOT_APPROVED`,
    because "Support User" is absent from `synthetic_eligibility.json` `viewers`.
  - Outside D-095 mode, `main.py:789` uses `synthetic_boundary_check`. Its manifest
    `synthetic_boundary.json:19-27` **does** list "Support User", because
    `build_synthetic_boundary.py:282` adds every seeded user with no exclusion.
  - So with the D-094 remote test model active and D-095 mode off, a Support case chat on
    the verified synthetic Garden case can pass the boundary and reach the external model.
    The same applies to a D-104 restricted model that uses `check_messages`.
  - The boundary admits only verified synthetic prompts, so no real or sponsor data is
    exposed, and D-105 C10 does not claim local-only for the case chat. This is therefore a
    comment overstatement, not a security or contract defect.
  - Fix: scope the comment to D-095 eligibility (for example "keeps those ticket chats off
    the D-095 path"). Or, if the owner wants local-only Support case chats, record that
    decision and exclude Support from the boundary viewers as well. The second option is a
    behaviour change and needs its own review.

The S4 row itself makes no local-only claim, so the decision record is truthful.

## 6. Disposition review of the earlier findings

| # | Owner disposition (PR body) | Recheck |
|---|---|---|
| L1 | Accepted. Per-answer feedback is superseded and the app no longer calls the legacy endpoint. | Truthful. `sendAiAssistantFeedback` (`apps/frontend/src/aiAssistant.ts:558`) is still exported, but nothing in `apps/frontend/src` calls it. The backend endpoint is still reachable through the API by the record's own user, as the earlier gate said. Recorded accurately. |
| L2 | Accepted (no unauthorised action reachable). | Matches the earlier gate's analysis. The code is unchanged. |
| L3 | Accepted. | Described accurately. The code is unchanged. |
| L4 | Accepted. | Described accurately. The "redacted" wording is unchanged in the log. |
| L5 | Accepted, with the corrected scope noted in the PR. | The PR "Model qualification" section is now accurate: all three basis files are named, every non-baseline profile loses its qualification, and only the environment baseline model is unaffected. The D-105 log paragraph still says "The local model is unaffected", so the correction lives only in the PR description. That matches "Accepted (noted here)". |
| L6 | Fixed in `5ffaad3`. | The original false claim is removed and S4 is accurate. The replacement comment carries R1 (above). |

Whether to accept the Low findings is the owner's decision. They are recorded truthfully.

## 7. Unavailable checks (carried forward, not passes)

| Missing | Blocked claim |
|---|---|
| Physical Mongo | That Mongo-mode startup seeds `support-user` once, never overwrites it, and fails closed, against a real driver and server. |
| Full official E2E / lifecycle suite | That the other browser journeys show no regression under the official runner. |
| Hosted CI (GitHub billing block) | The remote CI status of PR #138. |

## 8. Required fix

1. **R1 (Low).** `apps/assistant/scripts/build_synthetic_eligibility.py:120`: limit the
   "off the external models (local model only)" claim to the D-095 eligibility path, or make
   an explicit owner decision to keep Support out of the boundary viewers too.

   A comment-only fix needs only a trivial bounded recheck. It changes neither manifest nor
   the qualification basis.

## 9. Git status

- Nothing was staged, committed or pushed, and no GitHub comment was posted.
- `.env` was not opened, and the dev servers on ports 8000, 5173 and 8100 were not touched.
- The PR body was saved as a scratch copy under
  `/private/tmp/claude-501/-Users-despog-Documents-GitHub-data-dividends-zero-touch-clm/db1288e6-4e49-41f6-bb6d-1a3eb84a5b1f/scratchpad/`.
