"""Generate only fictional text-PDF fixtures for the Phase 08 local POC."""

from collections.abc import Mapping
from pathlib import Path

FIXTURE_DIRECTORY = (
    Path(__file__).resolve().parents[1] / "apps/backend/tests/fixtures/uat"
)


def text_pdf(
    fields: Mapping[str, str],
    *,
    extra_lines: tuple[str, ...] = (),
    include_text: bool = True,
) -> bytes:
    lines = ["SYNTHETIC TEST DATA", "CORPORATE PROFILE"] if include_text else []
    lines.extend(f"{label}: {value}" for label, value in fields.items())
    lines.extend(extra_lines)
    escaped = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in lines
    ]
    operations = "BT /F1 12 Tf 72 720 Td "
    operations += " Tj 0 -16 Td ".join(f"({line})" for line in escaped)
    operations += " Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(operations.encode('latin-1'))} >>\nstream\n{operations}\nendstream",
    ]
    output = "%PDF-1.4\n"
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(output.encode("latin-1")))
        output += f"{index} 0 obj\n{item}\nendobj\n"
    xref = len(output.encode("latin-1"))
    output += "xref\n0 6\n0000000000 65535 f\n"
    output += "".join(f"{offset:010d} 00000 n\n" for offset in offsets[1:])
    output += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return output.encode("latin-1")


def main() -> None:
    clean = {
        "Legal Name": "MERLION CIRCULAR LABS PTE. LTD.",
        "UEN": "202400001A",
        "Registered Address": "18 INNOVATION WAY, #04-01, 018956, SG",
        "Country": "SG",
    }
    variants: dict[str, tuple[dict[str, str], tuple[str, ...]]] = {
        "clean-company-profile.pdf": (clean, ()),
        "address-mismatch.pdf": (
            clean | {"Registered Address": "25 ROBINSON ROAD, SINGAPORE 048547"},
            (),
        ),
        "legal-name-mismatch.pdf": (
            clean | {"Legal Name": "INCORRECT SYNTHETIC NAME PTE. LTD."},
            (),
        ),
        "missing-field.pdf": (
            {key: value for key, value in clean.items() if key != "Country"},
            (),
        ),
        "low-confidence.pdf": (
            clean,
            ("Legal Name: SECOND SYNTHETIC NAME PTE. LTD.",),
        ),
        "second-case-isolation.pdf": (
            {
                "Legal Name": "LION CITY EXISTING CUSTOMER PTE. LTD.",
                "UEN": "202400005E",
                "Registered Address": "18 CUSTOMER ROAD, #05-02, 068914, SG",
                "Country": "SG",
            },
            (),
        ),
        "cycle-uen-clean.pdf": (
            {
                "Legal Name": "CYCLIC HARBOUR HOLDINGS PTE. LTD.",
                "UEN": "202400006F",
                "Registered Address": "18 CYCLE STREET, #01-01, 049001, SG",
                "Country": "SG",
            },
            (),
        ),
    }
    for name, (fields, extra_lines) in variants.items():
        (FIXTURE_DIRECTORY / name).write_bytes(
            text_pdf(fields, extra_lines=extra_lines)
        )
    (FIXTURE_DIRECTORY / "no-text.pdf").write_bytes(text_pdf({}, include_text=False))


if __name__ == "__main__":
    main()
