# Pre-Phase 22 ACRA Teammate-Change Reconciliation

## Conclusion

A Garden Business shareholder source file **did exist in reachable Git history** at:

`apps/backend/app/connectors/garden_business_shareholders.py`

Rika Miyachi added it in commit
`79e808f24a46b099ee111a0fa57492fa01a10a49` (`mock payload for acra entity`) on the
`acra-integration` line. That commit is not an ancestor of current `main`. The file was
then deleted in commit `6bcea75efd660e6dbaaa5dc2079b62749fc0abf1`
(`fix(acra): retire speculative activation and preserve routing guards`), also on the
same unmerged line. The current heads of `main`, `origin/acra-integration`, and
`origin/CRUDoperations` therefore do not contain the Garden file.

No ACRA/provider source was restored or changed by this task. Restoring the historical
file would alter provider mapping and synthetic ownership behavior, so it requires a
separately authorized external-provider/contract change.

## Historical findings

Repository-wide, case-insensitive history and reachable-object searches for `garden`,
`garden business`, `shareholder`, `shareholders`, and `coShareholdersDetails` found:

| Commit | Author | Main ancestry | Finding |
|---|---|---:|---|
| `4ae4ed19e10fa0ae25b432717df52bb5b8448d0f` | rikamiyachi | yes | Introduced `acra_bizfile_sandbox.py`. |
| `74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93` | Shane Tan | yes | Removed speculative OAuth/token lifecycle while retaining bounded company/officer/shareholder decoding and added tests/reports. |
| `897a4c4ca95f581110f60d8f9a9bc686e85b7451` | rikamiyachi | no | Unmerged attempt to compose a `bizfile_mock` mode, broaden UEN handling, add endpoint/transport behavior and debug/smoke utilities. |
| `79e808f24a46b099ee111a0fa57492fa01a10a49` | rikamiyachi | no | Added the Garden shareholder Python source fixture plus special-case connector logic/tests and a project-defined ownership rule. |
| `cb34e6637ebc7bbf482eefd9bacbcbacd8bcc061` | Rika Miyachi | no | Merged then-current `main` into `acra-integration`; no separate Garden introduction. |
| `6bcea75efd660e6dbaaa5dc2079b62749fc0abf1` | shaneqwaszx | no | Retired the speculative activation, Garden special case, debug utilities, and its provisional decision text while preserving routing guards. |
| `a81e7da1c677f063408952e2ae1a1a2478afc22b` | Rika Miyachi | yes | Strengthened non-Singapore zero-call regression coverage; not a Garden payload change. |

The exact reachable object path search returned only one Garden-named source path. It
was a Python source fixture containing a synthetic Mock shareholder payload, not a PDF,
CSV, sponsor document, private artefact, or standalone test file. Its associated tests
and documentation were changes inside commit `79e808f...`, but the named file itself
was source/fixture code.

## Branch/ref reconciliation

- `main` contains the accepted initial connector commit `4ae4ed19...`, its security
  remediation `74a5fd2f...`, and the current connector test. It does not contain
  `897a4c4...`, `79e808f...`, `cb34e66...`, or `6bcea75...`.
- `origin/acra-integration` contains all four commits outside main. Its current head is
  `6bcea75...`, where the Garden file and special-case rule are already deleted and the
  speculative runtime composition is retired.
- `origin/CRUDoperations` has merge base `b196d887964f0d93b93dfd2d39c271195eb19af9`
  with current main, has no commits ahead of main in the inspected comparison, contains
  the older connector source, and contains no Garden file.
- The only current refs containing commit `79e808f...` are `acra-integration`,
  `codex/pr26-acra-remediation`, and `origin/acra-integration`; of those, the first and
  remote-tracking heads advance through the deleting commit. The historical blob stays
  reachable through Git history, which explains why a teammate can remember it while
  no current branch head presents it as active source.

## Why it disappeared

Commit `79e808f...` implemented a special bounded Garden Business fallback when the
Marketplace Mock returned no shareholders, including a local payload and derived
economic-unit ownership relationships. This was project-defined behavior, not an
authoritative ACRA contract. Commit `6bcea75...` explicitly removed that speculative
activation and the Garden-only rule, deleted the debug utilities, and restored the
provider/routing boundary. Phase 21 now records BizFile as Dormant/Blocked and requires
explicit provider reauthorization before composition or mapping behavior may change.

## Required human action if the teammate expects different work

The Git history is conclusive for the Garden file above. If the teammate meant another
local or untracked artefact, obtain the exact filename, branch, and commit SHA (or a
sanitized description without confidential payload). Do not copy private/local data
into Git. Any proposal to revive the Garden special case, the `bizfile_mock` mode, new
paths, auth, network behavior, schemas, or mapping must be separately authorized and
reviewed against the Phase 21 activation gates.
