# MongoDB recovery phase 1

## Offline execution

Run from the isolated worktree at source baseline
`671882a9ef2f60c1da5a79139eacb572c87cc2f4`. Use Python 3.12,
OpenSSL 3, a local Linux Docker engine, the cached Mongo image pinned in the
drill, and a cached backend runtime with the baseline Python dependencies.
The fixture mounts the baseline backend source read-only. Select only a trusted
local fixture image. A tag used for dependencies does not attest image provenance.

```powershell
python deploy/recovery/offline_drill.py --openssl 'C:/Program Files/Git/usr/bin/openssl.exe' --fixture-image clm-hosted-smoke-backend:671882a
python deploy/recovery/offline_drill.py --openssl 'C:/Program Files/Git/usr/bin/openssl.exe' --fixture-image clm-hosted-smoke-backend:671882a --qualify-cached-backend
```

The first command also runs the CAS regression against the restored volume with
approved baseline source. It demonstrates the old pre-write comparison would
reject the write, then checks revision 2 against the returned persisted snapshot
at BSON millisecond precision for the managed timestamp. The raw BSON record
must retain every field except the intended revision and managed timestamp.

The optional flag substitutes a probe of the cached registry digest with its
own code through schema-20 reads, repository initialization and revision CAS.
A failure exits nonzero. This is a repository compatibility probe. Full
application startup, HTTPS, frontend pairing and completed-ledger no-replay
need separate qualification of an owner-confirmed pair and configuration.

Before Docker use, the drill checks the actual Git HEAD against the approved
SHA, rejects unexpected worktree changes, and rejects ignored files and hidden
index entries under the mounted application source. The manifest records the
actual source commit, app-tree and whole-worktree status separately, and the
Git status and SHA-256 of each recovery candidate file. Provenance is checked
again before accepting the rehearsal evidence.

Each run creates a random allowlisted database, two new Docker volumes and an
internal-only network. No ports are published, no host credentials are mounted,
and image pulls are disabled. The database fixture uses the canonical
persistence model and makes a mock ledger entry without dispatching it.
The fixtures cover one collection and one ledger state. The drill compares the
full BSON values and index specs and independently checks revision, audit and
ledger evidence. It uses ephemeral unauthenticated Mongo inside the internal
network. Production Mongo authentication and TLS remain a separate preflight.

The exporter pipes the compressed archive into OpenSSL CMS AES-256-GCM
recipient encryption. The checksum and length refer to ciphertext. A local
copy models download. A changed byte is rejected by both the manifest check
and CMS decryption. Successful decryption finishes before restore starts.
The restore workstation needs a private encrypted scratch filesystem in
production. A failed decrypt may write unauthenticated plaintext to scratch,
which must be removed without use. The ephemeral test key is for this drill.
A production private key must stay off Lightsail and off the uploader.

## Recorded rehearsal

On 2026-11-07 at 16:55 SGT the second command above used Docker 29.9.2,
OpenSSL 3.5.8 and MongoDB 7.0.40 with FCV 7.0. The fixture runtime image ID
was `sha256:da2252c31b072d909ab7cdc3e48b9965adbcff5322764a8edb67ea163384f3ed`.

- Streaming backup and manifest took 0.28 seconds. The 5,109-byte ciphertext
  SHA-256 was `16e7f65720a22cc9c3dcb02de17eec8f174f96a28ce86852adaa13567f344062`.
- Both SHA-256 and CMS authentication rejected the corrupted copy.
- Download verification, authenticated decryption, restore and comparison
  took 3.94 seconds. The separate volume contained one schema-20 case at
  revision 1, four audit events, one NOT_STARTED target-ledger entry and six
  matching indexes. Mongorestore reported one document and zero failures.
- The cached GHCR backend rejected the restored record with
  `PersistenceSchemaUnsupportedError`. The combined invocation exited 1.
  That digest is ineligible for schema-20 rollback. Repository initialization
  and CAS on that digest, full startup and a positive rollback image test
  remain unverified. Do not approve the image pair for rollback on this evidence.

## Recovery inventory

| Component | Evidence and follow-up |
| --- | --- |
| Source | Approved main SHA above. Obtain the deployed and prospective rollback build attestations from the release owner. |
| Backend | Cached GHCR digest `sha256:313e882248e3b72e9237bf4419a497a02ad32251ff9d597226c47d9732d40733`, cached release tag `4c1db4925865ebf7f50a8f73d96c113c26304503`. Owner must confirm the tag-to-source mapping, approval and deployment. |
| Frontend | Cached GHCR digest `sha256:cdbfca7163e19d139a1115e26f499153ef2d00c13c95faf5f4ecf9a3812688b7` under the same release tag. Owner must confirm deployment and compatible pairing. |
| Mongo | Approved overlay pins `sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b`. Compare measured rehearsal server version/FCV to the release owner's live inventory before selecting restore tools. |
| Configuration | `deploy/compose.yml`, `deploy/compose.mongo.yml`, `deploy/Caddyfile` at the approved SHA. Host copies expected under `/opt/clm` and `/etc/clm/compose.env`. Release owner supplies deployed checksums and Caddy image provenance. |
| Volumes | Production Mongo name supplied as `clm-fyp-mongo-data`. Compose defines Caddy TLS data and config volumes. Record their live identities and custody from the operator's inventory. |
| Secret references | Runtime backend env file, Mongo app and backup identities, Mongo CA/server certificate and key, registry pull identity, operator SSH and recovery key escrow. Record owner, vault reference and recovery procedure separately from values. Mongo application database export excludes credentials and server configuration. |
| Dependencies | DNS and ACME, GHCR pull access, correct Mongo TLS identity, and the owner-approved provider modes. Check that any separate assistant store or other writer is inventoried independently before certifying whole-environment recovery. |

Phase 1.1 read-only inventory checked local registry digests, the deployment
contract and merged PRs [#166](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/166)
and [#168](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/168).
The locally cached baseline-tagged fixture runtime has a local image ID with
no registry RepoDigest. The merged PRs establish source history but supply
no owner-approved schema-20 image digest or live digest attestation. Application
qualification is blocked pending an owner-confirmed digest and release evidence.

## Production proposals and approvals

The following are proposals for `ap-southeast-2`. Resolve the account ID,
instance ARN, bucket name availability, operator principals, and DNS name
before submitting any change. Require separate approvals for each row.

| Approval | Exact intended change | Availability, cost and rollback |
| --- | --- | --- |
| Bucket and retention | `clm-fyp-mongo-backups-<account-id>-ap-southeast-2`, S3 Standard, all four public-access blocks, bucket-owner-enforced, versioning, SSE-S3, deny non-TLS. Use `mongo/v1/daily/<run-id>/` and `mongo/v1/pre-release/<run-id>/`, expiring at 14 and 30 days. Expire noncurrent versions after seven additional days, clean expired delete markers, abort incomplete multipart after one day. Enforce create-only conditional writes. Consider governance Object Lock under separate retention approval if admin deletion protection is required. | No planned downtime. Retained archive size drives cost. Revoke access and preserve verified versions for approved retention if pilot is rolled back. |
| IAM and escrow | Operator uses an MFA-backed temporary session off-host to assume proposed `ClmFypBackupSigner`. Trust only the approved workforce role. Allow `s3:PutObject` only on the two backup prefixes. Restrict each session further to the exact two object keys. Issue SigV4 PUT URLs for 10 minutes with signed `If-None-Match: *` and signed SHA-256 checksum. Deny query-signed writes older than 600000 ms. `ClmFypBackupVerifier` gets prefix-scoped `s3:ListBucket` and `s3:GetObject`/`s3:GetObjectVersion`; restore access is independently approved and time-limited. The bucket administrator owns lifecycle and deletion. | No AWS credentials on Lightsail and no IAM instance profile assumption. Keep URLs out of arguments visible to other users, history and logs. Revoke signer sessions or deny signer in bucket policy to cut off live URLs. No customer-managed KMS fee. Escrow the CMS private key with two authorized recovery operators and retain old keys through archive expiry. |
| First backup | Approve one write-quiescence window and a dedicated database-scoped export identity. Stream encryption on the host. Use the two short-lived URLs for archive and manifest, with manifest uploaded last. Independently download the exact versions, recompute digest and record bucket/key/version, bytes, verified-at and boundary in the operator record. A valid manifest must be linked to that independently verified record. Single PUT only within S3 size limits. Larger archives need a separately approved multipart design. | Demo writes paused. If any step fails, discard incomplete evidence, preserve prior verified backup and resume the same stack after owner sign-off. Verify when it is safe to resume under the approved window. No host AWS key rotation needed. |
| Monitoring | Lightsail `clm-fyp-status-failed` for `StatusCheckFailed` and `clm-fyp-burst-low` for `BurstCapacityPercentage` on the exact approved instance. Proposed thresholds are two consecutive failing samples and below 20% for 15 minutes, mapped to supported periods. Confirm Sydney email contact. Use an independent approved runner for HTTPS and expected `/health` every five minutes, TLS below 21 days, disk and inode usage at 80%/90%, verified backup age beyond the 24-hour RPO, and missing signal alarms. Publish only sanitized timestamp/status from host disk checks. | No planned interruption. Confirm runner and notification costs. Scope any separately approved CloudTrail data events, S3 access logging and CloudWatch metrics to this bucket and budget them independently. Revert by disabling the probes and removing the named alarms. |
| Isolated recovery exercise | Approve decryption of an authorized backup on an encrypted isolated host, a new volume, and an exact backend/frontend pair. Block provider egress and obtain a two-person key recovery check. | No demo downtime. Temporary isolated compute and possible data transfer. Stop the isolated exercise and dispose of its scratch/volume under the data handling policy. |
| Live recovery or rollback | Separate incident approval for ingress suspension, deployment or volume cutover and any later provider re-enable. | Planned interruption. Preserve original volume, configuration, images, and ledger evidence. Only reverse to an owner-approved state with one writer. |

For cost planning, one 1-GiB daily archive retained for 14 days plus four
1-GiB pre-release copies would average approximately 18 GiB in steady state
before version overhead. At a provisional USD 0.025/GiB-month planning input
this is USD 0.45/month for storage, plus requests and any data transfer.
This is a scenario, with regional rates, actual sizes, version overhead,
taxes and monitoring charges to be validated by the owner before provisioning.
SSE-S3 and off-host operator signing avoid a customer-managed KMS key.
Daily operator-assisted transfer requires a staffed schedule. Unattended
operation would require a separately designed credential broker or IAM Roles
Anywhere with managed certificate issuance, renewal and revocation.

References: [S3 pricing](https://aws.amazon.com/s3/pricing/),
[presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html),
[conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html),
[Lightsail alarms](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-alarms.html).

## Production consistency and recovery gate

1. Freeze releases and manual mutations. Inventory every potential database
   writer and target caller with its owner. Include the web API, worker
   processes, scheduled jobs and timers, queue consumers and producers,
   automatic retries, startup recovery, admin scripts and external clients.
2. Block new HTTP ingress and verify rejection externally. Pause queue and
   scheduled intake, then drain consumers and requests. Obtain evidence of
   zero active writers, in-flight target calls and running/retrying jobs.
   Persist offsets, pause receipts and unresolved target-ledger markers.
   Do not purge the queue to manufacture a zero count.
3. Stop all application writers after draining and inhibit automatic restart.
   Check process and container state, supervisor and scheduler state, queue
   pause and lease status, Mongo sessions/operations and the effective
   connection boundary. Sample Mongo insert/update/delete counters before
   and after the export as corroboration. An unexplained writer, in-flight
   external action, uncertain lease or write-counter delta invalidates the
   consistency claim. Preserve the failed attempt and reconcile before retry.
4. Record UTC quiescence boundary, case/audit/ledger checks and writer
   evidence. Export using an identity unable to write. Keep the boundary
   until export ends. Verify encryption and transfer per the approval,
   then resume only the approved stack, with ingress last.
5. For application rollback preserve the current database, require the
   exact prior image pair to pass schema-20 read, write, audit and no-replay
   checks, and replace a single drained writer. For data recovery preserve
   the original volume and restore to a new one. Compare audit and target
   ledger against the archive boundary and reconcile all post-boundary
   target operations before enabling any external writes.

Proposed owner targets are RPO 24 hours during a staffed daily schedule and
RTO 2 hours after incident declaration and authorization. Keep a separately
verified pre-release archive. The offline elapsed times cover a tiny synthetic
dataset and omit incident response, AWS transfer, key retrieval and provider
reconciliation. Measure these with a production-sized authorized exercise
before accepting either target. Repeat an isolated drill before a
schema-changing release and quarterly while the environment is in service.
