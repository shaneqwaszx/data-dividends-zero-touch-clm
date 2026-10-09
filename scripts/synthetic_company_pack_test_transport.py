"""Test-server-only Marketplace transport guard; never a production fallback."""

from collections import Counter


class ForbiddenMarketplaceRequest(BaseException):
    """Escape connector Exception sanitization so a forbidden request fails immediately."""


class NoMarketplaceRequests:
    def __init__(self):
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append("TOKEN")
        raise ForbiddenMarketplaceRequest(
            "Seeded path attempted Marketplace token request"
        )

    def get(self, *args, **kwargs):
        self.calls.append("ENTITY_OR_SHAREHOLDERS")
        raise ForbiddenMarketplaceRequest(
            "Seeded path attempted Marketplace HTTP request"
        )

    def metadata(self):
        return {
            "calls": list(self.calls),
            "external_calls": 0,
            "marketplace_requests": dict(Counter(self.calls)),
        }
