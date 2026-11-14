"""The hosted ASGI entry point: ``assistant_hosting.app:app``.

The settings are checked before ``ai_assistant.main`` is imported, because that import opens
the stores and builds the service.
"""

from fastapi import FastAPI

from ai_assistant.config import AiAssistantSettings

from . import provider
from .harden import harden
from .profile import refusals


class HostedConfigurationError(SystemExit):
    def __init__(self, codes: list[str]) -> None:
        super().__init__("hosted configuration refused: " + ",".join(codes))


def build() -> FastAPI:
    settings = AiAssistantSettings()
    codes = refusals(settings)
    if codes:
        raise HostedConfigurationError(codes)
    # R2.2: before the service is built, so a restored Claude activation sees the same
    # hosted deployment as every later call.
    provider.install(settings)
    from ai_assistant.main import app as service

    return harden(service, settings)


app = build()
