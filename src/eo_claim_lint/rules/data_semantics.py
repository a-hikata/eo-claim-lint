"""Rules about disclosing where the data came from.

Neither rule here treats a value as suspect. ``synthetic`` data is legitimate
and often necessary, and ``unknown`` origin is an honest admission. What both
rules ask is that the reader be told, because a reader who assumes measurement
and receives something else has been misled by omission rather than by
assertion.
"""

from __future__ import annotations

from eo_claim_lint.models import ClaimDocument, DataOrigin, LintIssue, Severity
from eo_claim_lint.rules.base import Rule, RuleConfig

__all__ = ["SyntheticDisclosureRule", "UnknownOriginDisclosureRule"]


def _has_disclaimer(document: ClaimDocument) -> bool:
    return bool((document.display.disclaimer or "").strip())


class SyntheticDisclosureRule(Rule):
    """EOC401 — synthetic origin that the display does not mention.

    Synthetic does not mean false, and this rule makes no judgement about the
    quality of the value. It asks only that a document whose data was generated
    rather than recorded says so where a reader will see it.

    False positives: a page may disclose the synthetic origin outside this
    document — a banner across a demo site, for example. The disclosure is real
    but invisible here.
    """

    rule_id = "EOC401"
    default_severity = Severity.WARNING
    summary = "Synthetic origin should be disclosed to the reader."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        if document.data_origin is not DataOrigin.SYNTHETIC:
            return ()
        if _has_disclaimer(document):
            return ()
        return (
            self.issue(
                config,
                message=(
                    "The data origin is synthetic, but the display carries no "
                    "disclaimer. Say so where the reader will see it. Synthetic data "
                    "is legitimate; the point is that nobody should have to guess."
                ),
                path="$.display",
                field_name="disclaimer",
                context={"data_origin": document.data_origin.value},
            ),
        )


class UnknownOriginDisclosureRule(Rule):
    """EOC402 — unknown origin that the display does not mention.

    Recording the origin as unknown is honest. Showing the value without
    repeating that is not: the reader has no way to know the question was left
    open.

    False positives: the same as EOC401 — the disclosure may live outside the
    document.
    """

    rule_id = "EOC402"
    default_severity = Severity.WARNING
    summary = "An unestablished data origin should be disclosed to the reader."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        if document.data_origin is not DataOrigin.UNKNOWN:
            return ()
        if _has_disclaimer(document):
            return ()
        return (
            self.issue(
                config,
                message=(
                    "The data origin is recorded as unknown, but the display carries "
                    "no disclaimer. A reader shown the value alone will assume it was "
                    "established."
                ),
                path="$.display",
                field_name="disclaimer",
                context={"data_origin": document.data_origin.value},
            ),
        )
