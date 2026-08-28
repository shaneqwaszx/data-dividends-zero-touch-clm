"""Safe connector-boundary exception types."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PublicConnectorError:
    """Trusted public representation separated from private exception context."""

    code: str
    message: str


class ConnectorError(RuntimeError):
    """Base error with fixed public fields and optional private diagnostic context."""

    code: ClassVar[str] = "CONNECTOR_FAILURE"
    public_message: ClassVar[str] = "An external service request could not be completed."

    def __init__(self, internal_context: object | None = None) -> None:
        self._internal_context = internal_context
        super().__init__(self.public_message)


class AcraConfigurationError(ConnectorError):
    """Required ACRA sandbox configuration or authorization is unavailable."""

    code = "ACRA_CONFIGURATION_ERROR"
    public_message = "The ACRA sandbox connector is not configured for authorized use."


class AcraAuthenticationError(ConnectorError):
    """ACRA rejected or could not authorize the request."""

    code = "ACRA_AUTHENTICATION_ERROR"
    public_message = "The ACRA registry request could not be authorized."


class AcraTimeoutError(ConnectorError):
    """ACRA did not respond inside the configured timeout."""

    code = "ACRA_TIMEOUT"
    public_message = "The ACRA registry request timed out."


class AcraServiceUnavailableError(ConnectorError):
    """ACRA or its network path is temporarily unavailable."""

    code = "ACRA_SERVICE_UNAVAILABLE"
    public_message = "The ACRA registry service is unavailable."


class AcraMalformedResponseError(ConnectorError):
    """ACRA returned a response that cannot be safely interpreted."""

    code = "ACRA_MALFORMED_RESPONSE"
    public_message = "The ACRA registry returned an unexpected response."


class AcraUnexpectedConnectorError(ConnectorError):
    """An unexpected transport implementation failure was sanitized."""

    code = "ACRA_CONNECTOR_UNEXPECTED_FAILURE"
    public_message = "The ACRA registry request could not be completed."


class AcraResponseInvalidError(ConnectorError):
    """The provider result failed the strict source DTO boundary."""

    code = "ACRA_RESPONSE_INVALID"
    public_message = "Corporate registry response could not be validated safely."


class AcraResponseIdentityMismatchError(ConnectorError):
    """The returned entity did not bind to the requested identifier."""

    code = "ACRA_RESPONSE_IDENTITY_MISMATCH"
    public_message = "Corporate registry response did not match the requested entity."


class AcraMappingError(ConnectorError):
    """Validated ACRA source data could not be mapped to the canonical entity."""

    code = "ACRA_SOURCE_MAPPING_FAILED"
    public_message = "Registry data could not be mapped safely."


class AcraUnexpectedMappingError(ConnectorError):
    """Unexpected mapping implementation errors are projected safely."""

    code = "ACRA_MAPPING_UNEXPECTED_FAILURE"
    public_message = "Registry data could not be mapped safely."


_TRUSTED_PUBLIC_ERRORS: tuple[
    tuple[type[ConnectorError], PublicConnectorError], ...
] = (
    (
        AcraConfigurationError,
        PublicConnectorError(
            code="ACRA_CONFIGURATION_ERROR",
            message="The ACRA sandbox connector is not configured for authorized use.",
        ),
    ),
    (
        AcraAuthenticationError,
        PublicConnectorError(
            code="ACRA_AUTHENTICATION_ERROR",
            message="The ACRA registry request could not be authorized.",
        ),
    ),
    (
        AcraTimeoutError,
        PublicConnectorError(
            code="ACRA_TIMEOUT",
            message="The ACRA registry request timed out.",
        ),
    ),
    (
        AcraServiceUnavailableError,
        PublicConnectorError(
            code="ACRA_SERVICE_UNAVAILABLE",
            message="The ACRA registry service is unavailable.",
        ),
    ),
    (
        AcraMalformedResponseError,
        PublicConnectorError(
            code="ACRA_MALFORMED_RESPONSE",
            message="The ACRA registry returned an unexpected response.",
        ),
    ),
    (
        AcraUnexpectedConnectorError,
        PublicConnectorError(
            code="ACRA_CONNECTOR_UNEXPECTED_FAILURE",
            message="The ACRA registry request could not be completed.",
        ),
    ),
    (
        AcraResponseInvalidError,
        PublicConnectorError(
            code="ACRA_RESPONSE_INVALID",
            message="Corporate registry response could not be validated safely.",
        ),
    ),
    (
        AcraResponseIdentityMismatchError,
        PublicConnectorError(
            code="ACRA_RESPONSE_IDENTITY_MISMATCH",
            message="Corporate registry response did not match the requested entity.",
        ),
    ),
    (
        AcraMappingError,
        PublicConnectorError(
            code="ACRA_SOURCE_MAPPING_FAILED",
            message="Registry data could not be mapped safely.",
        ),
    ),
    (
        AcraUnexpectedMappingError,
        PublicConnectorError(
            code="ACRA_MAPPING_UNEXPECTED_FAILURE",
            message="Registry data could not be mapped safely.",
        ),
    ),
)


def public_connector_error(error: ConnectorError) -> PublicConnectorError:
    """Return fixed public fields for trusted error families only."""

    for error_type, public_error in _TRUSTED_PUBLIC_ERRORS:
        if isinstance(error, error_type):
            return public_error
    return PublicConnectorError(
        code="CONNECTOR_FAILURE",
        message="An external service request could not be completed.",
    )
