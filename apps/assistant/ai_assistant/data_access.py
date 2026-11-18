# Data access policy (D-104): which cases each class of model may receive, as an explicit,
# audited HR setting on AI Models ("Restrict AI to verified synthetic cases").
#
#     openrouter, anthropic   GPT-OSS through OpenRouter and Claude through Anthropic. Always
#                             restricted to verified synthetic cases by their own code
#                             (remote_test.py, anthropic_runtime.py and the chat's D-094/D-095
#                             gate in main.py), whatever the stored policy says or whether it
#                             can be read. Locked: no HR setting can send real case data to
#                             them; that needs a separately approved external-data decision and
#                             deployment controls.
#     it_configured           a model IT configured on an endpoint that is not a literal
#                             loopback address. It is treated like the external models:
#                             restricted and locked, whatever the policy, with or without model
#                             management (only a model passed in by tests is exempt).
#     local_internal          a model on a literal loopback endpoint (D-093). Every authorised
#                             case unless HR restricts it (D-093 behaviour, unchanged); then it
#                             answers only cases that pass the same synthetic gate as the external
#                             models. A stored policy that cannot be read restricts it (fail
#                             closed).
#
# A restricted model is SyntheticOnlyModel: the chat applies the shared D-095 eligibility check
# (provenance, SHA-256 document digests, grounded values, viewer, knowledge, identifier screen
# and its single-use ticket) when D-095 mode is on (synthetic_eligibility.shared_mode), else the
# D-094 fixed-fixture boundary, and the model re-checks every call. Neither the policy nor this
# module relaxes either check. Comments, not docstrings: the D-094 boundary admits every word
# of every string constant in this package (scripts/build_synthetic_boundary.py), and the
# strings here add none.

from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import Any

from . import anthropic_runtime, privacy_boundary, remote_test, synthetic_eligibility
from .config import AiAssistantSettings, external_conversational
from .llm import ChatModel, LlmUnavailableError, ModelAnswer, Piece, is_local_model_url
from .model_admin_store import DataAccessPolicy
from .synthetic_boundary import check_messages

LOCAL_CLASS = "local_internal"
IT_CLASS = "it_configured"
LOCKED_CLASSES = ("openrouter", "anthropic", IT_CLASS)

LOCAL_NOTICES = anthropic_runtime.Notices(
    answered=(
        "Answered by the local model (data access policy: the approved synthetic test case only)."
    ),
    boundary=(
        "The local model is used only on the approved synthetic test case under the data access"
        " policy, so this answer comes straight from the case data."
    ),
    dev_answered="Answered by the local model (data access policy: verified synthetic case).",
    eligibility=(
        "The local model is used only on verified synthetic cases under the data access policy,"
        " so this answer comes straight from the case data."
    ),
)
IT_NOTICES = anthropic_runtime.Notices(
    answered=(
        "Answered by the model IT configured (data access policy: the approved synthetic test"
        " case only)."
    ),
    boundary=(
        "The model IT configured is not on a literal loopback address, so it is used only on the"
        " approved synthetic test case and this answer comes straight from the case data."
    ),
    dev_answered=(
        "Answered by the model IT configured (data access policy: verified synthetic case)."
    ),
    eligibility=(
        "The model IT configured is not on a literal loopback address, so it is used only on"
        " verified synthetic cases and this answer comes straight from the case data."
    ),
)
# The lead notices main.py shows as a policy refusal (never the generic "not available").
REFUSAL_NOTICES = (
    LOCAL_NOTICES.boundary,
    LOCAL_NOTICES.eligibility,
    IT_NOTICES.boundary,
    IT_NOTICES.eligibility,
)


def model_class(model: ChatModel | None, base_url: str | None) -> str | None:
    # The provider class of the model answers use (None: no model). Only a literal loopback
    # endpoint is local; any other endpoint IT configured is not.
    # D-142 R1 (P2-3): every wrapper stack is unwrapped to the model that is actually called:
    # the synthetic gate, the privacy boundary around an IT-configured model, and the
    # qualification watcher (model_qualification.WatchedModel), in any order or depth.
    from .model_qualification import WatchedModel  # deferred: it imports this module's peers

    wrappers = (SyntheticOnlyModel, privacy_boundary.BoundedModel, WatchedModel)
    for _ in range(8):
        if not isinstance(model, wrappers):
            break
        model = model.inner
    if model is None:
        return None
    if isinstance(model, remote_test.RemoteTestModel):
        return "openrouter"
    if isinstance(model, anthropic_runtime.ClaudeTestModel):
        return "anthropic"
    return LOCAL_CLASS if is_local_model_url(base_url or "") else IT_CLASS


def local_restricted(policy: DataAccessPolicy | None) -> bool:
    # None (the stored policy could not be read) restricts: fail closed.
    return policy is None or policy.local_restricted


def verification_mode(settings: AiAssistantSettings, provider_class: str | None) -> str:
    # The shared synthetic check a restricted model's questions pass: D-095 provenance, or the
    # D-094 fixed fixture when D-095 mode is off. GPT-OSS keeps its OpenRouter-ready mode.
    if provider_class == "openrouter":
        development = synthetic_eligibility.mode(settings)
    elif provider_class == "anthropic":
        # D-107: Claude's own mode (HR enablement or the D-095 interlocks).
        from .anthropic_runtime import synthetic_mode

        development = synthetic_mode(settings)
    else:
        development = synthetic_eligibility.shared_mode(settings)
    return "D-095" if development else "D-094"


class SyntheticOnlyModel:
    # A local or IT-configured model under the policy's restriction. The chat gates it like the
    # external models (requires_synthetic_boundary): the case passes the shared synthetic gate
    # first, or nothing is sent. Every call is decided again here for its exact messages (the
    # D-095 single-use ticket, or the D-094 text check), whoever the caller is, and there is no
    # warm-up (it would send case facts before any check).

    requires_synthetic_boundary = True

    def __init__(
        self, inner: ChatModel, settings: AiAssistantSettings, *, local: bool = True
    ) -> None:
        self.inner = inner
        self._settings = settings
        self.notices = LOCAL_NOTICES if local else IT_NOTICES

    @property
    def name(self) -> str:
        return self.inner.name

    def development_mode(self) -> bool:
        return synthetic_eligibility.shared_mode(self._settings)

    def _admit(self, messages: list[dict[str, str]]) -> None:
        ticket = synthetic_eligibility.admitted(messages)
        if ticket and (external_conversational(self._settings) or self.development_mode()):
            return
        if check_messages(messages) is not None:
            raise LlmUnavailableError("refused by the data access policy")

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self._admit(messages)
        return self.inner.complete(messages)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self._admit(messages)
        async with aclosing(self.inner.stream(messages)) as source:
            async for piece in source:
                yield piece

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None


def view(
    policy: DataAccessPolicy | None,
    *,
    managed: bool,
    remote_restricted: bool,
    settings: AiAssistantSettings,
    model: ChatModel | None,
    base_url: str | None,
) -> dict[str, Any]:
    # What the AI Models page shows: the effective server-side policy, never a wish. Without
    # model management (no state database) nothing is applied (D-093, unchanged), and the page
    # says so.
    # D-122: conversational answers reach every class on any case the user may read.
    open_access = external_conversational(settings)
    restricted = local_restricted(policy) and not open_access if managed else False
    remote_restricted = remote_restricted and not open_access
    active = model_class(model, base_url)
    if not managed:
        status = "not_managed"
    elif policy is None:
        status = "unavailable"
    elif policy.revision == 0:
        status = "default"
    else:
        status = "stored"
    return {
        "status": status,
        "revision": policy.revision if policy is not None else None,
        "changed_at": policy.changed_at if policy is not None else None,
        "classes": [
            {"provider_class": "openrouter", "restricted": not open_access, "locked": True},
            {"provider_class": "anthropic", "restricted": not open_access, "locked": True},
            {"provider_class": IT_CLASS, "restricted": remote_restricted, "locked": True},
            {
                "provider_class": LOCAL_CLASS,
                "restricted": restricted,
                "locked": not managed or open_access,
            },
        ],
        "active_class": active,
        "active_restricted": (active in ("openrouter", "anthropic") and not open_access)
        or (remote_restricted and active == IT_CLASS)
        or (active == LOCAL_CLASS and restricted),
        "verification": verification_mode(settings, active),
    }
