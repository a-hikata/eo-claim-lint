"""The command-line interface.

A thin shell over the public API: parse arguments, load documents, call
:func:`~eo_claim_lint.engine.lint_document`, render, choose an exit code. No
rule logic lives here, and none should — a check that behaved differently on
the command line than through the API would be a second implementation to keep
in step.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TextIO

from eo_claim_lint.cli.commands import run_check, run_init, run_rules, run_schema
from eo_claim_lint.cli.errors import CliUsageError
from eo_claim_lint.cli.exit_codes import ExitCode
from eo_claim_lint.cli.parser import build_parser
from eo_claim_lint.rules import RuleExecutionError

__all__ = ["ExitCode", "main"]

_COMMANDS = {
    "check": run_check,
    "rules": run_rules,
    "schema": run_schema,
    "init": run_init,
}


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the CLI and return the exit status.

    Streams are injectable so that the behaviour can be tested without
    capturing the process's real output.
    """
    out = sys.stdout if stdout is None else stdout
    err = sys.stderr if stderr is None else stderr

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(err)
        return ExitCode.USAGE_ERROR

    try:
        return _COMMANDS[args.command](args, stdout=out)
    except CliUsageError as exc:
        err.write(f"error: {exc}\n")
        return ExitCode.USAGE_ERROR
    except RuleExecutionError as exc:
        # A rule crashed. That is a defect in this package, not a finding about
        # the document, so it gets its own status rather than being folded into
        # "the document failed".
        err.write(f"internal error: {exc}\n")
        err.write("This is a bug in eo-claim-lint. Please report it.\n")
        return ExitCode.INTERNAL_ERROR
    except Exception as exc:
        # Deliberately broad. Anything unforeseen is still our fault, and the
        # caller must not read it as a lint failure. The traceback is withheld
        # because it can quote the document being checked.
        err.write(f"internal error: {type(exc).__name__}: {exc}\n")
        err.write("This is a bug in eo-claim-lint. Please report it.\n")
        return ExitCode.INTERNAL_ERROR
