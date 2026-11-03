"""HR recovery centre: what is stopping the AI Assistant, why, and who may fix it.

Pure functions over the views AI Models already serves (the overview, Claude's spending and
reconciliation views). Nothing here reads a ledger, a key or a store, and nothing writes: each
problem names an action that one of the existing guarded endpoints performs (reconcile, resolve
a run, enter a key, Test connection, edit a limit, qualify, activate, roll back), or, where only
the owner or an operator may act (D-110 R8: breaker reset, release, quarantine coverage, the P1
attestation), an owner recovery request with the evidence attached.

Every value shown is already on the page: codes, counts, amounts and times. No key, path,
workspace secret or case data. Not a qualification-basis file.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

Severity = Literal["blocking", "warning", "info"]
Authority = Literal["HR", "OWNER", "IT", "NONE"]
ActionKind = Literal[
    "RECONCILE",
    "RESOLVE_RUN",
    "ENTER_KEY",
    "TEST_CONNECTION",
    "EDIT_DAILY_LIMIT",
    "EDIT_LIFETIME_LIMIT",
    "QUALIFY",
    "ACTIVATE",
    "ROLLBACK",
    "SIGN_IN_AGAIN",
    "WAIT",
    "OWNER_REQUEST",
]

# The console section where each HR action's existing, guarded control lives.
ACTION_SECTION: dict[str, str] = {
    "RECONCILE": "spending",
    "RESOLVE_RUN": "spending",
    "ENTER_KEY": "providers",
    "TEST_CONNECTION": "qualifications",
    "EDIT_DAILY_LIMIT": "spending",
    "EDIT_LIFETIME_LIMIT": "spending",
    "QUALIFY": "qualifications",
    "ACTIVATE": "overview",
    "ROLLBACK": "overview",
    "SIGN_IN_AGAIN": "providers",
    "WAIT": "overview",
    "OWNER_REQUEST": "overview",
}

# Problems an owner recovery request may name: only those the owner or IT must act on.
OWNER_PROBLEMS = frozenset(
    {
        "CLAUDE_BREAKER_OPEN",
        "GPT_OSS_BREAKER_OPEN",
        "CLAUDE_QUARANTINED_CALLS",
        "CLAUDE_OPEN_CALLS_STUCK",
        "CLAUDE_RECONCILIATION_RUN_UNRESOLVED",
        "CLAUDE_RECONCILIATION_MARKER",
        "CLAUDE_RECONCILIATION_PREREQUISITE",
        "CLAUDE_NEVER_RECONCILED",
        "CLAUDE_LEDGER_UNREADABLE",
        "CLAUDE_SERVER_KEY_UNAVAILABLE",
        "GPT_OSS_SERVER_KEY_UNAVAILABLE",
        "CLAUDE_LIFETIME_CEILING_REACHED",
        "CLAUDE_SETUP_NOT_READY",
    }
)

DUE_SOON_SECONDS = 24 * 3600
KEY_ENDING_SECONDS = 3600
# An open paid call older than this is not just in flight.
OPEN_CALL_PATIENCE_SECONDS = 15 * 60


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    label: str
    authority: Authority
    # What to check afterwards: the problem's own code no longer appears.
    verify: str
    profile_id: str | None = None
    run_id: str | None = None
    # Codes of other problems that must be cleared first (the action's own refusal list).
    blocked_by: tuple[str, ...] = ()

    def view(self, hr_allowed: bool) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "authority": self.authority,
            "permitted": hr_allowed and self.authority == "HR" and not self.blocked_by,
            "section": ACTION_SECTION[self.kind],
            "verify": self.verify,
            "profile_id": self.profile_id,
            "run_id": self.run_id,
            "blocked_by": list(self.blocked_by),
        }


@dataclass(frozen=True)
class Problem:
    code: str
    severity: Severity
    provider: Literal["anthropic", "openrouter", "local", "service"]
    title: str
    cause: str
    actions: tuple[Action, ...]
    evidence: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def view(self, hr_allowed: bool) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "provider": self.provider,
            "title": self.title,
            "cause": self.cause,
            "evidence": [{"label": label, "value": value} for label, value in self.evidence],
            "actions": [action.view(hr_allowed) for action in self.actions],
            "owner_request_allowed": self.code in OWNER_PROBLEMS,
        }


def _parse(moment: object) -> datetime | None:
    if not isinstance(moment, str) or not moment:
        return None
    try:
        value = datetime.fromisoformat(moment.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _usd(micro: object) -> str:
    return f"US${int(micro) / 1_000_000:.2f}" if isinstance(micro, int) else "unknown"


def _map(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _owner(label: str, verify: str) -> Action:
    return Action("OWNER_REQUEST", label, "OWNER", verify)


def _credential(
    provider: Literal["anthropic", "openrouter"],
    name: str,
    credential: Mapping[str, Any],
    now: datetime,
    test_profile: str | None,
) -> list[Problem]:
    prefix = "CLAUDE" if provider == "anthropic" else "GPT_OSS"
    status, source = credential.get("status"), credential.get("source")
    hr_editable = bool(credential.get("hr_editable"))
    test = (
        (Action("TEST_CONNECTION", "Test connection", "HR", "Test connection passes",
                profile_id=test_profile),)
        if test_profile
        else ()
    )
    expires = credential.get("expires_at")
    evidence: list[tuple[str, str]] = [("Key source", str(source or "none"))]
    if isinstance(expires, int | float):
        evidence.append(("HR key ends", datetime.fromtimestamp(expires, UTC).isoformat()))
    if status == "configured":
        if (
            source == "hr_session"
            and isinstance(expires, int | float)
            and 0 <= expires - now.timestamp() <= KEY_ENDING_SECONDS
        ):
            return [
                Problem(
                    f"{prefix}_HR_KEY_ENDING",
                    "info",
                    provider,
                    f"{name}: the HR session key ends within the hour",
                    "An HR key lasts only as long as the HR session that entered it, and at most"
                    " 8 hours (D-106). After that the server key is used, if there is one.",
                    (Action("ENTER_KEY", "Enter the key again after signing in", "HR",
                            "the key shows as configured with a later end time"),),
                    tuple(evidence),
                )
            ]
        return []
    if status == "unverified":
        return [
            Problem(
                f"{prefix}_KEY_UNVERIFIED",
                "blocking",
                provider,
                f"{name}: the HR key's session cannot be checked",
                "The service could not confirm that the HR session that entered the key is still"
                " signed in, so the key is held back and no server key is used in its place.",
                (Action("SIGN_IN_AGAIN", "Sign in again, then enter the key", "HR",
                        "the key shows as configured"), *test),
                tuple(evidence),
            )
        ]
    if status == "invalid":
        return [
            Problem(
                f"{prefix}_KEY_INVALID",
                "blocking",
                provider,
                f"{name}: the key is not in the expected form",
                "The key the service would use is malformed; a malformed key never falls"
                " through to another source.",
                (Action("ENTER_KEY", "Replace the key", "HR", "the key shows as configured")
                 if hr_editable else _owner("Ask the key owner to replace the server key",
                                            "the key shows as configured"), *test),
                tuple(evidence),
            )
        ]
    # missing: an HR key ended or none was entered, and no server key is set.
    if hr_editable:
        return [
            Problem(
                f"{prefix}_KEY_MISSING",
                "blocking",
                provider,
                f"{name}: no key is available",
                "No HR session key is held (it may have ended with its session) and no server key"
                " is set.",
                (Action("ENTER_KEY", "Enter a key for your session", "HR",
                        "the key shows as configured"), *test),
                tuple(evidence),
            )
        ]
    return [
        Problem(
            f"{prefix}_SERVER_KEY_UNAVAILABLE",
            "blocking",
            provider,
            f"{name}: the server key is unavailable",
            "This deployment does not accept HR keys and the server key is not set. Only its"
            " owner can restore it; afterwards Test connection revalidates it.",
            (_owner("Request the server key be restored", "the key shows as configured"), *test),
            tuple(evidence),
        )
    ]


def _claude(
    claude: Mapping[str, Any],
    listing: Mapping[str, Any] | None,
    listing_error: str | None,
    claude_profile: str | None,
    now: datetime,
) -> tuple[list[Problem], dict[str, Any]]:
    problems: list[Problem] = []
    ledger = claude.get("ledger")
    recon = claude.get("reconciliation")
    expiries: dict[str, Any] = {}
    if not isinstance(ledger, Mapping) or not isinstance(recon, Mapping):
        problems.append(
            Problem(
                "CLAUDE_LEDGER_UNREADABLE",
                "blocking",
                "anthropic",
                "Claude: the spending ledger cannot be read",
                "Claude answers only with a readable, healthy ledger (fail closed). The ledger is"
                " an operator store; HR cannot create or repair it.",
                (_owner("Request ledger recovery", "the ledger's figures appear on this page"),),
            )
        )
        return problems, expiries
    calls = _map(recon.get("calls"))
    expiries["claude_chat_deadline_at"] = recon.get("chat_deadline_at")
    expiries["claude_paid_deadline_at"] = recon.get("paid_deadline_at")

    blockers: list[str] = []
    if ledger.get("breaker_open"):
        blockers.append("CLAUDE_BREAKER_OPEN")
        problems.append(
            Problem(
                "CLAUDE_BREAKER_OPEN",
                "blocking",
                "anthropic",
                "Claude: the spending breaker is open",
                "The ledger stopped paid calls because an amount could not be accounted for"
                f" ({ledger.get('breaker_code') or 'no code'}). D-110 R8: HR cannot reset it."
                " The owner reconciles with the Console figure and resets it with the script"
                " once the cause is understood.",
                (_owner("Request owner reconciliation and breaker reset",
                        "the breaker shows closed"),),
                (("Breaker code", str(ledger.get("breaker_code") or "none")),),
            )
        )
    quarantined = _int(calls.get("quarantined"))
    if quarantined:
        blockers.append("CLAUDE_QUARANTINED_CALLS")
        problems.append(
            Problem(
                "CLAUDE_QUARANTINED_CALLS",
                "blocking",
                "anthropic",
                f"Claude: {quarantined} paid call(s) quarantined",
                "A reply did not match the pinned model or route, so its charge is uncertain. It"
                " is never marked settled automatically; an owner reconciliation must cover it"
                " (D-110 R10).",
                (_owner("Request an owner reconciliation", "no call is quarantined"),),
                (("Quarantined calls", str(quarantined)),),
            )
        )
    unverified = _int(calls.get("unverified"))
    if unverified:
        blockers.append("CLAUDE_UNVERIFIED_CALLS")
        problems.append(
            Problem(
                "CLAUDE_UNVERIFIED_CALLS",
                "blocking",
                "anthropic",
                f"Claude: {unverified} closed call(s) not yet verified",
                "Closed calls are checked in-band against the reply that was recorded. Test"
                " connection runs that check for free (no inference, no case data); a call that"
                " fails it is quarantined instead.",
                (Action("TEST_CONNECTION", "Verify calls with Test connection", "HR",
                        "no call is unverified", profile_id=claude_profile),),
                (("Unverified calls", str(unverified)),),
            )
        )
    open_calls = _int(calls.get("open"))
    if open_calls:
        blockers.append("CLAUDE_OPEN_CALLS")
        problems.append(
            Problem(
                "CLAUDE_OPEN_CALLS",
                "warning",
                "anthropic",
                f"Claude: {open_calls} paid call(s) still open",
                "A call is open while its reply is being written; its reservation is held until"
                " it settles. Reconciliation waits for open calls. A call that stays open after"
                f" {OPEN_CALL_PATIENCE_SECONDS // 60} minutes needs the owner: HR never recovers"
                " expired calls (D-110 R4).",
                (Action("WAIT", "Wait for the call to settle, then check again", "NONE",
                        "no call is open"),
                 _owner("Request recovery of a stuck call", "no call is open")),
                (("Open calls", str(open_calls)),
                 ("Reserved", _usd(recon.get("open_reserved_micro_usd")))),
            )
        )

    runs: list[Mapping[str, Any]] = []
    if listing_error is not None:
        problems.append(
            Problem(
                "CLAUDE_RECONCILIATION_UNAVAILABLE",
                "blocking",
                "anthropic",
                "Claude: reconciliation records cannot be read",
                f"The reconciliation run store refused the read ({listing_error}).",
                (_owner("Request the run store be checked", "reconciliation runs are listed"),),
                (("Code", listing_error),),
            )
        )
        blockers.append("CLAUDE_RECONCILIATION_UNAVAILABLE")
    elif listing is not None:
        runs = [run for run in listing.get("runs") or [] if isinstance(run, Mapping)]
        if not listing.get("prerequisite_recorded"):
            blockers.append("CLAUDE_RECONCILIATION_PREREQUISITE")
            problems.append(
                Problem(
                    "CLAUDE_RECONCILIATION_PREREQUISITE",
                    "blocking",
                    "anthropic",
                    "Claude: HR reconciliation is not yet enabled by the owner",
                    "D-110 R13 (P1): the owner must first record that every earlier copy of the"
                    " ledger script and every earlier launcher is retired"
                    " (budget_ledger.py attest-legacy-retired). Until then only the owner can"
                    " reconcile, with the script.",
                    (_owner("Request the P1 attestation (or an owner CLI reconciliation)",
                            "HR reconciliation is enabled"),),
                )
            )
        if listing.get("marker_run_id") and not any(
            run.get("run_id") == listing.get("marker_run_id") and run.get("status") == "requested"
            for run in runs
        ):
            blockers.append("CLAUDE_RECONCILIATION_MARKER")
            problems.append(
                Problem(
                    "CLAUDE_RECONCILIATION_MARKER",
                    "blocking",
                    "anthropic",
                    "Claude: a reconciliation intent marker is left on the ledger",
                    "An earlier reconciliation left its durable intent marker"
                    + (" and it was overridden by the owner" if listing.get("marker_overridden")
                       else "")
                    + ". Reconciliation refuses while it exists; only the owner clears it.",
                    (_owner("Request the marker be cleared", "no marker is reported"),),
                    (("Run", str(listing.get("marker_run_id"))),),
                )
            )
        for run in runs:
            status = run.get("status")
            if status == "requested":
                after = _parse(run.get("resolvable_after"))
                ready = after is not None and after <= now
                blockers.append("CLAUDE_RECONCILIATION_RUN_PENDING")
                problems.append(
                    Problem(
                        "CLAUDE_RECONCILIATION_RUN_PENDING",
                        "blocking",
                        "anthropic",
                        "Claude: a reconciliation did not finish",
                        "The run's intent was recorded but its outcome was not. Resolve decides"
                        " it from the ledger's own events: applied only when commit and"
                        " attribution are proven, failed only when no commit is proven,"
                        " otherwise unresolved for the owner. The ledger is never written.",
                        (Action("RESOLVE_RUN", "Resolve the run", "HR",
                                "the run shows applied or failed", run_id=str(run.get("run_id")))
                         if ready else
                         Action("WAIT", "Wait until the run can be resolved", "NONE",
                                "Resolve becomes available"),),
                        (("Run", str(run.get("run_id"))),
                         ("Intent at", str(run.get("intent_at"))),
                         ("Resolvable after", str(run.get("resolvable_after")))),
                    )
                )
            elif status == "unresolved" and not run.get("acknowledged_state"):
                blockers.append("CLAUDE_RECONCILIATION_RUN_UNRESOLVED")
                problems.append(
                    Problem(
                        "CLAUDE_RECONCILIATION_RUN_UNRESOLVED",
                        "blocking",
                        "anthropic",
                        "Claude: a reconciliation run is unresolved",
                        "Neither commit nor non-commit could be proven from the ledger, so the"
                        " run is left for the owner (D-110 R9). The owner's acknowledgement"
                        " never marks it applied and never changes the ledger.",
                        (_owner("Request owner acknowledgement", "the run is acknowledged"),),
                        (("Run", str(run.get("run_id"))),
                         ("Reason", str(run.get("reason") or "none"))),
                    )
                )

    reconcile_blockers = tuple(dict.fromkeys(blockers))
    reconciled_at = recon.get("reconciled_at")
    reconcile = Action(
        "RECONCILE",
        "Reconcile with the Anthropic Console figure",
        "HR",
        "the chat and paid windows show new deadlines",
        blocked_by=reconcile_blockers,
    )
    evidence = (
        ("Last reconciled", str(reconciled_at or "never")),
        ("Chat allowed until", str(recon.get("chat_deadline_at") or "not set")),
        ("Paid operations allowed until", str(recon.get("paid_deadline_at") or "not set")),
    )
    if reconciled_at is None:
        problems.append(
            Problem(
                "CLAUDE_NEVER_RECONCILED",
                "blocking",
                "anthropic",
                "Claude: the ledger was never reconciled",
                "The first reconciliation sets the opening usage and is the owner's step.",
                (_owner("Request the owner's first reconciliation", "a reconciliation time"
                        " appears"),),
                evidence,
            )
        )
    elif recon.get("chat_fresh") is False:
        problems.append(
            Problem(
                "CLAUDE_CHAT_WINDOW_EXPIRED",
                "blocking",
                "anthropic",
                "Claude: the 7-day chat window has expired",
                "Claude answers only while the ledger was reconciled within 7 days. A successful"
                " reconciliation renews it (and the 24-hour paid window); nothing else does.",
                (reconcile,),
                evidence,
            )
        )
    else:
        if recon.get("paid_fresh") is False:
            problems.append(
                Problem(
                    "CLAUDE_PAID_WINDOW_EXPIRED",
                    "warning",
                    "anthropic",
                    "Claude: the 24-hour paid-operation window has expired",
                    "Chat still works, but a paid qualification or an activation needs a"
                    " reconciliation within 24 hours. Reconciling renews both windows.",
                    (reconcile,),
                    evidence,
                )
            )
        deadline = _parse(recon.get("chat_deadline_at"))
        if deadline is not None and 0 <= (deadline - now).total_seconds() <= DUE_SOON_SECONDS:
            problems.append(
                Problem(
                    "CLAUDE_RECONCILIATION_DUE_SOON",
                    "warning",
                    "anthropic",
                    "Claude: reconciliation is due within 24 hours",
                    "When the 7-day chat window ends, Claude stops answering until the ledger is"
                    " reconciled again.",
                    (reconcile,),
                    evidence,
                )
            )

    daily = claude.get("daily")
    if isinstance(daily, Mapping) and _int(daily.get("remaining_micro_usd")) <= 0:
        problems.append(
            Problem(
                "CLAUDE_DAILY_LIMIT_REACHED",
                "blocking",
                "anthropic",
                "Claude: today's spending limit is used up",
                "The HR daily limit stops paid calls until the next reset. HR may raise it within"
                " its permitted range (D-102); the lifetime ledger cap still applies.",
                (Action("EDIT_DAILY_LIMIT", "Review the daily limit", "HR",
                        "today's remaining amount is above zero"),
                 Action("WAIT", "Or wait for the daily reset", "NONE", "the reset has passed")),
                (("Daily limit", _usd(daily.get("cap_micro_usd"))),
                 ("Next reset", str(claude.get("next_reset_at")))),
            )
        )
    if _int(ledger.get("headroom_micro_usd")) <= 0:
        cap = _int(ledger.get("cap_micro_usd"))
        ceiling = _int(claude.get("lifetime_ceiling_micro_usd"))
        raisable = cap < ceiling
        problems.append(
            Problem(
                "CLAUDE_LIFETIME_LIMIT_REACHED" if raisable else "CLAUDE_LIFETIME_CEILING_REACHED",
                "blocking",
                "anthropic",
                "Claude: the lifetime spending cap is reached",
                "Committed spend has reached the ledger cap. "
                + ("HR may raise the cap up to the ceiling with a typed confirmation."
                   if raisable else
                   "The cap is already at the ceiling (the lower of US$30.00 and the confirmed"
                   " workspace limit); only a new owner decision can change that."),
                (Action("EDIT_LIFETIME_LIMIT", "Review the lifetime cap", "HR",
                        "headroom is above zero"),)
                if raisable
                else (_owner("Request an owner decision on the ceiling", "headroom is above"
                             " zero"),),
                (("Cap", _usd(cap)), ("Ceiling", _usd(ceiling)),
                 ("Committed", _usd(ledger.get("committed_micro_usd")))),
            )
        )
    credential = claude.get("credential")
    if isinstance(credential, Mapping):
        problems.extend(_credential("anthropic", "Claude", credential, now, claude_profile))
        if isinstance(credential.get("expires_at"), int | float):
            expiries["claude_hr_key_ends_at"] = datetime.fromtimestamp(
                credential["expires_at"], UTC
            ).isoformat()
    expiries["claude_daily_reset_at"] = claude.get("next_reset_at")
    return problems, expiries


def _gpt_oss(budget: Mapping[str, Any], profile_id: str | None, now: datetime) -> list[Problem]:
    problems: list[Problem] = []
    ledger = budget.get("ledger")
    if isinstance(ledger, Mapping) and ledger.get("breaker_open"):
        problems.append(
            Problem(
                "GPT_OSS_BREAKER_OPEN",
                "blocking",
                "openrouter",
                "GPT-OSS: the spending breaker is open",
                f"The ledger stopped paid calls ({ledger.get('breaker_code') or 'no code'}). The"
                " operator reconciles and resets it with the script; HR cannot.",
                (_owner("Request operator reconciliation", "the breaker shows closed"),),
                (("Breaker code", str(ledger.get("breaker_code") or "none")),),
            )
        )
    daily = budget.get("daily")
    if isinstance(daily, Mapping) and _int(daily.get("remaining_micro_usd")) <= 0:
        problems.append(
            Problem(
                "GPT_OSS_DAILY_LIMIT_REACHED",
                "blocking",
                "openrouter",
                "GPT-OSS: today's spending limit is used up",
                "HR may raise the daily limit within its permitted range, or wait for the reset.",
                (Action("EDIT_DAILY_LIMIT", "Review the daily limit", "HR",
                        "today's remaining amount is above zero"),),
                (("Next reset", str(budget.get("next_reset_at"))),),
            )
        )
    provider = budget.get("provider")
    if isinstance(provider, Mapping) and provider.get("passed") is False:
        problems.append(
            Problem(
                "GPT_OSS_PROVIDER_CHECK_FAILED",
                "warning",
                "openrouter",
                "GPT-OSS: the provider's key check did not pass",
                "The free preflight (the key's limit and usage) failed at its last check.",
                (Action("TEST_CONNECTION", "Test connection", "HR", "the preflight passes",
                        profile_id=profile_id),),
                (("Checked at", str(provider.get("checked_at"))),),
            )
        )
    credential = budget.get("credential")
    if isinstance(credential, Mapping):
        problems.extend(_credential("openrouter", "GPT-OSS", credential, now, profile_id))
    return problems


def _models(overview: Mapping[str, Any]) -> list[Problem]:
    problems: list[Problem] = []
    active = _map(overview.get("active"))
    profiles = [p for p in overview.get("profiles") or [] if isinstance(p, Mapping)]
    by_id = {str(p.get("profile_id")): p for p in profiles}
    running = overview.get("running")
    if active.get("unavailable"):
        candidates = [
            p for p in profiles
            if p.get("eligible_qualification") and not p.get("activation_blockers")
        ]
        actions: list[Action] = [
            Action("ACTIVATE", f"Activate {c.get('display_name')}", "HR",
                   "a model is active", profile_id=str(c.get("profile_id")))
            for c in candidates[:3]
        ]
        if overview.get("last_good"):
            actions.append(Action("ROLLBACK", "Roll back to the last good model", "HR",
                                  "a model is active"))
        if not actions:
            actions.append(Action("QUALIFY", "Test connection, then run a qualification", "HR",
                                  "a configuration becomes eligible to activate"))
        problems.append(
            Problem(
                "MODEL_UNAVAILABLE",
                "blocking",
                "service",
                "No model is answering (AI unavailable)",
                "The stored active model stopped being usable (for example its qualification is"
                " out of date after a code change), so the chat gives labelled case-data guidance"
                " only. Nothing switches model automatically.",
                tuple(actions),
                (("Reverted", str(active.get("reverted") or "no")),),
            )
        )
    if active.get("config_changed"):
        problems.append(
            Problem(
                "MODEL_CONFIG_CHANGED",
                "warning",
                "service",
                "The active model's configuration changed since activation",
                "Its settings no longer match the qualified configuration; requalify before"
                " relying on it.",
                (Action("QUALIFY", "Run a qualification", "HR", "a current pass is recorded",
                        profile_id=str(active.get("profile_id"))),),
            )
        )
    for profile_id, profile in by_id.items():
        qualification = _map(profile.get("qualification"))
        is_active = profile_id == active.get("profile_id")
        if not qualification or profile.get("status") != "selectable":
            continue
        if running and _map(running).get("profile_id") == profile_id:
            continue
        name = str(profile.get("display_name") or profile_id)
        diagnosis = _map(qualification.get("diagnosis"))
        if qualification.get("status") == "passed" and qualification.get("current") is False:
            problems.append(
                Problem(
                    "QUALIFICATION_OUT_OF_DATE",
                    "blocking" if is_active else "info",
                    _provider_of(profile),
                    f"{name}: its qualification is out of date",
                    "The qualification was for different code or configuration (the"
                    " qualification basis moved). A new run is needed before activation; paid"
                    " runs ask for confirmation and stay within the spending limits.",
                    (Action("TEST_CONNECTION", "Test connection", "HR", "Test connection passes",
                            profile_id=profile_id),
                     Action("QUALIFY", "Run a new qualification", "HR",
                            "the qualification shows current", profile_id=profile_id)),
                    (("Finished at", str(qualification.get("finished_at"))),),
                )
            )
        elif qualification.get("status") not in {"passed", "running"} and diagnosis.get(
            "category"
        ) not in {None, "passed", "running", "cancelled"}:
            escalation = str(diagnosis.get("action") or "")
            act: Action
            if escalation.startswith("ESCALATE"):
                act = _owner("Request help from the responsible owner", "a later run passes")
            elif escalation == "TEST_CONNECTION":
                act = Action("TEST_CONNECTION", "Test connection", "HR", "Test connection passes",
                             profile_id=profile_id)
            elif escalation == "REVIEW_SPENDING":
                act = Action("EDIT_DAILY_LIMIT", "Review spending limits", "HR",
                             "the paid estimate fits the limits")
            else:
                act = Action("QUALIFY", "Run the qualification again", "HR", "a later run passes",
                             profile_id=profile_id)
            problems.append(
                Problem(
                    "QUALIFICATION_FAILED",
                    "warning" if is_active else "info",
                    _provider_of(profile),
                    f"{name}: the latest qualification did not pass",
                    f"Category: {diagnosis.get('category')}; cause {diagnosis.get('cause')}.",
                    (act,),
                    (("Run", str(qualification.get("qualification_id"))),
                     ("Code", str(qualification.get("code") or "none"))),
                )
            )
        test = _map(profile.get("connection_test"))
        if is_active and test and test.get("outcome") not in {None, "passed"}:
            problems.append(
                Problem(
                    "CONNECTION_TEST_FAILED",
                    "warning",
                    _provider_of(profile),
                    f"{name}: the last connection test failed",
                    "The model may be temporarily unavailable. Test again once the provider or"
                    " local model is back; activation and rollback stay available.",
                    (Action("TEST_CONNECTION", "Test connection again", "HR",
                            "Test connection passes", profile_id=profile_id),),
                    (("Tested at", str(test.get("at"))), ("Code", str(test.get("code") or "none"))),
                )
            )
    return problems


def _provider_of(profile: Mapping[str, Any]) -> Literal["anthropic", "openrouter", "local"]:
    deployment = str(profile.get("deployment") or "")
    if deployment == "anthropic":
        return "anthropic"
    if deployment == "openrouter":
        return "openrouter"
    return "local"


def _profile_for(overview: Mapping[str, Any], deployment: str) -> str | None:
    profiles = [p for p in overview.get("profiles") or [] if isinstance(p, Mapping)]
    active = _map(overview.get("active")).get("profile_id")
    matching = [p for p in profiles if p.get("deployment") == deployment]
    for profile in matching:
        if profile.get("profile_id") == active:
            return str(active)
    return str(matching[0]["profile_id"]) if matching else None


_ORDER = {"blocking": 0, "warning": 1, "info": 2}


def diagnose(
    overview: Mapping[str, Any],
    *,
    listing: Mapping[str, Any] | None,
    listing_error: str | None,
    now: datetime,
    hr_allowed: bool,
) -> dict[str, Any]:
    """Every current problem, worst first, with its permitted actions and separate expiries."""

    problems = _models(overview)
    expiries: dict[str, Any] = {}
    budget = _map(overview.get("budget"))
    claude = budget.get("claude")
    setup = _map(overview.get("anthropic_setup"))
    claude_profile = _profile_for(overview, "anthropic")
    if setup.get("enabled") and setup.get("readiness"):
        problems.append(
            Problem(
                "CLAUDE_SETUP_NOT_READY",
                "blocking",
                "anthropic",
                "Claude: the provider setup is not ready",
                f"The server's readiness check reports {setup.get('readiness')}.",
                (Action("ENTER_KEY", "Review the Anthropic setup", "HR",
                        "the setup shows ready"),),
                (("Readiness", str(setup.get("readiness"))),),
            )
        )
    if isinstance(claude, Mapping) and claude.get("configured"):
        found, expiries = _claude(claude, listing, listing_error, claude_profile, now)
        problems.extend(found)
    if budget.get("configured"):
        problems.extend(_gpt_oss(budget, _profile_for(overview, "openrouter"), now))
        credential = _map(budget.get("credential"))
        if isinstance(credential.get("expires_at"), int | float):
            expiries["gpt_oss_hr_key_ends_at"] = datetime.fromtimestamp(
                credential["expires_at"], UTC
            ).isoformat()
    qualification_validity = []
    active_id = _map(overview.get("active")).get("profile_id")
    for profile in overview.get("profiles") or []:
        if not isinstance(profile, Mapping):
            continue
        qualification = _map(profile.get("qualification"))
        if qualification:
            qualification_validity.append(
                {
                    "profile_id": profile.get("profile_id"),
                    "display_name": profile.get("display_name"),
                    "active": profile.get("profile_id") == active_id,
                    "status": qualification.get("status"),
                    "finished_at": qualification.get("finished_at"),
                    # A qualification has no time limit: it stays valid while the code basis and
                    # the configuration are the ones it ran on.
                    "current": qualification.get("current"),
                }
            )
    expiries["qualifications"] = qualification_validity
    problems.sort(key=lambda item: (_ORDER[item.severity], item.provider, item.code))
    return {
        "generated_at": now.isoformat(),
        "basis": overview.get("basis"),
        "healthy": not any(p.severity == "blocking" for p in problems),
        "problems": [problem.view(hr_allowed) for problem in problems],
        "expiries": expiries,
        # Which parts were fully diagnosed: a problem missing from a part that was not cannot
        # be taken as cleared (QG F4).
        "covered": sorted(_covered(overview, listing, listing_error)),
    }


def _covered(
    overview: Mapping[str, Any], listing: Mapping[str, Any] | None, listing_error: str | None
) -> set[str]:
    budget = _map(overview.get("budget"))
    claude = _map(budget.get("claude"))
    parts = {"MODEL", "QUALIFICATION", "CONNECTION"}
    if claude.get("configured") and isinstance(claude.get("ledger"), Mapping) and isinstance(
        claude.get("reconciliation"), Mapping
    ):
        parts.add("CLAUDE")
        if listing is not None and listing_error is None:
            parts.add("CLAUDE_RECONCILIATION")
    if budget.get("configured"):
        parts.add("GPT_OSS")
    return parts


def problem_covered(view: Mapping[str, Any], code: str) -> bool:
    """True when the diagnosis that produced ``view`` looked at the part ``code`` belongs to."""

    covered = set(view.get("covered") or [])
    if code.startswith("CLAUDE_RECONCILIATION") or code in {
        "CLAUDE_NEVER_RECONCILED",
    }:
        return "CLAUDE_RECONCILIATION" in covered and "CLAUDE" in covered
    for part in ("CLAUDE", "GPT_OSS"):
        if code.startswith(part + "_"):
            return part in covered
    return True


def present_codes(view: Mapping[str, Any]) -> set[str]:
    return {str(item.get("code")) for item in view.get("problems") or []}


def evidence_snapshot(view: Mapping[str, Any], code: str) -> list[dict[str, str]]:
    """The server's own evidence for one current problem (what an owner request carries)."""

    for item in view.get("problems") or []:
        if item.get("code") == code:
            return [dict(entry) for entry in item.get("evidence") or []]
    return []


def codes(items: Iterable[Mapping[str, Any]]) -> list[str]:
    return [str(item.get("code")) for item in items]
