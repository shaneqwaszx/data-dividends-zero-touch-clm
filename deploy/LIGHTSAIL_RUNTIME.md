# Single-host Lightsail demo runtime

Use the base Compose file and the same-host Mongo overlay together. The overlay adds a TLS-only MongoDB service on an internal Docker network with no published ports. Only Caddy publishes ports. Mongo uses a pre-created external named volume, so Compose fails if that volume is absent and does not remove it on teardown. The app still runs as one staging writer with Mock ACRA and GoldTier, Sandbox writes disabled, and local OCR. Use synthetic data only.

## Host and files

After owner authorization, use one Sydney Ubuntu 24.04 AMD64 Lightsail host. Install Docker Engine and the Compose plugin from Docker's signed Ubuntu APT repository. Confirm `dpkg --print-architecture` reports `amd64`, Docker is enabled on boot, and Compose is at least v2.30. Limit Docker and sudo access to the designated operator. [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/)

Attach the approved static IPv4. Point the approved hostname's A record at it. Permit TCP 80 and 443 for Caddy and TCP 22 only from the approved operator CIDR and public key. Check the IPv6 firewall separately if enabled. Leave ports 8000 and 27017 unpublished. Verify DNS and public HTTPS before the demo. [Lightsail firewall guidance](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html)

Keep the reviewed Compose files under `/opt/clm`. Put the non-secret interpolation file at `/etc/clm/compose.env`. Set `BACKEND_IMAGE` and `FRONTEND_IMAGE` to the approved AMD64 registry digests, `CLM_SITE` to the approved hostname, `BACKEND_ENV_FILE` to the protected external runtime file, and `MONGO_CA_FILE`, `MONGO_SERVER_PEM`, and `MONGO_DATA_VOLUME` to the designated host paths and volume name. Authenticate to the approved registry with least-privilege pull access. Keep the exact HTTPS origin and temporary synthetic scrypt hashes in the protected backend file. Inject `MONGO_URI` into the operator process from the approved secret source. Use the restricted app user, host `mongo`, database and authentication source `clm_staging`, TLS enabled, and CA path `/run/clm/mongo-ca.pem`. Percent-encode credentials and keep the connection setting out of command arguments and logs. Use `config --quiet` for validation.

Provision a CA-signed Mongo server certificate with DNS SANs `mongo` and `localhost` for app and operator connections. Keep the CA signing key offline. Mount the public CA and the server certificate/key bundle from outside the checkout. Restrict the server bundle to the Mongo process (UID 999 for the pinned image, mode 0600). Make only the public CA readable by the backend. The server requires TLS and uses SCRAM password authentication over it. Client certificates are optional, and server certificate and hostname validation remain required. [MongoDB TLS configuration](https://www.mongodb.com/docs/manual/core/tls/configure-server-tls-tutorial/)

## Initial provisioning and startup

Create the designated external volume once for a new installation with `docker volume create` and the approved name, and record its name and inspect its identity before each startup. If an expected volume is absent, stop and recover it. Preserve the external volume and Caddy volumes on app replacement. Use the same Compose project on the single designated host.

```sh
cd /opt/clm
dc() {
  docker compose --env-file /etc/clm/compose.env -f deploy/compose.yml -f deploy/compose.mongo.yml "$@"
}
dc config --quiet
dc pull
dc up -d --no-build --wait mongo
dc exec mongo mongosh --quiet --host localhost --tls --tlsCAFile /run/clm/mongo-ca.pem
```

On a confirmed fresh volume, use the localhost exception once in that shell to create a credential-management user in `admin` with `userAdminAnyDatabase` on `admin` for credential provisioning only. Use `passwordPrompt()` and approved secret handling. Authenticate as that user and create the separate `clm_app` identity in `clm_staging` with only `readWrite` on that database. The backend uses the app identity. Existing volumes retain users and data across restart. A failed login on an existing volume calls for checking the selected volume and credentials before any bootstrap step. The localhost exception closes when the first user is created. [MongoDB localhost exception](https://www.mongodb.com/docs/manual/core/localhost-exception/)

Run `dc up -d --no-build --wait` after user provisioning. Verify only the approved Caddy ports are bound, one backend is running, the staging profile and HTTPS login work, and a synthetic case reaches its expected status. For a controlled shutdown run `dc stop frontend`, then `dc stop backend`, then `dc stop mongo`, keeping the volumes. For app replacement stop ingress and the old backend before starting the new one. On the authorized host, rehearse a VM restart and confirm Mongo retains the case and target ledger, exactly one backend resumes, and RM login works again. Use the accepted digest pair and compatible config for rollback.

## Quiesced export and recovery

For a bounded synthetic-demo backup, stop ingress and the backend before exporting so the database and target ledger are at one point in time. Use a protected host backup directory and a timestamped archive. With the scoped database account and password prompt, run:

```sh
dc stop frontend backend
dc exec mongo mongodump --host localhost --ssl --sslCAFile /run/clm/mongo-ca.pem \
  --username clm_app --authenticationDatabase clm_staging --db clm_staging \
  --gzip --archive=/tmp/clm-demo.archive.gz
```

Copy the archive out with `dc cp` to the protected directory, restrict its permissions, record a SHA-256, and remove the temporary container copy. Keep the latest verified archive and the previous known-good one. Start the app only after the export and its verification are complete.

For recovery, keep ingress and the backend stopped and run `dc stop mongo`. Preserve the original volume. Set `MONGO_DATA_VOLUME` to a newly created external recovery volume and run `dc up -d --no-build --wait mongo`. Confirm the mounted volume, bootstrap its users, and verify that it has no case or ledger data before import. Verify the archive checksum and that no target operations occurred after its backup boundary. If that boundary cannot be proved, keep the app stopped pending ledger reconciliation. Using the credential-management account on the recovery volume, create a temporary operator in `admin` with the built-in `restore` role. Copy the archive to the Mongo container and run the restore against the recovery volume.

```sh
dc exec mongo mongorestore --host localhost --ssl --sslCAFile /run/clm/mongo-ca.pem \
  --username clm_restore --authenticationDatabase admin --nsInclude 'clm_staging.*' \
  --gzip --archive=/tmp/clm-demo.archive.gz --stopOnError
```

Remove the container copy and drop the temporary restore user after import. Check the recovered case status and ledger before resuming the demo. Retain the original volume until the recovery is accepted. The export contains synthetic case data and excludes users. Keep the identity provisioning material separate. [MongoDB Database Tools](https://www.mongodb.com/docs/database-tools/mongodump/)

## Cost and release gate

Confirm the exact bundle and credit eligibility immediately before launch, set an approved cost alert, and check available credit and usage during the demo. Record a teardown date and confirm that the instance and any detached static IP are accounted for. This overlay requires applicable acceptance and independent review. Follow the separate source and image publication approvals before transferring digest-pinned images or launching the host.
