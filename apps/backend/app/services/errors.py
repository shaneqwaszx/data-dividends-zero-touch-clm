"""Sanitized application errors raised after terminal workflow persistence."""

from uuid import UUID


class OnboardingInfrastructureError(RuntimeError):
    """Report a retrievable failed case without retaining the original exception."""

    def __init__(
        self,
        *,
        case_id: UUID,
        correlation_id: UUID,
        code: str,
        public_message: str,
    ) -> None:
        super().__init__(public_message)
        self.case_id = case_id
        self.correlation_id = correlation_id
        self.code = code
        self.public_message = public_message
