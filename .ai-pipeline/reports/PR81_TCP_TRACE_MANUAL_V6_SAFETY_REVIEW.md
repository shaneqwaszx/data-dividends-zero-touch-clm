# PR81 V6 independent manual-procedure safety review

## Outcome and reviewed identity

**FAIL / BLOCKED for manual V6 capture preparation.** One proven profile-provenance defect remains: the V6 sanitizer writes the immutable V2 profile hash into sanitized.json while the actual V6 controller/profile/bundle bind V6. The SOP does not identify this discrepancy. No elevated execution or ordinary fixture is authorized by this report. PR81 remains NOT READY FOR HUMAN MERGE.

This fresh manual reviewer is separate from the implementer and helper-code reviewer. Review was read-only except this sole assigned report. The independently accepted code-gate report remains unchanged; its PASS does not waive this separately found manual/output-binding blocker. No helper, SOP, test, old report or acceptance condition was edited.

Worktree C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm; branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached origin/main and merge base e799d74063678bb0eccbea445d5ab3c8628dd2c0. No fetch or Git mutation. Existing23 tracked changes match the frozen status; staged set empty. Source25 identity ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490 and all1175 historical hashes independently match before and after review.

Read AGENTS.md, fyp-quality-gate, integration-security-review and relevant checklist, scoped CI_TOOLING dev_context and selected current workflow/architecture/state, V6 plan/handoff/code gate, exact SOP/issued/frozen manifests, actual helper/runner/sanitizer/profile/schema, safe V5 stop report and installed SDK. Review is preparation for local metadata capture, with no product-contract or external-provider change.

## Blocking finding: wrong profile identity in sanitized output

**High: exact capture profile provenance is false at the export boundary.** Source .ai-pipeline/reports/pr81-tcp-capture-v6/Sanitize-TcpTrace.ps1:148 computes profile_sha256 using ../PR81_TCP_TRACE_CAPTURE_PROFILE_V2.json. That literal reference produces the old V2 hash for any successful V6 export; this is established directly from the exporter, without reading ETL or executing export.

| Binding | Actual SHA256 |
|---|---|
| V6 capture profile; bundle.profile_sha256; armed/active/stopped markers | ce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f |
| V6 sanitized.json profile_sha256 expression, inherited literal V2 path | 74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1 |

The V2 mode is0x10000002, whereas V6 approves0x10400002. The helper/runner/controller correctly bind the V6 profile, but the eventual export would identify a different capture configuration. SOP section3 names V6; sections5 and review boundary require validated exact diagnostic/package provenance without disclosing this mismatched output. Treating sanitized.profile_sha256 as evidence of the actual V6 logging mode would be incorrect, and enforcing equality to V6 would reject that export. Neither outcome satisfies a truthful exact-bound manual handoff.

No reinterpretation of this field as a new sanitizer-contract identity is accepted. The profile hash is not silently replaced or waived. This does not demonstrate confidential body exposure or a product regression; it blocks exact capture-output provenance and readiness.

Smallest proposed correction, only with fresh owner authority for this sanitizer-binding path: change the one literal profile reference at sanitizer line148 to PR81_TCP_TRACE_CAPTURE_PROFILE_V6.json, preserving all event selection, schema, connection-lifetime and output constraints. Add focused positive/adverse provenance checks proving the V6 export header matches the approved V6 profile and rejecting a V2/stale profile identity. No raw ETL is necessary for those focused checks. Regenerate exact bundle/manifests, obtain fresh helper-code and manual reviews of changed bytes, then stop again before any capture. This report implements none of that work; the final authorized helper cycle is stopped for owner reassessment rather than broadened automatically.

## Other safety criteria verified

Microsoft documents STOP_ON_HYBRID_SHUTDOWN0x00400000, PERSIST0x00800000 and session-dependent default choice when neither is specified. The V5 returned-mode evidence is consistent with that documented default; no direct new measurement of Windows internal normalization is claimed. [Microsoft Logging Mode Constants](https://learn.microsoft.com/en-us/windows/win32/etw/logging-mode-constants).

Installed SDK10.0.19041.0 evntrace.h hash matches the frozen SDK receipt; lines401/439/447/448 confirm CIRCULAR2, shared buffers0x10000000, STOP0x00400000 and PERSIST0x00800000. V6 actual Native.Props and Native.Bounds use named immutable ApprovedLogFileMode0x10400002 with exact equality; controller comparison retains the exact guard. No extra-bit masking or PERSIST substitution is allowed.

Microsoft permits administrative users, Performance Log Users and specified service identities to control standard ETW sessions. This exact helper additionally requires Administrator for Arm/Watchdog; current ordinary token lacks that membership/elevation, and no account changes are proposed. Manual operator uses a separate PowerShell7 x64 administrator window on the same Windows host. Codex and runner remain ordinary. [Microsoft StartTraceW permissions](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-starttracew).

Current reviewer host is Windows10.0.26200.0, PowerShell Core7.6.5 x64, Administrator=false; LocalMachine RemoteSigned and higher scopes Undefined. Installed event schema/SDK and frozen runtime bindings support the proposed procedure. Actual future elevated access, raw ACL enforcement, returned native limits/filter, child operation and capture coverage remain unexecuted. The SOP fails closed on incompatible policy/runtime and never bypasses policy or automatically requests UAC/RunAs, edits groups, installs drivers or changes firewall/network/security settings.

The SOP binds issued manifest, code gate, bundle and all members before loading/executing helpers, and requires final manual gate/SOP raw hashes from the externally issued final manifest before manual action. There is no circular self-hash expectation. Fresh owner coordinated authorization is explicitly required before section2; all previous RunIds are prohibited, arming expiry/failure/incompleteness stops without retry, and active.json is required before fixture import. Original Selector/HTTP15s/cleanup10s/assertions/idempotence/no replay remain unchanged.

45s absolute capture assigned before hidden typed watchdog launch,300s arming/readiness5s/raw8MiB/buffers64KiB4..16/flush1 and allowlists are unchanged. Typed object/PID/creation binding and known Boolean liveness remain fail closed; unknown liveness cannot authorize start/enable/export. Finally and independent deadline child request stop only for the exact GUID/handle. Emergency commands repeat integrity checks, query the same descriptive session, reject foreign GUID and stop only the exact-owned session. Absence4201 is required. No global stop/enumeration/unrelated process kill/raw deletion is included. OS failure or simultaneous controller/watchdog loss is expressly not guaranteed cleanup.

## Data collected and excluded

Selected TCPIP metadata acquisition remains host-wide, not connection-only. Event schema20 IDs/35 versions/319 fields independently inspected:229UInt32,11UInt64,44Pointer,1Boolean and34Binary fields, all Binary fields typed SocketAddress. There are no arbitrary packet buffers, strings, HTTP bodies, credentials or document/provider payload fields; exclusion is schema-based, not packet truncation. ETL headers can contain local host/user/path metadata, so raw stays operator-local/protected and is never shared with Codex. Fresh fixed-drive/no-UNC/no-reparse directories and explicit operator/SYSTEM/Administrators ACL remain required.

The unchanged strict sanitizer excludes unrelated connections and raw addresses/pointers/keys/messages/binaries, requires one unique fresh tuple/PID/process-key/two complete TCB lifetimes, rejects unknown schemas/ambiguous reuse/missing coverage/loss/overwrite and bounds output1MiB/4096 events. Numeric diagnostics keep formatversion5 and integer/Boolean/null fields only, fresh bounded fixed files, no exception messages/stacks. Null/missing metadata is UNKNOWN. Send acceptance is not ACK; selected FIN-related events do not prove literal wire FIN. Historical V3 abort and underlying506-byte HTTP delivery cause remain UNKNOWN.

## Independently executed review evidence

| Check | Result |
|---|---|
| Exact manual two-path frozen manifest and content identity | PASS |
| Issued21-path bindings; code20-path bindings; bundle13 members | PASS |
| Source25 identity and historical1175 paths, before/after | PASS |
| Frozen branch/HEAD/cached-main/base/status/empty stage, before/after | PASS |
| All four SOP PowerShell blocks via Parser.ParseInput only | PASS: zero errors; none executed |
| Installed SDK and319 schema field types | PASS |
| Scoped canonical supported-pattern secret scan on SOP/issued manifest | PASS: zero findings; limited scanner coverage |
| Explicit SOP/issued-manifest whitespace | PASS |
| Sanitized profile provenance versus actual V6 bundle/profile | FAIL: stale V2 literal at sanitizer148 |

No SOP block, live Native Query/Start/Enable/Stop, emergency command, watchdog child, fixture, socket confirmation, ETL access or elevated execution occurred. The separate frozen code reviewer independently ran mode50/controller30/watchdog39 plus six Process probes/sanitizer19/scanner8 and safe Validate/runner--validate with PASS; those results are reviewed existing code evidence, not newly executed manual capture evidence. Full product/pre-PR/CI release acceptance is outside this assigned manual review.

## Boundary and exact report binding

**FAIL / BLOCKED.** No manual V6 capture readiness, no automatic retry or RunId reuse. Return the proven export-profile blocker to the owner. Product API/types, durable schema, connectors, business rules, mapping, product auth/security/architecture/provider classification and product runtime are unchanged. V6 helper mode correction and all historical evidence remain exact; only this new independent report was written. No commit/push/PR update/merge. PR81 remains NOT READY FOR HUMAN MERGE.

Review identity is SHA256 of sorted compact UTF-8 JSON below, no newline. Raw report hash is supplied externally.

Review identity: 55821087e96a3ff4a979120814d82a30cf8ef1c6a68518f11c124bb1d3a9097f

```json
{
  "branch": "feat/blocker-resolution-idp-ux-optimization",
  "bundle_sha256": "b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7",
  "cached_main": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "code_gate_sha256": "64e8e6759196a1c0c7f27cee5273fe13d81a49f0fa6c7ca09d7970c811cdf61b",
  "code_manifest_sha256": "8888ad82038cc147aa42eb345654947dd86dc03f44205e1b2f2fd7a45100acde",
  "fixture_executed": false,
  "head": "dd8c36c8a911f4b5f3b80e7441d049f1aa976599",
  "manual_manifest_content_identity": "70c07164a74f5009b130a7d6b00aaf203506647c39a1bff46d885318363ec8fc",
  "manual_manifest_sha256": "230f5fadf90a30a608b8b71b57ba7a9d0fb33bbef30f8e49ccfa39f4c5411a06",
  "merge_base": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "native_trace_control_executed": false,
  "parse_errors": 0,
  "parsed_powershell_blocks": 4,
  "preserved_count": 1175,
  "raw_etl_accessed": false,
  "readiness": "BLOCKED",
  "reviewed_paths": {
    ".ai-pipeline/reports/PR81_TCP_TRACE_MANUAL_PROCEDURE_V6.md": "239de2a9609a1411c8bf25cd0819e76ae00e7c8b5e5d01026f16236c38d686b0",
    ".ai-pipeline/reports/PR81_TCP_V6_ISSUED_BINDING_MANIFEST.json": "fdc75fc6bc8e528b8da40c08c8e2f8a5f88f10a36cf535a3d5e64f07d3fe8618"
  },
  "scope": "Independent V6 manual procedure safety preparation only; no capture execution",
  "source25_identity": "ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490",
  "verdict": "FAIL"
}
```
