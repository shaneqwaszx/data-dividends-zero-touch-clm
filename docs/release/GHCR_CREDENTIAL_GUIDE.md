# Registry credential bootstrap, rotation and revocation

| Field | Value |
|---|---|
| Status | Design plus local implementation (`tools/release/credstore.py`, `registry.py`). **No token has been created, entered or stored. Nothing is installed on any host** |
| Registry | Private GHCR packages `ghcr.io/shaneqwaszx/clm-aws-demo-{frontend,backend,assistant,goldtier-egress}` |

## 1. Two identities

| Identity | Scope | Where it is used | Where it is stored |
|---|---|---|---|
| `publish` | `write:packages` (which includes reading) | This Windows machine only, for `publish --execute` | Windows Credential Manager, target `clm-release/ghcr-publish` |
| `pull` | `read:packages` only | Streamed once per image to the host over SSH standard input | Windows Credential Manager, target `clm-release/ghcr-pull`. **Never stored on the host** |

The tool refuses to store the same token under both identities. A host compromise during a
pull could at worst capture a read-only token; it could never push an image.

**Least privilege, and its limit.** At the time of writing, GitHub Packages accepts classic
personal access tokens, whose package scopes apply to every package the account can reach;
they cannot be limited to these four packages. Confirm the current rules in GitHub's
documentation before the bootstrap. Two ways to narrow the pull identity further (owner
decision; the second needs a new account):

1. Keep one account, two classic tokens with one scope each and a short expiry (default).
2. A separate reader account that is granted the Read role on these four packages only, and a
   `read:packages` token from that account. The token then reaches nothing else.

## 2. How a token is handled

- Typed by the owner at a hidden prompt (`getpass`). The commands refuse to run without an
  interactive terminal, so an automated session cannot enter or replace a token.
- Stored by the Windows Credential Manager (DPAPI, per Windows user). The entry's comment
  holds only the user name, creation time and stated expiry.
- Held in memory as a `Secret`: it cannot be printed, formatted or pickled; any text that
  contains it is redacted before it is logged or returned; a command whose argument or
  environment would contain it is refused.
- Given to Docker on standard input only (`--password-stdin`).
- **Publication:** a throwaway `DOCKER_CONFIG` directory with no credential helper is created,
  used, logged out and deleted on every exit path, including failures. The user's own Docker
  configuration is neither used nor changed.
- **Host pull:** one remote command creates `/run/clm-ghcr.XXXXXXXX` (memory-backed, mode 700),
  logs in from standard input, pulls by digest, logs out, deletes the directory and reports
  how many such directories remain (must be 0). This is the pattern reviewed for Approval B.
- Never in the repository, a Compose file, `compose.env`, a log, a result record, an
  environment variable or a command-line argument. `tests/release` checks this against the
  mock host and registry with sentinel tokens, on success paths and failure paths. Redaction
  removes the exact token and its base64 forms; it would not catch a token that some other
  program re-encoded.
- The host pull script removes its temporary directory on every exit, including a dropped
  session (`trap`). It has not been executed on a real host.

## 3. One-time bootstrap (owner; needs owner approval because it creates credentials)

1. On GitHub: create two classic tokens, each with one scope (`write:packages`;
   `read:packages`) and an expiry of 90 days or less. The tool refuses a longer stated expiry.
2. On this machine, in an interactive PowerShell window:

   ```powershell
   .\tools\release.ps1 creds bootstrap --identity publish --username <github user> --expires-at 2027-01-31T00:00:00Z
   .\tools\release.ps1 creds bootstrap --identity pull --username <github user> --expires-at 2027-01-31T00:00:00Z
   .\tools\release.ps1 creds status
   ```

   `--expires-at` is the expiry chosen on GitHub. The tool records it and refuses to use the
   token after that time.
3. Close the browser tab that showed the tokens. Do not save them anywhere else.

## 4. Rotation

Rotate before expiry (`creds status` shows `expires-soon` within 7 days), after any suspected
exposure, and after any release run that ended in a state you cannot explain.

1. Create the new token on GitHub (same single scope).
2. `.\tools\release.ps1 creds rotate --identity pull --username <user> --expires-at <new expiry>`.
   The tool refuses the token that is already stored.
3. Delete the old token on GitHub.

## 5. Expiry

An expired token stops the release with `CREDENTIAL_EXPIRED` before any registry or host
contact. Nothing is retried. Rotate, then start again inside a valid approval window.

## 6. Revocation

1. Delete the token on GitHub (Settings, Developer settings, Personal access tokens). That is
   the revocation.
2. `.\tools\release.ps1 creds revoke --identity <publish|pull>` removes the local copy.
3. If the pull token may have been exposed on the host: also confirm `/run/clm-ghcr.*` is
   absent and that no `~/.docker/config.json` on the host contains a `ghcr.io` entry. These are
   read-only checks for the host operator.

## 7. Host pull by digest compared with archive transfer over SSH

| | Host pull by digest (`--transfer pull`) | Archive over SSH (`--transfer load`) |
|---|---|---|
| Credential on the host | Read-only token in memory and a memory-backed directory for one command; nothing left | None at all |
| Long-lived credential on the host | None | None |
| Reference in `compose.env` | `repository@sha256:<manifest digest>`: content-addressed, as every release so far | A tag `rc-<commit12>-<config12>`; a loaded image has no registry digest, so the pin is a tag that the tool re-verifies by id |
| Identity proof | The registry digest plus the config digest check after publication | Archive SHA-256 on both sides plus the config digest of the loaded image |
| Evidence on this host | The manual procedure this script is modelled on was used for Approval B and R3. This script itself has never run there | None. The host uses the containerd image store, where the loaded image id may differ from the config digest; the tool then stops |
| Network | Host needs outbound HTTPS to GHCR | 67 MB to 587 MB per image uploaded over the operator's link |
| Needs GHCR | Yes | No (also works if the registry is unreachable) |
| Rollback store | The registry keeps every published digest | Only what is cached on the host |

**Recommendation: host pull by digest, with the read-only token streamed over SSH.** It keeps
no long-lived credential on the host, keeps digest pinning in `compose.env` exactly as today,
and follows the manual procedure already reviewed and used on this host, so it is the simpler
one to adopt. Archive transfer is implemented and mock-tested as a fallback for a registry outage;
it needs one supervised trial on the host before it is relied on.

## 8. Not done

No token exists. No registry call has been made by this toolchain. The package role
assignment for a reader account (option 2) is an owner action on GitHub.
