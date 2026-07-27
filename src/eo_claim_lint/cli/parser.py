"""Argument parsing.

Kept apart from the commands so that the surface can be tested without running
anything. ``argparse`` exits with status 2 on a parse error, which is already
the code this CLI uses for a bad invocation.
"""

from __future__ import annotations

import argparse
from typing import Final

from eo_claim_lint import __version__

__all__ = ["SCHEMA_NAMES", "build_parser"]

SCHEMA_NAMES: Final = ("claim", "lint-output", "cli-output")

_DESCRIPTION = (
    "Check whether Earth observation claims distinguish measurements, "
    "estimates, uncertainty, and supporting evidence."
)

_EPILOG = (
    "Exit codes: 0 nothing at or above the --fail-on threshold; "
    "1 the threshold was reached; 2 the invocation or the input was wrong; "
    "3 the linter itself failed."
)


def build_parser() -> argparse.ArgumentParser:
    """Build the full command-line parser."""
    parser = argparse.ArgumentParser(
        prog="eo-claim-lint",
        description=_DESCRIPTION,
        epilog=_EPILOG,
    )
    parser.add_argument("--version", action="version", version=f"eo-claim-lint {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    _add_check(subparsers)
    _add_rules(subparsers)
    _add_schema(subparsers)
    _add_init(subparsers)

    return parser


def _add_check(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    check = subparsers.add_parser(
        "check",
        help="check one or more claim documents",
        description="Check one or more claim documents. Use '-' to read one from stdin.",
    )
    check.add_argument("files", nargs="*", metavar="FILE", help="claim document, or '-' for stdin")
    check.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json", "github"),
        default="text",
        help="output format (default: text)",
    )
    check.add_argument("--output", metavar="PATH", help="write the report here instead of stdout")
    check.add_argument(
        "--force", action="store_true", help="overwrite --output if it already exists"
    )
    check.add_argument(
        "--quiet", action="store_true", help="omit the summary line; print nothing if clean"
    )
    check.add_argument(
        "--fail-on",
        dest="fail_on",
        choices=("error", "warning", "info"),
        default="error",
        help="lowest severity that makes the process exit 1 (default: error)",
    )
    check.add_argument(
        "--enable",
        action="append",
        default=[],
        metavar="RULE_ID",
        help="run only this rule; repeatable",
    )
    check.add_argument(
        "--disable",
        action="append",
        default=[],
        metavar="RULE_ID",
        help="skip this rule; repeatable",
    )
    check.add_argument(
        "--severity",
        action="append",
        default=[],
        metavar="RULE_ID=SEVERITY",
        help="report this rule at another severity; repeatable",
    )
    check.add_argument(
        "--stdin-name",
        dest="stdin_name",
        default="<stdin>",
        metavar="NAME",
        help="label to report stdin under (default: <stdin>)",
    )
    check.add_argument(
        "--no-color",
        action="store_true",
        help="accepted for compatibility; output is never colourised",
    )


def _add_rules(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    rules = subparsers.add_parser(
        "rules",
        help="list the available rules",
        description="List the available rules, or describe one of them.",
    )
    rules.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    rules.add_argument("--rule", metavar="RULE_ID", help="describe a single rule")


def _add_schema(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    schema = subparsers.add_parser(
        "schema",
        help="print a bundled JSON Schema",
        description=(
            "Print a JSON Schema bundled with this package. Nothing is downloaded; "
            "the $id values are identifiers, not locations."
        ),
    )
    schema.add_argument("name", choices=SCHEMA_NAMES, metavar="NAME", help=", ".join(SCHEMA_NAMES))
    schema.add_argument("--output", metavar="PATH", help="write here instead of stdout")
    schema.add_argument(
        "--force", action="store_true", help="overwrite --output if it already exists"
    )


def _add_init(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    init = subparsers.add_parser(
        "init",
        help="write an example claim document",
        description=(
            "Write a synthetic example claim document. The example is entirely "
            "fictional and passes every default rule."
        ),
    )
    init.add_argument(
        "path",
        nargs="?",
        default="claim-document.json",
        metavar="PATH",
        help="where to write (default: claim-document.json)",
    )
    init.add_argument("--stdout", action="store_true", help="print instead of writing a file")
    init.add_argument("--force", action="store_true", help="overwrite PATH if it already exists")
