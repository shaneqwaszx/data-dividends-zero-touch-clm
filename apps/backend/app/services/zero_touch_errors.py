"""Safe application errors for the zero-touch boundary."""

from uuid import UUID


class ZeroTouchRequestError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message


class ZeroTouchInfrastructureError(Exception):
    def __init__(
        self,
        *,
        case_id: UUID,
        automation_id: UUID,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.case_id = case_id
        self.automation_id = automation_id
        self.code = code
        self.public_message = message
