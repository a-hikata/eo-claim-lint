"""Tests for EOC102 and EOC103."""

from __future__ import annotations

import pytest

from eo_claim_lint import (
    ClaimType,
    ClaimValue,
    DataProcessing,
    DisplayInfo,
    RuleConfig,
    Severity,
    Uncertainty,
    UncertaintyKind,
)
from eo_claim_lint.rules.claim_type import (
    InterpretationQualificationRule,
    ObservationProcessingRule,
)
from tests.conftest import make_document

OBSERVATION_PROCESSING = ObservationProcessingRule()
INTERPRETATION_QUALIFICATION = InterpretationQualificationRule()


# --------------------------------------------------------------------------
# EOC102
# --------------------------------------------------------------------------


def test_eoc102_metadata() -> None:
    assert OBSERVATION_PROCESSING.rule_id == "EOC102"
    assert OBSERVATION_PROCESSING.default_severity is Severity.WARNING


def test_eoc102_fires_on_a_modeled_observation(config: RuleConfig) -> None:
    document = make_document(data_processing=DataProcessing.MODELED)

    issues = OBSERVATION_PROCESSING.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC102"
    assert issues[0].path == "$"
    assert issues[0].field == "data_processing"
    assert issues[0].context["data_processing"] == "modeled"


@pytest.mark.parametrize(
    "processing", [DataProcessing.RAW, DataProcessing.DERIVED, DataProcessing.UNKNOWN]
)
def test_eoc102_is_silent_for_other_processing_states(
    processing: DataProcessing, config: RuleConfig
) -> None:
    assert OBSERVATION_PROCESSING.check(make_document(data_processing=processing), config) == ()


def test_eoc102_is_silent_for_a_modeled_estimate(config: RuleConfig) -> None:
    """A modeled estimate is exactly what an estimate is supposed to be."""
    document = make_document(
        claim=ClaimValue(
            type=ClaimType.ESTIMATE,
            statement="An example quantity was estimated.",
            uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN),
        ),
        data_processing=DataProcessing.MODELED,
    )

    assert OBSERVATION_PROCESSING.check(document, config) == ()


def test_eoc102_does_not_modify_the_document(config: RuleConfig) -> None:
    document = make_document(data_processing=DataProcessing.MODELED)
    before = document.to_dict()

    OBSERVATION_PROCESSING.check(document, config)

    assert document.to_dict() == before


# --------------------------------------------------------------------------
# EOC103
# --------------------------------------------------------------------------


def _interpretation(**claim_kwargs: object) -> ClaimValue:
    base: dict[str, object] = {
        "type": ClaimType.INTERPRETATION,
        "statement": "The example series is read as showing an increase.",
        "value": "increasing",
    }
    base.update(claim_kwargs)
    return ClaimValue(**base)  # type: ignore[arg-type]


def test_eoc103_metadata() -> None:
    assert INTERPRETATION_QUALIFICATION.rule_id == "EOC103"
    assert INTERPRETATION_QUALIFICATION.default_severity is Severity.WARNING


def test_eoc103_fires_on_a_bare_interpretation(config: RuleConfig) -> None:
    document = make_document(claim=_interpretation())

    issues = INTERPRETATION_QUALIFICATION.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC103"
    assert issues[0].path == "$.claim"
    assert issues[0].field == "uncertainty"


def test_eoc103_is_satisfied_by_an_uncertainty(config: RuleConfig) -> None:
    document = make_document(
        claim=_interpretation(
            uncertainty=Uncertainty(
                kind=UncertaintyKind.QUALITATIVE, description="The magnitude is not established."
            )
        )
    )

    assert INTERPRETATION_QUALIFICATION.check(document, config) == ()


def test_eoc103_is_satisfied_by_a_disclaimer(config: RuleConfig) -> None:
    document = make_document(
        claim=_interpretation(),
        display=DisplayInfo(label="Interpreted trend", disclaimer="An interpretation."),
    )

    assert INTERPRETATION_QUALIFICATION.check(document, config) == ()


def test_eoc103_treats_a_blank_disclaimer_as_absent(config: RuleConfig) -> None:
    document = make_document(
        claim=_interpretation(), display=DisplayInfo(label="Interpreted trend", disclaimer="   ")
    )

    assert INTERPRETATION_QUALIFICATION.check(document, config)


def test_eoc103_ignores_observations_and_estimates(config: RuleConfig) -> None:
    assert INTERPRETATION_QUALIFICATION.check(make_document(), config) == ()
