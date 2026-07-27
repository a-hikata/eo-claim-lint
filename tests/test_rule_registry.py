"""Tests for the rule registry."""

from __future__ import annotations

import re

import pytest

from eo_claim_lint import EoClaimLintError, Rule, Severity, get_default_rules, get_rule
from eo_claim_lint.rules.base import RULE_ID_PATTERN


def test_default_rules_are_not_empty() -> None:
    assert get_default_rules()


def test_rule_ids_are_unique() -> None:
    ids = [rule.rule_id for rule in get_default_rules()]

    assert len(ids) == len(set(ids))


def test_rule_ids_match_the_published_pattern() -> None:
    for rule in get_default_rules():
        assert RULE_ID_PATTERN.match(rule.rule_id), rule.rule_id


def test_order_is_stable_and_sorted_by_id() -> None:
    ids = [rule.rule_id for rule in get_default_rules()]

    assert ids == sorted(ids)
    assert ids == [rule.rule_id for rule in get_default_rules()]


def test_the_same_tuple_is_returned_each_time() -> None:
    assert get_default_rules() is get_default_rules()


def test_default_rules_cannot_be_extended_by_a_caller() -> None:
    rules = get_default_rules()

    with pytest.raises(AttributeError):
        rules.append(None)  # type: ignore[attr-defined]


def test_get_rule_returns_the_matching_rule() -> None:
    rule = get_rule("EOC101")

    assert rule.rule_id == "EOC101"


def test_get_rule_rejects_an_unknown_id() -> None:
    with pytest.raises(EoClaimLintError, match="unknown rule id"):
        get_rule("EOC999")


def test_get_rule_error_lists_the_known_ids() -> None:
    with pytest.raises(EoClaimLintError, match="EOC101"):
        get_rule("EOC999")


def test_every_rule_declares_the_required_attributes() -> None:
    for rule in get_default_rules():
        assert isinstance(rule, Rule)
        assert isinstance(rule.default_severity, Severity)
        assert rule.summary.strip()
        assert rule.summary.endswith("."), f"{rule.rule_id}: summary should be a sentence"


def test_rule_repr_names_the_id() -> None:
    assert "EOC101" in repr(get_rule("EOC101"))


def test_a_rule_class_with_a_bad_id_is_rejected_at_definition() -> None:
    with pytest.raises(TypeError, match="rule_id"):

        class BadRule(Rule):
            rule_id = "NOPE"
            default_severity = Severity.WARNING
            summary = "Invalid."

            def check(self, document: object, config: object) -> tuple[()]:
                return ()


def test_a_rule_class_missing_an_attribute_is_rejected_at_definition() -> None:
    with pytest.raises(TypeError, match="summary"):

        class Incomplete(Rule):
            rule_id = "EOC998"
            default_severity = Severity.WARNING

            def check(self, document: object, config: object) -> tuple[()]:
                return ()


def test_rule_ids_are_grouped_by_concern() -> None:
    """The published grouping is part of the contract, not an accident."""
    groups = {rule.rule_id[3] for rule in get_default_rules()}

    assert groups <= set("01234")
    assert re.match(r"^EOC[1-4]", get_default_rules()[0].rule_id)
