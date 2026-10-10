# Blocker optimisation: prepared pre-publication checklist

This is bounded preparation against the repository
[canonical checklist](../../.agents/skills/integration-safe-development/references/PRE_PR_CHECKLIST.md).
It is not a completed clean committed pre-PR audit. Independent acceptance is pending
at this record's freeze. Publication requires its exact PASS and separate owner authority.
Commit, push, PR creation and merge remain unauthorized in this assignment.

## Baseline and branch

| Item | Observed disposition |
|---|---|
| Feature branch is not main | Satisfied: feat/blocker-resolution-idp-ux-optimization. |
| Initial BASE_SHA recorded | Satisfied: e799d74063678bb0eccbea445d5ab3c8628dd2c0. |
| Fresh fetch and latest-main drift check | Satisfied in this governance run: HEAD/main/merge-base all e799d740; HEAD..origin/main empty. |
| Latest main integration | No drift; no merge needed or performed. Recheck after owner-authorized commit and immediately before publication. |

## Conflict, delta and commit scope

| Item | Observed disposition / remaining action |
|---|---|
| Frozen prior content/source match | Satisfied: prior384 content1c880a5a and source68 identity5de89b19 exact. Final governance augmentation must receive new independent review. |
| Unmerged paths/conflict markers | No unmerged paths. Final explicit-path marker/hygiene audit is required before freeze and staging. |
| Path ownership/classification | Task entry has365 changed paths:65 tracked modifications and300 untracked; all accounted for by historical manifests/final artifacts. Final file manifest must classify every new governance/report derivative too. |
| Intended/supporting work committed | NOT DONE: explicit owner prohibition. Proposed original implementation/evidence scope and new governance scope are below. |
| Clean index/worktree | NOT DONE: index is empty; implementation/report changes are intentionally uncommitted. Do not claim task/repository clean. |
| Whitespace | Tracked diff and explicit new Markdown checks pass in acceptance verification; publisher must repeat staged checks. |
| Hotspots | Existing backend document/reconciliation/CLM/zero-touch owners, CaseDetail/batch review view/query effects, owning E2E cleanup runner and CI shard aggregate. Retain accepted source identity. |
| Dependencies/lockfiles | No dependency or lockfile change in the current changed-path set; no regeneration is assigned. |
| Existing CI | Retained jobs and complete89-selector scheduling are independently covered by prior source review and runner tests. Candidate remote runs remain NOT_RUN. |

Proposed commit separation, subject to owner authorization:

1. **Original implementation and preserved evidence:** the365 task-entry changed paths,
   with exact per-file hashes from the final publication manifest. Suggested message:
   `feat: batch blocker reviews and support safe Final Review edits`.
2. **Owner risk acceptance and release governance:** only the new owner-risk record,
   updated criteria, acceptance verification, this checklist, review/publication manifests,
   new independent report and final publication handoff/receipt. Suggested message:
   `docs: record candidate-scoped SDQ-01 risk acceptance and release gate`.

Use explicit allowlisted paths and inspect the staged diff; never broadly stage ignored
tmp, dependencies, runtime output, private configuration or unrelated checkout content.
The manifest's self/final-receipt hashes are recorded as final derivatives without a
circular content identity. Neither commit has been created here.

## Contracts, authority and behavior

| Surface | Original implementation disclosure / governance delta |
|---|---|
| API/types | Bounded group review request/response/current-context and derived Final Review edit availability. Governance continuation changes no route/type. |
| Persistence/schema/CAS | Existing schema10, strict identity/CAS and insert/update/deletion semantics remain; section checkpoints are resumable, not a cross-owner atomic transaction. |
| Connector/mapping | Existing local IDP line-ending normalization/native classification; GoldTier mapping/contracts/TLS and source precedence remain. No new provider owner. |
| Configuration | Opt-in synthetic sponsor fixture/seed modes and test composition; unchanged dependencies and provider classifications. Current continuation adds documentation only. |
| Business/auth/security | Explicit supported choices, in-lock creator/team/currentness reauthorization and freeze/no-replay preserved. No sponsor-confirmed new policy, grant or approval. |
| Runtime/frontend | Original task adds tab-scoped draft choices, one explicit batch mutation/authoritative refresh and safe Final Review edit-return/re-evaluation. No runtime change in this governance continuation. |
| Main behavior | No main drift observed. Existing recovery, safe404, session/cache/currentness, ledger stop/freeze and provider isolation retained. |

## Verification and publication conditions

| Item | Current evidence / pending publication requirement |
|---|---|
| Focused/broad applicable checks | Recorded product evidence plus round3 complete89/112 browser,48 harness,109 backend,576 frontend/typecheck and independent focused checks; exact reuse attribution in updated acceptance. |
| Mongo/contract/security | Recorded guarded physical143/zero skips and owner/restart/CAS checks; no persistence changes here. SDQ-02 closed; current exact resource absence/hygiene verified without database access. |
| New DOCS_ONLY checks | Six governance/security checks, exact hashes/evidence bindings, new Markdown/diff hygiene pass; no new forensic/product run. |
| Independent QG | PENDING new assigned report at freeze. Earlier FAILs are historical; do not replace them with a self-issued PASS. |
| Clean committed pre_pr_check.py | NOT_RUN. Required only after authorized commits/integration and clean tree; cannot be satisfied by this uncommitted preparation. |
| GitHub candidate CI | NOT_RUN. No candidate commit/push/PR exists; main's old CI is not candidate evidence. |
| Publication authority | NOT_GRANTED. Stop after independent PASS and completed publication handoff; return READY FOR OWNER PUBLICATION AUTHORIZATION only. |
| Future main drift or source change | Integrate only with owner authority, preserve current-main intent, rerun affected checks and obtain fresh independent review when reviewed content changes. |
| Push/PR CI and human merge | After authorization/pre-PR PASS, publisher verifies local/remote SHA, opens PR against main and checks push and pull_request runs separately. Human repository owner performs merge. |

Historical SDQ-01 cause remains unresolved and owner-accepted for this exact candidate.
A future timeout/full-suite failure/new correctness concern is actionable new evidence;
STOP rather than apply this acceptance automatically. Real Sandbox/UAT remains
NOT_VERIFIED; production SSO/Live interoperability/final approval are not proved.
