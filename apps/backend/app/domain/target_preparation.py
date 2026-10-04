"""Safe, case-scoped request-preview models for GoldTier target preparation."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TargetValueProvenance(StrEnum):
    CANONICAL_EVIDENCE = "CANONICAL_EVIDENCE"
    REGISTRY = "REGISTRY"
    DOCUMENT = "DOCUMENT"
    ENTITY_RESOLUTION = "ENTITY_RESOLUTION"
    POLICY = "POLICY"
    USER_INPUT = "USER_INPUT"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    SPONSOR_SUPPLIED = "SPONSOR_SUPPLIED"
    SANDBOX_OBSERVED = "SANDBOX_OBSERVED"
    INDUSTRY_PRACTICE = "INDUSTRY_PRACTICE"


class TargetFieldAuthority(StrEnum):
    CANONICAL_EVIDENCE = "CANONICAL_EVIDENCE"
    SPONSOR_SUPPLIED = "SPONSOR_SUPPLIED"
    SPONSOR_DOCUMENTED = "SPONSOR_DOCUMENTED"
    SPONSOR_EXAMPLE = "SPONSOR_EXAMPLE"
    SANDBOX_OBSERVED = "SANDBOX_OBSERVED"
    USER_AUTHORIZED_POC = "USER_AUTHORIZED_POC"
    PROJECT_DERIVED_POC = "PROJECT_DERIVED_POC"
    PROJECT_DEFINED_PROVISIONAL = "PROJECT_DEFINED_PROVISIONAL"
    INDUSTRY_PRACTICE = "INDUSTRY_PRACTICE"
    TBD_SPONSOR = "TBD_SPONSOR"
    SANDBOX_TEST_ONLY = "SANDBOX_TEST_ONLY"


class TargetFieldValidation(StrEnum):
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"


class GoldTierPreviewField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_field: Annotated[str, Field(min_length=1, max_length=96)]
    value: Annotated[str | None, Field(default=None, max_length=240)]
    provenance: TargetValueProvenance
    authority: TargetFieldAuthority
    required: bool
    missing: bool
    validation: TargetFieldValidation

    @model_validator(mode="after")
    def validation_matches_presence(self) -> GoldTierPreviewField:
        if self.missing != (self.validation == TargetFieldValidation.MISSING):
            raise ValueError("preview missing flag contradicts validation")
        if self.missing and self.value is not None:
            raise ValueError("missing preview field cannot expose a value")
        return self


class GoldTierOperationPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["SEARCH", "SHELL", "POLICY", "AMEND", "READBACK"]
    fields: tuple[GoldTierPreviewField, ...] = Field(max_length=32)
    missing_fields: tuple[Annotated[str, Field(min_length=1, max_length=96)], ...] = Field(
        max_length=32
    )
    validation: TargetFieldValidation


class GoldTierRequestPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: Literal["MOCK", "SANDBOX"]
    policy_version: int = Field(ge=0)
    operations: tuple[GoldTierOperationPreview, ...] = Field(min_length=1, max_length=5)
    dispatch_ready: bool
