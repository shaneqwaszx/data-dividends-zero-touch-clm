# Documentation Archive

Superseded documents kept for history. Nothing here describes the current system, and
no script, test, or CI job reads these files. For current behavior, start from the
[documentation index](../README.md).

## `2026-08-ui-improvements/`

A one-off UI improvement pass dated 2026-08-25, before the Phase 08 runtime baseline.
Four of these files used to sit in the repository root.

| File | What it was |
|---|---|
| `UI_IMPROVEMENTS_INDEX.md` | Index for the other five files |
| `BUILD_COMPLETE.md` | Short status summary |
| `EXECUTION_SUMMARY.md` | Full delivery report |
| `UI_IMPROVEMENTS_SUMMARY.md` | Feature and design-system notes (formerly `docs/`) |
| `UI_DEMO_QUICK_START.md` | How to run the improved UI (formerly `docs/`) |
| `COMPREHENSIVE_UI_AUDIT_REPORT.md` | UI and functionality gap audit |

Why they are archived:

- The audit and the feature notes describe `DocumentPanel` and `OwnershipPanel`
  components that no longer exist in `apps/frontend/src`.
- Run and demo steps are superseded by [`demo/DEMO_RUNBOOK.md`](../demo/DEMO_RUNBOOK.md)
  and [`demo/SPONSOR_DEMO_SCRIPT.md`](../demo/SPONSOR_DEMO_SCRIPT.md).

The files are archived unchanged, so paths written inside them (for example
`docs/UI_IMPROVEMENTS_SUMMARY.md`) refer to their old locations.
