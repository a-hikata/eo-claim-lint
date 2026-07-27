"""Rendering results, and deciding what the process should exit with.

Three renderings of the same findings: one for a person reading a terminal, one
for a program reading stdout, one for GitHub Actions to turn into annotations.
None of them ever prints the document that was checked.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from eo_claim_lint import __version__
from eo_claim_lint.cli.exit_codes import ExitCode
from eo_claim_lint.models import LintIssue, LintResult, Severity

__all__ = [
    "CLI_OUTPUT_SCHEMA_VERSION",
    "FileReport",
    "build_payload",
    "determine_exit_code",
    "escape_workflow_data",
    "escape_workflow_property",
    "format_github",
    "format_json",
    "format_text",
]

CLI_OUTPUT_SCHEMA_VERSION: Final = "0.1"
TOOL_NAME: Final = "eo-claim-lint"

#: Ordered from least to most serious, so that a `--fail-on` threshold can be
#: expressed as "this severity or worse".
SEVERITY_ORDER: Final = (Severity.INFO, Severity.WARNING, Severity.ERROR)

#: GitHub Actions has no "info" annotation; the closest is "notice".
_ANNOTATION_KIND: Final = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "notice",
}


@dataclass(frozen=True)
class FileReport:
    """One source and what linting it produced."""

    source: str
    result: LintResult


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _location(issue: LintIssue) -> str:
    """A single readable location, joining the path and the field."""
    if not issue.field:
        return issue.path
    separator = "" if issue.path.endswith(".") else "."
    return f"{issue.path}{separator}{issue.field}"


def _counts(reports: Sequence[FileReport]) -> dict[Severity, int]:
    tally = dict.fromkeys(SEVERITY_ORDER, 0)
    for report in reports:
        for issue in report.result.issues:
            tally[issue.severity] += 1
    return tally


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


# --------------------------------------------------------------------------
# Exit code
# --------------------------------------------------------------------------


def determine_exit_code(reports: Sequence[FileReport], fail_on: Severity) -> ExitCode:
    """Decide the process status from the findings and the chosen threshold.

    This is deliberately not the same question as ``LintResult.valid``. A report
    is valid when it carries no error; the process fails when it carries
    anything at or above the threshold the caller asked about. With
    ``--fail-on warning``, a warning-only run is a valid report and a failed
    build, and both statements are true at once.
    """
    threshold = SEVERITY_ORDER.index(fail_on)
    for report in reports:
        for issue in report.result.issues:
            if SEVERITY_ORDER.index(issue.severity) >= threshold:
                return ExitCode.LINT_FAILURE
    return ExitCode.SUCCESS


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------


def format_text(reports: Sequence[FileReport], *, quiet: bool = False) -> str:
    """Render for a person. No colour, no box drawing, no terminal width."""
    lines: list[str] = []
    for report in reports:
        for issue in report.result.issues:
            lines.append(
                f"{report.source}: {issue.rule_id} {issue.severity.value} "
                f"{_location(issue)} {issue.message}"
            )

    if quiet:
        return "".join(f"{line}\n" for line in lines)

    tally = _counts(reports)
    summary = (
        f"{_plural(len(reports), 'file')} checked: "
        f"{_plural(tally[Severity.ERROR], 'error')}, "
        f"{_plural(tally[Severity.WARNING], 'warning')}, "
        f"{tally[Severity.INFO]} info"
    )
    lines.append(summary)
    return "".join(f"{line}\n" for line in lines)


# --------------------------------------------------------------------------
# JSON
# --------------------------------------------------------------------------


def build_payload(reports: Sequence[FileReport]) -> dict[str, object]:
    """The aggregated result, matching ``cli-output-0.1``.

    ``valid`` here means what it means everywhere else in this package: no
    issue reached error severity. It is not the exit code.
    """
    tally = _counts(reports)
    return {
        "schema_version": CLI_OUTPUT_SCHEMA_VERSION,
        "tool": {"name": TOOL_NAME, "version": __version__},
        "valid": all(report.result.valid for report in reports),
        "files": [
            {
                "source": report.source,
                "valid": report.result.valid,
                "issues": [issue.to_dict() for issue in report.result.issues],
            }
            for report in reports
        ],
        "summary": {
            "files": len(reports),
            "errors": tally[Severity.ERROR],
            "warnings": tally[Severity.WARNING],
            "info": tally[Severity.INFO],
        },
    }


def format_json(reports: Sequence[FileReport]) -> str:
    """Render for another program. Nothing but JSON goes to stdout."""
    return json.dumps(build_payload(reports), ensure_ascii=False, indent=2) + "\n"


# --------------------------------------------------------------------------
# GitHub Actions workflow commands
# --------------------------------------------------------------------------


def escape_workflow_data(value: str) -> str:
    """Escape a workflow command's message.

    Escaping the newlines is what prevents command injection: a workflow
    command is only recognised at the start of a line, so a message that cannot
    contain a line break cannot start one. The percent sign goes first, or it
    would double-escape the sequences introduced afterwards.
    """
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_workflow_property(value: str) -> str:
    """Escape a workflow command property value.

    Properties are separated by commas and terminated by a colon, so both need
    escaping on top of the message rules.
    """
    return escape_workflow_data(value).replace(":", "%3A").replace(",", "%2C")


def _annotation(source: str, issue: LintIssue) -> str:
    kind = _ANNOTATION_KIND[issue.severity]
    message = f"{_location(issue)}: {issue.message}"
    if issue.doc_url:
        message = f"{message} See {issue.doc_url}"
    properties = (
        f"file={escape_workflow_property(source)},title={escape_workflow_property(issue.rule_id)}"
    )
    return f"::{kind} {properties}::{escape_workflow_data(message)}"


def format_github(reports: Sequence[FileReport], *, quiet: bool = False) -> str:
    """Render as GitHub Actions workflow commands."""
    lines = [
        _annotation(report.source, issue) for report in reports for issue in report.result.issues
    ]

    if not quiet:
        tally = _counts(reports)
        lines.append(
            f"{_plural(len(reports), 'file')} checked: "
            f"{_plural(tally[Severity.ERROR], 'error')}, "
            f"{_plural(tally[Severity.WARNING], 'warning')}, "
            f"{tally[Severity.INFO]} info"
        )
    return "".join(f"{line}\n" for line in lines)
