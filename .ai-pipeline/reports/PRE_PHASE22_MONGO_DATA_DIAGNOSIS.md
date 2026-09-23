# Pre-Phase 22 Mongo Data Diagnosis

## Result

**Classification A — data still exists; current memory mode merely hides it.**

The read-only probe on 2026-09-22 reached MongoDB and found the configured durable case
collection with 14 schema-v2 case envelopes. No deletion is evidenced. The current
application setting is `memory`, so the normal simple demo cannot display those Mongo
cases until it is deliberately run in the separately supported Mongo mode.

## Safe configuration and count evidence

Only repository settings metadata, database/collection labels, counts, and schema
version counts were emitted. The URI, host, credentials, documents, KYC data, and case
payloads were not printed or inspected.

| Item | Read-only result |
|---|---|
| Current persistence mode | `memory` |
| Mongo URI configured | yes (used internally for the connection; never printed) |
| Mongo reachable | yes, read-only ping succeeded |
| Configured database | `clm_poc` |
| Configured case collection | `clm_case_snapshots` |
| Configured database exists | yes |
| Configured case collection exists | yes |
| Configured case count | 14 |
| Safe case schema-version counts | schema v2: 14 |
| `clm_admin_teams` | exists, count 2 |
| `clm_admin_profiles` | exists, count 6 |
| `clm_admin_policies` | exists, count 1 |
| `clm_registry_snapshots` | absent, count 0; cache is optional and disabled by default |

The historical diagnostic namespace also exists: database `FYP`, collection `users`,
count 2. It contains no `clm_case_snapshots` collection. Git commit
`65c4452ecbd759547fac2c2329168235d4d73e33` introduced that old connectivity-only
`FYP.users` diagnostic before Phase 12 durable case persistence. Phase 12 commit
`bc51b78bbca0b208a7a17c607eac498dbe6b65af` introduced the stable `clm_poc` /
`clm_case_snapshots` defaults; all tracked history inspected retains those defaults.

## Deletion-owner review

- `scripts/stop_demo_windows.bat` and `scripts/reset_demo_windows.bat` own process
  lifecycle, not Mongo cleanup. The runbook explicitly says reset does not delete Mongo
  data and supplies no general durable-data purge command.
- Physical Mongo tests call `scripts/mongo_test_safety.py`. Its allowlist accepts only
  generated `clm_p12_*`, `clm_p13_*`, `clm_p14_*`, `clm_p145_*`, `clm_p16_*`,
  `clm_p17_*`, `clm_p18_*`, or `clm_p19_*` names with a 24-hex suffix. It rejects
  `clm_poc` before any drop operation.
- Application case deletion can delete one explicitly authorized case through the
  canonical service/repository boundary; nothing in the observed mode switch invokes
  it, and the retained count disproves collection-wide disappearance.
- Switching `CLM_PERSISTENCE_MODE` from `mongo` to `memory` changes repository
  composition only. It does not issue a Mongo write or delete.

## Probe boundary

The temporary probe performed only `ping`, database/collection listing,
`count_documents({})`, and a schema-version aggregation. It was removed immediately
after execution. No insert, update, delete, drop, migration, repair, cleanup, raw read,
or physical mutation test ran.

## Conclusion

Historical durable cases were not deleted: 14 remain in
`clm_poc.clm_case_snapshots`. Their apparent disappearance is explained by the normal
demo currently composing in-memory repositories. This task makes no configuration or
data change; choosing Mongo mode for a future demonstration remains a deliberate human
runtime action under the existing runbook.
