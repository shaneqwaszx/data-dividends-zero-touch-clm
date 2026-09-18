"""Authenticated typed policy catalogue HTTP contract."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.domain.access import AuthenticatedActor
from app.domain.policy import (
    PolicyCatalogue,
    PolicyClassification,
    PolicyEnforcement,
    PolicyRule,
    PolicyValue,
    PolicyValueType,
)
from app.persistence.errors import PersistenceUnavailableError
from app.services.admin_repository import (
    AdministrationAuditCapacityError,
    AdministrationConflictError,
)
from app.services.policy_management import (
    PolicyForbiddenError,
    PolicyManagementService,
    PolicyNotFoundError,
    PolicyValidationError,
)


class PolicyRuleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    policy_id: str
    category: str
    name: str
    description: str
    value: PolicyValue
    value_type: PolicyValueType
    default_value: PolicyValue
    minimum: str | int | None
    maximum: str | int | None
    allowed_values: tuple[str, ...]
    classifications: tuple[PolicyClassification, ...]
    enforcement: PolicyEnforcement
    version: int
    created_at: datetime
    updated_at: datetime
    updated_by: str

    @classmethod
    def from_domain(cls, rule: PolicyRule) -> PolicyRuleResponse:
        return cls.model_validate(rule)


class PolicyCatalogueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    catalogue_id: str
    version: int
    rules: tuple[PolicyRuleResponse, ...]
    created_at: datetime
    updated_at: datetime
    updated_by: str

    @classmethod
    def from_domain(cls, catalogue: PolicyCatalogue) -> PolicyCatalogueResponse:
        return cls(
            catalogue_id=catalogue.catalogue_id,
            version=catalogue.version,
            rules=tuple(PolicyRuleResponse.from_domain(rule) for rule in catalogue.rules),
            created_at=catalogue.created_at,
            updated_at=catalogue.updated_at,
            updated_by=catalogue.updated_by,
        )


class CreatePolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_catalogue_version: Annotated[int, Field(strict=True, ge=1)]
    policy_id: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]
    category: Annotated[str, Field(min_length=2, max_length=48)]
    name: Annotated[str, Field(min_length=2, max_length=80)]
    description: Annotated[str, Field(min_length=2, max_length=240)]
    value: PolicyValue


class UpdatePolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_catalogue_version: Annotated[int, Field(strict=True, ge=1)]
    expected_rule_version: Annotated[int, Field(strict=True, ge=1)]
    value: PolicyValue
    name: Annotated[str | None, Field(default=None, min_length=2, max_length=80)]
    description: Annotated[str | None, Field(default=None, min_length=2, max_length=240)]


class ResetPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_catalogue_version: Annotated[int, Field(strict=True, ge=1)]
    expected_rule_version: Annotated[int, Field(strict=True, ge=1)]
    confirmation: Literal["RESET_POLICY_DEFAULT"]


class ResetAllPoliciesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_catalogue_version: Annotated[int, Field(strict=True, ge=1)]
    confirmation: Literal["RESET_ALL_POLICY_DEFAULTS"]


def build_policy_router(service: PolicyManagementService) -> APIRouter:
    router = APIRouter(prefix="/api/policies", tags=["policies"])

    @router.get("", response_model=PolicyCatalogueResponse)
    def list_policies() -> PolicyCatalogueResponse:
        return _policy_call(lambda: PolicyCatalogueResponse.from_domain(service.catalogue()))

    @router.get("/{policy_id}", response_model=PolicyRuleResponse)
    def get_policy(policy_id: str) -> PolicyRuleResponse:
        return _policy_call(lambda: PolicyRuleResponse.from_domain(service.get(policy_id)))

    @router.post("", response_model=PolicyCatalogueResponse, status_code=status.HTTP_201_CREATED)
    def create_policy(body: CreatePolicyRequest, request: Request) -> PolicyCatalogueResponse:
        actor = _actor(request)
        return _policy_call(
            lambda: PolicyCatalogueResponse.from_domain(
                service.create_showcase(
                    actor,
                    expected_catalogue_version=body.expected_catalogue_version,
                    policy_id=body.policy_id,
                    category=body.category,
                    name=body.name,
                    description=body.description,
                    value=body.value,
                )
            )
        )

    @router.patch("/{policy_id}", response_model=PolicyCatalogueResponse)
    def update_policy(
        policy_id: str, body: UpdatePolicyRequest, request: Request
    ) -> PolicyCatalogueResponse:
        actor = _actor(request)
        return _policy_call(
            lambda: PolicyCatalogueResponse.from_domain(
                service.update(
                    actor,
                    policy_id,
                    expected_catalogue_version=body.expected_catalogue_version,
                    expected_rule_version=body.expected_rule_version,
                    value=body.value,
                    name=body.name,
                    description=body.description,
                )
            )
        )

    @router.post("/{policy_id}/reset", response_model=PolicyCatalogueResponse)
    def reset_policy(
        policy_id: str, body: ResetPolicyRequest, request: Request
    ) -> PolicyCatalogueResponse:
        actor = _actor(request)
        return _policy_call(
            lambda: PolicyCatalogueResponse.from_domain(
                service.reset_one(
                    actor,
                    policy_id,
                    expected_catalogue_version=body.expected_catalogue_version,
                    expected_rule_version=body.expected_rule_version,
                )
            )
        )

    @router.post("/reset", response_model=PolicyCatalogueResponse)
    def reset_all(body: ResetAllPoliciesRequest, request: Request) -> PolicyCatalogueResponse:
        actor = _actor(request)
        return _policy_call(
            lambda: PolicyCatalogueResponse.from_domain(
                service.reset_all(actor, expected_catalogue_version=body.expected_catalogue_version)
            )
        )

    return router


def _actor(request: Request) -> AuthenticatedActor:
    actor = getattr(request.state, "actor", None)
    if not isinstance(actor, AuthenticatedActor):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return actor


def _policy_call[ResponseT](call: Callable[[], ResponseT]) -> ResponseT:
    try:
        return call()
    except PolicyForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "POLICY_MUTATION_FORBIDDEN",
                "message": "Policy mutation is not permitted.",
            },
        ) from None
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "POLICY_NOT_FOUND", "message": "The policy was not found."},
        ) from None
    except (AdministrationConflictError, AdministrationAuditCapacityError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "POLICY_VERSION_CONFLICT",
                "message": "The policy catalogue changed; refresh before retrying.",
            },
        ) from None
    except PolicyValidationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "POLICY_REQUEST_INVALID", "message": "The policy request is invalid."},
        ) from None
    except PersistenceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "ADMINISTRATION_UNAVAILABLE",
                "message": "Policy administration is temporarily unavailable.",
            },
        ) from None
