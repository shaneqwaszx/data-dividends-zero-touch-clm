# Quick Start - Running the Improved UI

## Prerequisites
- Node.js 22+ for frontend
- Python 3.12+ for backend
- Modern browser (Chrome, Firefox, Safari, Edge)

## Starting the Application

### 1. Start Backend Server
```bash
cd apps/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: `http://localhost:8000`

### 2. Start Frontend Development Server
```bash
cd apps/frontend
npm run dev
```

Frontend runs at: `http://localhost:5173`

### 3. Open in Browser
Navigate to: `http://localhost:5173`

---

## Key UI Improvements to Demo

The app now opens on **Start onboarding**. Select up to 20 browser-provided PDF, DOCX,
or UTF-8 TXT files (5 MiB each, 25 MiB total), or use **Select folder** as a browser
convenience. Each file is uploaded and analysed independently; processing beyond the
Document stage begins only after the full intended set has uploaded successfully. The
Start page keeps the created case ID visible and shows creation, upload, analysis,
review, completion, or safe-failure progress.

The **Dashboard** lists every case retained by the current backend process. The
**Review** tab lists every backend case in `WAITING_FOR_REVIEW`; selecting an item opens
that exact case. Restarting the backend clears both lists. They are not durable history,
production assignment, or production case management.

### 1. Exception Handling (Try: DOCUMENT_DISCREPANCY scenario)
1. Open the app
2. Select **"Document discrepancy"** from Demo Controls dropdown
3. Upload any PDF
4. Wait for automation to reach DOCUMENT stage and stop
5. Select **Review queue** (or use the dashboard's **Review active exception** action)
6. **See:**
   - ⚠️ Clear "Human review required" header
   - Color-coded blocker cards with explanations
   - Evidence comparison cards showing registry vs. document
   - Confidence scores displayed
   - "Upload corrected document" option

### 2. Ownership Graph Visualization (Try: OWNERSHIP_CYCLE scenario)
1. From Demo Controls: Select **"Ownership cycle"** scenario
2. Start onboarding
3. Wait for automation to reach OWNERSHIP stage
4. View **SponsorOwnershipEvidence** section
5. **See:**
   - Graph visualization showing ownership hierarchy by level
   - Blue boxes = Legal entities
   - Green boxes = Natural persons
   - Yellow highlighted boxes = UBO candidates with 🏆 icon
   - Ownership percentages shown
   - Warning section explaining the cycle issue

### 3. Better Error Messages (Try: LOW_CONFIDENCE scenario)
1. From Demo Controls: Select **"Low-confidence document"**
2. Start onboarding
3. Navigate through workflow
4. **See:**
   - Errors appear with emoji indicators
   - 📄 Document extraction issues clearly explained
   - ⚠️ Confidence thresholds visible
   - Specific field issues highlighted

### 4. Clean Primary UI
1. Default view shows professional primary workflow
2. Demo controls are hidden in **collapsible section** (Details dropdown)
3. Legacy diagnostics moved to: Demo Controls → Legacy manual diagnostics
4. Main dashboard focuses on zero-touch automation

---

## Test Scenarios Available

Use Demo Controls dropdown to select test scenarios:

| Scenario | What it Demonstrates |
|----------|---------------------|
| **STRAIGHT_THROUGH** | Perfect happy path (no exceptions) |
| **DOCUMENT_DISCREPANCY** | Document vs. Registry mismatch |
| **MULTIPLE_DOCUMENT_BLOCKERS** | Multiple field issues at once |
| **LOW_CONFIDENCE** | Low extraction confidence |
| **OWNERSHIP_CYCLE** | Circular ownership (with graph viz) |
| **OWNERSHIP_INCOMPLETE** | Missing ownership data |
| **MULTIPLE_OWNERSHIP_PATHS** | Complex UBO candidate display |
| **EXISTING_PARTY** | Duplicate party detection |
| **TARGET_FAILURE** | GoldTier submission failure |
| **PARTIAL_AMEND** | Partial field update scenario |
| **RECOVERY** | Recovery without full replay |
| **TECHNICAL_FAILURE** | IDP technical failure handling |

---

## Navigation Guide

### Dashboard Tab
- **Recent CLM cases:** Open any case retained by the current backend process
- **Start onboarding:** remains the first/default tab; enter UEN and select documents
- **Onboarding Progress:** Shows 5-stage workflow (Registry → Document → Ownership → Readiness → GoldTier)
- **Case Summary:** Key metrics and active exceptions

### Review Tab
- **Process-local review queue:** all authoritative `WAITING_FOR_REVIEW` cases
- **Human Review Panel:** Exception handling with explanations
- **Document Evidence:** Field extraction results with confidence scores
- **Ownership Evidence:** 
  - **Graph visualization** (visual hierarchy by level)
  - **Detailed table** (relationship details)
  - **UBO candidates** (with classification)
- **CLM Journey:** Readiness status and GoldTier submission

### Logs Tab
- Automation timeline with events and timestamps

### Account Tab
- Placeholder for user profile

---

## Visual Indicators (Updated)

### Colors
- 🟦 **Blue:** Legal entities, links, actions
- 🟩 **Green:** Natural persons, success states
- 🟨 **Yellow:** UBO candidates, warnings
- 🔴 **Red:** Mismatches, errors
- ⚫ **Gray:** Registry data, neutral info

### Icons
- ⚠️ Warning/Review required
- 🏆 UBO candidate
- ✓ Match/Complete
- ⚙️ Processing
- 📄 Document
- 👤 Natural person
- 🏢 Legal entity

### Badges
- **[MATCH]** - Extracted data matches registry
- **[MISMATCH]** - Extracted data differs from registry
- **[MISSING_FROM_DOCUMENT]** - Field not in document
- **[MISSING_FROM_REGISTRY]** - Field not in registry

---

## Common Tasks

### View Exception Details
1. In SponsorCaseSummary, click exception in "Active exceptions" list
2. HumanReviewPanel opens with all details
3. Read explanation and evidence comparison
4. Choose resolution action or upload replacement document

### Understand Ownership Structure
1. Scroll to SponsorOwnershipEvidence section
2. View SimpleOwnershipGraph for visual hierarchy
3. Hover over nodes to see entity details
4. Review "Detailed ownership structure" table for edge details
5. Check "Natural-person ownership threshold results" for UBO candidates

### Resolve a Document Exception
1. In HumanReviewPanel, review blockers and evidence
2. **Option A:** Click "Keep registry values" to proceed with registry data
3. **Option B:** Click "Request additional information" to wait for manual input
4. **Option C:** Upload replacement PDF using "Upload corrected document" section
5. System re-evaluates and may proceed or raise new exceptions

### Check Readiness for Submission
1. In ClmJourney section, see "Readiness evaluation" status
2. If blockers exist, they're listed with explanations
3. Click blocker to see affected field and remediation
4. Once ready, "Submit to GoldTier" button becomes active

---

## Troubleshooting

### Frontend not loading?
- Check: `http://localhost:5173` loads in browser
- Check: Backend is running on `http://localhost:8000`
- Check: VITE_API_BASE_URL environment variable (defaults to empty string for localhost)

### Automation stuck on RUNNING?
- Check browser console for errors
- Polling happens every 2 seconds automatically
- If stuck for >30s, check backend terminal for errors
- Refresh browser to reset state

### Demo controls not visible?
- Set `VITE_DEMO_CONTROLS_ENABLED=true` environment variable
- Rebuild frontend: `npm run build`
- Default: Demo controls visible only in development mode

### Ownership graph not showing?
- Check that OWNERSHIP stage reached
- Verify ownership data loaded successfully
- Look for warnings/errors in OwnershipSummary
- Graph only displays if parties and relationships exist

---

## Build Commands

### Development
```bash
# Frontend dev server
cd apps/frontend && npm run dev

# Backend dev server
cd apps/backend && python -m uvicorn app.main:app --reload
```

### Production Build
```bash
# Frontend production build
cd apps/frontend && npm run build

# Backend production
cd apps/backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run contract tests
cd /repo && python -m pytest tests/contract/ -xvs

# Specific phase tests
python -m pytest tests/contract/test_phase_06_zero_touch_contract.py -xvs
python -m pytest tests/contract/test_phase_04_ownership_contract.py -xvs
```

---

## Environment Configuration

### Frontend (.env or vite.config.ts)
```
VITE_API_BASE_URL=http://localhost:8000
VITE_DEMO_CONTROLS_ENABLED=true
```

### Backend (pyproject.toml or .env)
```
DEBUG=true
ENVIRONMENT=development
MOCK_CONNECTORS_ENABLED=true
```

---

## Performance Notes

- **Frontend bundle:** 202KB (60KB gzipped) - fast initial load
- **Polling interval:** 2 seconds during automation
- **Build time:** ~360ms with Vite
- **Test suite:** ~1 second for all contract tests
- **Graph render:** Instant for up to 50 nodes

---

## Support & Debugging

### Check Build Status
```bash
cd apps/frontend && npm run build  # Should complete without errors
```

### Verify Tests
```bash
cd /repo && python -m pytest tests/contract/test_phase_06_zero_touch_contract.py -v
# Should show 3 tests PASSED
```

### View Backend Logs
```bash
# Terminal running backend will show request/response logs
# Safe logs only - no credentials or raw KYC/PII
```

### Browser DevTools
- **Console:** Check for JavaScript errors
- **Network:** Verify API calls and responses
- **Application:** Check localStorage (if using)
- **Accessibility:** Run WCAG audit

---

## Next Demo Script

### 5-Minute Demo Flow
1. **Intro (1 min):** Show dashboard, explain 5 stages
2. **Happy Path (1 min):** STRAIGHT_THROUGH scenario end-to-end
3. **Exception Handling (1.5 min):** DOCUMENT_DISCREPANCY with manual review
4. **Ownership Visualization (1 min):** OWNERSHIP_CYCLE with graph display
5. **Recovery (0.5 min):** Show document replacement & reprocessing

This demonstrates all key improvements without overwhelming the audience.
