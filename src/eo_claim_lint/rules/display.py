"""Rules about what a reader is shown versus what the document records."""

from __future__ import annotations

import re
from typing import Final

from eo_claim_lint.models import ClaimDocument, ClaimType, LintIssue, Severity
from eo_claim_lint.rules.base import Rule, RuleConfig

__all__ = ["DisplayLabelContradictionRule", "DisplayUnitMismatchRule"]

# A deliberately tiny, English-only vocabulary. The point is to catch a label
# that states the opposite of the declared claim type, not to review prose. A
# longer list would start flagging phrasing rather than contradiction, which is
# the job of a prose linter such as Vale or textlint. Other languages wait
# until vocabularies can be supplied through configuration.
MEASUREMENT_WORDS: Final = ("measured", "observed", "recorded")
NON_MEASUREMENT_WORDS: Final = ("estimated", "predicted", "forecast", "modeled", "modelled")

_WORD = re.compile(r"[a-z]+")


def _first_word_present(text: str, vocabulary: tuple[str, ...]) -> str | None:
    words = set(_WORD.findall(text.lower()))
    for term in vocabulary:
        if term in words:
            return term
    return None


class DisplayLabelContradictionRule(Rule):
    """EOC201 — the label says one thing, the claim type says another.

    A label reading "Measured vegetation index" over a claim typed as an
    estimate tells the reader the opposite of what the document records. This
    is the failure the whole tool exists for, so it is checked directly rather
    than left to the reader.

    Only a handful of English words are recognised, and only as whole words.
    A label that overstates without using one of them is not caught, and a label
    in another language is not examined at all.

    False positives: a label may quote the vocabulary rather than assert it —
    "compared against measured values" on an estimate is accurate, not
    contradictory. Such a label should be reworded or the rule disabled.
    """

    rule_id = "EOC201"
    default_severity = Severity.WARNING
    summary = "The display label contradicts the declared claim type."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        label = document.display.label
        claim_type = document.claim.type

        if claim_type is ClaimType.OBSERVATION:
            term = _first_word_present(label, NON_MEASUREMENT_WORDS)
            expected = "an observation"
        else:
            term = _first_word_present(label, MEASUREMENT_WORDS)
            expected = (
                f"an {claim_type.value}"
                if claim_type.value[0] in "aeiou"
                else (f"a {claim_type.value}")
            )

        if term is None:
            return ()

        return (
            self.issue(
                config,
                message=(
                    f"The display label calls this '{term}' while the claim is typed "
                    f"as {expected}. A reader will believe the label."
                ),
                path="$.display",
                field_name="label",
                context={"claim_type": claim_type.value, "term": term},
            ),
        )


class DisplayUnitMismatchRule(Rule):
    """EOC202 — the displayed unit is not the unit that was recorded.

    Compared as plain strings. No unit conversion and no synonym table: this
    rule cannot tell you that "m" and "metre" agree, and it will not try.

    False positives are expected and are the main cost of this rule. A
    dimensionless value recorded as ``"1"`` and displayed as ``"index"`` is
    correct in both places, yet the strings differ. Projects that render units
    for humans should either keep the two identical or lower this rule's
    severity through configuration.
    """

    rule_id = "EOC202"
    default_severity = Severity.WARNING
    summary = "The displayed unit differs from the recorded unit."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        unit = document.claim.unit
        display_unit = document.display.display_unit

        if unit is None or display_unit is None or unit == display_unit:
            return ()

        return (
            self.issue(
                config,
                message=(
                    "The displayed unit does not match the recorded unit. This rule "
                    "compares them as plain strings and performs no conversion, so a "
                    "deliberate human-readable rendering will also be reported."
                ),
                path="$.display",
                field_name="display_unit",
                context={},
            ),
        )
