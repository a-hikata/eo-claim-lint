"""Rules about whether a claim can be traced back to anything."""

from __future__ import annotations

from eo_claim_lint.models import ClaimDocument, LintIssue, Severity
from eo_claim_lint.rules.base import Rule, RuleConfig

__all__ = ["MissingEvidenceRule"]


class MissingEvidenceRule(Rule):
    """EOC301 — the claim references no evidence at all.

    The schema permits an empty evidence array, because whether evidence is
    required is a policy question rather than a structural one. This is that
    policy: a claim published with nothing behind it cannot be checked by
    anyone, which is the failure this tool exists to prevent. Hence **error**
    rather than warning — it is the one finding here that makes a document
    unusable for its stated purpose.

    Scope note: this applies to **every** claim type, including
    ``interpretation``. Exempting interpretations would leave the least directly
    grounded kind of claim as the only one allowed to cite nothing, which
    inverts the intent.

    False positives: a project that records provenance outside the document —
    in a catalogue entry, or a signed manifest alongside it — will see this fire
    on documents that are traceable in practice. Such a project should disable
    the rule deliberately rather than add placeholder references, because a
    fabricated evidence entry is worse than an honest empty list.
    """

    rule_id = "EOC301"
    default_severity = Severity.ERROR
    summary = "A claim should reference at least one piece of evidence."

    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        if document.evidence:
            return ()
        return (
            self.issue(
                config,
                message=(
                    "This claim references no evidence. Add at least one reference so "
                    "that a reader can trace where the value came from."
                ),
                path="$",
                field_name="evidence",
                context={"claim_type": document.claim.type.value},
            ),
        )
