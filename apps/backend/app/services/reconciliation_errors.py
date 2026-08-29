"""Safe request and infrastructure errors for reconciliation."""


class ReconciliationRequestError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message


class ReconciliationInfrastructureError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message
