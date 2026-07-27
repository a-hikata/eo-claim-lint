"""Tests for EOC302."""

from __future__ import annotations

import pytest

from eo_claim_lint import DataProcessing, ProcessingInfo, RuleConfig, Severity
from eo_claim_lint.rules.provenance import ModeledSoftwareRule
from tests.conftest import make_document

MODELED_SOFTWARE = ModeledSoftwareRule()


def test_eoc302_metadata() -> None:
    assert MODELED_SOFTWARE.rule_id == "EOC302"
    assert MODELED_SOFTWARE.default_severity is Severity.WARNING


def test_eoc302_fires_on_modeled_data_without_software(config: RuleConfig) -> None:
    document = make_document(data_processing=DataProcessing.MODELED)

    issues = MODELED_SOFTWARE.check(document, config)

    assert len(issues) == 1
    assert issues[0].rule_id == "EOC302"
    assert issues[0].path == "$.processing"
    assert issues[0].field == "software"


def test_eoc302_is_satisfied_by_a_software_name(config: RuleConfig) -> None:
    document = make_document(
        data_processing=DataProcessing.MODELED,
        processing=ProcessingInfo(method="Example estimator", software="example-estimator"),
    )

    assert MODELED_SOFTWARE.check(document, config) == ()


def test_eoc302_is_satisfied_by_a_version_alone(config: RuleConfig) -> None:
    """A one-off script may have a version and no published name."""
    document = make_document(
        data_processing=DataProcessing.MODELED,
        processing=ProcessingInfo(method="Example estimator", software_version="1.0.0"),
    )

    assert MODELED_SOFTWARE.check(document, config) == ()


def test_eoc302_treats_blank_software_as_absent(config: RuleConfig) -> None:
    document = make_document(
        data_processing=DataProcessing.MODELED,
        processing=ProcessingInfo(method="Example estimator", software="   "),
    )

    assert MODELED_SOFTWARE.check(document, config)


@pytest.mark.parametrize(
    "processing", [DataProcessing.RAW, DataProcessing.DERIVED, DataProcessing.UNKNOWN]
)
def test_eoc302_only_applies_to_modeled_data(
    processing: DataProcessing, config: RuleConfig
) -> None:
    assert MODELED_SOFTWARE.check(make_document(data_processing=processing), config) == ()


def test_eoc302_does_not_duplicate_the_schema_check_on_method(config: RuleConfig) -> None:
    """`method` is already required and non-empty by schema; this rule ignores it."""
    document = make_document(
        data_processing=DataProcessing.MODELED,
        processing=ProcessingInfo(method="Example estimator", software="example-estimator"),
    )

    assert MODELED_SOFTWARE.check(document, config) == ()


def test_eoc302_does_not_modify_the_document(config: RuleConfig) -> None:
    document = make_document(data_processing=DataProcessing.MODELED)
    before = document.to_dict()

    MODELED_SOFTWARE.check(document, config)

    assert document.to_dict() == before
