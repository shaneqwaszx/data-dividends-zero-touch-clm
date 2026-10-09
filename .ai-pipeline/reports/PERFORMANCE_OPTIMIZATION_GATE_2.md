# Gate 2 computational optimization evidence

Status: implementer evidence complete; independent Gate 2 verdict pending.
Claim class: DEVELOPMENT_MEASUREMENT / LOCAL_MEASURED only.

## Identity and smallest change

BASE and fetched origin/main:198341b059ebf500252ce93d72eb099d2585c60b.
Current checkpoint HEAD:c779cf3a2b68ad5acf626b05a313e70067af1228; branch
feat/performance-computational-throughput-optimization; merge-base is BASE, ahead2/behind0.
Worktree:C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm.

The sole product delta is strict nested-field traversal in the existing Mongo codec.
Product raw SHA256:cf6e784c7bd6596a7aff713eec41b34dddfdb3fb64714ff51a2afa71265e5b9e.
New test raw SHA256:602ea7ddbcacff6995edef2c94f92a7dc31d0aa67f49bad27a0de71b1ca9a3ee.
Unchanged serial harness SHA256:2bd95660eccc445a886991c58ba97d5211b401443c96e7366e57d2cb50c87222.
The source tree/diff identity actually measured is in the Gate2 JSON; the untracked
test is additionally bound by the hash here and the independent manifest.

The accepted baseline profile ranked deepcopy first and strict nested traversal next.
Traversal had642,078 total calls in one profiled Mongo onboarding. This includes
containers and a large scalar-leaf subset. Scalar calls performed three isinstance
checks and returned without inspecting or modifying their inputs. The candidate
recurses only into BaseModel/list/tuple/dict values; scalar validation remains in the
existing preceding Pydantic owner. Model key views avoid rebuilding the allowed set
and intersection. Dict enum-key normalization, raw model/list/dict shape, list length,
all unknown-key checks and recursive container inspection remain.

No cache, schema/model/default, migration, source precedence, new owner or dependency
was introduced. Create/update/CAS/identity/delete/recovery paths remain untouched.
Ten inserted/six removed product lines; unrelated original source bytes are preserved.

## Comparable whole-workload repeat

Both runs use all10 accepted workloads,20 primary repetitions each,2 excluded warmups,
the same versions/settings/fixtures/container limits and the exact Gate1 harness.
Setup/login/teardown, resource sampling and Yappi are outside the primary timing window.
All200 outcomes and DB/provider/target/request-count signatures equal the baseline.
Gate2 raw files are preserved under .runtime/performance-optimization/gate2; their
manifest is in that directory. Later smoke/final runs cannot overwrite this evidence.

|Workload|n|Baseline p50 ms|Gate2 p50 ms|Observed p50 delta|Baseline p95 ms|Gate2 p95 ms|Baseline parent CPU p50 ms|Gate2 parent CPU p50 ms|Correctness|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| memory_onboarding |20| 1216.980 | 1154.183 | -5.2% | 1293.223 | 1202.822 | 218.750 | 187.500 | PASS |
| mongo_onboarding |20| 3595.463 | 3201.799 | -10.9% | 3958.299 | 3342.732 | 1992.188 | 1734.375 | PASS |
| blocker_correction_resume |20| 112.982 | 104.788 | -7.3% | 211.655 | 129.881 | 109.375 | 109.375 | PASS |
| mock_target_success |20| 78.241 | 71.591 | -8.5% | 204.186 | 187.952 | 78.125 | 78.125 | PASS |
| uncertain_policy_recovery |20| 58.590 | 51.787 | -11.6% | 81.460 | 56.713 | 62.500 | 46.875 | PASS |
| case_detail |20| 17.863 | 13.437 | -24.8% | 19.854 | 14.997 | 15.625 | 15.625 | PASS |
| portfolio_memory |20| 47.551 | 43.826 | -7.8% | 55.624 | 60.231 | 46.875 | 46.875 | PASS |
| portfolio_mongo |20| 18.712 | 17.614 | -5.9% | 21.366 | 19.020 | 0.000 | 0.000 | PASS |
| ownership_graph |20| 0.434 | 0.367 | -15.5% | 0.785 | 0.462 | 0.000 | 0.000 | PASS |
| native_document |20| 508.814 | 482.190 | -5.2% | 537.136 | 497.022 | 0.000 | 0.000 | PASS |

These are observed differences between time windows. The Mongo median decreased
10.9% (393.664ms),p95 decreased15.6%,parent CPU median decreased12.9%.
Unchanged memory onboarding also decreased5.2% and several other unmodified controls
improved. Environment/noise contributes: the entire end-to-end difference is not
attributed to the codec change. Memory portfolio p95 rose8.3% (4.607ms),while its
median fell7.8%; its unchanged code and small tail sample do not establish a material
candidate regression. No p99, production/SLA or external-provider latency claim.

Short process CPU samples quantize to0 or15.625ms; zero is not zero computation.
RSS/host CPU remain separate one-run sampled observations including setup, with child
CPU/Mongo-server CPU unavailable. JSON retains them without a causal memory-saving
claim. Fixture limits and the separate owner-manual Lane C remain as in the baseline.

## Paired hotspot evidence

To separate helper improvement from shifted host conditions, a second clean experiment
compares immutable old helper AST from c779cf3 with the frozen current helper in the
same process on the same populated supported reconciliation snapshot.20 alternating
before/after pairs;1000calls per batch;200 excluded warmups per function; no sampling or
profiler; source and method identity outside timing. It neither switches nor edits source.

|Metric per helper call|Before|After|Delta|
|---|---:|---:|---:|
|Elapsed median ms|0.4296468|0.36186285|-15.8%|
|Elapsed p95 ms|0.4628455|0.4037409|-12.8%|
|Parent CPU median ms|0.421875|0.359375|-14.8%|
|Elapsed batch standard deviation ms|0.0202892|0.0194913|small compared with median separation|

Both inputs remain equal to their originals. Method SHA256:d863f6910eea18049a436585d98090d942e0c38b36f84f18eeec5537d3e41c30.
Immutable old source SHA256:a8959db4874078cdcd8c1d6aaf972c3e3196d738744e2b1be3ec89db835bcf4f.
Current raw source SHA256:cf6e784c7bd6596a7aff713eec41b34dddfdb3fb64714ff51a2afa71265e5b9e.
Current normalized source SHA256:e2b5026dc2ba52520e7a4e413feac4256d8c301e3af04b7a197cf1be7cabe661.
Script/raw/summary reside in the stable Gate2 directory. Independent review inspected
the method and differentially exercised the old/current helpers.

The profiled full Mongo workload now calls this helper108,878 times:533,200 fewer
calls (83.0%). Profiling timings include overhead and are diagnostic, not wall fractions.
The paired>=10% hotspot result plus eliminated no-op work supports retention.

The earlier separate-run microbenchmark (0.4944678->0.40136555ms median) is preliminary.
Its before execution preceded product edits at c779cf3; its after execution used the
initial LF-normalized candidate text, before unchanged CRLF bytes were restored.
It lacks imported-source hashes in its own output and does not alone prove provenance.
The paired result with exact source identities is the acceptance evidence.

## Correctness, affected regression and adverse paths

|Check|Result|Execution identity/limits|
|---|---|---|
|Focused traversal + legacy compatibility|102PASS|current product/current test after style correction|
|Full backend pytest|2580PASS/131 opt-in SKIP/3 warnings|same frozen product; pre-style test16bfbb60625454188aed1b89ba1bdb1859d6a91169bd78fa6c9e9e9842528b8b|
|Full backend configured Ruff|PASS|canonical apps/backend cwd; current test|
|Strict mypy|PASS126 source files|current product|
|Contract unittest|44PASS|current product|
|Performance harness unittest|4PASS|unchanged harness|
|Physical Mongo canonical19 suites|125PASS/0FAIL/0SKIP|generated allowlisted task databases; cleanup asserted|
|Project state/architecture/tooling/policy/provider/secrets|6PASS|current worktree|
|Independent differential probe|146PASS|old/current scalar/container/model/enum/unknown/input-immutability comparisons|
|Complete comparable measurement|200PASS|all10 workload outcomes/counts equal baseline|

The full suite's131 opt-ins comprise125 physical Mongo and6 real OCR cases.
All physical tests ran separately with zero skips. Tesseract exists at the known local
installation but is absent from PATH; the6 real OCR acceptance cases are explicitly
unexecuted here and will run in cumulative verification. No OCR measurement is claimed.
Three full-suite warnings arise from existing synthetic invalid-timestamp serialization
fixtures. Logs and direct exit receipts are current ignored task evidence, not CI claims.

Ruff initially rejected only the new test import grouping. Root invocation inferred a
different first-party import scope; canonical backend CI cwd fixed the grouping.
No test/assertion/product fix followed full pytest. Fresh102 focused tests and full
Ruff cover the current test bytes; the distinction from full-suite tested bytes is explicit.
The independent reviewer freshly inspects the current style-only delta.

Physical evidence covers strict schema10/legacy1..9, corruption rejection, CAS/conflicts,
insert/update distinction, restart/no replay, deletion/no resurrection and both repository
lanes. This is not a physical sponsor/provider interoperability claim.

## Contracts, security and behavior flags

API/type:same. Durable schema:schema10 with unchanged strict1..9 readers.
Connector:same. Runtime owner configuration:same. Business rule/mapping:same.
Auth/security decisions,case scope,reauthorization/locks:same. Architecture owners:same.
Provider classifications:same. Functional product runtime semantics:same; Mongo codec
computational traversal cost changes. Development tests/reports change.

Normal success still uses registry4 and target Search3/Shell1/Policy1/Amend1.
Physical onboarding still finds481/inserts1/updates60 (542commands); portfolio still
finds3/aggregates1. Recovery still has one Shell and one uncertain Policy attempt,
zero recovery mutation calls and only remaining readback. No ordered target operation
was parallelized and no uncertain write was replayed. No private .env/shared clm_poc,
real ACRA/GoldTier request,protected payload or owner configuration was accessed.

## Handoff

Candidate is uncommitted pending exact independent Gate2 PASS. Required next action:
independent review of this frozen delta/evidence; only then authorized local checkpoint
and Gate3. Gate2 supplies no later-gate acceptance or publication readiness.
