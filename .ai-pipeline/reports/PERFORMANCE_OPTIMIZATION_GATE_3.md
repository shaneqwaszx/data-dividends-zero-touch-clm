# Gate 3 - measured persistence read cost

Frozen candidate pending exact independent review. Lane B is physical local Mongo;
Lane A remains deterministic local. No real registry or target requests.

## Identity and scope

Base/origin main: `198341b059ebf500252ce93d72eb099d2585c60b`.
Current checkpoint: `8ad875e60883129221e06e588c1a650394283aba`; four product/test files are uncommitted.
Branch: `feat/performance-computational-throughput-optimization`.
Unchanged Gate1 harness SHA256: `2bd95660eccc445a886991c58ba97d5211b401443c96e7366e57d2cb50c87222`.
Current source and tests, full regression, microbenchmarks and complete control group
use the exact four-file hashes in the companion JSON. Raw receipt manifest is ignored
under `.runtime/performance-optimization/gate3/manifest.json`.

## Diagnosis and retained delta

Every Mongo read obtains a new driver envelope and performs a fresh strict decode.
The store retains no model cache. The adapters then deep-copied the same read sections.
Eleven exercised getters now transfer the fresh section; document lists still construct
their caller-owned list. Write candidates, returned writes, transactions and CAS copies
remain unchanged. The unmeasured verified-target search copy remains unchanged.

Product files: `apps/backend/app/persistence/repositories.py` and one ownership-contract
docstring in `mongo_case_store.py`. New ownership tests and two physical tests prove
read independence, nested caller mutation safety, restart isolation and no resurrection.

## Source-bound paired physical measurement

Both implementations use the same fresh physical store and accepted rich_v7 current
envelope. Old classes are compiled from immutable checkpoint8ad875e source; current
classes use the frozen source.20 alternating pairs,200 calls/batch,20 warmups per
implementation. No sampler or profiler in timing windows. Parent CPU excludes Mongo
and native child processes. Paired order reduces time-window drift; no statistical
significance or production confidence is claimed.

|Read|Old median ms|New median ms|Change|Old CPU ms|New CPU ms|Improved pairs|
|---|---:|---:|---:|---:|---:|---:|
|case_get|3.504112|3.103811|-11.42%|2.656250|2.304688|20/20|
|documents_list|3.327850|2.995855|-9.98%|2.500000|2.265625|20/20|

Separate original-before/current-after medians are3.492572->3.026211ms(case) and
3.297379->3.033974ms(documents). Those separate-window deltas are corroboration;
alternating source-bound pairs are the causal acceptance evidence. The case-read
median clears10%; document-list median is smaller and its98%+ recursive copy-call
elimination is material repeated-work evidence.
Single-read profile counts are950->12(case) and639->12(documents). CPU timings
in those single-call profiles quantize to zero and are not speed evidence.
Complete diagnostic deepcopy calls across10 profiles: 1977844->1724565.
Mongo onboarding alone:1,089,551->836,272 recursive deepcopy visits (23.25% fewer).
Counts use Yappi total recursive ncall, checked against harness JSON; its pstat
export stores ncall in tuple position0 and primitive calls in position1. Counts
include recursive container/scalar visits, not distinct objects or DB calls.

## Query, conversion and operation findings

Case reads still decode complete strict envelopes, including BSON/model conversion;
no request memoization, partial case validation, store cache or persistence bypass.
Full physical onboarding retains481 finds,1 insert,60 updates. Portfolio retains
3 finds and1 bounded aggregate. CAS cycles and checkpoint writes remain owned.
ID lookup uses IDHACK and examines1 key/1 document. Document/submission lookups
use their existing indexes, each1 key/1 document. The authorized portfolio plan
uses onboarding_team_lookup:100 ordinary cases plus the populated lookup fixture
yield101 examined authorized documents; bounded rows51 feed the50-row page.
The corruption-rejecting facet intentionally sees the authorized candidate set.
No measured index problem justifies changing queries, indexes or validation scope.

## Identical ten-workload remeasurement

20 measured samples per workload +2 separate warmups, same unchanged Gate1 harness.
All200 outcomes and DB/provider/target/HTTP/repository operation counts equal both
baseline and Gate2. Read-only setup reuse and mutating fresh runtime rules are unchanged.
Separate resource observation and Yappi profiles remain outside primary windows.

|Workload|Gate2 p50 ms|Gate3 p50 ms|p50 delta|Gate2 p95 ms|Gate3 p95 ms|
|---|---:|---:|---:|---:|---:|
|memory_onboarding|1154.183|1140.760|-1.16%|1202.822|1175.189|
|mongo_onboarding|3201.799|2870.821|-10.34%|3342.732|3075.768|
|blocker_correction_resume|104.788|97.804|-6.67%|129.881|195.848|
|mock_target_success|71.591|64.986|-9.23%|187.952|164.137|
|uncertain_policy_recovery|51.787|49.914|-3.62%|56.713|52.539|
|case_detail|13.437|12.869|-4.23%|14.997|15.213|
|portfolio_memory|43.826|38.663|-11.78%|60.231|39.990|
|portfolio_mongo|17.614|17.936|+1.83%|19.020|20.753|
|ownership_graph|0.367|0.333|-9.37%|0.462|0.468|
|native_document|482.190|471.334|-2.25%|497.022|482.245|

Unchanged Lane A code and native child runtime are host controls. Whole-run changes
are descriptive observations across time windows; they do not isolate copy cost.
Retention rests on the alternating physical hotspot and proven eliminated copy work.
No memory-path optimization or external/provider latency improvement is claimed.
The unchanged memory blocker p95 rose129.881->195.848ms in the full run. A single
predeclared20-sample repeat, without source edits, gave median89.392/p95135.747ms.
The original higher tail remains in the table and raw evidence; the repeat is
corroboration of variable tails, not replacement or a latency guarantee. Its p95
is5.866ms/4.52% above Gate2. Mongo-only copy changes cannot affect this memory path.

## Correctness and adverse verification

|Check|Actual result|
|---|---|
|Focused traversal/read ownership/phase12/strict legacy|176PASS|
|Full backend|2594PASS/133 opt-in SKIP/3 existing timestamp-fixture warnings|
|Full backend Ruff / strict mypy|PASS / PASS126 source files|
|Contracts / unchanged harness|44PASS /4PASS|
|Project state/architecture/tooling/policy/provider/secrets|6PASS|
|Canonical physical Mongo|19suites/127PASS/0FAIL/0ERROR/0SKIP|
|Independent legacy ownership probe|strict1..9/current10 disjoint reachable mutable objects; no raw mutation|
|Complete measurement|200PASS with exact outcome/operation equality|

Full-suite skips are127 physical and6 real OCR opt-ins. Physical tests ran separately
with zero skips; the6 OCR cases remain explicitly pending cumulative verification.
Initial new-test fixture mixed old policy catalogue0 and current intelligence1 and
failed strict validation. It was replaced by the accepted complete current flow;
no validator or assertion was weakened. All acceptance checks use the corrected bytes.
Generated allowlisted p12 databases are validated before use, cleanup verifies absence.

Schema10/strict1..9, create/update/CAS/conflicts/corruption/restart/delete/no-resurrection
and Decimal/target currentness/no-replay checks pass. Independent review is separate
and will determine acceptance; self-authored evidence cannot provide the verdict.

## Behavior flags and next action

API/type:same. Schema:same. Connector/configuration/business rule/mapping:same.
Auth/security/architecture/provider status:same. Functional runtime semantics:same;
Mongo adapter computational copy cost changes. Defensive writes and locks remain.
Search3/Shell1/Policy1/Amend1 ordered success and uncertain-policy recovery with
zero replay retain exact baseline counts. No .env/shared clm_poc/external load.

Next: exact independent Gate3 review, then authorized local checkpoint on PASS and
Gate4 dependency/shared-state map. This report provides no later-gate acceptance.
