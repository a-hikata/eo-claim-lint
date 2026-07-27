"""Tests for loading the bundled JSON Schema documents."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Final

import pytest

from eo_claim_lint import (
    CLAIM_DOCUMENT_SCHEMA_ID,
    LINT_OUTPUT_SCHEMA_ID,
    load_claim_document_schema,
    load_lint_output_schema,
)

DRAFT_2020_12: Final = "https://json-schema.org/draft/2020-12/schema"

LOADERS: Final[list[tuple[Callable[[], dict[str, object]], str]]] = [
    (load_claim_document_schema, CLAIM_DOCUMENT_SCHEMA_ID),
    (load_lint_output_schema, LINT_OUTPUT_SCHEMA_ID),
]


def _iter_refs(node: object) -> list[str]:
    """Every ``$ref`` value anywhere in a schema."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_iter_refs(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_refs(item))
    return found


@pytest.mark.parametrize(("loader", "schema_id"), LOADERS)
def test_schema_loads_from_the_package(
    loader: Callable[[], dict[str, object]], schema_id: str
) -> None:
    schema = loader()

    assert isinstance(schema, dict)
    assert schema["$id"] == schema_id


@pytest.mark.parametrize(("loader", "schema_id"), LOADERS)
def test_schema_declares_draft_2020_12(
    loader: Callable[[], dict[str, object]], schema_id: str
) -> None:
    assert loader()["$schema"] == DRAFT_2020_12


@pytest.mark.parametrize(("loader", "schema_id"), LOADERS)
def test_schema_has_no_external_refs(
    loader: Callable[[], dict[str, object]], schema_id: str
) -> None:
    """A ``$ref`` that points outward would make validation need the network."""
    for ref in _iter_refs(loader()):
        assert ref.startswith("#"), f"external $ref found: {ref}"


@pytest.mark.parametrize(("loader", "schema_id"), LOADERS)
def test_each_call_returns_an_independent_object(
    loader: Callable[[], dict[str, object]], schema_id: str
) -> None:
    """Callers routinely mutate a schema before validating; one must not affect the next."""
    first = loader()
    first["$id"] = "mutated-by-the-caller"

    assert loader()["$id"] == schema_id


def test_loading_does_not_depend_on_the_working_directory(tmp_path: Path) -> None:
    program = "import eo_claim_lint as m; print(m.load_claim_document_schema()['$id'])"
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == CLAIM_DOCUMENT_SCHEMA_ID


def test_schema_files_are_valid_json() -> None:
    for loader, _ in LOADERS:
        json.dumps(loader())


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _built_artifacts(suffix: str) -> list[Path]:
    dist = _project_root() / "dist"
    return sorted(dist.glob(f"*{suffix}")) if dist.is_dir() else []


@pytest.mark.parametrize(
    "member",
    [
        "eo_claim_lint/py.typed",
        "eo_claim_lint/schemas/claim-document-0.1.schema.json",
        "eo_claim_lint/schemas/lint-output-1.0.schema.json",
    ],
)
def test_wheel_contains_data_files(member: str) -> None:
    wheels = _built_artifacts(".whl")
    if not wheels:
        pytest.skip("no wheel built; run `python -m build` first")

    with zipfile.ZipFile(wheels[-1]) as archive:
        assert member in archive.namelist()


@pytest.mark.parametrize(
    "member",
    [
        "src/eo_claim_lint/py.typed",
        "src/eo_claim_lint/schemas/claim-document-0.1.schema.json",
        "src/eo_claim_lint/schemas/lint-output-1.0.schema.json",
    ],
)
def test_sdist_contains_data_files(member: str) -> None:
    sdists = _built_artifacts(".tar.gz")
    if not sdists:
        pytest.skip("no sdist built; run `python -m build` first")

    with tarfile.open(sdists[-1]) as archive:
        names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}
        assert member in names
