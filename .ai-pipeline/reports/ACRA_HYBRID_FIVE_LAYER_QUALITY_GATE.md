# ACRA Hybrid Five-Layer Onboarding (D-077) - Independent Stage 3 Quality Gate

Independent reviewer. I did not author or remediate this content. The review was
read-only. The only write to the worktree is this report.

## 1. Executive Result

**FAIL.** One bounded false-success defect blocks the gate. The backend design meets
acceptance substantially, and so do provider-truth separation in runtime code, the
narrow discovery gate, cache isolation, Garden compatibility, schema 12 persistence, the
onboarding PDF and frontend scope compliance. All of these were verified independently.

The defect: the owner-run probe tool now prints
`evidence_class: MOCK_INTEROPERABILITY_OBSERVED` on every run. It does so even when the
OAuth exchange is rejected, or the transport is unavailable, and zero Marketplace reads
succeed. That label is the evidence class the owner is told to rely on for the
authorized live receipt. Under the gate rules a false-success correction cannot be a
minor fix. Remediation is small and bounded (section 7). It needs a scoped re-QG.

## Reviewed identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\acra-hybrid-five-layer-20261023`,
  branch `feat/acra-marketplace-hybrid-five-layer-ubo-20261023`.
- `HEAD` = `BASE` = `origin/main` = `24c3de385ba5cda099a3dc3b1b266fdf93aa4738`.
- Candidate is uncommitted. The real index is untouched (0 staged).
- Frozen content tree: **`2f53d7857cc11e127051be98777cb892a697bf50`**.
  - Computed with a temporary index; 50 paths: 40 modified plus 10 new.
  - Rechecked at the end of the review (excluding this report): unchanged.
  - No EOL-only churn: `--shortstat` equals `--ignore-cr-at-eol`.
- `apps/frontend/src`: byte-identical to HEAD (empty diff, no untracked files). The only
  frontend path is `apps/frontend/e2e/five-layer-hybrid.e2e.ts`.
- Evidence trees exist in the object store and were diffed against `2f53d78`:
  - `1bf13a8` differs only in the implementer report.
  - `3b19e39` and `2340f21` differ only in reverted frontend/UI-only files, the demo
    doc, the e2e spec and the report.
  - `2340f21` additionally lacks the new physical test.
  - Backend app, persistence and scripts are identical across all of them, so the reused
    backend evidence is valid.

## 2. Phase Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| Official cache-first lookup for each L2-L5 issuer through the existing coordinator | PASS | Test shows 5 `ENTITY_PROFILE` GETs (L5 fetched once in the diamond) and 1 token. `_acquire` → `acquire_subsidiary_registry_evidence` (`ownership_discovery.py`). |
| NOT_FOUND → `LOCAL_SYNTHETIC_IDENTITY`. Failure, mismatch, other lane or official rows → unresolved, never overlay | PASS | `_attach_overlay` `ownership_discovery.py:513-605`. Tests cover 500/429/401/timeout, mismatch, official rows, corrupt cache and token 401. |
| LOCAL links never carry ACRA/MOCK provenance; official identity only from a same-UEN official profile | PASS | `overlay_component` always uses `LOCAL_SYNTHETIC_RELATIONSHIP`/`LOCAL`. The official branch checks UEN, environment and official source link. The LOCAL exemption in `_validate_source` applies only when `local_overlay=True`. |
| Synthetic topology never ANALYZED/READY or GoldTier-sent; `SYNTHETIC_OWNERSHIP_EVIDENCE` always raised | PASS | `ownership_analysis.py:1182-1202`. Audit validator forbids `COMPLETE` certainty. Candidate validator forbids the synthetic field on non-review classifications. QG probes: re-analysis and all-official-identity variants stay REVIEW_REQUIRED. |
| `synthetic_basis_threshold_result` labelled and sound | PASS | MET is a lower bound. NOT_MET needs no `INCOMPLETE_LEGAL_ENTITY`, or `total + sound bound < threshold`. Blocking issues give INDETERMINATE. Arithmetic stays in the single Decimal engine (calculator untouched). |
| Narrow gate: SINGLE_SOURCE plus hybrid only; legacy flattened supplement excluded; no UEN conditionals outside the catalogue | PASS | `_DISCOVERY_SOURCE_CLASSIFICATIONS` (`ownership_analysis.py:256`). The legacy-lane test asserts `discovery is None`. No new UEN literals in services, calculator or router. |
| Cache isolation: official namespace only; negative hit counted as zero calls; partial prefix never complete | PASS | `ACRA_API_MARKETPLACE_MOCK_V1` keys present and `MOCK_ACRA_SYNTHETIC_V2` absent (test). Cached entity prefix stays provider-backed (test). Negative-hit refinement judged safe (see below). |
| Garden: default keeps ABCD123 51.13636375; hybrid = direct 62.5/37.5 plus official SIM LIM lookup, no 900/100/100 | PASS | Two tests. Default lane: `111111111M` GETs = 0. Hybrid: SIM LIM `NOT_FOUND`, branch unresolved, no ABCD123/TAN WEI LING/EFGH2345 parties. |
| Persistence schema 12; v1-v11 readers reject hybrid values; strict decode; physical Mongo | PASS | `reject_hybrid_overlay_legacy_fields`, exact `DurableCaseSnapshotV11`, central guard in `mongo_case_store.py:604`. QG reran the physical suite (3/3, includes restart plus a stored schema-11 rejection). Databases cleaned. |
| Onboarding PDF valid, deterministic, allowlisted, no ownership values/PII/tokens, address absent | PASS | QG: `render()` equals the file; SHA-256 `a2d9b198…5551`, 1,387 bytes. Delivery-asset allowlist test OK. Journey test confirms extraction, REGISTRY_ONLY address and `MATCHED`. |
| Frontend untouched; API additive | PASS | `src` diff empty. The API adds one literal value and optional fields only. |
| Honest probe: NOT_RUN_CREDENTIALS; no fabricated evidence | **FAIL** | The report and docs truthfully state NOT_RUN_CREDENTIALS. The probe tool itself mislabels failed runs (finding M1). |
| Browser verification through the existing UI | PASS | QG reran 4 selectors on the frozen content: 4/4 PASS. |

## 3. Contract and Integration Findings

- **M1 - Medium - bug, false-success label.**
  - Location: `scripts/phase24_acra_mock_discovery.py:323-326`.
  - What happens: `evidence_class: "MOCK_INTEROPERABILITY_OBSERVED"` is emitted
    unconditionally, for every lane. Before this candidate the script printed no such
    label.
  - QG reproduction (scratch test, offline transport):
    - Token 401: 0 data reads, label still emitted.
    - `httpx.ConnectError` (receipt `transport: UNAVAILABLE`): label still emitted.
  - Why this is wrong:
    - The contract defines this class as requiring "sanitized success evidence"
      (`docs/contracts/EXTERNAL_PROVIDER_ACTIVATION_CONTRACT.md:22-24`).
    - The assignment requires distinct `TRANSPORT_FAILURE` / `NOT_RUN_CREDENTIALS` /
      `NOT_FOUND` outcomes.
    - `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md:189` tells the owner that this label
      means live HTTPS access occurred.
  - `apps/backend/tests/test_five_layer_probe_lane.py:55` asserts the label on an
    offline monkeypatched run, which cements the mislabel.
- No direct ACRA-to-GoldTier mapping and no new provider operation. The connector is
  unchanged.
- The offline fixture is labelled `AUTOMATED_OFFLINE_SIMULATION`. Its browser runs carry
  the existing `API_MARKETPLACE_PROTOCOL_TEST` banner.
- Catalogue traceability: the cited page of all eight UENs was re-checked against the
  implementer's in-memory extract (p.1-7). No source PDF is tracked.
- D-077, the ADR-013 amendment and the contract section accurately describe the code.

Later sponsor/provider dependencies (not current blockers):

- Live Marketplace probe not run (credential access was denied to the implementer).
- OPQ official name and registered address are unconfirmed. The live lane may stop at
  `CANONICAL_DATA_INCOMPLETE`; this is documented.
- Open questions Q-004, Q-012, Q-019 and Q-002.

## 4. Tester and Adversarial Findings

Run by the QG on the frozen content (pinned worktree `PYTHONPATH`, `app.__file__`
verified in the worktree; caches written outside the repo):

| Check | Result |
|---|---|
| New tests (overlay, journey, probe lane) | 31/31 PASS |
| Targeted regression: 22 files (marketplace auth/connector, Garden ×3, ownership analysis/discovery, registry acquisition/cache, phase24 ×3, recursive discovery, slice B, persistence ×4, manual evidence, classification conflict, zero-touch, continuation) | 964 passed, 0 failed/skipped |
| Physical Mongo `test_recursive_ownership_real_mongo.py` (task container 127.0.0.1:27219, generated `p16` databases) | 3/3 PASS. Afterwards only `admin`/`config`/`local` remain. |
| Ruff (`apps/backend scripts tests`) | PASS |
| mypy (129 files) | PASS |
| Contract unittest (CI invocation) | 44 OK |
| `test_run_e2e`, `check_secrets`, policy authority and pre-PR unittests | 157 OK |
| Delivery-asset allowlist | 4 OK |
| `check_secrets.py`, `check_project_state.py`, `check_architecture.py` | PASS |
| `git diff --check`; whitespace and final newline on every untracked text file | clean |
| PDF generator determinism | identical bytes |
| E2E selectors `five-layer-hybrid:78`, `slice-b-registry-demo:94/:132`, `ownership-document-streamline:235` | 4/4 PASS |

QG adversarial probes (scratch only):

- Probe label on 401 and on transport failure: confirms M1.
- Root with official shareholder rows: overlay kept outside the graph (2 supplemental
  links, 0 LOCAL graph edges), REVIEW_REQUIRED, `SYNTHETIC_OWNERSHIP_EVIDENCE` raised.
- All five issuers officially identified: `official_identity_complete=True`,
  `quantitative_evidence_complete=False`, `UNCERTAIN`, still REVIEW_REQUIRED, and
  official names replace the synthetic labels.
- Re-analysis keeps the hybrid review.

Reused evidence (identity verified by tree diff):

- Full backend on `2340f21`: JUnit 3120 tests, 0 failures/errors, 173 skipped (physical).
- Physical runner on `3b19e39`: 25 suites, 168/168.
- Full browser suite: 115/115 PASS.
  - Note: `run_e2e` binds only the HEAD tree plus a dirty flag, not the candidate tree.
    Assigning this run to `1bf13a8` therefore rests on the implementer's sequencing.
  - The QG's targeted rerun on the frozen content compensates.
- Frontend typecheck/Vitest (1050)/build: frontend `src` equals HEAD.

Not executed: the Windows demo lifecycle (missing worktree `.venv`, as reported). It has
no dependency on this delta.

Negative-cache refinement (PR #104 semantics): **safe.** It changes only the
`provider_backed`/`cache_hits` counters and the optional business budget, and no provider
call occurs. The discovery outcome stays `NOT_FOUND` (unresolved) and can never become a
resolved `CACHE_HIT`. It is recorded in D-077 and ADR-013.

## 5. Code and Architecture Review

- No new service, repository, router or calculator. The catalogue is a connector-level
  fixture boundary. `_merge` was extracted and is shared with the official path. Root
  eligibility is a strict generic clone of the accepted Garden predicate. Overlays are
  exclusive with the legacy supplement (config and constructor guards).
- **L1 - Low - doc bug.**
  - `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md:175` says issuers "show *Official Mock
    entity fetched*".
  - No such UI text exists after the owner scope correction. The lookup label is
    API-only, as the same document states at :135-145.
- **L2 - Low - doc accuracy.**
  - `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md:129`: "Every issuer lookup reuses the
    official-namespace cache".
  - That holds for NOT_FOUND issuers. For an official COMPANY profile the required
    (empty) shareholder operation is re-read and the lookup is provider-backed (proven
    by `test_hybrid_five_layer_overlay.py:457-460`). The statement should be qualified.
- **Debt - Low - test depth (non-blocking).** Behaviour exists, and the root case was
  QG-verified, but there is no dedicated test for:
  - the other-lane / local-seed bundle reason `OVERLAY_REQUIRES_OFFICIAL_LOOKUP`
    (`ownership_discovery.py:546`);
  - the root-with-official-quantity branch (`ownership_analysis.py:1670`);
  - the negative-hit counter change on the non-hybrid local Mock lane;
  - the hybrid hard lookup limit and business budget.
- **Observation.** A sub-issuer whose official legal form is OTHER or a partnership still
  receives a declared share overlay. Only `official_legal_form` records it. This is
  contained because every hybrid analysis is review-required.

## 6. Security Review

No findings:

- No secrets, tokens, raw payloads or PII are added. `check_secrets` passed and
  `.env.example` adds a non-secret setting only.
- Offline tokens exist in memory only and are excluded from metadata.
- Probe output is limited to field names and counts.
- Reason codes are safe enums.
- Browser projection adds enum fields only.
- No TLS, auth or CSRF change.
- Persistence stays strict, with fail-closed legacy rejection.
- Physical tests used generated allowlisted databases only; `clm_poc` was never touched.

## 7. Required Fixes

1. **M1 (required).** In `scripts/phase24_acra_mock_discovery.py`, derive `evidence_class`
   from the receipts:
   - emit `MOCK_INTEROPERABILITY_OBSERVED` only when at least one 2xx official data read
     succeeded;
   - otherwise emit a truthful non-success class, such as `TRANSPORT_FAILURE` or an
     auth-rejected / not-observed class.

   Update `test_five_layer_probe_lane.py` so it does not certify the success label for
   offline input without stating that it is offline. Add token-401 and
   transport-failure tests. Align `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md:189`.
2. **L1 and L2 (minor, same pass).** Correct the two demo-guide statements.

Re-QG scope:

- Review: the changed files only.
- Rerun: Ruff, the probe-lane test, `check_secrets`, and whitespace checks.
- All other evidence above remains valid unless backend app code changes.

## 8. Readiness

- **Not ready** for Stage 4 publication until M1 is remediated and a fresh independent
  re-QG passes.
- Live ACRA verification: not performed (NOT_RUN_CREDENTIALS). Marketplace Mock
  interoperability for this lane is unproven.
- Real GoldTier integration: unaffected. No send occurs, and review blocks progression.
- This readiness statement authorizes no further phase.

## 9. Git Status

- Branch `feat/acra-marketplace-hybrid-five-layer-ubo-20261023`, HEAD `24c3de3`.
- 40 tracked files modified and 10 untracked, unchanged by the QG. This report is the
  QG's only new file. Nothing is staged.
- E2E runs wrote only to the git-ignored `tmp/browser-evidence/`. All other QG outputs
  are under the session scratchpad `qg/`.
- No implementation fix, commit, push, PR, merge, reset, stash or branch change was made,
  and no next phase was started.
