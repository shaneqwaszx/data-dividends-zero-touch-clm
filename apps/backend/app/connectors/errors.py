"""Safe connector-boundary exception types."""


class ConnectorError(RuntimeError):
    """Base error connectors may use after sanitizing implementation failures."""
