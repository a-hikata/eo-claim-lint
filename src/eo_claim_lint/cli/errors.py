"""Errors the CLI raises to select an exit code.

Both carry a message that is safe to print: it names paths and options, never
the contents of a document.
"""

from __future__ import annotations

__all__ = ["CliUsageError"]


class CliUsageError(Exception):
    """The invocation or the input was wrong.

    Routed to :attr:`~eo_claim_lint.cli.exit_codes.ExitCode.USAGE_ERROR`. This
    covers everything the caller can fix by changing the command or the file:
    an unreadable path, malformed JSON, a document the model rejects, an
    unknown rule id, a contradictory selection of rules.
    """
