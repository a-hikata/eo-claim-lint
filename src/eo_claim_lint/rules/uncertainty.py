"""Rules about whether a claim admits how unsure it is."""

from __future__ import annotations

import re
from typing import Final

from eo_claim_lint.models import ClaimDocument, ClaimType, LintIssue, Severity, UncertaintyKind
from eo_claim_lint.rules.base import Rule, RuleConfig

__all__ = ["DefinitiveWordingRule", "EstimateUncertaintyRule"]


class EstimateUncertaintyRule(Rule):
    """EOC101 — an estimate that declares no uncertainty.

    An estimate is a number a model produced, and a model that cannot say how
    far off it might be has told the reader only half of what it knows. The
    schema allows the omission on purpose, because whether it is acceptable
    depends on the project; this rule is where that judgement lives.

    False positives: a claim can be legitimately typed as an estimate while its
    uncertainty is recorded elsewhere, for example in a companion dataset. Such
    a project should disable this rule rather than invent an uncertainty block.
    """

    rule_id = "EOC101"
    default_severity = Severity.WARNING
    summary = "An estimate should declare its uncertainty."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        if document.claim.type is not ClaimType.ESTIMATE:
            return ()
        if document.claim.uncertainty is not None:
            return ()
        return (
            self.issue(
                config,
                message=(
                    "This claim is typed as an estimate but declares no uncertainty. "
                    "State an interval, a standard deviation, or a qualitative "
                    "description, or record that it is unknown."
                ),
                path="$.claim",
                field_name="uncertainty",
                context={"claim_type": document.claim.type.value},
            ),
        )


# Words that assert exactness. Kept short and English-only on purpose: this is
# not a prose linter, and a longer list would start making style judgements
# instead of contradiction checks. Other languages wait until vocabularies can
# be supplied through configuration.
DEFINITIVE_TERMS: Final = (
    "exactly",
    "precisely",
    "confirmed",
    "proven",
    "guaranteed",
    "certain",
    "definitive",
)

_WORD = re.compile(r"[a-z]+")


def _contains_definitive_term(text: str) -> str | None:
    words = set(_WORD.findall(text.lower()))
    for term in DEFINITIVE_TERMS:
        if term in words:
            return term
    return None


class DefinitiveWordingRule(Rule):
    """EOC203 — definitive wording while the uncertainty is unquantified.

    A claim may honestly say its uncertainty is unknown. What it may not do is
    say that and then describe the result as confirmed or exact. The two
    statements contradict each other, and a reader who sees only the prose will
    believe the stronger one.

    This checks a fixed, short list of English adverbs and adjectives. It is not
    a prose linter and will not catch a claim that overstates its confidence
    without using one of those words.

    False positives: a word such as "certain" can appear in an unrelated sense
    ("certain fields were excluded"). The rule looks at the display label and
    the statement only, where such usage is rare but possible.
    """

    rule_id = "EOC203"
    default_severity = Severity.WARNING
    summary = "Definitive wording contradicts an unquantified uncertainty."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        uncertainty = document.claim.uncertainty
        if uncertainty is None or uncertainty.kind is not UncertaintyKind.UNKNOWN:
            return ()

        issues: list[LintIssue] = []
        for text, path, field_name in (
            (document.display.label, "$.display", "label"),
            (document.claim.statement, "$.claim", "statement"),
        ):
            term = _contains_definitive_term(text)
            if term is None:
                continue
            issues.append(
                self.issue(
                    config,
                    message=(
                        f"The uncertainty is declared unknown, but this text calls the "
                        f"result '{term}'. Either quantify the uncertainty or soften "
                        f"the wording."
                    ),
                    path=path,
                    field_name=field_name,
                    context={"term": term},
                )
            )
        return tuple(issues)
