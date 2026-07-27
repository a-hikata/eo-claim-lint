"""Tests for `rules`, `schema`, and `init`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from eo_claim_lint import (
    ClaimDocument,
    get_default_rules,
    lint_document,
    load_claim_document_schema,
    load_cli_output_schema,
    load_lint_output_schema,
)
from eo_claim_lint.cli.commands import EXAMPLE_DOCUMENT
from eo_claim_lint.cli.exit_codes import ExitCode
from tests.conftest import run_cli

# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------


def test_rules_lists_every_rule() -> None:
    run = run_cli(["rules"])

    assert run.code == ExitCode.SUCCESS
    for rule in get_default_rules():
        assert rule.rule_id in run.stdout


def test_rules_text_shows_id_severity_and_summary() -> None:
    run = run_cli(["rules"])

    assert "EOC101  warning  An estimate should declare its uncertainty." in run.stdout


def test_rules_order_is_stable() -> None:
    first = run_cli(["rules"]).stdout
    second = run_cli(["rules"]).stdout

    assert first == second
    ids = [line.split()[0] for line in first.splitlines()]
    assert ids == sorted(ids)


def test_rules_json_shape() -> None:
    run = run_cli(["rules", "--format", "json"])

    payload = json.loads(run.stdout)

    assert len(payload["rules"]) == len(get_default_rules())
    assert payload["rules"][0]["rule_id"] == "EOC101"
    assert payload["rules"][0]["default_severity"] == "warning"
    assert payload["rules"][0]["doc_url"] is None


def test_rules_json_reports_the_category() -> None:
    run = run_cli(["rules", "--format", "json", "--rule", "EOC301"])

    assert json.loads(run.stdout)["rules"][0]["category"] == "EOC3xx"


def test_single_rule_lookup() -> None:
    run = run_cli(["rules", "--rule", "EOC301"])

    assert run.code == ExitCode.SUCCESS
    assert run.stdout.count("EOC") == 1


def test_unknown_rule_exits_two() -> None:
    run = run_cli(["rules", "--rule", "EOC997"])

    assert run.code == ExitCode.USAGE_ERROR
    assert "unknown rule id" in run.stderr


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "loader"),
    [
        ("claim", load_claim_document_schema),
        ("lint-output", load_lint_output_schema),
        ("cli-output", load_cli_output_schema),
    ],
)
def test_schema_prints_the_bundled_document(name: str, loader: object) -> None:
    run = run_cli(["schema", name])

    assert run.code == ExitCode.SUCCESS
    assert json.loads(run.stdout)["$id"] == loader()["$id"]  # type: ignore[operator]


def test_schema_output_is_terminated() -> None:
    assert run_cli(["schema", "claim"]).stdout.endswith("\n")


def test_schema_writes_to_a_file(tmp_path: Path) -> None:
    target = tmp_path / "claim.schema.json"

    run = run_cli(["schema", "claim", "--output", str(target)])

    assert run.code == ExitCode.SUCCESS
    assert run.stdout == ""
    assert json.loads(target.read_text(encoding="utf-8"))["$id"]


def test_schema_refuses_to_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "claim.schema.json"
    target.write_text("keep me", encoding="utf-8")

    run = run_cli(["schema", "claim", "--output", str(target)])

    assert run.code == ExitCode.USAGE_ERROR
    assert target.read_text(encoding="utf-8") == "keep me"


def test_schema_force_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "claim.schema.json"
    target.write_text("stale", encoding="utf-8")

    run = run_cli(["schema", "claim", "--output", str(target), "--force"])

    assert run.code == ExitCode.SUCCESS
    assert json.loads(target.read_text(encoding="utf-8"))["$id"]


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------


def test_init_writes_the_default_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    run = run_cli(["init"])

    assert run.code == ExitCode.SUCCESS
    assert (tmp_path / "claim-document.json").is_file()


def test_init_writes_a_given_path(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "example.json"
    target.parent.mkdir()

    run = run_cli(["init", str(target)])

    assert run.code == ExitCode.SUCCESS
    assert json.loads(target.read_text(encoding="utf-8"))["claim_id"] == "claim-001"


def test_init_stdout_writes_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    run = run_cli(["init", "--stdout"])

    assert json.loads(run.stdout)["claim_id"] == "claim-001"
    assert list(tmp_path.iterdir()) == []


def test_init_refuses_to_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "example.json"
    target.write_text("keep me", encoding="utf-8")

    run = run_cli(["init", str(target)])

    assert run.code == ExitCode.USAGE_ERROR
    assert target.read_text(encoding="utf-8") == "keep me"


def test_init_force_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "example.json"
    target.write_text("stale", encoding="utf-8")

    run = run_cli(["init", str(target), "--force"])

    assert run.code == ExitCode.SUCCESS
    assert json.loads(target.read_text(encoding="utf-8"))["claim_id"] == "claim-001"


def test_the_example_matches_the_claim_schema() -> None:
    validator = Draft202012Validator(load_claim_document_schema())

    assert list(validator.iter_errors(EXAMPLE_DOCUMENT)) == []


def test_the_example_reports_nothing_under_the_default_rules() -> None:
    """A first-time user should see a working example, not a pile of warnings."""
    result = lint_document(ClaimDocument.from_dict(EXAMPLE_DOCUMENT))

    assert result.issues == ()
    assert result.valid is True


def test_the_example_is_entirely_fictional() -> None:
    rendered = json.dumps(EXAMPLE_DOCUMENT, ensure_ascii=False)

    assert "urn:example:" in rendered
    assert "Example Area" in rendered
    # Written without quoting an absolute path, so that the repository-wide
    # safety scan does not trip on this very assertion.
    for forbidden in ("@", "://"):
        assert forbidden not in rendered
    assert '"/' not in rendered, "no value may be an absolute filesystem path"


def test_the_example_declares_its_synthetic_origin() -> None:
    """It is a generated example, and it says so — which is what EOC401 asks for."""
    assert EXAMPLE_DOCUMENT["data_origin"] == "synthetic"
    display = EXAMPLE_DOCUMENT["display"]
    assert isinstance(display, dict)
    assert display["disclaimer"]
