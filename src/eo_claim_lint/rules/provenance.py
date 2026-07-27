"""Rules about whether the document records how the value was produced."""

from __future__ import annotations

from eo_claim_lint.models import ClaimDocument, DataProcessing, LintIssue, Severity
from eo_claim_lint.rules.base import Rule, RuleConfig

__all__ = ["ModeledSoftwareRule"]


class ModeledSoftwareRule(Rule):
    """EOC302 — modeled data that does not say what produced it.

    ``processing.method`` is already required by the schema, so this rule does
    not repeat that check. What it looks for is narrower: when a model was
    involved, the model itself is part of the result. Two runs of different
    versions of the same software can disagree, and a reader who cannot tell
    which one ran cannot reproduce anything.

    Either ``software`` or ``software_version`` satisfies the rule. Requiring
    both would fail documents produced by a one-off script that has a name but
    no release.

    False positives: a model implemented as part of a larger pipeline may be
    identified only by ``method``, in prose. That is a legitimate style, and
    such a project should lower or disable this rule.
    """

    rule_id = "EOC302"
    default_severity = Severity.WARNING
    summary = "Modeled data should identify the software that produced it."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        if document.data_processing is not DataProcessing.MODELED:
            return ()

        processing = document.processing
        if (processing.software or "").strip() or (processing.software_version or "").strip():
            return ()

        return (
            self.issue(
                config,
                message=(
                    "The data is marked as modeled, but no software or version is "
                    "recorded. Name what produced the value so that the result can be "
                    "reproduced."
                ),
                path="$.processing",
                field_name="software",
                context={"data_processing": document.data_processing.value},
            ),
        )
