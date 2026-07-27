"""Tests for the claim document and report data model."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta, timezone

import pytest

from eo_claim_lint.models import (
    BoundingBoxScope,
    Checksum,
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
    Uncertainty,
    UncertaintyKind,
)


def _document(**overrides: object) -> ClaimDocument:
    """A minimal well-formed document, with fields replaceable per test."""
    base: dict[str, object] = {
        "claim_id": "claim-001",
        "claim": ClaimValue(type=ClaimType.OBSERVATION, statement="An example statement."),
        "data_origin": DataOrigin.MEASURED,
        "data_processing": DataProcessing.RAW,
        "spatial_scope": NamedAreaScope(name="Example Area"),
        "temporal_scope": TemporalScope(observed_at=datetime(2026, 1, 15, 1, 30, tzinfo=UTC)),
        "display": DisplayInfo(label="Example label"),
        "processing": ProcessingInfo(method="Example procedure"),
    }
    base.update(overrides)
    return ClaimDocument(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------


def test_claim_type_values() -> None:
    assert [member.value for member in ClaimType] == [
        "observation",
        "estimate",
        "interpretation",
    ]


def test_prediction_is_not_a_claim_type() -> None:
    with pytest.raises(ValueError, match="prediction"):
        ClaimType("prediction")


def test_data_origin_values() -> None:
    assert [member.value for member in DataOrigin] == ["measured", "synthetic", "unknown"]


def test_data_processing_values() -> None:
    assert [member.value for member in DataProcessing] == [
        "raw",
        "derived",
        "modeled",
        "unknown",
    ]


def test_severity_values() -> None:
    assert [member.value for member in Severity] == ["info", "warning", "error"]


def test_evidence_type_values() -> None:
    assert [member.value for member in EvidenceType] == [
        "dataset",
        "file",
        "url",
        "record",
        "other",
    ]


def test_uncertainty_kind_values() -> None:
    assert [member.value for member in UncertaintyKind] == [
        "interval",
        "standard_deviation",
        "qualitative",
        "unknown",
    ]


def test_legacy_real_and_mock_vocabulary_is_gone() -> None:
    for legacy in ("real", "mock"):
        with pytest.raises(ValueError, match=legacy):
            DataOrigin(legacy)
        with pytest.raises(ValueError, match=legacy):
            DataProcessing(legacy)


# --------------------------------------------------------------------------
# Construction and immutability
# --------------------------------------------------------------------------


def test_document_construction() -> None:
    document = _document()

    assert document.schema_version == "0.1"
    assert document.claim_id == "claim-001"
    assert document.evidence == ()


def test_document_is_frozen() -> None:
    document = _document()

    with pytest.raises(dataclasses.FrozenInstanceError):
        document.claim_id = "claim-002"  # type: ignore[misc]


def test_empty_claim_id_is_rejected() -> None:
    with pytest.raises(EoClaimLintError, match="claim_id"):
        _document(claim_id="   ")


def test_unexpected_schema_version_is_rejected() -> None:
    with pytest.raises(EoClaimLintError, match="schema_version"):
        _document(schema_version="0.2")


def test_default_context_is_not_shared_between_issues() -> None:
    first = LintIssue(
        rule_id="EOC001", severity=Severity.ERROR, message="An example message.", path="$"
    )
    second = LintIssue(
        rule_id="EOC001", severity=Severity.ERROR, message="An example message.", path="$"
    )

    assert first.context == {}
    assert second.context == {}
    assert first.context is not second.context


def test_context_does_not_alias_the_caller_mapping() -> None:
    supplied: dict[str, object] = {"example": 1}
    issue = LintIssue(
        rule_id="EOC001",
        severity=Severity.ERROR,
        message="An example message.",
        path="$",
        context=supplied,
    )

    supplied["example"] = 2

    assert issue.context["example"] == 1


def test_processing_parameters_do_not_alias_the_caller_mapping() -> None:
    supplied: dict[str, object] = {"window_days": 10}
    processing = ProcessingInfo(method="Example procedure", parameters=supplied)

    supplied["window_days"] = 99

    assert processing.parameters is not None
    assert processing.parameters["window_days"] == 10


def test_rule_id_pattern_is_enforced() -> None:
    for bad in ("EOC1", "eoc001", "EOC0001", "XYZ001"):
        with pytest.raises(EoClaimLintError, match="rule_id"):
            LintIssue(rule_id=bad, severity=Severity.ERROR, message="An example message.", path="$")


# --------------------------------------------------------------------------
# Round trip
# --------------------------------------------------------------------------


def test_document_round_trip() -> None:
    document = _document(
        claim=ClaimValue(
            type=ClaimType.ESTIMATE,
            statement="An example estimate.",
            value=0.55,
            unit="1",
            uncertainty=Uncertainty(
                kind=UncertaintyKind.INTERVAL, lower=0.5, upper=0.6, confidence=0.9
            ),
        ),
        spatial_scope=BoundingBoxScope(bbox=(10.0, 10.0, 11.0, 11.0)),
        temporal_scope=TemporalScope(
            start=datetime(2026, 1, 1, tzinfo=UTC), end=datetime(2026, 1, 31, tzinfo=UTC)
        ),
        evidence=(
            EvidenceReference(
                id="evidence-001",
                type=EvidenceType.FILE,
                title="Example synthetic record",
                uri="urn:example:evidence:001",
                checksum=Checksum(algorithm="sha256", value="0" * 64),
                observed_at=datetime(2026, 2, 1, tzinfo=UTC),
            ),
        ),
        processing=ProcessingInfo(method="Example procedure", parameters={"window_days": 10}),
    )

    as_dict = document.to_dict()

    assert ClaimDocument.from_dict(as_dict) == document
    assert ClaimDocument.from_dict(as_dict).to_dict() == as_dict


def test_utc_datetimes_serialise_with_a_z_suffix() -> None:
    document = _document()

    temporal = document.to_dict()["temporal_scope"]

    assert temporal == {"observed_at": "2026-01-15T01:30:00Z"}


def test_non_utc_offsets_are_preserved() -> None:
    tokyo = timezone(timedelta(hours=9))
    document = _document(
        temporal_scope=TemporalScope(observed_at=datetime(2026, 1, 15, 10, 30, tzinfo=tokyo))
    )

    temporal = document.to_dict()["temporal_scope"]

    assert temporal == {"observed_at": "2026-01-15T10:30:00+09:00"}


def test_optional_fields_are_omitted_rather_than_serialised_as_null() -> None:
    payload = _document().to_dict()
    claim = payload["claim"]

    assert isinstance(claim, dict)
    assert "value" not in claim
    assert "unit" not in claim
    assert "uncertainty" not in claim


def test_explicit_null_is_read_as_absent() -> None:
    payload = _document().to_dict()
    display = payload["display"]
    assert isinstance(display, dict)
    display["disclaimer"] = None

    assert ClaimDocument.from_dict(payload).display.disclaimer is None


# --------------------------------------------------------------------------
# Parsing failures
# --------------------------------------------------------------------------


def test_unknown_enum_value_is_rejected() -> None:
    payload = _document().to_dict()
    payload["data_origin"] = "real"

    with pytest.raises(EoClaimLintError, match="data_origin"):
        ClaimDocument.from_dict(payload)


def test_missing_required_field_is_rejected() -> None:
    payload = _document().to_dict()
    del payload["claim_id"]

    with pytest.raises(EoClaimLintError, match="claim_id"):
        ClaimDocument.from_dict(payload)


def test_unknown_field_is_rejected_and_named() -> None:
    payload = _document().to_dict()
    payload["confidence_score"] = 0.99

    with pytest.raises(EoClaimLintError, match="confidence_score"):
        ClaimDocument.from_dict(payload)


def test_error_message_does_not_quote_the_document() -> None:
    payload = _document(claim_id="claim-secret-identifier").to_dict()
    payload["surprise"] = "a value that must not be echoed"

    with pytest.raises(EoClaimLintError) as caught:
        ClaimDocument.from_dict(payload)

    message = str(caught.value)
    assert "surprise" in message
    assert "a value that must not be echoed" not in message
    assert "claim-secret-identifier" not in message


def test_claim_value_rejects_nested_structures() -> None:
    payload = _document().to_dict()
    claim = payload["claim"]
    assert isinstance(claim, dict)
    claim["value"] = [1, 2, 3]

    with pytest.raises(EoClaimLintError, match="value"):
        ClaimDocument.from_dict(payload)


# --------------------------------------------------------------------------
# Temporal scope
# --------------------------------------------------------------------------


def test_naive_datetime_is_rejected() -> None:
    payload = _document().to_dict()
    payload["temporal_scope"] = {"observed_at": "2026-01-15T01:30:00"}

    with pytest.raises(EoClaimLintError, match="timezone"):
        ClaimDocument.from_dict(payload)


def test_instant_and_period_are_mutually_exclusive() -> None:
    with pytest.raises(EoClaimLintError, match="mutually exclusive"):
        TemporalScope(
            observed_at=datetime(2026, 1, 15, tzinfo=UTC),
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 1, 31, tzinfo=UTC),
        )


def test_temporal_scope_requires_one_of_the_two_forms() -> None:
    with pytest.raises(EoClaimLintError, match="temporal_scope"):
        TemporalScope()


def test_period_requires_both_ends() -> None:
    with pytest.raises(EoClaimLintError, match="both"):
        TemporalScope(start=datetime(2026, 1, 1, tzinfo=UTC))


def test_period_start_must_not_follow_end() -> None:
    with pytest.raises(EoClaimLintError, match="later than"):
        TemporalScope(start=datetime(2026, 1, 31, tzinfo=UTC), end=datetime(2026, 1, 1, tzinfo=UTC))


# --------------------------------------------------------------------------
# Spatial scope
# --------------------------------------------------------------------------


def test_bounding_box_defaults_to_wgs84() -> None:
    assert BoundingBoxScope(bbox=(10.0, 10.0, 11.0, 11.0)).crs == "EPSG:4326"


def test_bounding_box_rejects_reversed_longitude() -> None:
    with pytest.raises(EoClaimLintError, match="west"):
        BoundingBoxScope(bbox=(11.0, 10.0, 10.0, 11.0))


def test_bounding_box_rejects_reversed_latitude() -> None:
    with pytest.raises(EoClaimLintError, match="south"):
        BoundingBoxScope(bbox=(10.0, 11.0, 11.0, 10.0))


def test_bounding_box_requires_four_numbers() -> None:
    payload = _document().to_dict()
    payload["spatial_scope"] = {"type": "bbox", "bbox": [10.0, 10.0, 11.0]}

    with pytest.raises(EoClaimLintError, match="4 numbers"):
        ClaimDocument.from_dict(payload)


def test_unknown_spatial_scope_type_is_rejected() -> None:
    payload = _document().to_dict()
    payload["spatial_scope"] = {"type": "polygon", "name": "Example Area"}

    with pytest.raises(EoClaimLintError, match="spatial_scope.type"):
        ClaimDocument.from_dict(payload)


# --------------------------------------------------------------------------
# Uncertainty
# --------------------------------------------------------------------------


def test_interval_requires_both_bounds() -> None:
    with pytest.raises(EoClaimLintError, match="lower"):
        Uncertainty(kind=UncertaintyKind.INTERVAL, lower=0.1)


def test_interval_lower_must_not_exceed_upper() -> None:
    with pytest.raises(EoClaimLintError, match="exceed"):
        Uncertainty(kind=UncertaintyKind.INTERVAL, lower=0.9, upper=0.1)


def test_interval_may_be_a_single_point() -> None:
    assert Uncertainty(kind=UncertaintyKind.INTERVAL, lower=0.5, upper=0.5).lower == 0.5


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
def test_confidence_outside_the_unit_range_is_rejected(confidence: float) -> None:
    with pytest.raises(EoClaimLintError, match="confidence"):
        Uncertainty(kind=UncertaintyKind.UNKNOWN, confidence=confidence)


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_confidence_bounds_are_inclusive(confidence: float) -> None:
    assert Uncertainty(kind=UncertaintyKind.UNKNOWN, confidence=confidence).confidence == (
        confidence
    )


def test_standard_deviation_requires_a_value() -> None:
    with pytest.raises(EoClaimLintError, match="standard deviation"):
        Uncertainty(kind=UncertaintyKind.STANDARD_DEVIATION)


def test_standard_deviation_must_not_be_negative() -> None:
    with pytest.raises(EoClaimLintError, match="negative"):
        Uncertainty(kind=UncertaintyKind.STANDARD_DEVIATION, value=-1.0)


def test_qualitative_requires_a_description() -> None:
    with pytest.raises(EoClaimLintError, match="qualitative"):
        Uncertainty(kind=UncertaintyKind.QUALITATIVE, description="  ")


def test_unknown_uncertainty_needs_nothing() -> None:
    assert Uncertainty(kind=UncertaintyKind.UNKNOWN).description is None


def test_estimate_without_uncertainty_is_a_valid_document() -> None:
    """Whether an estimate must declare uncertainty is a rule, not a structure."""
    document = _document(
        claim=ClaimValue(type=ClaimType.ESTIMATE, statement="An example estimate.", value=0.55)
    )

    assert document.claim.uncertainty is None


# --------------------------------------------------------------------------
# Evidence, display, processing
# --------------------------------------------------------------------------


def test_evidence_reference_round_trip() -> None:
    reference = EvidenceReference(
        id="evidence-001",
        type=EvidenceType.DATASET,
        title="Example synthetic record",
        uri="urn:example:evidence:001",
        media_type="application/json",
        license="CC0-1.0",
    )

    assert EvidenceReference.from_dict(reference.to_dict()) == reference


def test_checksum_requires_both_parts() -> None:
    with pytest.raises(EoClaimLintError, match="algorithm"):
        Checksum(algorithm="", value="0" * 64)


def test_display_label_is_required() -> None:
    with pytest.raises(EoClaimLintError, match="display.label"):
        DisplayInfo(label="")


def test_processing_method_is_required() -> None:
    with pytest.raises(EoClaimLintError, match="processing.method"):
        ProcessingInfo(method="   ")


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _issue(severity: Severity, rule_id: str = "EOC001") -> LintIssue:
    return LintIssue(
        rule_id=rule_id, severity=severity, message="An example message.", path="$.claim"
    )


def test_empty_report_is_valid() -> None:
    assert LintResult().valid is True


def test_report_with_an_error_is_invalid() -> None:
    assert LintResult(issues=(_issue(Severity.ERROR),)).valid is False


def test_warnings_and_info_alone_leave_a_report_valid() -> None:
    result = LintResult(issues=(_issue(Severity.WARNING), _issue(Severity.INFO)))

    assert result.valid is True


def test_validity_cannot_be_asserted_against_the_issues() -> None:
    """A caller must not be able to hand in a 'valid' that the issues contradict."""
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "tool": {"name": "eo-claim-lint", "version": "9.9.9"},
        "valid": True,
        "issues": [_issue(Severity.ERROR).to_dict()],
    }

    assert LintResult.from_dict(payload).valid is False


def test_report_tool_identity_is_taken_from_this_package() -> None:
    from eo_claim_lint import __version__

    tool = LintResult().to_dict()["tool"]

    assert tool == {"name": "eo-claim-lint", "version": __version__}


def test_by_severity_selects_matching_issues() -> None:
    result = LintResult(issues=(_issue(Severity.ERROR), _issue(Severity.WARNING)))

    assert len(result.by_severity(Severity.ERROR)) == 1
    assert len(result.by_severity(Severity.INFO)) == 0


def test_report_round_trip() -> None:
    result = LintResult(
        issues=(
            LintIssue(
                rule_id="EOC101",
                severity=Severity.ERROR,
                message="An estimate must declare uncertainty.",
                path="$.claim",
                field="uncertainty",
                context={"claim_type": "estimate"},
            ),
        )
    )

    as_dict = result.to_dict()

    assert LintResult.from_dict(as_dict) == result
    assert LintResult.from_dict(as_dict).to_dict() == as_dict


def test_report_rejects_an_unknown_severity() -> None:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "tool": {"name": "eo-claim-lint", "version": "0.1.0"},
        "valid": False,
        "issues": [
            {
                "rule_id": "EOC001",
                "severity": "critical",
                "message": "An example message.",
                "path": "$",
                "field": None,
                "doc_url": None,
                "context": {},
            }
        ],
    }

    with pytest.raises(EoClaimLintError, match="severity"):
        LintResult.from_dict(payload)
