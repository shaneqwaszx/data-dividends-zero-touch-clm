"""Project-owned SYNTHETIC MOCK data feeding the existing local seed owner.

These fictional identities/graphs are not official ACRA or legal UBO evidence.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SyntheticCompany:
    code: str
    uen: str
    legal_name: str
    street: str
    unit: str
    postal_code: str
    document_name: str
    parties: tuple[tuple[str, str, str], ...]
    # ROOT binds to ENTITY_<UEN>; all percentages enter the strict DTO as Decimal.
    edges: tuple[tuple[str, str, str], ...]

    @property
    def document_fields(self) -> dict[str, str]:
        return {
            "Legal Name": self.legal_name,
            "UEN": self.uen,
            "Registered Address": f"18 {self.street}, {self.unit}, {self.postal_code}, SG",
            "Country": "SG",
        }


SYNTHETIC_COMPANIES = (
    SyntheticCompany(
        "ORION",
        "202400014N",
        "ORION SYNTHETIC TECHNOLOGIES PTE. LTD.",
        "ORION PARK",
        "#06-01",
        "049014",
        "orion-synthetic-technologies-client.pdf",
        (
            ("ORION_OWNER_A", "NATURAL_PERSON", "Avery Synthetic"),
            ("ORION_OWNER_B", "NATURAL_PERSON", "Blair Synthetic"),
        ),
        (("ROOT", "ORION_OWNER_A", "70"), ("ROOT", "ORION_OWNER_B", "30")),
    ),
    SyntheticCompany(
        "PACIFIC",
        "202400015O",
        "PACIFIC SYNTHETIC LEDGER PTE. LTD.",
        "LEDGER QUAY",
        "#07-02",
        "049015",
        "pacific-synthetic-ledger-client.pdf",
        (
            ("PACIFIC_OWNER_A", "NATURAL_PERSON", "Casey Synthetic"),
            ("PACIFIC_OWNER_B", "NATURAL_PERSON", "Dana Synthetic"),
            ("PACIFIC_OWNER_C", "NATURAL_PERSON", "Ellis Synthetic"),
        ),
        (
            ("ROOT", "PACIFIC_OWNER_A", "40"),
            ("ROOT", "PACIFIC_OWNER_B", "35"),
            ("ROOT", "PACIFIC_OWNER_C", "25"),
        ),
    ),
    SyntheticCompany(
        "STRAITS",
        "202400016P",
        "STRAITS SYNTHETIC HOLDINGS PTE. LTD.",
        "STRAITS VIEW",
        "#08-03",
        "049016",
        "straits-synthetic-holdings-client.pdf",
        (
            ("STRAITS_HOLDING", "LEGAL_ENTITY", "Straits Synthetic Ventures Pte. Ltd."),
            ("STRAITS_DIRECT", "NATURAL_PERSON", "Jordan Synthetic"),
            ("STRAITS_PERSON_A", "NATURAL_PERSON", "Fiona Synthetic"),
            ("STRAITS_PERSON_B", "NATURAL_PERSON", "Gabriel Synthetic"),
        ),
        (
            ("ROOT", "STRAITS_HOLDING", "60"),
            ("ROOT", "STRAITS_DIRECT", "40"),
            ("STRAITS_HOLDING", "STRAITS_PERSON_A", "80"),
            ("STRAITS_HOLDING", "STRAITS_PERSON_B", "20"),
        ),
    ),
    SyntheticCompany(
        "MERIDIAN",
        "202400017Q",
        "MERIDIAN SYNTHETIC INFRASTRUCTURE PTE. LTD.",
        "MERIDIAN DRIVE",
        "#09-04",
        "049017",
        "meridian-synthetic-infrastructure-client.pdf",
        (
            ("MERIDIAN_HOLDING", "LEGAL_ENTITY", "Meridian Synthetic Capital Pte. Ltd."),
            ("MERIDIAN_DIRECT_A", "NATURAL_PERSON", "Iris Synthetic"),
            ("MERIDIAN_DIRECT_B", "NATURAL_PERSON", "Julian Synthetic"),
            ("MERIDIAN_PERSON_A", "NATURAL_PERSON", "Hannah Synthetic"),
            ("MERIDIAN_PERSON_B", "NATURAL_PERSON", "Ian Synthetic"),
        ),
        (
            ("ROOT", "MERIDIAN_HOLDING", "50"),
            ("ROOT", "MERIDIAN_DIRECT_A", "30"),
            ("ROOT", "MERIDIAN_DIRECT_B", "20"),
            ("MERIDIAN_HOLDING", "MERIDIAN_PERSON_A", "60"),
            ("MERIDIAN_HOLDING", "MERIDIAN_PERSON_B", "40"),
        ),
    ),
)

# Sponsor-demo shortlist is additive. Orion and the original four fixtures remain.
AURORA = SyntheticCompany(
    "AURORA", "202400019S", "AURORA SYNTHETIC SIGNALS PTE. LTD.",
    "SIGNAL TERRACE", "#10-01", "049019", "aurora-sponsor-demo-registry-annex.pdf",
    (("AURORA_PERSON_A", "NATURAL_PERSON", "Morgan Synthetic"),
     ("AURORA_PERSON_B", "NATURAL_PERSON", "Rowan Synthetic")),
    (("ROOT", "AURORA_PERSON_A", "65"), ("ROOT", "AURORA_PERSON_B", "35")),
)
SPONSOR_DEMO_COMPANIES = (AURORA, *SYNTHETIC_COMPANIES[1:])


def sponsor_demo_document_name(company: SyntheticCompany) -> str:
    return f"{company.code.lower()}-sponsor-demo-registry-annex.pdf"
