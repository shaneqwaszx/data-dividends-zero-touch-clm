# D-095 AI Assistant — independent Quality Gate R4 (owner-review correction)

A fresh independent, read-only reviewer agent reviewed the owner-required correction
(document provenance by backend-computed SHA-256). The report is reproduced as delivered,
lightly reflowed; scratch paths are the reviewer's temporary files. Remediation and the
recheck follow (`D095_AI_ASSISTANT_QUALITY_GATE_R5.md`).

- Reviewed range: `1f18ce1..c2218620480cf6b7ff11c58127425d51f69a5cc2` (46 files).
- Verdict: **FAIL** (QG-R4-1, QG-R4-2 required).

## Verified

- **Digest origin:** `hashlib.sha256(content)` of the same uploaded bytes the media router
  extracts from; the replacement path is the same code; no route or service accepts a
  browser-supplied digest; the only record built without one (`policy_impact_fixtures`) is
  memory-only.
- **No content to OpenRouter when verification fails:** in D-095 mode `remote_gate` reads the
  digests with the RM's own session; `_verify_documents` refuses the whole case for an
  unreadable list, a list/document mismatch (id and version: gaps, extras, duplicates), a
  malformed or missing digest, an unapproved digest, or a media type/size mismatch. It runs
  before `answer_with_model`; the single-use ticket is unchanged; journey tests show no
  OpenRouter call for tampered or mixed uploads.
- **D-094 (flag off) unchanged:** digests are read only on the D-095 branch; the saved Garden
  documents are ineligible under D-095 (documented) and still pass D-094.
- **Route exposure is narrow:** `CASE_SCOPED` like the document list (86 routes, 46
  case-scoped); unknown case 404; not in any browser projection; documented in API_HANDOFF;
  unused by the frontend.
- **Schema-15 rejection** of a digest key (even null); unknown version 17 rejected.
- **Line endings:** `--numstat` equal with and without `--ignore-cr-at-eol`.
- **Budget:** B1–B6 is text only; B5 requires a next-Singapore-day guard before use.

## Findings

- **QG-R4-1 — BLOCKER, REQUIRED.** `DurableCaseSnapshotV15.to_current()` rebuilt the snapshot
  from `model_dump()`, which omits backend-only excluded fields (reconciliation `raw_value`,
  `source_record_id`, automation bindings and digests) that the current validators require.
  Every real schema-15 case with reconciliation evidence then failed to read
  (`PersistenceDataInvalidError`); reproduced with an old-tree encode of
  `rich_v7_snapshot("RECONCILIATION")` decoded at `c221862`. The tests passed because the
  schema-15 test used a bare case and a shallow copy. Fix: build from attributes; add a
  populated schema-15 test with a deep no-rewrite check and a re-encode comparison.
- **QG-R4-2 — MAJOR, REQUIRED.** Reconciliation, zero-touch and review fingerprints hash
  `model_dump`s of document records, which gained `"content_sha256": null`, so upgraded cases'
  evidence read as stale (not-current readiness for RECONCILIATION_RESOLVED documents,
  re-raised discrepancies, `ZERO_TOUCH_EXCEPTION_STALE`). Fails closed, but an undocumented
  behaviour change. Fix: keep the digest out of those dumps; test that fingerprints do not
  change.
- **QG-R4-3 — MINOR, OPTIONAL.** No direct cross-team 404 test for the digest route.
- **QG-R4-4 — ADVISORY, pre-existing, out of scope.** Schema 9–14 readers have the same
  `to_current` problem on `main` (reproduced on `1f18ce1` for V14). Suggested as a separate
  task.
- **Unproven here:** no MongoDB server is available (no Docker daemon; downloads blocked), so
  83 physical/real-Mongo tests were skipped; driver-level schema-16 write/read, CAS on an
  upgraded document and restart reconstruction are unproven. R4-1 was reproduced at the codec
  level (`MongoCaseStore._decode`), the path the physical store uses.

## Commands run

| Command | Result |
| --- | --- |
| Backend pytest, the 31 test files the delta touches | 860 passed, 83 skipped (Mongo) |
| Assistant pytest: eligibility, credentials, model management | 141 passed |
| `build_synthetic_eligibility.py --check` / `build_synthetic_boundary.py --check` | current / current |
| `scripts/check_secrets.py` / `scripts/check_project_state.py` | pass / PASS |
| `git diff --check 1f18ce1..c221862` | clean |
| `--numstat` with and without `--ignore-cr-at-eol` | identical |
| R4-1 and R4-2 reproductions | failure confirmed; patched `to_current` decodes, fingerprint stale |

`QG VERDICT: FAIL` — SHA reviewed `c2218620480cf6b7ff11c58127425d51f69a5cc2` (base `1f18ce1`).

## Remediation (author)

- R4-1: `DurableCaseSnapshotV15.to_current()` builds from attributes. New test
  `test_a_populated_schema_15_case_upgrades_without_losing_hidden_evidence` (populated
  `rich_v7_snapshot("RECONCILIATION")` at schema 15: deep no-rewrite, schema 16, digest-less
  documents, re-encode equals the original plus `schema_version` 16 and `content_sha256`
  null). The schema-15 no-rewrite test now compares a deep copy.
- R4-2: `content_sha256` is `exclude=True` (backend-only, like the other excluded evidence):
  the store still persists it (it writes every declared field) and the digests route reads the
  attribute, but no `model_dump` includes it, so all dump-based fingerprints and projections
  are unchanged. New test `test_the_digest_never_enters_a_dump_so_evidence_fingerprints_do_not_drift`.
- R4-3: new test `test_another_teams_case_digests_are_a_safe_404`.
- Full backend suite after remediation: 3,183 passed, 181 skipped, 1 failed — the pre-existing
  `test_s3_retained_recovery.py::test_verified_interrupted_shell_prefix_projects_finalization_and_resumes_only_next_operation`,
  which fails identically on unmodified `origin/main`.
