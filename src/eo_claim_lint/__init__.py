"""eo-claim-lint — a linter for Earth observation claim documents.

This package checks whether a published claim derived from Earth observation
data keeps measurements and estimates distinguishable, declares uncertainty,
and carries the evidence needed to trace where the numbers came from.

It does not recompute or scientifically validate the numbers themselves.

Status: early development. No linting rules are implemented yet; this release
contains the package skeleton only. See README.md for the roadmap.
"""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("eo-claim-lint")
except PackageNotFoundError:  # pragma: no cover - only when running from a source tree
    __version__ = "0.0.0+unknown"
