# UI V2 Onboarded Responsive Remediation

## 1. Root cause

RQG-01 was caused by the visually hidden `Open` text in the last Onboarded table header, not by the table wrapper's normal intrinsic sizing.

The shared `.sr-only` rule uses `position: absolute`. The Onboarded scroll wrapper was `position: static`, so the far-right hidden span had no offset parent and was positioned against the initial containing block at its static table-cell location. At 480px, the observed values were:

- wrapper: 435px client width, 1100px scroll width, `min-width: 0`, `max-width: 100%`, `overflow-x: auto`
- table: 1100px wide, from x=15 to x=1115
- hidden span: x=1029.45 to x=1030.45, `position: absolute`, no offset parent
- document: 1030px scroll width / 465px client width

The table itself was already contained by the wrapper. The out-of-flow hidden span alone extended the document to approximately its x-coordinate. This accounts exactly for the reproduced recurrence at every narrow width.

## 2. Files changed

- `apps/frontend/src/pages/OnboardedClients.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `.ai-pipeline/reports/UI_V2_RESPONSIVE_REMEDIATION.md`

No CSS, backend, lifecycle-script, security-tooling, API-contract, or unrelated file was changed.

## 3. Exact CSS/layout correction

The existing scroll containment CSS was inspected and retained because it was already correct:

```css
.table-card, .table-scroll { max-width: 100%; overflow-x: auto; }
.onboarded-table { min-width: 1100px !important; }
```

The layout correction removes the escaping absolute box at its canonical owner. The header changed from an absolutely positioned `.sr-only` descendant to an accessible name on the table-header element:

```tsx
export function OnboardedActionColumnHeader() {
  return <th aria-label="Open" />;
}
```

This retains the accessible `Open` header name, removes the out-of-flow box, preserves the 1100px table, and leaves horizontal scrolling inside the intended wrapper. No page-wide `overflow:hidden`, clipping, column compression, or desktop redesign was introduced.

A focused test proves the rendered header retains `aria-label="Open"` and contains no `.sr-only` box. Browser measurements, rather than the structural test, provide the pixel-containment evidence.

## 4. Why Cases did not exhibit the defect

Cases uses the same `table-card table-scroll` structure and its table remains 980px wide at narrow viewports. It did not contain any absolute `.sr-only` descendant in the far-right intrinsic-width region.

At the pre-fix 480px comparison:

- Cases document: 480/480
- Cases wrapper: 450px client width / 980px scroll width
- Cases table: 980px
- absolute/`.sr-only` descendants in the Cases wrapper: 0

Therefore Cases demonstrated that the shared overflow wrapper already contained a wide table correctly. Onboarded's extra out-of-flow header label was the differentiating recurrence generator.

## 5. 1280 measurements

| Measurement | Result |
|---|---:|
| Document scroll width | 1280px |
| Document client width | 1280px |
| Onboarded scroll-container client width | 1223px |
| Onboarded scroll-container scroll width | 1223px |
| Onboarded table width | 1222.81px |

Result: PASS. No document overflow; the table naturally fills the desktop container.

## 6. 1024 measurements

| Measurement | Result |
|---|---:|
| Document scroll width | 1024px |
| Document client width | 1024px |
| Onboarded scroll-container client width | 967px |
| Onboarded scroll-container scroll width | 1100px |
| Onboarded table width | 1100px |

Result: PASS. The document remains bounded while the table scrolls inside its 967px container.

## 7. 760 measurements

| Measurement | Result |
|---|---:|
| Document scroll width | 760px |
| Document client width | 760px |
| Onboarded scroll-container client width | 722px |
| Onboarded scroll-container scroll width | 1100px |
| Onboarded table width | 1100px |

Result: PASS. The document remains bounded while the table scrolls inside its 722px container.

## 8. 480 measurements

| Measurement | Result |
|---|---:|
| Document scroll width | 480px |
| Document client width | 480px |
| Onboarded scroll-container client width | 450px |
| Onboarded scroll-container scroll width | 1100px |
| Onboarded table width | 1100px |

Result: PASS. The former approximately 565px page overflow is eliminated. The table retains its wide intrinsic layout and scrolls only within the 450px wrapper.

## 9. Regression measurements for Cases/Audit/Client/Case Detail

Document `scrollWidth / clientWidth` measurements:

| Viewport | Cases | Audit | Client record | Case Detail |
|---:|---:|---:|---:|---:|
| 1280 | 1280/1280 | 1280/1280 | 1265/1265 | 1265/1265 |
| 1024 | 1024/1024 | 1024/1024 | 1009/1009 | 1009/1009 |
| 760 | 760/760 | 760/760 | 745/745 | 745/745 |
| 480 | 480/480 | 465/465 | 465/465 | 465/465 |

Cases also retained its intended contained-scroll behavior:

| Viewport | Container client width | Container scroll width | Table width |
|---:|---:|---:|---:|
| 1280 | 1223px | 1223px | 1222.81px |
| 1024 | 967px | 980px | 980px |
| 760 | 722px | 980px | 980px |
| 480 | 450px | 980px | 980px |

Other page responsive regressions: 0

## 10. Frontend test/type/build results

- TDD RED: the focused action-header test failed before the exported accessible header existed.
- TDD GREEN: focused test passed, 1 passed / 37 skipped.
- `npm ls --all`: PASS; expected optional-platform dependency notices only.
- `npm run typecheck`: PASS.
- `npm test`: PASS; 2/2 files and 96/96 tests passed (`App.test.tsx` 58, `UiV2Integration.test.tsx` 38).
- `npm run build`: PASS; 42 modules transformed, CSS 55.28kB, JavaScript 231.77kB.

Frontend failures: 0

## 11. Visual-parity assessment

The 1280px desktop rendering was visually inspected after the fix. The Autoboard shell, navigation, account/operator, heading, explanatory copy, jurisdiction/risk/search controls, risk-disabled treatment, table card, column order, typography, spacing, row content, Open button, and Mock/POC wording are unchanged.

At 1024, 760, and 480, the table retains its 1100px intrinsic width and existing column layout. Only the page-level overflow is removed; users scroll the intended table wrapper to reach later columns.

Material desktop visual changes: 0

## 12. Git hygiene

- Branch: `integration/ui-v2-finalization`
- Starting/current committed HEAD: `a1f83a3c2b52e4a163979b5d4fd076a4070cb6b0`
- Staged files: 0
- Commits created: 0
- Pushes, merges, rebases, resets, stashes, or cleans: 0
- Backend files changed: 0
- `scripts/demo_lifecycle.ps1` changed: no
- Secret tooling changed: no material diff and no task edit
- API contracts changed: 0
- The unrelated filename beginning `e workspace and multi-document intake` was not opened, staged, modified, or deleted.
- Pre-existing reports, cache directories, and scanner EOL/stat indications were left untouched.
- Browser viewport override was reset; local verification servers were stopped and ports 8001/5175 were closed.

## 13. Readiness

```text
Onboarded document-overflow defects: 0
Other page responsive regressions: 0
Material desktop visual changes: 0
Frontend failures: 0
```

RQG-01 is repaired at its canonical layout owner with direct browser evidence at every required width. The branch is ready for the bounded Onboarded responsive re-quality gate; no broader UI, backend, lifecycle, or integration approval is implied.

READY FOR ONBOARDED RESPONSIVE RE-QUALITY GATE
