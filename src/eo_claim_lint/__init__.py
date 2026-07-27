"""eo-claim-lint — a linter for Earth observation claim documents.

This package checks whether a published claim derived from Earth observation
data keeps measurements and estimates distinguishable, declares uncertainty,
and carries the evidence needed to trace where the numbers came from.

It does not recompute or scientifically validate the numbers themselves.

Status: early development. The data model and the JSON Schemas exist; the
rule engine, the CLI, and the GitHub Action do not. See README.md.
"""

from importlib.metadata import PackageNotFoundError, version

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
    SpatialScope,
    TemporalScope,
    Uncertainty,
    UncertaintyKind,
)
from eo_claim_lint.schema import (
    CLAIM_DOCUMENT_SCHEMA_ID,
    LINT_OUTPUT_SCHEMA_ID,
    load_claim_document_schema,
    load_lint_output_schema,
)

__all__ = [
    "CLAIM_DOCUMENT_SCHEMA_ID",
    "LINT_OUTPUT_SCHEMA_ID",
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
    "__version__",
    "load_claim_document_schema",
    "load_lint_output_schema",
]

try:
    __version__ = version("eo-claim-lint")
except PackageNotFoundError:  # pragma: no cover - only when running from a source tree
    __version__ = "0.0.0+unknown"
