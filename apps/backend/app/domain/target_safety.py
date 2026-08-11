"""Provider-neutral safety bounds for target-returned text retained by the POC."""

from typing import Annotated

from pydantic import StringConstraints

SafeTargetIdentifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=96,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
SafeTargetStatus = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Z][A-Z0-9_:-]*$",
    ),
]
SafeTargetErrorCode = SafeTargetStatus
SafeTargetMessage = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=200,
        pattern=r"^[^\x00-\x1f\x7f]+$",
    ),
]
