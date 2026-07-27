"""What each subcommand does.

Every command writes to a stream the caller supplies, so that tests can read
the output without touching the process's real stdout.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final, TextIO

from eo_claim_lint.cli.errors import CliUsageError
from eo_claim_lint.cli.exit_codes import ExitCode
from eo_claim_lint.cli.input import load_documents
from eo_claim_lint.cli.output import (
    FileReport,
    determine_exit_code,
    format_github,
    format_json,
    format_text,
)
from eo_claim_lint.engine import lint_document
from eo_claim_lint.models import EoClaimLintError, Severity
from eo_claim_lint.rules import RuleConfig, get_default_rules, get_rule
from eo_claim_lint.schema import (
    load_claim_document_schema,
    load_cli_output_schema,
    load_lint_output_schema,
)

__all__ = ["EXAMPLE_DOCUMENT", "run_check", "run_init", "run_rules", "run_schema"]

_SCHEMA_LOADERS: Final = {
    "claim": load_claim_document_schema,
    "lint-output": load_lint_output_schema,
    "cli-output": load_cli_output_schema,
}

#: A document that is entirely fictional and that every default rule accepts.
#: Anyone running `init` should get a working example on the first try, not a
#: pile of warnings to decipher before they have learned what the tool does.
EXAMPLE_DOCUMENT: Final[dict[str, object]] = {
    "schema_version": "0.1",
    "claim_id": "claim-001",
    "claim": {
        "type": "observation",
        "statement": "A vegetation index was computed for the specified area.",
        "value": 0.42,
        "unit": "1",
    },
    "data_origin": "synthetic",
    "data_processing": "derived",
    "spatial_scope": {"type": "named_area", "name": "Example Area"},
    "temporal_scope": {"observed_at": "2026-01-15T01:30:00Z"},
    "evidence": [
        {
            "id": "evidence-001",
            "type": "dataset",
            "title": "Example synthetic source record",
            "uri": "urn:example:evidence:001",
        }
    ],
    "display": {
        "label": "Vegetation index for the area",
        "disclaimer": "Generated for demonstration; not recorded by an instrument.",
    },
    "processing": {"method": "Example index calculation"},
}


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _write(text: str, *, output: str | None, force: bool, stream: TextIO) -> None:
    if output is None:
        stream.write(text)
        return

    path = Path(output)
    if path.exists() and not force:
        raise CliUsageError(f"{output}: already exists; pass --force to overwrite")
    try:
        path.write_text(text, encoding="utf-8")
    except IsADirectoryError as exc:
        raise CliUsageError(f"{output}: is a directory") from exc
    except OSError as exc:
        raise CliUsageError(f"{output}: cannot be written ({exc.strerror})") from exc


def _build_config(args: argparse.Namespace) -> RuleConfig:
    overrides: dict[str, Severity] = {}
    for raw in args.severity:
        rule_id, separator, value = raw.partition("=")
        if not separator:
            raise CliUsageError(f"--severity {raw!r}: expected RULE_ID=SEVERITY")
        try:
            overrides[rule_id] = Severity(value)
        except ValueError as exc:
            allowed = ", ".join(member.value for member in Severity)
            raise CliUsageError(
                f"--severity {raw!r}: unknown severity; expected one of {allowed}"
            ) from exc

    try:
        return RuleConfig(
            enabled=frozenset(args.enable) if args.enable else None,
            disabled=frozenset(args.disable),
            severity_overrides=overrides,
        )
    except EoClaimLintError as exc:
        raise CliUsageError(str(exc)) from exc


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------


def run_check(args: argparse.Namespace, *, stdout: TextIO) -> ExitCode:
    """Lint the given documents and report."""
    config = _build_config(args)
    loaded = load_documents(args.files, stdin_name=args.stdin_name)

    try:
        reports = tuple(
            FileReport(item.source, lint_document(item.document, config=config)) for item in loaded
        )
    except EoClaimLintError as exc:
        # The engine rejects a configuration that names a rule it does not have.
        raise CliUsageError(str(exc)) from exc

    if args.output_format == "json":
        rendered = format_json(reports)
    elif args.output_format == "github":
        rendered = format_github(reports, quiet=args.quiet)
    else:
        rendered = format_text(reports, quiet=args.quiet)

    _write(rendered, output=args.output, force=args.force, stream=stdout)
    return determine_exit_code(reports, Severity(args.fail_on))


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------


def _rule_payload(rule_id: str) -> dict[str, object]:
    rule = get_rule(rule_id)
    return {
        "rule_id": rule.rule_id,
        "default_severity": rule.default_severity.value,
        "summary": rule.summary,
        "category": f"EOC{rule.rule_id[3]}xx",
        "doc_url": None,
    }


def run_rules(args: argparse.Namespace, *, stdout: TextIO) -> ExitCode:
    """List the available rules, or describe one."""
    if args.rule is not None:
        try:
            payloads = [_rule_payload(args.rule)]
        except EoClaimLintError as exc:
            raise CliUsageError(str(exc)) from exc
    else:
        payloads = [_rule_payload(rule.rule_id) for rule in get_default_rules()]

    if args.output_format == "json":
        stdout.write(json.dumps({"rules": payloads}, ensure_ascii=False, indent=2) + "\n")
        return ExitCode.SUCCESS

    for payload in payloads:
        stdout.write(
            f"{payload['rule_id']}  {str(payload['default_severity']):<7}  {payload['summary']}\n"
        )
    return ExitCode.SUCCESS


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------


def run_schema(args: argparse.Namespace, *, stdout: TextIO) -> ExitCode:
    """Print a bundled schema."""
    loader = _SCHEMA_LOADERS[args.name]
    rendered = json.dumps(loader(), ensure_ascii=False, indent=2) + "\n"
    _write(rendered, output=args.output, force=args.force, stream=stdout)
    return ExitCode.SUCCESS


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------


def run_init(args: argparse.Namespace, *, stdout: TextIO) -> ExitCode:
    """Write an example claim document."""
    rendered = json.dumps(EXAMPLE_DOCUMENT, ensure_ascii=False, indent=2) + "\n"

    if args.stdout:
        stdout.write(rendered)
        return ExitCode.SUCCESS

    _write(rendered, output=args.path, force=args.force, stream=stdout)
    return ExitCode.SUCCESS
