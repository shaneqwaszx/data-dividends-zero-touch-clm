# ACRA Hybrid Five-Layer Onboarding (D-077) - Independent Re-Quality Gate (round 2)

I am the independent reviewer of the round-1 gate. I did not author or remediate any of
this content. This review was read-only, and its only write is this report. The round-1
report stays unchanged.

## 1. Executive Result

**PASS.** The round-1 blocking defect M1 is fixed and the two low documentation findings
are corrected. The remediation delta introduces no new defect.

The probe now derives `evidence_class` from recorded receipts. It emits the label only for
the `five-layer-hybrid` lane, so the other lanes keep main's output shape. All
behavioural evidence accepted in round 1 stays valid, because no backend app, persistence,
API, frontend source or E2E code changed.

## Reviewed identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\acra-hybrid-five-layer-20261023`.
- Branch `feat/acra-marketplace-hybrid-five-layer-ubo-20261023`.
- HEAD, BASE and `origin/main` are all `24c3de385ba5cda099a3dc3b1b266fdf93aa4738`.
- The candidate is uncommitted. Nothing is staged.
- Frozen tree: **`f30d7e218548b3b7c43364ce7be7cd32fa9d0441`**.
  - Computed with a temporary index over the modified and untracked paths, including the
    round-1 report and excluding this file.
  - Verified at the start and again before this report was written.
- Delta from the round-1 tree `2f53d78…`, checked with `git diff --stat`:
  - `scripts/phase24_acra_mock_discovery.py`
  - `apps/backend/tests/test_five_layer_probe_lane.py`
  - `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md`
  - the implementer report
  - the round-1 QG report (now in the tree, content as written)
- `apps/frontend/src` is still byte-identical to HEAD.

## 2. Remediation checklist

| Round-1 finding | Result | Evidence |
|---|---|---|
| **M1** (Medium): probe printed `MOCK_INTEROPERABILITY_OBSERVED` unconditionally | **RESOLVED** | See the M1 notes below the table. |
| **L1**: demo guide claimed a UI label "Official Mock entity fetched" | **RESOLVED** | The guide now says verified issuers are recorded through the API (`identity_basis = OFFICIAL_MOCK_ENTITY_PROFILE`, `official_entity_lookup = ENTITY_PROFILE_FETCHED`) and that the official name replaces the synthetic name. This is consistent with the unchanged UI and with the guide's API-only section. |
| **L2**: "Every issuer lookup reuses the official-namespace cache" | **RESOLVED** | Step 7 now distinguishes the cases. NOT_FOUND issuers reuse the negative cache with zero GETs within the 600 s TTL. An official COMPANY profile reuses its entity profile but re-reads the required shareholder operation, so it stays provider-backed. This matches `test_hybrid_five_layer_overlay.py:457-460`. |
| Test-depth debt and the sub-issuer legal-form observation | Unchanged; non-blocking | These were classified non-blocking in round 1. The root-with-official-quantity behaviour was already verified by the QG in round 1. |

M1 notes:

- `evidence_class(receipts)` (`scripts/phase24_acra_mock_discovery.py:197-214`) returns
  `MOCK_INTEROPERABILITY_OBSERVED` only when an official data-read receipt has HTTP 200.
  Otherwise it returns `AUTHENTICATION_FAILED` (401/403), then `TRANSPORT_FAILURE` (no
  HTTP response), then `NO_SUCCESSFUL_READ`.
- The label is emitted only for `five-layer-hybrid` (`:344-348`).
- The documentation at `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md:194-201` matches the
  code.
- QG reproductions are listed in section 3.

## 3. Tester and adversarial findings

Run by the QG on `f30d7e2`. `PYTHONPATH` was pinned to the worktree, and `app` and the
probe script were confirmed to load from the worktree. Caches were kept outside the repo.

| Check | Result |
|---|---|
| Ruff (`apps/backend scripts tests`) | PASS |
| `test_five_layer_probe_lane.py` | 4/4 PASS |
| Five-layer backend modules (probe lane, overlay, journey) | 34/34 PASS |
| `check_secrets.py` / `check_project_state.py` / `check_architecture.py` | PASS / PASS / PASS |
| `git diff --check`; trailing whitespace and final newline on the four changed text files | clean |

QG adversarial probes ran as a scratch test only, against the offline transport, with no
network calls:

| Case | Result |
|---|---|
| Token 401 | `AUTHENTICATION_FAILED`, 1 receipt |
| Token transport down | `TRANSPORT_FAILURE`, single OAuth receipt `transport: UNAVAILABLE` |
| Every read `ConnectError` | `TRANSPORT_FAILURE` (loop stops after the first) |
| Every read 403 | `AUTHENTICATION_FAILED` |
| Every read 500 | `NO_SUCCESSFUL_READ`, 9 receipts, within the 17-receipt bound |
| Lanes `discovery`, `unbound-shareholders`, `documented-basic` | no `evidence_class` key |

- Credentials and the offline token were absent from every output.
- The QG's round-1 reproductions (401 and transport failure) now give truthful
  non-success classes.

Observation, non-blocking and not a defect: an HTTP 200 whose body then fails strict
decoding still yields `MOCK_INTEROPERABILITY_OBSERVED`. In that case every sample shows
`UNAVAILABLE_OR_CONTRACT_REJECTED`. This matches the owner-defined meaning that the
assignment and the guide document ("live HTTPS access to the Marketplace Mock
environment"). A 200 can only come from the fixed host over verified TLS, and the
per-sample result shows the rejection. The owner may later choose to also require at
least one decoded sample.

Reused, still valid (unchanged code; identities verified in round 1):

- full backend run, 3120 tests / 0 failed;
- physical Mongo, 168/168, plus the QG rerun at 3/3;
- the QG's targeted regression, 964 passed;
- mypy;
- contract tests, 44;
- the CI unittest lanes;
- frontend typecheck, Vitest and build;
- browser: 115/115, plus the QG's own rerun of 4 selectors at 4/4.

The remediation touches only an owner-run, opt-in script, its test and documentation. No
behavioural rerun is invalidated.

## 4. Code, architecture and security

- The change is minimal and pure. It touches no runtime composition and no provider
  connector.
- The other lanes are restored to main's output shape, which removes the round-1 scope
  creep.
- No secrets, tokens or raw bodies appear in any output. Receipt and sample shapes are
  unchanged.
- No new findings.

## 5. Required Fixes

None.

## 6. Readiness

- Stage 3 independent gate: **PASS** for tree `f30d7e2…`.
- The candidate may proceed to Stage 4 publication only with explicit owner
  authorization. Publication must commit exactly this reviewed content and rerun
  `scripts/pre_pr_check.py` on the clean committed state. Any content change requires a
  fresh review.
- Live ACRA Marketplace Mock verification was not performed (NOT_RUN_CREDENTIALS), so
  live interoperability for this lane remains unproven.
- These later sponsor/provider dependencies remain open: the OPQ official name and
  address, Q-004, Q-012, Q-019 and Q-002.
- Real GoldTier integration is unaffected.

## 7. Git Status

- HEAD `24c3de3`; the candidate is unchanged by the QG; nothing is staged.
- This report is the QG's only new file. QG scratch outputs are kept under the session
  scratchpad `qg/` folder.
- The QG made no implementation fix, commit, push, PR, merge, reset, stash or branch
  change, and started no next phase.
