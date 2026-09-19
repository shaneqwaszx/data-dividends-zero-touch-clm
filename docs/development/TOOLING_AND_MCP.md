# Tooling, MCP and External-Service Guidance

## Definitions

| Kind | Meaning | Repository treatment |
|---|---|---|
| REPO TOOL | Tracked script/test/build command | May run within its documented safe boundary |
| SKILL | Repository procedure under `.agents/skills/` | Guides work; grants no external authority |
| MCP / CONNECTOR | Agent/app bridge to another system | Requires installation, permissions and scoped use |
| EXTERNAL ACCOUNT / SERVICE | GitHub, Drive, SharePoint, Mongo, ACRA, GoldTier, etc. | Owner controls access and acceptable environment |
| SECRET | Credential, token, URI with credentials, key or certificate | Never stored in Git/docs/tests/output; provision manually |

A connector's availability does not establish source authority, contract correctness,
Live status, permission to mutate external state, or permission to expose retrieved data.

## Current posture

### GitHub

GitHub is useful for source, PRs, CI evidence and review. Use repository tools and the
integration workflow. `scripts/github_pr_ci.py` may observe `gh pr view` and
`gh pr checks` only; its SHA-bound result is evidence, not merge approval. It has no
push, create/edit, review, rerun/cancel, settings, approval, or merge path. Do not embed
tokens or credentials. This task does not change repository settings, branch
protection, accounts, secrets, checks or merge policy.

### Sponsor document connector

A Drive/SharePoint/document connector can help when authoritative sponsor documents live
there. Installation and OAuth/account authorization are owner actions. Retrieve only the
documents required by scope, preserve confidentiality, and apply the `AGENTS.md` source-
authority order. A retrieved file never overrides current source/contracts solely because
a connector returned it.

### MongoDB

Agents do not receive unrestricted production-style database access. Application mode is
explicit and URIs remain runtime secrets. Physical tests use only fresh generated
allowlisted disposable database names through the project safety harness. Never test,
drop, clean or mutate `clm_poc`; never store or print a Mongo URI. Owner setup of a local
or CI Mongo service and secret is manual. `scripts/run_physical_mongo_tests.py` reads
only `PHASE12_MONGO_URI`, contains pytest output, and treats all-skipped execution as
blocked. `scripts/check_mongodb.py` is a connectivity-only ping.

### ACRA and GoldTier/PingFed

Documentation/browser/API tooling may support contract verification. Credentials,
client certificates, tokens and external accounts require explicit authorized owner
setup. Tool access or successful authentication is not contract authority, sponsor
approval or Live interoperability proof. Use `external-provider-integration`, contract
reconciliation and integration-security review; retain only sanitized evidence.

### Camunda

The current runtime has no Camunda adapter/composition. The project-scoped Codex config
contains two developer-tool entries only:

- `camunda_docs` is optional, prompt-approved, and restricted in this client to the
  Kapa-powered `search_camunda_knowledge_sources` documentation search tool. Queries
  leave the machine; never send sponsor-confidential material, source payloads, PII,
  secrets, or private code, and verify consequential answers against official Camunda
  documentation.
- `camunda_cluster` is disabled and restricted to `getClusterStatus` and `getTopology`.
  Enabling it requires a separate authorized architecture/security change and owner
  provisioning. It does not make Camunda part of product runtime.

`enabled_tools` is a Codex client exposure restriction. It is not server-side
authorization and does not constrain other clients.

## Repository configuration boundary

Official Codex documentation supports project-local `.codex/config.toml` for trusted
repositories. The tracked file contains only public endpoint/command metadata, exact
tool allowlists, prompt approvals, optional startup, and bounded timeouts. It contains
no credential, token, header, client/cluster identifier, environment-forwarding map, or
machine-global preference. `scripts/check_tooling_config.py` validates that exact shape
offline and is wired into CI and the pre-PR checker.

See [Development Tooling Runbook](DEVELOPMENT_TOOLING_RUNBOOK.md) for manual sign-in,
privacy/rate-limit boundaries, safe commands, and the future disabled cluster gate.

## Manual-only setup

The repository cannot automate:

1. MCP/plugin/connector installation that needs owner approval;
2. OAuth or external-account authentication;
3. secret, token, certificate, URI or credential provisioning/rotation;
4. GitHub repository/account/branch-protection/CI-secret settings;
5. external sponsor access or final human PR merge;
6. machine-global dependency/service installation.

Record only presence/status and sanitized evidence. Never copy a secret value into a
ticket, prompt, report, screenshot, fixture or terminal transcript.
