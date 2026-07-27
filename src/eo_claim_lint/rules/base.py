"""The contract every rule implements, and the configuration that selects rules.

A rule reads one claim document and reports what it finds. It may not touch the
filesystem, the network, the environment, or the document it was given. Those
restrictions are what make a run reproducible: the same document produces the
same findings on any machine, at any time.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Final

from eo_claim_lint.models import (
    ClaimDocument,
    EoClaimLintError,
    LintIssue,
    Severity,
)

__all__ = ["Rule", "RuleConfig", "RuleExecutionError"]

RULE_ID_PATTERN: Final = re.compile(r"^EOC[0-9]{3}$")


class RuleExecutionError(Exception):
    """Raised when a rule itself fails, as distinct from a document being wrong.

    This is deliberately **not** an :class:`EoClaimLintError`, which means "the
    document you gave me is invalid". A rule that raises has a bug, and calling
    that a document problem would report the tool's own defect as a finding
    about the user's data. Keeping the two apart is what lets a future CLI exit
    with a distinct status for "the linter broke" rather than "the document
    failed".
    """

    def __init__(self, rule_id: str, cause: BaseException) -> None:
        super().__init__(f"rule {rule_id} raised {type(cause).__name__}")
        self.rule_id = rule_id


class Rule(ABC):
    """One check over one claim document."""

    #: Stable identifier, matching ``EOC`` followed by three digits.
    rule_id: str

    #: Severity used when the configuration does not override it.
    default_severity: Severity

    #: One line describing what the rule looks for.
    summary: str

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "__abstractmethods__", frozenset()):
            return
        for attribute in ("rule_id", "default_severity", "summary"):
            if not hasattr(cls, attribute):
                raise TypeError(f"{cls.__name__} must define '{attribute}'")
        if not RULE_ID_PATTERN.match(cls.rule_id):
            raise TypeError(f"{cls.__name__}.rule_id must match EOC followed by three digits")

    @abstractmethod
    def check(self, document: ClaimDocument, config: RuleConfig) -> tuple[LintIssue, ...]:
        """Return every issue this rule finds in ``document``.

        Implementations must not modify ``document`` and must not perform I/O.
        """

    def severity(self, config: RuleConfig) -> Severity:
        return config.severity_overrides.get(self.rule_id, self.default_severity)

    def issue(
        self,
        config: RuleConfig,
        *,
        message: str,
        path: str,
        field_name: str | None = None,
        context: Mapping[str, object] | None = None,
    ) -> LintIssue:
        """Build an issue attributed to this rule.

        ``doc_url`` is left null: the rule documentation pages do not exist
        yet, and a link that resolves to nothing is worse than no link.
        """
        return LintIssue(
            rule_id=self.rule_id,
            severity=self.severity(config),
            message=message,
            path=path,
            field=field_name,
            doc_url=None,
            context={} if context is None else dict(context),
        )

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.rule_id}>"


def _frozen_ids(values: Iterable[str] | None, label: str) -> frozenset[str]:
    if values is None:
        return frozenset()
    ids = frozenset(values)
    for rule_id in sorted(ids):
        if not RULE_ID_PATTERN.match(rule_id):
            raise EoClaimLintError(f"{label}: {rule_id!r} is not a valid rule id")
    return ids


@dataclass(frozen=True)
class RuleConfig:
    """Which rules run, and how loudly they speak.

    Nothing here configures *what* a rule considers wrong. Thresholds,
    vocabularies, and domain-specific conditions are deliberately absent: a
    rule whose meaning changes with configuration is a rule whose findings
    cannot be compared between projects.
    """

    #: Rule ids to run. ``None`` means every rule in the given set.
    enabled: frozenset[str] | None = None

    #: Rule ids to skip, applied after ``enabled``.
    disabled: frozenset[str] = frozenset()

    #: Severity to use instead of a rule's default.
    severity_overrides: Mapping[str, Severity] = field(default_factory=dict)

    def __post_init__(self) -> None:
        enabled = None if self.enabled is None else _frozen_ids(self.enabled, "enabled")
        disabled = _frozen_ids(self.disabled, "disabled")
        overrides = dict(self.severity_overrides)

        for rule_id, severity in overrides.items():
            if not RULE_ID_PATTERN.match(rule_id):
                raise EoClaimLintError(f"severity_overrides: {rule_id!r} is not a valid rule id")
            if not isinstance(severity, Severity):
                raise EoClaimLintError(f"severity_overrides[{rule_id}]: expected a Severity member")

        if enabled is not None:
            both = sorted(enabled & disabled)
            if both:
                raise EoClaimLintError(
                    f"rules cannot be both enabled and disabled: {', '.join(both)}"
                )

        object.__setattr__(self, "enabled", enabled)
        object.__setattr__(self, "disabled", disabled)
        object.__setattr__(self, "severity_overrides", dict(overrides))

    def selects(self, rule_id: str) -> bool:
        if rule_id in self.disabled:
            return False
        return self.enabled is None or rule_id in self.enabled

    def referenced_ids(self) -> frozenset[str]:
        """Every rule id named anywhere in this configuration."""
        named = set(self.disabled) | set(self.severity_overrides)
        if self.enabled is not None:
            named |= set(self.enabled)
        return frozenset(named)
