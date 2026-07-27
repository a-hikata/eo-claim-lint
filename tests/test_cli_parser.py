"""Tests for the command-line parser and the top-level dispatch."""

from __future__ import annotations

import pytest

from eo_claim_lint.cli.exit_codes import ExitCode
from eo_claim_lint.cli.parser import build_parser
from tests.conftest import run_cli


def test_no_command_prints_help_to_stderr_and_fails() -> None:
    run = run_cli([])

    assert run.code == ExitCode.USAGE_ERROR
    assert run.stdout == ""
    assert "usage:" in run.stderr


def test_root_help_succeeds() -> None:
    with pytest.raises(SystemExit) as caught:
        run_cli(["--help"])

    assert caught.value.code == 0


def test_version_succeeds() -> None:
    with pytest.raises(SystemExit) as caught:
        run_cli(["--version"])

    assert caught.value.code == 0


@pytest.mark.parametrize("command", ["check", "rules", "schema", "init"])
def test_each_subcommand_has_help(command: str) -> None:
    with pytest.raises(SystemExit) as caught:
        run_cli([command, "--help"])

    assert caught.value.code == 0


def test_unknown_command_exits_two() -> None:
    with pytest.raises(SystemExit) as caught:
        run_cli(["nonsense"])

    assert caught.value.code == ExitCode.USAGE_ERROR


def test_unknown_format_exits_two() -> None:
    with pytest.raises(SystemExit) as caught:
        run_cli(["check", "--format", "xml", "any.json"])

    assert caught.value.code == ExitCode.USAGE_ERROR


def test_unknown_fail_on_exits_two() -> None:
    with pytest.raises(SystemExit) as caught:
        run_cli(["check", "--fail-on", "fatal", "any.json"])

    assert caught.value.code == ExitCode.USAGE_ERROR


def test_unknown_schema_name_exits_two() -> None:
    with pytest.raises(SystemExit) as caught:
        run_cli(["schema", "nonsense"])

    assert caught.value.code == ExitCode.USAGE_ERROR


# --------------------------------------------------------------------------
# Parsed values
# --------------------------------------------------------------------------


def test_check_defaults() -> None:
    args = build_parser().parse_args(["check", "a.json"])

    assert args.files == ["a.json"]
    assert args.output_format == "text"
    assert args.fail_on == "error"
    assert args.output is None
    assert args.quiet is False
    assert args.stdin_name == "<stdin>"
    assert args.enable == []
    assert args.disable == []
    assert args.severity == []


def test_enable_and_disable_are_repeatable() -> None:
    args = build_parser().parse_args(
        ["check", "--enable", "EOC101", "--enable", "EOC102", "--disable", "EOC202", "a.json"]
    )

    assert args.enable == ["EOC101", "EOC102"]
    assert args.disable == ["EOC202"]


def test_severity_is_repeatable() -> None:
    args = build_parser().parse_args(
        ["check", "--severity", "EOC101=error", "--severity", "EOC301=info", "a.json"]
    )

    assert args.severity == ["EOC101=error", "EOC301=info"]


def test_no_color_is_accepted_and_inert() -> None:
    """Accepted so that a CI script passing it does not fail; output is never coloured."""
    args = build_parser().parse_args(["check", "--no-color", "a.json"])

    assert args.no_color is True


def test_rules_defaults() -> None:
    args = build_parser().parse_args(["rules"])

    assert args.output_format == "text"
    assert args.rule is None


def test_init_defaults() -> None:
    args = build_parser().parse_args(["init"])

    assert args.path == "claim-document.json"
    assert args.stdout is False
    assert args.force is False
