"""Authenticated typed policy catalogue HTTP contract."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.api_auth import SESSION_COOKIE_NAME
from app.domain.access import AuthenticatedActor
from app.domain.policy import (
    IDP_POLICY_ID,
    PolicyAuthority,
    PolicyCatalogue,
    PolicyClassification,
    PolicyEnforcement,
    PolicyProposal,
    PolicyRule,
    PolicyValue,
    PolicyValueType,
    PolicyVersionRecord,
)
from app.domain.policy_impact import PolicyImpactResponse
from app.persistence.errors import PersistenceUnavailableError
from app.services.admin_repository import (
    AdministrationAuditCapacityError,
    AdministrationConflictError,
)
from app.services.authentication import AuthenticationError, AuthenticationService
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
    authority: PolicyAuthority | None
    default_authority: PolicyAuthority | None
    enforcement: PolicyEnforcement
    version: int
    created_at: datetime
    updated_at: datetime
    updated_by: str

    @classmethod
    def from_domain(cls, rule: PolicyRule) -> PolicyRuleResponse:
        response = cls.model_validate(rule)
        if rule.policy_id == IDP_POLICY_ID:
            return response.model_copy(update={
                "name": "IDP extraction evidence score threshold",
                "description": "Minimum deterministic extraction evidence score for "
                "provisional document continuation; not a probability or "
                "source-agreement measure.",
            })
        if rule.policy_id == "DOCUMENT_SUPPORTED_MEDIA_TYPES":
            return response.model_copy(update={
                "description": "Retained technical format snapshot. Current runtime "
                "supports bounded PDF, DOCX, UTF-8 TXT, PNG, JPEG and TIFF intake. "
                "File-processing safety limits are not editable policy.",
            })
        return response


class PolicyCatalogueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    catalogue_id: str
    version: int
    active_version: int
    active_identity: str
    active_origin: Literal["DEFAULT", "APPROVED", "MIGRATED"]
    active_effective_at: datetime | None
    proposals: tuple[PolicyProposal, ...]
    superseded_versions: tuple[PolicyVersionRecord, ...]
    rules: tuple[PolicyRuleResponse, ...]
    created_at: datetime
    updated_at: datetime
    updated_by: str

    @classmethod
    def from_domain(cls, catalogue: PolicyCatalogue) -> PolicyCatalogueResponse:
        return cls(
            catalogue_id=catalogue.catalogue_id,
            version=catalogue.version,
            active_version=catalogue.active_version,
            active_identity=catalogue.active_identity,
            active_origin=catalogue.active_origin,
            active_effective_at=catalogue.active_effective_at,
            proposals=catalogue.proposals,
            superseded_versions=catalogue.superseded_versions,
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
    authority: PolicyAuthority | None = None


class ResetPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_catalogue_version: Annotated[int, Field(strict=True, ge=1)]
    expected_rule_version: Annotated[int, Field(strict=True, ge=1)]
    confirmation: Literal["RESET_POLICY_DEFAULT"]


class ResetAllPoliciesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_catalogue_version: Annotated[int, Field(strict=True, ge=1)]
    confirmation: Literal["RESET_ALL_POLICY_DEFAULTS"]


class CreateProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_catalogue_version: Annotated[int, Field(strict=True, ge=1)]
    changes: Annotated[dict[str, PolicyValue], Field(max_length=64)] = Field(default_factory=dict)
    reset_ids: Annotated[tuple[str, ...], Field(max_length=64)] = ()
    reason: Annotated[str, Field(min_length=10, max_length=240)]


class EditProposalRequest(CreateProposalRequest):
    expected_proposal_version: Annotated[int, Field(strict=True, ge=1)]


class ProposalVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_catalogue_version: Annotated[int, Field(strict=True, ge=1)]
    expected_proposal_version: Annotated[int, Field(strict=True, ge=1)]


class ProposalDecisionRequest(ProposalVersionRequest):
    approve: Annotated[bool, Field(strict=True)]
    reason: Annotated[str, Field(min_length=10, max_length=240)]


def build_policy_router(
    service: PolicyManagementService, authentication: AuthenticationService
) -> APIRouter:
    router = APIRouter(prefix="/api/policies", tags=["policies"])

    @router.get("", response_model=PolicyCatalogueResponse)
    def list_policies() -> PolicyCatalogueResponse:
        return _policy_call(lambda: PolicyCatalogueResponse.from_domain(service.catalogue()))

    def fresh_actor(request: Request) -> Callable[[], AuthenticatedActor]:
        token = request.cookies.get(SESSION_COOKIE_NAME)

        def reauthorize() -> AuthenticatedActor:
            try:
                return authentication.authenticate_session(token).actor
            except AuthenticationError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": "A valid authenticated session is required.",
                    },
                ) from None

        return reauthorize

    @router.get("/classifier-benchmark")
    def classifier_benchmark() -> dict[str, object]:
        return _policy_call(service.classifier_benchmark)

    @router.get("/proposals/{proposal_id}/impact", response_model=PolicyImpactResponse)
    def proposal_impact(proposal_id: str) -> dict[str, object]:
        return _policy_call(lambda: service.proposal_impact(proposal_id))

    @router.post(
        "/proposals", response_model=PolicyCatalogueResponse, status_code=status.HTTP_201_CREATED
    )
    def create_proposal(body: CreateProposalRequest, request: Request) -> PolicyCatalogueResponse:
        return _policy_call(
            lambda: PolicyCatalogueResponse.from_domain(
                service.create_proposal(
                    _actor(request),
                    expected_catalogue_version=body.expected_catalogue_version,
                    changes=body.changes,
                    reset_ids=body.reset_ids,
                    reason=body.reason,
                    reauthorize=fresh_actor(request),
                )
            )
        )

    @router.patch("/proposals/{proposal_id}", response_model=PolicyCatalogueResponse)
    def edit_proposal(
        proposal_id: str, body: EditProposalRequest, request: Request
    ) -> PolicyCatalogueResponse:
        return _policy_call(
            lambda: PolicyCatalogueResponse.from_domain(
                service.edit_proposal(
                    _actor(request),
                    proposal_id,
                    expected_catalogue_version=body.expected_catalogue_version,
                    expected_proposal_version=body.expected_proposal_version,
                    changes=body.changes,
                    reset_ids=body.reset_ids,
                    reason=body.reason,
                    reauthorize=fresh_actor(request),
                )
            )
        )

    @router.post("/proposals/{proposal_id}/submit", response_model=PolicyCatalogueResponse)
    def submit_proposal(
        proposal_id: str, body: ProposalVersionRequest, request: Request
    ) -> PolicyCatalogueResponse:
        return _policy_call(
            lambda: PolicyCatalogueResponse.from_domain(
                service.submit_proposal(
                    _actor(request),
                    proposal_id,
                    expected_catalogue_version=body.expected_catalogue_version,
                    expected_proposal_version=body.expected_proposal_version,
                    reauthorize=fresh_actor(request),
                )
            )
        )

    @router.post("/proposals/{proposal_id}/decision", response_model=PolicyCatalogueResponse)
    def decide_proposal(
        proposal_id: str, body: ProposalDecisionRequest, request: Request
    ) -> PolicyCatalogueResponse:
        return _policy_call(
            lambda: PolicyCatalogueResponse.from_domain(
                service.decide_proposal(
                    _actor(request),
                    proposal_id,
                    expected_catalogue_version=body.expected_catalogue_version,
                    expected_proposal_version=body.expected_proposal_version,
                    approve=body.approve,
                    reason=body.reason,
                    reauthorize=fresh_actor(request),
                )
            )
        )

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
                    authority=body.authority,
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
