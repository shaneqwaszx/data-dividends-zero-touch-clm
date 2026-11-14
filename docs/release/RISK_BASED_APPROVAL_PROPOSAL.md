# Risk-based approval: proposal

| Field | Value |
|---|---|
| Status | **PROPOSAL. Not in force.** Every owner gate that exists today stays exactly as it is until the owner approves a revised procedure in writing. Nothing in the toolchain relaxes a gate |
| Decides | The repository owner |
| Purpose | Fewer decisions per routine release without less control over risky ones |

## 1. The problem

A frontend-only swap currently takes the same number of owner decisions as a backend change:
source approval, image approval, publication approval, a host window, and a go-ahead at
several steps inside the window. The mechanical steps are now code with tests, so a decision
per command adds delay but no information.

## 2. Proposed classes

| Class | Releases in it | Why |
|---|---|---|
| **LOW** | Reviewed frontend-only and static releases: the Caddy image, the built React assets, the Caddyfile | Stateless; one container; rollback is the previous image and is data-compatible by construction |
| **MEDIUM** | Assistant-only updates, and updates to existing approved model-free services, with no new network, port, recipient or key | Private service; the fastest rollback is to stop it (fixed 503, onboarding unaffected); its stores live on a volume a newer image may upgrade, so image rollback is not automatic |
| **HIGH** | Backend or Mongo changes; case-snapshot schema or target-ledger compatibility; new egress or firewall rules; GoldTier external writes; ACRA windows that can create cases; new AI recipients, provider keys or paid inference | Durable data, external systems, cost or the network boundary |

The toolchain computes a **floor** from the manifest and refuses a lower declared class:

- the highest base class among the changed services (frontend LOW, assistant MEDIUM, backend HIGH);
- assistant with the hosted provider overlay active: HIGH;
- a declared new network, published port or container setting: HIGH;
- a declared new environment variable: MEDIUM, or HIGH if its name concerns a key, token,
  secret, provider, egress, GoldTier, ACRA, Anthropic or write switch;
- change class `PERSISTENCE`, `EXTERNAL_PROVIDER` or `AUTH_RBAC_SECURITY`: HIGH.

The owner may always declare a higher class. Mongo, the GoldTier egress services and firewall
files are never changed by the automated applier, whatever the class.

## 3. Proposed approvals per class

| Step | LOW | MEDIUM | HIGH |
|---|---|---|---|
| Source: merged by the owner on `main` | required | required | required |
| Local checks for the change class | required | required | required, plus the manual CI jobs the class needs |
| Independent Quality Gate on the exact candidate | required | required | required |
| Independent image QG (file equality, fingerprint, no secrets) | the toolchain's own image checks, reviewed once per release in the QG | same, plus the assistant fingerprint equals the reviewed value | separate independent image QG, as today |
| Owner approval to publish | **one combined approval** (publish + deploy) | **one combined approval** (publish + deploy) | separate publish approval |
| Owner approval to deploy | covered by the combined approval | covered by the combined approval | separate deploy approval, after the host preflight result has been read |
| Decisions inside the window | none: one approved run does preflight, deploy and postflight | none | owner go-ahead after preflight; the applier may be run service by service |
| Automatic rollback | yes, if the owner ticks it | no by default (stop the assistant instead); yes only with proven store compatibility | no, unless both schema versions are equal, the target is confirmed on the host, and the owner ticks it |
| Browser acceptance by the owner | required | required | required |
| Window length | up to 24 h cap; suggested 2 h | suggested 2 h | suggested 2 h, with the backup taken inside the window |

"One combined approval" means one approval record whose actions are `publish` and `deploy`.
Because publication fills in the registry digests and so changes the manifest hash, the
toolchain today still needs a second record for the published manifest. If the owner accepts
this proposal, the small follow-up is to let one record name the candidate hash and accept the
published manifest derived from it (`candidate_manifest_sha256`). Until then the owner types
two approvals a few minutes apart.

## 4. What stays the same in every class

- The owner approves in person at a terminal; an approval names one manifest hash, one exact
  service list, a start and an expiry; expiry stops execution and is never extended silently.
- No auto-promotion. The controller stops at "promotion ready".
- One host operator session, one release at a time (local and host locks).
- Images are published as built and pinned by digest. No rebuild after qualification, no
  floating tag.
- Never `down`, `-v`, `--remove-orphans`, volume removal or a second backend.
- A stateful backend is never rolled back blindly.
- GoldTier external writes, ACRA case-creating windows, provider keys and paid inference keep
  their own separate owner approvals; this pipeline does not perform any of them.

## 5. What the owner is asked to decide

1. Accept, change or reject the three classes and the floor rules in section 2.
2. Accept, change or reject the combined approval for LOW and MEDIUM (section 3).
3. Whether a routine LOW release may use automatic rollback by default.
4. Whether to add the signed approval record (`PIPELINE_ARCHITECTURE.md`, limitation 2) before
   any class is relaxed.

Until those answers exist, treat every release as HIGH for approval purposes and use the
toolchain only to do the mechanical work faster and more repeatably.
