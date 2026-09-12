# Reflection

The phase replaced several static/runtime-global owners without adding compatibility
fallbacks. The main implementation judgment was to retain `TEAM_A`, `TEAM_B`, and the
five Phase 13 profile definitions only as persisted IDs/bootstrap input while moving
runtime authority to repositories. That keeps legacy behavior stable without creating
two mutable sources of truth.

The highest-risk boundaries were credential persistence, session invalidation, policy
retroactivity, and schema compatibility. Repository-held hashes remain authoritative,
session records revalidate `security_version`, policies bind once per case, and v1/v2
readers synthesize legacy policy values without rewriting storage.

One verification command initially inherited an ambient package path and reached the
concurrent Phase 14 checkout. The corrective control was to pin all later Python
commands to this workspace explicitly. No Phase 14 implementation content was used.

The implementation is ready for owner review with bounded gaps: physical Mongo awaits
an explicit safe URI, repository-wide formatting debt predates this phase, and
`main.py` remains an oversized composition root. The next valuable action is an
independent quality gate on this exact unstaged tree, followed by separately authorized
Phase 14 integration when Phase 14 reaches `origin/main`.
