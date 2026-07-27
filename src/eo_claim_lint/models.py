"""Data model for claim documents and linter output.

The types here describe *what a document says about itself*: whether a number
is an observation or an estimate, where the data came from, how far it was
processed, what uncertainty was declared, and what evidence backs it.

They deliberately hold no domain rules. Whether a particular document *should*
declare uncertainty, or *should* carry evidence, is a linting decision and is
not encoded here — a document that omits either is still a well-formed
document. Keeping policy out of the model is what allows the same model to
describe documents from projects that disagree about policy.

Nothing in this module validates the truth of a claim. It validates that the
claim is internally consistent and machine-readable.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, StrEnum
from types import MappingProxyType
from typing import TypeVar

_E = TypeVar("_E", bound=Enum)

__all__ = [
    "BoundingBoxScope",
    "Checksum",
    "ClaimDocument",
    "ClaimType",
    "ClaimValue",
    "DataOrigin",
    "DataProcessing",
    "DisplayInfo",
    "EoClaimLintError",
    "EvidenceReference",
    "EvidenceType",
    "LintIssue",
    "LintResult",
    "NamedAreaScope",
    "ProcessingInfo",
    "Severity",
    "SpatialScope",
    "TemporalScope",
    "Uncertainty",
    "UncertaintyKind",
]

CLAIM_DOCUMENT_SCHEMA_VERSION = "0.1"
LINT_OUTPUT_SCHEMA_VERSION = "1.0"
TOOL_NAME = "eo-claim-lint"

RULE_ID_PATTERN = re.compile(r"^EOC[0-9]{3}$")


class EoClaimLintError(ValueError):
    """Raised when a document cannot be represented by this model.

    Messages name the offending field and never quote the document's values,
    so that an error surfacing in a log or a CI transcript cannot leak the
    contents of the document being checked.
    """


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------


class ClaimType(StrEnum):
    """What kind of statement is being made."""

    OBSERVATION = "observation"
    """Recorded by an instrument or supplied by a data source."""

    ESTIMATE = "estimate"
    """Produced by a model, an interpolation, or a statistical procedure."""

    INTERPRETATION = "interpretation"
    """A meaning assigned to an observation or an estimate."""


class DataOrigin(StrEnum):
    """Where the underlying data came from."""

    MEASURED = "measured"
    SYNTHETIC = "synthetic"
    UNKNOWN = "unknown"


class DataProcessing(StrEnum):
    """How far the underlying data has been transformed."""

    RAW = "raw"
    DERIVED = "derived"
    MODELED = "modeled"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    """How serious a linting issue is."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EvidenceType(StrEnum):
    """What kind of thing an evidence reference points at."""

    DATASET = "dataset"
    FILE = "file"
    URL = "url"
    RECORD = "record"
    OTHER = "other"


class UncertaintyKind(StrEnum):
    """How uncertainty is expressed."""

    INTERVAL = "interval"
    STANDARD_DEVIATION = "standard_deviation"
    QUALITATIVE = "qualitative"
    UNKNOWN = "unknown"


ClaimValueType = bool | int | float | str | None
"""The value a claim may carry. Arrays and nested objects are out of scope."""


# --------------------------------------------------------------------------
# Parsing helpers
#
# Every helper names the field it failed on and nothing else.
# --------------------------------------------------------------------------


def _require_mapping(raw: object, where: str) -> Mapping[str, object]:
    if not isinstance(raw, Mapping):
        raise EoClaimLintError(f"{where}: expected an object")
    for key in raw:
        if not isinstance(key, str):
            raise EoClaimLintError(f"{where}: object keys must be strings")
    return raw


def _reject_unknown(data: Mapping[str, object], allowed: frozenset[str], where: str) -> None:
    unexpected = sorted(set(data) - allowed)
    if unexpected:
        raise EoClaimLintError(f"{where}: unexpected field(s): {', '.join(unexpected)}")


def _get(data: Mapping[str, object], key: str) -> object | None:
    """Read a key, treating an explicit ``null`` as absent."""
    return data.get(key)


def _require_str(data: Mapping[str, object], key: str, where: str) -> str:
    value = _get(data, key)
    if value is None:
        raise EoClaimLintError(f"{where}.{key}: required field is missing")
    if not isinstance(value, str):
        raise EoClaimLintError(f"{where}.{key}: expected a string")
    return value


def _require_non_empty_str(data: Mapping[str, object], key: str, where: str) -> str:
    value = _require_str(data, key, where)
    if not value.strip():
        raise EoClaimLintError(f"{where}.{key}: must not be empty")
    return value


def _optional_str(data: Mapping[str, object], key: str, where: str) -> str | None:
    value = _get(data, key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise EoClaimLintError(f"{where}.{key}: expected a string or null")
    return value


def _optional_number(data: Mapping[str, object], key: str, where: str) -> float | None:
    value = _get(data, key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise EoClaimLintError(f"{where}.{key}: expected a number or null")
    return float(value)


def _require_enum(data: Mapping[str, object], key: str, where: str, enum_type: type[_E]) -> _E:
    value = _require_str(data, key, where)
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(str(member.value) for member in enum_type)
        raise EoClaimLintError(f"{where}.{key}: unknown value; expected one of {allowed}") from exc


def _require_sequence(data: Mapping[str, object], key: str, where: str) -> Sequence[object]:
    value = _get(data, key)
    if value is None:
        raise EoClaimLintError(f"{where}.{key}: required field is missing")
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise EoClaimLintError(f"{where}.{key}: expected an array")
    return value


def _parse_datetime(raw: object, where: str) -> datetime:
    if not isinstance(raw, str):
        raise EoClaimLintError(f"{where}: expected an RFC 3339 date-time string")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise EoClaimLintError(f"{where}: not a valid RFC 3339 date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EoClaimLintError(f"{where}: date-time must carry a timezone offset")
    return parsed


def _format_datetime(value: datetime) -> str:
    text = value.isoformat()
    if text.endswith("+00:00"):
        return f"{text[:-6]}Z"
    return text


def _freeze_mapping(raw: object, where: str) -> Mapping[str, object] | None:
    if raw is None:
        return None
    mapping = _require_mapping(raw, where)
    return MappingProxyType(dict(mapping))


def _put(target: dict[str, object], key: str, value: object) -> None:
    """Write a key only when the value is present.

    Optional fields are omitted rather than serialised as ``null``, so that a
    round trip through :meth:`to_dict` is stable.
    """
    if value is not None:
        target[key] = value


# --------------------------------------------------------------------------
# Uncertainty
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Uncertainty:
    """A declared uncertainty about a claimed value.

    One class covers all four kinds, with ``kind`` acting as the discriminator.
    Which fields are required depends on the kind and is checked on
    construction.
    """

    kind: UncertaintyKind
    lower: float | None = None
    upper: float | None = None
    value: float | None = None
    unit: str | None = None
    confidence: float | None = None
    description: str | None = None

    _FIELDS = frozenset({"kind", "lower", "upper", "value", "unit", "confidence", "description"})

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise EoClaimLintError("uncertainty.confidence: must be between 0 and 1 inclusive")

        if self.kind is UncertaintyKind.INTERVAL:
            if self.lower is None or self.upper is None:
                raise EoClaimLintError("uncertainty: an interval requires both 'lower' and 'upper'")
            if self.lower > self.upper:
                raise EoClaimLintError("uncertainty: 'lower' must not exceed 'upper'")
        elif self.kind is UncertaintyKind.STANDARD_DEVIATION:
            if self.value is None:
                raise EoClaimLintError("uncertainty: a standard deviation requires 'value'")
            if self.value < 0:
                raise EoClaimLintError(
                    "uncertainty.value: a standard deviation must not be negative"
                )
        elif self.kind is UncertaintyKind.QUALITATIVE and not (self.description or "").strip():
            raise EoClaimLintError("uncertainty: a qualitative uncertainty requires 'description'")

    @classmethod
    def from_dict(cls, raw: object, where: str = "uncertainty") -> Uncertainty:
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)
        return cls(
            kind=_require_enum(data, "kind", where, UncertaintyKind),
            lower=_optional_number(data, "lower", where),
            upper=_optional_number(data, "upper", where),
            value=_optional_number(data, "value", where),
            unit=_optional_str(data, "unit", where),
            confidence=_optional_number(data, "confidence", where),
            description=_optional_str(data, "description", where),
        )

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {"kind": self.kind.value}
        _put(out, "lower", self.lower)
        _put(out, "upper", self.upper)
        _put(out, "value", self.value)
        _put(out, "unit", self.unit)
        _put(out, "confidence", self.confidence)
        _put(out, "description", self.description)
        return out


# --------------------------------------------------------------------------
# Claim
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ClaimValue:
    """The statement being made, and the value it carries."""

    type: ClaimType
    statement: str
    value: ClaimValueType = None
    unit: str | None = None
    uncertainty: Uncertainty | None = None

    _FIELDS = frozenset({"type", "statement", "value", "unit", "uncertainty"})

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise EoClaimLintError("claim.statement: must not be empty")

    @classmethod
    def from_dict(cls, raw: object, where: str = "claim") -> ClaimValue:
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)

        value = _get(data, "value")
        if value is not None and not isinstance(value, bool | int | float | str):
            raise EoClaimLintError(f"{where}.value: expected a number, string, boolean, or null")

        raw_uncertainty = _get(data, "uncertainty")
        return cls(
            type=_require_enum(data, "type", where, ClaimType),
            statement=_require_non_empty_str(data, "statement", where),
            value=value,
            unit=_optional_str(data, "unit", where),
            uncertainty=(
                None
                if raw_uncertainty is None
                else Uncertainty.from_dict(raw_uncertainty, f"{where}.uncertainty")
            ),
        )

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {"type": self.type.value, "statement": self.statement}
        _put(out, "value", self.value)
        _put(out, "unit", self.unit)
        if self.uncertainty is not None:
            out["uncertainty"] = self.uncertainty.to_dict()
        return out


# --------------------------------------------------------------------------
# Spatial scope
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class NamedAreaScope:
    """An area identified by name rather than by geometry."""

    name: str

    _FIELDS = frozenset({"type", "name"})
    TYPE = "named_area"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise EoClaimLintError("spatial_scope.name: must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {"type": self.TYPE, "name": self.name}


@dataclass(frozen=True)
class BoundingBoxScope:
    """An axis-aligned bounding box, in the order west, south, east, north."""

    bbox: tuple[float, float, float, float]
    crs: str = "EPSG:4326"

    _FIELDS = frozenset({"type", "bbox", "crs"})
    TYPE = "bbox"

    def __post_init__(self) -> None:
        west, south, east, north = self.bbox
        if west > east:
            raise EoClaimLintError("spatial_scope.bbox: west must not exceed east")
        if south > north:
            raise EoClaimLintError("spatial_scope.bbox: south must not exceed north")
        if not self.crs.strip():
            raise EoClaimLintError("spatial_scope.crs: must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {"type": self.TYPE, "bbox": list(self.bbox), "crs": self.crs}


SpatialScope = NamedAreaScope | BoundingBoxScope


def _spatial_scope_from_dict(raw: object, where: str = "spatial_scope") -> SpatialScope:
    data = _require_mapping(raw, where)
    kind = _require_str(data, "type", where)

    if kind == NamedAreaScope.TYPE:
        _reject_unknown(data, NamedAreaScope._FIELDS, where)
        return NamedAreaScope(name=_require_non_empty_str(data, "name", where))

    if kind == BoundingBoxScope.TYPE:
        _reject_unknown(data, BoundingBoxScope._FIELDS, where)
        values = _require_sequence(data, "bbox", where)
        if len(values) != 4:
            raise EoClaimLintError(f"{where}.bbox: expected exactly 4 numbers")
        numbers: list[float] = []
        for item in values:
            if isinstance(item, bool) or not isinstance(item, int | float):
                raise EoClaimLintError(f"{where}.bbox: every element must be a number")
            numbers.append(float(item))
        crs = _optional_str(data, "crs", where)
        return BoundingBoxScope(
            bbox=(numbers[0], numbers[1], numbers[2], numbers[3]),
            crs="EPSG:4326" if crs is None else crs,
        )

    raise EoClaimLintError(
        f"{where}.type: unknown value; expected one of "
        f"{NamedAreaScope.TYPE}, {BoundingBoxScope.TYPE}"
    )


# --------------------------------------------------------------------------
# Temporal scope
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TemporalScope:
    """Either a single instant or a period, never both."""

    observed_at: datetime | None = None
    start: datetime | None = None
    end: datetime | None = None

    _FIELDS = frozenset({"observed_at", "start", "end"})

    def __post_init__(self) -> None:
        has_instant = self.observed_at is not None
        has_period = self.start is not None or self.end is not None

        if has_instant and has_period:
            raise EoClaimLintError(
                "temporal_scope: 'observed_at' and a start/end period are mutually exclusive"
            )
        if not has_instant and not has_period:
            raise EoClaimLintError(
                "temporal_scope: requires either 'observed_at' or both 'start' and 'end'"
            )
        if has_period:
            if self.start is None or self.end is None:
                raise EoClaimLintError("temporal_scope: a period requires both 'start' and 'end'")
            if self.start > self.end:
                raise EoClaimLintError("temporal_scope: 'start' must not be later than 'end'")

    @classmethod
    def from_dict(cls, raw: object, where: str = "temporal_scope") -> TemporalScope:
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)

        def _read(key: str) -> datetime | None:
            value = _get(data, key)
            return None if value is None else _parse_datetime(value, f"{where}.{key}")

        return cls(observed_at=_read("observed_at"), start=_read("start"), end=_read("end"))

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {}
        if self.observed_at is not None:
            out["observed_at"] = _format_datetime(self.observed_at)
        if self.start is not None:
            out["start"] = _format_datetime(self.start)
        if self.end is not None:
            out["end"] = _format_datetime(self.end)
        return out


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Checksum:
    """A recorded digest of an evidence artifact.

    Neither the algorithm nor the digest is verified against anything. This
    records what the document claims; it establishes no authenticity.
    """

    algorithm: str
    value: str

    _FIELDS = frozenset({"algorithm", "value"})

    def __post_init__(self) -> None:
        if not self.algorithm.strip():
            raise EoClaimLintError("checksum.algorithm: must not be empty")
        if not self.value.strip():
            raise EoClaimLintError("checksum.value: must not be empty")

    @classmethod
    def from_dict(cls, raw: object, where: str = "checksum") -> Checksum:
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)
        return cls(
            algorithm=_require_non_empty_str(data, "algorithm", where),
            value=_require_non_empty_str(data, "value", where),
        )

    def to_dict(self) -> dict[str, object]:
        return {"algorithm": self.algorithm, "value": self.value}


@dataclass(frozen=True)
class EvidenceReference:
    """A pointer to something that backs the claim."""

    id: str
    type: EvidenceType
    title: str
    uri: str
    checksum: Checksum | None = None
    media_type: str | None = None
    observed_at: datetime | None = None
    license: str | None = None

    _FIELDS = frozenset(
        {"id", "type", "title", "uri", "checksum", "media_type", "observed_at", "license"}
    )

    def __post_init__(self) -> None:
        for name, value in (("id", self.id), ("title", self.title), ("uri", self.uri)):
            if not value.strip():
                raise EoClaimLintError(f"evidence.{name}: must not be empty")

    @classmethod
    def from_dict(cls, raw: object, where: str = "evidence") -> EvidenceReference:
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)
        raw_checksum = _get(data, "checksum")
        raw_observed_at = _get(data, "observed_at")
        return cls(
            id=_require_non_empty_str(data, "id", where),
            type=_require_enum(data, "type", where, EvidenceType),
            title=_require_non_empty_str(data, "title", where),
            uri=_require_non_empty_str(data, "uri", where),
            checksum=(
                None
                if raw_checksum is None
                else Checksum.from_dict(raw_checksum, f"{where}.checksum")
            ),
            media_type=_optional_str(data, "media_type", where),
            observed_at=(
                None
                if raw_observed_at is None
                else _parse_datetime(raw_observed_at, f"{where}.observed_at")
            ),
            license=_optional_str(data, "license", where),
        )

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "uri": self.uri,
        }
        if self.checksum is not None:
            out["checksum"] = self.checksum.to_dict()
        _put(out, "media_type", self.media_type)
        if self.observed_at is not None:
            out["observed_at"] = _format_datetime(self.observed_at)
        _put(out, "license", self.license)
        return out


# --------------------------------------------------------------------------
# Display and processing
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DisplayInfo:
    """What a reader is shown."""

    label: str
    disclaimer: str | None = None
    display_value: str | None = None
    display_unit: str | None = None

    _FIELDS = frozenset({"label", "disclaimer", "display_value", "display_unit"})

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise EoClaimLintError("display.label: must not be empty")

    @classmethod
    def from_dict(cls, raw: object, where: str = "display") -> DisplayInfo:
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)
        return cls(
            label=_require_non_empty_str(data, "label", where),
            disclaimer=_optional_str(data, "disclaimer", where),
            display_value=_optional_str(data, "display_value", where),
            display_unit=_optional_str(data, "display_unit", where),
        )

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {"label": self.label}
        _put(out, "disclaimer", self.disclaimer)
        _put(out, "display_value", self.display_value)
        _put(out, "display_unit", self.display_unit)
        return out


@dataclass(frozen=True)
class ProcessingInfo:
    """How the claimed value was produced.

    ``parameters`` is a free-form JSON object. It is written into published
    artifacts, so it must never carry credentials, tokens, passwords, or
    personal data.
    """

    method: str
    software: str | None = None
    software_version: str | None = None
    parameters: Mapping[str, object] | None = None
    workflow_uri: str | None = None

    _FIELDS = frozenset({"method", "software", "software_version", "parameters", "workflow_uri"})

    def __post_init__(self) -> None:
        if not self.method.strip():
            raise EoClaimLintError("processing.method: must not be empty")
        if self.parameters is not None:
            object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    @classmethod
    def from_dict(cls, raw: object, where: str = "processing") -> ProcessingInfo:
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)
        return cls(
            method=_require_non_empty_str(data, "method", where),
            software=_optional_str(data, "software", where),
            software_version=_optional_str(data, "software_version", where),
            parameters=_freeze_mapping(_get(data, "parameters"), f"{where}.parameters"),
            workflow_uri=_optional_str(data, "workflow_uri", where),
        )

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {"method": self.method}
        _put(out, "software", self.software)
        _put(out, "software_version", self.software_version)
        if self.parameters is not None:
            out["parameters"] = dict(self.parameters)
        _put(out, "workflow_uri", self.workflow_uri)
        return out


# --------------------------------------------------------------------------
# Claim document
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ClaimDocument:
    """One claim, with everything needed to tell what kind of claim it is."""

    claim_id: str
    claim: ClaimValue
    data_origin: DataOrigin
    data_processing: DataProcessing
    spatial_scope: SpatialScope
    temporal_scope: TemporalScope
    display: DisplayInfo
    processing: ProcessingInfo
    evidence: tuple[EvidenceReference, ...] = ()
    schema_version: str = CLAIM_DOCUMENT_SCHEMA_VERSION

    _FIELDS = frozenset(
        {
            "schema_version",
            "claim_id",
            "claim",
            "data_origin",
            "data_processing",
            "spatial_scope",
            "temporal_scope",
            "evidence",
            "display",
            "processing",
        }
    )

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise EoClaimLintError("claim_id: must not be empty")
        if self.schema_version != CLAIM_DOCUMENT_SCHEMA_VERSION:
            raise EoClaimLintError(f"schema_version: expected '{CLAIM_DOCUMENT_SCHEMA_VERSION}'")

    @classmethod
    def from_dict(cls, raw: object, where: str = "document") -> ClaimDocument:
        """Build a document from a JSON-compatible mapping.

        Unknown fields are rejected rather than ignored: a field this model
        does not understand is more likely a typo or a version mismatch than a
        deliberate extension, and silently dropping it would hide both.
        """
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)

        evidence_items = _require_sequence(data, "evidence", where)
        evidence = tuple(
            EvidenceReference.from_dict(item, f"{where}.evidence[{index}]")
            for index, item in enumerate(evidence_items)
        )

        return cls(
            schema_version=_require_str(data, "schema_version", where),
            claim_id=_require_non_empty_str(data, "claim_id", where),
            claim=ClaimValue.from_dict(_get(data, "claim"), f"{where}.claim"),
            data_origin=_require_enum(data, "data_origin", where, DataOrigin),
            data_processing=_require_enum(data, "data_processing", where, DataProcessing),
            spatial_scope=_spatial_scope_from_dict(
                _get(data, "spatial_scope"), f"{where}.spatial_scope"
            ),
            temporal_scope=TemporalScope.from_dict(
                _get(data, "temporal_scope"), f"{where}.temporal_scope"
            ),
            evidence=evidence,
            display=DisplayInfo.from_dict(_get(data, "display"), f"{where}.display"),
            processing=ProcessingInfo.from_dict(_get(data, "processing"), f"{where}.processing"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "claim": self.claim.to_dict(),
            "data_origin": self.data_origin.value,
            "data_processing": self.data_processing.value,
            "spatial_scope": self.spatial_scope.to_dict(),
            "temporal_scope": self.temporal_scope.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "display": self.display.to_dict(),
            "processing": self.processing.to_dict(),
        }


# --------------------------------------------------------------------------
# Linter output
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LintIssue:
    """One finding about one document."""

    rule_id: str
    severity: Severity
    message: str
    path: str
    field: str | None = None
    doc_url: str | None = None
    # `dataclasses.field` is spelled out because this class has a member called
    # `field`, which shadows the bare name inside the class body.
    context: Mapping[str, object] = dataclasses.field(default_factory=dict)

    _FIELDS = frozenset({"rule_id", "severity", "message", "path", "field", "doc_url", "context"})

    def __post_init__(self) -> None:
        if not RULE_ID_PATTERN.match(self.rule_id):
            raise EoClaimLintError("rule_id: must match EOC followed by three digits")
        if not self.message.strip():
            raise EoClaimLintError("message: must not be empty")
        if not self.path.strip():
            raise EoClaimLintError("path: must not be empty")
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))

    @classmethod
    def from_dict(cls, raw: object, where: str = "issue") -> LintIssue:
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)
        context = _freeze_mapping(_get(data, "context"), f"{where}.context")
        return cls(
            rule_id=_require_non_empty_str(data, "rule_id", where),
            severity=_require_enum(data, "severity", where, Severity),
            message=_require_non_empty_str(data, "message", where),
            path=_require_non_empty_str(data, "path", where),
            field=_optional_str(data, "field", where),
            doc_url=_optional_str(data, "doc_url", where),
            context={} if context is None else context,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "path": self.path,
            "field": self.field,
            "doc_url": self.doc_url,
            "context": dict(self.context),
        }


def _tool_version() -> str:
    # Imported lazily so that this module does not import its own package.
    from eo_claim_lint import __version__

    return __version__


@dataclass(frozen=True)
class LintResult:
    """The findings for one linting run.

    ``valid`` is derived from the issues, never stored and never accepted from
    input. A report cannot claim to be valid while carrying an error, because
    there is no way to express that combination.
    """

    issues: tuple[LintIssue, ...] = ()
    schema_version: str = LINT_OUTPUT_SCHEMA_VERSION

    _FIELDS = frozenset({"schema_version", "tool", "valid", "issues"})

    def __post_init__(self) -> None:
        if self.schema_version != LINT_OUTPUT_SCHEMA_VERSION:
            raise EoClaimLintError(f"schema_version: expected '{LINT_OUTPUT_SCHEMA_VERSION}'")

    @property
    def valid(self) -> bool:
        """True when no issue has error severity."""
        return not any(issue.severity is Severity.ERROR for issue in self.issues)

    def by_severity(self, severity: Severity) -> tuple[LintIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is severity)

    @classmethod
    def from_dict(cls, raw: object, where: str = "report") -> LintResult:
        """Build a report from a JSON-compatible mapping.

        ``tool`` and ``valid`` are accepted but ignored: both are derived on
        output, so honouring an incoming value would let a report assert
        something its own issues contradict.
        """
        data = _require_mapping(raw, where)
        _reject_unknown(data, cls._FIELDS, where)
        items = _require_sequence(data, "issues", where)
        return cls(
            schema_version=_require_str(data, "schema_version", where),
            issues=tuple(
                LintIssue.from_dict(item, f"{where}.issues[{index}]")
                for index, item in enumerate(items)
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "tool": {"name": TOOL_NAME, "version": _tool_version()},
            "valid": self.valid,
            "issues": [issue.to_dict() for issue in self.issues],
        }
