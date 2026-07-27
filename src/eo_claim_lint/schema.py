"""Access to the JSON Schema documents bundled with this package.

The schemas are read from package resources, so they resolve identically from
a source checkout and from an installed wheel, and do not depend on the
current working directory. Nothing here touches the network: the ``$id`` of
each schema is a canonical identifier, not a location that gets fetched.

Each call returns a fresh object. Callers routinely mutate a schema before
handing it to a validator, and a shared cached copy would let one caller's
edit change what the next caller sees.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Final

__all__ = [
    "CLAIM_DOCUMENT_SCHEMA_ID",
    "LINT_OUTPUT_SCHEMA_ID",
    "load_claim_document_schema",
    "load_lint_output_schema",
]

CLAIM_DOCUMENT_SCHEMA_ID: Final = (
    "https://schemas.orbseekr.jp/eo-claim-lint/claim-document-0.1.schema.json"
)
LINT_OUTPUT_SCHEMA_ID: Final = (
    "https://schemas.orbseekr.jp/eo-claim-lint/lint-output-1.0.schema.json"
)

_CLAIM_DOCUMENT_FILENAME: Final = "claim-document-0.1.schema.json"
_LINT_OUTPUT_FILENAME: Final = "lint-output-1.0.schema.json"


def _load(filename: str) -> dict[str, object]:
    text = files("eo_claim_lint.schemas").joinpath(filename).read_text(encoding="utf-8")
    document = json.loads(text)
    if not isinstance(document, dict):
        raise TypeError(f"{filename}: expected a JSON object at the top level")
    return document


def load_claim_document_schema() -> dict[str, object]:
    """Return the claim document schema as a new dictionary."""
    return _load(_CLAIM_DOCUMENT_FILENAME)


def load_lint_output_schema() -> dict[str, object]:
    """Return the linter report schema as a new dictionary."""
    return _load(_LINT_OUTPUT_FILENAME)
