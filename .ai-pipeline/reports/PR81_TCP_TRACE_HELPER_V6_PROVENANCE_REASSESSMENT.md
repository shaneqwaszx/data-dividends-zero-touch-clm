# PR81 V6 independent provenance reassessment

## Current verdict

**FAIL for complete V6 candidate acceptance; BLOCKED for manual V6 capture.** A proven profile-provenance defect in the unchanged sanitizer export envelope prevents the emitted metadata from truthfully binding to the approved V6 capture configuration. No capture/export has been executed, so this is a statically demonstrated would-export mismatch, not an observed bad trace or confidential-content disclosure.

The earlier independent helper-code PASS remains byte-preserved historical evidence for its recorded tests and mode checks. I missed the sanitizer export-envelope dependency when relying on V5 byte identity and selection regressions. That earlier verdict is insufficient for complete V6 preparation acceptance; its no-required-correction conclusion must not authorize capture in light of this proven finding. This supplemental current verdict governs the newly assessed provenance criterion without rewriting prior evidence.

## Proven owner, path and consequence

Affected authoritative field: pr81-tcp-capture-v6/Sanitize-TcpTrace.ps1 line148, actual export payload.profile_sha256. Its Get-FileHash expression resolves the literal ../PR81_TCP_TRACE_CAPTURE_PROFILE_V2.json. The frozen file hashes below independently reproduce the expected/actual mismatch without running the sanitizer export path, mocks, Get-WinEvent or ETL reading.

| Identity | Required/derived SHA256 |
|---|---|
| Approved V6 bundle/profile identity | ce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f |
| Export line148 literal V2 reference | 74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1 |

V6 profile requests exact LogFileMode0x10400002. V2 requests0x10000002. These profiles describe different configured capture semantics. The same field name profile_sha256 cannot be silently reinterpreted as an unrelated or secondary baseline identity to accept both values.

V6 bundle.profile_sha256 is the V6 hash. Controller ownership/armed/active/stopped records use that bundle value at lines83/84/129/147, and the ordinary runner compares armed/active profile_sha256 to the bundle at lines59/75. Administrator SOP line85 names V6 and its exact hash; its sharing boundary requires validated sanitized metadata. The actual sanitized envelope therefore contradicts the configuration identity expected by those bindings.

The V6 bundle explicitly binds the V6 profile member and has no V2 profile member. Consequently the stale export reference also resolves a profile outside the V6 bundle member set; the historical preservation snapshot still protects that file in this worktree but does not make it the approved V6 profile. The proposed regression must exercise production payload identity against the bundle and the same armed/active/stopped V6 binding.

No current automatic post-export equality assertion was found that reconciles or safely rejects the wrong envelope hash. Strict independent consumer validation against the approved profile must reject it; accepting it would mislabel evidence from the explicit STOP configuration as the historical profile. Header schema identity remains correctly V2 and unchanged; that is a different field and does not excuse the profile discrepancy.

Severity: high evidence-integrity/capture-readiness blocker. Its impact is false provenance or rejected export, not a demonstrated provider-filter expansion or payload leak. The native mode correction itself and exact equality remain validly tested; underlying HTTP/TCP delivery causality remains UNKNOWN.

## Why existing passing tests did not detect it

Sanitizer -Validate finishes at line133 before the actual envelope at148. Its19 cases test connection selection/types/lifetimes and safe event fields but do not construct the exported provenance envelope. Runner --validate does not invoke this envelope. The new50-case mode suite proves Start properties, exact mode/bounds/ownership and profile configuration, but does not assert export identity. The independently passing controller/watchdog/scanner checks likewise cannot cover this cross-version field dependency. Byte-identical sanitizer behavior across V5/V6 preserved a stale profile path after the capture profile changed; unchanged bytes are not proof of compatibility with changed inputs.

## Preservation and bounded evidence

Branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached origin/main and merge base e799d74063678bb0eccbea445d5ab3c8628dd2c0. Staging remains empty. No Git mutation/fetch.

Independently rehashed all20 frozen code paths,13 bundle members,2 frozen manual paths,25 product-source paths and1175 preserved historical paths: exact. Source25 remains ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. Prior PASS report SHA64e8e6759196a1c0c7f27cee5273fe13d81a49f0fa6c7ca09d7970c811cdf61b unchanged. V6 bundle remains b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7. No existing source/report/helper/test/SOP changed; only this assigned supplemental report is new.

No ETW Query/Start/Enable/Stop, Arm/Watchdog, fixture, confirmation, socket, raw ETL or protected operator file execution/access. No test rerun was needed to prove this literal hash origin; no uncertainty was replaced by a passing rerun.

## Minimum contingent correction and stop boundary

Under fresh owner reassessment only, the smallest proposed helper change is the V6 sanitizer's single profile-file reference in actual payload construction from V2 to the independently approved V6 profile. Preserve the V2 schema reference, field selection, sanitizer protections and all capture/runtime constraints. Add focused actual-envelope provenance regression proving the exported profile_sha256 equals the approved bundle/V6 profile, that the stale V2 value is rejected, and that field/schema/connection safety behavior remains. A test must reach the envelope construction boundary rather than merely repeat the existing selection tests; synthetic metadata is sufficient and raw ETL is unnecessary.

Any correction changes the frozen sanitizer/bundle identity and needs a fresh exact binding, independent code review and independent administrator manual review. Reassess candidate versioning with the owner rather than editing accepted/frozen evidence. No fix, dual-identity exception, weakened binding, capture rerun or reuse of previous RunIds is authorized by this supplemental review. The current owner assignment bounded profile/controller/tests/docs and marked this as the final helper correction cycle; the coordinator is correctly stopping for owner reassessment before widening sanitizer remediation.

Current disposition: **BLOCKED; do not arm V6.** PR81 remains NOT READY FOR HUMAN MERGE. No product, Git publication or PR update/merge action is justified.

## Exact supplemental binding

Review identity uses SHA256 of sorted compact UTF-8 JSON below without newline. Report raw hash is reported externally.

Review identity: 1f37eb1bdcb36aab160dc1498fdce206a4abdf3d20a345f86e9a37a85b23891a

```json
{
  "actual_export_v2_profile_sha256": "74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1",
  "branch": "feat/blocker-resolution-idp-ux-optimization",
  "bundle_sha256": "b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7",
  "cached_main": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "capture_executed": false,
  "code_manifest_identity": "14a0e1e9e969244719042245920f786e1aeede6ae485ec3484f3b00fda4d66f3",
  "code_manifest_sha256": "8888ad82038cc147aa42eb345654947dd86dc03f44205e1b2f2fd7a45100acde",
  "correction_implemented": false,
  "expected_v6_profile_sha256": "ce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f",
  "fixture_executed": false,
  "head": "dd8c36c8a911f4b5f3b80e7441d049f1aa976599",
  "manual_manifest_identity": "70c07164a74f5009b130a7d6b00aaf203506647c39a1bff46d885318363ec8fc",
  "manual_manifest_sha256": "230f5fadf90a30a608b8b71b57ba7a9d0fb33bbef30f8e49ccfa39f4c5411a06",
  "merge_base": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "preserved_count": 1175,
  "prior_code_gate_sha256": "64e8e6759196a1c0c7f27cee5273fe13d81a49f0fa6c7ca09d7970c811cdf61b",
  "raw_etl_accessed": false,
  "readiness": "BLOCKED",
  "sanitizer_sha256": "f4b67b37fc9980a4731698559ff0dbfbcdfc72cc1d85868ba79d0aad74c1392c",
  "scope": "read-only V6 sanitized export profile provenance reassessment",
  "source25_identity": "ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490",
  "source_location": "pr81-tcp-capture-v6/Sanitize-TcpTrace.ps1:148",
  "verdict": "FAIL"
}
```
