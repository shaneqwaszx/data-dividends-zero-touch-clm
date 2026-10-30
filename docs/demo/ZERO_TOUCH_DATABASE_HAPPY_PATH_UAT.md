# Database-backed zero-touch happy paths: Company, Partnership and Government

One clean case per entity type (D-101): **Company** Alpha `209990101A` (also Beta and Delta),
**Partnership** Gamma `209990103C`, and **Government** DEMO PARKS FYP TEST AUTHORITY `T99FY0105G`.

All names, addresses, officers, ownership and UENs below are fictional FYP test data.
Future-looking identifiers were generated to meet the repository's syntax validator;
they are not issued/verified ACRA registrations. No company is preseeded in GoldTier.
Actual Sandbox absence is unknown until owner-authorized Search.

## Worktree runs: import this checkout's code

A shared virtual environment can hold an editable install that maps `app` to another
checkout (usually the primary one). Run from a task worktree and the seed script and backend
then silently import that other checkout's code: the seed writes the other branch's fixtures
and cases fail registry verification. Do not change the shared environment. In every
terminal that seeds or starts the backend, from the worktree root, first run:

```zsh
export PYTHONPATH=$PWD/apps/backend:$PWD
```

Check it with
`python -c "import app, scripts.zero_touch_happy_path_fixtures as f; print(app.__file__, f.__file__)"`;
both paths must be inside the worktree.

## Seed and safe check

Use this branch's managed worktree and provision backend runtime secrets separately.
The utility never reads or edits .env. Create a new disposable target name, set the
same MONGO_DATABASE in the app process, and use the same configured registry collection.
MONGO_URI must already be provisioned in the process environment; do not print it.

```powershell
$env:APP_ENV = "development"
$env:CLM_PERSISTENCE_MODE = "mongo"
$env:MONGO_DATABASE = "clm_uat_" + [guid]::NewGuid().ToString("N").Substring(0,24)
python scripts/seed_zero_touch_happy_path_companies.py --seed --database $env:MONGO_DATABASE
python scripts/seed_zero_touch_happy_path_companies.py --check --database $env:MONGO_DATABASE
```

Expected initial safe counts: FIXTURE_COUNT=4, CREATED=4. Check: FRESH=4, MISSING=0,
EXPIRED=0. Seed rerun: CREATED=0, REFRESHED=0, FRESH=4. Conflicting evidence aborts
without overwriting it. Expired matching seeds are refreshed using revision CAS;
refresh advances original seed timestamps explicitly. `--check` never writes.
The CLI accepts only clm_uat_<24 lowercase hex> or guarded clm_p16_<24 hex>
databases, rejects production and clm_poc, and cannot drop a database.

Ordinary REGISTRY_CACHE_MODE defaults to auto. Remove an old explicit disabled process
override or deliberately select auto; no RM cache setting is required. Legacy mock
requires REGISTRY_CACHE_FRESHNESS_SECONDS=7776000. Approved frozen case freshness
(default90days, expiry exclusive) controls binding. Retained cases keep their bound
copy; missing/expired/incomplete shared seed evidence uses configured ACRA acquisition.
Corrupt persisted evidence remains fail-closed and must be repaired separately.

## Runtime and document pack

Configure the intended process with CLM_PERSISTENCE_MODE=mongo, the same disposable
MONGO_DATABASE, ACRA_CONNECTOR_MODE=api_marketplace_mock, GOLDTIER_CONNECTOR_MODE=sandbox,
GOLDTIER_SANDBOX_ALLOW_WRITES=true, IDP_CONNECTOR_MODE=local_pdf_text and installed
LOCAL_OCR_EXECUTABLE. Provision approved provider configuration/secrets through existing
backend handling. Implementation/testing made zero external provider calls.

Documents are in apps/backend/tests/fixtures/uat/zero-touch-database. They are image-only
PDFs with matching Legal Name, UEN, Registered Address and Country plus explicitly labelled
KYC Customer Type and Client Segment. Fixed DSD/ACRA/Singapore/ANZBGL profile values
are visible but remain system-owned. Gamma also has `demo-gamma-partnership-agreement.pdf` and the
Government case uses `demo-parks-government-status.pdf` (see the D-101 sections below). The generator
uses an installed local Arial/DejaVu font (Verdana-style glyphs for the two D-101 letters); every page visibly labels fictional FYP data.
SSIC/business activity is unsupported by the current canonical domain and is omitted.
Alpha, Beta and Delta are private companies; Gamma is a synthetic Partnership. All are SG, fictional LIVE status,
incorporation2026-01-05; one active DEMO Director and DEMO Secretary appointed that day.
No natural person has a registration identifier or real NRIC/PII. Corporate nodes
have separate generated synthetic identifiers.

| Company (exact legal name) | UEN | Document | Registered address | Effective people in P1..Pn order | PROVISIONAL UBO CANDIDATE >=25% |
|---|---|---|---|---|---|
| DEMO ALPHA CIRCULAR FYP TEST PTE. LTD. | 209990101A | demo-alpha-scanned.pdf | 11 DEMO ALPHA WAY, 000101, SG | 60 / 40 | ALPHA P1 60%, P2 40% |
| DEMO BETA HOLDINGS FYP TEST PTE. LTD. | 209990102B | demo-beta-scanned.pdf | 22 DEMO BETA WAY, 000102, SG | 30 / 25 / 17 / 14 / 8.5 / 5.5 | BETA P1 30%, P2 25%; P3..P6 below threshold |
| DEMO GAMMA TECHNOLOGIES FYP TEST PARTNERSHIP | 209990103C | demo-gamma-scanned.pdf + demo-gamma-partnership-agreement.pdf | 33 DEMO GAMMA WAY, 000103, SG | 30 / 25 / 20 / 10 / 10 / 5 (agreement, RM-confirmed) | GAMMA P1 30%, P2 25%; P3..P6 below threshold |
| DEMO DELTA SUSTAINABILITY FYP TEST PTE. LTD. | 209990104D | demo-delta-scanned.pdf | 44 DEMO DELTA WAY, 000104, SG | 30 / 10 / 40 / 20 | DELTA P1 30%, P3 40%; P2/P4 below threshold |

Party names are DEMO <CODE> PERSON Pn; officers DEMO <CODE> OFFICER 1/2. All direct
parent totals are exactly100%. ALPHA root -> P1/P2 60/40. BETA root -> H1/H2/P1 50/30/20;
H1 -> P1..P6 20/50/10/10/5/5; H2 -> P3..P6 40/30/20/10.
GAMMA: the registry seed lists partners P1..P6 by name and role only, with no ownership links or
percentages (a partnership register never carries shares). The 30/25/20/10/10/5 split comes only from the
partnership agreement and counts only after the RM confirms it. DELTA root -> H1/P4 80/20;
H1 -> H2/P3 50/50; H2 -> P1/P2 75/25. The existing Decimal engine owns all calculations.
No hierarchy/related-party creation is dispatched to GoldTier.

## Manual journey

1. Sign in as the authorized RM and start a new case using the exact name/UEN/SG above.
2. Expect successful Sandbox Search with zero candidates -> NO_MATCH -> completed
   Existing-customer search. If a real candidate exists, follow truthful exact/candidate
   resolution; never force NO_MATCH. Rejection/timeout/malformed is a failure, not absence.
3. Expect registry CACHE_HIT/database reuse, COMPLETE normalized evidence, MOCK source,
   retained local-synthetic provenance and zero ACRA HTTP operations (including token calls).
4. Upload the matching scan and finish intake. Classification is expected to auto-bind from current trusted
   document evidence: Alpha/Beta/Delta Company - Private / Corporate; Gamma Partnership -
   Unregulated / Corporate. No classification click is needed. Manual selection is fallback
   only when a label is unsafe/missing/conflicting; safe automatic fields remain retained.
5. Expect LOCAL_TESSERACT_OCR, exact identity
   matches and eligible fields AUTO_CONFIRMED at frozen score>=threshold (default0.85);
   no Accept clicks or manual ownership declaration. Investigate any OCR mismatch truthfully.
   Gamma and Government differ here; follow the D-101 sections below, then continue from step 6.
6. Inspect the graph and provisional candidates. Submission readiness = Complete;
   GoldTier submission package = Prepared/Complete. The remaining blocker
   should be final Review & Send confirmation only.
7. Review & Send once. NO_MATCH creates exactly one Shell, retains its returned GoldTier
   ID, then Policy, conditional Amend only if the existing plan requires it, and exact-ID
   readback. The tested identity-only package skips Amend.
8. Verify the completed case shows GoldTier ID, new customer created, readback verified
   and submission confirmed. Use the existing read-only Verify in Sandbox action to
   search that retained ID; provider response must identify the same customer. Never
   resend to verify. Completed or uncertain mutations cannot replay.

Marketplace sample UENs are operation-specific and are not coherent whole-company
fixtures by assumption. These local synthetic fixtures (four companies/partnership plus the Government case) are the controlled happy
paths; Garden remains its separately bounded partial/LOCAL supplement example.
Review & Send is final local approval; GoldTier KYC/four-eye approval, legal UBO,
Production/Live integration, and original-document transfer remain outside this demo.

## Atlas name and fresh database prerequisites

`clm_uat_<24 lowercase hex>` is32 ASCII bytes, below the38-byte Atlas limit.
The previous longer `clm_uat_registry_...` format is refused. Never use `clm_poc`.
Before startup/seed, separately provision the approved Mongo connection in the process,
network access/TLS and a database user authorized for the new disposable database.
Authentication database/authSource must match the user's provisioned authentication
source; a new empty database does not create an application login or Mongo user.
Normal app initialization must bootstrap the existing administration/profile/policy
repositories with separately provisioned synthetic login hashes. Do not copy credentials,
hashes or connection strings into this guide, fixtures, shell transcripts or Git.

## D-101 Partnership journey (Gamma)

1. Start the Gamma case with its exact name/UEN/SG. The registry evidence is the local synthetic seed
   (PARTIAL: complete entity profile, partners by name and role, no shareholding), never a cache hit.
2. Upload `demo-gamma-scanned.pdf` and `demo-gamma-partnership-agreement.pdf`, then finish intake.
   Classification auto-binds Partnership - Unregulated / Corporate from the scan.
3. Ownership & UBO shows the banner "Partner shares from partnership agreement, awaiting RM confirmation".
   The agreement rows are suggestions only; nothing is accepted automatically.
4. Open the manual ownership evidence form: it defaults to the agreement's partner rows (P1..P6,
   30/25/20/10/10/5, natural persons). Check them and **Submit manual ownership evidence**.
5. The banner becomes "Partner shares from partnership agreement, RM-confirmed". The Decimal engine shows
   P1 30% and P2 25% at or above the policy threshold (default 25%); P3..P6 below it.
6. Fail-closed cross-checks keep the case blocked and send it to review when: no current reviewed
   agreement, low confidence, a different entity, a registry partner missing from the agreement, an
   extra partner, a duplicate partner, a zero/negative share, a total other than exactly 100, or a
   confirmed declaration that differs from the agreement.

## D-101 Government journey (Demo Parks)

`demo-parks-government-status.pdf`: DEMO PARKS FYP TEST AUTHORITY, T99FY0105G (fictional T-format; the
letters are not an official code), `Founding Instrument:`, `KYC Customer Type: Government`,
`Client Segment: DI - Government`, two display-only authorised signatories. It replaces the retired
classification-only `demo-government-scanned.pdf` (DEMO GOVERNMENT FYP TEST AUTHORITY, 209990105E).

1. Start the case as DEMO PARKS FYP TEST AUTHORITY / T99FY0105G / SG. Government bodies are not
   ACRA-registered: identity comes from the local synthetic seed, labelled
   "Local synthetic identity: not ACRA-registered; government status from reviewed document".
   No ACRA verification is claimed.
2. Upload the status letter and finish intake. Classification auto-binds Government / DI - Government;
   a Government label on a company or partnership legal form is UNSAFE and goes to manual review.
3. The Ownership & UBO stage holds the **Government status** step instead of an ownership analysis
   (MAS Notice 626 para 6.12: confirm it is a Singapore Government entity). It shows the reviewed
   founding instrument and signatories (display only; not sent to GoldTier, no ownership graph).
4. **Confirm Government status** (authenticated RM, version-checked). Without a current reviewed
   status document, or without this confirmation, the case stays blocked
   (`GOVERNMENT_STATUS_REQUIRED`). It is never set automatically or from the label alone.
5. Readiness then completes with ownership evidence "Government status confirmed" and 0 UBO
   candidates; continue with Review & Send as in step 7. A foreign government body is out of scope
   and keeps normal checks.

Not legal UBO policy (Q-004), not ACRA capability (Q-012), not Live.

## Evidence and recovery

Automatic choices retain document ID/version/event count, page/reference, exact labelled
value, method/quality/score, classification time and frozen case policy/vocabulary versions.
The browser shows Automatically classified from document or Selected by user.
Three bounded automatic KYC types are Company - Private, Partnership - Unregulated and
Government; segment always comes from an explicit sponsor-vocabulary document value.
No entity-form-to-segment mapping follows from this pack. Fixed values never come from OCR.
Classification save is local only: provider calls0, target mutation attempts0. Only
explicit final Review & Send authorizes ledger execution. Actual uncertain Shell/Policy
outcomes freeze inputs and prohibit replay; the UI identifies the earlier operation.
An empty retained intent is not an uncertain mutation. The original owner UAT ledger
was not accessed; its historical cause remains unknown under this bounded assignment.

If an earlier user choice disagrees with newly trusted explicit document labels, resolve
classification review before Send. The system retains the source choice and blocks the
conflict; it does not silently pick a source. Stale confirmation history cannot mark a
blocked current package Prepared, and the server rechecks classification at snapshot
creation before target mutation.

The same review protection applies in Mock mode whenever explicit classification labels
or choices exist. A partial profile or conflict cannot prepare/freeze a submission.
Legacy Mock examples without classification labels or choices remain supported.

## Current classification conflict review — 2026-10-06

If new trusted documents disagree, Submission readiness shows review required, the
package is not prepared and Final review & send is not reached/blocked. Target
classification shows the current trusted vocabulary values. Review them and explicitly
Save target classification, including a same-value choice where compatible. This is a
new decision tied to the displayed current evidence, not a silent source winner.
After review, readiness/package may complete; Final Review & Send still remains. A
later relevant trusted document makes the review stale again. The existing pre-send
intake can accept that document before a frozen target intent; all freeze rules remain.
A stale browser review is refused and current evidence reloaded. Unsafe low-score
evidence remains separate from trusted contradiction. No classification action calls
external providers or target writes. Government cases use the D-101 Government status step, not a
control/share analysis.
