# AWS demo deployment candidate

The Compose stack runs the production React build in Caddy and one FastAPI worker. Caddy serves the frontend and proxies the same-origin API. Only Caddy publishes ports. The backend uses the existing Mongo repositories. ACRA and GoldTier are Mock, and document extraction and Tesseract OCR run locally. The AI Assistant is excluded. Its separate HTTP service needs Chroma and writable model and spending stores, and the core onboarding demo needs no model.

## Reproduce the local demo

From the repository root with Python 3.12, a Linux AMD64 Docker engine, and Compose v2.30 or later:

```powershell
docker build --platform linux/amd64 -f deploy/backend.Dockerfile -t clm-aws-demo-backend:local .
docker build --platform linux/amd64 -f deploy/frontend.Dockerfile -t clm-aws-demo-frontend:local .
python -B deploy/smoke.py clm-aws-demo-backend:local clm-aws-demo-frontend:local
```

The smoke uses a unique Compose project, a generated disposable Mongo database, a temporary Mongo certificate, and a locally trusted Caddy CA. It verifies both TLS connections and binds ingress to loopback. It runs the application in the test profile for the disposable database. It authenticates normally with an ephemeral synthetic RM credential, verifies CSRF enforcement, uploads tracked synthetic PDFs, resolves a registry conflict, checks ownership and UBO candidates, and explicitly confirms the Mock GoldTier dispatch. It replaces the only backend writer and checks the retained case and ledger. The disposable project, Mongo data, and certificates are removed on exit.

## Hosted staging prerequisites

The local smoke is implementation evidence. Promotion requires the repository's integrated acceptance, exact independent Quality Gate PASS, and owner publication and promotion authorization. Select the exact reviewed source and record the verified image digests before transferring images to the host.

For `DC - ONBOARDING`, target Sydney (`ap-southeast-2`). The proposed host is one Lightsail `medium_3_2` Linux instance with Ubuntu 24.04 (`ubuntu_24_04`), 4 GB RAM, and public IPv4. Use the authenticated `Shane` profile and pass `--region ap-southeast-2` on regional calls. Before provisioning, confirm the project context, account-level launch eligibility, applicable credits, and spending approval. Confirm the demo DNS name and dedicated Sydney Mongo service. Use only a database user scoped to the isolated `clm_staging` database, with access limited to the host and a verified Mongo TLS connection. The staging profile rejects other database names, disabled TLS verification, insecure cookies and missing browser origin evidence on protected mutations.

After release and infrastructure approval, install Docker and Compose on the designated host. Configure the approved DNS record and allow the Caddy HTTP and HTTPS ports for certificate issuance and demo access. Restrict administrative access to the approved operator path. Use a protected runtime configuration file outside the checkout based on `backend.env.example`, and a separate interpolation file for non-secret settings. Set `BACKEND_IMAGE` and `FRONTEND_IMAGE` to the reviewed digests, `CLM_SITE` to the approved DNS hostname, and `BACKEND_ENV_FILE` to the protected file's absolute path. Set the exact HTTPS browser origin and populate the required scrypt hashes through the operator's secret handling process.

```sh
docker compose --env-file /etc/clm/compose.env -f deploy/compose.yml config --quiet
docker compose --env-file /etc/clm/compose.env -f deploy/compose.yml up -d --no-build --wait
```

Use a single designated host and never overlap backend writers against the database. For replacement, stop ingress, drain and stop the old backend, then start the approved pair. Retain the previous pair and review compatibility against the current data before rollback. Check external HTTPS, ingress exposure, authenticated synthetic onboarding, Mock dispatch and persistence after replacement. Preserve the existing target ledger recovery process for interrupted writes.


### Login admission and proxy trust

The staging worker limits login attempts per source and across all sources, with
at most two password verifications in flight. The limiter resets when the
backend restarts. Login bursts can return HTTP 429 with a Retry-After value.

Caddy and the backend share an internal proxy network. Uvicorn trusts forwarded
headers only from the reserved Caddy address on that network. The same-host
Mongo overlay attaches only the backend and Mongo to the separate database
network. Leave backend and database ports unpublished.

Before deployment, check that the proxy subnet does not overlap any host or
Docker route. The defaults are `172.30.240.0/29`, Caddy `172.30.240.2`, and
backend `172.30.240.3`. If needed, set `CLM_PROXY_SUBNET`, `CLM_PROXY_IPV4`,
and `CLM_BACKEND_PROXY_IPV4` together in the Compose interpolation file.
Reserve distinct IPv4 addresses within that subnet, keep the proxy network
exclusive to Caddy and the backend, and verify health after either service is
recreated. The address supplied to Uvicorn and the Caddy network assignment
come from the same Compose value.

The aggregate budget is shared by all unauthenticated callers. Six sources can
rotate attempts and consume every replenished slot, delaying login for a shared
office network for the duration of that traffic. The deterministic test covers
120 seconds of contention and recovery after traffic stops. Retry-After reports
when a slot may become available. It does not reserve one. A queue or a pool
reserved for new sources would still accept unauthenticated attack traffic.
Keep the aggregate and concurrency limits as the backend safety boundary.
If sustained contention affects the demo, evaluate an upstream access policy
or a bot challenge before increasing the backend budget.
