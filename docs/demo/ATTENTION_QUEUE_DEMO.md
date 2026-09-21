# Blocker-aware Attention Queue demo

## Five-minute synthetic journey

Use only the repository's synthetic fixtures and normal local launcher. Start from the
repository root:

```powershell
.\scripts\start_demo_windows.bat
```

Confirm the banner truthfully says ACRA Mock, IDP Local POC, Ownership Mock, and GoldTier
Mock. Sign in as an existing case-capable synthetic user. Do not use customer, sponsor,
or confidential provider data.

1. Create an SG onboarding case with UEN `202400001A` and
   `apps/backend/tests/fixtures/uat/low-confidence.pdf`. Start processing and wait for the
   case to pause for review.
2. Create a second SG onboarding case with UEN `202400006F` and
   `apps/backend/tests/fixtures/uat/cycle-uen-clean.pdf`. Start processing and wait for
   the case to pause for review.
3. Open **Cases**. In **Open business exception type**, choose
   **Document low confidence**. The first case remains and displays that type; the cycle
   case is absent.
4. Choose **Ownership cycle**. The second case remains and displays that type; the
   low-confidence case is absent.
5. Choose **All types (no type filter)**. Both cases return. Use the native **Open** link
   on the ownership-cycle row to enter the existing case-detail review/recovery and
   evidence workbench.

The queue shows retained open business-exception categories. It does not assign work,
rank risk or urgency, create an SLA, approve a case, or imply that a row with no recorded
open business exceptions is healthy. Technical-failure and recovery states remain
distinct from business-exception categories.

## Stop and cleanup

```powershell
.\scripts\stop_demo_windows.bat
```

The default demonstration is process-local. A verified stop removes only the
launcher-owned backend/frontend process trees; it does not exercise a Live registry,
vendor OCR, external ownership service, PingFed, or Live GoldTier integration.
