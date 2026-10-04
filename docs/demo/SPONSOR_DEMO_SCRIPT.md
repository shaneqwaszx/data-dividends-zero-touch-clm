# Sponsor Demo Script (5–10 minutes)

Current sponsor entry point: [Final Sponsor Demo Runbook](FINAL_SPONSOR_DEMO_RUNBOOK.md)
and [Final UAT Acceptance Matrix](FINAL_UAT_ACCEPTANCE_MATRIX.md). The retained instructions
below preserve their historical fixture/evidence boundaries.

## Before the room

Run `scripts/start_demo_windows.bat`, confirm both URLs, select only files under
`apps/backend/tests/fixtures/uat/`, and keep this statement visible: **Mock and
provisional POC; not Ready-for-Approval or live interoperability.**

## 1. Problem (about 45 seconds)

Corporate onboarding repeats registry checks, document comparison, ownership analysis,
readiness decisions, and target handoffs. This POC asks whether deterministic evidence
can move automatically while exceptions stop for a human.

## 2. Clean zero-touch case (2 minutes)

1. Enter UEN `202400001A` and upload `clean-company-profile.pdf`.
2. Select **Start onboarding** once.
3. Let Registry, Document Verification, Ownership & UBO, Readiness, and Mock GoldTier
   progress automatically.
4. Show the actual extracted document values, registry comparison, Local POC confidence,
   ownership edge/path evidence, readiness, and server-authored Mock GoldTier operations.
5. Point to `Human interventions after Start: 0` and the ordered safe timeline.
6. State precisely: the result is `MOCK_GOLDTIER_SUBMITTED`, not approval.

## 3. Exception-only HITL (2 minutes)

1. Use the same UEN and upload `address-mismatch.pdf`.
2. Start and show the automatic pause with separate registry/document values.
3. Explain that the system does not autonomously override conflicting source evidence.
4. Upload `clean-company-profile.pdf` as a corrected replacement, or use the permitted
   `Keep registry values` action.
5. Show fresh evidence, the old document marked **SUPERSEDED**, automatic resume, and
   the current document marked **CURRENT**.

## 4. Auditability (1 minute)

Show the sponsor case summary, blocker/warnings, server-authored metrics, event order,
and safe UAT export. The export contains no PDF content, provider payload, secret,
endpoint, or private fingerprint.

For ownership-cycle evidence, use UEN `202400006F` with `cycle-uen-clean.pdf`. The
document passes first; the independent synthetic ownership graph then reports `CYCLE`.
The classification remains provisional, not a legal UBO finding.

## 5. Recovery and target safety (1 minute)

Use UEN `202400005E` with `second-case-isolation.pdf`. Show server-authored `SEARCH /
MATCH_FOUND` and that Shell, Policy, and Amend are `NOT_ATTEMPTED`.

## 6. Integration handoff and boundaries (1–2 minutes)

Open `docs/integration/INTEGRATION_HANDOFF.md` and
`PROVIDER_REPLACEMENT_GUIDE.md`. Explain that Registry, IDP, Ownership, and GoldTier are
replaceable adapters and generic orchestration remains unchanged.

Close with explicit boundaries:

- Mock GoldTier, input-driven synthetic ownership, and Local POC text-PDF IDP.
- ACRA Mock by default; sandbox-shaped seam is not verified live access.
- Provisional document/readiness and UBO rules.
- Live dependencies are listed by Q-ID.
- No Ready-for-Approval, autonomous approval, related-party write, or live-system claim.
Developer/Test Controls are fault injection and deterministic regression tooling, not
the way a presenter selects normal onboarding outcomes.
