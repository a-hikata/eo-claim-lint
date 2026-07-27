"""Tests for the three output formats and for workflow-command escaping."""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

from eo_claim_lint import LintIssue, LintResult, Severity, load_cli_output_schema
from eo_claim_lint.cli.exit_codes import ExitCode
from eo_claim_lint.cli.output import (
    FileReport,
    build_payload,
    determine_exit_code,
    escape_workflow_data,
    escape_workflow_property,
    format_github,
    format_json,
    format_text,
)


def _issue(
    severity: Severity = Severity.ERROR,
    *,
    rule_id: str = "EOC301",
    message: str = "An example message.",
    path: str = "$",
    field: str | None = "evidence",
    doc_url: str | None = None,
) -> LintIssue:
    return LintIssue(
        rule_id=rule_id,
        severity=severity,
        message=message,
        path=path,
        field=field,
        doc_url=doc_url,
    )


def _report(*issues: LintIssue, source: str = "claim.json") -> FileReport:
    return FileReport(source, LintResult(issues=issues))


# --------------------------------------------------------------------------
# Exit code
# --------------------------------------------------------------------------


def test_nothing_reported_is_success() -> None:
    assert determine_exit_code([_report()], Severity.ERROR) is ExitCode.SUCCESS


@pytest.mark.parametrize(
    ("severity", "fail_on", "expected"),
    [
        (Severity.ERROR, Severity.ERROR, ExitCode.LINT_FAILURE),
        (Severity.WARNING, Severity.ERROR, ExitCode.SUCCESS),
        (Severity.INFO, Severity.ERROR, ExitCode.SUCCESS),
        (Severity.ERROR, Severity.WARNING, ExitCode.LINT_FAILURE),
        (Severity.WARNING, Severity.WARNING, ExitCode.LINT_FAILURE),
        (Severity.INFO, Severity.WARNING, ExitCode.SUCCESS),
        (Severity.ERROR, Severity.INFO, ExitCode.LINT_FAILURE),
        (Severity.WARNING, Severity.INFO, ExitCode.LINT_FAILURE),
        (Severity.INFO, Severity.INFO, ExitCode.LINT_FAILURE),
    ],
)
def test_threshold_table(severity: Severity, fail_on: Severity, expected: ExitCode) -> None:
    assert determine_exit_code([_report(_issue(severity))], fail_on) is expected


def test_the_threshold_spans_every_file() -> None:
    reports = [_report(source="a.json"), _report(_issue(), source="b.json")]

    assert determine_exit_code(reports, Severity.ERROR) is ExitCode.LINT_FAILURE


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------


def test_text_line_carries_every_required_part() -> None:
    text = format_text([_report(_issue())])

    assert "claim.json: EOC301 error $.evidence An example message." in text


def test_text_joins_the_path_and_the_field() -> None:
    text = format_text([_report(_issue(path="$.claim", field="uncertainty"))])

    assert "$.claim.uncertainty" in text


def test_text_uses_the_path_alone_when_there_is_no_field() -> None:
    text = format_text([_report(_issue(path="$.claim", field=None))])

    assert "$.claim An example message." in text


def test_text_ends_with_a_summary() -> None:
    text = format_text([_report(_issue(), _issue(Severity.WARNING, rule_id="EOC101"))])

    assert text.splitlines()[-1] == "1 file checked: 1 error, 1 warning, 0 info"


def test_text_summary_pluralises() -> None:
    reports = [_report(source="a.json"), _report(source="b.json")]

    assert format_text(reports).splitlines()[-1] == "2 files checked: 0 errors, 0 warnings, 0 info"


def test_quiet_text_omits_the_summary() -> None:
    assert format_text([_report()], quiet=True) == ""


def test_text_carries_no_ansi_escapes() -> None:
    text = format_text([_report(_issue())])

    assert "\x1b" not in text


def test_text_ends_with_a_newline() -> None:
    assert format_text([_report(_issue())]).endswith("\n")


# --------------------------------------------------------------------------
# JSON
# --------------------------------------------------------------------------


def test_json_is_valid_and_terminated() -> None:
    rendered = format_json([_report(_issue())])

    assert rendered.endswith("\n")
    assert json.loads(rendered)["valid"] is False


def test_json_matches_the_cli_schema() -> None:
    rendered = format_json([_report(_issue()), _report(source="b.json")])
    validator = Draft202012Validator(load_cli_output_schema())

    assert list(validator.iter_errors(json.loads(rendered))) == []


def test_json_carries_the_tool_version() -> None:
    from eo_claim_lint import __version__

    payload = build_payload([_report()])

    assert payload["tool"] == {"name": "eo-claim-lint", "version": __version__}


def test_json_summary_counts_every_severity() -> None:
    reports = [
        _report(_issue(), _issue(Severity.WARNING, rule_id="EOC101")),
        _report(_issue(Severity.INFO, rule_id="EOC401"), source="b.json"),
    ]

    assert build_payload(reports)["summary"] == {
        "files": 2,
        "errors": 1,
        "warnings": 1,
        "info": 1,
    }


def test_json_valid_is_false_when_any_file_has_an_error() -> None:
    reports = [_report(source="a.json"), _report(_issue(), source="b.json")]

    assert build_payload(reports)["valid"] is False


def test_json_valid_stays_true_for_warnings() -> None:
    assert build_payload([_report(_issue(Severity.WARNING, rule_id="EOC101"))])["valid"] is True


def test_json_does_not_escape_non_ascii() -> None:
    rendered = format_json([_report(_issue(message="架空の指標"))])

    assert "架空" in rendered


# --------------------------------------------------------------------------
# GitHub annotations
# --------------------------------------------------------------------------


def test_error_maps_to_the_error_annotation() -> None:
    assert format_github([_report(_issue())]).startswith("::error ")


def test_warning_maps_to_the_warning_annotation() -> None:
    rendered = format_github([_report(_issue(Severity.WARNING, rule_id="EOC101"))])

    assert rendered.startswith("::warning ")


def test_info_maps_to_notice() -> None:
    """GitHub has no 'info' annotation; 'notice' is the closest."""
    rendered = format_github([_report(_issue(Severity.INFO, rule_id="EOC401"))])

    assert rendered.startswith("::notice ")


def test_annotation_carries_the_file_and_the_rule_id() -> None:
    rendered = format_github([_report(_issue())])

    assert "file=claim.json" in rendered
    assert "title=EOC301" in rendered


def test_annotation_includes_the_location_in_the_message() -> None:
    rendered = format_github([_report(_issue())])

    assert "::$.evidence: An example message." in rendered


def test_annotation_appends_a_doc_url_when_present() -> None:
    rendered = format_github([_report(_issue(doc_url="https://example.org/EOC301"))])

    # The doc_url lives in the message, where colons are not escaped.
    assert "See https://example.org/EOC301" in rendered


def test_annotation_omits_a_missing_doc_url() -> None:
    assert "See " not in format_github([_report(_issue())])


def test_quiet_github_omits_the_summary() -> None:
    assert format_github([_report()], quiet=True) == ""


# --------------------------------------------------------------------------
# Escaping
# --------------------------------------------------------------------------


def test_percent_is_escaped_first() -> None:
    """Escaping the percent afterwards would corrupt the sequences it introduces."""
    assert escape_workflow_data("100%") == "100%25"
    assert escape_workflow_data("a\nb%") == "a%0Ab%25"


def test_newlines_are_escaped() -> None:
    assert escape_workflow_data("a\nb") == "a%0Ab"
    assert escape_workflow_data("a\rb") == "a%0Db"


def test_data_keeps_colons_and_commas() -> None:
    assert escape_workflow_data("a:b,c") == "a:b,c"


def test_properties_escape_colons_and_commas() -> None:
    assert escape_workflow_property("a:b,c") == "a%3Ab%2Cc"


def test_property_escaping_covers_the_data_rules_too() -> None:
    assert escape_workflow_property("a\nb%c:d,e") == "a%0Ab%25c%3Ad%2Ce"


def test_a_message_cannot_start_a_new_workflow_command() -> None:
    """A command is only recognised at the start of a line, so no line break means no injection."""
    hostile = "harmless\n::error file=/etc/passwd::pwned"

    rendered = format_github([_report(_issue(message=hostile))])
    command_lines = [line for line in rendered.splitlines() if line.startswith("::")]

    assert len(command_lines) == 1


def test_a_file_name_cannot_close_the_property_list() -> None:
    hostile = "a.json::error file=b.json"

    rendered = format_github([_report(_issue(), source=hostile)])

    assert rendered.count("::error") == 1
    assert "%3A%3Aerror" in rendered


def test_a_file_name_cannot_inject_another_property() -> None:
    rendered = format_github([_report(_issue(), source="a.json,line=1")])

    assert ",line=1" not in rendered
    assert "%2Cline=1" in rendered
