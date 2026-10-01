# CI publication remediation - round 2

## Outcome and reviewed parent

Last authorized bounded CI remediation for PR #65 on `fix/demo-happy-path-stabilization`, parent `f685d01421839efbbce03225f594f6d7278581b6`; original integration base `efc31f450f0103766fa812bc0aa80754f801dbe9`.
Original 112-path publication and round-1 content, gates, manifests and provider chronology are preserved. This delta requires a fresh independent PASS before commit.

## Cause and smallest correction

**A - product defect:** round-1 push run 36843727980 and PR run 36843733110 passed five lanes, including genuine physical Mongo, but both E2E jobs failed the same existing Garden 200% content-zoom assertion. Root scroll width was 1513 at client width 1440; the case-header controls extended past the viewport. Header/action wrapping depended on a viewport media query even though magnification reduces available content width independently.

The existing stylesheet now wraps the case-detail header and its actions at available width, with bounded shrinking and title wrapping. No overflow-hiding or clipping was added. A deterministic 280-pixel header-container regression failed first on the committed CSS with scroll width 416, then passed the correction. It verifies priority selector, Set button and status remain visible; the existing root zoom, evidence width, corporate width, confirmation and ownership assertions remain enabled and unchanged. The new regression changes only temporary inline container width and restores it in a finally block; it issues no business mutation.

## Verification and identity distinctions

- Focused Garden browser: failing-first container overflow, then PASS with original 200% zoom and complete explicit Mock confirmation.
- Complete configured isolated browser lifecycle: 26 selectors / 27 actual tests PASS, including all six Garden tests and Golden; supported 900-second local overall deadline, no skip or disabled assertion.
- Full frontend: 393 passed / 33 files; typecheck and build PASS. Supported secret scan and tracked/new-file whitespace PASS before review.
- Backend, cache owner, provider transport/ledger, persistence, CI launcher and fixture routing bytes are unchanged from independently accepted round 1. Its relevant backend 1531 passed / 38 ordinary skips, contracts 44, runner 34 and real Mongo 38 passed / zero skips are explicitly reused; no new execution claim is made for those unchanged local suites.
- Round-1 current CI physical jobs executed nine suites, 38 collected / 38 passed / zero failed, errors or skipped. That evidence is historical after this delta commits: the new current PR physical lane must execute successfully again. Current remote CI for round 2 is pending publication.
- Raw three-path review identity is frozen under ignored task-owned `tmp/PUBLICATION_REMEDIATION_02_REVIEW_MANIFEST.json`; the assigned independent report is the fourth publication path. Local runtime executions precede the report-only freeze; source/test bytes remain unchanged after those executions.

## Scope and safety

Only frontend case-header reflow and its browser regression changed. Application API/types, schema, connectors, configuration, business rules, mapping, authentication/security, architecture owners, provider classification, backend workflow/cache behavior and target ordering are unchanged. Accepted zero-touch, Garden LOCAL 60/40 Decimal ownership, Golden zero exception interventions and one final confirmation remain verified.

External ACRA/GoldTier/PingFed/Production calls: zero. Retained recovery remains ID 143880 / PROVIDER_VERIFIED_RECOVERY, original Shell uncertain, replayed=false, Policy/Amend absent. No retained Mongo access, mutation, cleanup or shutdown; no Atlas/normal application database test use. Retained service remains running. No Live or full external lifecycle claim.

## Next authorized action and stop boundary

Fresh independent quality gate, exact four-path stage/commit, clean committed pre-PR, normal push and observation of both current push/PR runs. Require all applicable lanes including current physical Mongo, then an independent post-publication checkpoint. This is remediation round 2 of 2: any unresolved current CI failure must be preserved and returned for planner review. No third remediation or merge is authorized.
