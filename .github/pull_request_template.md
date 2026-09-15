## Change

- Phase/change name:
- Change class(es):
- Purpose and explicit non-goals:
- Feature branch / initial BASE_SHA / latest origin/main SHA:

## Architecture and authority

- Canonical architecture owner(s) affected:
- Architecture invariant changed: Yes / No — detail:
- ADR required: Yes / No — link/reason:
- Sponsor authority used:
- Project-defined/provisional behavior:
- Open questions/blockers:
- External providers: name / mode / classification (Mock, Local, Sandbox, Partial, Dormant, Live):

## Impact

- API/shared types/configuration:
- Security/auth/RBAC/data/logging:
- Persistence/schema/CAS/restart/deletion:
- Hotspot/dependency/CI files and why necessary:

## Verification

<!-- Exact commands and results; state skipped/unavailable checks. -->

- Focused and broad affected checks:
- Contract/security/physical/regression evidence:
- `python scripts/check_project_state.py`:
- `python scripts/check_architecture.py`:
- `python scripts/pre_pr_check.py`:
- Independent QG/re-QG:

## Integration and context

- Latest main integrated and conflicts reconciled:
- `PROJECT_STATE` / `ARCHITECTURE` / workflow context refreshed or not applicable:
- Mock/sandbox/live labeling reviewed:
- Known limitations and reviewer attention:

Final merge is performed by a human repository owner.
