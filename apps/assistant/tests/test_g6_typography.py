"""G-6 R1 (basis-changing; bundled with the next assistant release): hyphen and space variants
that some models write are mapped to plain ones before the copilot's sentence checks, so a
correct sentence is not removed for typography alone. Invisible characters and letters from
other scripts stay refused. Synthetic text only."""

from __future__ import annotations

import pytest

from ai_assistant import copilot


@pytest.mark.parametrize(
    "variant",
    ["‐", "‑"],
    ids=["hyphen", "non-breaking-hyphen"],
)
def test_hyphen_variants_no_longer_remove_a_sentence(variant: str) -> None:
    check = copilot.check_answer(f"The document review is a two{variant}step check.", None)
    assert check.left_out == [] and check.kept == 1
    assert check.text == "The document review is a two-step check."


@pytest.mark.parametrize(
    "variant", [" ", " ", " "], ids=["figure", "thin", "narrow-no-break"]
)
def test_space_variants_no_longer_remove_a_sentence(variant: str) -> None:
    check = copilot.check_answer(f"The UEN{variant}field is read from the document.", None)
    assert check.left_out == [] and check.kept == 1
    assert check.text == "The UEN field is read from the document."


@pytest.mark.parametrize(
    "character",
    ["​", "⁠", "﻿", "а"],
    ids=["zero-width-space", "word-joiner", "bom", "cyrillic-a"],
)
def test_invisible_and_other_script_characters_stay_refused(character: str) -> None:
    check = copilot.check_answer(f"The document review is n{character}t finished.", None)
    assert check.left_out == ["unsupported_character"] and check.kept == 0


def test_the_mapping_never_turns_a_removed_claim_into_a_kept_one() -> None:
    # The checks see plain ASCII: a claim hidden behind a non-breaking hyphen is still found.
    check = copilot.check_answer("I have approved the case‑file for you.", None)
    assert check.kept == 0 and check.left_out == ["assistant_action_claim"]
