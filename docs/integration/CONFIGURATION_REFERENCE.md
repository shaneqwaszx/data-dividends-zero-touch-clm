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
| `MONGO_URI` | optional secret | empty | Used only by the manual MongoDB connectivity diagnostic; not used for onboarding persistence |
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

## Optional MongoDB diagnostic

`MONGO_URI` is consumed only by `app.mongo` and `scripts/check_mongodb.py`. The script
performs a connection ping and a read-only count of the diagnostic `FYP.users`
collection. It is not imported by application composition and does not persist cases,
documents, ownership, workflow checkpoints, or target outcomes. Normal onboarding
therefore runs without `MONGO_URI` and all application repositories remain in memory.

When configuration is absent or the server is unavailable, the script exits nonzero
and reports only a safe exception class; it does not print the URI or server error.

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
- No TLS-disable, certificate-ignore, wildcard CORS, or secret-printing option exists.
