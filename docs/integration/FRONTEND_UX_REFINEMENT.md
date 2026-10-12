# Frontend UX refinement

Assigned 2026-10-12. Change class: `FRONTEND_UI`. Task scope is the owner's four
frontend refinements; publication is authorized only after a fresh independent PASS.

## Task identity and boundary

- Worktree: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ux-task`.
- Branch: `feat/case-ownership-ux-quick-refinement`.
- BASE_SHA / initial HEAD / inspected origin/main:
  `832ff770d37c3f4710a9fd271a8fe00af3d2a407`.
- One implementation writer. Independent review is a separate read-only run over
  frozen content, with only its assigned gate report writable.
- Managed worktree creation hit Windows path-length limits. Ordinary task-owned
  creation with Git long-path support succeeded. Existing worktrees were preserved.
- No commit, push or PR before independent PASS; human owner decides the merge.

## Behavior and canonical owners

`ownershipDisplay.ts` formats fixed-point and scientific Decimal strings solely for display, with at most two
fractional digits and no trailing zeroes. Positive values rounded below the display
resolution are labelled `<0.01%`; actual zero remains `0%`. Retained calculation
operators remain unchanged while percentage tokens use the same formatter.
OwnershipStructure, OwnershipPathExplorer, UboSummary (also used in Final Review),
and proposed observation labels reuse it. Raw declarations in editable inputs remain
exact. Backend Decimal strings, evidence, calculations, comparisons and classification
are never changed or recomputed. On-screen wording distinguishes rounded display from
full-precision backend threshold results.

OwnershipPathExplorer removes the redundant candidate button row and its unused
selection-request counter. Native holder buttons remain in OwnershipStructure, including
repeated occurrences, root/unlinked selection, collapse, retained paths and technical
inspection. Technical actions and the actual UBO summary remain.

The existing CaseDetail/design-system layout owns desktop stickiness. Above 900px,
the pipeline sidebar stays 12px inside the viewport and can scroll vertically when
its content exceeds the available height. The existing stacked layout remains at
900px and below. All twelve backend pipeline stages remain present.

CaseAttentionSummary derives its current entries directly from the loaded summary's
OPEN active exceptions, matching intervention projections, technical failure and pending
document intake. Final confirmation is an action, excluded from blocker counts;
backend-labelled warnings are also excluded. No immediate blockers is explicit.

CaseDetail routes attention through its existing evidence/action/disclosure helpers.
Document attention selects the specific current source or document decision, or the
bound replacement upload when no source choice is authorized. The BlockerDecisionReview
handle can expose a decision group without choosing a draft or applying a mutation.
Ownership, identity, classification, policy, existing-customer confirmation, Final Review
and retained safe diagnostics keep their existing controls and authority. Remaining
interventions use their existing card. Missing/disabled actions give a status notice
beside Attention required. Delayed focus is case/actor/generation/version bound; changed
case/version cancels pending navigation. Every navigation action is local and read-only.

## Preflight and verification boundary

Current session uses PowerShell, Python 3.12.10, Node 22.23.3, npm 10.9.9,
Vitest 3.2.4 and the configured authenticated Playwright lifecycle. Browser checks
reserve ports 8875/4283, memory-only backend, ephemeral synthetic sessions, and offline
Mock/protocol fixtures. No Mongo database or live provider is used; no dotenv is read.
Local HTTP/process checks need execution outside sandbox restrictions. A task-local
system-package Python venv binds this worktree's unchanged backend, plus already pinned
pypdfium2 5.13.0 / Pillow 12.3.0. `pip check` passes. Locked frontend install changes no
manifest or lockfile. No new dependencies are introduced.

Mandatory evidence: complete frontend tests, typecheck, production build, targeted
actual authenticated browser checks (desktop/tablet/mobile), root relationship-ID
collision, source/field/replacement/ownership/customer/final/technical navigation,
case/version changes, disabled controls, raw precision/classification and no unwanted
mutations/replay. Security/governance use tracked/task-owned paths. Backend/contracts/
physical Mongo and full E2E are not required by this frontend-only change class.

Fresh evidence and the frozen path/hash identity are recorded in the independent
[fresh correction gate](../../.ai-pipeline/reports/FRONTEND_UX_REFINEMENT_QUALITY_GATE_R1.md).
The initial gate found scientific API Decimal values were displayed as unavailable;
the one authorized correction supports those strings in the same display-only owner.
The initial FAIL report remains preserved separately.
Runtime screenshots/logs remain task-owned ignored evidence; no confidential artefact
is added to Git. Existing frontend React test warnings and the production bundle-size
warning are reported rather than hidden.

## Change disclosure and next action

Only frontend presentation, accessibility and local focus/selection behavior change.
API/shared browser types, durable schema, connectors, configuration, business rules,
backend mappings, auth/security semantics, architecture owners, provider classifications,
target ledger and backend runtime are unchanged. The internal review navigation handle
and ownership component props change locally. No sponsor rule, source precedence,
autonomous resume/send, new mutation or external interoperability claim is introduced.
After independent PASS, the separately authorized publication run verifies identical
content, latest main, scoped staging, a normal commit, canonical clean committed
pre-PR checks, normal push, one PR and authoritative remote SHA/tree/CI evidence.
