# Configuration Reference

Copy `.env.example` to a local untracked `.env` only when needed. Never place real
credentials in examples, tests, docs, frontend variables, or commits.

## Active backend settings

| Variable | Class | Default / safe example | Meaning |
|---|---|---|---|
| `APP_NAME` | optional | `Zero-Touch CLM API` | Non-secret application/health display name |
| `APP_ENV` | optional | `development` | Non-secret app label: development/test/production |
| `DEMO_CONTROLS_ENABLED` | Mock/demo | `false` | Backend gate for every demo/test route |
| `ZERO_TOUCH_MAX_TRANSITIONS_PER_RUN` | optional | `12` | Bounded local progress loop, 1–32 |
| `CLM_PERSISTENCE_MODE` | persistence | `memory` | Explicit `memory` or `mongo`; never inferred from URI presence |
| `MONGO_URI` | required secret in Mongo mode | empty | Backend-only Mongo connection string; never returned or logged |
| `MONGO_DATABASE` | persistence | `clm_poc` | Bounded database namespace |
| `MONGO_CASE_COLLECTION` | persistence | `clm_case_snapshots` | Bounded one-envelope-per-case collection |
| `MONGO_REGISTRY_CACHE_COLLECTION` | persistence | `clm_registry_snapshots` | Separate complete synthetic Mock registry-snapshot collection; must differ from every case/admin collection |
| `MONGO_ADMIN_TEAMS_COLLECTION` | persistence | `clm_admin_teams` | Canonical team and bounded audit records |
| `MONGO_ADMIN_PROFILES_COLLECTION` | persistence | `clm_admin_profiles` | Account authority, security version, and backend-only password hash records |
| `MONGO_ADMIN_POLICIES_COLLECTION` | persistence | `clm_admin_policies` | Singleton typed policy catalogue and bounded audit record |
| `PHASE13_MAYA_LIM_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for synthetic operator Maya Lim |
| `PHASE13_ETHAN_TAN_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for synthetic operator Ethan Tan |
| `PHASE13_SOPHIA_NG_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for synthetic operator Sophia Ng |
| `PHASE13_RYAN_LEE_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for synthetic operator Ryan Lee |
| `PHASE13_OLIVIA_KOH_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for synthetic Director Olivia Koh |
| `PHASE14_5_HR_ADMIN_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for synthetic HR administrator |
| `PHASE14_5_MAX_ACTIVE_SESSIONS` | security | `256` | Process-local global session capacity, 1–1000 |
| `PHASE13_COOKIE_SECURE` | security | environment-derived | Defaults `true` in production and `false` in local development/test; explicit production `false` fails startup |
| `PHASE13_BROWSER_ORIGIN` | security | `http://127.0.0.1:8000` locally | Canonical browser origin. Production requires an explicit exact HTTPS origin and fails before persistence initialization when absent or malformed. |
| `ACRA_CONNECTOR_MODE` | integration | `mock` | `mock`, canonical `api_marketplace_mock`, or generic `sandbox`; local Mock remains the default and there is no fallback |
| `GARDEN_SUPPLEMENT_ENABLED` | deprecated compatibility | `false` | Accepted legacy input; normal official Marketplace Mock automatically enables only the exact fresh successful Garden fixture with either value. True outside that lane retains its validation error; no runtime toggle is needed. |
| `REGISTRY_CACHE_MODE` | provisional Mock POC | `auto` | Ordinary non-production synthetic/official Mock lanes reuse exact-key normalized evidence; explicit `disabled` overrides; legacy `mock` remains supported |
| `REGISTRY_CACHE_FRESHNESS_SECONDS` | provisional Mock POC | unset (auto uses 7776000) | Legacy `mock` requires exactly `7776000`; auto accepts unset or that baseline; frozen approved case policy controls actual freshness |
| `ACRA_BASE_URL` | integration | empty | HTTPS subscriber base; required only for the generic sandbox mode |
| `ACRA_COMPANY_PATH_TEMPLATE` | integration | empty | Generic-sandbox authorized path with exactly one `{uen}` placeholder |
| `ACRA_TIMEOUT_SECONDS` | integration | `10` | Bounded ACRA HTTP timeout |
| `ACRA_AUTH_HEADER_NAME` | security | empty | Backend-only generic-sandbox seam pending Q-012; not authority for API Marketplace Mock authentication |
| `ACRA_AUTH_HEADER_VALUE` | secret | empty | Local generic-sandbox secret only; never commit/log; not an API Marketplace Mock auth decision |
| `ACRA_API_MARKETPLACE_MOCK_CLIENT_ID` | required backend secret in official Mock mode | empty | Official Mock OAuth2 client identifier; `SecretStr`, never commit/log; presence alone does not select the provider |
| `ACRA_API_MARKETPLACE_MOCK_SECRET_KEY` | required backend secret in official Mock mode | empty | Official Mock OAuth2 secret key; `SecretStr`, never commit/log; presence alone does not select the provider |
| `GOLDTIER_CONNECTOR_MODE` | integration | `mock` | Explicit `mock` or sponsor XPI `sandbox`; there is no automatic fallback |
| `GOLDTIER_SANDBOX_BASE_URL` | integration | empty | HTTPS origin only; required in sandbox mode and never a production/Live claim |
| `GOLDTIER_SANDBOX_ENVIRONMENT` | integration | empty | Bounded path segment used by the supplied XPI routes |
| `GOLDTIER_SANDBOX_USER_ID` | backend-only secret | empty | Supplied `user_id` header value; never returned, logged, or exposed to the browser |
| `GOLDTIER_SANDBOX_TIMEOUT_SECONDS` | security | `10` | Per-request timeout, bounded to 30 seconds |
| `GOLDTIER_SANDBOX_MAX_RESPONSE_BYTES` | security | `131072` | Maximum retained response body, bounded to 1 MiB |
| `GOLDTIER_SANDBOX_ALLOW_WRITES` | safety | `false` | Separate opt-in for customer mutations; false still permits bounded search diagnostics |
| `IDP_CONNECTOR_MODE` | local POC | `local_pdf_text` | `local_pdf_text` for the normal sponsor PDF path; `mock` only for developer/test fault injection |
| `OWNERSHIP_CONNECTOR_MODE` | Mock | `mock` | Current schema accepts `mock` only |
| `IDP_MAX_UPLOAD_BYTES` | security | `5242880` | POC upload bound, max configurable 20 MiB |
| `IDP_MAX_FILES_PER_CASE` | security | `20` | POC current-document count bound, capped at the supported maximum of 20 |
| `IDP_MAX_TOTAL_INTAKE_BYTES` | security | `26214400` | POC total current-intake bound, max configurable 100 MiB and never below the per-file bound |
| `IDP_REVIEW_CONFIDENCE_THRESHOLD` | provisional | `0.85` | Project default, not sponsor-approved |
| `UBO_OWNERSHIP_THRESHOLD_PERCENT` | provisional | `25` | Inclusive project default pending Q-004 |
| `OWNERSHIP_MAX_PARTIES` | security | `100` | Graph bound |
| `OWNERSHIP_MAX_RELATIONSHIPS` | security | `200` | Graph bound |
| `OWNERSHIP_MAX_DEPTH` | security | `8` | Traversal bound |
| `OWNERSHIP_MAX_PATHS_PER_CANDIDATE` | security | `64` | Candidate path bound |
| `OWNERSHIP_MAX_TOTAL_PATHS` | security | `256` | Total traversal/emission bound |

## Active frontend settings

| Variable | Default | Meaning |
|---|---|---|
| `VITE_DEMO_CONTROLS_ENABLED` | `false` | Shows synthetic selectors; backend gate remains authoritative |
| `VITE_API_BASE_URL` | empty | Optional build-time base URL; local Vite proxy is supported. Cross-origin hosting requires a separately approved CORS design. |

Phase 14 adds exact-pinned `@tanstack/react-query` as a browser runtime dependency and
`jsdom` as a test-only dependency. The query cache is process memory with fixed code
defaults (`staleTime` 45 seconds, `gcTime` 15 minutes); it has no environment toggle or
persistent-storage configuration.

For the scripted sponsor demo both demo flags are enabled in their respective launched
processes, while `IDP_CONNECTOR_MODE=local_pdf_text` remains the normal sponsor path.
Developer controls use their dedicated demo provider boundary and do not replace it.

`api_marketplace_mock` is the sole canonical name for the official ACRA API Marketplace
Mock lane. In that explicit mode the two dedicated credentials are required for the
fixed HTTP Basic token request. The observed strict response is cached in process memory
with pre-expiry renewal, and downstream requests use the raw header named `token`.
Bearer is not used. Fixed entity-basic and shareholder operations have bounded observed
Mock interoperability; Garden shareholder evidence is empty and no percentage is
derived. The generic `ACRA_*` sandbox URL/path/header fields are not consulted or used as
fallbacks. Q-012 remains open, and the lane is never labelled Sandbox or Live.

## Script-only smoke settings

`ACRA_LIVE_SMOKE_ENABLED` and `ACRA_SMOKE_UEN` are read only by the legacy generic
`scripts/acra_sandbox_smoke.py`. They remain disabled/empty and are not repurposed for
the official Mock lane. The dedicated `scripts/acra_marketplace_mock_smoke.py` uses only
fixed official Mock operations, dedicated credentials, bounded safe output, and no Live
toggle.

## MongoDB persistence and diagnostic

Memory mode is process-local and needs no Mongo service. Mongo mode validates
connectivity, stored schema, and bounded indexes during application composition and
stores authoritative structured case envelopes. Missing/unreachable Mongo or invalid
stored data fails closed and never falls back to memory. `scripts/check_mongodb.py`
remains a separate connectivity/read-only diagnostic.

The ordinary `auto` default enables the existing registry snapshot repository in
non-production synthetic/official Mock lanes. Production auto and generic Sandbox
perform no registry-cache use. `disabled` explicitly opts out. Complete exact-UEN
`LOCAL_SYNTHETIC_UAT_V1` seed evidence precedes the configured Mock provider namespace;
seed misses, expiry and incomplete bundles never mix into external acquisition. The
configured provider's own complete cache hit also avoids all ACRA operations. Strict
malformed-storage errors remain fail-closed. See D-069 / ADR-010 and the
[database UAT guide](../demo/ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT.md).
No source validity, production sharing or retention policy is implied.

The URI, credentials, database internals, and raw PyMongo error are never included in
health, execution-profile, case responses, or normal logs. No TTL/purge is configured.

Run the sanitized preflight before starting a teammate profile:

```powershell
.\.venv\Scripts\python.exe scripts\dev_preflight.py
.\.venv\Scripts\python.exe scripts\dev_preflight.py --persistence-mode memory
.\.venv\Scripts\python.exe scripts\dev_preflight.py --persistence-mode mongo
```

The command loads normal settings validation but prints no setting values for secrets,
URIs, authorization headers, or provider payloads. It reports the selected persistence
mode, whether Mongo is required/reachable, the configured ACRA mode, dedicated official
Mock credential presence, composed connector class, bounded timeout, and GoldTier mode.
Memory mode never pings Mongo. Mongo failure output is deliberately reduced to a safe
unreachable/missing-configuration statement.

## Future/unconsumed placeholders

`GOLDTIER_BASE_URL`, `PINGFED_TOKEN_URL`, `GOLDTIER_CLIENT_ID`,
`GOLDTIER_CLIENT_SECRET`, and `GOLDTIER_SCOPE` are present in `.env.example` only as
future PingFed/production inventory. Current `Settings` and composition do not read
them. The separately named `GOLDTIER_SANDBOX_*` settings compose only the sponsor XPI
sandbox adapter, classified `SANDBOX_PARTIAL`. Populating either family is not evidence
of Live readiness. The provider registry records `GOLDTIER_XPI` as explicit
`PARTIAL / SANDBOX_PARTIAL` while keeping `GOLDTIER_REAL` and `PINGFED_AUTH` blocked.
D-018 still prohibits the quarantined authentication material.

## Fail-closed rules

- Unsupported connector modes fail settings validation.
- API Marketplace Mock credentials alone never activate its blocked runtime lane and
  are never substituted for generic-sandbox authorization.
- ACRA sandbox mode without valid HTTPS/path/auth configuration fails before use.
- GoldTier sandbox mode without a safe HTTPS origin, bounded environment, or backend-
  only `user_id` fails before use; mutation dispatch also requires the separate write
  opt-in and a complete authority-labelled case policy snapshot.
- Registry caching outside Mock ACRA, without the exact freshness value, or with a
  colliding Mongo collection name fails settings validation.
- Demo UI visibility does not bypass the backend demo gate.
- Mongo mode never degrades to memory when configuration, startup, read, or write fails.
- All six bootstrap credential hashes must be present and valid or startup fails with
  only the missing/invalid setting name. Plaintext passwords are never accepted as
  settings.
- Use `python scripts/generate_admin_bootstrap_password_hashes.py` interactively and copy
  its six hash assignments only into the local untracked environment. The script never
  writes a credential file or prints plaintext.
- Existing local Phase 13 hashes use retired setting names and are not migrated. After
  this remediation, regenerate all five hashes so the new synthetic-profile setting
  names above are populated.
- Browser Origin/Referer validation uses configured origins only; request `Host` and
  forwarding headers never add trust. At most one physical field of each name is
  accepted, and duplicate fields fail closed even when identical. Origin is an exact
  origin; Referer may include path/query but not a fragment. Development/test has exact
  loopback origins for the backend and documented Vite proxy. Production requires one
  explicit exact HTTPS `PHASE13_BROWSER_ORIGIN` and inherits no development origin.
- No TLS-disable, certificate-ignore, wildcard CORS, or secret-printing option exists.
