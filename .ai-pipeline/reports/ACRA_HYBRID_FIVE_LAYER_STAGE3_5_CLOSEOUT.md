# ACRA Hybrid Five-Layer (D-077) — Stage 3.5 Owner Visual Review Closeout

This is a report artifact only. It changes no reviewed content, and like the QG reports it
is outside the reviewed tree.

## Outcome

- **Owner visual acceptance:** CONDITIONALLY ACCEPTED (owner decision, 2026-10-23). The
  existing, unchanged Ownership & UBO frontend correctly shows:
  - the five corporate levels;
  - DIANA KOH's two paths (18.75% + 6.25% = 25%) and the other synthetic interests
    (BEATRICE LIM 30, ALEX TAN 20, EDWARD NG 15, CHARLES ONG 10);
  - the Review Required state.

  The frontend must remain unchanged.
- **Actual Marketplace Mock integration verification: PARTIAL.** The bounded read-only
  provider probe ran with genuine HTTPS requests and its observations are below. No
  application onboarding journey has been run against the live Marketplace Mock lane.
- **Publication:** on hold until the owner decides.

## Bounded Marketplace Mock probe (owner-authorized, executed once)

Command:
`python scripts/phase24_acra_mock_discovery.py --config-env-path <approved .env> --lane five-layer-hybrid`.
It was run from the worktree with `PYTHONPATH` pinned to the worktree backend.

Preflight on the reviewed script:
- **Credentials:** only the two named Marketplace keys are read, from the process
  environment first, otherwise from the env file in memory. They are never printed, and
  if absent the script makes zero calls.
- **Endpoints:** one token POST to the fixed token endpoint. GETs go only through the
  existing connector's fixed `entityBasicInformation` and `coShareholdersDetails`
  operations, and non-Mock URLs are rejected.
- **Budget:** at most 17 receipts (1 token plus 16 reads) across 8 UENs.
- **Transport:** verified TLS, no proxy inheritance, 10 s timeouts. It stops on
  401/403/transport failure.
- **Output:** sanitized.

The raw sanitized output is kept outside the repository. A scan found no credential-like
content.

Observed: `evidence_class: MOCK_INTEROPERABILITY_OBSERVED` (live HTTPS access to the ACRA API
Marketplace **Mock** environment only, never ACRA production or Live-registry verification).
There were 11 genuine external requests (1 OAuth POST plus 10 GETs), all HTTP 200, and 0
cache hits (the probe bypasses the application cache).

| UEN | Role in demo | Observed | Classification |
|---|---|---|---|
| `11111999A` | Garden root | Same-UEN profile; BUSINESS_PARTNERSHIP; 4 people, all OWNER/PARTNER/MEMBER roles (2 GETs: company + embedded officers) | Verified official identity; no quantitative ownership |
| `201511222D` | L1 root (OPQ) | Same-UEN profile; constitution value absent, so the current classifier gives `OTHER` | Verified official identity; company-shareholder method not applicable (not dispatched) |
| `111111111M` | Garden's SIM LIM | Basic entity empty. Diagnostic shareholder read: 1 entity, 4 parties, 1 withdrawn | Missing entity identity; shareholder rows UNBOUND_NOT_CANONICAL (never a canonical issuer) |
| `200811111M` | L2 | Basic entity empty | Missing entity identity, so the app uses `LOCAL_SYNTHETIC_IDENTITY` |
| `201688888A` | L3 | Basic entity empty | Same as L2 |
| `200811111K` | L4A | Basic entity empty | Same as L2 |
| `199801111H` | L4B | Basic entity empty | Same as L2 |
| `111111111K` | L5 | Basic entity empty | Same as L2 |

Not exercised by this probe:
- The relationship operation (unsupported, never dispatched).
- The local synthetic relationships (they exist only in the application overlay).
- The offline stand-in (used only by tests, E2E and the visual review).

The live observations agree with the offline fixture's assumptions: root profile present
with an unclassified legal form, and L2–L5 and SIM LIM empty. The probe does not report
OPQ's legal name or registered address. A live application onboarding could therefore
still stop at `CANONICAL_DATA_INCOMPLETE` (no address) or raise a name reconciliation
review.

**The sample catalogue does not provide a live five-layer ownership graph.** Only the root
identity is official. Every L2–L5 identity and every ownership link is local synthetic,
and the analysis stays REVIEW_REQUIRED.

## Presentation/provenance limitations (owner-recorded; no frontend change authorized)

1. **Misleading synthetic-registry caption.** The corporate-owners table caption reads
   "Each corporate owner is resolved from its own synthetic Mock registry record". For the
   hybrid lane the truth is different: an official Marketplace lookup (here NOT_FOUND),
   then whitelisted LOCAL_SYNTHETIC_RELATIONSHIP links. The per-issuer `identity_basis` /
   `official_entity_lookup` are available only through the API.
2. **Partial graph with "0% undisclosed".** "Graph partial … Up to 0% root-equivalent
   interest remains undisclosed" means every branch is topologically attached. It does not
   mean the evidence is complete: quantitative evidence is local synthetic.
3. **Simulated provider-backed counter.** In the offline visual review, "5 registry lookups
   (5 provider-backed, 0 reused from cache)" counts offline stand-in responses, not
   external calls. The offline status is disclosed only by the header badge "ACRA
   Marketplace protocol · synthetic offline test evidence". In a live lane the same
   counter would count genuine Marketplace Mock lookups.
4. **OPQ legal-form blocker versus synthetic ownership review.** The primary visible
   blocker is `OWNERSHIP_METHOD_UNSUPPORTED` ("No ownership method is supported for this
   registry legal form"), caused by OPQ's unclassified official legal form. The separate
   `SYNTHETIC_OWNERSHIP_EVIDENCE` issue, which would independently keep the case under
   review, is not surfaced in the UI and is visible only through the API. Resolving the
   legal-form blocker alone would not make the case ready.

## Reviewed identity and evidence validity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\acra-hybrid-five-layer-20261023`,
  branch `feat/acra-marketplace-hybrid-five-layer-ubo-20261023`. HEAD = BASE =
  `origin/main` = `24c3de385ba5cda099a3dc3b1b266fdf93aa4738`. The candidate is
  uncommitted, and nothing is staged.
- Reviewed tree (temporary-index identity over the modified and untracked paths, excluding
  the re-QG report and this report) is still
  **`f30d7e218548b3b7c43364ce7be7cd32fa9d0441`**. No source, test, configuration or doc
  content changed after the re-QG PASS.
- Unchanged, therefore still valid:
  - full backend run, 3120 tests / 0 failed;
  - physical Mongo, 168/168;
  - contract tests (44) and the CI unittest lanes;
  - frontend typecheck, Vitest (1050) and build;
  - browser 115/115;
  - focused five-layer tests.
- The independent re-QG verdict, PASS on `f30d7e2…`, still applies.

## Remaining publication prerequisites

1. Explicit owner authorization for Stage 4 (commit, non-force push, one PR; no merge).
2. Owner decision on the stale wording in the reviewed docs, which predate this probe.
   The demo guide's §2 table and the Stage 1/2 report still say the live probe was
   `NOT_RUN_CREDENTIALS`. Recording the observations above in tracked docs would be a
   docs-only change, and it needs a bounded independent recheck before publication.
   Otherwise this closeout report carries the observations alongside the reviewed
   content.
3. At publication: commit exactly the reviewed content plus the chosen reports, run
   `scripts/pre_pr_check.py` on the clean committed state, then record the remote CI
   result. Billing-blocked jobs count as not executed, not as passed.
4. Optional: an owner-run live-lane application onboarding of OPQ
   (`ACRA_CONNECTOR_MODE=api_marketplace_mock`,
   `ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay`). It would show whether the
   official OPQ profile passes the canonical address/name checks. It is not required for
   the bounded read-only verification.
5. Open sponsor/provider dependencies: Q-004, Q-012, Q-019, Q-002.

## Evidence classification summary (added at Stage 4 publication, 2026-10-23)

The owner authorized Stage 4 publication on 2026-10-23. The sections above are kept as
written at Stage 3.5. This summary restates their classifications without changing them.

| Evidence | Classification |
|---|---|
| Actual ACRA API Marketplace Mock integration | PARTIAL verification |
| Genuine network requests (bounded probe) | 11: 1 OAuth token POST + 10 read GETs, all HTTP 200, 0 cache hits |
| Offline five-layer fixture (tests, E2E, visual review) | Simulated in-process responses (`AUTOMATED_OFFLINE_SIMULATION`), 0 genuine external calls |
| Five-layer ownership relationships (L1 to L5 and the persons) | LOCAL SYNTHETIC (`LOCAL_SYNTHETIC_RELATIONSHIP` overlay) |
| Lower-level official entity records (L2 to L5, SIM LIM) | Empty in the observed Marketplace Mock reads |
| Root OPQ `201511222D` | Officially observed same-UEN profile; legal form `OTHER` (constitution absent) |
| Relationship operation | Unsupported; never dispatched |
| Live-lane application onboarding | NOT_RUN |
| Independent QG | PASS on reviewed tree `f30d7e218548b3b7c43364ce7be7cd32fa9d0441` |
| Owner visual acceptance | CONDITIONALLY ACCEPTED |

The demo guide (§2) and the Stage 1/2 report say the live probe was
`NOT_RUN_CREDENTIALS`. That was true when they were written and reviewed, and they are
left unchanged. For the separate read-only Marketplace probe only, this report
supersedes those statements.
