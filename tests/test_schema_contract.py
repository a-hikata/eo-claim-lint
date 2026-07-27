"""Tests that the schemas, the model, and the fixtures agree with each other.

Three things have to stay in step: what the JSON Schema accepts, what the
Python model accepts, and what the fixtures demonstrate. Where the two
validators deliberately differ, the difference is written down here rather
than left to be discovered.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest
from jsonschema import Draft202012Validator

from eo_claim_lint import (
    ClaimDocument,
    ClaimType,
    ClaimValue,
    DataOrigin,
    DataProcessing,
    DisplayInfo,
    EoClaimLintError,
    EvidenceReference,
    EvidenceType,
    LintIssue,
    LintResult,
    NamedAreaScope,
    ProcessingInfo,
    Severity,
    TemporalScope,
    load_claim_document_schema,
    load_lint_output_schema,
)

FIXTURES: Final = Path(__file__).resolve().parent / "fixtures"

# `lower <= upper` compares two sibling values, which Draft 2020-12 has no
# vocabulary for. The constraint lives in the Python model instead. Listing the
# exception here keeps the boundary between the two validators explicit: if a
# future schema change closes the gap, the test below starts failing and this
# entry has to be removed deliberately.
MODEL_ONLY_REJECTIONS: Final = frozenset({"reversed-interval.json"})

EXPECTED_VALID: Final = frozenset(
    {
        "measured-raw.json",
        "measured-derived.json",
        "synthetic-modeled.json",
        "unknown-minimal.json",
        "estimate-with-interval-uncertainty.json",
        "interpretation-with-qualitative-uncertainty.json",
        "bbox-period.json",
    }
)

EXPECTED_INVALID: Final = frozenset(
    {
        "missing-claim-id.json",
        "invalid-claim-type.json",
        "invalid-data-origin.json",
        "invalid-data-processing.json",
        "invalid-datetime.json",
        "temporal-point-and-period.json",
        "invalid-bbox-length.json",
        "reversed-interval.json",
        "confidence-over-one.json",
        "unexpected-property.json",
    }
)

EXPECTED_LINT_INVALID: Final = frozenset(
    {
        "estimate-without-uncertainty.json",
        "interpretation-without-evidence.json",
        "measured-claim-with-estimate-label.json",
    }
)


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _files(directory: str) -> list[Path]:
    return sorted((FIXTURES / directory).glob("*.json"))


def _ids(paths: list[Path]) -> list[str]:
    return [path.name for path in paths]


def _claim_validator() -> Draft202012Validator:
    return Draft202012Validator(load_claim_document_schema())


def _errors(document: object) -> Iterator[str]:
    for error in _claim_validator().iter_errors(document):
        yield error.message


VALID_FILES: Final = _files("schema_valid")
INVALID_FILES: Final = _files("schema_invalid")
LINT_INVALID_FILES: Final = _files("lint_invalid")


# --------------------------------------------------------------------------
# The schemas themselves
# --------------------------------------------------------------------------


def test_claim_document_schema_is_a_valid_schema() -> None:
    Draft202012Validator.check_schema(load_claim_document_schema())


def test_lint_output_schema_is_a_valid_schema() -> None:
    Draft202012Validator.check_schema(load_lint_output_schema())


# --------------------------------------------------------------------------
# The fixture set itself
# --------------------------------------------------------------------------


def test_expected_fixtures_are_present() -> None:
    assert set(_ids(VALID_FILES)) == EXPECTED_VALID
    assert set(_ids(INVALID_FILES)) == EXPECTED_INVALID
    assert set(_ids(LINT_INVALID_FILES)) == EXPECTED_LINT_INVALID


# --------------------------------------------------------------------------
# schema_valid
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", VALID_FILES, ids=_ids(VALID_FILES))
def test_valid_fixture_passes_the_schema(path: Path) -> None:
    assert list(_errors(_load(path))) == []


@pytest.mark.parametrize("path", VALID_FILES, ids=_ids(VALID_FILES))
def test_valid_fixture_loads_into_the_model(path: Path) -> None:
    document = ClaimDocument.from_dict(_load(path))

    assert document.claim_id


@pytest.mark.parametrize("path", VALID_FILES, ids=_ids(VALID_FILES))
def test_model_output_still_passes_the_schema(path: Path) -> None:
    """Whatever the model emits must remain a valid document."""
    emitted = ClaimDocument.from_dict(_load(path)).to_dict()

    assert list(_errors(emitted)) == []


# --------------------------------------------------------------------------
# schema_invalid
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", INVALID_FILES, ids=_ids(INVALID_FILES))
def test_invalid_fixture_is_rejected_by_the_model(path: Path) -> None:
    """The model is the stricter of the two validators and must reject all of these."""
    with pytest.raises(EoClaimLintError):
        ClaimDocument.from_dict(_load(path))


@pytest.mark.parametrize("path", INVALID_FILES, ids=_ids(INVALID_FILES))
def test_invalid_fixture_is_rejected_by_the_expected_layer(path: Path) -> None:
    schema_errors = list(_errors(_load(path)))

    if path.name in MODEL_ONLY_REJECTIONS:
        assert schema_errors == [], (
            f"{path.name} is recorded as model-only, but the schema now rejects it; "
            "remove it from MODEL_ONLY_REJECTIONS"
        )
    else:
        assert schema_errors, f"{path.name} should be rejected by the schema"


# --------------------------------------------------------------------------
# lint_invalid
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", LINT_INVALID_FILES, ids=_ids(LINT_INVALID_FILES))
def test_lint_invalid_fixture_passes_the_schema(path: Path) -> None:
    """These are structurally fine. Only a rule can object to them."""
    assert list(_errors(_load(path))) == []


@pytest.mark.parametrize("path", LINT_INVALID_FILES, ids=_ids(LINT_INVALID_FILES))
def test_lint_invalid_fixture_loads_into_the_model(path: Path) -> None:
    assert ClaimDocument.from_dict(_load(path)).claim_id


# --------------------------------------------------------------------------
# Constructed objects against the schemas
# --------------------------------------------------------------------------


def test_constructed_document_passes_the_schema() -> None:
    document = ClaimDocument(
        claim_id="claim-001",
        claim=ClaimValue(
            type=ClaimType.OBSERVATION, statement="An example statement.", value=0.42, unit="1"
        ),
        data_origin=DataOrigin.MEASURED,
        data_processing=DataProcessing.DERIVED,
        spatial_scope=NamedAreaScope(name="Example Area"),
        temporal_scope=TemporalScope(observed_at=datetime(2026, 1, 15, 1, 30, tzinfo=UTC)),
        evidence=(
            EvidenceReference(
                id="evidence-001",
                type=EvidenceType.DATASET,
                title="Example synthetic record",
                uri="urn:example:evidence:001",
            ),
        ),
        display=DisplayInfo(label="Example label"),
        processing=ProcessingInfo(method="Example procedure"),
    )

    assert list(_errors(document.to_dict())) == []


def test_constructed_report_passes_the_schema() -> None:
    report = LintResult(
        issues=(
            LintIssue(
                rule_id="EOC101",
                severity=Severity.ERROR,
                message="An estimate must declare uncertainty.",
                path="$.claim",
                field="uncertainty",
            ),
        )
    )
    validator = Draft202012Validator(load_lint_output_schema())

    assert list(validator.iter_errors(report.to_dict())) == []


def test_empty_report_passes_the_schema() -> None:
    validator = Draft202012Validator(load_lint_output_schema())

    assert list(validator.iter_errors(LintResult().to_dict())) == []
