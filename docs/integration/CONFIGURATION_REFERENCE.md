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
| `PHASE13_TEAM_A_ONBOARDER_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for the Team A Client Onboarder |
| `PHASE13_TEAM_A_RM_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for the Team A Relationship Manager |
| `PHASE13_TEAM_B_ONBOARDER_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for the Team B Client Onboarder |
| `PHASE13_TEAM_B_RM_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for the Team B Relationship Manager |
| `PHASE13_DIRECTOR_PASSWORD_HASH` | required secret | empty | Backend-only scrypt hash for the Director |
| `PHASE13_COOKIE_SECURE` | security | environment-derived | Defaults `true` in production and `false` in local development/test; explicit production `false` fails startup |
| `ACRA_CONNECTOR_MODE` | integration | `mock` | `mock` or sandbox-shaped `sandbox` |
| `ACRA_BASE_URL` | integration | empty | HTTPS subscriber base; required only for sandbox mode |
| `ACRA_COMPANY_PATH_TEMPLATE` | integration | empty | Authorized path with exactly one `{uen}` placeholder |
| `ACRA_TIMEOUT_SECONDS` | integration | `10` | Bounded sandbox HTTP timeout |
| `ACRA_AUTH_HEADER_NAME` | security | empty | Backend-only generic seam pending Q-012 |
| `ACRA_AUTH_HEADER_VALUE` | secret | empty | Local secret only; never commit/log |
| `GOLDTIER_CONNECTOR_MODE` | Mock | `mock` | Current schema accepts `mock` only |
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

For the scripted sponsor demo both demo flags are enabled in their respective launched
processes, while `IDP_CONNECTOR_MODE=local_pdf_text` remains the normal sponsor path.
Developer controls use their dedicated demo provider boundary and do not replace it.

## Script-only smoke settings

`ACRA_LIVE_SMOKE_ENABLED` and `ACRA_SMOKE_UEN` are read only by
`scripts/acra_sandbox_smoke.py`. The smoke is disabled by default and must not run until
Q-012 and authorized access are satisfied.

## MongoDB persistence and diagnostic

Memory mode is process-local and needs no Mongo service. Mongo mode validates
connectivity, stored schema, and bounded indexes during application composition and
stores authoritative structured case envelopes. Missing/unreachable Mongo or invalid
stored data fails closed and never falls back to memory. `scripts/check_mongodb.py`
remains a separate connectivity/read-only diagnostic.

The URI, credentials, database internals, and raw PyMongo error are never included in
health, execution-profile, case responses, or normal logs. No TTL/purge is configured.

## Future/unconsumed placeholders

`GOLDTIER_BASE_URL`, `PINGFED_TOKEN_URL`, `GOLDTIER_CLIENT_ID`,
`GOLDTIER_CLIENT_SECRET`, and `GOLDTIER_SCOPE` are present in `.env.example` only as
future inventory. Current `Settings` and composition do not read them and no real
GoldTier adapter exists. Populating them does nothing and must not be represented as
real readiness. D-018 still prohibits the quarantined authentication material.

## Fail-closed rules

- Unsupported connector modes fail settings validation.
- ACRA sandbox mode without valid HTTPS/path/auth configuration fails before use.
- Demo UI visibility does not bypass the backend demo gate.
- Mongo mode never degrades to memory when configuration, startup, read, or write fails.
- All five Phase 13 credential hashes must be present and valid or startup fails with
  only the missing/invalid setting name. Plaintext passwords are never accepted as
  settings.
- Use `python scripts/generate_phase13_demo_password_hashes.py` interactively and copy
  its five hash assignments only into the local untracked environment. The script never
  writes a credential file or prints plaintext.
- No TLS-disable, certificate-ignore, wildcard CORS, or secret-printing option exists.
