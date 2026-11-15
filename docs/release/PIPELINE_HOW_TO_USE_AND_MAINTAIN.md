# Pipeline: how to use and maintain

*Written to be pasted into an engineering handoff. It assumes no earlier context.*

## What it is

`tools/release/` is a Python 3.12 package (standard library only) with one PowerShell entry
point, `tools/release.ps1`. It prepares, publishes and deploys the AWS demo stack without
GitHub Actions. It has been tested only against mocks: it has never contacted the Lightsail
host or GHCR. It has been through several independent reviews and checks; the latest on code, at
the last code commit, is PASS WITH NOTES (`TEST_EVIDENCE_AND_LIMITATIONS.md` sections 4.7 to
4.9). No reviewer
has reviewed the whole toolchain at the head in one pass, and it is not cleared for use
against the host or the registry. All existing owner gates still apply; the tool makes
the mechanical work repeatable, it does not grant authority.

Full detail: `docs/release/PIPELINE_ARCHITECTURE.md` (design and limitations),
`RELEASE_AUTOMATION_RUNBOOK.md` (commands), `FIRST_AUTOMATED_RELEASE_CHECKLIST.md` (first real
use), `GHCR_CREDENTIAL_GUIDE.md`, `RISK_BASED_APPROVAL_PROPOSAL.md` (a proposal, not in force),
`LOCAL_RELEASE_CONTROLLER.md`, `TEST_EVIDENCE_AND_LIMITATIONS.md`.

## The rules you must not break

1. **You do not contact the host, AWS or the registry.** Only the session that owns the host
   runs `publish --execute` or `deploy --execute`, in an owner-approved window. Everything
   else (`verify-source`, `checks`, `image`, `manifest`, `validate`, `plan`, `controller tick`,
   any `--plan-only` or `--dry-run --offline`) stays on this machine.
2. **You never approve.** `approve`, `accept`, `recover`, `unlock` and `creds bootstrap|rotate` refuse a
   non-interactive caller. Do not work around that.
3. **Never rebuild a qualified image.** Accept it by its exact image id.
4. **Never** `down`, `-v`, `--remove-orphans`, volume removal, `compose rm`, a second backend,
   a floating tag, or a credential in a file or on a command line.
5. A `NOT_RUN` check is not a pass. Say so.

## Using it for a release you have built

```powershell
git fetch origin                                  # then check out the approved commit, clean
.\tools\release.ps1 verify-source --commit <40 hex> --tree <40 hex>
.\tools\release.ps1 checks --change-class <CLASS>         # add --list to preview
.\tools\release.ps1 image --service <frontend|backend|assistant> --commit <40 hex> `
    --reference <local tag> --image-id sha256:<64 hex>    # or --build
.\tools\release.ps1 manifest --request <request.json>     # see samples/release-request...json
.\tools\release.ps1 validate --manifest <manifest.json>
.\tools\release.ps1 plan --manifest <manifest.json>
```

Hand the manifest, the plan and the image output to the independent Quality Gate, then to the
release coordinator. Report the manifest SHA-256 printed by `validate`.

What you decide in the request, and must justify from evidence, not from an old document:

- `services_changed`, `change_classes`, `risk_class` (the tool refuses a class below its floor);
- `active_host_overlays`: which optional overlays are live on the host (`assistant`,
  `assistant-provider`, `goldtier`). Ask the host operator; do not guess;
- `rollback` per service: the target digest, `data_compatible` (`true`, `false`, `"unproven"`),
  `automatic`, and stop conditions. For a backend also the target's source commit and
  case-snapshot schema version, and `target_confirmed_on_host`. A schema-19 target
  (`4c1db49`) is refused. The tool checks only what you declare: take the target's commit and
  digest from the host lane's record. If you cannot show compatibility, write `"unproven"`;
- `coupling`: for example a frontend that needs this release's backend;
- `smoke`: public, signed-out requests and the exact status each must return;
- `declared_config_changes`: any network, port, environment variable or container setting the
  release adds. Undeclared additions are refused; declared ones raise the risk class.

## When you change the product

| You changed | Do this in the same change |
|---|---|
| Any Compose file | `.\tools\release.ps1 baseline` fails. Run `baseline --write`, **read the diff of `tools/release/policy/effective-baseline.json`**, and have it reviewed. If the change adds a network, port or variable, the next manifest must declare it |
| `.github/workflows/ci.yml` (a job added, renamed or removed) | Update `CHECKS`, `SELECTION` or `MANUAL_CI_JOBS` in `tools/release/source.py`; `test_every_ci_job_is_mirrored_or_listed_as_not_run` tells you |
| A Dockerfile's copied paths | Update `in_image_paths` in `tools/release/catalog.py` so file equality covers the same files |
| The case-snapshot schema version | Nothing in the tool: it reads `CASE_SNAPSHOT_SCHEMA_VERSION` from the commit. In the manifest, the rollback entry must then say `data_compatible: false` for an older target |
| Added a service or an overlay | Add it to `catalog.py` (service, overlay set, wrapper), to `render.NETWORK_CEILING`, regenerate the baseline, add tests. Until then a release naming it is refused |
| The runbook wrappers (`dc`, `dca`, `dcg`) | Update `catalog.OVERLAY_SETS` and `wrapper_set_for` to match `deploy/LIGHTSAIL_RUNTIME.md`, which stays the authority |

## When you change the pipeline itself

Change class `CI_TOOLING`. Before handing over:

```bash
python -m ruff check --select E,F,I,UP,B,SIM --line-length 100 --target-version py312 tools/release tests/release
python -m mypy --strict -p tools.release
python -m pytest tests/release -q -p no:cacheprovider
python scripts/check_secrets.py
python -m pytest tests/deploy -q -p no:cacheprovider      # from Git Bash
```

Design rules to keep:

- Every external action is a `Command` with an honest `Effect`, issued through the `Gate`.
  Never call `subprocess` directly from a new module. A host command that changes anything is
  `HOST_WRITE`; if you label a write as a read, dry-run stops being safe.
- Host Compose commands come only from `Host.compose*` in `host.py`. Do not add `down`, `rm`,
  `run` or scaling; the gate's deny-list would refuse them anyway.
- A credential is a `Secret`, read from the store at the moment of use and passed on standard
  input. Tests use sentinel tokens built by concatenation (`fakes.sentinel_token`) so
  `scripts/check_secrets.py` stays green; do not write a token-shaped literal.
- Refuse by raising `StopCondition(code, message)` with a stable code. Messages never contain
  a secret or a full configuration.
- A new safety rule needs a test that fails without it. A new host step needs the mock host in
  `tests/release/fakes.py` to model it.
- Do not add a third-party dependency: the release path must run from a plain Python install.

## Result states you will see

`FAILED_NO_CHANGE`, `DEPLOYED_AWAITING_ACCEPTANCE`, `ACCEPTED`, `ACCEPTANCE_FAILED`,
`ROLLED_BACK`, `FAILED_HELD`, and for a rollback without a verified outcome
`ROLLBACK_IN_PROGRESS` and `ROLLBACK_INTERRUPTED` (diagram: `PIPELINE_ARCHITECTURE.md` 3.7).
`ROLLBACK_IN_PROGRESS` is written before the first rollback step; found at rest it means the
tool died mid-rollback and the host state is unknown. Only `recover` (read-only, run by a
person) or a further `rollback` attempt under a new approval can move a release out of an
unfinished rollback, and only `recover` can return it to awaiting acceptance, on what it
verified. Never
report a release as rolled back, or the previous service as restored, from anything but a
`ROLLED_BACK` record.

If you change the rollback code: keep the in-progress record ahead of the first step, keep
every step journalled before it is issued, and keep `rollback()` returning only after its
final verification. `tests/release/test_rollback_interruption.py` holds those rules.


## Redeploying after a failed acceptance (owner decision, 2026-11-15)

Exact words: "A release that previously failed acceptance MAY be redeployed under the same release_id, but only as a new, independently identifiable and authorised deployment attempt. The same release_id identifies the qualified release; the new attempt must have its own immutable attempt_id."

`release_id` = the qualified release; `attempt_id` = one deployment attempt of it; a retry keeps
the `release_id` and gets a new `attempt_id`. The tool has no `attempt_id` today. Until the
mandatory follow-up engineering in `PIPELINE_ARCHITECTURE.md` section 3.8 (requirements 1 to
4) is implemented, tested and independently reviewed, **do not deploy a release again after a
failed acceptance**, and do not build that retry path as a side effect of other work: it is a
piece of engineering of its own, with its own review. For now a failed release is replaced by
a new release with a new `release_id`.

## Known gaps (do not assume they work)

Never run against the real host or registry; no single review covers the whole toolchain at
the head; **redeploying a release after a failed acceptance is prohibited for now**: the owner's
2026-11-15 decision allows it only as a new attempt with its own `attempt_id`, which the tool
does not have, and four of its six requirements are not fully enforced
(`PIPELINE_ARCHITECTURE.md` 3.8, "mandatory follow-up engineering"); the tool does not block
it, so the rule is procedural; approval records are not signed; "compatible" is a declaration the
tool cannot verify; the configuration summary does not cover every Compose field; archive
transfer is unproven on the host's image store; installing changed Compose files or host
units is manual; Mongo, GoldTier egress and firewall changes are manual; the backup check
does not validate an archive; a backend swap stops ingress briefly. See
`PIPELINE_ARCHITECTURE.md` section 5 and `TEST_EVIDENCE_AND_LIMITATIONS.md`.
