# Repository skill routing

Repository skills are focused workflows, not extra authority. `AGENTS.md`, the assigned
task/planner, current source/tests, contracts, and decisions remain controlling. Load
only the skills triggered by the work.

| Skill | Use when | Boundary |
|---|---|---|
| `fyp-phase-execution` | Ordinary bounded FYP feature, phase, or remediation implementation | Canonical implementation coordinator; stops before independent review or the next phase |
| `fyp-quality-gate` | Independent review of completed implementation or governance content | Reconstructs requirements and issues the sole `PASS`, `PASS WITH MINOR FIXES`, or `FAIL` verdict; does not remediate |
| `worktree-task` | Concurrent checkout isolation or worktree setup | Decides whether a worktree is necessary and protects existing worktrees |
| `architecture-change-review` | New/replaced owner, service, repository, provider, framework, dependency direction, or durable boundary | Runs before implementation; tests reuse and ADR need |
| `ci-failure-triage` | Failing CI job or repository check | Finds the first causal failure before any authorized fix |
| `external-provider-integration` | External provider, transport, auth, sandbox, contract, adapter, or Live-mode behavior | Composes contract and security review; never upgrades evidence labels by assumption |
| `frontend-state-cache-change` | React Query keys, authenticated cache scope, cancellation, invalidation, mutation retry, or stale responses | Owns frontend server-state/session-cache safety |
| `persistence-schema-change` | Durable schema, repository semantics, CAS/index, migration, restart, or recovery | Owns persistence safety and guarded physical evidence |
| `integration-security-review` | Credentials, TLS, auth, uploads, external payloads, KYC/PII, logging, or browser error projection | Review-only unless remediation is explicitly assigned |
| `integration-safe-development` | Branch synchronization, conflict resolution, integration, or pre-PR readiness | Canonical integration/pre-PR workflow; uses `references/PRE_PR_CHECKLIST.md` |
| `poc-regression-check` | Accepted POC scenarios, terminal states, ordering, call stopping, or truthful mode labels | Verifies the canonical regression catalogue after affected work |
| `sponsor-contract-reconciliation` | Conflicting sponsor/API artefacts, mappings, mandatory fields, or authority | Reconciles evidence and stops dependent work rather than guessing |
| `phase-closeout-context-refresh` | Accepted or merged phase context/state refresh | Updates current truth only at the appropriate acceptance/merge state |

Typical composition for implementation is:

`fyp-phase-execution -> triggered specialist skill(s) -> affected regression -> independent fyp-quality-gate -> integration-safe-development -> phase-closeout-context-refresh`

Use `worktree-task` before that flow only when concurrent checkout isolation is needed.
Do not create generic implementation, quality-gate, or pre-PR skills that overlap the
three canonical workflows above.

Skill directories may contain `references/`, `scripts/`, `assets/`, or
`agents/openai.yaml`. Read supporting material only when the selected skill directs it.

Claude Code does not read `.agents/`. `.claude/skills/<name>/SKILL.md` exposes only the
four canonical workflows named in `AGENTS.md` as discovery pointers. Each pointer copies
its canonical `name` and `description`, reads the canonical skill from the current
checkout, and must add no instructions or authority. `tests/test_claude_skill_pointers.py`
checks the pointer set, exact frontmatter and canonical references; review of the pointer
body remains required. These pointers are not additional or overlapping workflows.
