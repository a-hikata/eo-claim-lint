"""Reading claim documents for the CLI.

Every failure here is the caller's to fix, so every failure raises
:class:`CliUsageError` and nothing else. In particular, a document that the
model rejects is a usage error rather than a lint finding: the linter never got
far enough to have an opinion about it.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from eo_claim_lint.cli.errors import CliUsageError
from eo_claim_lint.models import ClaimDocument, EoClaimLintError

__all__ = ["STDIN_TOKEN", "LoadedDocument", "load_documents"]

STDIN_TOKEN = "-"


@dataclass(frozen=True)
class LoadedDocument:
    """One document, and the label it should be reported under."""

    source: str
    document: ClaimDocument


def _parse(text: str, source: str) -> ClaimDocument:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        # Line and column locate the problem; the content itself is not echoed.
        raise CliUsageError(
            f"{source}: not valid JSON (line {exc.lineno}, column {exc.colno})"
        ) from exc

    try:
        return ClaimDocument.from_dict(payload)
    except EoClaimLintError as exc:
        raise CliUsageError(f"{source}: {exc}") from exc


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CliUsageError(f"{path}: no such file") from exc
    except IsADirectoryError as exc:
        raise CliUsageError(f"{path}: is a directory, not a file") from exc
    except UnicodeDecodeError as exc:
        raise CliUsageError(f"{path}: not valid UTF-8") from exc
    except OSError as exc:
        raise CliUsageError(f"{path}: cannot be read ({exc.strerror})") from exc


def load_documents(
    sources: Sequence[str], *, stdin_name: str = "<stdin>"
) -> tuple[LoadedDocument, ...]:
    """Load every source, in the order given.

    Raises :class:`CliUsageError` on the first source that cannot be read or
    parsed. Loading is deliberately all-or-nothing: reporting on the files that
    happened to parse would present a partial run as a complete one, and a
    consumer of the output has no way to tell the difference.
    """
    if not sources:
        raise CliUsageError("no input given; pass one or more files, or '-' for stdin")

    stdin_count = sum(1 for source in sources if source == STDIN_TOKEN)
    if stdin_count > 1:
        raise CliUsageError("stdin ('-') may only be given once")
    if stdin_count and len(sources) > 1:
        raise CliUsageError("stdin ('-') cannot be combined with file arguments")

    loaded: list[LoadedDocument] = []
    for source in sources:
        if source == STDIN_TOKEN:
            loaded.append(LoadedDocument(stdin_name, _parse(sys.stdin.read(), stdin_name)))
        else:
            path = Path(source)
            loaded.append(LoadedDocument(source, _parse(_read_file(path), source)))
    return tuple(loaded)
