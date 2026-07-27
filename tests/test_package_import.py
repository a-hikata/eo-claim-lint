"""Skeleton checks: the package imports, is versioned, and ships type information.

These tests deliberately assert nothing about linting behaviour, because no
rules are implemented yet.
"""

from __future__ import annotations

import sys
from importlib.metadata import version as metadata_version
from importlib.resources import files


def test_package_is_importable() -> None:
    import eo_claim_lint

    assert eo_claim_lint.__doc__


def test_version_is_exposed() -> None:
    import eo_claim_lint

    assert isinstance(eo_claim_lint.__version__, str)
    assert eo_claim_lint.__version__


def test_version_matches_installed_metadata() -> None:
    import eo_claim_lint

    assert eo_claim_lint.__version__ == metadata_version("eo-claim-lint")


def test_typed_marker_is_shipped() -> None:
    marker = files("eo_claim_lint").joinpath("py.typed")

    assert marker.is_file()


def test_runs_on_supported_python() -> None:
    assert sys.version_info >= (3, 11)
