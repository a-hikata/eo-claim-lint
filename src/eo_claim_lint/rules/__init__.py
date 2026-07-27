"""The rule registry.

The default set is built once, at import, from a literal tuple. There is no
mutable global registry and no plugin discovery: a run that produces different
findings depending on what happened to be installed is not reproducible, and
reproducibility is the property this tool sells.

Building the tuple performs no I/O and reads no environment.
"""

from __future__ import annotations

from typing import Final

from eo_claim_lint.models import EoClaimLintError
from eo_claim_lint.rules.base import Rule, RuleConfig, RuleExecutionError
from eo_claim_lint.rules.claim_type import (
    InterpretationQualificationRule,
    ObservationProcessingRule,
)
from eo_claim_lint.rules.data_semantics import (
    SyntheticDisclosureRule,
    UnknownOriginDisclosureRule,
)
from eo_claim_lint.rules.display import DisplayLabelContradictionRule, DisplayUnitMismatchRule
from eo_claim_lint.rules.evidence import MissingEvidenceRule
from eo_claim_lint.rules.provenance import ModeledSoftwareRule
from eo_claim_lint.rules.uncertainty import DefinitiveWordingRule, EstimateUncertaintyRule

__all__ = [
    "Rule",
    "RuleConfig",
    "RuleExecutionError",
    "get_default_rules",
    "get_rule",
]


def _build_default_rules() -> tuple[Rule, ...]:
    rules: tuple[Rule, ...] = (
        # EOC1xx — observation, estimate, interpretation
        EstimateUncertaintyRule(),
        ObservationProcessingRule(),
        InterpretationQualificationRule(),
        # EOC2xx — claim safety and display consistency
        DisplayLabelContradictionRule(),
        DisplayUnitMismatchRule(),
        DefinitiveWordingRule(),
        # EOC3xx — evidence, provenance, processing
        MissingEvidenceRule(),
        ModeledSoftwareRule(),
        # EOC4xx — data origin and processing state
        SyntheticDisclosureRule(),
        UnknownOriginDisclosureRule(),
    )

    seen: dict[str, Rule] = {}
    for rule in rules:
        if rule.rule_id in seen:
            raise EoClaimLintError(f"duplicate rule id: {rule.rule_id}")
        seen[rule.rule_id] = rule

    # Sorting by id makes the execution order independent of the order rules
    # happen to be listed above.
    return tuple(sorted(rules, key=lambda item: item.rule_id))


_DEFAULT_RULES: Final = _build_default_rules()
_BY_ID: Final = {rule.rule_id: rule for rule in _DEFAULT_RULES}


def get_default_rules() -> tuple[Rule, ...]:
    """Every rule that runs unless the caller says otherwise, ordered by id.

    The tuple is immutable, and rules hold no state, so a caller cannot change
    what a later caller receives.
    """
    return _DEFAULT_RULES


def get_rule(rule_id: str) -> Rule:
    """Return one rule by id.

    Raises :class:`EoClaimLintError` if no such rule exists.
    """
    try:
        return _BY_ID[rule_id]
    except KeyError:
        known = ", ".join(sorted(_BY_ID))
        raise EoClaimLintError(f"unknown rule id: {rule_id!r}; known ids are {known}") from None
