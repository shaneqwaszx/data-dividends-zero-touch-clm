"""Four entirely fictional FYP companies; normalized evidence, never HTTP payloads."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.jurisdiction import is_eligible_singapore_uen
from app.domain.models import (
    CanonicalLegalEntity,
    RegisteredAddress,
    RegistryAcquisitionBundle,
    RegistryAcquisitionStatus,
    RegistryCacheKey,
    RegistryEvidenceProvenance,
    RegistryOfficer,
    RegistryOperation,
    RegistryOperationResult,
    RegistryOperationStatus,
    RegistryOwnershipParty,
    RegistryPartyType,
    RegistryRelationship,
    RegistrySnapshotEntry,
    SourceEnvironment,
    SourceMetadata,
    SourceSystem,
)
from app.domain.registry_dataset import local_synthetic_registry_identity

from scripts.synthetic_company_pack import (
    AURORA,
    SYNTHETIC_COMPANIES,
    sponsor_demo_document_name,
)


@dataclass(frozen=True)
class HappyPathCompany:
    code: str
    name: str
    uen: str
    street: str
    postal_code: str
    # Owned entity suffix ROOT is bound to this company's root.
    edges: tuple[tuple[str, str, str], ...]
    expected: tuple[tuple[str, str], ...]

    kyc_customer_type: str = "Company - Private"
    client_segment: str = "Corporate"
    party_type: str = "PRIVATE COMPANY LIMITED BY SHARES"

    # Optional explicit fictional identities; defaults preserve the original four seeds.
    unit: str | None = None
    native_document_name: str | None = None
    explicit_parties: tuple[tuple[str, str, str], ...] = ()

    @property
    def document_fields(self) -> dict[str, str]:
        return self.fields

    @property
    def document_name(self) -> str:
        return self.native_document_name or f"demo-{self.code.lower()}-scanned.pdf"

    @property
    def fields(self) -> dict[str, str]:
        return {
            "Legal Name": self.name,
            "UEN": self.uen,
            "Registered Address": ", ".join(part for part in (self.street, self.unit, self.postal_code, "SG") if part),
            "Country": "SG",
        }

    @property
    def target_profile(self) -> dict[str, str]:
        return {"KYC Customer Type": self.kyc_customer_type, "Client Segment": self.client_segment,
                "Registration Type": "ACRA", "Customer External System": "DSD",
                "Policy": "Singapore", "Booking Entity": "ANZBGL (Singapore Branch)"}

    def bundle(self, now: datetime) -> RegistryAcquisitionBundle:
        if not self.edges:
            raise ValueError("Classification-only fixture has no supported share ownership bundle")
        if not is_eligible_singapore_uen(self.uen):
            raise ValueError("fictional identifier is not supported")
        root = f"ENTITY_{self.uen}"

        def party_id(suffix: str) -> str:
            if suffix == "ROOT":
                return root
            return suffix if self.explicit_parties else f"DEMO_{self.code}_{suffix}"

        def provenance(operation: RegistryOperation) -> RegistryEvidenceProvenance:
            return RegistryEvidenceProvenance(
                provider=SourceSystem.ACRA,
                environment=SourceEnvironment.MOCK,
                operation=operation,
                retrieved_at=now,
                evidence_reference=f"LOCAL_SYNTHETIC_SEED_{self.code}_{operation.value}",
            )

        corporate = {owned for owned, _, _ in self.edges if owned != "ROOT"}
        owners = sorted({owner for _, owner, _ in self.edges})
        parties = tuple(
            RegistryOwnershipParty(
                party_id=party_id(owner),
                party_type=(
                    RegistryPartyType.LEGAL_ENTITY
                    if owner in corporate
                    else RegistryPartyType.NATURAL_PERSON
                ),
                name=(f"DEMO {self.code} "
                      f"{'HOLDING ENTITY' if owner in corporate else 'PERSON'} {owner}"),
                registration_identifier=(
                    f"{int(self.uen[:-1]) + int(owner[1:]) * 100}{self.uen[-1]}"
                    if owner in corporate
                    else None
                ),
                country="SG",
                provenance=provenance(RegistryOperation.OWNERSHIP_PARTIES),
            )
            for owner in (() if self.explicit_parties else owners)
        )
        if self.explicit_parties:
            parties = tuple(
                RegistryOwnershipParty(
                    party_id=identifier, party_type=RegistryPartyType(kind), name=name,
                    registration_identifier=f"SYN-{identifier}" if kind == "LEGAL_ENTITY" else None,
                    country="SG", provenance=provenance(RegistryOperation.OWNERSHIP_PARTIES),
                ) for identifier, kind, name in self.explicit_parties
            )
        officers = tuple(
            RegistryOfficer(
                officer_id=f"DEMO_{self.code}_OFFICER_{index}",
                name=f"DEMO {self.code} OFFICER {index}",
                role=role,
                appointment_date=date(2026, 1, 5),
                country="SG",
                provenance=provenance(RegistryOperation.OFFICERS),
            )
            for index, role in enumerate(("DIRECTOR", "SECRETARY"), 1)
        )
        relationships = tuple(
            RegistryRelationship(
                relationship_id=f"DEMO_{self.code}_EDGE_{index}",
                owned_entity_id=party_id(owned),
                owner_party_id=party_id(owner),
                ownership_percentage=Decimal(percent),
                provenance=provenance(RegistryOperation.RELATIONSHIPS),
            )
            for index, (owned, owner, percent) in enumerate(self.edges, 1)
        )
        counts = (1, len(officers), len(parties), len(relationships))
        return RegistryAcquisitionBundle(
            requested_identifier=self.uen,
            root_party_id=root,
            entity_profile=CanonicalLegalEntity(
                registration_number=self.uen,
                legal_name=self.name,
                country_of_incorporation="SG",
                party_type=self.party_type,
                registration_date=date(2026, 1, 5),
                entity_status="LIVE",
                registered_address=RegisteredAddress(
                    address_line_1=self.street,
                    address_line_2=self.unit,
                    postal_code=self.postal_code,
                    country_code="SG",
                ),
                source=SourceMetadata(
                    source_system=SourceSystem.ACRA,
                    environment=SourceEnvironment.MOCK,
                    registry_source_link=f"local-synthetic:LOCAL_SYNTHETIC_UAT_V1:{self.code}",
                    retrieved_at=now,
                ),
            ),
            officers=officers,
            ownership_parties=parties,
            relationships=relationships,
            operation_results=tuple(
                RegistryOperationResult(
                    operation=operation,
                    status=RegistryOperationStatus.COMPLETE,
                    record_count=count,
                    provenance=provenance(operation),
                )
                for operation, count in zip(RegistryOperation, counts, strict=True)
            ),
            status=RegistryAcquisitionStatus.COMPLETE,
            retrieved_at=now,
        )

    def snapshot(self, now: datetime) -> RegistrySnapshotEntry:
        key = RegistryCacheKey(
            provider_identity=local_synthetic_registry_identity(), normalized_identifier=self.uen
        )
        return RegistrySnapshotEntry(
            cache_schema_version=2,
            cache_id=key.digest,
            key=key,
            revision=0,
            acquisition=self.bundle(now),
            freshness_anchor=now,
            written_at=now,
        )


COMPANIES = (
    HappyPathCompany(
        "ALPHA",
        "DEMO ALPHA CIRCULAR FYP TEST PTE. LTD.",
        "209990101A",
        "11 DEMO ALPHA WAY",
        "000101",
        (("ROOT", "P1", "60"), ("ROOT", "P2", "40")),
        (("P1", "60"), ("P2", "40")),
    ),
    HappyPathCompany(
        "BETA",
        "DEMO BETA HOLDINGS FYP TEST PTE. LTD.",
        "209990102B",
        "22 DEMO BETA WAY",
        "000102",
        (("ROOT", "H1", "50"), ("ROOT", "H2", "30"), ("ROOT", "P1", "20"),
         ("H1", "P1", "20"), ("H1", "P2", "50"), ("H1", "P3", "10"), ("H1", "P4", "10"), ("H1", "P5", "5"), ("H1", "P6", "5"),
         ("H2", "P3", "40"), ("H2", "P4", "30"), ("H2", "P5", "20"), ("H2", "P6", "10")),
        (("P1", "30"), ("P2", "25"), ("P3", "17"), ("P4", "14"), ("P5", "8.5"), ("P6", "5.5")),
    ),
    HappyPathCompany(
        "GAMMA",
        "DEMO GAMMA TECHNOLOGIES FYP TEST PARTNERSHIP",
        "209990103C",
        "33 DEMO GAMMA WAY",
        "000103",
        (("ROOT", "P1", "30"), ("ROOT", "P2", "25"), ("ROOT", "P3", "20"), ("ROOT", "P4", "10"), ("ROOT", "P5", "10"), ("ROOT", "P6", "5")),
        (("P1", "30"), ("P2", "25"), ("P3", "20"), ("P4", "10"), ("P5", "10"), ("P6", "5")),
        kyc_customer_type="Partnership - Unregulated", party_type="PARTNERSHIP",
    ),
    HappyPathCompany(
        "DELTA",
        "DEMO DELTA SUSTAINABILITY FYP TEST PTE. LTD.",
        "209990104D",
        "44 DEMO DELTA WAY",
        "000104",
        (
            ("ROOT", "H1", "80"),
            ("ROOT", "P4", "20"),
            ("H1", "H2", "50"),
            ("H1", "P3", "50"),
            ("H2", "P1", "75"),
            ("H2", "P2", "25"),
        ),
        (("P1", "30"), ("P2", "10"), ("P3", "40"), ("P4", "20")),
    ),
)

# Classification-only: no fabricated Government natural-person share/control graph.
GOVERNMENT = HappyPathCompany("GOVERNMENT", "DEMO GOVERNMENT FYP TEST AUTHORITY", "209990105E",
    "55 DEMO GOVERNMENT WAY", "000105", (), (), kyc_customer_type="Government",
    client_segment="DI - Government", party_type="GOVERNMENT")


# Data definitions feed the same normalized bundle/snapshot owner as Alpha through Delta.

_NEW_EXPECTED = {
    "ORION": (("ORION_OWNER_A", "70"), ("ORION_OWNER_B", "30")),
    "PACIFIC": (("PACIFIC_OWNER_A", "40"), ("PACIFIC_OWNER_B", "35"), ("PACIFIC_OWNER_C", "25")),
    "STRAITS": (("STRAITS_PERSON_A", "48"), ("STRAITS_DIRECT", "40"), ("STRAITS_PERSON_B", "12")),
    "MERIDIAN": (("MERIDIAN_PERSON_A", "30"), ("MERIDIAN_PERSON_B", "20"), ("MERIDIAN_DIRECT_A", "30"), ("MERIDIAN_DIRECT_B", "20")),
}
NEW_COMPANIES = tuple(
    HappyPathCompany(
        code=c.code, name=c.legal_name, uen=c.uen, street=f"18 {c.street}",
        postal_code=c.postal_code, edges=c.edges, expected=_NEW_EXPECTED[c.code],
        unit=c.unit, native_document_name=c.document_name, explicit_parties=c.parties,
    ) for c in SYNTHETIC_COMPANIES
)
ALL_COMPANIES = (*COMPANIES, *NEW_COMPANIES)

# Explicit opt-in seed selection; legacy default and its negative neighbor stay intact.
SPONSOR_DEMO_COMPANIES = (
    HappyPathCompany(
        code=AURORA.code, name=AURORA.legal_name, uen=AURORA.uen, street=f"18 {AURORA.street}",
        postal_code=AURORA.postal_code, edges=AURORA.edges,
        expected=(("AURORA_PERSON_A", "65"), ("AURORA_PERSON_B", "35")),
        unit=AURORA.unit, native_document_name=sponsor_demo_document_name(AURORA),
        explicit_parties=AURORA.parties,
    ),
    *(HappyPathCompany(
        code=c.code, name=c.name, uen=c.uen, street=c.street, postal_code=c.postal_code,
        edges=c.edges, expected=c.expected, unit=c.unit,
        native_document_name=f"{c.code.lower()}-sponsor-demo-registry-annex.pdf",
        explicit_parties=c.explicit_parties,
    ) for c in NEW_COMPANIES[1:]),
)
