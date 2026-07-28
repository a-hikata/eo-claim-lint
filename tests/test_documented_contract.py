"""Tests that the published documents describe the code that actually exists.

A linter whose subject is "what a document says versus what is true" cannot
afford a README that credits itself with checks it does not perform. These
tests hold the prose to the registry: every rule named in the documentation
exists, every rule that exists is documented, and the capabilities withdrawn
in 0.1.1 cannot come back unnoticed.

The `fail-on` cases below fix the resolution order as it stands in 0.1.x —
option, then built-in default, with nothing in between — so that adding a
configuration file later has to move a test rather than change behaviour in
silence.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest
import yaml

from action.run import Inputs, build_argv
from eo_claim_lint import get_default_rules
from eo_claim_lint.cli.parser import build_parser

PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent
README: Final = PROJECT_ROOT / "README.md"
ACTION_YML: Final = PROJECT_ROOT / "action.yml"

RULE_ID: Final = re.compile(r"\bEOC[0-9]{3}\b")

#: A row of the "What gets checked" table: `| ``EOC101`` | warning | text |`.
TABLE_ROW: Final = re.compile(r"^\|\s*`(EOC[0-9]{3})`\s*\|\s*\**(\w+)\**\s*\|")


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _section(title: str) -> str:
    """The text of one `##` section of the README, heading excluded."""
    text = _readme()
    start = text.index(f"\n## {title}\n") + len(f"\n## {title}\n")
    rest = text[start:]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


# --------------------------------------------------------------------------
# The rule table is the registry
# --------------------------------------------------------------------------


def _documented_rules() -> dict[str, str]:
    documented: dict[str, str] = {}
    for line in _section("What gets checked").splitlines():
        match = TABLE_ROW.match(line)
        if match:
            documented[match.group(1)] = match.group(2)
    return documented


def test_the_rule_table_lists_every_rule_that_exists() -> None:
    assert set(_documented_rules()) == {rule.rule_id for rule in get_default_rules()}


def test_the_rule_table_states_the_real_default_severity() -> None:
    documented = _documented_rules()

    for rule in get_default_rules():
        assert documented[rule.rule_id] == rule.default_severity.value, rule.rule_id


@pytest.mark.parametrize(
    "path",
    [README, PROJECT_ROOT / "CHANGELOG.md", PROJECT_ROOT / "examples" / "github-action.yml"],
    ids=lambda path: str(path.name),
)
def test_no_document_names_a_rule_that_does_not_exist(path: Path) -> None:
    """A reader who copies `disable: EOCxxx` from a document must get a real id."""
    known = {rule.rule_id for rule in get_default_rules()}

    assert set(RULE_ID.findall(path.read_text(encoding="utf-8"))) <= known


# --------------------------------------------------------------------------
# Capabilities the README used to claim, and the code never had
#
# Until 0.1.1 the Purpose section credited the linter with checking that
# declared layers exist, that a manifest agrees with its items, and that an
# asserted class discloses where its thresholds came from. None of the ten
# rules does any of that; the first two belong to a different tool and the
# third was never ported. Naming them again would be the exact failure this
# linter exists to report.
# --------------------------------------------------------------------------

WITHDRAWN_CAPABILITIES: Final = (
    "declared layers exist",
    "manifest and the items agree",
    "where its thresholds came from",
    "thresholds came from",
    "provenance of a threshold",
)


@pytest.mark.parametrize("phrase", WITHDRAWN_CAPABILITIES)
def test_the_readme_does_not_claim_a_withdrawn_capability(phrase: str) -> None:
    """Matched against collapsed whitespace, so line wrapping cannot hide it."""
    assert phrase not in " ".join(_readme().split()), phrase


def test_the_purpose_section_names_only_rules_that_exist() -> None:
    purpose = _section("Purpose and non-goals")
    known = {rule.rule_id for rule in get_default_rules()}

    named = set(RULE_ID.findall(purpose))
    assert named, "the purpose section should point at the rules it describes"
    assert named <= known


def test_the_purpose_section_says_what_is_not_read() -> None:
    """The withdrawn wording is replaced by a statement, not by a silence."""
    purpose = " ".join(_section("Purpose and non-goals").split())

    assert "no manifest, no layer inventory" in purpose


# --------------------------------------------------------------------------
# There is no configuration file in 0.1.x
# --------------------------------------------------------------------------


@pytest.mark.parametrize("option", ["--config", "--no-config"])
def test_the_cli_offers_no_configuration_option(option: str) -> None:
    """`--config` arriving without this test being updated would be an accident."""
    with pytest.raises(SystemExit) as raised:
        build_parser().parse_args(["check", option, "document.json"])

    assert raised.value.code == 2


def test_nothing_in_the_package_reads_a_configuration_file() -> None:
    sources = [
        *(PROJECT_ROOT / "src").rglob("*.py"),
        *(PROJECT_ROOT / "action").rglob("*.py"),
    ]

    for path in sources:
        text = path.read_text(encoding="utf-8")
        assert "import tomllib" not in text, path
        assert "tomllib." not in text, path


def test_the_readme_states_that_no_configuration_file_is_read() -> None:
    limitations = " ".join(_section("Limitations").split())

    assert "No configuration file." in limitations
    assert "in a parent directory" in limitations


# --------------------------------------------------------------------------
# `fail-on` resolves the same way on both surfaces
# --------------------------------------------------------------------------


def test_the_cli_threshold_defaults_to_error() -> None:
    arguments = build_parser().parse_args(["check", "document.json"])

    assert arguments.fail_on == "error"


def test_the_action_input_defaults_to_error() -> None:
    action = dict(yaml.safe_load(ACTION_YML.read_text(encoding="utf-8")))

    assert action["inputs"]["fail-on"]["default"] == "error"


@pytest.mark.parametrize("supplied", ["", "   ", "\n"])
def test_an_empty_action_input_means_error_rather_than_unset(supplied: str) -> None:
    """0.1.x has no third answer: an empty input resolves to the same default."""
    inputs = Inputs.from_environ({"INPUT_FILES": "claims/a.json", "INPUT_FAIL_ON": supplied})

    assert inputs.fail_on == "error"


def test_the_action_always_passes_the_threshold_to_the_cli(tmp_path: Path) -> None:
    """While no configuration file exists, the CLI is never left to decide."""
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims" / "a.json").write_text("{}", encoding="utf-8")
    inputs = Inputs.from_environ({"INPUT_FILES": "claims/a.json"})

    argv = build_argv(inputs, base=tmp_path.resolve(), workspace=tmp_path.resolve())

    assert argv.count("--fail-on") == 1
    assert argv[argv.index("--fail-on") + 1] == "error"


def test_the_documented_threshold_table_matches_both_defaults() -> None:
    section = " ".join(_section("Command line").split())

    assert "Where the fail threshold comes from" in section
    assert "the Action passes `--fail-on error` on your behalf" in section
