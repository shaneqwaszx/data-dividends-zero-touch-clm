# UI V2 Screen & Function Contract

**Audit date:** 2026-09-02
**Audit mode:** Analysis only
**Current integration branch:** `integration/ui-v2-finalization`
**Current integration `HEAD`:** `b196d887964f0d93b93dfd2d39c271195eb19af9`
**Latest backend/business reference:** `origin/main` at `74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93` (`fix: defer speculative ACRA OAuth handling (#21)`)
**Frontend reference:** `origin/ui-edits-v2` at `be6bf3fa6dc3f15230d196f0d9c84cf9ccc66814`
**Original teammate PR:** PR #20, `ui edits v2`, open, head SHA equal to the frontend reference
**Repository state:** Existing unstaged/untracked integration work was inspected and not modified. This report is the only file created by this pass.

## 1. Executive summary

The intended product is a Singapore-only, evidence-led Zero-Touch CLM POC with a restrained serif design, a compact top navigation, a two-card onboarding intake, a persistent pipeline rail on detail states, portfolio tables, review dialogs, a completed-case projection, a client-style record, a per-case timeline projection, and a read-only policy view.

The original screenshots were not present in the supplied attachment directory. The directory contained only `pasted-text.txt`, and no product UI screenshot was found in the repository or PR #20 description/discussion. Consequently, screenshot-only facts—exact logo treatment, account name, dropdown icon, some labels, pixel spacing, and the exact composition of states described only in the brief—cannot be visually verified. The task brief's explicit statement that the screenshots contain a signed-in/account area is retained as a requirement, but its exact pixels and copy remain a human approval dependency.

The strongest verifiable visual reference is therefore `origin/ui-edits-v2`. It defines brand `CLM Onboarding`, visible navigation `Home`, `Cases`, `Onboarded`, `Audit`, a hidden `Policy` route, Cormorant Garamond headings, Lora body text, a warm neutral/gold palette, compact tables/cards, 460 px dialogs, and a roughly 53 px content-driven header. It does not mount an account area. The current integration also does not mount one.

Latest `origin/main` exposes no login, user session, reviewer directory, reviewer identity, role, RBAC, assignment, return-for-rework, generic resubmit, production screening, production risk, scheduler, global audit export, or production client-master API. The truthful account treatment is therefore a presentation-only identity such as `Local POC operator` plus `Authentication pending`; it must not claim that a named reviewer is logged in.

The current integration has a sound adapter direction and covers early case creation, independent multi-file intake, explicit completion, targeted failed-file retry, same-case continuation, case list/detail, replacement, reconciliation decisions, exception resolution, ownership reads, recovery/resume, completed-case projection, timeline projection, execution profile, and safe errors. It is not yet the complete screen/function contract. Material gaps include:

- the missing account/login visual region;
- no available screenshot baseline for pixel/label acceptance;
- a Cases jurisdiction filter that does not affect the results;
- list columns whose backend values are unavailable but whose UI does not clearly explain that limitation;
- no dedicated registry-progress, registry-unavailable, or confirm-details composition;
- Case Detail omits important backend-authored exception evidence, registry operations/issues/provenance, document field evidence/provenance/confidence, reconciliation validity/provenance, ownership graph paths/provenance/threshold, readiness blockers/warnings, metrics, and Mock target summary;
- unsupported assignment/rework launch buttons look actionable before their disabled dialogs explain the limitation;
- the original design's conceptual `SCREENING`, risk, approval, rework, resubmit, scheduler, reviewer and production-client concepts have no corresponding backend state or mutation;
- responsive rules do not cover the UI V2 `nav`, `ds-two-col`, `side-panel`, wide tables, or fixed-width content rails sufficiently.

No implementation-ready verdict is issued. The final remediation must wait for the human approvals at the end of this report.

## 2. Source hierarchy

| Priority | Source | Authority in this audit | Evidence status |
|---|---|---|---|
| 1 | Original user-provided screenshots / visual prototype | Layout, brand, navigation, account area, composition, visible product language | **Unavailable in supplied files.** The brief's descriptions are retained, but pixels cannot be verified. |
| 2 | `origin/ui-edits-v2` / PR #20 | Reusable JSX, CSS, tokens, tables, dialogs, forms and page structures | Verified at `be6bf3f`; PR #20 contains 17 frontend files and no linked screenshots. |
| 3 | `origin/main` | Routes, DTOs, domain states, workflow semantics, persistence/recovery, errors, security and execution profile | Verified at `74a5fd2`, including PR #21. |
| 4 | `integration/ui-v2-finalization` | Implementation under audit only | Inspected at `HEAD b196d88` plus existing unstaged/untracked frontend work. |

Project authority remains subject to `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/decisions/DECISION_LOG.md`, and open sponsor questions. In particular, Q-012 and Q-015 remain open.

## 3. Screenshot inventory

### 3.1 Supplied screenshot files

| Screenshot ID | Screen/state | Major regions | Controls/data/navigation/account/dialogs/actions |
|---|---|---|---|
| `NONE-SUPPLIED` | Not inspectable | Not inspectable | The attachment directory contained only the written brief. No screenshot ID can be assigned without fabricating evidence. |

### 3.2 Brief-asserted visual states requiring screenshot confirmation

These are requirements named by the task, not substitutes for a screenshot inventory.

| Evidence ID | State/concept | Verifiable branch analogue | Unverified screenshot-specific items |
|---|---|---|---|
| `BRIEF-01` | New onboarding | `HomeOnboarding` initial state | Exact title/nav wording, artwork/icons, spacing and dropzone copy |
| `BRIEF-02` | Registry extraction / verification | Home/Case pipeline plus registry data | Exact progress treatment and operation animation |
| `BRIEF-03` | Registry unavailable | Banner/error patterns | Exact error composition and CTA |
| `BRIEF-04` | Confirm details | Corporate particulars and reconciliation | Exact card order, editable appearance and provenance placement |
| `BRIEF-05` | Cases | `CaseQueue` | Exact filters, table widths and status language |
| `BRIEF-06` | Case detail running/attention | `CaseDetail` | Exact pipeline band names, loop treatment, review composition |
| `BRIEF-07` | Assign reviewer | `AssignReviewerDialog` | Exact reviewer list/account relationship |
| `BRIEF-08` | Return for rework / Rework | `ReturnForReworkDialog`; prototype-only `REWORK_REQUIRED` | Exact returned-case page and correction affordances |
| `BRIEF-09` | Corrections/resubmit/rerun | Replacement/retry/resume equivalents | Exact distinctions between resubmit and rerun |
| `BRIEF-10` | Completed / Onboarded | completion banner, `OnboardedClients` | Exact completion copy and production-looking fields |
| `BRIEF-11` | Client record | `ClientDetail` | Exact field inventory and side-rail treatment |
| `BRIEF-12` | Audit trail | `AuditTrail` | Exact action labels and export appearance |
| `BRIEF-13` | Policy/rules | `PolicyRules` | Whether Policy is visible in navigation |
| `BRIEF-14` | Signed-in/account area | No mounted UI V2 analogue | Account name, signed-in text, avatar/logo and dropdown affordance |

## 4. `ui-edits-v2` implementation inventory

PR #20 was verified directly: title `ui edits v2`, head `ui-edits-v2`, SHA `be6bf3f`, base `main`, and 17 frontend files.

| Area | Reference implementation | Important visual/function facts |
|---|---|---|
| Shell | `App.tsx`, `design-system.css`, `main.tsx` | Brand `CLM Onboarding`; `Home`, `Cases`, `Onboarded`, `Audit`; Policy route hidden; environment banner in the trailing nav position; no account control |
| Home | `HomeOnboarding.tsx` | `Start onboarding`; jurisdiction + Registration ID/UEN card; document drop card; file rows; `Create onboarding`; pipeline detail state |
| Cases | `CaseQueue.tsx` | status/jurisdiction/search toolbar; 8-column table; row click |
| Case detail | `CaseDetail.tsx` | 260 px left rail, pipeline, loop text, exception cards, particulars/directors, dialogs, prototype resubmit |
| Assign reviewer | `AssignReviewerDialog.tsx` | 460 px modal; reviewer select; note; Cancel/Assign |
| Return for rework | `ReturnForReworkDialog.tsx` | reason; required comment; flagged field chips; Cancel/Return |
| Onboarded | `OnboardedClients.tsx` | jurisdiction/risk/search; Client/Company/Jurisdiction/Risk/Onboarded/Next review |
| Client record | `ClientDetail.tsx` | 284 px rail; schedule; documents; export/review; particulars/activity/directors/beneficial owners/relationship/onboarding/checks/history |
| Audit | `AuditTrail.tsx` | page title `Audit trail`; action chips; Timestamp/Action/By/Change/Loop; CSV export |
| Policy | `PolicyRules.tsx` | jurisdiction table; pipeline, roles and scheduler cards; hidden from visible nav |
| Prototype data layer | `api.ts`, `mockData.ts`, `types.ts` | Speculative `/api/cases`, `/api/clients`, `/api/audit`, `/api/reviewers`, `/api/policy`, assign/rework/resubmit calls and mock fallbacks; not authoritative |

The reference branch's prototype concepts `SCREENING`, `REWORK_REQUIRED`, loop history, reviewer assignment, false-positive clearing, risk, approval, scheduling and global audit are not evidence that the backend supports them.

## 5. Latest-main backend inventory

### 5.1 Registered UI-relevant endpoints

| Domain | Endpoint/function | Request | Response / behavior |
|---|---|---|---|
| System | `GET /health` | None | Service health only |
| System | `GET /api/system/execution-profile` | None | Safe connector environments, IDP threshold, UBO threshold and persistence label |
| Demo | `GET /api/onboarding/mock-scenarios` | Demo gate | Scenario discovery; not normal runtime |
| Onboarding | `POST /api/onboarding/cases` | UEN, optional jurisdiction | Early onboarding case |
| Onboarding | `GET /api/onboarding/cases/{case_id}` | Case ID | Canonical entity, jurisdiction, registry acquisition, events and safe error |
| Staged CLM | `POST /api/clm/cases` | UEN, optional jurisdiction | Staged CLM aggregate |
| Staged CLM | `GET /api/clm/cases/{case_id}` | Case ID | Readiness, plan, submission/target result and timeline |
| Staged CLM | `POST .../readiness/evaluate` | Case ID | Server re-evaluation |
| Staged CLM | `GET .../submission-plan` | Case ID | Mock target operation plan |
| Staged CLM | `POST .../submit` | Case ID | Server-controlled Mock submission |
| Zero-touch create | `POST /api/clm/zero-touch/cases` | UEN, optional jurisdiction | `PENDING_INPUTS` zero-touch aggregate |
| Zero-touch list | `GET /api/clm/zero-touch/cases?status=` | Optional real automation status | Lightweight list; read-only/no provider calls |
| Zero-touch detail | `GET /api/clm/zero-touch/cases/{case_id}` | Case ID | Full zero-touch summary |
| Intake | `POST .../{case_id}/intake/documents` | One raw PDF/DOCX/TXT + `X-Document-Name` | Independent `DocumentProcessingResponse` |
| Intake retry | `POST .../{case_id}/intake/documents/{failed_document_id}/retry` | Replacement bytes/name/type | Targeted same-case retry |
| Intake complete | `POST .../{case_id}/intake/complete` | `expected_document_count` 1–20 | Explicitly starts/continues automation |
| Compatibility attach | `POST .../{case_id}/documents` | One file | Legacy attach-and-progress operation |
| Replacement | `POST .../{case_id}/documents/{document_id}/replacement` | One file + `X-Document-Event-Count` | Explicit supersession with concurrency binding |
| Progression | `POST .../{case_id}/start` | Case ID | Idempotent explicit progression |
| Recovery | `POST .../{case_id}/resume` | Case ID | Explicit resume/finalisation recovery; browser does not replay target |
| Exception decision | `POST .../{case_id}/exceptions/{exception_id}/resolve` | action + automation version + evidence version | Only server-advertised action |
| Reconciliation | `POST .../{case_id}/reconciliation/discrepancies/{discrepancy_id}/resolve` | action + automation/reconciliation versions + fingerprint | Stale-safe field decision |
| Documents | `GET /api/onboarding/cases/{case_id}/documents` | Case ID | All current and superseded document records |
| Document detail | `GET .../documents/{document_id}` | IDs | Exact document record |
| Field review | `POST .../documents/{document_id}/reviews` | field, accept/reject/correct, optional note | Legacy unauthenticated local POC field review |
| Ownership | `POST .../ownership/load`, `POST .../ownership/analyze` | Case ID | Provider-neutral load and deterministic analysis |
| Ownership | `GET .../ownership`, `GET .../ubo-candidates` | Case ID | Parties, relationships, paths, issues and candidates |
| Demo variants | `/api/demo/...` | Demo gate | Synthetic providers/UAT evidence; never normal fallback |

### 5.2 Authoritative automation states

- Status: `PENDING_INPUTS`, `RUNNING`, `WAITING_FOR_REVIEW`, `RESUMING`, `RECOVERY_PENDING`, `COMPLETED`, `TECHNICAL_FAILURE`.
- Stage: `REGISTRY`, `DOCUMENT`, `OWNERSHIP`, `READINESS`, `MOCK_GOLDTIER`, `COMPLETE`.
- There is no backend `SCREENING`, `RISK`, `APPROVAL`, `REWORK_REQUIRED`, `RESUBMITTED` or production `ONBOARDED` workflow state.
- `COMPLETED` means the accepted Mock workflow/`MOCK_GOLDTIER_SUBMITTED`; it does not mean legal approval, production onboarding, Ready-for-Approval or live GoldTier acceptance.

### 5.3 Core response facts

- The case list contains: case ID, UEN, legal name, status, current stage, updated time, active-exception count, human interventions and final outcome.
- The list does **not** contain jurisdiction, created time, assignment, reviewer, risk, client ID or next-review date.
- Detail contains the canonical entity, jurisdiction observations/resolution, registry route and four-operation registry acquisition, officers, ownership parties, relationships, issues, documents through the document endpoint, reconciliation observations/discrepancies/decisions, deterministic ownership, CLM readiness/plan/outcome, automation metrics, target operation statuses and timelines.
- No response contains a logged-in user or reviewer identity.

## 6. Global shell specification

| Attribute | Contract |
|---|---|
| Brand | Verifiable branch text is `CLM Onboarding`. Screenshot precedence cannot be applied until screenshots are supplied. |
| Logo treatment | Text-only in `ui-edits-v2`; no image/logo asset. Do not invent an icon. |
| Visible nav | `Home`, `Cases`, `Onboarded`, `Audit` in that order. Page title is `Audit trail`; top-nav label is `Audit`. |
| Onboarding wording | Nav: `Home`; page: `Start onboarding`; primary CTA: `Create onboarding`. Any screenshot wording such as `New onboarding` requires visual confirmation. |
| Policy visibility | Valid internal route but hidden in the reference/current nav. Human decision required before exposing it. |
| Divider | 1 px vertical divider, 24 px high, after brand; 1 px horizontal bottom border. |
| Header height | Content-driven, approximately 53 px: 24 px tallest inner item + 27.6 px vertical padding + 1 px border. Do not hardcode a different height without screenshot measurement. |
| Typography | Heading: Cormorant Garamond 600; body: Lora; system fallbacks. H1 34 px, H2 26 px, body 15 px/1.55. |
| Colour | Warm light gray background `#f3f2f2`; near-black `#201f1d`; gold accents `#b68235`/`#ac803e`; nav `#faf9f8`. |
| Spacing | Base sequence 4.6/9.2/13.8/18.4/27.6/36.8 px; page padding 18.4 px top, 27.6 px sides, 36.8 px bottom. |
| Active state | Text darkens and a 1.5 px gold underline appears. |
| Environment | Keep a compact backend-authored environment/persistence indicator; it is system context, not user identity. Do not let it displace the account requirement. |
| Account | Required by the brief's description of the screenshots; absent from both UI V2 shell and current integration. See section 7. |
| Responsive | Preserve visual order; below tablet width, wrap/collapse nav and account deliberately, stack two-column regions, turn side rails into top summaries, and horizontally scroll wide tables. Current CSS does not fully do this. |

## 7. Account/login specification

### A. Screenshot requirement

The brief states that the original screenshots contain a signed-in/account area with signed-in text, account name and a dropdown affordance. The actual screenshot is unavailable, so exact wording, name, avatar and geometry are unresolved.

### B. `ui-edits-v2`

`WorkspaceTabs` renders brand, divider, four tabs and a trailing environment banner. `.nav-user` exists in CSS but is unused. An `AccountPlaceholder` component says `Local demo operator` and `Authentication pending`, but it is not mounted in the UI V2 route tree.

### C. Current integration

The current integration preserves the same shell and also does not mount an account region. It retains an unmounted `AccountPlaceholder` with truthful text.

### D. Backend identity capability

None. There is no login/session/current-user/reviewer/RBAC route or response field. PingFed is a future GoldTier connector authentication dependency, not an application-user login implementation.

### E. Truthful POC presentation

Recommended contract pending human copy approval:

- small eyebrow: `LOCAL POC` or `OPERATOR`;
- display name: `Local POC operator`;
- secondary state: `Authentication pending`;
- optional screenshot-shaped chevron may open an informational popover only: `No authenticated user or reviewer role is connected in this POC.`;
- no avatar initials tied to a real person, no `Signed in as reviewer`, no role, and no account actions that imply identity/session support;
- environment profile remains separate from account identity.

## 8. New onboarding

| Specification field | Contract |
|---|---|
| 1 Purpose | Create a case early, collect bounded supporting evidence, and explicitly start processing only after intended intake is complete. |
| 2 Entry | Home nav; no active summary; no retained intake case, or user explicitly chose `Start a new case`. |
| 3 Exit/navigation | Successful completion moves within the Home workspace to progress/detail; row navigation may open Cases; `Start a new case` resets presentation state only after explicit intent. |
| 4 Visual layout | Page header followed by two cards: left identity/jurisdiction, right document dropzone/list; CTA beneath. Preserve this composition. |
| 5 Header | `Start onboarding` plus concise registry/document automation explanation. |
| 6 Rails | None before creation. |
| 7 Cards | Fixed-width identity card (420 px reference) and flexible document card (minimum 380 px reference). |
| 8 Tables | None; selected documents are compact rows. |
| 9 Fields | Jurisdiction: omitted, SG, AU, MY, HK. Registration ID/UEN: uppercase, max 32, backend grammar. |
| 10 Controls | Drop, browse, folder select, remove file, `Create onboarding`; optional demo scenario only behind both frontend/backend demo gates. |
| 11 Dialogs | None. Validation is inline/banner-based. |
| 12 Status indicators | Selected count and total bytes; per-file name/size; retained case ID after partial failure. |
| 13 Empty state | Dropzone guidance; CTA disabled or validation error when no file is selected. |
| 14 Error state | Safe per-file validation/processing error; successful uploads remain accepted; show exact retained case ID and targeted retry guidance. |
| 15 Loading state | Distinguish `Creating case`, `Uploading n of m`, `Completing intake`, and backend `RUNNING`; no fake timer. |
| 16 Backend data | Created zero-touch summary and each `DocumentProcessingResponse`. |
| 17 Backend mutation | Create; one intake POST per file; failed-document retry; explicit intake completion with intended count. |
| 18 Unsupported concepts | Server folder traversal, ZIP upload, images/OCR, `.doc`, arbitrary directory upload, client-authenticated uploader. |
| 19 Truthful fallback | Folder chooser supplies ordinary files only. Unsupported/mismatched types are rejected before upload and again by backend. |
| 20 Responsive | Stack cards; remove fixed minimums; make file row actions touch-safe; keep total/count visible. |

Functional constraints: PDF, DOCX and UTF-8 TXT; multiple files; ordinary folder selection; maximum 20 current files; maximum 5 MiB each; maximum 25 MiB total; basename/MIME validation; frontend duplicate suppression by name+size+last-modified; backend count/size/total remains authoritative. The backend does not provide content-hash deduplication, so the UI must not claim cryptographic duplicate detection.

## 9. Registry progress

| Specification field | Contract |
|---|---|
| 1 Purpose | Show jurisdiction resolution and bounded ACRA acquisition without implying live ACRA. |
| 2 Entry | Intake completion/start enters `REGISTRY`, or detail opens while current stage is Registry. |
| 3 Exit/navigation | Continue automatically on valid SG evidence; otherwise Registry unavailable/review/technical state. |
| 4 Visual layout | Pipeline rail plus main progress card using the original card/banner language. |
| 5 Header | Case UEN, resolved jurisdiction when available, `Registry verification`. |
| 6 Rails | Pipeline rail; Registry node `now`. |
| 7 Cards | Jurisdiction observations/resolution; selected registry route; operation progress/results. |
| 8 Tables | Optional compact operation table: entity profile, officers, ownership parties, relationships. |
| 9 Fields | Provider, environment, operation status, record count, retrieved time and safe evidence reference. |
| 10 Controls | None during automated work; no manual fake progression. |
| 11 Dialogs | None. |
| 12 Status indicators | `RUNNING`, operation `COMPLETE`/`EMPTY`/`FAILED`/`NOT_ATTEMPTED`; acquisition `COMPLETE`/`PARTIAL`/`FAILED`. |
| 13 Empty state | Valid empty officers is `EMPTY`, not an error. |
| 14 Error state | Separate business-review route issues from `TECHNICAL_FAILURE`. |
| 15 Loading state | Backend-authored current stage; polling only for `RUNNING`/`RESUMING`. |
| 16 Backend data | Jurisdiction resolution, registry route, acquisition bundle, operation results/issues/provenance. |
| 17 Backend mutation | None beyond the already-triggered server progression. |
| 18 Unsupported concepts | Live ACRA/ACRA+, ASIC, fabricated percentage ownership, retry timer or status stream not returned by backend. |
| 19 Truthful fallback | `ACRA Mock`/configured environment and `External access is backend-managed`. |
| 20 Responsive | Operation table becomes stacked status rows; pipeline rail becomes a horizontal/compact summary. |

## 10. Registry unavailable

| Specification field | Contract |
|---|---|
| 1 Purpose | Explain why registry processing stopped and what, if anything, the current POC permits. |
| 2 Entry | Unresolved/conflicting jurisdiction, foreign provider not implemented, ineligible identifier, registry review, partial acquisition, or technical failure. |
| 3 Exit/navigation | Back/start new; replacement only if relevant; no unsupported jurisdiction override. |
| 4 Visual layout | Original warning banner plus retained pipeline/case identity; do not redesign the page. |
| 5 Header | UEN and status; entity name only if actually available. |
| 6 Rails | Registry node attention/failed; downstream nodes pending. |
| 7 Cards | Observations, route decision, operation results and safe issue text. |
| 8 Tables | Registry operations where present. |
| 9 Fields | Issue code/message and provider/environment. |
| 10 Controls | Only server-advertised action; most registry/jurisdiction states expose none. |
| 11 Dialogs | No generic reviewer/override dialog unless a real route is later added. |
| 12 Status indicators | `WAITING_FOR_REVIEW` versus `TECHNICAL_FAILURE` must remain distinct. |
| 13 Empty state | `No registry provider selected` or `Provider not implemented`; never empty success. |
| 14 Error state | Safe message; no endpoint URL, raw payload or stack trace. |
| 15 Loading state | None after terminal stop; preserve last acquired safe evidence. |
| 16 Backend data | Active exception, safe evidence, registry issues, technical failure. |
| 17 Backend mutation | Currently none for jurisdiction conflict/foreign provider. |
| 18 Unsupported concepts | ASIC/live ACRA switch, manual provider selection, invented retry. |
| 19 Truthful fallback | `Recognised jurisdiction; registry provider not implemented in this Singapore-only POC.` |
| 20 Responsive | Warning/evidence stack; actions full-width only when needed. |

## 11. Confirm details

| Specification field | Contract |
|---|---|
| 1 Purpose | Compare canonical, Registry and document observations before any permitted decision. |
| 2 Entry | Registry/document evidence exists and reconciliation has been evaluated. |
| 3 Exit/navigation | Automatic continuation on all matches; explicit decision on allowed conflict; replacement for unusable evidence. |
| 4 Visual layout | Preserve original particulars/cards; add comparison rows inside that vocabulary, not a legacy-main panel. |
| 5 Header | Case identity and reconciliation status. |
| 6 Rails | Document/data band active when review is required. |
| 7 Cards | One per accepted field or one table with expandable provenance. |
| 8 Tables | Field, Registry, Document(s), outcome, confidence/validity, action. |
| 9 Fields | Legal name, registration identifier, registered address, country of incorporation. |
| 10 Controls | Only discrepancy `allowed_actions`; replacement upload for missing/invalid/unverifiable evidence. |
| 11 Dialogs | Optional confirmation dialog for consequential source selection; must show version-staleness behavior. |
| 12 Status indicators | `MATCH`, `CONFLICT`, `MISSING_IN_SOURCE`, `UNVERIFIABLE`, `INVALID`; never collapse them into generic mismatch. |
| 13 Empty state | `Reconciliation has not started` when absent. |
| 14 Error state | On HTTP 409, refresh authoritative evidence and show stale-decision message. |
| 15 Loading state | Fetch exact summary/documents; no inferred winner while loading. |
| 16 Backend data | Reconciliation field results, observations, validity, confidence, provenance, discrepancies, fingerprints and decisions. |
| 17 Backend mutation | Version/fingerprint-bound reconciliation resolution. |
| 18 Unsupported concepts | Arbitrary inline canonical editing; structured-address replacement from flat document; confidence-wins/latest-wins. |
| 19 Truthful fallback | No source is authoritative by default. Missing/invalid/unverifiable evidence requires replacement. |
| 20 Responsive | Each field becomes a stacked comparison card with outcome/actions kept adjacent. |

Outcome appearance: Match uses calm positive treatment; Conflict uses warning treatment and shows both usable values; Missing uses neutral-warning and identifies the missing source; Unverifiable shows confidence/provenance and replacement guidance; Invalid shows safe validation reason and replacement guidance. Colour must not be the sole signal.

## 12. Cases

| Specification field | Contract |
|---|---|
| 1 Purpose | Portfolio of backend-authored zero-touch cases without executing workflow work. |
| 2 Entry | `Cases` nav. |
| 3 Exit/navigation | Row click opens exact case; Home starts a new case. |
| 4 Visual layout | Title/subtitle, toolbar, bordered white table. |
| 5 Header | `Cases`. |
| 6 Rails | None. |
| 7 Cards | Table card only. |
| 8 Tables | Company, Registration ID, Jurisdiction, Status, Stage, Assigned to, Created, Updated. |
| 9 Fields | See classification below. |
| 10 Controls | Status filter, jurisdiction filter, search, row click. |
| 11 Dialogs | None. |
| 12 Status indicators | Exact automation statuses; stage progress derived from real stage bands. |
| 13 Empty state | `No cases match these filters.` |
| 14 Error state | `The case queue is unavailable.` with no mock fallback. |
| 15 Loading state | `Loading cases…`. |
| 16 Backend data | Lightweight case list; exact detail only when enrichment is intentionally chosen. |
| 17 Backend mutation | None. |
| 18 Unsupported concepts | Assignment/reviewer, true creation timestamp and jurisdiction in list response. |
| 19 Truthful fallback | `—` plus explanatory copy, or enrich from exact case detail. Do not silently present a dead filter. |
| 20 Responsive | Horizontal scroll or priority-column collapse; row remains keyboard-operable. |

| Column | Classification | Source / rule |
|---|---|---|
| Company | REAL | `legal_name`, fallback UEN |
| Registration ID | REAL | `requested_uen` |
| Jurisdiction | UNAVAILABLE IN LIST; REAL IN DETAIL | Requires detail enrichment or backend list DTO change |
| Status | REAL | `status` |
| Stage | DERIVED | `current_stage` mapped to approved visual bands |
| Assigned to | UNAVAILABLE | No assignment backend |
| Created | UNAVAILABLE IN LIST; REAL IN DETAIL | Detail has `created_at` |
| Updated | REAL | `updated_at` |

Current gap: the integration's jurisdiction filter changes local state but is not applied to the mapped cases and is not sent to the backend. It is a dead control. The integration also discards real list fields `active_exception_count`, `human_interventions` and `final_outcome`.

## 13. Case detail — running

| Specification field | Contract |
|---|---|
| 1 Purpose | Show exact server progression and accumulated evidence for one case. |
| 2 Entry | Cases row, retained Home case, or exact case link. |
| 3 Exit/navigation | Back to Cases; automatic refresh while running; Start new only from Home. |
| 4 Visual layout | 260 px pipeline rail plus flexible detail pane; preserve prototype order. |
| 5 Header | UEN, jurisdiction, legal name and exact status badge. |
| 6 Rails | Registry; Document and data; Readiness and Mock target. Do not add real Screening. |
| 7 Cards | Particulars, registry operations, documents, reconciliation, ownership/UBO, readiness, target and metrics. |
| 8 Tables | Officers, documents, reconciliation, relationships/candidates, target operations, timeline. |
| 9 Fields | All safe evidence described in section 5.3. |
| 10 Controls | Back only while actively running; polling is automatic. |
| 11 Dialogs | None in normal running state. |
| 12 Status indicators | Stage/current/completed bands; target operation states; document/ownership/reconciliation states. |
| 13 Empty state | Explicit `Not yet available` per downstream section. |
| 14 Error state | Poll warning does not erase last authoritative summary. |
| 15 Loading state | Initial full-case loading; background refresh without blanking known evidence. |
| 16 Backend data | Summary + documents + ownership; no provider calls caused by reads. |
| 17 Backend mutation | None during ordinary running. |
| 18 Unsupported concepts | Loop count, real screening, SLA countdown, production approval/risk. |
| 19 Truthful fallback | `Loop —`; `Screening not implemented in current backend` only if the visual band is retained by human choice. |
| 20 Responsive | Rail becomes compact top stepper; fixed 330/350 px columns stack; tables scroll. |

## 14. Case detail — attention/review

| Specification field | Contract |
|---|---|
| 1 Purpose | Explain each active business exception and expose only permitted resolution/recovery paths. |
| 2 Entry | `WAITING_FOR_REVIEW`. |
| 3 Exit/navigation | Supported decision auto-resumes; replacement/retry; back to Cases. |
| 4 Visual layout | Same detail skeleton with prominent warning cards above evidence. |
| 5 Header | Identity plus `WAITING FOR REVIEW`/product-friendly `Attention required`. |
| 6 Rails | Current affected stage marked attention. |
| 7 Cards | One active exception card with blocker codes, explanation, bounded evidence and available actions. |
| 8 Tables | Underlying evidence remains visible. |
| 9 Fields | exception ID hidden; visible stage, type, codes, explanation, source values, confidence, comparison, time. |
| 10 Controls | Server-advertised exception/reconciliation actions, exact replacement/retry, unsupported dialog disclosures. |
| 11 Dialogs | Assign/rework may remain visually present only as explicitly unavailable disclosures. |
| 12 Status indicators | Business exception is not a technical failure; resolved decisions retain outcome. |
| 13 Empty state | No action available: state replacement evidence or sponsor policy requirement. |
| 14 Error state | 409 refreshes; failed mutation retains case and safe message. |
| 15 Loading state | Disable mutation while refetching and do not show stale success. |
| 16 Backend data | Active exceptions + reconciliation + documents/ownership/readiness. |
| 17 Backend mutation | Exact resolve/reconciliation/replacement/retry routes only. |
| 18 Unsupported concepts | False-positive screening clearance, reviewer assignment, generic approve, generic rework. |
| 19 Truthful fallback | Disabled or disclosure-only controls with `Not available in current POC`. |
| 20 Responsive | Action buttons wrap/stack; evidence values remain readable without truncating source labels. |

## 15. Assign reviewer

| Specification field | Contract |
|---|---|
| 1 Purpose | Preserve prototype dialog placement while stating capability absence. |
| 2 Entry | User opens `Assign reviewer` from an exception card. |
| 3 Exit/navigation | Cancel/close only. |
| 4 Visual layout | Original centered 460 px dialog and dimmed backdrop. |
| 5 Header | Stage kicker; `Assign reviewer`; exception explanation. |
| 6 Rails | None. |
| 7 Cards | Dialog surface. |
| 8 Tables | None. |
| 9 Fields | Disabled reviewer select; optional note should also be disabled or explicitly labelled local draft if retained. |
| 10 Controls | Cancel enabled; Assign disabled. |
| 11 Dialogs | This screen is the dialog. |
| 12 Status indicators | `Reviewer assignment is not supported by the current backend.` |
| 13 Empty state | Reviewer list: `Not available in current POC`. |
| 14 Error state | Not applicable; no request should be sent. |
| 15 Loading state | None; do not call `/api/reviewers`. |
| 16 Backend data | None. |
| 17 Backend mutation | None; no endpoint exists. |
| 18 Unsupported concepts | Directory, workload count, assignee, authenticated role. |
| 19 Truthful fallback | Disclosure-only dialog. |
| 20 Responsive | Dialog width `min(460px, 100%)`; maintain focus trap/escape/close in implementation. |

## 16. Return for rework

| Specification field | Contract |
|---|---|
| 1 Purpose | Preserve prototype explanation structure without creating a case transition. |
| 2 Entry | User opens `Return for rework` from review state. |
| 3 Exit/navigation | Cancel/close only. |
| 4 Visual layout | Original dialog, reason, comment, field chips and actions. |
| 5 Header | Stage exception kicker; `Return for rework`. |
| 6 Rails | None. |
| 7 Cards | Dialog surface. |
| 8 Tables | None. |
| 9 Fields | Reason/comment/flag chips may be disabled or clearly labelled unsubmitted draft. |
| 10 Controls | Cancel enabled; Return disabled. |
| 11 Dialogs | This screen is the dialog. |
| 12 Status indicators | `Return for rework is not supported by the current backend.` |
| 13 Empty state | No evidence fields: omit chips. |
| 14 Error state | None; no speculative request. |
| 15 Loading state | None. |
| 16 Backend data | Exception evidence for display only. |
| 17 Backend mutation | None. |
| 18 Unsupported concepts | Reason persistence, comments, flagged-field workflow, assignee/client notification. |
| 19 Truthful fallback | Direct user to actual replacement/reconciliation controls outside the dialog. |
| 20 Responsive | Full-width fields and vertically stacked actions on small screens. |

## 17. Rework

| Specification field | Contract |
|---|---|
| 1 Purpose | Represent cases requiring new evidence without inventing `REWORK_REQUIRED`. |
| 2 Entry | `WAITING_FOR_REVIEW` with missing/invalid/unverifiable document evidence or retry-required failed document. |
| 3 Exit/navigation | Targeted retry/replacement, then backend re-evaluation/resume. |
| 4 Visual layout | Attention Case Detail with correction callout; not a new backend state. |
| 5 Header | `Attention required`; optionally `Replacement evidence required`. |
| 6 Rails | Document/data band active. |
| 7 Cards | Flagged document/field evidence and retained history. |
| 8 Tables | Current/superseded documents; reconciliation fields. |
| 9 Fields | Backend-authored blocker/evidence only. |
| 10 Controls | Retry failed document; replace current document. |
| 11 Dialogs | File chooser; no generic return/resubmit mutation. |
| 12 Status indicators | Backend state stays `WAITING_FOR_REVIEW` or `PENDING_INPUTS` after restart interruption. |
| 13 Empty state | Explain sponsor policy is required when no backend action exists. |
| 14 Error state | Keep same case and successful evidence after partial failure. |
| 15 Loading state | Per-file upload/reprocessing. |
| 16 Backend data | Documents, exceptions and reconciliation. |
| 17 Backend mutation | Retry/replacement only. |
| 18 Unsupported concepts | Generic returned-case owner, due date, client portal, `REWORK_REQUIRED`. |
| 19 Truthful fallback | Product label may say `Rework` while technical status remains visible/accessible. |
| 20 Responsive | One-column evidence and upload action. |

## 18. Corrections / replacement

| Specification field | Contract |
|---|---|
| 1 Purpose | Correct evidence through supported bounded paths. |
| 2 Entry | Current document or open reconciliation discrepancy. |
| 3 Exit/navigation | Re-evaluation and automatic continuation if blockers clear. |
| 4 Visual layout | Original document/evidence card with replace control and supersession history. |
| 5 Header | `Corrections and replacement evidence` or screenshot-confirmed wording. |
| 6 Rails | Document/data active. |
| 7 Cards | Current document, replacement input, prior superseded documents. |
| 8 Tables | Document state/type/provenance/event count; field comparison. |
| 9 Fields | New file only; no arbitrary registration/address/country edit. |
| 10 Controls | Replace current; retry failed; allowed reconciliation action. |
| 11 Dialogs | Optional confirmation before supersession. |
| 12 Status indicators | Current/superseded/failed/retry-required. |
| 13 Empty state | No retained bytes means download unavailable. |
| 14 Error state | Stale event count/409 refresh; invalid media remains an error. |
| 15 Loading state | Per-document upload and authoritative refresh. |
| 16 Backend data | Document ID/events/supersession links, reconciliation version/fingerprint. |
| 17 Backend mutation | Exact replacement, retry or reconciliation route. |
| 18 Unsupported concepts | Generic form resubmit, arbitrary master-data patch, raw file download. |
| 19 Truthful fallback | `Replacement evidence is required`; keep original evidence/history. |
| 20 Responsive | Upload control and file metadata stack; never hide version/error state. |

## 19. Pipeline rerun / recovery

| Specification field | Contract |
|---|---|
| 1 Purpose | Resume from a safe checkpoint without browser replay of target calls. |
| 2 Entry | `RECOVERY_PENDING` or restart-produced retry-required document state. |
| 3 Exit/navigation | Explicit resume may complete or return a real blocker/failure. |
| 4 Visual layout | Existing completion/warning banner in Case Detail. |
| 5 Header | `Recovery pending`; avoid `Rerun all`. |
| 6 Rails | Backend current stage. |
| 7 Cards | Retained outcome/target operations and recovery explanation. |
| 8 Tables | Target operation status evidence. |
| 9 Fields | None. |
| 10 Controls | `Complete safe recovery` -> resume. |
| 11 Dialogs | Optional confirmation explaining no target replay. |
| 12 Status indicators | `RECOVERY_PENDING`, `RESUMING`, final actual status. |
| 13 Empty state | No recovery action outside a recovery state. |
| 14 Error state | Retain recovery pending on repeat finalisation fault; uncertain target work is not replayed. |
| 15 Loading state | Disable action while resume is in flight; poll only `RESUMING`. |
| 16 Backend data | status, technical failure, target operations, timeline. |
| 17 Backend mutation | `POST .../resume`. |
| 18 Unsupported concepts | Full pipeline reset, deleting evidence, browser-side target retry. |
| 19 Truthful fallback | `Backend recovery is pending; target operations will not be replayed by the browser.` |
| 20 Responsive | Recovery banner stacks copy/action. |

## 20. Completed

| Specification field | Contract |
|---|---|
| 1 Purpose | Present real Mock workflow completion and retained evidence. |
| 2 Entry | Exact status `COMPLETED`. |
| 3 Exit/navigation | Onboarded projection, Client record, Audit, start another case. |
| 4 Visual layout | Completion banner plus full evidence/detail composition. |
| 5 Header | `Mock workflow completed` or screenshot-confirmed wording. |
| 6 Rails | All real bands cleared; no separate screening/approval clearance. |
| 7 Cards | Entity, documents, reconciliation, ownership, readiness, target outcome, metrics. |
| 8 Tables | Real evidence/timeline. |
| 9 Fields | Mock target party ID may be labelled `Mock GoldTier party ID`, never production Client ID. |
| 10 Controls | Navigate/export sanitized presentation if approved; no approve button. |
| 11 Dialogs | None. |
| 12 Status indicators | `COMPLETED`; `MOCK_GOLDTIER_SUBMITTED`; warnings remain visible. |
| 13 Empty state | Unsupported production fields show `—`/unavailable. |
| 14 Error state | Completion and technical failure are mutually exclusive. |
| 15 Loading state | Exact detail load. |
| 16 Backend data | Full summary/documents/ownership. |
| 17 Backend mutation | None. |
| 18 Unsupported concepts | Approval, production client ID, risk rating, next review, reviewer, production screening/scheduler. |
| 19 Truthful fallback | Persistent boundary copy: not Ready-for-Approval or production onboarding. |
| 20 Responsive | Completed evidence stacks; banner remains first. |

## 21. Onboarded

| Specification field | Contract |
|---|---|
| 1 Purpose | Product-friendly projection of completed zero-touch cases, not a production client master. |
| 2 Entry | `Onboarded` nav. |
| 3 Exit/navigation | Row click opens Client record. |
| 4 Visual layout | Title/caveat, filters/search, bordered table. |
| 5 Header | `Onboarded`. |
| 6 Rails | None. |
| 7 Cards | Table card. |
| 8 Tables | Client, Company, Jurisdiction, Risk, Onboarded, Next review. |
| 9 Fields | Company real; other classifications below. |
| 10 Controls | Jurisdiction/risk/search and row click. Unsupported filters should be disabled/explained unless detail enrichment supplies data. |
| 11 Dialogs | None. |
| 12 Status indicators | Only completed cases. |
| 13 Empty state | No completed cases or no matches. |
| 14 Error state | No mock fallback. |
| 15 Loading state | `Loading clients…`. |
| 16 Backend data | List, optionally exact detail enrichment. |
| 17 Backend mutation | None. |
| 18 Unsupported concepts | Client master, risk and scheduler. |
| 19 Truthful fallback | Preserve columns with `—` and page-level limitation copy, subject to human approval. |
| 20 Responsive | Horizontal scroll/priority columns; row click keyboard accessible. |

| Column | Classification |
|---|---|
| Client | UNSUPPORTED as production ID; optional real Mock GoldTier party ID requires detail fetch and explicit label |
| Company | REAL |
| Jurisdiction | REAL in detail, unavailable in list |
| Risk | UNSUPPORTED |
| Onboarded | DERIVED from completion timeline; current use of list `updated_at` is only an approximation |
| Next review | UNSUPPORTED |

## 22. Client record

| Specification field | Contract |
|---|---|
| 1 Purpose | Consolidated read-only case/evidence projection in the original client-record layout. |
| 2 Entry | Completed-case row. |
| 3 Exit/navigation | Back to Onboarded; per-case Audit. |
| 4 Visual layout | 284 px side rail plus two-column main detail; preserve section order where truthful. |
| 5 Header | Mock/case identity, UEN, jurisdiction and company. |
| 6 Rails | Case ID/status/completion/jurisdiction; schedule unavailable; documents with disabled download. |
| 7 Cards | Particulars, capital/activity, directors, provisional UBO, relationship, onboarding record/checks/history. |
| 8 Tables | Directors, UBO candidates, stages and checks. |
| 9 Fields | Classification below. |
| 10 Controls | Back, Audit; sanitized JSON export only if approved; raw document download/start review disabled. |
| 11 Dialogs | None. |
| 12 Status indicators | Mock completed/provisional UBO; no approval/risk. |
| 13 Empty state | Per-section unavailable copy, not fabricated rows. |
| 14 Error state | Exact case/evidence unavailable banner. |
| 15 Loading state | Concurrent case/documents/ownership loading. |
| 16 Backend data | Canonical entity, acquisition, documents, ownership, metrics and timeline. |
| 17 Backend mutation | None. |
| 18 Unsupported concepts | Production client master, raw download, review initiation, schedule and relationship/contact business data. |
| 19 Truthful fallback | `Not available in current POC`; preserve prototype placement where useful. |
| 20 Responsive | Side rail becomes top summary; 352 px column stacks; tables scroll. |

| Field group | Classification |
|---|---|
| Case ID, UEN, company, jurisdiction, entity type/status/date/address | REAL BACKEND DATA |
| Officers: name/role/appointment/cessation/country/source | REAL BACKEND DATA |
| Document names/types/states/provenance/confidence/supersession | REAL BACKEND DATA; raw bytes unavailable |
| Ownership parties/relationships/paths/percentages/classifications/issues | REAL BACKEND DATA; labels must say provisional |
| Workflow stages, metrics, target operations and timelines | REAL BACKEND DATA |
| Display address string, stage rows, elapsed display | DERIVABLE PRESENTATION DATA |
| Completion date from `MOCK_SUBMISSION_COMPLETED` event | DERIVABLE PRESENTATION DATA |
| Production Client ID, risk, next review, re-screening, tax residency, annual volume | UNSUPPORTED CURRENT POC |
| Principal business/activity/capital/contact/relationship fields not in DTO | PROTOTYPE-ONLY unless a future authoritative source is added |
| Production approval/onboarded-by | PROTOTYPE-ONLY / MUST NOT BE CLAIMED |

## 23. Audit

| Specification field | Contract |
|---|---|
| 1 Purpose | Present safe per-case workflow history, optionally aggregated for the current POC portfolio. |
| 2 Entry | `Audit` nav or Client record `Audit trail`. |
| 3 Exit/navigation | Nav or clear case filter. |
| 4 Visual layout | Header/actions, filter chips, bordered table. |
| 5 Header | Page `Audit trail`; top nav `Audit`. |
| 6 Rails | None. |
| 7 Cards | Table card. |
| 8 Tables | Timestamp, Action, By, Change, Loop. |
| 9 Fields | Timestamp/event type/message real; actor/loop unavailable. |
| 10 Controls | Case clear, action filter, disabled CSV export. |
| 11 Dialogs | None. |
| 12 Status indicators | Event type/action badge. |
| 13 Empty state | `No entries match this filter.` |
| 14 Error state | Case/list/detail read error; no local/fake entries. |
| 15 Loading state | `Loading audit trail…`. |
| 16 Backend data | Per-case onboarding, CLM and automation timelines as selected by adapter. |
| 17 Backend mutation | None. |
| 18 Unsupported concepts | Authenticated actor, loop, compliance-grade global audit, pagination/export endpoint. |
| 19 Truthful fallback | `By —`, `Loop —`; disabled `Export CSV` with explicit availability message. |
| 20 Responsive | Table scroll or stacked event rows; preserve timestamp/action/change priority. |

Current global aggregation performs a list call followed by one detail call per case. This is acceptable only for the small POC and must not be described as a global audit service.

## 24. Policy

| Specification field | Contract |
|---|---|
| 1 Purpose | Read-only explanation of current connector/runtime profile and open policy boundaries. |
| 2 Entry | Hidden internal route unless Shane approves visible navigation. |
| 3 Exit/navigation | Normal nav. |
| 4 Visual layout | Jurisdiction table left; pipeline/roles/scheduler/execution cards right. |
| 5 Header | `Policy and rules`. |
| 6 Rails | None. |
| 7 Cards | Pipeline, roles, scheduler, execution profile. |
| 8 Tables | Jurisdiction rules and key/value policy cards. |
| 9 Fields | Classified below. |
| 10 Controls | Read-only; no editing. |
| 11 Dialogs | None. |
| 12 Status indicators | Implemented vs not implemented; POC/pending/unavailable labels. |
| 13 Empty state | Loading/unavailable profile. |
| 14 Error state | `Policy is unavailable.`; no mock fallback. |
| 15 Loading state | `Loading policy…`. |
| 16 Backend data | `GET /api/system/execution-profile`. |
| 17 Backend mutation | None. |
| 18 Unsupported concepts | Screening threshold, reviewer/RBAC policy, schedules, staleness, source precedence, editable policy. |
| 19 Truthful fallback | `Pending sponsor confirmation` or `Not available in current POC`, not invented values. |
| 20 Responsive | Jurisdiction table scroll; cards stack; fixed 360 px rail removed. |

| Policy value | Classification |
|---|---|
| Registry system/environment | REAL |
| IDP system/environment/provider | REAL |
| Document confidence threshold | REAL runtime value, but project-defined/provisional |
| Ownership system/environment | REAL |
| UBO threshold | REAL runtime value, but project-defined/provisional pending Q-004 |
| Target system/environment | REAL and Mock-only |
| Persistence mode | REAL |
| SG/ACRA implemented | DERIVED from current route/domain contract and profile |
| AU/MY/HK recognised but provider not implemented | DERIVED from jurisdiction domain, not from execution-profile response alone |
| Pipeline stages | DERIVED from backend state enum |
| Screening auto-clear | PENDING SPONSOR / NOT IMPLEMENTED |
| Source precedence/reviewer authority | PENDING SPONSOR under Q-015 |
| Live ACRA endpoint/auth | PENDING SPONSOR under Q-012 |
| Reviewer count/self-review policy | NOT AVAILABLE / PENDING SPONSOR |
| Next-review/re-screening schedules | NOT AVAILABLE |
| Registry staleness policy | NOT AVAILABLE |

## 25. Responsive design

The reference `design-system.css` has no media rules for the new `nav`, `ds-two-col`, `side-panel`, `ds-page`, or wide UI V2 tables. Existing `styles.css` media queries mainly target the older main UI classes. Therefore responsiveness is a required remediation, not a verified property.

| Breakpoint intent | Required behavior |
|---|---|
| Desktop ≥ 1100 px | Preserve reference header, side rails, two-column cards and full tables. |
| Tablet 761–1099 px | Allow nav/account wrapping; stack fixed secondary columns; keep rail compact; enable table overflow. |
| Mobile ≤ 760 px | Brand/account first row, scrollable or wrapped nav second row; side rail becomes top stepper/summary; all `ds-two-col` regions stack; page padding reduces; buttons remain content-width except primary flow actions. |
| Narrow mobile ≤ 480 px | Dialogs full-width within safe padding; field/action rows stack; tables use horizontal scroll or labelled cards; no fixed 260/284/320/330/350/352/360/380/420 px widths. |

Touch targets, keyboard row activation, visible focus, dialog focus containment, non-colour status labels, and no horizontal viewport overflow are acceptance requirements.

## 26. Backend capability inventory

### User-facing capabilities that must be represented

- Early case creation and exact case read.
- Jurisdiction observations/resolution and safe foreign-provider stop.
- Four-operation registry acquisition with officers, ownership parties, relationships, partial/empty/error semantics and provenance.
- Independent multi-document PDF/DOCX/TXT intake, explicit completion, count/size/total limits and same-case retry.
- Current/superseded document history, provider/environment/confidence/provenance and field evidence.
- Source-neutral reconciliation with all five outcomes and stale-safe decisions.
- Deterministic ownership/UBO parties, relationships, paths, percentages, threshold, candidates and issues.
- Readiness statuses, blockers, warnings and Mock submission plan.
- Business exceptions distinct from technical failure.
- Target operation evidence for Search/Shell/Policy/Amend.
- Resume/recovery and replay-prevention state.
- Process-local or Mongo-backed durable POC label.
- Read-only case list/review population and per-case timelines.
- Demo scenarios/UAT evidence only behind explicit demo gates.

### Capabilities added after the original UI prototype that the current integration underexposes

The integration handles the mutations but underexposes the depth of registry acquisition, document field evidence, reconciliation provenance/validity, ownership graph/path evidence, readiness blockers/warnings, metrics and list summary values. Durable recovery is shown at a high level; interrupted-document `DOCUMENT_REUPLOAD_REQUIRED` needs a clearer targeted UI state. PR #21 changes only the dormant ACRA BizFile Mock connector security boundary and adds no new user-facing route.

## 27. UI functionality inventory

| UI concept | Classification against latest main |
|---|---|
| Create zero-touch case | REAL BACKEND FUNCTION |
| Multi-file/folder selection | DISPLAY/CLIENT INTAKE FUNCTION; files upload individually |
| Intake, targeted retry, completion | REAL BACKEND FUNCTION |
| Registry/canonical/officer display | REAL BACKEND FUNCTION |
| Case list/detail | REAL BACKEND FUNCTION |
| Reconciliation decisions | REAL BACKEND FUNCTION |
| Replacement/retry/resume | REAL BACKEND FUNCTION |
| Ownership/UBO/readiness/target/timeline | REAL BACKEND FUNCTION, currently partial display |
| Search/filter/table sort presentation | DISPLAY/DERIVED; backend supports only status filter on case list |
| `/api/cases`, `/api/clients`, `/api/audit`, `/api/reviewers`, `/api/policy` | FAKE/PROTOTYPE ROUTES; must never be called |
| Assign reviewer | UNSUPPORTED CURRENT POC |
| Return for rework | UNSUPPORTED CURRENT POC |
| Generic resubmit | UNSUPPORTED CURRENT POC |
| Screening/false-positive clearance | PROTOTYPE-ONLY |
| Production risk/approval/client/scheduler | PROTOTYPE-ONLY |
| Audit CSV | UNSUPPORTED CURRENT POC |
| Sanitized local JSON export | PRESENTATION FUNCTION only; human approval required |
| Raw document download | UNSUPPORTED; bytes are not retained |
| Account/login | VISUAL REQUIREMENT; authentication unsupported |

## 28. Master UI ↔ Backend matrix

| Screen | Visual element/control | User action / expected UI state | Latest backend capability | Endpoint/function | Request / response | Supported? | Adapter needed? | Truthful unsupported behavior | Test required |
|---|---|---|---|---|---|---|---|---|---|
| Global | Home tab | Show intake without mutation | Presentation | None | Local state | Yes | No | N/A | Nav/active/focus |
| Global | Cases tab | Show list | List | `GET /api/clm/zero-touch/cases` | status query -> list items | Yes | Yes | N/A | Load/error/no fallback |
| Global | Onboarded tab | Show completed projection | List filter | same with `status=COMPLETED` | list items | Yes, derived | Yes | Boundary copy | Only completed rows |
| Global | Audit tab | Show timeline projection | List + detail reads | list/detail GET | summaries -> events | POC-only aggregation | Yes | Not compliance-grade | N+1/error/filter |
| Global | Policy tab | Hidden/read-only | Profile | profile GET | profile -> policy view | Yes, if exposed | Yes | No editor | Visibility decision |
| Global | Account | Open info popover | No identity backend | None | Local disclosure | Visual only | Yes | `Authentication pending` | No auth claim |
| Global | Environment pill | Show real modes | Profile | profile GET | profile | Yes | Small label | Loading/unavailable | Exact labels |
| New onboarding | Jurisdiction | Select/omit | Jurisdiction gateway | create case | JSON -> summary | Yes | No | AU/MY/HK stop safely | All values/conflict |
| New onboarding | UEN | Enter uppercase ID | Validation | create case | JSON -> summary | Yes | No | Inline safe validation | grammar/blank |
| New onboarding | Drop/browse | Add files | Local selection | None | File objects | Yes | Yes | Reject invalid | MIME/ext/size |
| New onboarding | Folder | Add ordinary files | Local selection only | None | File objects | Yes | Yes | No server folder traversal | folder/mixed files |
| New onboarding | Remove | Remove before create | Local selection | None | Local state | Yes | No | N/A | total/count update |
| New onboarding | Create | Create early, upload independently, complete | Real | create/intake/complete | JSON/raw/JSON -> records/summary | Yes | Yes | Retain case on partial failure | sequence/partial |
| New onboarding | Retry selection | Retry only failed file | Real | failed-document retry | raw -> document | Yes | Yes | Same case ID | no duplicate accepted upload |
| Registry | Progress rail | Show real stage/operations | Real detail | case GET | summary | Yes | Yes | No fake timer | running/poll stop |
| Registry | Operation rows | Show four statuses/issues | Acquisition data | case GET | acquisition bundle | Yes | Yes | Unavailable until returned | empty/partial/fail |
| Registry unavailable | Action area | Only advertised action | Exception model | resolve if advertised | guarded JSON -> summary | Conditional | Yes | Otherwise no action | registry/jurisdiction states |
| Confirm | Comparison rows | Inspect sources | Reconciliation | detail GET | reconciliation | Yes | Yes | No source precedence | five outcomes |
| Confirm | Keep Registry | Decide current conflict | Real | reconciliation resolve | versions/fingerprint -> summary | Yes when advertised | Yes | Hidden/disabled otherwise | 409/stale |
| Confirm | Use Document | Legal-name only | Real | reconciliation resolve | guarded JSON -> summary | Yes when advertised | Yes | Not for ID/address/country | action scope |
| Confirm | Request information | Prototype wording | Reserved enum, never advertised | None in practice | None | No | No | Disabled/absent | ensure never sent |
| Cases | Status filter | Server-filter real statuses | Real | list GET | query -> list | Yes | No | Exact statuses only | every status |
| Cases | Jurisdiction filter | Filter cases | Not in list endpoint | None | None | Not with current list DTO | Detail enrichment/backend DTO | Disable/explain until real | dead-control test |
| Cases | Search | Client-filter name/UEN/ID | Local display | None | Local | Yes | Yes | N/A | case-insensitive |
| Cases | Row | Open exact case | Real | detail GET | ID -> summary | Yes | No | Error state | keyboard/click |
| Case detail | Back | Return to list | Local navigation | None | Local | Yes | No | N/A | state restore |
| Case detail | Pipeline | Map stages | Real states | detail GET | summary | Yes | Yes | No real Screening | all states |
| Case detail | Exception evidence | Show codes/values/confidence | Real | detail GET | exceptions | Yes | Yes | N/A | bounded evidence |
| Case detail | Exception action | Resolve only advertised action | Real | exception resolve | versions -> summary | Yes | Yes | No generic approve | 409/403-like errors |
| Case detail | Assign reviewer | Open visual dialog | No backend | None | None | Disclosure only | Yes | Disabled submit | no request test |
| Case detail | Return for rework | Open visual dialog | No backend | None | None | Disclosure only | Yes | Disabled submit | no request test |
| Case detail | Retry failed document | Upload targeted evidence | Real | intake retry | raw -> document | Yes | Yes | Only failed/current record | retry ID binding |
| Case detail | Replace document | Supersede current | Real | replacement | event-count header/raw -> summary | Yes | Yes | No overwrite | stale/current/superseded |
| Case detail | Reconciliation action | Guarded decision | Real | reconciliation resolve | versions/fingerprint -> summary | Yes | Yes | Server actions only | 409 refresh |
| Case detail | Resume | Safe recovery | Real | resume POST | ID -> summary | Yes in recovery state | No | Hide otherwise | no target replay |
| Case detail | Readiness/target | Inspect statuses | Real | detail GET | readiness/target ops | Yes | Yes | Mock-only copy | blockers/warnings/ops |
| Case detail | Timeline | Inspect safe history | Real | detail GET | events | Yes | Yes | Actor/loop unavailable | order/timestamps |
| Rework | Resubmit | Restart all stages | No route/state | None | None | No | No | Map only to retry/replacement/resume | no speculative call |
| Completed | Completion banner | Show Mock completion | Real | detail GET | summary | Yes | Yes | Not approval | boundary text |
| Onboarded | Jurisdiction filter | Filter completed cases | Detail-only data | detail GET enrichment | summaries | Conditional | Yes | Disable if not enriched | filter truth |
| Onboarded | Risk filter | Filter by risk | No risk data | None | None | No | No | Disable/explain | no fabricated risk |
| Onboarded | Search/row | Find/open completed case | Real list/detail | GETs | list/detail | Yes | Yes | N/A | only completed |
| Client | Audit link | Open case audit | Real timeline | detail GET | summary | Yes | Yes | Per-case only | route/filter |
| Client | Document download | Download evidence bytes | Bytes not retained | None | None | No | No | Disabled/explained | no fake file |
| Client | Export record | Download sanitized view | Presentation only | None | Local JSON | Conditional | Yes | Must say sanitized POC export | payload whitelist |
| Client | Start a review | Create review | No backend | None | None | No | No | Disabled/explained | no request |
| Audit | Action chips | Filter mapped events | Local display | None after read | Local | Yes | Yes | Only real event types | filter mapping |
| Audit | Clear case | Aggregate current portfolio | Read-only list/detail | GETs | summaries | POC-only | Yes | Not global compliance audit | multi-case/error |
| Audit | Export CSV | Download audit | No endpoint | None | None | No | No | Disabled/explained | no request |
| Policy | Profile fields | Inspect runtime | Real | profile GET | profile | Yes | Yes | Mark provisional values | value classification |
| Policy | Screening/roles/scheduler | Inspect prototype slots | No backend | None | None | No | Yes | Pending/unavailable | no numeric invention |
| Demo | Scenario/run | Run synthetic demo | Real gated demo | `/api/demo/...` | gated requests | Yes, demo only | Yes | Hidden normal runtime | dual gate |
| Demo | UAT evidence | Export safe JSON | Real gated demo | UAT evidence GET | whitelisted JSON | Yes, demo only | Yes | Hidden normal runtime | whitelist/no raw data |
| Backend-only | Legacy staged onboarding/CLM | Not required in sponsor UI V2 | Real compatibility APIs | onboarding/CLM routes | domain DTOs | Yes, not mounted | No | Document as compatibility | regression tests |
| Backend-only | Field accept/reject/correct | Legacy local review | Real legacy route | document reviews POST | review -> document | Yes, policy-limited | Decision required | Do not mix with zero-touch authority | review policy tests |
| Backend-only | Ownership load/analyze/UBO list | Normal zero-touch automates it | Real | ownership routes | records | Yes, not manual UI | No | Demo/manual controls gated | orchestration regression |

## 29. Unsupported prototype concepts

- `/api/cases`, `/api/clients`, `/api/audit`, `/api/reviewers`, `/api/policy`.
- Assignment, assignee, reviewer directory/workload and authenticated reviewer identity.
- Return-for-rework mutation, persisted reasons/comments/flagged fields and a `REWORK_REQUIRED` status.
- Generic `resubmit` or full pipeline rerun.
- `SCREENING`, sanctions/PEP result, false-positive clearance and screening threshold.
- Risk rating, approval, Ready-for-Approval, production customer/client ID and approval actor.
- Scheduler, next review, periodic re-screening and registry refresh policy.
- Compliance-grade global audit and CSV export.
- Raw document download, because bytes are not retained.
- Production client master, CRM relationship/contact/capital/activity fields absent from canonical sources.
- Live ACRA/ACRA+, ASIC or other live foreign registry behavior.

## 30. Current integration gaps

| Gap type | Finding |
|---|---|
| MISSING VISUAL ELEMENT | Screenshot-asserted account/signed-in area is absent. |
| MISSING VISUAL ELEMENT | No dedicated Registry progress, Registry unavailable or Confirm details screen composition. |
| WRONG/MISSING LABEL | `Readiness and approval` remains in `HomeOnboarding` while shared Case Detail says `Readiness and Mock target`; approval language is unsafe. |
| WRONG SCREEN STRUCTURE | Case Detail adds required data but compresses much of it into dense inline JSX/tables and omits the fuller evidence hierarchy expected by the contract. |
| MISSING FUNCTION | Cases jurisdiction filter does nothing. |
| MISSING FUNCTION | Real list fields active-exception count, human interventions and final outcome are discarded. |
| MISSING FUNCTION | No clear UI for interrupted-document `DOCUMENT_REUPLOAD_REQUIRED` beyond generic failed-document retry. |
| MISSING FUNCTION | Demo UAT evidence handler exists but is not mounted; acceptable only if intentionally excluded. |
| INCORRECT FUNCTION | Onboarded jurisdiction selection filters all rows because the mapped list jurisdiction is always null; risk selection intentionally filters all rows but looks like a real filter. |
| UNSUPPORTED PRESENTED AS REAL | Assign reviewer and Return for rework launch buttons look active before the dialog reveals no backend support. |
| BACKEND FUNCTION NOT EXPOSED | Registry operation result detail/issues/provenance. |
| BACKEND FUNCTION NOT EXPOSED | Document fields, confidence, comparison, provider/environment/provenance and event history in Case Detail. |
| BACKEND FUNCTION NOT EXPOSED | Reconciliation observation validity/confidence/provenance and recorded decisions in Case Detail. |
| BACKEND FUNCTION NOT EXPOSED | Ownership parties, relationships, paths, threshold/comparator and provenance in Case Detail. |
| BACKEND FUNCTION NOT EXPOSED | Readiness blockers/warnings, submission plan/receipt, metrics and real list summary fields. |
| OLD-MAIN UI LEAKAGE RISK | Large legacy components remain exported in `App.tsx`; they are not mounted, but final remediation must keep them out of the UI V2 route tree. |
| RESPONSIVE GAP | Fixed widths and missing UI V2 media rules will overflow or compress poorly. |

## 31. Visual gaps

1. Screenshot baseline is missing; visual acceptance cannot be closed.
2. Account area is missing from both reference and integration nav.
3. Environment banner currently occupies the entire trailing position; account and environment need an approved hierarchy.
4. Header, nav labels and Policy visibility cannot be reconciled to screenshots.
5. Registry/confirm/rework/completed states are currently variants of generic banners/details rather than verified screenshot compositions.
6. Status language is inconsistent: `Readiness and approval` versus `Readiness and Mock target`.
7. Unsupported columns/actions lack consistent disabled/unavailable styling.
8. Wide tables and fixed rails lack a complete responsive design.
9. Case Detail's dense single-line JSX structure makes visual preservation and maintainability fragile even though it uses the reference CSS vocabulary.

## 32. Functional gaps

1. Fix or disable/enrich Cases jurisdiction filtering.
2. Use or deliberately omit `active_exception_count`, `human_interventions` and `final_outcome`.
3. Do not present Onboarded risk/jurisdiction filters as operational unless data is loaded.
4. Expand exception evidence and blocker display.
5. Expand registry/document/reconciliation/ownership/readiness/metrics/target projections.
6. Make assignment/rework entry points explicitly unavailable before click or label them as prototype disclosures.
7. Distinguish targeted retry, replacement, reconciliation resolution and resume from unsupported generic resubmit/rerun.
8. Define whether legacy field review belongs in UI V2; it must not silently become master-data authority.
9. Define sanitized Client export scope; current local view-model JSON export is not a backend audit/export capability.
10. Add a deliberate interrupted-document/re-upload-required recovery state.
11. Ensure unsupported `REQUEST_ADDITIONAL_INFORMATION` is never sent; the enum is reserved and not server-advertised.
12. Maintain 409 authoritative refresh across all guarded mutations.

## 33. Required final remediation

1. Obtain/freeze all original screenshots and give each an ID, viewport and expected state.
2. Reconcile exact brand/nav/account pixels and wording against those screenshots.
3. Add the approved truthful POC account treatment without inventing authentication.
4. Unify stage bands and remove approval/screening implications not backed by states.
5. Preserve the onboarding two-card composition while completing create/intake/retry/complete progress feedback.
6. Add explicit Registry progress, Registry unavailable and Confirm details states using existing cards/banners.
7. Correct dead/unsupported filters and decide whether detail enrichment or a list-DTO change is preferred.
8. Expand Case Detail to expose the safe latest-main evidence inventory.
9. Keep assignment/rework dialogs as unavailable visual prototypes or remove their launch controls per human decision.
10. Map rework-like visuals only to retry/replacement/reconciliation/resume; add no generic resubmit route.
11. Make Completed/Onboarded/Client language explicitly Mock/POC and preserve unavailable production fields truthfully.
12. Keep Audit per-case/POC scoped and CSV disabled.
13. Keep Policy read-only, classify every value and keep Q-012/Q-015 visible.
14. Implement responsive rules for every UI V2 layout primitive.
15. Add the tests in section 34, then run the full required project checks without staging/committing unless separately instructed.

## 34. Proposed test matrix

| Test area | Required cases |
|---|---|
| Screenshot regression | Every supplied state at approved desktop/tablet/mobile viewport; account/header/nav pixel comparison |
| Shell | Brand, exact labels/order, active underline, Policy visibility, account copy/popover, environment separation |
| Intake validation | PDF/DOCX/TXT; MIME-extension mismatch; empty/oversize; 20/21 files; 25 MiB boundary; duplicate selection; folder files |
| Intake orchestration | Early case retained; independent uploads; partial failure; exact failed ID retry; explicit count completion; no successful-file replay |
| Registry | unresolved/conflict/foreign stop; complete/empty/partial/failed operations; safe provenance; no downstream call after stop |
| Reconciliation | all five outcomes; legal-name use-document only; keep-registry scopes; no action for unusable evidence; stale 409 refresh |
| Cases | every real status; search; live/disabled jurisdiction filter; real/placeholder columns; row keyboard/click; no provider side effects |
| Case detail | running/review/recovery/technical/completed; documents/supersession; ownership paths/issues; readiness blockers/warnings; target ops; timeline |
| Unsupported actions | assign/rework/resubmit/screening/CSV/start-review/raw download send zero requests and show explicit availability text |
| Recovery | interrupted document targeted retry; recovery pending; resume; no browser target replay; retained outcome finalisation only |
| Completed/Onboarded/Client | only completed cases; no production ID/risk/reviewer/schedule; Mock party ID label if approved; sanitized export whitelist |
| Audit | per-case events; POC portfolio aggregation; actor/loop `—`; event filtering; CSV disabled |
| Policy | real profile values; provisional/pending/unavailable classifications; Q-012/Q-015 copy; no editing |
| Error handling | network, 400, 404, 409, 422, 500/503; no mock fallback/fake success/raw response body |
| Accessibility | landmarks, headings, labels, dialog focus/escape, keyboard rows, focus visibility, non-colour states, touch targets |
| Responsive | 1280, 1024, 760, 480 and narrow viewport; no fixed-width overflow; table strategy; account/nav wrapping |
| Regression/security | frontend type/lint/test/build; backend/contract/phase tests; secrets/dependency/whitespace checks; no sensitive logs or raw evidence |

## 35. Acceptance criteria for final implementation

- Every supplied screenshot has an identified implemented state and visual regression test.
- Global shell matches the approved screenshot contract, including truthful account treatment.
- Every interactive control is either connected to a registered latest-main function, intentionally local presentation behavior, or visibly disabled with an explanation.
- No speculative route or mock fallback exists in normal runtime.
- Every user-relevant latest-main capability is visible, intentionally automated, or documented as a compatibility/demo/internal endpoint.
- All actual automation statuses/stages render without invented screening/risk/approval states.
- All five reconciliation outcomes and server-advertised actions render correctly with concurrency guards.
- Intake limits, file formats, partial failure, targeted retry, replacement and explicit completion are correct.
- Business exception, technical failure and recovery are visually/semantically distinct.
- Completed/Onboarded/Client views make no production approval/client/risk/scheduler claim.
- Audit is explicitly POC/per-case and contains no invented actor/loop/export.
- Policy values are real, derived, pending or unavailable—never fabricated.
- Account language makes no authentication/reviewer claim.
- Desktop/tablet/mobile layouts pass visual and accessibility acceptance.
- Relevant frontend/backend/contract/security checks pass with no skipped check misreported as success.

## 36. Open sponsor dependencies

- **Q-012:** authoritative ACRA Business Profile operation/auth/error/TLS/access contract; blocks live ACRA claims and exact live registry UI semantics.
- **Q-015:** jurisdiction/source precedence and authenticated review authority; blocks authoritative source/reviewer wording.
- **Q-001:** real Ready-for-Approval transition.
- **Q-002:** seeded hierarchy retrieval contract.
- **Q-003:** final document types/fields.
- **Q-004:** sponsor-approved UBO rule.
- **Q-005:** validation/master-data responsibility split.
- **Q-006/Q-007:** related-party semantics and Singapore mapping sign-off.
- **Q-008:** safe GoldTier authentication material and sandbox details.
- **Q-013:** document privacy/retention/upload security policy.
- **Q-014:** confidence, reviewer role, authentication and audit policy.

These dependencies do not block truthful Mock UI work, but they block production/authenticated/approval language and several prototype actions.

## 37. Human decisions required before implementation

1. Supply or identify the original UI screenshots and confirm their viewport/order.
2. Confirm whether screenshot wording overrides branch wording for brand, Home/New onboarding, Audit/Audit trail and Policy visibility.
3. Approve account text and behavior: recommended `Local POC operator` + `Authentication pending` + informational-only dropdown.
4. Decide whether the environment profile is beside, below or inside the account region.
5. Approve three truthful pipeline bands or require a visually retained but explicitly unsupported Screening band.
6. Decide whether unsupported prototype columns remain visible with placeholders or are removed.
7. Decide whether Cases/Onboarded list enrichment may fetch exact detail per row or whether the backend list DTO should be extended in a later scoped task.
8. Decide whether assignment/rework launch controls remain as disclosure dialogs or are visibly disabled in place.
9. Decide whether the legacy unauthenticated field-review endpoint belongs in the final zero-touch UI; replacement/reconciliation is the safer default.
10. Decide whether the Client `Export record` local sanitized JSON action is wanted and approve its field whitelist.
11. Decide whether a real Mock GoldTier party ID should appear and approve the exact label `Mock GoldTier party ID`.
12. Confirm that `Onboarded` may mean completed Mock workflow cases with a permanent POC disclaimer.
13. Decide whether Policy remains hidden, becomes a nav item, or is linked from an informational account/system menu.
14. Approve responsive behavior for side rails/tables/nav/account and target viewports.
15. Confirm whether external Google font loading is acceptable for the demo or fonts must be bundled/system-fallback-only.

## HUMAN APPROVAL CHECKLIST

- [ ] All original screenshots are supplied, identified and approved as the visual baseline.
- [ ] Exact brand, navigation labels/order and Policy visibility are approved.
- [ ] Exact account text, account name, dropdown behavior and environment placement are approved.
- [ ] Truthful pipeline bands are approved; no unsupported Screening/Risk/Approval stage is presented as real.
- [ ] Registry progress, Registry unavailable and Confirm details compositions are approved.
- [ ] Cases/Onboarded unavailable columns and filter strategy are approved.
- [ ] Assignment and Return-for-rework disclosure behavior is approved.
- [ ] Retry, replacement, reconciliation and recovery wording is approved instead of generic resubmit/rerun.
- [ ] Completed/Onboarded/Client Mock/POC boundary language is approved.
- [ ] Optional Mock GoldTier party-ID presentation is approved or rejected.
- [ ] Sanitized Client JSON export is approved or rejected.
- [ ] Audit and Policy visibility/scope are approved.
- [ ] Responsive breakpoints and table/rail behavior are approved.
- [ ] External font-loading policy is approved.
- [ ] Q-012 and Q-015 remain visibly open and no implementation copy implies they are resolved.

UI V2 SCREEN & FUNCTION CONTRACT READY FOR HUMAN REVIEW
