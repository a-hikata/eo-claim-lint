"""Rules about whether the declared claim type matches the rest of the document."""

from __future__ import annotations

from eo_claim_lint.models import (
    ClaimDocument,
    ClaimType,
    DataProcessing,
    LintIssue,
    Severity,
)
from eo_claim_lint.rules.base import Rule, RuleConfig

__all__ = ["InterpretationQualificationRule", "ObservationProcessingRule"]


class ObservationProcessingRule(Rule):
    """EOC102 — an observation whose data is marked as modeled.

    ``modeled`` means a model added assumptions the input data did not contain.
    A value that went through that step is not, in the ordinary sense, something
    an instrument recorded. When a document says both, one of the two labels is
    usually left over from an earlier version.

    The severity is a warning rather than an error because the combination is
    not impossible: a reanalysis product is modelled yet is routinely described
    as an observation of the atmosphere. The rule asks for a second look; it
    does not assert an error.

    This is the only rule that inspects the observation/modeled pair. Nothing in
    the EOC4xx range repeats it.
    """

    rule_id = "EOC102"
    default_severity = Severity.WARNING
    summary = "An observation is unlikely to be modeled data."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        if document.claim.type is not ClaimType.OBSERVATION:
            return ()
        if document.data_processing is not DataProcessing.MODELED:
            return ()
        return (
            self.issue(
                config,
                message=(
                    "This claim is typed as an observation while its data is marked "
                    "as modeled. Confirm that the reader is meant to treat a model "
                    "output as an observation; otherwise correct one of the two."
                ),
                path="$",
                field_name="data_processing",
                context={
                    "claim_type": document.claim.type.value,
                    "data_processing": document.data_processing.value,
                },
            ),
        )


class InterpretationQualificationRule(Rule):
    """EOC103 — an interpretation offered without any qualification.

    An interpretation is a judgement about what an observation or an estimate
    means. Presented bare, it reads with the same authority as a measurement
    while resting on reasoning the reader cannot see. Either an uncertainty or
    a disclaimer is enough; the rule does not care which.

    False positives: a project whose interpretations are qualified in a field
    this model does not carry — a surrounding article, for instance — will see
    this fire on documents that are fine in context.
    """

    rule_id = "EOC103"
    default_severity = Severity.WARNING
    summary = "An interpretation should carry an uncertainty or a disclaimer."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        if document.claim.type is not ClaimType.INTERPRETATION:
            return ()
        if document.claim.uncertainty is not None:
            return ()
        if (document.display.disclaimer or "").strip():
            return ()
        return (
            self.issue(
                config,
                message=(
                    "This claim is typed as an interpretation but offers neither an "
                    "uncertainty nor a disclaimer. Add one so that a reader can tell "
                    "it apart from a measurement."
                ),
                path="$.claim",
                field_name="uncertainty",
                context={"claim_type": document.claim.type.value},
            ),
        )
