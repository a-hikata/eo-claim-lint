"""Tests for `eo-claim-lint check`, including every exit code."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Final

import pytest
from jsonschema import Draft202012Validator

from eo_claim_lint import Rule, RuleConfig, Severity, load_cli_output_schema
from eo_claim_lint.cli.exit_codes import ExitCode
from eo_claim_lint.models import ClaimDocument, LintIssue
from tests.conftest import run_cli

FIXTURES: Final = Path(__file__).resolve().parent / "fixtures"

CLEAN: Final = FIXTURES / "lint_valid" / "observation-fully-qualified.json"
ERROR_DOC: Final = FIXTURES / "lint_invalid" / "interpretation-without-evidence.json"
WARNING_DOC: Final = FIXTURES / "lint_invalid" / "estimate-without-uncertainty.json"


# --------------------------------------------------------------------------
# Exit code 0
# --------------------------------------------------------------------------


def test_clean_document_exits_zero() -> None:
    run = run_cli(["check", str(CLEAN)])

    assert run.code == ExitCode.SUCCESS
    assert "0 errors" in run.stdout
    assert run.stderr == ""


def test_warning_only_exits_zero_by_default() -> None:
    run = run_cli(["check", str(WARNING_DOC)])

    assert run.code == ExitCode.SUCCESS
    assert "EOC101" in run.stdout


def test_info_only_exits_zero_by_default() -> None:
    run = run_cli(["check", "--severity", "EOC101=info", str(WARNING_DOC)])

    assert run.code == ExitCode.SUCCESS
    assert "info" in run.stdout


# --------------------------------------------------------------------------
# Exit code 1
# --------------------------------------------------------------------------


def test_error_exits_one() -> None:
    run = run_cli(["check", str(ERROR_DOC)])

    assert run.code == ExitCode.LINT_FAILURE
    assert "EOC301" in run.stdout


def test_fail_on_warning_turns_a_warning_into_a_failure() -> None:
    run = run_cli(["check", "--fail-on", "warning", str(WARNING_DOC)])

    assert run.code == ExitCode.LINT_FAILURE


def test_fail_on_info_fails_on_anything() -> None:
    run = run_cli(["check", "--fail-on", "info", "--severity", "EOC101=info", str(WARNING_DOC)])

    assert run.code == ExitCode.LINT_FAILURE


def test_fail_on_error_ignores_warnings() -> None:
    run = run_cli(["check", "--fail-on", "error", str(WARNING_DOC)])

    assert run.code == ExitCode.SUCCESS


def test_a_valid_report_can_still_fail_the_build() -> None:
    """`valid` and the exit code answer different questions."""
    run = run_cli(["check", "--format", "json", "--fail-on", "warning", str(WARNING_DOC)])

    assert json.loads(run.stdout)["valid"] is True
    assert run.code == ExitCode.LINT_FAILURE


# --------------------------------------------------------------------------
# Exit code 2
# --------------------------------------------------------------------------


def test_missing_file_exits_two() -> None:
    run = run_cli(["check", "no-such-file.json"])

    assert run.code == ExitCode.USAGE_ERROR
    assert run.stdout == ""
    assert "no such file" in run.stderr


def test_malformed_json_exits_two(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")

    run = run_cli(["check", str(broken)])

    assert run.code == ExitCode.USAGE_ERROR
    assert "not valid JSON" in run.stderr


def test_a_document_the_model_rejects_exits_two(tmp_path: Path) -> None:
    payload = json.loads(CLEAN.read_text(encoding="utf-8"))
    del payload["claim_id"]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    run = run_cli(["check", str(path)])

    assert run.code == ExitCode.USAGE_ERROR
    assert "claim_id" in run.stderr


def test_no_input_exits_two() -> None:
    run = run_cli(["check"])

    assert run.code == ExitCode.USAGE_ERROR
    assert "no input" in run.stderr


def test_unknown_rule_id_exits_two() -> None:
    run = run_cli(["check", "--disable", "EOC997", str(CLEAN)])

    assert run.code == ExitCode.USAGE_ERROR
    assert "EOC997" in run.stderr


def test_malformed_rule_id_exits_two() -> None:
    run = run_cli(["check", "--disable", "nope", str(CLEAN)])

    assert run.code == ExitCode.USAGE_ERROR
    assert "not a valid rule id" in run.stderr


def test_enable_and_disable_conflict_exits_two() -> None:
    run = run_cli(["check", "--enable", "EOC101", "--disable", "EOC101", str(CLEAN)])

    assert run.code == ExitCode.USAGE_ERROR
    assert "both enabled and disabled" in run.stderr


def test_severity_without_an_equals_sign_exits_two() -> None:
    run = run_cli(["check", "--severity", "EOC101", str(CLEAN)])

    assert run.code == ExitCode.USAGE_ERROR
    assert "RULE_ID=SEVERITY" in run.stderr


def test_unknown_severity_exits_two() -> None:
    run = run_cli(["check", "--severity", "EOC101=critical", str(CLEAN)])

    assert run.code == ExitCode.USAGE_ERROR
    assert "unknown severity" in run.stderr


def test_severity_for_an_unknown_rule_exits_two() -> None:
    run = run_cli(["check", "--severity", "EOC997=error", str(CLEAN)])

    assert run.code == ExitCode.USAGE_ERROR


def test_stdin_combined_with_files_exits_two() -> None:
    run = run_cli(["check", "-", str(CLEAN)])

    assert run.code == ExitCode.USAGE_ERROR
    assert "cannot be combined" in run.stderr


def test_stdin_given_twice_exits_two() -> None:
    run = run_cli(["check", "-", "-"])

    assert run.code == ExitCode.USAGE_ERROR
    assert "only be given once" in run.stderr


def test_existing_output_is_not_overwritten(tmp_path: Path) -> None:
    target = tmp_path / "report.txt"
    target.write_text("keep me", encoding="utf-8")

    run = run_cli(["check", "--output", str(target), str(CLEAN)])

    assert run.code == ExitCode.USAGE_ERROR
    assert target.read_text(encoding="utf-8") == "keep me"


# --------------------------------------------------------------------------
# Exit code 3
# --------------------------------------------------------------------------


class _ExplodingRule(Rule):
    rule_id = "EOC999"
    default_severity = Severity.WARNING
    summary = "Always raises, for testing."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        raise RuntimeError("deliberate failure")


def test_a_crashing_rule_exits_three(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eo_claim_lint.engine.get_default_rules", lambda: (_ExplodingRule(),))

    run = run_cli(["check", str(CLEAN)])

    assert run.code == ExitCode.INTERNAL_ERROR
    assert "internal error" in run.stderr
    assert "EOC999" in run.stderr
    assert run.stdout == ""


def test_an_unexpected_exception_exits_three(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise MemoryError("out of memory")

    monkeypatch.setattr("eo_claim_lint.cli.commands.lint_document", _boom)

    run = run_cli(["check", str(CLEAN)])

    assert run.code == ExitCode.INTERNAL_ERROR
    assert "MemoryError" in run.stderr
    assert run.stdout == ""


def test_an_internal_error_prints_no_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    """A traceback can quote the document being checked."""
    monkeypatch.setattr("eo_claim_lint.engine.get_default_rules", lambda: (_ExplodingRule(),))

    run = run_cli(["check", str(CLEAN)])

    assert "Traceback" not in run.stderr


# --------------------------------------------------------------------------
# stdin, multiple files, ordering
# --------------------------------------------------------------------------


def test_stdin_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(ERROR_DOC.read_text(encoding="utf-8")))

    run = run_cli(["check", "-"])

    assert run.code == ExitCode.LINT_FAILURE
    assert "<stdin>" in run.stdout


def test_stdin_name_can_be_relabelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(ERROR_DOC.read_text(encoding="utf-8")))

    run = run_cli(["check", "--stdin-name", "piped.json", "-"])

    assert "piped.json" in run.stdout


def test_malformed_stdin_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))

    run = run_cli(["check", "-"])

    assert run.code == ExitCode.USAGE_ERROR


def test_multiple_files_are_all_reported() -> None:
    run = run_cli(["check", "--format", "json", str(CLEAN), str(ERROR_DOC)])

    payload = json.loads(run.stdout)

    assert payload["summary"]["files"] == 2
    assert [entry["source"] for entry in payload["files"]] == [str(CLEAN), str(ERROR_DOC)]


def test_input_order_is_preserved() -> None:
    run = run_cli(["check", "--format", "json", str(ERROR_DOC), str(CLEAN)])

    payload = json.loads(run.stdout)

    assert [entry["source"] for entry in payload["files"]] == [str(ERROR_DOC), str(CLEAN)]


def test_a_repeated_file_is_processed_twice() -> None:
    run = run_cli(["check", "--format", "json", str(CLEAN), str(CLEAN)])

    assert json.loads(run.stdout)["summary"]["files"] == 2


def test_one_unreadable_file_aborts_the_whole_run(tmp_path: Path) -> None:
    """No partial report: a consumer cannot tell a partial run from a complete one."""
    run = run_cli(["check", "--format", "json", str(CLEAN), str(tmp_path / "missing.json")])

    assert run.code == ExitCode.USAGE_ERROR
    assert run.stdout == ""


def test_output_is_deterministic() -> None:
    first = run_cli(["check", "--format", "json", str(ERROR_DOC), str(CLEAN)])
    second = run_cli(["check", "--format", "json", str(ERROR_DOC), str(CLEAN)])

    assert first.stdout == second.stdout


# --------------------------------------------------------------------------
# Rule selection
# --------------------------------------------------------------------------


def test_disable_silences_a_rule() -> None:
    run = run_cli(["check", "--disable", "EOC301", str(ERROR_DOC)])

    assert run.code == ExitCode.SUCCESS
    assert "EOC301" not in run.stdout


def test_enable_restricts_to_the_named_rules() -> None:
    run = run_cli(["check", "--enable", "EOC101", str(ERROR_DOC)])

    assert run.code == ExitCode.SUCCESS


def test_severity_override_changes_the_reported_severity() -> None:
    run = run_cli(["check", "--severity", "EOC301=warning", str(ERROR_DOC)])

    assert run.code == ExitCode.SUCCESS
    assert "EOC301 warning" in run.stdout


# --------------------------------------------------------------------------
# Output plumbing
# --------------------------------------------------------------------------


def test_quiet_prints_nothing_for_a_clean_document() -> None:
    run = run_cli(["check", "--quiet", str(CLEAN)])

    assert run.stdout == ""
    assert run.code == ExitCode.SUCCESS


def test_quiet_still_prints_issues() -> None:
    run = run_cli(["check", "--quiet", str(ERROR_DOC)])

    assert "EOC301" in run.stdout
    assert "checked:" not in run.stdout


def test_quiet_does_not_shrink_json() -> None:
    run = run_cli(["check", "--quiet", "--format", "json", str(CLEAN)])

    payload = json.loads(run.stdout)

    assert payload["summary"]["files"] == 1


def test_output_writes_to_a_file(tmp_path: Path) -> None:
    target = tmp_path / "report.json"

    run = run_cli(["check", "--format", "json", "--output", str(target), str(ERROR_DOC)])

    assert run.stdout == ""
    assert json.loads(target.read_text(encoding="utf-8"))["valid"] is False
    assert run.code == ExitCode.LINT_FAILURE


def test_force_overwrites_an_existing_output(tmp_path: Path) -> None:
    target = tmp_path / "report.txt"
    target.write_text("stale", encoding="utf-8")

    run = run_cli(["check", "--output", str(target), "--force", str(CLEAN)])

    assert run.code == ExitCode.SUCCESS
    assert "checked" in target.read_text(encoding="utf-8")


def test_json_output_matches_the_cli_schema() -> None:
    run = run_cli(["check", "--format", "json", str(CLEAN), str(ERROR_DOC)])
    validator = Draft202012Validator(load_cli_output_schema())

    assert list(validator.iter_errors(json.loads(run.stdout))) == []


def test_unicode_survives_the_round_trip(tmp_path: Path) -> None:
    payload = json.loads(ERROR_DOC.read_text(encoding="utf-8"))
    payload["display"]["label"] = "架空市の指標 🛰"
    path = tmp_path / "unicode.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    run = run_cli(["check", "--format", "json", str(path)])

    assert "架空市" not in run.stdout  # labels are not echoed back
    assert json.loads(run.stdout)["files"][0]["issues"]
