"""Tests for the lint engine and for the whole pipeline over the fixtures."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Final

import pytest
from jsonschema import Draft202012Validator

from eo_claim_lint import (
    ClaimDocument,
    EoClaimLintError,
    LintIssue,
    Rule,
    RuleConfig,
    RuleExecutionError,
    Severity,
    get_default_rules,
    get_rule,
    lint_document,
    load_lint_output_schema,
)
from tests.conftest import make_document

FIXTURES: Final = Path(__file__).resolve().parent / "fixtures"

# Every lint_invalid fixture, and exactly the rules it is meant to trip. Listing
# the full expected set rather than "contains" catches a rule that starts firing
# somewhere it was not designed to.
EXPECTED_ISSUES: Final[Mapping[str, tuple[str, ...]]] = {
    "estimate-without-uncertainty.json": ("EOC101",),
    "observation-marked-modeled.json": ("EOC102",),
    "interpretation-without-qualification.json": ("EOC103",),
    "measured-claim-with-estimate-label.json": ("EOC201",),
    "display-unit-mismatch.json": ("EOC202",),
    "definitive-wording-unknown-uncertainty.json": ("EOC203",),
    "interpretation-without-evidence.json": ("EOC301",),
    "modeled-without-software.json": ("EOC302",),
    "synthetic-without-disclaimer.json": ("EOC401",),
    "unknown-origin-without-disclaimer.json": ("EOC402",),
}


def _load(path: Path) -> ClaimDocument:
    return ClaimDocument.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _files(directory: str) -> list[Path]:
    return sorted((FIXTURES / directory).glob("*.json"))


def _ids(paths: list[Path]) -> list[str]:
    return [path.name for path in paths]


LINT_VALID: Final = _files("lint_valid")
LINT_INVALID: Final = _files("lint_invalid")


class _ExplodingRule(Rule):
    rule_id = "EOC999"
    default_severity = Severity.WARNING
    summary = "Always raises, for testing."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        raise RuntimeError("deliberate failure")


class _AlwaysFiringRule(Rule):
    rule_id = "EOC998"
    default_severity = Severity.INFO
    summary = "Always reports, for testing."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        return (self.issue(config, message="Always reported.", path="$"),)


# --------------------------------------------------------------------------
# Engine behaviour
# --------------------------------------------------------------------------


def test_a_clean_document_produces_no_issues() -> None:
    result = lint_document(make_document())

    assert result.issues == ()
    assert result.valid is True


def test_all_default_rules_run() -> None:
    """Every default rule must be reachable; a rule nobody runs is dead code."""
    reported: set[str] = set()
    for path in LINT_INVALID:
        reported.update(issue.rule_id for issue in lint_document(_load(path)).issues)

    assert reported == {rule.rule_id for rule in get_default_rules()}


def test_a_custom_rule_subset_runs_only_those_rules() -> None:
    result = lint_document(
        make_document(evidence=()), rules=[get_rule("EOC302"), get_rule("EOC301")]
    )

    assert [issue.rule_id for issue in result.issues] == ["EOC301"]


def test_a_disabled_rule_does_not_run() -> None:
    document = make_document(evidence=())

    assert lint_document(document).issues
    assert lint_document(document, config=RuleConfig(disabled=frozenset({"EOC301"}))).issues == ()


def test_enabled_restricts_to_the_named_rules() -> None:
    document = make_document(evidence=())
    config = RuleConfig(enabled=frozenset({"EOC302"}))

    assert lint_document(document, config=config).issues == ()


def test_severity_override_changes_the_reported_severity() -> None:
    document = make_document(evidence=())
    config = RuleConfig(severity_overrides={"EOC301": Severity.INFO})

    result = lint_document(document, config=config)

    assert result.issues[0].severity is Severity.INFO
    assert result.valid is True


def test_an_error_makes_the_report_invalid() -> None:
    result = lint_document(make_document(evidence=()))

    assert result.by_severity(Severity.ERROR)
    assert result.valid is False


def test_warnings_alone_leave_the_report_valid() -> None:
    result = lint_document(_load(FIXTURES / "lint_invalid" / "estimate-without-uncertainty.json"))

    assert [issue.severity for issue in result.issues] == [Severity.WARNING]
    assert result.valid is True


def test_info_alone_leaves_the_report_valid() -> None:
    result = lint_document(make_document(), rules=[_AlwaysFiringRule()])

    assert result.issues[0].severity is Severity.INFO
    assert result.valid is True


def test_issues_are_sorted_deterministically() -> None:
    document = _load(FIXTURES / "schema_valid" / "unknown-minimal.json")

    ids = [issue.rule_id for issue in lint_document(document).issues]

    assert ids == sorted(ids)


def test_repeated_runs_produce_identical_reports() -> None:
    document = _load(FIXTURES / "schema_valid" / "unknown-minimal.json")

    assert lint_document(document).to_dict() == lint_document(document).to_dict()


def test_the_input_document_is_not_modified() -> None:
    document = _load(FIXTURES / "schema_valid" / "unknown-minimal.json")
    before = document.to_dict()

    lint_document(document)

    assert document.to_dict() == before


def test_a_failing_rule_is_reported_as_a_tool_error_not_an_issue() -> None:
    with pytest.raises(RuleExecutionError) as caught:
        lint_document(make_document(), rules=[_ExplodingRule()])

    assert caught.value.rule_id == "EOC999"
    assert isinstance(caught.value.__cause__, RuntimeError)


def test_a_failing_rule_does_not_produce_an_eoclaimlint_error() -> None:
    """A broken rule is not a broken document; the two must not be confused."""
    with pytest.raises(RuleExecutionError) as caught:
        lint_document(make_document(), rules=[_ExplodingRule()])

    assert not isinstance(caught.value, EoClaimLintError)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


def test_config_rejects_a_rule_that_is_both_enabled_and_disabled() -> None:
    with pytest.raises(EoClaimLintError, match="both enabled and disabled"):
        RuleConfig(enabled=frozenset({"EOC101"}), disabled=frozenset({"EOC101"}))


def test_config_rejects_a_malformed_rule_id() -> None:
    with pytest.raises(EoClaimLintError, match="not a valid rule id"):
        RuleConfig(disabled=frozenset({"nope"}))


def test_config_rejects_a_severity_that_is_not_a_severity() -> None:
    with pytest.raises(EoClaimLintError, match="expected a Severity"):
        RuleConfig(severity_overrides={"EOC101": "error"})  # type: ignore[dict-item]


def test_engine_rejects_a_configuration_naming_an_unavailable_rule() -> None:
    with pytest.raises(EoClaimLintError, match="not available"):
        lint_document(make_document(), config=RuleConfig(disabled=frozenset({"EOC997"})))


def test_config_does_not_alias_the_caller_mapping() -> None:
    overrides = {"EOC101": Severity.INFO}
    config = RuleConfig(severity_overrides=overrides)

    overrides["EOC101"] = Severity.ERROR

    assert config.severity_overrides["EOC101"] is Severity.INFO


# --------------------------------------------------------------------------
# Fixture contract
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", LINT_VALID, ids=_ids(LINT_VALID))
def test_lint_valid_fixture_reports_nothing(path: Path) -> None:
    result = lint_document(_load(path))

    assert result.issues == (), [issue.rule_id for issue in result.issues]
    assert result.valid is True


@pytest.mark.parametrize("path", LINT_INVALID, ids=_ids(LINT_INVALID))
def test_lint_invalid_fixture_reports_exactly_the_expected_rules(path: Path) -> None:
    expected = EXPECTED_ISSUES[path.name]

    reported = tuple(issue.rule_id for issue in lint_document(_load(path)).issues)

    assert reported == expected


def test_every_expected_fixture_exists() -> None:
    assert set(EXPECTED_ISSUES) == set(_ids(LINT_INVALID))


def test_every_rule_has_a_failing_fixture() -> None:
    """A rule without a fixture that trips it has never been shown to work."""
    covered = {rule_id for ids in EXPECTED_ISSUES.values() for rule_id in ids}

    assert covered == {rule.rule_id for rule in get_default_rules()}


@pytest.mark.parametrize("path", LINT_INVALID, ids=_ids(LINT_INVALID))
def test_report_passes_the_output_schema(path: Path) -> None:
    validator = Draft202012Validator(load_lint_output_schema())

    errors = list(validator.iter_errors(lint_document(_load(path)).to_dict()))

    assert errors == []


@pytest.mark.parametrize("path", LINT_INVALID, ids=_ids(LINT_INVALID))
def test_issue_context_stays_small(path: Path) -> None:
    """Context is for machine-readable detail, not for a copy of the document."""
    for issue in lint_document(_load(path)).issues:
        assert len(issue.context) <= 3
        for value in issue.context.values():
            assert isinstance(value, str | int | float | bool)


# --------------------------------------------------------------------------
# Rules do no I/O
# --------------------------------------------------------------------------

FORBIDDEN_IN_RULES: Final = (
    re.compile(r"\bopen\("),
    re.compile(r"\bimport os\b"),
    re.compile(r"\bos\.environ\b"),
    re.compile(r"\bimport socket\b"),
    re.compile(r"\burllib\b"),
    re.compile(r"\brequests\b"),
    re.compile(r"\bsubprocess\b"),
    re.compile(r"\bPath\("),
)

RULE_SOURCES: Final = sorted(
    (Path(__file__).resolve().parent.parent / "src" / "eo_claim_lint" / "rules").glob("*.py")
)


@pytest.mark.parametrize("path", RULE_SOURCES, ids=[p.name for p in RULE_SOURCES])
def test_rule_module_performs_no_io(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    for pattern in FORBIDDEN_IN_RULES:
        assert not pattern.search(source), f"{path.name} matches {pattern.pattern}"
