"""D-095: the backend computes a SHA-256 of each uploaded document's bytes, stores it on the
document record (case snapshot schema 16) and serves it only through the narrow, case-scoped
document-digests route. Synthetic fixtures only; no network."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from test_document_api import create_case, upload

from app.composition import build_onboarding_service
from app.config import Settings
from app.domain.documents import (
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
)
from app.main import create_app
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.authorization import RouteAccess, classify_route

UAT = Path(__file__).parent / "fixtures" / "uat"
FIXTURE = UAT / "clean-company-profile.pdf"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _tampered(content: bytes) -> bytes:
    """The same length, one byte changed inside the PDF body (still a parseable upload)."""

    position = content.index(b"stream") + 20
    changed = bytes([content[position] ^ 0x01])
    return content[:position] + changed + content[position + 1 :]


async def _digests(client: httpx.AsyncClient, case_id: object) -> list[dict[str, object]]:
    response = await client.get(f"/api/onboarding/cases/{case_id}/document-digests")
    assert response.status_code == 200, response.text
    body: list[dict[str, object]] = response.json()
    return body


@pytest.mark.anyio
async def test_the_digest_is_computed_from_the_uploaded_bytes_and_served_for_that_record() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        content = FIXTURE.read_bytes()
        created = await upload(client, case["case_id"], content=content, name=FIXTURE.name)
        assert created.status_code == 201, created.text
        listed = (await client.get(f"/api/onboarding/cases/{case['case_id']}/documents")).json()
        digests = await _digests(client, case["case_id"])
    # Upload and retrieval agree: the same document id and version, the digest of its bytes.
    assert [(item["document_id"], item["document_version"]) for item in digests] == [
        (item["document_id"], item["document_version"]) for item in listed
    ]
    assert digests[0]["content_sha256"] == hashlib.sha256(content).hexdigest()
    assert set(digests[0]) == {"document_id", "document_version", "content_sha256"}


@pytest.mark.anyio
async def test_altered_bytes_with_the_same_name_type_and_size_get_another_digest() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    content = FIXTURE.read_bytes()
    tampered = _tampered(content)
    assert len(tampered) == len(content) and tampered != content
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        original = await upload(client, case["case_id"], content=content, name=FIXTURE.name)
        other = await create_case(client)
        altered = await upload(client, other["case_id"], content=tampered, name=FIXTURE.name)
        assert original.status_code == altered.status_code == 201
        first = await _digests(client, case["case_id"])
        second = await _digests(client, other["case_id"])
    assert original.json()["size_bytes"] == altered.json()["size_bytes"]
    assert first[0]["content_sha256"] == hashlib.sha256(content).hexdigest()
    assert second[0]["content_sha256"] == hashlib.sha256(tampered).hexdigest()
    assert first[0]["content_sha256"] != second[0]["content_sha256"]


@pytest.mark.anyio
async def test_browser_document_projections_do_not_carry_the_digest() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        created = await upload(client, case["case_id"], content=FIXTURE.read_bytes())
        document_id = created.json()["document_id"]
        texts = [
            created.text,
            (await client.get(f"/api/onboarding/cases/{case['case_id']}/documents")).text,
            (
                await client.get(f"/api/onboarding/cases/{case['case_id']}/documents/{document_id}")
            ).text,
            (await client.get(f"/api/onboarding/cases/{case['case_id']}")).text,
        ]
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert all("content_sha256" not in text and digest not in text for text in texts)


@pytest.mark.anyio
async def test_an_unknown_case_has_no_digests() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/onboarding/cases/{uuid4()}/document-digests")
    assert response.status_code == 404


def test_the_digest_route_has_the_document_list_case_scope() -> None:
    policy, params = classify_route("GET", f"/api/onboarding/cases/{uuid4()}/document-digests")
    assert policy is not None and policy.access == RouteAccess.CASE_SCOPED
    assert set(params) == {"case_id"}


# --- persistence: schema 16 keeps the digest; schema 15 reads without one -----------------------


def _snapshot(digest: str | None) -> DurableCaseSnapshot:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    document = DocumentProcessingRecord(
        case_id=case.case_id,
        document_id=uuid4(),
        correlation_id=uuid4(),
        display_name=FIXTURE.name,
        media_type="application/pdf",
        size_bytes=FIXTURE.stat().st_size,
        content_sha256=digest,
        profile=DocumentProfile.CERTIFICATE_OF_INCORPORATION_POC,
        state=DocumentProcessingState.UPLOADED,
        created_at=now,
        updated_at=now,
    )
    return DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        documents=(document,),
        created_at=now,
        updated_at=now,
    )


def _raw(snapshot: DurableCaseSnapshot) -> dict[str, object]:
    raw: dict[str, object] = snapshot.model_dump(mode="json", exclude_unset=False)
    raw["_id"] = str(snapshot.case_id)
    return raw


def test_schema_16_keeps_the_digest_through_a_round_trip() -> None:
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    raw = _raw(_snapshot(digest))
    assert raw["schema_version"] == 16
    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001
    assert decoded.documents[0].content_sha256 == digest


def test_a_schema_15_document_reads_without_a_digest_and_is_not_rewritten() -> None:
    raw = _raw(_snapshot(None))
    raw["schema_version"] = 15
    for document in raw["documents"]:  # type: ignore[attr-defined]
        document.pop("content_sha256")
    before = {**raw}
    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001
    assert decoded.schema_version == 16
    assert decoded.documents[0].content_sha256 is None
    assert raw == before


@pytest.mark.parametrize("digest", ["0" * 64, None])
def test_a_schema_15_envelope_cannot_carry_a_digest_even_if_null(digest: str | None) -> None:
    raw = _raw(_snapshot(digest))
    raw["schema_version"] = 15
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


def test_a_malformed_digest_is_refused() -> None:
    with pytest.raises(ValueError):
        _snapshot("not-a-sha256")
