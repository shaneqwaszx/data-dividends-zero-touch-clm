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
integration workflow. Do not embed tokens or credentials. This task does not change
repository settings, branch protection, accounts, secrets, checks or merge policy.

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
or CI Mongo service and secret is manual.

### ACRA and GoldTier/PingFed

Documentation/browser/API tooling may support contract verification. Credentials,
client certificates, tokens and external accounts require explicit authorized owner
setup. Tool access or successful authentication is not contract authority, sponsor
approval or Live interoperability proof. Use `external-provider-integration`, contract
reconciliation and integration-security review; retain only sanitized evidence.

### Camunda

The current runtime has no Camunda adapter/composition. Do not recommend or install a
Camunda MCP/integration until an explicit phase and architecture decision require it.

## Repository configuration boundary

No official tracked repo-local MCP configuration schema was found at the verified
baseline. Therefore this task creates no `.mcp.json` or guessed equivalent. Follow the
Codex/connector owner's official installation flow outside the repository, authorize the
minimum account/scope, and keep machine-global configuration/secrets out of Git.

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
