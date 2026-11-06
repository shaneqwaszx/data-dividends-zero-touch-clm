"""D-125: the one deterministic statute comparison (no fuzzy or partial match, no AI)."""

import pytest

from app.services.government_status import normalise_statute, statute_matches

DOCUMENT = "Demo Parks FYP Test Authority Act (fictional FYP test instrument)"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Demo Parks FYP Test Authority Act", "demo parks fyp test authority act"),
        ("  DEMO   Parks\tFYP Test Authority Act  ", "demo parks fyp test authority act"),
        (DOCUMENT, "demo parks fyp test authority act"),
        ("Demo Parks FYP Test Authority Act 2099", "demo parks fyp test authority act"),
        ("Demo Parks FYP Test Authority Act, 2099.", "demo parks fyp test authority act"),
        ("Demo Parks (Amendment (No. 2)) Act", "demo parks act"),
        ("Demo-Parks F.Y.P. Act", "demo parks f y p act"),
        ("Demo Parks Act 2099 2098", "demo parks act 2099"),  # only one trailing year
        ("Demo 2099 Parks Act", "demo 2099 parks act"),  # a year mid-name stays
        ("Demo Parks Act 209", "demo parks act 209"),  # not a four-digit year
        ("Demo Parks Act2099", "demo parks act2099"),  # not a separate token
        ("(fictional)", ""),
    ],
)
def test_normalise_statute(value, expected):
    assert normalise_statute(value) == expected


@pytest.mark.parametrize(
    "entered",
    [
        "Demo Parks FYP Test Authority Act",
        "demo parks fyp test authority act",
        "  Demo  Parks  FYP  Test  Authority  Act  ",
        "Demo Parks FYP Test Authority Act 2099",
        "Demo Parks FYP Test Authority Act (Cap. 999)",
        DOCUMENT,
    ],
)
def test_equal_after_normalisation_is_accepted(entered):
    assert statute_matches(entered, DOCUMENT)


@pytest.mark.parametrize(
    "entered",
    [
        "Some Other Act",
        "Demo Parks FYP Test Authority",  # partial: no prefix matching
        "Demo Parks FYP Test Authority Act Extra",
        "Demo Parks FYP Test Authority Bill",  # one word off: no fuzzy matching
        "Demo Parks FYP Test Authorty Act",  # a typo is not corrected
        "fictional FYP test instrument",  # only the bracketed text
        "(Demo Parks FYP Test Authority Act)",  # all bracketed: empty after normalising
        "...",
    ],
)
def test_a_different_or_partial_statute_is_rejected(entered):
    assert not statute_matches(entered, DOCUMENT)


def test_an_empty_normal_form_never_matches_an_empty_instrument():
    assert not statute_matches("(x)", "(y)")
