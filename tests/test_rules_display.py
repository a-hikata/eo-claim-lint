"""Tests for EOC201 and EOC202."""

from __future__ import annotations

import pytest

from eo_claim_lint import (
    ClaimType,
    ClaimValue,
    DisplayInfo,
    RuleConfig,
    Severity,
    Uncertainty,
    UncertaintyKind,
)
from eo_claim_lint.rules.display import DisplayLabelContradictionRule, DisplayUnitMismatchRule
from tests.conftest import make_document

LABEL_CONTRADICTION = DisplayLabelContradictionRule()
UNIT_MISMATCH = DisplayUnitMismatchRule()


def _estimate_claim() -> ClaimValue:
    return ClaimValue(
        type=ClaimType.ESTIMATE,
        statement="An example quantity was estimated.",
        value=0.55,
        unit="1",
        uncertainty=Uncertainty(kind=UncertaintyKind.INTERVAL, lower=0.5, upper=0.6),
    )


# --------------------------------------------------------------------------
# EOC201
# --------------------------------------------------------------------------


def test_eoc201_metadata() -> None:
    assert LABEL_CONTRADICTION.rule_id == "EOC201"
    assert LABEL_CONTRADICTION.default_severity is Severity.WARNING


@pytest.mark.parametrize("word", ["measured", "observed", "recorded"])
def test_eoc201_fires_when_an_estimate_is_labelled_as_a_measurement(
    word: str, config: RuleConfig
) -> None:
    document = make_document(
        claim=_estimate_claim(), display=DisplayInfo(label=f"{word.title()} example quantity")
    )

    issues = LABEL_CONTRADICTION.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC201"
    assert issues[0].path == "$.display"
    assert issues[0].field == "label"
    assert issues[0].context["term"] == word


@pytest.mark.parametrize("word", ["estimated", "predicted", "forecast", "modeled", "modelled"])
def test_eoc201_fires_when_an_observation_is_labelled_as_a_projection(
    word: str, config: RuleConfig
) -> None:
    document = make_document(display=DisplayInfo(label=f"{word.title()} example value"))

    assert LABEL_CONTRADICTION.check(document, config)


def test_eoc201_is_silent_on_a_consistent_label(config: RuleConfig) -> None:
    document = make_document(
        claim=_estimate_claim(), display=DisplayInfo(label="Estimated example quantity")
    )

    assert LABEL_CONTRADICTION.check(document, config) == ()


def test_eoc201_is_silent_on_a_neutral_label(config: RuleConfig) -> None:
    assert LABEL_CONTRADICTION.check(make_document(), config) == ()


def test_eoc201_matches_whole_words_only(config: RuleConfig) -> None:
    """'Remeasured' is a different word from 'measured'."""
    document = make_document(
        claim=_estimate_claim(), display=DisplayInfo(label="Remeasurement of the quantity")
    )

    assert LABEL_CONTRADICTION.check(document, config) == ()


def test_eoc201_applies_to_interpretations_as_well(config: RuleConfig) -> None:
    document = make_document(
        claim=ClaimValue(
            type=ClaimType.INTERPRETATION,
            statement="The series is read as increasing.",
            uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN),
        ),
        display=DisplayInfo(label="Measured trend"),
    )

    assert LABEL_CONTRADICTION.check(document, config)


def test_eoc201_does_not_modify_the_document(config: RuleConfig) -> None:
    document = make_document(
        claim=_estimate_claim(), display=DisplayInfo(label="Measured example quantity")
    )
    before = document.to_dict()

    LABEL_CONTRADICTION.check(document, config)

    assert document.to_dict() == before


# --------------------------------------------------------------------------
# EOC202
# --------------------------------------------------------------------------


def test_eoc202_metadata() -> None:
    assert UNIT_MISMATCH.rule_id == "EOC202"
    assert UNIT_MISMATCH.default_severity is Severity.WARNING


def test_eoc202_fires_when_the_units_differ(config: RuleConfig) -> None:
    document = make_document(display=DisplayInfo(label="Index", display_unit="index"))

    issues = UNIT_MISMATCH.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC202"
    assert issues[0].path == "$.display"
    assert issues[0].field == "display_unit"


def test_eoc202_is_silent_when_the_units_match(config: RuleConfig) -> None:
    document = make_document(display=DisplayInfo(label="Index", display_unit="1"))

    assert UNIT_MISMATCH.check(document, config) == ()


def test_eoc202_is_silent_when_no_display_unit_is_given(config: RuleConfig) -> None:
    assert UNIT_MISMATCH.check(make_document(), config) == ()


def test_eoc202_is_silent_when_the_claim_has_no_unit(config: RuleConfig) -> None:
    document = make_document(
        claim=ClaimValue(type=ClaimType.OBSERVATION, statement="An example statement.", value=1),
        display=DisplayInfo(label="Index", display_unit="index"),
    )

    assert UNIT_MISMATCH.check(document, config) == ()


def test_eoc202_does_no_conversion_and_says_so(config: RuleConfig) -> None:
    """Documented behaviour: a human-readable rendering is reported too."""
    document = make_document(display=DisplayInfo(label="Index", display_unit="index"))

    assert "no conversion" in UNIT_MISMATCH.check(document, config)[0].message


def test_eoc202_context_carries_no_values(config: RuleConfig) -> None:
    """The units themselves stay out of the report; the path is enough to find them."""
    document = make_document(display=DisplayInfo(label="Index", display_unit="index"))

    assert UNIT_MISMATCH.check(document, config)[0].context == {}
