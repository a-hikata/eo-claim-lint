"""Exit codes, and the reason there are four of them.

A caller in CI has to distinguish three different bad outcomes that all look
like "it did not succeed":

* the document failed the checks,
* the invocation was wrong — a missing file, a malformed option,
* the linter itself broke.

Collapsing those into one non-zero code means a crash in this package reads as
a finding about the user's data. The whole point of :class:`RuleExecutionError`
being a separate exception is that it can be routed here, to its own code.
"""

from __future__ import annotations

from enum import IntEnum

__all__ = ["ExitCode"]


class ExitCode(IntEnum):
    """Process exit statuses."""

    SUCCESS = 0
    """Nothing to report, or nothing at or above the ``--fail-on`` threshold."""

    LINT_FAILURE = 1
    """At least one issue reached the ``--fail-on`` threshold."""

    USAGE_ERROR = 2
    """The invocation or the input was wrong: bad path, bad JSON, bad option."""

    INTERNAL_ERROR = 3
    """The linter failed. Not a statement about the document."""
