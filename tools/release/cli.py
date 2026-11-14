"""Command line for the release toolchain. Run through ``tools/release.ps1`` on Windows.

Nothing changes the host or the registry unless ``--execute`` is given together with an owner
approval record. The default for ``publish`` and ``deploy`` is a dry run.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Any

from . import approval as approvals
from . import catalog, controller, credstore, deploy, images, records, registry, render, source
from .core import (
    AuditLog,
    Gate,
    Mode,
    ReleaseError,
    StopCondition,
    SubprocessRunner,
    redact,
    write_json,
)
from .host import Host, SshTarget
from .manifest import load_manifest, manifest_hash, release_tag, require_publishable

ROOT = Path(__file__).resolve().parents[2]


def _emit(document: Any) -> None:
    print(redact(json.dumps(document, indent=2, sort_keys=True, default=str)))


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _mode(args: argparse.Namespace) -> Mode:
    if getattr(args, "plan_only", False):
        return Mode.PLAN_ONLY
    if getattr(args, "execute", False):
        return Mode.EXECUTE
    return Mode.DRY_RUN


def _store(args: argparse.Namespace) -> records.StateStore:
    return records.StateStore(
        Path(args.state_dir) if args.state_dir else records.default_state_dir()
    )


def _gate(
    args: argparse.Namespace, mode: Mode, store: records.StateStore, release: str = ""
) -> Gate:
    name = f"{release or 'toolchain'}.audit.jsonl"
    path = (store.release_dir(release) if release else store.root) / name
    log = AuditLog(
        path=path, echo=(lambda line: print(line, file=sys.stderr)) if args.verbose else None
    )
    return Gate(SubprocessRunner(), mode, log, host_reads=not getattr(args, "offline", False))


def _host(args: argparse.Namespace, gate: Gate) -> Host:
    """The SSH target comes from an operator file outside the repository, never from here."""

    config = getattr(args, "operator_config", None)
    if config is None:
        if gate.mode is Mode.EXECUTE:
            raise StopCondition(
                "OPERATOR_CONFIG_MISSING", "--operator-config is required to execute"
            )
        gate._host_reads = False  # no host named: nothing can be contacted
        return Host(gate, SshTarget("host-not-configured"), catalog.HostProfile())
    data = json.loads(Path(config).read_text(encoding="utf-8"))
    profile = catalog.HostProfile(backup_glob=data.get("backup_dir"))
    return Host(gate, SshTarget.load(Path(config)), profile)


# -- commands ------------------------------------------------------------------------------


def cmd_verify_source(args: argparse.Namespace) -> int:
    gate = _gate(args, Mode.LOCAL, _store(args))
    state = source.verify_source(
        gate,
        Path(args.root),
        commit=args.commit,
        tree=args.tree,
        allow_untracked=tuple(args.allow_untracked),
    )
    _emit({"status": "PASS", "commit": state.commit, "tree": state.tree, "base": state.base_ref})
    return 0


def cmd_checks(args: argparse.Namespace) -> int:
    names = source.select_checks(args.change_class, tuple(args.include))
    if args.list:
        _emit({"selected": names, "manual_ci_jobs": source.MANUAL_CI_JOBS})
        return 0
    results = source.run_checks(_gate(args, Mode.LOCAL, _store(args)), Path(args.root), names)
    _emit(results)
    return 1 if any(r["status"] == "FAIL" for r in results) else 0


def cmd_image(args: argparse.Namespace) -> int:
    gate = _gate(args, Mode.LOCAL, _store(args))
    root = Path(args.root)
    if args.build:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="clm-context-") as scratch:
            context = images.export_context(gate, root, args.commit, Path(scratch) / "context")
            images.build(gate, context, args.service, args.reference)
        mode = "built"
    else:
        if not args.image_id:
            raise ReleaseError("IMAGE_ID_REQUIRED", "give --image-id to accept an existing image")
        images.accept_existing(gate, args.reference, args.image_id)
        mode = "accepted-existing"
    _emit(
        images.describe_candidate(gate, root, args.commit, args.service, args.reference, mode=mode)
    )
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    store = _store(args)
    gate = _gate(args, Mode.LOCAL, store)
    request = controller.load_request(Path(args.request))
    manifest = controller.assemble_manifest(
        gate, Path(args.root), request, store, run_checks=not args.skip_checks
    )
    target = (
        Path(args.out) if args.out else store.release_dir(manifest["release_id"]) / "manifest.json"
    )
    write_json(target, manifest)
    _emit(
        {
            "manifest": str(target),
            "manifest_sha256": manifest_hash(manifest),
            "release_id": manifest["release_id"],
            "risk_class": manifest["risk_class"],
        }
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    gate = _gate(args, Mode.PLAN_ONLY, _store(args))
    sets = [] if args.no_render else render.validate_release_config(gate, Path(args.root), manifest)
    _emit({"status": "PASS", "manifest_sha256": manifest_hash(manifest), "rendered_sets": sets})
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    plan = deploy.build_plan(manifest, transfer=args.transfer, profile=catalog.HostProfile())
    store = _store(args)
    write_json(store.release_dir(manifest["release_id"]) / "plan.json", plan)
    _emit(plan)
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    record = approvals.create_approval(
        manifest,
        services=args.service,
        actions=args.action,
        auto_rollback=args.auto_rollback,
        not_before=args.not_before,
        expires_at=args.expires_at,
        approved_by=args.approved_by,
        confirm=input,
        interactive=_interactive(),
    )
    target = (
        Path(args.out)
        if args.out
        else (_store(args).release_dir(manifest["release_id"]) / f"{record['approval_id']}.json")
    )
    approvals.save_approval(target, record)
    _emit(
        {
            "approval": str(target),
            "approval_id": record["approval_id"],
            "expires_at": record["expires_at"],
        }
    )
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    store, mode = _store(args), _mode(args)
    gate = _gate(args, mode, store, manifest["release_id"])
    services = [s for s in manifest["images"] if s in (args.service or manifest["images"])]
    require_publishable(manifest, services)
    if mode is Mode.PLAN_ONLY:
        _emit(
            {
                "would_publish": {
                    s: f"{manifest['images'][s]['repository']}:{release_tag(manifest, s)}"
                    for s in services
                }
            }
        )
        return 0
    record = approvals.load_approval(Path(args.approval)) if args.approval else None
    if mode is Mode.EXECUTE or record is not None:
        if record is None:
            raise StopCondition("APPROVAL_MISSING", "publication needs an owner approval record")
        approvals.check_approval(
            record,
            manifest,
            action="publish",
            services=manifest["services_changed"],
            consumed=store.consumed_approvals(),
        )
        gate.set_deadline(approvals.deadline(record))
    with store.lock(manifest["release_id"]):
        if mode is Mode.EXECUTE:
            credential = credstore.fetch(credstore.default_store(), "publish")
        else:
            from .core import Secret

            credential = credstore.StoredCredential(
                "dry-run", Secret("dry-run-no-credential"), "", ""
            )
        published = registry.publish(gate, manifest, services, credential)
        if mode is Mode.EXECUTE:
            assert record is not None
            store.consume_approval(record["approval_id"], "publish")
            target = store.release_dir(manifest["release_id"]) / "manifest.published.json"
            write_json(target, published)
            _emit(
                {
                    "published_manifest": str(target),
                    "manifest_sha256": manifest_hash(published),
                    "note": "the deploy approval must be given for this published manifest",
                }
            )
        else:
            _emit({"state": "DRY_RUN_OK", "would_issue": [c.purpose for c in gate.skipped]})
    return 0


def _context(args: argparse.Namespace, mode: Mode) -> deploy.Context:
    manifest = load_manifest(Path(args.manifest))
    store = _store(args)
    gate = _gate(args, mode, store, manifest["release_id"])
    host = _host(args, gate)
    record = approvals.load_approval(Path(args.approval)) if args.approval else None
    return deploy.Context(
        gate=gate,
        host=host,
        manifest=manifest,
        store=store,
        root=Path(args.root),
        transfer=args.transfer,
        approval=record,
        credentials=credstore.default_store() if mode is Mode.EXECUTE else None,
    )


def cmd_deploy(args: argparse.Namespace) -> int:
    mode = _mode(args)
    if mode is Mode.PLAN_ONLY:
        return cmd_plan(args)
    ctx = _context(args, mode)
    outcome = deploy.run(ctx)
    if outcome["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE:
        sheet = ctx.store.release_dir(ctx.manifest["release_id"]) / "BROWSER_ACCEPTANCE_RUNSHEET.md"
        sheet.write_text(
            deploy.acceptance_runsheet(ctx.manifest, ctx.host.profile), encoding="utf-8"
        )
        outcome["runsheet"] = str(sheet)
    _emit(outcome)
    return (
        0 if outcome["state"] in {records.DRY_RUN_OK, records.DEPLOYED_AWAITING_ACCEPTANCE} else 2
    )


def cmd_accept(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    outcome = deploy.accept(
        _store(args),
        manifest,
        passed=args.result == "pass",
        accepted_by=args.accepted_by,
        interactive=_interactive(),
    )
    _emit({"state": outcome["state"], "known_good": outcome.get("known_good")})
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    mode = _mode(args)
    ctx = _context(args, mode)
    if mode is not Mode.EXECUTE:
        state = deploy.RunState(applied=ctx.changed, pins_before={s: "?" for s in ctx.changed})
        _emit(
            {
                "would_roll_back": [s for s in catalog.ROLLBACK_ORDER if s in ctx.changed],
                "blocked_by": deploy.rollback_blockers(ctx, state, None),
            }
        )
        return 0
    outcome = deploy.manual_rollback(ctx, ctx.manifest["release_id"])
    _emit({"state": outcome["state"], "held_reason": outcome.get("held_reason")})
    return 0 if outcome["state"] == records.ROLLED_BACK else 2


def cmd_status(args: argparse.Namespace) -> int:
    store = _store(args)
    releases = (
        sorted(p.name for p in (store.root / "releases").glob("rel-*"))
        if (store.root / "releases").is_dir()
        else []
    )
    _emit(
        {
            "state_dir": str(store.root),
            "known_good": store.known_good(),
            "lock_held": (store.root / "release.lock").exists(),
            "releases": {
                r: (store.read_result(r) or {}).get("state", "NO_RESULT") for r in releases
            },
        }
    )
    return 0


def cmd_unlock(args: argparse.Namespace) -> int:
    if not _interactive():
        raise StopCondition("UNLOCK_NEEDS_OWNER", "a lock is only removed by a person")
    if input("Type UNLOCK after confirming no release operation is running: ").strip() != "UNLOCK":
        raise StopCondition("UNLOCK_NOT_CONFIRMED", "not confirmed")
    _emit({"removed": _store(args).unlock()})
    return 0


def cmd_creds(args: argparse.Namespace) -> int:
    store = credstore.default_store()
    if args.action == "status":
        _emit(credstore.status(store))
        return 0
    if args.action == "revoke":
        removed = credstore.revoke_local(store, args.identity)
        _emit(
            {
                "removed_from_this_machine": removed,
                "next": "revoke the token on GitHub (Settings, Developer settings, Tokens)",
            }
        )
        return 0
    action = credstore.bootstrap if args.action == "bootstrap" else credstore.rotate
    metadata = action(
        store,
        args.identity,
        username=args.username,
        expires_at=args.expires_at,
        prompt=getpass.getpass,
        interactive=_interactive(),
    )
    _emit({"stored": metadata})
    return 0


def cmd_controller(args: argparse.Namespace) -> int:
    store = _store(args)
    instance = controller.Controller(_gate(args, Mode.LOCAL, store), Path(args.root), store)
    if args.action == "tick":
        _emit(instance.tick(run_checks=not args.skip_checks))
    elif args.action == "retry":
        _emit({"retry": instance.retry(args.request_id)})
    else:
        _emit(instance.status())
    return 0


def cmd_baseline(args: argparse.Namespace) -> int:
    gate = _gate(args, Mode.PLAN_ONLY, _store(args))
    fresh = render.build_baseline(gate, Path(args.root))
    if args.write:
        render.BASELINE.write_text(
            json.dumps(fresh, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        _emit({"written": str(render.BASELINE), "note": "review the diff before committing"})
        return 0
    same = fresh == render.load_baseline()
    _emit({"baseline_matches_compose_files": same})
    return 0 if same else 1


# -- parser --------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release", description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository checkout (default: this one)")
    parser.add_argument("--state-dir", default=None, help="release state directory")
    parser.add_argument("--verbose", action="store_true", help="echo redacted audit events")
    sub = parser.add_subparsers(dest="command", required=True)

    def modes(p: argparse.ArgumentParser) -> None:
        group = p.add_mutually_exclusive_group()
        group.add_argument(
            "--plan-only", action="store_true", help="print the plan; contact nothing"
        )
        group.add_argument(
            "--dry-run", action="store_true", help="read only; no host or registry write (default)"
        )
        group.add_argument("--execute", action="store_true", help="perform the approved changes")

    p = sub.add_parser("verify-source", help="exact approved commit and a clean checkout")
    p.add_argument("--commit", required=True)
    p.add_argument("--tree")
    p.add_argument("--allow-untracked", action="append", default=[])
    p.set_defaults(func=cmd_verify_source)

    p = sub.add_parser("checks", help="run the local mirror of the CI jobs for a change class")
    p.add_argument("--change-class", action="append", required=True)
    p.add_argument("--include", action="append", default=[])
    p.add_argument("--list", action="store_true")
    p.set_defaults(func=cmd_checks)

    p = sub.add_parser("image", help="accept an existing image by id, or build one, and prove it")
    p.add_argument("--service", required=True, choices=sorted(images.DOCKERFILES))
    p.add_argument("--commit", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--image-id")
    p.add_argument("--build", action="store_true")
    p.set_defaults(func=cmd_image)

    p = sub.add_parser("manifest", help="assemble a release manifest from a request")
    p.add_argument("--request", required=True)
    p.add_argument("--out")
    p.add_argument(
        "--skip-checks", action="store_true", help="record no check results (never a pass)"
    )
    p.set_defaults(func=cmd_manifest)

    p = sub.add_parser(
        "validate", help="validate a manifest and its effective Compose configuration"
    )
    p.add_argument("--manifest", required=True)
    p.add_argument("--no-render", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("plan", help="show exactly which services change and which must not")
    p.add_argument("--manifest", required=True)
    p.add_argument("--transfer", choices=["pull", "load"], default="pull")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("approve", help="owner only: record an approval bound to the manifest hash")
    p.add_argument("--manifest", required=True)
    p.add_argument("--service", action="append", required=True)
    p.add_argument("--action", action="append", required=True, choices=["publish", "deploy"])
    p.add_argument("--not-before", required=True)
    p.add_argument("--expires-at", required=True)
    p.add_argument("--approved-by", required=True)
    p.add_argument("--auto-rollback", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("publish", help="push the approved images to GHCR by digest")
    p.add_argument("--manifest", required=True)
    p.add_argument("--approval")
    p.add_argument("--service", action="append")
    modes(p)
    p.set_defaults(func=cmd_publish)

    for name, func, text in (
        ("deploy", cmd_deploy, "preflight, apply, verify; stops for browser acceptance"),
        ("rollback", cmd_rollback, "owner-requested rollback of a deployed release"),
    ):
        p = sub.add_parser(name, help=text)
        p.add_argument("--manifest", required=True)
        p.add_argument("--approval")
        p.add_argument("--transfer", choices=["pull", "load"], default="pull")
        p.add_argument(
            "--operator-config", help="JSON outside the repository naming the SSH target"
        )
        p.add_argument("--offline", action="store_true", help="dry run without any host read")
        modes(p)
        p.set_defaults(func=func)

    p = sub.add_parser("accept", help="owner only: record the browser acceptance result")
    p.add_argument("--manifest", required=True)
    p.add_argument("--result", required=True, choices=["pass", "fail"])
    p.add_argument("--accepted-by", required=True)
    p.set_defaults(func=cmd_accept)

    sub.add_parser("status", help="known-good release, lock and results").set_defaults(
        func=cmd_status
    )
    sub.add_parser("unlock", help="remove a stale local lock").set_defaults(func=cmd_unlock)

    p = sub.add_parser("creds", help="GHCR identities in the Windows Credential Manager")
    p.add_argument("action", choices=["bootstrap", "rotate", "status", "revoke"])
    p.add_argument("--identity", choices=sorted(credstore.IDENTITIES))
    p.add_argument("--username")
    p.add_argument("--expires-at")
    p.set_defaults(func=cmd_creds)

    p = sub.add_parser("controller", help="local release controller")
    p.add_argument("action", choices=["tick", "status", "retry"])
    p.add_argument("--request-id")
    p.add_argument("--skip-checks", action="store_true")
    p.set_defaults(func=cmd_controller)

    p = sub.add_parser("baseline", help="compare (or rewrite) the effective-config baseline")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_baseline)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except ReleaseError as error:
        kind = "STOP" if isinstance(error, StopCondition) else "ERROR"
        print(redact(f"{kind} {error.code}: {error.message}"), file=sys.stderr)
        return 3 if isinstance(error, StopCondition) else 1


if __name__ == "__main__":
    raise SystemExit(main())
