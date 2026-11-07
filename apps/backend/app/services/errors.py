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


class TargetWritesDisabledError(RuntimeError):
    """The configured target refuses mutations; nothing was attempted or recorded."""

    public_message = "GoldTier Sandbox writes are disabled; no target mutation was attempted."


class TargetRegistryProvenanceError(RuntimeError):
    """The identity has no evidence from a source this target accepts."""

    public_message = (
        "This identity has no evidence from a source GoldTier Sandbox accepts, so no "
        "provider request was made."
    )


class TargetProviderContextMismatchError(RuntimeError):
    """Fail closed when an immutable submission meets incompatible target wiring."""

    code = "GT_PROVIDER_CONTEXT_MISMATCH"
    public_message = "Target provider context changed; submission cannot continue safely."

    def __init__(self) -> None:
        super().__init__(self.public_message)
