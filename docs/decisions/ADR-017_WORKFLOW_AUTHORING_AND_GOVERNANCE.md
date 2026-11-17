# ADR-017: Workflow authoring, approval and the required-obligation ratchet (P2/P3)

## Status

**Proposed.** Owner-approved as the design for P2/P3 on 2026-11-15:
- revision R1
- decisions RD-1 to RD-6
- the G0 conditions
- the conditional-write dispatch fence, as the revised D10 mechanism
- the G0 remediation rulings
- the G0 R3 rulings of 2026-11-16, including RD-5 counts as maxima
- the G0 R4 rulings of 2026-11-16

This ADR is a design record only:
- **Nothing in it is implemented.** Current behaviour is unchanged.
- It is not sponsor-confirmed.
- Authority: `USER_AUTHORIZED_POC`.

Implementation needs separate phase approvals, starting with P2-0 (§7). Decision record: D-135 in
[DECISION_LOG](DECISION_LOG.md).

**Extends:**
- ADR-014 (Director-managed workflows)
- ADR-016 (read-only designer)

**Supersedes, when implemented:**
- D-123 W1 (roles) and W4 (versions), in part
- the owner's interim F2 publication restriction

**Amends D-136 E2 when P2-0 ships** (§3.6). D-136 is otherwise preserved in full.

## Date

2026-11-15

## Context

- Today a Director authors and activates workflow versions alone (D-123 W1). Activation
  publishes immediately, with no proposal, second person or comparison against the active
  version. The interim owner rule (D-136 E5, and F2) forbids removing or weakening required
  stages, but nothing enforces it.
- D-136 E6 records two open risks:
  - **R1:** a publication is not serialised with the start of a GoldTier write.
  - **R2:** a case sent through the legacy CLM routes is not counted as sent.
- The workflow audit silently drops events beyond 256.
- The backend runs as **one process per store**. D-124 S9 and startup recovery both assume it.
- The owner requires:
  - HR authors workflow changes.
  - Exactly one authorised Director approves or rejects each one.
  - This governance applies to every workflow.
  - Directors do not author ordinary changes.
  - Mandatory onboarding stages stay fixed.
  - Required stages are never removed, skipped, bypassed or weakened.
  - Existing roles, case access, policy authority, identity provenance, AI governance and
    no-replay recovery are unchanged.

## Decision

### 1. Roles and lifecycle

- HR (`POLICY_MUTATE`) creates, edits, validates, simulates, submits and withdraws workflow
  proposals.
- One Director (`POLICY_APPROVE`) approves or rejects each pending proposal, with a reason of
  10–240 characters. The decision is final and immutable.
- Self-decision is refused three ways: by role, by an identity check in the service, and by the
  model validator.
- `ROLE_CAPABILITIES` does not change.

**Proposal states:**

| State | Terminal? | Meaning |
|---|---|---|
| `DRAFT` | no | Being written by its HR author |
| `PENDING_APPROVAL` | no | Submitted. Content frozen by a SHA-256 content hash. Awaiting one Director decision |
| `APPROVED` | yes | Published as a new version |
| `REJECTED` | yes | Declined with a reason |
| `WITHDRAWN` | yes | Withdrawn by the author, or released (§1.2) |
| `STALE` | yes | Another publication changed the base version first |

**Rules:**
- **One open proposal per workflow.** At most one `DRAFT` or `PENDING_APPROVAL` exists per
  workflow.
- **Base version.** Every proposal records `base_version`. Submit and approve both require it to
  equal the active version.
- **Kinds:**

| Kind | Applies to |
|---|---|
| `CHANGE` | All workflows |
| `RESTORE_VERSION` | All workflows |
| `RESET_TO_DEFAULT` | All workflows |
| `DEACTIVATE` | Non-onboarding only |
| `REACTIVATE` | Non-onboarding only. A full stage set that must satisfy the baseline (§2) |

- **Every publication creates a new version number.** History is never rewritten.

#### 1.1 Atomic decision

- A decision is one compare-and-set on the workflow definition document. In a single write it:
  - records the proposal's terminal state and decision evidence
  - appends the new version and sets the top-level `active_version` and `latest_version`, plus a
    new `write_nonce` (§3.2, §3.5), on approval
  - updates `required_baseline` (§2)
  - adds the outbox entries (§5)
- The write uses the durable write rule (§3.1).
- Inside the definition lock, after reauthorization, the decision checks:
  - capability
  - definition revision
  - proposal revision
  - the proposal is `PENDING_APPROVAL`
  - the Director is not the author
  - the content hash matches
  - the base version is still active
  - the ratchet (§2)
  - the permanent-obligation acknowledgement (§1.3)
- A second decision fails on the revision or the state. A decision can never publish twice.
- **Publication report.** After commit, the report shows, from case ledger records (§3.3) and
  never from the anonymous D3 counter:
  - cases past their first write under an earlier version
  - cases `AUTHORISED` under an earlier version
  - live `TENTATIVE` claims under an earlier version, as **"possibly authorised"**. Such a claim
    may already have passed D3 before the publication (R1-4).

#### 1.2 Abandoned drafts

- A draft records `last_activity_at`.
- After **14 days** without activity (RD-4), or when its author's account is disabled or
  deleted, any HR user may **release** it, with a reason. It becomes `WITHDRAWN` with
  `released_by`, and its content is kept.
- **Copy into new draft** makes a new proposal authored by the copier, with `copied_from`.
  Authorship is never transferred.
- Release never submits or publishes. Directors cannot release drafts. Pending proposals are
  ended only by their author's withdrawal, a Director decision or becoming `STALE`.

#### 1.3 Permanent-obligation warning (RD-2)

- When a proposal adds a **new required obligation**, or tightens one (§2), the Director's
  comparison lists each one under a warning:

  > Once approved, this required step or field can never be removed or weakened in the
  > product.

- The decision request must carry `acknowledged_permanent_obligations`, exactly equal to that
  set. Otherwise it is refused with
  `409 WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED`. The UI shows the warning with
  one explicit confirmation before **Approve** is enabled.
- The approved R1 mockups predate this condition and are kept unchanged. P3-1 adds the warning
  to the decision panel.

#### 1.4 Legacy provenance (D12)

- Versions activated under D-123 keep `activated_by` and get
  `origin = PRE_GOVERNANCE_DIRECTOR_ACTIVATION`, `approved_by = None` and `author_id = None`, with
  the note "Activated by a Director before approval governance; not independently approved."
  They are never shown or counted as approved.
- A legacy `draft_stages` becomes a `WITHDRAWN` proposal with `origin = PRE_GOVERNANCE_DRAFT`,
  `author_id = None` and `legacy_editor = <activated_by>`. HR may copy it.
- Optional ratification is an ordinary proposal with identical content. It publishes a new
  version and never edits the legacy record.
- The baseline is seeded from the **currently active** legacy version only (§2). Obligations that
  a Director dropped under D-123 are **not** resurrected automatically. Re-imposing one needs a
  separate, approved proposal.

#### 1.5 Policy values from the designer

- "Propose change" on a policy reference calls the **existing**
  `POST /api/policies/proposals {expected_catalogue_version, changes: {RULE_ID: value}, reason}`
  (the request also accepts `reset_ids`), then the existing submit route.
- The Director decides it through the existing policy governance and impact advisor.
- Workflow proposals store no policy values, only `related_policy_proposal_ids`. There is no
  second source of policy values.

### 2. Required-obligation ratchet (RR-1 to RR-10; replaces F2)

**Definitions:**
- **A required stage** is an added stage that blocks the send (`stage_blocks_send`), identified by
  `stage_id`.
- **A required field** is identified by `(stage_id, field_id)`. Its semantic signature is:
  - `kind`
  - the normalised label: case-folded, whitespace collapsed, punctuation removed
  - for CHOICE, the normalised option set
  - whether it has a `case_data_key`
  - its applicability condition, once conditional steps exist (later phase)

**The baseline.** Each definition stores `required_baseline`: for every obligation, its
**strictest signature ever published** (N-9). It only ever becomes stricter:

| Part | Baseline value |
|---|---|
| CHOICE options | The **intersection** of every option set published while the field was required. An option once removed can never return as an escape value |
| Kind and label | Fixed. RR-4, RR-5 and RR-10 make them immutable |
| `case_data_key` | Absent once absent |
| Applicability (conditional obligations, later phase) | The **broadest** applicability ever published. Applicability is never narrowed, and an unconditional obligation stays unconditional |

**How the baseline is maintained:**
- **Seeding.** At migration it is seeded from each workflow's currently active version
  (`versions[-1]`). Superseded legacy versions do not contribute (§1.4).
- **Updates.** Every governed publication updates it in the same write as the version.
- **Deactivation** keeps it. Reactivation, restore, reset and emergency fallback must satisfy it.

**Refused** at validate, submit and approve, and for every publication kind, including emergency
fallback. Each candidate is checked against **both** the active version **and** the baseline:

| Rule | Refused |
|---|---|
| RR-1 | A required stage missing |
| RR-2 | A required stage no longer blocking the send |
| RR-3 | A required field missing or optional |
| RR-4 | A required field's `kind` changed |
| RR-5 | A required field's normalised label changed (RD-1) |
| RR-6 | A required CHOICE field offering any option outside the baseline intersection |
| RR-7 | A required field gaining a `case_data_key` |
| RR-8 | An obligation's applicability narrowed, or an unconditional obligation made conditional |
| RR-9 | Any change to a code-owned mandatory stage or the mandatory engine order |
| RR-10 | A required stage's normalised name changed |

**Allowed:**
- new stages and fields
- optional → required
- removing CHOICE options (answers using them must be given again)
- moving a step to another legal anchor
- edits to optional content
- deleting optional steps (D4)

**No in-product removal (RD-2).** Nothing in the product removes or weakens a required
obligation. Doing so needs a separately approved change outside the product.

**Recovery publications** publish the **safe target**:
`base ∪ required_baseline` (with the baseline signatures), where `base` is an earlier version or
the built-in default. This protects new cases as well as existing ones.

**Representative content (R1-12).** For each obligation, the baseline also keeps a
**representative full definition**, so that a safe target can always be rendered and filled:
- the stage name and anchor
- each required field's full definition (label, kind, options, autofill label)
- taken from the latest published version in which the obligation appeared, with CHOICE options
  restricted to the baseline intersection

The signature remains the comparison key. The representative content is used only to build the
safe target.

### 3. Send dispatch fence (resolves R1 and R2; revised D10)

#### 3.1 Durable write rule (P1-1)

Every safety-critical write uses `w: "majority", j: true` with a `wtimeout` (default 5 s, bounded
at 30 s). This covers:
- D2, D3, D4 and D5
- the first-write attempt marker
- lease takeover and clearing
- publication and decisions
- `active_version` and `latest_version` backfill, and provisioning
- cold-archive inserts and outbox removal
- notice acknowledgement

**A step counts as done only when its own write, or a confirming write, is durably
acknowledged.** A confirming write is a conditional modifying update whose filter asserts the
expected state, own token and the step's original receipt, under `w: "majority", j: true`
(R4-1). For a fence step (D2, D4, D5) a confirming write counts **only** when that same write
is durably acknowledged **and** returns a post-image showing the expected element with own
token and the original receipt (§3.2). A modified-document count never authorises a fence step.
For the archiver's confirming `$inc` (§5), which authorises no dispatch, durable
acknowledgement of a write whose filter asserts `_id` and the content hash is required.

**Ambiguous outcomes** (timeout, `wtimeout`, network error, unknown commit state) are treated as
**not done**:
- The worker never treats a **read** as proof that its write is durable.
- It either issues the confirming write or stops.
- A stop before D6 makes no GoldTier call.
- A stop in the archiver leaves the record in the outbox.

**What reads are used for.** Reads only **select** candidates: D1, building a write, displays and
reports. Every safety predicate is asserted again **in the filter of the durable write** that
acts on it (§3.2). No read concern is relied on for the correctness of authorisation, attempt
recording or archive removal.

> **Why this resolves P1-1 (inference, to be tested).**
> - **Replica set:** a majority-acknowledged conditional write whose filter matches a marker
>   implies that the marker was on the primary when the write applied. Because one primary
>   applies and replicates writes in order, the marker is then majority-committed too.
> - **Standalone:** `j: true` implies the journal has been synced.
>
> The ordering step in this argument is **not stated in the MongoDB manual** (R1-10). It is an
> inference that CT-16 must demonstrate on the pinned image: a simulated rollback, and a crash
> before the journal flush. If CT-16 cannot demonstrate it, **no confirming write is used
> anywhere** (R2-6):
> - **An ambiguous D2 or D4** stops. The claim expires, and a later attempt starts again at D2.
> - **An ambiguous D5** stops before D6. Recovery follows the provider-verified path.
> - **An ambiguous cold-archive insert** is retried as a **fresh insert under an attempt-suffixed
>   `_id`** (`<logical_id>#<n>`). That insert gets its own durable acknowledgement and does not
>   rely on the inference. Cold readers deduplicate by `(logical_id, content hash)`. An identical
>   duplicate is harmless; a differing hash for the same logical id is an integrity failure. So the
>   outbox always drains, without a confirming write.
>
> Either way, a write that was seen but never durably acknowledged never authorises D6, and never
> permits removing an outbox record.

#### 3.2 Same-snapshot compare-and-set (P1-2)

Every ledger mutation, including D2, D4, D5, takeover, clearing and the existing attempt
markers, must evaluate its predicate on **the same snapshot whose revision it compare-and-sets**,
and must **assert that predicate in the write's filter** (R1-1):

1. Read the case document at revision `R`, carrying write nonce `N`.
2. Evaluate the predicate on that read: own token, state, lease, and no prior attempt of the
   operation. This step only selects whether to try.
3. Write with a filter that contains **all** of:
   - `_id`, `revision: R` and `write_nonce: N`
   - the identity-bearing predicate, matched on the targeted ledger element (by `submission_id`):
     the expected `workflow_dispatch` state and own `token`, the absence of this operation in
     `attempted_operations`, and, for D4 and D5, `lease_until > $$NOW`
4. The update sets a **new random `write_nonce`** and `revision: R + 1`.

**Why both guards.** `write_nonce` is a per-write random value. It means a revision number reused
after a replica-set rollback, or after a standalone crash that loses unjournaled writes, can never
match a document from a different history. The predicate in the filter means that, even with a
matching nonce, a write never succeeds against another worker's claim or an existing marker.

**Every writer of a guarded document (R2-1, R2-8).** Both rules apply to **every** writer of the
case snapshot document and of the workflow definition document, not only to fence and ledger
writers:
- Each update or replace must **match** the `revision` **and** the `write_nonce` it read, and
  must set a new nonce.
- **Case snapshot writers:** creation, onboarding, documents, ownership, reconciliation, CLM,
  automation, recovery and deletion. Today some of these replace the whole case document,
  including the embedded ledger, filtered only on `{_id, revision, creator}`
  (`mongo_case_store.py`, `repositories.py`). P2-0 changes them all.
- **Workflow definition writers:** drafts, proposals, decisions, recovery, notices, the outbox and
  compaction. These also use the durable write rule (§3.1), so a stale definition write can never
  overwrite a durable publication or its `required_baseline`.
- **The one exception is D3.** It modifies only `dispatch_authorisation_seq`, never the payload,
  revision or nonce. Its order against a publication comes from single-document atomicity (§3.3),
  and a publication's own revision-and-nonce filter is unaffected by it.
- **P2-0 adds a repository-wide test** that fails if any case or definition writer issues a
  compare-and-set without both the revision and the nonce in its filter.

**One filter shape everywhere.** The §3.1 confirming write uses this same filter shape: the
expected state, own token and marker presence. It changes only the nonce and the revision.

Today's pattern must be removed: `MongoTargetExecutionRepository.replace` (`repositories.py`)
re-reads the snapshot and checks only `state`, so the caller's duplicate-attempt check and the
compare-and-set use different snapshots.

**P2-0 includes this repository correction explicitly**, covering:
- `replace`
- the memory repository
- `_mark_operation_attempted` (`services/onboarding.py`)
- every other ledger writer

A conflict means a re-read and a re-evaluation, never an overwrite.

**How fence writes are made (R1-3, R2-3).** Fence steps (D2, D4, D5, takeover, clearing) are
**update pipelines**, never a whole-document `replace_one`. `arrayFilters` is **not** used: it
cannot contain `$expr`, and it cannot compute a server-time lease.
- **The update.** The pipeline rewrites `target_executions` with `$map` and `$cond`, changing only
  the element whose `submission_id` matches. It sets `lease_until` as `$$NOW` plus 60 s on the
  server, plus a new nonce and revision. Client clocks never set or extend a lease.
- **The lease condition in the filter.** It is a top-level `$expr` over that element. `$expr`
  with `$$NOW` in an update filter is **not verified** in the manual, so CT-18 must demonstrate it
  on the pinned image.
- **Fallback (R3-1).** If CT-18 cannot demonstrate the filter, the lease condition moves into
  the pipeline, and it must govern **the whole update atomically**:
  - the ledger element change, including the claim, the authorisation, or the write attempt
    marker
  - `lease_until`
  - `write_nonce`
  - `revision`

  These are all computed under **one** `$cond` on the lease predicate. On an expired lease the
  pipeline writes nothing at all: no field, no nonce, no revision.
- **A modified-document count never authorises anything (R3-1).** D2, D4 and D5 use
  `find_one_and_update` with `return_document=AFTER`, under the durable write rule. A step
  succeeds only when that **same write** both:
  - is durably acknowledged; and
  - returns a post-image whose targeted ledger element shows the expected result carrying the
    worker's own token and the step's **per-attempt receipt**: a random value written by the
    step's original update and asserted (never rewritten) by any confirming write for that
    step (R4-1). For D5, that result is the write attempt marker for the operation.

  The returned post-image belongs to this one atomic write. It is not a separate read.
- **Fail closed.** If the pinned image cannot provide both of these, the fence refuses every
  dispatch (`WORKFLOW_STAGE_CHECK_UNAVAILABLE`) rather than approximating:
  - the lease condition applied atomically with the marker, nonce and revision (filter or
    pipeline)
  - the durably acknowledged post-image proof

  CT-20 must demonstrate both on the pinned image, including an expired lease, where the
  post-image must show no change and no receipt.

**Schema and safe rollback (R2-4).** `workflow_dispatch` and `write_nonce` change the **case
snapshot document**, so the case snapshot schema version is bumped (currently 20). New fields also
change the **workflow definition document**. Because today's readers reject unknown schema
versions and unknown fields, the bump is shipped in **two releases** to keep a code rollback safe:
1. **Reader release (first in P2-0).** It accepts both the current and the new schema and fields.
   **On every write it round-trips the new fields unchanged** (R3-4):
   - `workflow_dispatch`, including the dispatch `version` and the receipt
   - `write_nonce`, on case documents
   - `latest_version`, the baseline, the outbox, notices and the extended records, on definition
     documents

   It writes the new-schema version number back when it read one. It **refuses** to write a
   document whose new fields it cannot preserve. So a rollback to it never strips data. Rolling
   back from it to the pre-P2-0 code is a plain revert, provided no document has yet been written
   in the new schema.

   **Implementation consequence of R4-4 (P2-0, to be accepted at the reader-release QG).**
   Because the reader release sets a new `write_nonce` on every write, every case document it
   writes is a schema-21 document (the new schema number is 21), and every definition document
   it writes carries a top-level nonce. A plain revert below the reader release is therefore
   possible only **before** the reader release has written anything. After that, rolling back
   below it needs the reverse migration below, which drops the nonces. The reader release never
   creates a `workflow_dispatch` claim, an attempt-marker record, `active_version` or
   `latest_version`; once `latest_version` exists, it refuses any definition write whose versions
   exceed it.
2. **Writer release.** It writes the new schema. A rollback from it goes back only to the reader
   release, which can read every document written. Rolling back further needs a reviewed,
   idempotent, dry-run-first reverse migration.

In the reverse migration:
- **Case documents:**
  - `workflow_dispatch` is cleared only where no write attempt marker exists.
  - An entry with an attempt marker keeps its recovery data, and the reverse migration refuses
    until that entry is finalised.
  - Nonces are dropped.
- **Workflow definition documents (R3-4):**
  - The reverse migration refuses while any outbox record is undrained or any proposal is
    pending.
  - It first verifies that every hot history record has a durably acknowledged cold copy.
  - Only then does it reduce the document to the pre-P2-0 shape (versions, draft, audit) that
    legacy code can decode. `latest_version`, the nonce, the baseline, notices, the outbox and the
    extended fields are removed from the hot document only. The cold collections keep the full
    history, untouched.
  - `active_version: 0` (deactivation) cannot be expressed in the legacy shape, so a deactivated
    workflow blocks the reverse migration until the owner decides.

**Roll-forward after a reverse migration (R4-3, P2-0 part).** Rolling forward again
(re-deploying the reader, then the writer release) re-runs the P2-0 backfill only for documents
that never held P2-1 content. Once P2-1 exists, every post-P2-0 correction and every roll-forward
after a reverse migration must restore `required_baseline` from the cold archive, or refuse; the
P2-0 tools refuse any document carrying P2-1 content (`P2_1_CONTENT_PRESENT`), so they can never
empty a baseline.

**P2-0 implementation notes (writer release, local candidate 2026-11-16).**
- A dispatch with no active version records `version: 0` (D-136 E2: holds nothing), and D3
  still guards it (`active_version: 0, latest_version: 0`, no version 1).
- Fallback mode is used: **no confirming write** anywhere (CT-16's ordering inference is not
  claimed), so an ambiguous D2, D4 or D5 stops before D6.
- The lease condition is in the filter (`$expr` with `$$NOW`), demonstrated on the pinned image
  (7.0.40, the staging digest), where an expired lease changes nothing. The pinned major version
  is checked by the startup probe; another major refuses dispatch until re-verified.
- Definition writers that do not change the payload (D3, the backfill) keep `revision`, because
  legacy code compares the top-level revision with the payload revision. The backfill rotates
  the nonce; D3 changes only `dispatch_authorisation_seq`.

Both steps are reviewed under the persistence-schema change class. In both, a missing
`write_nonce` is treated as a fresh nonce by the first writer, and a missing `workflow_dispatch`
means no claim.

#### 3.3 States, leases and steps

**Terms:**
- **Write attempt marker:** SHELL, POLICY or AMEND only. SEARCH is **not** a write attempt
  marker anywhere in this section (N-4).
- **Dispatch:** the first write attempt of a frozen submission.
- **Irreversible boundary:** the durably acknowledged write attempt marker. Recovery (D-136 E3)
  treats a write attempt as "may have written".

The case ledger entry gains `workflow_dispatch`:

| State | Meaning |
|---|---|
| none | No claim |
| `TENTATIVE {token, version, lease_until, receipt}` | A claim. **Not** permission to write |
| `AUTHORISED {token, version, d3_at, lease_until, receipt}` | Permission **for the holder of `token`, until `lease_until`,** to record the first write attempt marker. It is the case-level dispatch evidence |

**Version 0 (P2-0, QG R1 N-1).** A claim may carry `version: 0` when the onboarding workflow
has no active version. That still holds nothing (D-136 E2), and it is fenced exactly like any
other version: D3 asserts `active_version: 0`, `latest_version: 0` and no stored version 1, so a
first publication between D1 and D3 makes D3 match nothing and the dispatch is re-evaluated.

**Leases (N-3):**
- `lease_until` is at most **60 seconds** from the step that set it, measured in server time.
  The lease condition uses `$$NOW`: in the compare-and-set filter (`$expr`) when CT-18
  demonstrates it, otherwise in the update pipeline's single `$cond` (§3.2 fallback). Client
  clocks are never trusted (R4-1).
- **Stale tokens.** Every step's predicate requires the worker's own token. A worker whose token
  was replaced fails its compare-and-set and stops.
- **Expiry before a write.** An expired `TENTATIVE` or `AUTHORISED` claim without any write
  attempt marker may be taken over by the next dispatch attempt. Takeover is a D2 compare-and-set
  that installs `TENTATIVE {new token}`, so D3 must run again.
- **Expiry never authorises replay.** Once any write attempt marker exists, leases and tokens are
  irrelevant. Continuation goes only through the existing E3 provider-verified recovery, which
  never repeats an attempted operation.

**Sequence** (each step must succeed under §3.1 and §3.2 before the next):

| Step | What happens |
|---|---|
| D1 | Read the active version `V` and evaluate the send hold under `V`. If held, refuse (`WORKFLOW_STAGE_INCOMPLETE`). Advisory: a stale read only causes a retry at D3 |
| D2 | Compare-and-set the case document: from no claim, or an expired claim with no write attempt marker (Search-only entries qualify), to `TENTATIVE {new token, V, lease}`. A conflict, or a live claim held by another token, means stop |
| **D3** | **Linearisation point.** `update_one({_id: workflow_id, active_version: V, latest_version: V, "payload.versions.version": {$ne: V + 1}}, {$inc: {dispatch_authorisation_seq: 1}}, w: "majority", j: true, wtimeout)`. It asserts the authoritative active version, the monotonic high-water mark, and that no newer version has been appended outside the governed path (for example by a rolled-back legacy activation). It never counts retained versions, so archival cannot break it (R2-2), and a desynchronised document fails closed (R1-6). For a deactivated non-onboarding workflow this guard is not used, because no dispatch applies. It succeeds only when acknowledged **and** `modified_count == 1` (N-6). `$inc` always modifies the document, so the write is ordered against any publication on the same document (a no-op `$set` would not be). `matched == 0` means the version changed: back to D1, at most 3 times, then refuse with `WORKFLOW_STAGE_CHECK_UNAVAILABLE`. An ambiguous outcome counts as not authorised: repeat D3 within the lease, or stop. The counter is an **anonymous ordering aid, not case-level dispatch evidence** |
| D4 | Compare-and-set the case document: `TENTATIVE {own token, V}`, lease unexpired, to `AUTHORISED {own token, V, d3_at, new lease}` with a fresh receipt. It succeeds only with a durably acknowledged post-image showing `AUTHORISED`, own token and that receipt (§3.2). If ambiguous, issue a confirming write asserting `AUTHORISED` with own token and that receipt; it counts only with the same durably acknowledged post-image (§3.1, R4-1). Otherwise stop |
| D5 | Compare-and-set the case document, requiring all of: `AUTHORISED` with own token, lease unexpired, no prior attempt of this operation. It records the write attempt marker with the dispatch `version` and a fresh receipt. **Only a durably acknowledged post-image that shows the marker with own token and this receipt authorises D6** (§3.2). A modified count alone never does. If ambiguous, issue a confirming write asserting the marker with own token and receipt. Acknowledged with that post-image: go to D6. Not matched and still `AUTHORISED` within the lease: retry D5. Anything else: stop before D6, and recovery follows the existing provider-verified path |
| D6 | The provider call, unchanged. Made **once**, by the worker whose D5 (or confirming write) returned a durably acknowledged post-image with its own marker and receipt |

**Publication** is one compare-and-set on the same definition document, using the durable write
rule. Filtered on `revision` and `write_nonce`, it updates `payload`, `active_version`,
`latest_version`, `required_baseline`, a new `write_nonce` and `revision`, all in one write
(§3.2, §3.5).

**Why the fence holds:**

| Property | Argument |
|---|---|
| **Linearisation** | D3 and every publication are durable modifying writes on one document, so the storage engine orders them. D3 first: the dispatch is authorised under `V`, and later publications apply only to later authorisations (an explicit, durable cutoff). Publication first: D3 matches nothing and the dispatch is re-evaluated. A newly applicable requirement is never bypassed. An authorisation is also bounded by its lease, so a stalled worker cannot write long afterwards |
| **Competing workers** | §3.2 writes assert own token, state and "no marker for this operation" in their **filter**, and match a unique `write_nonce`. Two workers therefore cannot both record a write attempt, even if a revision number is reused after a rollback or crash loss |
| **Crashes** | Before a write attempt marker: the claim expires and is taken over, or startup recovery clears it (§3.4). After one: E3 recovery, provider-verified, no replay |
| **Ambiguity** | §3.1: no ambiguous step authorises D6 |
| **No duplicate writes** | D6 runs only after the worker's own durably acknowledged marker. Markers are unique per operation (§3.2). Takeover is impossible after a marker |

#### 3.4 Process model and startup (N-5; ruling 4)

- **Single process per store.** The supported deployment remains **one backend process per
  store**. Broader multi-instance runtime support is **not** authorised.
- **Why the fence still has multi-process tests.** The fence is designed and tested for competing
  processes (§8) as defence in depth, so its safety does not rest on the single-process
  assumption.
- **Startup recovery.** Under the single-process rule, startup recovery (`MongoCaseStore` recovery
  of interrupted entries) clears every `workflow_dispatch` claim that has **no write attempt
  marker**, using a §3.2 compare-and-set, because no other process can hold it. This is the only
  "demotion" actor apart from D2 takeover.
- **Existing startup behaviour, kept:**
  - Deleting IN_PROGRESS entries with no attempt.
  - Treating uncertain entries as uncertain.
  - The D-124 S9 startup release. As recorded in D-124 S9, it moves holds on only as far as the
    human target-confirmation wait, and makes at most a read-only Search. CT-0 enforces that any
    write path it could reach goes through the fence.
- **Continuations.** A recovery continuation, or a legacy recovery-only `/submit`, whose next
  operation is the **first** write must pass the fence.

#### 3.5 Version field, backfill and P2-0 transition (N-7; ruling 6)

- **The fields (R2-2).** The definition document gains two top-level fields:
  - **`active_version`**: the authoritative active version number, where 0 means none.
  - **`latest_version`**: the monotonic high-water mark of every version number ever published.

  **They do not depend on how many versions are retained.** Versions keep their numbers when they
  are archived. Numbers are never reused, and `latest_version` never decreases.

  Invariants:
  - `active_version` is 0 or `latest_version`. For onboarding, which cannot be deactivated, it
    equals `latest_version` once anything is published.
  - The active version is always kept hot, so the newest hot version's number equals
    `latest_version`.
- **Who maintains them.** Every publication path sets both in the same write as `payload`. In P2-1
  that is approval, recovery and emergency fallback. The memory repository does the same.
- **Provisioning.** The onboarding definition document is provisioned at startup with an
  idempotent, insert-only create (`active_version: 0`, durable write rule).
- **Create-on-read removed (R1-2).** Today `GET /api/workflows` and `GET /api/workflows/{id}`
  still create it on read, through `_baseline()` (`workflow_management.py`), and `create()` writes
  no top-level `active_version`. P2-0 removes both read-path creations, so these reads return what
  is stored and never create it. Every definition create writes `active_version` under the
  durable write rule. The P1 rule ("a read never creates a definition") then holds on every path.
- **Startup re-verification (R1-6, R2-2).** At each startup the fence checks every definition
  document:
  - hot version numbers **strictly increase** along the stored array, and **the last element's
    number** equals `latest_version`
  - `active_version` is 0 or `latest_version`
  - no version number above `latest_version` exists, hot or cold
  - **every version published after the P2-1 migration marker carries governed provenance**: an
    `origin` of `APPROVED_PROPOSAL` or `EMERGENCY_FALLBACK`, with its proposal or decision
    record (R3-3)

  The checks never count retained versions. The provenance rule catches a legacy activation that
  slipped through, whatever number it used: legacy code numbers versions `len + 1`, which after
  compaction can fall below `latest_version`, and it never writes governed provenance.

  **A mismatch refuses dispatches** (`WORKFLOW_STAGE_CHECK_UNAVAILABLE`). The P2-0 backfill rule
  is **not** reused as the remedy. After P2-0, a mismatch needs a **separately reviewed
  correction** that:
  - preserves `active_version: 0` on a deactivated workflow
  - never adopts a version without governed provenance
  - never lowers `latest_version`
  - leaves archived history untouched
- **D1's source.** D1 takes `V` from the top-level `active_version`, and D3 guards it as above.
- **P2-0 transition, in order:**
  1. **Freeze legacy activation at the backend.** `POST /api/workflows/{id}/activate` returns
     `409 WORKFLOW_PUBLICATION_FROZEN`, so no publication path exists that could skip
     `active_version`. Draft saving may continue; it changes no case. Governed publication returns
     in P2-1.
  2. **Backfill (P2-0 only).** A reviewed, idempotent, dry-run-first backfill sets
     `latest_version` to the **highest version number** present and `active_version` to that same
     number (0 if none), on every existing definition document, under the durable write rule. Its
     derivation rule is valid **only** for this one P2-0 run. At that point every version is still
     hot, nothing has been archived, nothing has been deactivated, and every existing version is a
     migrated pre-governance activation. It must never run after P2-1 (R3-3).
  3. **Verify, then enable.** Run the startup checks above on every document. Only then enable the
     fence.
- **Safeguards during the transition.** D-136 E1–E4 enforcement stays exactly as today
  throughout. The fence adds to it and never replaces it. If the fence cannot run (an unbackfilled
  document, an unsupported topology), the dispatch is refused.

#### 3.6 D-136 E2 amendment (N-10; ruling 8)

D-136 E2 says an empty store, meaning no definition or no active version, holds nothing. From
P2-0:
- **No active version** (`active_version: 0`) still holds nothing.
- **A missing expected onboarding definition document** is **refused**. A provisioning or backfill
  gap is treated as unavailability, not as "no workflow".

This is a deliberate fail-closed narrowing of D-136 E2, recorded in D-135.

#### 3.7 Re-confirmation, "sent", and legacy routes

**Re-confirmation (RD-3; N-12):**
- When D1 or D3 holds a case that already has a target dispatch confirmation, because a newly
  applicable requirement appeared, a §3.2 compare-and-set marks that confirmation
  `SUPERSEDED_BY_WORKFLOW_CHANGE`. It keeps the frozen submission and records the event
  `DISPATCH_RECONFIRMATION_REQUIRED`.
- After the new stage is confirmed, the operator re-confirms through the existing zero-touch
  confirmation route. Until then dispatch returns `409 WORKFLOW_DISPATCH_RECONFIRMATION_REQUIRED`.

**Refusals on the zero-touch send (P2-0 implementation).** A fence refusal never ends
automation:
- `WORKFLOW_STAGE_CHECK_UNAVAILABLE` pauses the send (`RECOVERY_PENDING`), and the same
  submission continues on explicit resume.
- `WORKFLOW_STAGE_INCOMPLETE` and `WORKFLOW_DISPATCH_RECONFIRMATION_REQUIRED` return the case to
  the target confirmation step at readiness, where it is re-confirmed through the zero-touch
  route once the stage is confirmed.
- Only `WORKFLOW_STAGE_INCOMPLETE` (a newly applicable requirement) supersedes a confirmation.
  An unreadable check never does.

**"Sent":**
- A case is sent when it has a SHELL, POLICY or AMEND write attempt marker, a retained target
  outcome or receipt, or automation COMPLETE.
- It is **never** sent because of a confirmation, a `TENTATIVE` or `AUTHORISED` claim, a frozen
  snapshot, a pin, or the MOCK_GOLDTIER stage alone.
- This replaces `_automation_is_sent` and resolves R2.
- A sent case's version is the dispatch `version` recorded with its first write attempt marker.
  Historical cases without one use the creation-time rule, labelled "version inferred".

**Legacy routes (N-11):**
- `POST /api/clm/cases/{id}/target-confirmation` has **no** frontend caller (`api.ts` uses the
  zero-touch route). It is retired.
- `POST /api/clm/cases/{id}/submit` is called only by `ClmJourney` (rendered only in
  `App.test.tsx`) and by recovery tests. It becomes **recovery-only**: accepted only when the full
  D-136 E3 predicate holds for the frozen submission, meaning a write attempt marker **or** a
  retained target outcome or receipt (R1-11; deliberately not narrower than E3). Every existing
  check keeps its order. Otherwise it returns `409 CLM_SUBMIT_RECOVERY_ONLY` and nothing is
  written.
- Retirement is gated on a caller inventory and a read-only staging count of in-flight entries.

#### 3.8 Deployment guarantees and failing closed

**Supported topologies:**
1. A **standalone `mongod` with journaling.** This is the staging topology, if P2-0 confirms that
   `deploy/compose.mongo.yml`, which runs one `mongod` with no `--replSet`, is what is deployed.
   On a standalone server, `w: "majority"` with `j: true` acknowledges after the on-disk journal
   write. `j: true` without journaling is an error.
2. A **replica-set primary**, with `w: "majority", j: true`.

**Not supported:** sharded clusters and any unidentified topology. A `hello` probe classifies the
server at startup and before fence use.

**Read concerns.** `majority` read concern is not linearizable. `linearizable` is documented only
for replica-set primaries, so it is unavailable on the staging topology and is not used.

**To verify in P2-0** (not verified at G0):
- the pinned image's server version
- that journaling is on
- the deployed topology

**If a guarantee is unavailable:** an unsupported topology, a refused or unacknowledged durable
write, or a probe failure. Then the fence refuses every dispatch
(`WORKFLOW_STAGE_CHECK_UNAVAILABLE`), and governance mutations are refused. Reads and case work
continue.

**Memory mode** (one process):
- The case store lock orders D2, D4 and D5.
- The workflow repository lock orders D3 and publication.
- Each step is atomic within its own store, so the two locks need not be shared.

### 4. Recovery and deactivation

| Action | Who | Approval | Publishes |
|---|---|---|---|
| Restore draft | HR author | none | nothing |
| Restore version `vK` | HR proposes | one Director | safe target of `vK` |
| Reset to default | HR proposes | one Director | safe target of the default |
| Emergency fallback | Director alone, mandatory reason | none (the single-actor exception, D6) | safe target, `origin = EMERGENCY_FALLBACK` |
| Deactivate (non-onboarding) | HR proposes | one Director | no active version for **new runs** |
| Reactivate (non-onboarding) | HR proposes | one Director | new version that satisfies the baseline |

**Emergency fallback** also:
- writes an immutable record
- marks open proposals `STALE` (kept)
- raises a persisted **governance notice** that stays until an HR user acknowledges it (§5)

It cannot bypass the ratchet, the mandatory stages, D-136 enforcement, the fence, ledgers or
recovery.

**Owner clarification (2026-11-18): the fallback never expands the baseline.**
- A Director's single-actor emergency fallback must not expand the permanent required-obligation
  baseline. It preserves every existing obligation (the safe target), and adds none.
- If the target would add or tighten any permanent obligation, the fallback is refused with
  `422 WORKFLOW_PROPOSAL_INVALID`, listing each obligation. Examples: a required stage or field
  not in the baseline, a narrower CHOICE intersection, or a dropped `case_data_key`. Nothing is
  written.
- Stripping the extra required content instead is not allowed. Later candidates are checked
  against the active version, so that content would become sticky anyway.
- A fallback to the built-in default (the baseline's own representative content), or to any
  version within the baseline, remains available. On success the stored baseline is unchanged.
- Any additional permanent obligation goes through a normal proposal and one Director's
  approval, with the §1.3 warning and acknowledgement.

**Deactivate:**
- It is applied under the definition lock and **never modifies any run**.
- Existing runs keep their frozen stages and remain completable: answer, confirm and view.
- **Restored R1 refusal (R1-9).** The deactivation decision is refused with
  `409 WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS` while any run of that workflow is inside a
  required-stage confirmation.
  - **The counter.** Confirmations are tracked by a per-workflow in-progress counter, which is valid
    under the single-backend-process deployment (§3.4).
  - **One shared lock (R2-5).** The counter is protected by a per-workflow **confirmation gate
    lock** that both paths take:
    - a confirmation takes it briefly to increment the counter before entering the run's lock,
      and to decrement it afterwards
    - the deactivation decision holds it from checking the counter until its own compare-and-set
      completes

    So no confirmation can begin between the check and the decision.
  - **The structural property still holds:** deactivation writes no run state.
- `required_baseline` is kept.
- Onboarding cannot be deactivated.

### 5. History storage

**Hot document** (`workflow_definitions`). It holds:
- metadata, `revision`, `write_nonce`, `active_version`, `latest_version` and `required_baseline`
- the active version plus **up to** 15 more (RD-5 maxima)
- the open proposal
- **up to** the last 16 decided proposals
- **up to** the last 64 events
- every **unacknowledged** governance notice
- the **outbox**

**Cold collections, insert-only:**
- `workflow_versions`, with `logical_id = workflow_id:version`
- `workflow_proposals`, with `logical_id = proposal_id`
- `workflow_governance_events`, with `logical_id = workflow_id:sequence`, which also holds notices
  and acknowledgements

**Record identity (R3-5):**
- Every cold record carries `logical_id` and `content_hash`. Its `_id` is
  `<logical_id>#<attempt>`, where the first attempt is 0.
- Each collection has an index on `logical_id`.
- `get_version` and every other cold lookup read **by `logical_id`**, and take any record whose
  content hash matches. Records with the same logical id and different hashes are an integrity
  failure.

**Outbox, crash-safe and idempotent:**
1. Every mutation writes its history records into the outbox in the same compare-and-set as the
   change.
2. The archiver drains it at startup, before every governance mutation, and after each commit.
   It inserts each record as `<logical_id>#<attempt>` under the durable write rule.
3. **A duplicate key never counts as inserted by itself (R3-5):**
   - **Confirming writes allowed** (CT-16 demonstrated the inference): a duplicate whose stored
     hash is equal needs the confirming `$inc` (step 4) before the record leaves the outbox.
   - **Fallback mode:** the duplicate is ambiguous. The archiver inserts a fresh
     `<logical_id>#<attempt+1>` with its own durable acknowledgement.
   - **Either mode:** a duplicate with a **different** hash is an integrity failure, and
     governance mutations fail closed.
4. A record leaves the outbox only after **durable acknowledgement of its cold copy**: either the
   insert's own acknowledgement, or a confirming write. A plain read-back is never sufficient
   (P1-1).
   - **Cold records are insert-only in their content.** Their content fields and content hash
     never change.
   - **One permitted marker field (R1-5).** Each cold record has `archive_confirmations`, an
     integer that only the archiver's confirming write increments
     (`$inc: {archive_confirmations: 1}`, filtered on `_id` and the content hash). It is used
     only when CT-16 has demonstrated the ordering inference. Otherwise the fresh-suffix insert
     applies, and the outbox still drains.
5. A crash or an ambiguous outcome leaves the record in the outbox, and draining is repeatable.

**Compaction** moves an item from hot to cold only after a durably acknowledged cold copy exists.
- Unacknowledged notices are never compacted. Acknowledgement is itself an archived event.
- The existing silent 256-event truncation is removed.

**Byte budget (N-13):**

| Limit | Value |
|---|---|
| Encoded version, enforced at validate and submit | ≤ 1 MiB, else `WORKFLOW_PROPOSAL_TOO_LARGE` |
| Proposal record | ≤ 1 MiB |
| Notice | ≤ 4 KiB |
| Outbox | ≤ 32 records |
| Case dispatch fields | ≤ 1 KiB |
| `required_baseline` plus representative stage content (R1-12), and metadata | ≤ 1 MiB, enforced at submit |
| **Pinned set** (always kept hot): active version, open proposal, unacknowledged notices (≤ 64), outbox at most one publication's records, baseline and metadata | worst case about 5.3 MiB (R1-7) |
| Compaction starts | 4 MiB, of non-pinned content |
| Hard ceiling | 8 MiB (MongoDB's document limit is 16 MiB) |

- The size is computed (BSON) before every compare-and-set.
- **RD-5 counts are maxima (owner-approved 2026-11-16).** They are limited by the byte budget and
  by verified archival. Nothing leaves the hot document without a durably acknowledged cold copy,
  and cold storage always holds everything.
- If a write would exceed the ceiling after compaction, or the cold store is unavailable while
  limits are reached, governance mutations return `503 WORKFLOW_HISTORY_UNAVAILABLE`. Nothing is
  truncated.
- At 64 unacknowledged notices, a new emergency fallback is refused with
  `409 WORKFLOW_NOTICES_UNACKNOWLEDGED`. Nothing is discarded.

**Referenced versions stay reachable.** `get_version(workflow_id, n)` reads hot, then cold. A
version referenced by a run or a dispatch record is resolvable:
- Runs embed their stage copies.
- Onboarding cases resolve the active version (always hot) or their dispatch version.

If a referenced version cannot be read, the send check refuses and the display says it is
unavailable.

### 6. API changes (when implemented)

**Added routes** (all `ACTOR_ONLY` in `ROUTE_POLICIES` and reauthorized inside the owning lock):
- `POST /api/workflows/{wid}/proposals`
- `PUT …/proposals/{pid}`
- `POST …/restore-draft`, `/validate`, `/simulate`, `/submit`, `/withdraw`, `/release`, `/copy`
- `GET /api/workflow-approvals`
- `GET …/comparison`
- `POST …/decision`
- `POST /api/workflows/{wid}/emergency-fallback`
- `GET /api/workflows/notices`, `POST …/notices/{id}/acknowledge`
- `GET /api/workflows/simulation-scenarios`

**Frozen in P2-0, retired in P2-1:**
- `POST /api/workflows/{wid}/activate`
- `PUT /api/workflows/{wid}/draft` (retired in P2-1)

**Retired in P2-0:** `POST /api/clm/cases/{id}/target-confirmation`.
**Restricted in P2-0:** `POST /api/clm/cases/{id}/submit` (recovery-only).

**Simulation** is synthetic only, from a fixed scenario catalogue. It reads no case store, makes
no provider call and writes nothing. Counts of affected cases go to the Director only.

### 7. P2-0 scope (explicit)

1. The dispatch fence (§3.3), with leases and stale-token rejection.
2. The durable write rule (§3.1), with a `wtimeout`.
3. The same-snapshot ledger compare-and-set correction (§3.2), with predicates in write filters,
   `write_nonce`, targeted `$$NOW` lease updates and the case snapshot schema bump. It applies
   across `replace`, the memory
   repository, `_mark_operation_attempted` and every ledger writer.
4. Startup clearing of unattempted claims (§3.4).
5. The sent predicate and the re-confirmation mechanism (§3.7).
6. Legacy route retirement, and recovery-only `/submit`.
7. The legacy activation freeze, the one-time `active_version` and `latest_version` backfill, and
   provisioning (§3.5).
8. The topology and journaling probe (§3.8).
9. Removing create-on-read from the workflow read routes, and startup re-verification of
   `active_version`, `latest_version` and version provenance (§3.5).
10. The repository-wide revision-and-nonce writer test (§3.2), the two-release schema rollout
    (reader, then writer) with its reverse migration, and the choke-point regression test, and
    CT-0 to CT-20 where they apply (Verification). These run
    against mocks and disposable MongoDB only.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Pin the version at confirmation, inside the case lock | Rejected. It does not serialise a publication with the write, and a confirmed but unsent case would skip a new requirement |
| A cutoff record followed by a validating re-read | Rejected. It needs linearizable reads, which are not documented for the standalone staging topology, and majority reads are not equivalent |
| Settling ambiguous writes by re-reading | Rejected (P1-1). It can observe writes that are later rolled back or lost |
| A publication that takes every open case lock | Rejected. Its cost grows with the number of cases, it risks deadlock, and the locks are process-local |
| Multi-document transactions | Rejected. They need a replica set |
| Multi-instance runtime | Not authorised. One backend process per store remains |
| F2 as a check on presence and the Required toggle only | Rejected. It misses semantic weakening |
| Embedded, bounded decision lists with truncation | Rejected. They silently lose history |

## Consequences

- **Gains:**
  - Requirements 1–7 become technically enforced.
  - R1 and R2 are resolved by design.
  - The audit becomes complete and never silently trimmed.
- **Accepted costs:**
  - One extra durable write on the workflow definition per dispatch.
  - Lease bookkeeping.
  - New cold collections.
  - Legacy activation is frozen between P2-0 and P2-1.
  - Mistaken required obligations are permanent (RD-2).
  - A confirmed case may need a second confirmation (RD-3).

## Architecture invariants affected

**Preserved:**
- backend-authoritative RBAC
- reauthorization inside the owning lock or compare-and-set
- explicit memory/Mongo modes with no silent fallback
- insert-only create and update-only mutation
- ledger-owned target ordering with no replay
- one orchestration owner and one workflow persistence owner
- the code-owned mandatory engine order
- ACRA identity provenance and the staging identity policy
- user-scoped frontend state
- AI Assistant safeguards: no workflow tool or data; it cannot author, decide or fall back
- D-136 E1, E3 and E4
- D-136 E2, except the narrowing in §3.6
- the single-backend-process deployment

**Added:**
- The dispatch fence is the only path to a first GoldTier write.
- Safety-critical steps count only after durable acknowledgement.
- Ledger compare-and-sets use one snapshot.
- Required obligations only grow stricter.
- No governance history is deleted without a durably acknowledged archived copy.

## Security and persistence implications

- **New persisted fields:**
  - on the workflow definition: top-level `active_version`, `latest_version`, `write_nonce`,
    `required_baseline`,
    `dispatch_authorisation_seq`, the outbox, notices and the extended version and proposal
    records
  - on the case snapshot document: `workflow_dispatch` on each ledger entry, and the
    document-level `write_nonce`. This is a **case snapshot schema bump** (currently 20) in P2-0,
    with backward-compatible defaults (§3.2).
- **New insert-only collections.** Content is immutable. The single `archive_confirmations`
  marker field is the only permitted mutation (§5).
- **Reviewed, idempotent, dry-run-first scripts:** the one-time P2-0 `active_version` and
  `latest_version` backfill, the reverse migration (§3.2), and the P2-1
  migration. Each runs in an approved window after a read-only staging inventory (D15, future
  gates). They never touch `clm_poc`.
- No secrets or case data enter workflow documents or simulation output.

## Migration and retirement implications

- Legacy versions and drafts are migrated as in §1.4.
- The baseline is seeded from each workflow's currently active version.
- Legacy routes are retired or restricted as in §3.7, after the inventory gates.
- **Rollback (R2-4).** Older code rejects unknown schema versions and fields, so a plain revert
  past the writer release is **not** safe. Safe rollback follows the two-release sequence in §3.2:
  - Revert from the writer release to the reader release.
  - Below the reader release, only after the reviewed reverse migration.

  Any rollback that restores the legacy activation or legacy routes also needs workflow
  publications kept frozen until the forward version is restored. The startup checks (§3.5)
  refuse dispatches if a legacy activation slipped through.

## Verification

**Test environment (owner instruction, 2026-11-16):** P2-0 and later dispatch-safety tests use
**only mocks and a newly generated, allowlisted, disposable MongoDB database**.
- Never `clm_poc`, `clm_staging` or any staging host.
- No AWS.
- No GoldTier Sandbox. A recording mock GoldTier transport asserts exact call counts.
- The disposable server runs the same MongoDB image digest as staging.

The tests use independent **processes**, so the fence's safety is tested beyond the supported
single-process deployment, with forced interleavings at D1–D6 and inside publication.

**Replica-set rollback and crash loss** are simulated against the disposable server, using:
- a disposable replica set where a scenario needs one
- injected acknowledgement failures
- killing `mongod` before a journal flush on a disposable standalone

| ID | Covers |
|---|---|
| CT-0 | **Choke-point regression test** (R1 §3.4). It fails if any SHELL, POLICY or AMEND connector call in `app/` is not preceded by its write attempt marker through the fence. It covers the zero-touch send, legacy recovery-only `/submit`, the D-124 S9 startup release and the recovery continuation |
| CT-1 to CT-3 | Decisions and proposals |
| CT-4 | Fence interleavings, including D3 against publication (`modified_count == 1`) |
| CT-5 | Process crashes between every pair of steps, with startup clearing |
| CT-6 | E3 recovery, no replay, and expired leases after a write marker |
| CT-7 | Re-confirmation |
| CT-8 | Stale after emergency fallback |
| CT-9 | Ratchet, including option removal and re-add (RR-6 against the baseline), applicability narrowing, deactivate then reactivate, and no legacy resurrection |
| CT-10 | Safe-target recovery for new cases |
| CT-11 to CT-13 | Outbox, idempotence, hash mismatch, byte budget, notices never dropped |
| CT-14 | Draft release |
| CT-15 | Whole-version reads |
| CT-16 | Fail closed on an unsupported topology, refused journaling, an injected `wtimeout` or ambiguous write, and a simulated rollback of an unacknowledged marker or archive insert. It also demonstrates the §3.1 ordering inference (R1-10) |
| CT-17 | Two processes stalled between the read and the compare-and-set (P1-2). It includes the **revision-collision** case: a revision reused after a simulated rollback or crash loss must fail on `write_nonce` and the filter predicate, never overwrite another worker's marker (R1-1) |
| CT-18 | Lease expiry before D5 (back to D3), stale-token rejection, Search-only claim takeover, legacy activation frozen, backfill verification and startup re-verification (R1-6), missing definition refused, `GET /api/workflows` never creating a definition (R1-2), the deactivate refusal during a run confirmation (R1-9), `$$NOW`-based leases (R1-3), and "possibly authorised" counts in the publication report (R1-4) |
| CT-19 | Recovery-only `/submit` accepts each half of the full E3 predicate (an attempt marker, or a retained outcome or receipt) and refuses otherwise (R1-11). The archive confirming marker drains the outbox (R1-5). A safe target built from representative baseline content (R1-12) |
| CT-20 | **R3 additions:**<br>• **Durable acknowledgement:** every safety-critical write under injected `wtimeout`, network loss and simulated rollback, including the no-confirming-write fallbacks for D2, D4 and D5 and the attempt-suffixed cold re-insert (R2-6).<br>• **Writer guards:** every case and definition writer, including ownership, document and automation writers, refuses a stale revision or nonce after a revision collision (R2-1, R2-8).<br>• **The D3 guard** stays correct after versions are archived (R2-2).<br>• **The deactivate gate lock** (R2-5).<br>• **Lease in the update pipeline**, or the `$cond` fallback. An expired lease must change nothing: no nonce, no revision, no receipt. D6 must be authorised only by a durably acknowledged post-image showing the own marker and receipt (R2-3, R3-1).<br>• **Provenance startup check:** a legacy-numbered append after compaction is detected (R3-3).<br>• **Reader-release round-trip** of the new fields, and the definition-document reverse migration refusals (R3-4).<br>• **Archive lookup by `logical_id`,** and fresh-suffix re-insert in fallback mode (R3-5).<br>• **Schema rollback:** the reader release reads writer-release documents, and the reverse migration refuses entries with a write marker (R2-4) |

D-136, P1, RBAC inventory, AI Assistant and identity-provenance suites must stay green.

## Revisit conditions

- A change of MongoDB topology or version.
- A request for multi-instance runtime.
- A sponsor decision on workflow governance.
- Any proposal to remove a required obligation.
- Conditional steps (their own ADR).
- A move away from code-owned mandatory order.

## Related decisions

D-123, D-124, D-135, D-136; ADR-006, ADR-014, ADR-016.
