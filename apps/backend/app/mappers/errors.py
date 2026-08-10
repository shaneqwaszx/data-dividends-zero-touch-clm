"""Explicit errors for violated mapper preconditions."""


class MappingError(ValueError):
    """Raised when canonical input cannot safely produce a target request."""
