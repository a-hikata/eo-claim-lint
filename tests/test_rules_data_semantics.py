"""Tests for EOC401 and EOC402."""

from __future__ import annotations

import pytest

from eo_claim_lint import DataOrigin, DisplayInfo, RuleConfig, Severity
from eo_claim_lint.rules.data_semantics import (
    SyntheticDisclosureRule,
    UnknownOriginDisclosureRule,
)
from tests.conftest import make_document

SYNTHETIC_DISCLOSURE = SyntheticDisclosureRule()
UNKNOWN_DISCLOSURE = UnknownOriginDisclosureRule()


# --------------------------------------------------------------------------
# EOC401
# --------------------------------------------------------------------------


def test_eoc401_metadata() -> None:
    assert SYNTHETIC_DISCLOSURE.rule_id == "EOC401"
    assert SYNTHETIC_DISCLOSURE.default_severity is Severity.WARNING


def test_eoc401_fires_on_undisclosed_synthetic_data(config: RuleConfig) -> None:
    document = make_document(data_origin=DataOrigin.SYNTHETIC)

    issues = SYNTHETIC_DISCLOSURE.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC401"
    assert issues[0].path == "$.display"
    assert issues[0].field == "disclaimer"
    assert issues[0].context["data_origin"] == "synthetic"


def test_eoc401_is_silent_when_a_disclaimer_is_present(config: RuleConfig) -> None:
    document = make_document(
        data_origin=DataOrigin.SYNTHETIC,
        display=DisplayInfo(label="Demonstration value", disclaimer="Generated, not recorded."),
    )

    assert SYNTHETIC_DISCLOSURE.check(document, config) == ()


def test_eoc401_treats_a_blank_disclaimer_as_absent(config: RuleConfig) -> None:
    document = make_document(
        data_origin=DataOrigin.SYNTHETIC,
        display=DisplayInfo(label="Demonstration value", disclaimer="  "),
    )

    assert SYNTHETIC_DISCLOSURE.check(document, config)


@pytest.mark.parametrize("origin", [DataOrigin.MEASURED, DataOrigin.UNKNOWN])
def test_eoc401_only_applies_to_synthetic_origin(origin: DataOrigin, config: RuleConfig) -> None:
    assert SYNTHETIC_DISCLOSURE.check(make_document(data_origin=origin), config) == ()


def test_eoc401_does_not_call_synthetic_data_wrong(config: RuleConfig) -> None:
    """Synthetic is a legitimate origin; the rule asks for disclosure, not apology."""
    message = SYNTHETIC_DISCLOSURE.check(make_document(data_origin=DataOrigin.SYNTHETIC), config)[
        0
    ].message

    assert "legitimate" in message
    for word in ("false", "fake", "invalid", "wrong"):
        assert word not in message.lower()


# --------------------------------------------------------------------------
# EOC402
# --------------------------------------------------------------------------


def test_eoc402_metadata() -> None:
    assert UNKNOWN_DISCLOSURE.rule_id == "EOC402"
    assert UNKNOWN_DISCLOSURE.default_severity is Severity.WARNING


def test_eoc402_fires_on_undisclosed_unknown_origin(config: RuleConfig) -> None:
    document = make_document(data_origin=DataOrigin.UNKNOWN)

    issues = UNKNOWN_DISCLOSURE.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC402"
    assert issues[0].field == "disclaimer"


def test_eoc402_is_silent_when_a_disclaimer_is_present(config: RuleConfig) -> None:
    document = make_document(
        data_origin=DataOrigin.UNKNOWN,
        display=DisplayInfo(label="Unattributed value", disclaimer="Origin not established."),
    )

    assert UNKNOWN_DISCLOSURE.check(document, config) == ()


@pytest.mark.parametrize("origin", [DataOrigin.MEASURED, DataOrigin.SYNTHETIC])
def test_eoc402_only_applies_to_unknown_origin(origin: DataOrigin, config: RuleConfig) -> None:
    assert UNKNOWN_DISCLOSURE.check(make_document(data_origin=origin), config) == ()


def test_the_two_disclosure_rules_never_fire_together(config: RuleConfig) -> None:
    """`data_origin` is a single enum, so the two conditions are mutually exclusive."""
    for origin in DataOrigin:
        document = make_document(data_origin=origin)
        fired = len(SYNTHETIC_DISCLOSURE.check(document, config)) + len(
            UNKNOWN_DISCLOSURE.check(document, config)
        )

        assert fired <= 1
