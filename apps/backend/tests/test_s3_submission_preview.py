"""Exact reviewed XPI payload fields and canonical-source labels."""

from test_goldtier_xpi_sandbox import _sandbox_submission

from app.mappers.goldtier_xpi import GoldTierXpiRequestMapper


def test_every_transmitted_shell_scalar_is_in_the_frozen_preview() -> None:
    mapper = GoldTierXpiRequestMapper()
    submission = _sandbox_submission()
    payload = mapper.build_shell_request(submission).model_dump(by_alias=True, exclude_none=True)
    preview = mapper.build_preview(submission)
    shell = next(item for item in preview.operations if item.operation == "SHELL")
    flattened = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            flattened.update({f"{key}.{nested}": scalar for nested, scalar in value.items()})
        else:
            flattened[key] = value
    assert {field.target_field: field.value for field in shell.fields} == flattened
    assert all(
        field.provenance == "CANONICAL_EVIDENCE"
        for field in shell.fields if field.authority == "CANONICAL_EVIDENCE"
    )


def test_absent_optional_address_line_is_omitted_from_request_and_preview() -> None:
    mapper = GoldTierXpiRequestMapper()
    submission = _sandbox_submission()
    submission = submission.model_copy(update={"canonical_entity":
        submission.canonical_entity.model_copy(update={"registered_address":
            submission.canonical_entity.registered_address.model_copy(
                update={"address_line_2": None}
            )
        })
    })
    payload = mapper.build_shell_request(submission).model_dump(by_alias=True, exclude_none=True)
    shell = next(item for item in mapper.build_preview(submission).operations
                 if item.operation == "SHELL")
    assert "street2" not in payload["legalRegisteredAddress"]
    assert "legalRegisteredAddress.street2" not in {field.target_field for field in shell.fields}
