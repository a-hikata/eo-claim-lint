"""Mechanical checks that nothing real leaked into the repository.

These are cheap and they only catch what a regular expression can catch, but
the failure they guard against — a real coordinate or a credential pasted into
a reproduction case — is the kind that is easy to commit and hard to withdraw.

The checks here are deliberately **generic**. They look for categories of
sensitive content: addresses, credentials, absolute paths from a developer's
machine, coordinates precise enough to be real. They do not enumerate the
identifiers of any particular organisation. A deny-list naming one project's
internal vocabulary would publish that vocabulary, which is the opposite of
what such a list is for; a project with its own terms to exclude should add
that check in its own repository.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest

PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent

SCANNED_SUFFIXES: Final = frozenset({".py", ".json", ".toml", ".md", ".yml", ".yaml", ".cfg"})

SKIPPED_DIRECTORIES: Final = frozenset(
    {".git", ".venv", "venv", "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
)

# This file quotes the very strings it forbids.
DOCUMENTS_THE_PROHIBITIONS: Final = "test_fixture_safety.py"

FORBIDDEN_SUBSTRINGS: Final = (
    "/Users/",
    "/home/",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
)

EMAIL: Final = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

CREDENTIAL_WORDS: Final = (
    re.compile(r"\bapi[_-]?key\b", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\bsecret\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
)

# Latitudes and longitudes carry many decimal places. Fixture coordinates are
# deliberately blunt (10.0, 11.0), so anything with three or more decimals is
# suspicious.
PRECISE_COORDINATE: Final = re.compile(r"\b-?\d{1,3}\.\d{3,}\b")

RESERVED_URI_PREFIX: Final = "urn:example:"


def _scanned_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        if SKIPPED_DIRECTORIES.intersection(path.relative_to(PROJECT_ROOT).parts):
            continue
        yield path


FIXTURE_FILES: Final = sorted((PROJECT_ROOT / "tests" / "fixtures").rglob("*.json"))
REPOSITORY_FILES: Final = list(_scanned_files(PROJECT_ROOT))


def _ids(paths: list[Path]) -> list[str]:
    return [str(path.relative_to(PROJECT_ROOT)) for path in paths]


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=_ids(FIXTURE_FILES))
def test_fixture_has_no_credential_wording(path: Path) -> None:
    """A fixture has no reason to mention a credential, even as a placeholder."""
    text = path.read_text(encoding="utf-8")

    for pattern in CREDENTIAL_WORDS:
        assert not pattern.search(text), f"{path.name} matches {pattern.pattern}"


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=_ids(FIXTURE_FILES))
def test_fixture_has_no_precise_coordinates(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert not PRECISE_COORDINATE.search(text), (
        f"{path.name} contains a value precise enough to be a real coordinate"
    )


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=_ids(FIXTURE_FILES))
def test_fixture_uses_the_reserved_example_namespace(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    for match in re.finditer(r'"uri"\s*:\s*"([^"]+)"', text):
        assert match.group(1).startswith(RESERVED_URI_PREFIX), (
            f"{path.name} references {match.group(1)!r}, which is not a reserved example URI"
        )


@pytest.mark.parametrize("path", REPOSITORY_FILES, ids=_ids(REPOSITORY_FILES))
def test_repository_has_no_forbidden_substring(path: Path) -> None:
    if path.name == DOCUMENTS_THE_PROHIBITIONS:
        pytest.skip("this file quotes the prohibited strings in order to search for them")

    text = path.read_text(encoding="utf-8")

    for needle in FORBIDDEN_SUBSTRINGS:
        assert needle not in text, f"{path} contains {needle!r}"


def test_no_email_address_anywhere_in_the_repository() -> None:
    """No exemption for documentation: an address in prose is still published."""
    offenders: list[str] = []
    for path in REPOSITORY_FILES:
        if EMAIL.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == [], f"email addresses found in: {', '.join(offenders)}"
