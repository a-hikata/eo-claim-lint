"""Tests for EOC101 and EOC203."""

from __future__ import annotations

from eo_claim_lint import (
    ClaimType,
    ClaimValue,
    DisplayInfo,
    RuleConfig,
    Severity,
    Uncertainty,
    UncertaintyKind,
)
from eo_claim_lint.rules.uncertainty import DefinitiveWordingRule, EstimateUncertaintyRule
from tests.conftest import make_document

ESTIMATE_UNCERTAINTY = EstimateUncertaintyRule()
DEFINITIVE_WORDING = DefinitiveWordingRule()


def _estimate(**claim_kwargs: object) -> ClaimValue:
    base: dict[str, object] = {
        "type": ClaimType.ESTIMATE,
        "statement": "An example quantity was estimated.",
        "value": 0.55,
        "unit": "1",
    }
    base.update(claim_kwargs)
    return ClaimValue(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# EOC101
# --------------------------------------------------------------------------


def test_eoc101_metadata() -> None:
    assert ESTIMATE_UNCERTAINTY.rule_id == "EOC101"
    assert ESTIMATE_UNCERTAINTY.default_severity is Severity.WARNING


def test_eoc101_fires_on_an_estimate_without_uncertainty(config: RuleConfig) -> None:
    document = make_document(claim=_estimate())

    issues = ESTIMATE_UNCERTAINTY.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC101"
    assert issues[0].severity is Severity.WARNING
    assert issues[0].path == "$.claim"
    assert issues[0].field == "uncertainty"
    assert "estimate" in issues[0].message


def test_eoc101_is_silent_when_uncertainty_is_present(config: RuleConfig) -> None:
    uncertainty = Uncertainty(kind=UncertaintyKind.INTERVAL, lower=0.5, upper=0.6)
    document = make_document(claim=_estimate(uncertainty=uncertainty))

    assert ESTIMATE_UNCERTAINTY.check(document, config) == ()


def test_eoc101_accepts_an_explicitly_unknown_uncertainty(config: RuleConfig) -> None:
    """Saying 'we do not know' is a declaration; saying nothing is not."""
    document = make_document(claim=_estimate(uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN)))

    assert ESTIMATE_UNCERTAINTY.check(document, config) == ()


def test_eoc101_ignores_observations_and_interpretations(config: RuleConfig) -> None:
    for claim_type in (ClaimType.OBSERVATION, ClaimType.INTERPRETATION):
        document = make_document(
            claim=ClaimValue(type=claim_type, statement="An example statement.")
        )

        assert ESTIMATE_UNCERTAINTY.check(document, config) == ()


def test_eoc101_honours_a_severity_override() -> None:
    document = make_document(claim=_estimate())
    config = RuleConfig(severity_overrides={"EOC101": Severity.ERROR})

    assert ESTIMATE_UNCERTAINTY.check(document, config)[0].severity is Severity.ERROR


def test_eoc101_does_not_modify_the_document(config: RuleConfig) -> None:
    document = make_document(claim=_estimate())
    before = document.to_dict()

    ESTIMATE_UNCERTAINTY.check(document, config)

    assert document.to_dict() == before


def test_eoc101_is_deterministic(config: RuleConfig) -> None:
    document = make_document(claim=_estimate())

    first = ESTIMATE_UNCERTAINTY.check(document, config)
    second = ESTIMATE_UNCERTAINTY.check(document, config)

    assert first == second


# --------------------------------------------------------------------------
# EOC203
# --------------------------------------------------------------------------


def test_eoc203_metadata() -> None:
    assert DEFINITIVE_WORDING.rule_id == "EOC203"
    assert DEFINITIVE_WORDING.default_severity is Severity.WARNING


def test_eoc203_fires_on_a_definitive_label(config: RuleConfig) -> None:
    document = make_document(
        claim=_estimate(uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN)),
        display=DisplayInfo(label="Confirmed example quantity"),
    )

    issues = DEFINITIVE_WORDING.check(document, config)

    assert len(issues) == 1
    assert issues[0].path == "$.display"
    assert issues[0].field == "label"
    assert issues[0].context["term"] == "confirmed"


def test_eoc203_fires_on_a_definitive_statement(config: RuleConfig) -> None:
    document = make_document(
        claim=_estimate(
            statement="The quantity is exactly as reported.",
            uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN),
        )
    )

    issues = DEFINITIVE_WORDING.check(document, config)

    assert [issue.field for issue in issues] == ["statement"]


def test_eoc203_reports_both_places_when_both_offend(config: RuleConfig) -> None:
    document = make_document(
        claim=_estimate(
            statement="The quantity is proven.",
            uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN),
        ),
        display=DisplayInfo(label="Guaranteed example quantity"),
    )

    assert len(DEFINITIVE_WORDING.check(document, config)) == 2


def test_eoc203_is_silent_when_the_uncertainty_is_quantified(config: RuleConfig) -> None:
    document = make_document(
        claim=_estimate(
            uncertainty=Uncertainty(kind=UncertaintyKind.INTERVAL, lower=0.5, upper=0.6)
        ),
        display=DisplayInfo(label="Confirmed example quantity"),
    )

    assert DEFINITIVE_WORDING.check(document, config) == ()


def test_eoc203_is_silent_without_a_definitive_word(config: RuleConfig) -> None:
    document = make_document(
        claim=_estimate(uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN)),
        display=DisplayInfo(label="Example quantity"),
    )

    assert DEFINITIVE_WORDING.check(document, config) == ()


def test_eoc203_matches_whole_words_only(config: RuleConfig) -> None:
    """'uncertainly' contains 'certain' as a substring but is not the same word."""
    document = make_document(
        claim=_estimate(uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN)),
        display=DisplayInfo(label="Ascertainment of the example quantity"),
    )

    assert DEFINITIVE_WORDING.check(document, config) == ()


def test_eoc203_is_case_insensitive(config: RuleConfig) -> None:
    document = make_document(
        claim=_estimate(uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN)),
        display=DisplayInfo(label="PROVEN example quantity"),
    )

    assert DEFINITIVE_WORDING.check(document, config)
