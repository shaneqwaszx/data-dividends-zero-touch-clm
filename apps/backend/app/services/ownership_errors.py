"""Trusted request and terminal errors for the ownership-analysis boundary."""

from uuid import UUID


class OwnershipRequestError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.public_message = message


class OwnershipInfrastructureError(Exception):
    def __init__(
        self,
        *,
        case_id: UUID,
        analysis_id: UUID,
        correlation_id: UUID,
        code: str,
        message: str,
    ) -> None:
        super().__init__(code)
        self.case_id = case_id
        self.analysis_id = analysis_id
        self.correlation_id = correlation_id
        self.code = code
        self.public_message = message
