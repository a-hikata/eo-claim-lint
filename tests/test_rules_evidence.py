"""Tests for EOC301."""

from __future__ import annotations

import pytest

from eo_claim_lint import (
    ClaimType,
    ClaimValue,
    EvidenceReference,
    EvidenceType,
    RuleConfig,
    Severity,
    Uncertainty,
    UncertaintyKind,
)
from eo_claim_lint.rules.evidence import MissingEvidenceRule
from tests.conftest import EXAMPLE_EVIDENCE, make_document

MISSING_EVIDENCE = MissingEvidenceRule()


def test_eoc301_metadata() -> None:
    assert MISSING_EVIDENCE.rule_id == "EOC301"
    assert MISSING_EVIDENCE.default_severity is Severity.ERROR


def test_eoc301_is_the_only_error_by_default() -> None:
    """Documented policy: an untraceable claim is the one finding that blocks."""
    from eo_claim_lint import get_default_rules

    errors = [
        rule.rule_id for rule in get_default_rules() if rule.default_severity is Severity.ERROR
    ]

    assert errors == ["EOC301"]


def test_eoc301_fires_on_an_empty_evidence_list(config: RuleConfig) -> None:
    document = make_document(evidence=())

    issues = MISSING_EVIDENCE.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC301"
    assert issues[0].severity is Severity.ERROR
    assert issues[0].path == "$"
    assert issues[0].field == "evidence"


def test_eoc301_is_silent_with_one_reference(config: RuleConfig) -> None:
    assert MISSING_EVIDENCE.check(make_document(), config) == ()


def test_eoc301_is_silent_with_several_references(config: RuleConfig) -> None:
    second = EvidenceReference(
        id="evidence-002",
        type=EvidenceType.URL,
        title="Example synthetic companion record",
        uri="urn:example:evidence:002",
    )
    document = make_document(evidence=(EXAMPLE_EVIDENCE, second))

    assert MISSING_EVIDENCE.check(document, config) == ()


@pytest.mark.parametrize(
    "claim_type", [ClaimType.OBSERVATION, ClaimType.ESTIMATE, ClaimType.INTERPRETATION]
)
def test_eoc301_applies_to_every_claim_type(claim_type: ClaimType, config: RuleConfig) -> None:
    """Interpretations are included on purpose: they are the least grounded."""
    document = make_document(
        claim=ClaimValue(
            type=claim_type,
            statement="An example statement.",
            uncertainty=Uncertainty(kind=UncertaintyKind.UNKNOWN),
        ),
        evidence=(),
    )

    issues = MISSING_EVIDENCE.check(document, config)

    assert len(issues) == 1
    assert issues[0].context["claim_type"] == claim_type.value


def test_eoc301_can_be_downgraded_by_configuration() -> None:
    document = make_document(evidence=())
    config = RuleConfig(severity_overrides={"EOC301": Severity.WARNING})

    assert MISSING_EVIDENCE.check(document, config)[0].severity is Severity.WARNING


def test_eoc301_does_not_modify_the_document(config: RuleConfig) -> None:
    document = make_document(evidence=())
    before = document.to_dict()

    MISSING_EVIDENCE.check(document, config)

    assert document.to_dict() == before
