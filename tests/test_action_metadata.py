"""Contract tests for `action.yml` and the self-test workflow.

These are static checks over the metadata. They cannot prove the action runs on
a GitHub-hosted runner — nothing local can — but they can prove that the
properties we promise are actually written down: no secrets, no write
permissions, no unpinned third-party actions, no shell evaluation of input.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Final

import pytest
import yaml

PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent
ACTION_YML: Final = PROJECT_ROOT / "action.yml"
WORKFLOWS: Final = PROJECT_ROOT / ".github" / "workflows"

EXPECTED_INPUTS: Final = frozenset(
    {
        "files",
        "fail-on",
        "enable",
        "disable",
        "severity",
        "python-version",
        "working-directory",
    }
)

EXPECTED_OUTPUTS: Final = frozenset({"exit-code", "outcome"})

#: A `uses:` reference is pinned when it names a 40-character commit.
PINNED_USES: Final = re.compile(r"^[\w.\-]+/[\w.\-]+@[0-9a-f]{40}$")


@pytest.fixture(scope="module")
def action() -> dict[str, Any]:
    return dict(yaml.safe_load(ACTION_YML.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def action_text() -> str:
    return ACTION_YML.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------


def test_action_yml_exists_at_the_repository_root() -> None:
    """GitHub only looks for it here."""
    assert ACTION_YML.is_file()


def test_metadata_is_present(action: dict[str, Any]) -> None:
    assert action["name"] == "EO Claim Lint"
    assert action["description"].strip()
    assert action["author"] == "Takahito Suzuki"


def test_branding_uses_permitted_values(action: dict[str, Any]) -> None:
    assert action["branding"]["icon"] == "check-circle"
    assert action["branding"]["color"] == "blue"


def test_it_is_a_composite_action(action: dict[str, Any]) -> None:
    assert action["runs"]["using"] == "composite"


def test_no_email_address_in_the_metadata(action_text: str) -> None:
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", action_text)


# --------------------------------------------------------------------------
# Inputs and outputs
# --------------------------------------------------------------------------


def test_inputs_are_exactly_the_documented_set(action: dict[str, Any]) -> None:
    assert set(action["inputs"]) == EXPECTED_INPUTS


def test_only_files_is_required(action: dict[str, Any]) -> None:
    required = {name for name, spec in action["inputs"].items() if spec.get("required")}

    assert required == {"files"}


def test_every_optional_input_has_a_default(action: dict[str, Any]) -> None:
    for name, spec in action["inputs"].items():
        if spec.get("required"):
            continue
        assert "default" in spec, name


def test_defaults_match_the_cli(action: dict[str, Any]) -> None:
    inputs = action["inputs"]

    assert inputs["fail-on"]["default"] == "error"
    assert inputs["python-version"]["default"] == "3.11"
    assert inputs["working-directory"]["default"] == "."


def test_every_input_is_described(action: dict[str, Any]) -> None:
    for name, spec in action["inputs"].items():
        assert spec.get("description", "").strip(), name


def test_outputs_are_exactly_the_documented_set(action: dict[str, Any]) -> None:
    assert set(action["outputs"]) == EXPECTED_OUTPUTS


def test_outputs_come_from_the_run_step(action: dict[str, Any]) -> None:
    for name, spec in action["outputs"].items():
        assert "steps.eo-claim-lint.outputs" in spec["value"], name


# --------------------------------------------------------------------------
# Steps
# --------------------------------------------------------------------------


def test_every_run_step_declares_a_shell(action: dict[str, Any]) -> None:
    for step in action["runs"]["steps"]:
        if "run" in step:
            assert step.get("shell") == "bash"


def test_third_party_actions_are_pinned_to_a_commit(action: dict[str, Any]) -> None:
    """A moving tag lets someone else change what runs in a user's workflow."""
    uses = [step["uses"] for step in action["runs"]["steps"] if "uses" in step]

    assert uses, "the action should set up Python itself"
    for reference in uses:
        assert PINNED_USES.match(reference), reference


def test_the_package_is_installed_from_the_action_checkout(action_text: str) -> None:
    """Never from a package index: the code that runs is the code at this ref."""
    assert 'pip install --disable-pip-version-check "$GITHUB_ACTION_PATH"' in action_text
    assert "pip install eo-claim-lint" not in action_text


def test_the_wrapper_is_invoked_by_path(action_text: str) -> None:
    assert 'python "$GITHUB_ACTION_PATH/action/run.py"' in action_text


def test_inputs_reach_the_wrapper_through_the_environment(action: dict[str, Any]) -> None:
    """Interpolating an input into a `run:` block would hand the caller a shell."""
    run_step = next(step for step in action["runs"]["steps"] if step.get("id") == "eo-claim-lint")

    assert set(run_step["env"]) == {
        "INPUT_FILES",
        "INPUT_FAIL_ON",
        "INPUT_ENABLE",
        "INPUT_DISABLE",
        "INPUT_SEVERITY",
        "INPUT_WORKING_DIRECTORY",
    }
    assert "${{" not in run_step["run"]


def test_no_step_evaluates_a_string_as_a_command(action_text: str) -> None:
    for forbidden in ("eval ", "eval\t", "set -x", "sh -c", "bash -c"):
        assert forbidden not in action_text


def test_the_action_requests_no_permissions_or_secrets(action_text: str) -> None:
    """Annotations travel as workflow commands, so nothing beyond read is needed."""
    for forbidden in ("secrets.", "permissions:", "id-token", "GITHUB_TOKEN"):
        assert forbidden not in action_text


# --------------------------------------------------------------------------
# Self-test workflow
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def self_test() -> dict[str, Any]:
    return dict(yaml.safe_load((WORKFLOWS / "action-test.yml").read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def self_test_text() -> str:
    return (WORKFLOWS / "action-test.yml").read_text(encoding="utf-8")


def test_self_test_workflow_exists(self_test: dict[str, Any]) -> None:
    assert self_test["name"] == "Action self-test"


def test_self_test_uses_the_local_action(self_test_text: str) -> None:
    assert "uses: ./" in self_test_text


def test_self_test_runs_with_read_only_permissions(self_test: dict[str, Any]) -> None:
    assert self_test["permissions"] == {"contents": "read"}


def test_self_test_never_uses_pull_request_target(self_test_text: str) -> None:
    assert "pull_request_target" not in self_test_text


def test_self_test_requests_no_secrets(self_test_text: str) -> None:
    assert "secrets." not in self_test_text


def test_self_test_covers_every_outcome(self_test_text: str) -> None:
    for outcome in ("passed", "lint-failed", "usage-error"):
        assert outcome in self_test_text


def test_self_test_checkout_is_pinned(self_test_text: str) -> None:
    for reference in re.findall(r"uses: (actions/[\w.\-]+@\S+)", self_test_text):
        assert PINNED_USES.match(reference), reference


# --------------------------------------------------------------------------
# Documentation must be copy-pasteable
# --------------------------------------------------------------------------

REPOSITORY_SLUG: Final = "a-hikata/eo-claim-lint"

DOCS_WITH_USAGE: Final = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "examples" / "github-action.yml",
)


@pytest.mark.parametrize("path", DOCS_WITH_USAGE, ids=[p.name for p in DOCS_WITH_USAGE])
def test_no_placeholder_owner_remains(path: Path) -> None:
    """A `uses:` line a reader cannot copy is worse than no example at all."""
    text = path.read_text(encoding="utf-8")

    for placeholder in ("OWNER/", "<owner>", "YOUR_ORG", "example-org/"):
        assert placeholder not in text, f"{path.name} still contains {placeholder!r}"


@pytest.mark.parametrize("path", DOCS_WITH_USAGE, ids=[p.name for p in DOCS_WITH_USAGE])
def test_usage_examples_name_this_repository(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    for reference in re.findall(r"uses: ([\w.\-]+/[\w.\-]+)@", text):
        if reference.startswith("actions/"):
            continue
        assert reference == REPOSITORY_SLUG, reference


def test_readme_leads_with_the_action() -> None:
    """A Marketplace visitor should reach a working workflow without scrolling far."""
    lines = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").splitlines()

    quick_start = next(i for i, line in enumerate(lines) if line.startswith("## Quick start"))
    usage = next(i for i, line in enumerate(lines) if REPOSITORY_SLUG in line and "uses:" in line)

    assert quick_start < 30, "Quick start should be near the top"
    assert usage < 45, "a copy-pasteable workflow should appear in the first screenful"


# --------------------------------------------------------------------------
# Existing CI is untouched by this task
# --------------------------------------------------------------------------


def test_ci_workflow_still_requests_only_read(self_test: dict[str, Any]) -> None:
    ci = dict(yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8")))

    assert ci["permissions"] == {"contents": "read"}


def test_no_workflow_requests_write_access() -> None:
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        for forbidden in ("contents: write", "id-token: write", "packages: write"):
            assert forbidden not in text, f"{path.name} requests {forbidden}"
