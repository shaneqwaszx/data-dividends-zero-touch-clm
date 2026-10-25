# Sim Lim ACRA ownership follow-through (D-080) - Stage 3 re-Quality Gate (recheck)

Independent Stage 3 recheck, 2026-10-24. I did not author, remediate or perform the first
gate on this content. This is a review only: nothing was fixed, staged, committed or pushed.

## 1. Executive Result

**PASS.**

All three round-1 required fixes are resolved, and the new text is true:
- **F1:** the cache rollback statement now matches what the code does. I proved it on a
  physical disposable Mongo against the `ceefe1e` reader.
- **F2:** the HTTP 200 statements are qualified. They match the sanitized receipts.
- **F3:** the live run's code identity is now explicit.

The recommended items N1 to N4 and N6 are implemented:
- The three changed or new test assertions (N1, N2, N3) each kill their target mutants.
  Five unit mutants and three physical mutants were run, on a scratch copy only.
- No test was weakened.
- Between the round-1 tree and the reviewed tree, only two test modules and five docs
  changed. No application, configuration or frontend file changed, so reusing the
  unchanged behavioural evidence is justified.
- Every invalidated check passed when I reran it.

Three informational wording notes remain (§3). None is a required fix.

Consequence: the reviewed content is eligible for Stage 4 publication. Commit, push and PR
still need explicit owner authorization (§8).

## Reviewed identity

- **Worktree:** `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024`.
- **Branch:** `feat/sim-lim-acra-ownership-followthrough-20261024`.
- **Revisions:** HEAD = BASE = local `origin/main` =
  `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`. I did not re-fetch.
- **Reviewed content:** the 38 unstaged paths in `git diff --name-only`.
- **Recomputed product tree: `5dfa8442cb9eb015b6c7cee26d577ad5c1fff342`.**
  - Method: a temporary index under the scratch `reqg` folder (`git read-tree HEAD`, then
    `git add -- $(git diff --name-only)`, then `git write-tree`).
  - It matches the expected identity, and I got the same result again after all checks.
- **Outside the tree:** the implementer report, the round-1 QG report and this report.
- **Round-1 tree:** `4944456a612e02b87a106e8bfe5d1408715840ee`. It differs from the reviewed
  tree in exactly 7 files (+112/-22):
  - tests: `test_official_shareholder_evidence.py` and `test_recursive_ownership_real_mongo.py`;
  - docs: `PROJECT_STATE.md`, `ACRA_MOCK_API_PROFILE.md`,
    `REGISTRY_CACHE_FRESHNESS_PROFILE.md`, `DECISION_LOG.md` and
    `ACRA_API_MARKETPLACE_MOCK_READINESS.md`.
  - No file under `apps/backend/app`, `apps/frontend`, `scripts` or any configuration
    changed.
- **Timestamps:** all 38 files were last written at 09:55:50-52, in a single batch. The
  content of the 31 untouched files is identical to the round-1 tree, as the tree diff
  proves; the timestamps alone carry no meaning.

## 2. Recheck Acceptance Checklist

| # | Item | Result | Direct evidence (re-QG) |
|---|---|---|---|
| F1 | Cache rollback statement | RESOLVED | `REGISTRY_CACHE_FRESHNESS_PROFILE.md:232-237`. Physical probe against the `ceefe1e` reader (§4) |
| F2 | "all HTTP 200" overstatement | RESOLVED | `DECISION_LOG.md:483-485, :494-495`; `ACRA_API_MARKETPLACE_MOCK_READINESS.md:127-129, :142-144`. Checked against sanitized `live.json`/`live2.json` (§3) |
| F3 | Live-run code identity | RESOLVED | `PROJECT_STATE.md:1014-1018`; readiness doc `:132` |
| N1 | Withdrawn-only class difference | DONE | `test_official_shareholder_evidence.py:432`. Kills MN1 (round-1 M2, which survived before) |
| N2 | Ordinary-acquisition test on a Marketplace COMPANY-form issuer | DONE | `:462`. Kills MN2a (round-1 M1) and MN2b. The removed local-lane half was vacuous (see §5) |
| N3 | Supported-version pin; positive physical v13 read | DONE | `:879` kills MN3 (round-1 M7). `test_recursive_ownership_real_mongo.py:345-363` kills MP1, MP2 and MP3 |
| N4 | Fail-closed decoder documented | DONE | `ACRA_MOCK_API_PROFILE.md:378-381`. Behaviour confirmed by probe (§4) |
| N5 | Informational | No change (accepted) | Affects the message only |
| N6 | Implementer report corrections | DONE | Report lines 40-43, 130-132, 162, 206-210, 229, 298 are now accurate |
| Scope | Only tests and docs changed since round 1 | CONFIRMED | Tree diff (above) |

## 3. Contract and Integration Findings

There are no defects, contract errors or overstatements that need a fix.

**F1, verified.** The new rollback bullet says four things, and each is true:
- **The startup decode.** At base, `MongoRegistryCacheStore.initialize()` decodes every
  document (`git show ceefe1e:apps/backend/app/persistence/mongo_registry_cache_store.py`,
  the `for raw in self._collection.find({})` loop). The candidate store is not in the diff,
  so it behaves the same. `MongoCaseStore.initialize()` also decodes every envelope, and
  base has no v14 branch, so a v14 envelope reaches `PersistenceSchemaUnsupportedError`,
  which `initialize()` re-raises.
- **The rejection set.** I ran a physical probe on the disposable loopback `mongo:7`
  container, with generated allowlisted DBs that were dropped afterwards (§4). The
  `ceefe1e` reader:
  - rejected the schema-4 `MARKETPLACE_SHAREHOLDERS_V2` entry;
  - rejected both D-080-written schema-2 entries that hold ownership parties (null
    `share_type`/`currency` keys);
  - decoded the D-080-written schema-2 entries without parties, both positive and
    negative.
  So the qualifier "whose ownership parties serialize ... as null" is exact.
- **The startup refusal.** In both probes, base `initialize()` raised
  `RegistrySnapshotRepositoryInvalidError` for the cache and
  `PersistenceSchemaUnsupportedError` for the v14 case collection.
- **The remedy.** "Until that collection is cleared" correctly limits the fix to the
  cache. The separate v14 case sentence makes no remedy claim.

The implementer report's rollback note (lines 206-210) now matches. The optional mirror in
`DECISION_LOG.md` was not added. That was optional, and its absence leaves no inaccurate
statement.

**F2, verified.** From the sanitized outputs (no credential-like content):
- run 1 recorded TOKEN 200 and four journey GETs at 200;
- run 1's `coCapitalDetails` receipt status was never printed;
- run 2 recorded TOKEN 200, shareholders 200, and capital 200 / 15 bytes / 0 entities.

That makes 8 of 9 receipts at HTTP 200, as the docs now say. The new phrase "The first read
returned no capital fields" (`READINESS.md:143-144`) is also supported:
- the scratch script sets `capital_field_paths` only after it receives a response;
- it recorded `[]`;
- no `capital_probe_failure` was recorded.

No "all HTTP 200" or "(×2) ... explicit empty" text remains in the 38 paths or the
implementer report.

**F3, verified.** `PROJECT_STATE.md:1014` now says "D-080 itself has offline tests only"
and that the Mock run "used the pre-D-080 (D-079) code".
- Run 1 is stated explicitly in the implementer report §4.
- For run 2, the identity is the implementer's assertion. It agrees with D-080 citing that
  run as its own evidence.

**Informational (no fix required):**
- I1: `ACRA_MOCK_API_PROFILE.md:380` uses "the diagnostic read" without defining it in that
  file. The implementer report calls it the "dormant/diagnostic decoder users". The claim
  itself holds: the decoder is shared, and a hostile value rejects the whole response.
- I2: `PROJECT_STATE.md:1015` calls two bounded runs "run" in the singular, and "observed
  their share classes" refers to the bounded probe reading source bodies, not to retention
  by the D-079 code. The readiness doc gives the exact split.
- I3: two added doc lines are longer than the surrounding wrap: `DECISION_LOG.md:495` (122
  characters) and `REGISTRY_CACHE_FRESHNESS_PROFILE.md:235` (97). Both files already have
  long lines (70 and 7). This is cosmetic, and every checker passes.

**Mock vs Live.** The remediation adds no Live, Sandbox or GoldTier claim. The
classification stays `MOCK_INTEROPERABILITY_OBSERVED`, and the provider matrix is unchanged.

**Unresolved sponsor authority (unchanged, not defects):**
- Q-004: share-class rights;
- Q-012: Marketplace capital and denominator semantics, the `coCapitalDetails` DTO, and
  corporate `shareholderId`;
- Q-019: person identity.

Together these keep any SIM LIM percentage blocked, correctly. P-A to P-E remain
unadopted proposals.

## 4. Tester and Adversarial Findings

**Environment:**
- Python 3.12.10 from the primary `.venv`.
- `PYTHONPATH` pinned to the worktree backend; `app.__file__` was verified in the worktree
  (and in the scratch copy for mutants).
- `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`.
- Ruff with `--no-cache`.

**Re-QG commands on tree `5dfa844…`:**

| Check | Result |
|---|---|
| `test_official_shareholder_evidence.py` (JUnit) | 34 tests, 34 passed, 0 skipped, 0 failed |
| Physical `test_recursive_ownership_real_mongo.py` on the disposable loopback `mongo:7` (`sim-lim-d080-mongo`), with generated allowlisted DBs and the URI never printed (JUnit) | 4 passed, 0 skipped |
| Backend `--collect-only` | 146 files, 3163 collected (3162 at round 1, +1 for the N1 test). 34 for the module above and 4 for the physical module |
| Ruff check, the two changed tests | PASS |
| Ruff check `apps/backend` | PASS |
| Ruff format `--check`, the two changed tests | 2 files already formatted |
| `git diff --check` | clean |
| `git diff --stat` vs `--ignore-cr-at-eol --stat` | identical: 38 files, +755/-85 |
| Untracked report hygiene (byte-level) | implementer report and round-1 QG report: LF only, 0 trailing-whitespace lines, 0 tabs, final newline present |
| `unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture` | 55 OK. Routine benchmark 30.047% (35.632 / 20.961 / 33.547) against the 30% floor |
| Contract lane (`tests/contract`) | 44 OK |
| Delivery assets | 4 OK |
| `test_check_secrets` | 8 OK |
| `check_project_state` | PASS |
| `check_architecture` | PASS |
| `check_secrets` (it scans tracked files and untracked, non-ignored files, including both reports) | PASS |
| `check_policy_authority` | PASS |
| `check_external_provider_readiness` | PASS |
| `check_tooling_config` | PASS |

**Mutation testing.** Each mutant ran on a scratch extraction (`git archive` of
`5dfa844…`), never in the worktree. Every file was restored byte-exact, and SHA-256 was
verified after each run.

| Mutant | Target | Result |
|---|---|---|
| MN1: the mixed-class check ignores `current_interest` | N1 | KILLED; within the module only by `test_only_current_rows_decide_whether_share_classes_are_mixed` |
| MN2a: ordinary normalization keeps the class and the bundle validator is disabled (round-1 M1) | N2 | KILLED; within the module only by `test_ordinary_acquisitions_never_carry_a_share_class` (`:485`) |
| MN2b: normalization keeps the class, validator intact | N2 | KILLED by the same test (`ValidationError` in the acquisition) |
| MN3: `_SUPPORTED_SCHEMA_VERSIONS` omits 13 (round-1 M7) | N3 | KILLED by the version pin (`:879`) |
| MP1: a v13 row with no class keys is rejected | physical N3 | KILLED (`PersistenceDataInvalidError` in the new block) |
| MP2: a legacy v13 read rewrites the stored document | physical N3 | KILLED (`== before`, `:363`) |
| MP3: the v13 upgrade drops `ownership` | physical N3 | KILLED (`:358`) |

**Probes (synthetic data only).**

*F1 rollback (physical).* Two runs. Each wrote with the candidate code (one in the
Marketplace hybrid lane, one in the local synthetic lane), started the `ceefe1e` stores
against the result, then dropped the DB. The results are in §3. Afterwards, no `clm_p*`
DB was left in the container and `clm_poc` was absent.

*N4 decoder.* A COMPANY-form Marketplace issuer acquisition through the subsidiary path:

| `shareType` value | Bundle | `OWNERSHIP_PARTIES` | Parties retained |
|---|---|---|---|
| `"Preference"` | PARTIAL | COMPLETE | 1, class dropped |
| exactly 64 characters | PARTIAL | COMPLETE | 1, class dropped |
| 65 characters | FAILED | FAILED | 0 (relationships `NOT_ATTEMPTED`) |
| a value containing NUL | FAILED | FAILED | 0 (relationships `NOT_ATTEMPTED`) |
| an integer | FAILED | FAILED | 0 (relationships `NOT_ATTEMPTED`) |

This confirms "safe failure, never partial evidence".

**Reuse of unchanged evidence, checked against identity.** Only tests and docs changed
since `4944456…`, and neither changed module is imported by another test module. Their
only other references are by name, in `scripts/run_physical_mongo_tests.py` and its test.
- **Chunked full backend at `4944456…`:** JUnit `chunk1-4.xml` totals 732 + 991 + 653 + 786
  = 3162 collected, 175 skipped, 0 failures, 0 errors, so 2987 passed. It stays valid for
  the 144 unchanged modules. The two changed modules were rerun above.
- **Physical runner `physical_r2.log`:** PASSED, 25 suites, 169/169, 0 skipped. It was
  written at 10:01:36, after the final content write at 09:55:52.
- **Browser `e2e.log`:** 115 configured selectors passed, exit 0. App, frontend and scripts
  are unchanged.
- **mypy `app`:** the app is unchanged.

**Not run by the re-QG:**
- The full single-process backend suite: the evidence above was reused and verified.
- The full physical runner and E2E: unaffected and reused.
- mypy: the app is unchanged.
- The GoldTier-examples lane: it needs an install.
- Hosted CI: the content is uncommitted.
- The live Mock run: it cannot be re-observed.

## 5. Code and Architecture Review

- **No application change.** The remediation is confined to two test modules and five
  docs. The owners, data flow, Decimal engine, 25% threshold, CAS and readiness are
  untouched.
- **Test quality.**
  - **N1** asserts the exact D-079 message when only a withdrawn row has a different class.
  - **N2** drives a Marketplace COMPANY-form issuer through
    `acquire_subsidiary_registry_evidence`, checks that the shareholder read happened
    (`calls[("SHAREHOLDERS", L2_UEN)] == 1`), and asserts that the bundle keeps
    `(10, None, None)`. It keeps the `pytest.raises(ValidationError)` half.
  - **The removed local-lane half was vacuous.** `garden_business.py:243` and `:408` build
    `AcraOwnershipPartyPayload` without a class, so it could never fail. Removing it is not
    a weakening.
  - **N3** pins `range(1, 15)`, consistent with the other mechanical schema pins.
  - **The physical block** uses `$unset` to reproduce the real D-079 shape (keys absent),
    then reads it and asserts no rewrite.
- **No scope creep.** No new endpoint, operation, mapping, rule or frontend change. No
  accepted technical debt is newly introduced.

## 6. Security Review

No security finding.
- The remediation delta adds no secret, URI, token, raw payload, email or new identifier.
  Only the already-tracked UENs `11111999A` and `111111111M` appear, plus `SYNTHETIC*`
  names.
- The implementer report's `.env` wording (lines 40-43) is now accurate.
- The N4 documentation correctly describes the fail-closed posture.

## 7. Required Fixes

None. I1-I3 are optional wording improvements and do not block publication.

## 8. Readiness

- **Publication readiness:** READY for Stage 4 on exactly tree `5dfa844…`. This needs:
  - explicit owner authorization to commit, push and open a PR;
  - unchanged reviewed content;
  - a clean-tree `python scripts/pre_pr_check.py`;
  - a fresh `origin/main` drift check.

  Any change to the reviewed paths needs a fresh independent recheck.
- **Next-phase readiness:** not applicable. No next phase is authorized or begun.
- **Live ACRA readiness:** not claimed. The evidence is `MOCK_INTEROPERABILITY_OBSERVED`
  only, and Q-004, Q-012 and Q-019 remain open.
- **Real GoldTier integration readiness:** unaffected and not claimed. SIM LIM keeps the case
  REVIEW_REQUIRED.

## 9. Git Status

- **Branch and revisions:** `feat/sim-lim-acra-ownership-followthrough-20261024`. HEAD =
  BASE = `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`.
- **Working tree:** 38 tracked files modified and unstaged. Staged: none. The real index
  was not touched; tree identity used only temporary index files under the scratch `reqg`
  folder.
- **Untracked:** the implementer report, the round-1 QG report and this report. This report
  is my only repository write.
- **Incidental ignored-file writes.** Two git-ignored runtime artefacts in the worktree were
  rewritten as a side effect of my checks:
  - 9 `__pycache__/*.pyc` files under `apps/backend/app/` were refreshed at 11:05. The
    rollback probe ran with `python -I`, which ignores `PYTHONDONTWRITEBYTECODE`.
  - The existing `apps/assistant/data/knowledge/*.sqlite3` files were rewritten at 11:11
    when backend test collection imported `test_ai_assistant_main_integration.py`.

  Neither touches tracked or reviewed content, and the tree identity is unchanged.
- **Scratch:** all other scratch material is under
  `C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane--claude-spares-spare-wwQzXZ\7b766e0f-c304-4fff-b2c4-b2dff544d6a7\scratchpad\reqg`.
- **What did not happen:**
  - no fix, stash, commit, push, PR, merge or next phase;
  - no `.env` opened and no ACRA or GoldTier host contacted;
  - no process I did not start was touched;
  - `clm_poc` was never connected to.
