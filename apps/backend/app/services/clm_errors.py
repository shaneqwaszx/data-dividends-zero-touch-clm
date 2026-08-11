"""Safe Phase 05 CLM request and infrastructure errors."""

from uuid import UUID


class ClmRequestError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.public_message = message


class ClmInfrastructureError(Exception):
    def __init__(
        self,
        *,
        case_id: UUID,
        orchestration_id: UUID,
        correlation_id: UUID,
        code: str,
        message: str,
    ) -> None:
        super().__init__(code)
        self.case_id = case_id
        self.orchestration_id = orchestration_id
        self.correlation_id = correlation_id
        self.code = code
        self.public_message = message
