"""Shared builders for rule tests.

Every rule test starts from a document that no rule objects to, then changes
exactly the one thing under test. That way a failing assertion points at the
change rather than at whatever else the fixture happened to contain.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from eo_claim_lint import (
    ClaimDocument,
    ClaimType,
    ClaimValue,
    DataOrigin,
    DataProcessing,
    DisplayInfo,
    EvidenceReference,
    EvidenceType,
    NamedAreaScope,
    ProcessingInfo,
    RuleConfig,
    TemporalScope,
)

EXAMPLE_EVIDENCE = EvidenceReference(
    id="evidence-001",
    type=EvidenceType.DATASET,
    title="Example synthetic source record",
    uri="urn:example:evidence:001",
)


def make_document(**overrides: object) -> ClaimDocument:
    """A document that every default rule passes, with fields replaceable."""
    base: dict[str, object] = {
        "claim_id": "claim-001",
        "claim": ClaimValue(
            type=ClaimType.OBSERVATION,
            statement="A value was computed for the specified area.",
            value=0.42,
            unit="1",
        ),
        "data_origin": DataOrigin.MEASURED,
        "data_processing": DataProcessing.DERIVED,
        "spatial_scope": NamedAreaScope(name="Example Area"),
        "temporal_scope": TemporalScope(observed_at=datetime(2026, 1, 15, 1, 30, tzinfo=UTC)),
        "evidence": (EXAMPLE_EVIDENCE,),
        "display": DisplayInfo(label="Value for the area"),
        "processing": ProcessingInfo(method="Example procedure"),
    }
    base.update(overrides)
    return ClaimDocument(**base)  # type: ignore[arg-type]


@pytest.fixture
def config() -> RuleConfig:
    return RuleConfig()


@pytest.fixture
def clean_document() -> ClaimDocument:
    return make_document()


@dataclass(frozen=True)
class CliRun:
    """What one in-process CLI invocation produced."""

    code: int
    stdout: str
    stderr: str


def run_cli(argv: Sequence[str]) -> CliRun:
    """Invoke the CLI in-process with captured streams."""
    from eo_claim_lint.cli import main

    out = io.StringIO()
    err = io.StringIO()
    code = main(list(argv), stdout=out, stderr=err)
    return CliRun(code, out.getvalue(), err.getvalue())
