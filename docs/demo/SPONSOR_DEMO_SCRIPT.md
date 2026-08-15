# Sponsor Demo Script (5–10 minutes)

## Before the room

Run `scripts/start_demo_windows.bat`, confirm both URLs, select only files under
`apps/backend/tests/fixtures/uat/`, and keep this statement visible: **Mock and
provisional POC; not Ready-for-Approval or live interoperability.**

## 1. Problem (about 45 seconds)

Corporate onboarding repeats registry checks, document comparison, ownership analysis,
readiness decisions, and target handoffs. This POC asks whether deterministic evidence
can move automatically while exceptions stop for a human.

## 2. Clean zero-touch case (2 minutes)

1. Choose `STRAIGHT_THROUGH`, UEN `202400001A`, and
   `clean-company-profile.pdf`.
2. Select **Start onboarding** once.
3. Let Registry, Document Verification, Ownership & UBO, Readiness, and Mock GoldTier
   progress automatically.
4. Point to `Human interventions after Start: 0` and the ordered safe timeline.
5. State precisely: the result is `MOCK_GOLDTIER_SUBMITTED`, not approval.

## 3. Exception-only HITL (2 minutes)

1. Choose `DOCUMENT_DISCREPANCY` and `legal-name-mismatch.pdf`.
2. Start and show the automatic pause with separate registry/document values.
3. Explain that the system does not autonomously override conflicting source evidence.
4. Select the only advertised `Keep registry values` action.
5. Show automatic resume and `Human interventions after Start: 1`.

Optional safety contrast: run `LOW_CONFIDENCE`. Show that no click-through action is
invented and the target-call export remains empty.

## 4. Auditability (1 minute)

Show the sponsor case summary, blocker/warnings, server-authored metrics, event order,
and safe UAT export. The export contains no PDF content, provider payload, secret,
endpoint, or private fingerprint.

For ownership arithmetic, use `MULTIPLE_OWNERSHIP_PATHS`: direct 20% plus indirect 20%
aggregates once to 40% in the detailed development view/tests. The classification is
provisional, not a legal UBO finding.

## 5. Recovery and target safety (1 minute)

Run `RECOVERY`. Show `RECOVERY_PENDING` after the Mock operations, then select
**Complete safe recovery**. Export before and after: `SEARCH, SHELL, POLICY, AMEND`
appears once in both; only local finalization is reconciled.

## 6. Integration handoff and boundaries (1–2 minutes)

Open `docs/integration/INTEGRATION_HANDOFF.md` and
`PROVIDER_REPLACEMENT_GUIDE.md`. Explain that Registry, IDP, Ownership, and GoldTier are
replaceable adapters and generic orchestration remains unchanged.

Close with explicit boundaries:

- Mock GoldTier and Mock IDP/ownership.
- ACRA Mock by default; sandbox-shaped seam is not verified live access.
- Provisional document/readiness and UBO rules.
- Live dependencies are listed by Q-ID.
- No Ready-for-Approval, autonomous approval, related-party write, or live-system claim.
