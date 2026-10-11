"""Generate only the four deterministic native-text SYNTHETIC MOCK client PDFs."""

import argparse
import sys
from pathlib import Path
from textwrap import wrap

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/backend")]

from scripts.generate_phase08_synthetic_pdfs import (
    FIXTURE_DIRECTORY,
    text_pdf,
)
from scripts.synthetic_company_pack import (
    SPONSOR_DEMO_COMPANIES,
    SYNTHETIC_COMPANIES,
    SyntheticCompany,
    sponsor_demo_document_name,
)


def registry_annex_lines(company: SyntheticCompany) -> tuple[str, ...]:
    lines = [
        "REGISTRY OWNERSHIP ANNEX - INFORMATIONAL",
        "Source: LOCAL_SYNTHETIC_UAT_V1 project fixture. Not official ACRA.",
        "This annex describes the seeded registry graph, not a client declaration.",
        "Percentages are registry-fixture interests. The existing Decimal engine",
        "computes effective interests and provisional candidates during onboarding.",
        f"ROOT = {company.legal_name} ({company.uen})",
    ]
    lines.extend(f"{key} = {name} ({kind})" for key, kind, name in company.parties)
    lines.append("Registered graph edges (owned entity -> interested party):")
    lines.extend(
        f"Registry edge {parent} -> {child} = {percent}%"
        for parent, child, percent in company.edges
    )
    return tuple(part for line in lines for part in wrap(line, width=74))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sponsor-demo", action="store_true",
        help="Create four separate sourced registry-annex documents; preserve legacy PDFs.",
    )
    args = parser.parse_args()
    if args.sponsor_demo:
        for company in SPONSOR_DEMO_COMPANIES:
            document_path = (
                FIXTURE_DIRECTORY / "zero-touch-database" / sponsor_demo_document_name(company)
            )
            document_path.write_bytes(
                text_pdf(company.document_fields | {
                    "KYC Customer Type": "Company - Private", "Client Segment": "Corporate",
                }, extra_lines=registry_annex_lines(company))
            )
        print("SPONSOR_DEMO_SYNTHETIC_MOCK_NATIVE_PDF_COUNT=4")
        return
    for company in SYNTHETIC_COMPANIES:
        (FIXTURE_DIRECTORY / "zero-touch-database" / company.document_name).write_bytes(
            text_pdf(
                company.document_fields | {
                    "KYC Customer Type": "Company - Private",
                    "Client Segment": "Corporate",
                },
                extra_lines=(
                    "LOCAL PROJECT SYNTHETIC MOCK - fictional identity only.",
                    "Ownership evidence comes from the synthetic registry graph.",
                ),
            )
        )
    print("SYNTHETIC_MOCK_NATIVE_PDF_COUNT=4")


if __name__ == "__main__":
    main()
