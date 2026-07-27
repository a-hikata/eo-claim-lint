"""Running rules over a claim document.

The engine is deliberately dull: it selects rules, calls them in a fixed order,
sorts what comes back, and derives validity. It performs no I/O, reads no
environment, and does not modify the document it is given, so two runs over the
same input produce byte-identical reports.
"""

from __future__ import annotations

from collections.abc import Sequence

from eo_claim_lint.models import ClaimDocument, EoClaimLintError, LintIssue, LintResult
from eo_claim_lint.rules import Rule, RuleConfig, RuleExecutionError, get_default_rules

__all__ = ["lint_document"]


def _issue_sort_key(issue: LintIssue) -> tuple[str, str, str, str]:
    return (issue.rule_id, issue.path, issue.field or "", issue.message)


def _select(rules: Sequence[Rule], config: RuleConfig) -> tuple[Rule, ...]:
    available = {rule.rule_id for rule in rules}
    unknown = sorted(config.referenced_ids() - available)
    if unknown:
        raise EoClaimLintError(
            f"configuration names rules that are not available: {', '.join(unknown)}"
        )
    return tuple(rule for rule in rules if config.selects(rule.rule_id))


def lint_document(
    document: ClaimDocument,
    *,
    rules: Sequence[Rule] | None = None,
    config: RuleConfig | None = None,
) -> LintResult:
    """Check one claim document and return the findings.

    ``rules`` defaults to :func:`~eo_claim_lint.rules.get_default_rules`.
    ``config`` selects among them and may override severities; it never changes
    what a rule considers wrong.

    Issues are sorted by rule id, then path, then field, then message, so the
    order does not depend on which rule happened to run first.

    Raises :class:`~eo_claim_lint.rules.RuleExecutionError` if a rule itself
    fails. A crashing rule is a defect in this package, not a finding about the
    document, and reporting it as an issue would hide the difference.
    """
    active_config = RuleConfig() if config is None else config
    candidate_rules = get_default_rules() if rules is None else tuple(rules)
    selected = _select(candidate_rules, active_config)

    collected: list[LintIssue] = []
    for rule in selected:
        try:
            found = rule.check(document, active_config)
        except Exception as exc:
            # Caught broadly on purpose: whatever a rule raises, the caller
            # needs to learn that a rule broke rather than that the document
            # did. The original exception is chained, not swallowed.
            raise RuleExecutionError(rule.rule_id, exc) from exc
        collected.extend(found)

    return LintResult(issues=tuple(sorted(collected, key=_issue_sort_key)))
