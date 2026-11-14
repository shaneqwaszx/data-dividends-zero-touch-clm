# Release pipeline documents

An Actions-independent release toolchain for the single-host AWS demo. **Implemented and
tested locally against mocks; never run against the host or the registry; changes no existing
owner gate. The one independent review returned FAIL; its findings were addressed but the fixes
are not independently re-reviewed, so this is not yet cleared for use.**

| Document | What it is for |
|---|---|
| [PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md) | Design, what is reused, the gate, manifest, approval, configuration check, sequence, limitations |
| [RELEASE_AUTOMATION_RUNBOOK.md](RELEASE_AUTOMATION_RUNBOOK.md) | The commands, in order, with rollback and stop conditions per service |
| [FIRST_AUTOMATED_RELEASE_CHECKLIST.md](FIRST_AUTOMATED_RELEASE_CHECKLIST.md) | The simplest first real use, through the existing host operator |
| [GHCR_CREDENTIAL_GUIDE.md](GHCR_CREDENTIAL_GUIDE.md) | Publish and pull identities, bootstrap, rotation, expiry, revocation; pull compared with archive transfer |
| [RISK_BASED_APPROVAL_PROPOSAL.md](RISK_BASED_APPROVAL_PROPOSAL.md) | Proposal only: LOW / MEDIUM / HIGH and the approvals each would need |
| [LOCAL_RELEASE_CONTROLLER.md](LOCAL_RELEASE_CONTROLLER.md) | The local controller and the evaluation of an always-on runner |
| [PIPELINE_HOW_TO_USE_AND_MAINTAIN.md](PIPELINE_HOW_TO_USE_AND_MAINTAIN.md) | Section to paste into an engineering handoff |
| [TEST_EVIDENCE_AND_LIMITATIONS.md](TEST_EVIDENCE_AND_LIMITATIONS.md) | What was run, the counts, the independent review, what is not proven |
| [INDEPENDENT_PIPELINE_REVIEW_20261114.md](INDEPENDENT_PIPELINE_REVIEW_20261114.md) | The independent review of the first candidate, unedited. Verdict: **FAIL**. The fixes made afterwards are not re-reviewed |

| Artefact | Path |
|---|---|
| Release manifest schema | `tools/release/schema/release-manifest.schema.json` |
| Approval record schema | `tools/release/schema/approval-record.schema.json` |
| Sample manifest for the three `d0142d8` candidates (registry digests unknown) | [samples/release-manifest.d0142d8.sample.json](samples/release-manifest.d0142d8.sample.json) |
| Sample approval record (already expired, so it is refused) | [samples/approval-record.sample.json](samples/approval-record.sample.json) |
| Sample release request (assistant-only) | [samples/release-request.assistant-only.sample.json](samples/release-request.assistant-only.sample.json) |
| Reviewed effective-configuration baseline | `tools/release/policy/effective-baseline.json` |
| Code and tests | `tools/release/`, `tools/release.ps1`, `tests/release/` |
