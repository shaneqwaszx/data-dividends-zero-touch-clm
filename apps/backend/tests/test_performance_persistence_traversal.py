"""Persistence traversal must reject ignored nested extras and malformed containers."""

from copy import deepcopy
from decimal import Decimal
from enum import StrEnum

import pytest
from pydantic import BaseModel

from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_case_store import _persistence_value, _reject_unknown_model_fields


class Key(StrEnum):
    ITEM = "item"


class Leaf(BaseModel):
    amount: Decimal


class Branch(BaseModel):
    leaf: Leaf
    rows: tuple[Leaf, ...]
    mapping: dict[Key, Leaf]
    scalars: list[int]
    optional: Leaf | None = None


def fixture() -> tuple[dict[str, object], Branch]:
    model = Branch(
        leaf=Leaf(amount=Decimal("25.0001")),
        rows=(Leaf(amount=Decimal("74.9999")),),
        mapping={Key.ITEM: Leaf(amount=Decimal("100"))},
        scalars=[1, 2],
    )
    return _persistence_value(model), model


def test_supported_nested_value_is_unchanged_and_exact() -> None:
    raw, model = fixture()
    original = deepcopy(raw)
    _reject_unknown_model_fields(raw, model)
    assert raw == original
    assert model.leaf.amount + model.rows[0].amount == Decimal("100")
    # An absent optional field remains valid, as it was before this traversal change.
    raw.pop("optional")
    _reject_unknown_model_fields(raw, model)


@pytest.mark.parametrize(
    "path, value",
    [
        ((), {"extra": True}),
        (("leaf",), {"amount": "25.0001", "extra": True}),
        (("rows",), [{"amount": "74.9999", "extra": True}]),
        (("mapping",), {"item": {"amount": "100", "extra": True}}),
        (("mapping",), {"other": {"amount": "100"}}),
        (("rows",), []),
        (("rows",), ({"amount": "74.9999"},)),
        (("mapping",), []),
        (("leaf",), []),
        (("scalars",), [1]),
    ],
)
def test_unknown_fields_and_container_shape_fail_closed(
    path: tuple[str, ...], value: object
) -> None:
    raw, model = fixture()
    if path:
        raw[path[0]] = value
    else:
        raw.update(value)
    original = deepcopy(raw)
    with pytest.raises(PersistenceDataInvalidError):
        _reject_unknown_model_fields(raw, model)
    assert raw == original
