"""Tests for the GitHub Action wrapper.

The wrapper is the layer where caller-supplied strings become an argument list,
so most of these are about the ways a string can escape the list it belongs in:
option injection, path traversal, symlinks pointing out of the checkout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import pytest

from action.run import (
    ActionInputError,
    Inputs,
    build_argv,
    expand_files,
    main,
    outcome_for,
    resolve_working_directory,
    split_lines,
    write_outputs,
    write_summary,
)

FIXTURES: Final = Path(__file__).resolve().parent / "fixtures"
CLEAN: Final = FIXTURES / "lint_valid" / "observation-fully-qualified.json"
ERROR_DOC: Final = FIXTURES / "lint_invalid" / "interpretation-without-evidence.json"
WARNING_DOC: Final = FIXTURES / "lint_invalid" / "estimate-without-uncertainty.json"


def _inputs(**overrides: str) -> Inputs:
    base = {
        "files": "claim.json",
        "fail_on": "error",
        "enable": "",
        "disable": "",
        "severity": "",
        "working_directory": ".",
    }
    base.update(overrides)
    return Inputs(**base)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A checkout containing one clean and one failing document."""
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims" / "clean.json").write_text(
        CLEAN.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "claims" / "bad.json").write_text(
        ERROR_DOC.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return tmp_path.resolve()


# --------------------------------------------------------------------------
# Input splitting
# --------------------------------------------------------------------------


def test_lines_are_the_only_separator() -> None:
    assert split_lines("a.json\nb.json") == ("a.json", "b.json")


def test_a_path_may_contain_spaces() -> None:
    """Splitting on whitespace would make this path impossible to express."""
    assert split_lines("my claims/a.json") == ("my claims/a.json",)


def test_blank_lines_are_dropped() -> None:
    assert split_lines("\n a.json \n\n\n b.json\n") == ("a.json", "b.json")


def test_an_empty_input_yields_nothing() -> None:
    assert split_lines("") == ()
    assert split_lines("   \n  ") == ()


# --------------------------------------------------------------------------
# working-directory
# --------------------------------------------------------------------------


def test_the_workspace_root_is_allowed(workspace: Path) -> None:
    assert resolve_working_directory(".", workspace) == workspace


def test_a_subdirectory_is_allowed(workspace: Path) -> None:
    assert resolve_working_directory("claims", workspace) == workspace / "claims"


def test_escaping_the_workspace_is_refused(workspace: Path) -> None:
    with pytest.raises(ActionInputError, match="outside the workspace"):
        resolve_working_directory("..", workspace)


def test_a_deep_escape_is_refused(workspace: Path) -> None:
    with pytest.raises(ActionInputError, match="outside the workspace"):
        resolve_working_directory("claims/../../..", workspace)


def test_an_absolute_path_outside_the_workspace_is_refused(
    workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    elsewhere = tmp_path_factory.mktemp("elsewhere")

    with pytest.raises(ActionInputError, match="outside the workspace"):
        resolve_working_directory(str(elsewhere), workspace)


def test_a_symlink_leading_out_of_the_workspace_is_refused(
    workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """`resolve()` follows the link, so containment catches it."""
    elsewhere = tmp_path_factory.mktemp("outside")
    (workspace / "escape").symlink_to(elsewhere, target_is_directory=True)

    with pytest.raises(ActionInputError, match="outside the workspace"):
        resolve_working_directory("escape", workspace)


def test_a_symlink_inside_the_workspace_is_allowed(workspace: Path) -> None:
    (workspace / "alias").symlink_to(workspace / "claims", target_is_directory=True)

    assert resolve_working_directory("alias", workspace) == workspace / "claims"


def test_a_missing_directory_is_refused(workspace: Path) -> None:
    with pytest.raises(ActionInputError, match="not a directory"):
        resolve_working_directory("nope", workspace)


def test_a_file_is_not_a_directory(workspace: Path) -> None:
    with pytest.raises(ActionInputError, match="not a directory"):
        resolve_working_directory("claims/clean.json", workspace)


# --------------------------------------------------------------------------
# File expansion
# --------------------------------------------------------------------------


def test_a_literal_path_is_matched(workspace: Path) -> None:
    assert expand_files(["claims/clean.json"], workspace, workspace) == ("claims/clean.json",)


def test_a_glob_is_expanded_and_sorted(workspace: Path) -> None:
    assert expand_files(["claims/*.json"], workspace, workspace) == (
        "claims/bad.json",
        "claims/clean.json",
    )


def test_several_patterns_are_kept_in_order(workspace: Path) -> None:
    matched = expand_files(["claims/clean.json", "claims/bad.json"], workspace, workspace)

    assert matched == ("claims/clean.json", "claims/bad.json")


def test_a_duplicate_match_is_reported_once(workspace: Path) -> None:
    matched = expand_files(["claims/*.json", "claims/clean.json"], workspace, workspace)

    assert matched.count("claims/clean.json") == 1


def test_no_patterns_is_an_error(workspace: Path) -> None:
    with pytest.raises(ActionInputError, match="at least one"):
        expand_files([], workspace, workspace)


def test_a_pattern_matching_nothing_is_an_error(workspace: Path) -> None:
    """Silently checking zero files would report success for an unchecked repository."""
    with pytest.raises(ActionInputError, match="no file matched"):
        expand_files(["claims/*.yaml"], workspace, workspace)


def test_a_directory_is_not_a_match(workspace: Path) -> None:
    with pytest.raises(ActionInputError, match="no file matched"):
        expand_files(["claims"], workspace, workspace)


def test_a_path_with_a_space_is_matched(workspace: Path) -> None:
    (workspace / "my claims").mkdir()
    (workspace / "my claims" / "a.json").write_text(
        CLEAN.read_text(encoding="utf-8"), encoding="utf-8"
    )

    assert expand_files(["my claims/a.json"], workspace, workspace) == ("my claims/a.json",)


def test_a_leading_dash_is_neutralised(workspace: Path) -> None:
    """`-x.json` would be read as an option however the argument list is built."""
    (workspace / "-x.json").write_text(CLEAN.read_text(encoding="utf-8"), encoding="utf-8")

    assert expand_files(["-x.json"], workspace, workspace) == ("./-x.json",)


def test_a_symlink_pointing_out_of_the_workspace_is_refused(
    workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    elsewhere = tmp_path_factory.mktemp("outside")
    secret = elsewhere / "secret.json"
    secret.write_text(CLEAN.read_text(encoding="utf-8"), encoding="utf-8")
    (workspace / "leak.json").symlink_to(secret)

    with pytest.raises(ActionInputError, match="outside the workspace"):
        expand_files(["leak.json"], workspace, workspace)


# --------------------------------------------------------------------------
# Path anchoring (regression: annotations were attached to the wrong file)
# --------------------------------------------------------------------------


def test_the_default_working_directory_is_unchanged(workspace: Path) -> None:
    """With the default, workspace-relative and base-relative are the same string."""
    assert expand_files(["claims/*.json"], workspace, workspace) == (
        "claims/bad.json",
        "claims/clean.json",
    )


def test_paths_are_anchored_to_the_workspace_not_the_working_directory(
    workspace: Path,
) -> None:
    """GitHub resolves an annotation's `file=` against the workspace root."""
    (workspace / "data").mkdir()
    (workspace / "data" / "nested").mkdir()
    (workspace / "data" / "nested" / "a.json").write_text(
        CLEAN.read_text(encoding="utf-8"), encoding="utf-8"
    )

    matched = expand_files(["nested/a.json"], workspace / "data", workspace)

    assert matched == ("data/nested/a.json",)


def test_patterns_are_still_matched_against_the_working_directory(
    workspace: Path,
) -> None:
    """The input still means "resolve my patterns here"; only the output moved."""
    (workspace / "data").mkdir()
    (workspace / "data" / "a.json").write_text(CLEAN.read_text(encoding="utf-8"), encoding="utf-8")

    matched = expand_files(["a.json"], workspace / "data", workspace)

    assert matched == ("data/a.json",)
    with pytest.raises(ActionInputError, match="no file matched"):
        expand_files(["a.json"], workspace, workspace)


def test_a_leading_dash_is_neutralised_under_a_working_directory(
    workspace: Path,
) -> None:
    """The `./` guard applies to the anchored path, not the pre-anchoring one."""
    (workspace / "-data").mkdir()
    (workspace / "-data" / "a.json").write_text(CLEAN.read_text(encoding="utf-8"), encoding="utf-8")

    assert expand_files(["a.json"], workspace / "-data", workspace) == ("./-data/a.json",)


def test_paths_use_forward_slashes(workspace: Path) -> None:
    """Annotations are read by GitHub, which wants posix separators everywhere."""
    (workspace / "data").mkdir()
    (workspace / "data" / "a.json").write_text(CLEAN.read_text(encoding="utf-8"), encoding="utf-8")

    for name in expand_files(["a.json"], workspace / "data", workspace):
        assert "\\" not in name


def test_duplicates_are_collapsed_after_anchoring(workspace: Path) -> None:
    """Two patterns reaching the same file through different bases report once."""
    (workspace / "data").mkdir()
    (workspace / "data" / "a.json").write_text(CLEAN.read_text(encoding="utf-8"), encoding="utf-8")

    matched = expand_files(["a.json", "a.json"], workspace / "data", workspace)

    assert matched == ("data/a.json",)


def test_annotation_names_the_path_from_the_repository_root(
    workspace: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end: the annotation must point at a path that exists from the root."""
    (workspace / "data").mkdir()
    (workspace / "data" / "bad.json").write_text(
        ERROR_DOC.read_text(encoding="utf-8"), encoding="utf-8"
    )

    code = main(_environ(workspace, tmp_path, files="bad.json", working_directory="data"))
    annotation = capsys.readouterr().out

    assert code == 1
    assert "file=data/bad.json," in annotation
    assert (workspace / "data/bad.json").is_file()


def test_glob_does_not_recurse(workspace: Path) -> None:
    """The CLI has no recursive mode; the action must not invent one."""
    (workspace / "claims" / "nested").mkdir()
    (workspace / "claims" / "nested" / "deep.json").write_text("{}", encoding="utf-8")

    assert expand_files(["claims/*.json"], workspace, workspace) == (
        "claims/bad.json",
        "claims/clean.json",
    )


# --------------------------------------------------------------------------
# Argument construction
# --------------------------------------------------------------------------


def test_argv_starts_with_check_in_github_format(workspace: Path) -> None:
    argv = build_argv(_inputs(files="claims/clean.json"), base=workspace, workspace=workspace)

    assert argv[:5] == ["check", "--format", "github", "--fail-on", "error"]


def test_paths_come_after_a_double_dash(workspace: Path) -> None:
    argv = build_argv(_inputs(files="claims/clean.json"), base=workspace, workspace=workspace)

    assert argv[-2] == "--"
    assert argv[-1] == "claims/clean.json"


def test_rule_selection_becomes_repeated_options(workspace: Path) -> None:
    argv = build_argv(
        _inputs(
            files="claims/clean.json",
            enable="EOC101\nEOC301",
            disable="EOC202",
            severity="EOC101=error\nEOC401=info",
        ),
        base=workspace,
        workspace=workspace,
    )

    assert argv.count("--enable") == 2
    assert argv.count("--disable") == 1
    assert argv.count("--severity") == 2
    assert "EOC401=info" in argv


def test_an_unknown_fail_on_is_refused(workspace: Path) -> None:
    with pytest.raises(ActionInputError, match="fail-on"):
        build_argv(
            _inputs(files="claims/clean.json", fail_on="fatal"),
            base=workspace,
            workspace=workspace,
        )


@pytest.mark.parametrize("value", ["error", "warning", "info"])
def test_every_documented_fail_on_is_accepted(value: str, workspace: Path) -> None:
    argv = build_argv(
        _inputs(files="claims/clean.json", fail_on=value), base=workspace, workspace=workspace
    )

    assert value in argv


def test_shell_metacharacters_stay_inside_one_argument(workspace: Path) -> None:
    """Nothing is ever handed to a shell, so a metacharacter is just a character."""
    hostile = "claims/clean.json; rm -rf /"

    with pytest.raises(ActionInputError, match="no file matched"):
        build_argv(_inputs(files=hostile), base=workspace, workspace=workspace)


def test_an_option_looking_rule_id_stays_an_argument(workspace: Path) -> None:
    """The CLI rejects it as a bad rule id; it never becomes a flag."""
    argv = build_argv(
        _inputs(files="claims/clean.json", disable="--output=/tmp/x"),
        base=workspace,
        workspace=workspace,
    )

    assert argv[argv.index("--disable") + 1] == "--output=/tmp/x"


# --------------------------------------------------------------------------
# Outcome mapping
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (0, "passed"),
        (1, "lint-failed"),
        (2, "usage-error"),
        (3, "internal-error"),
    ],
)
def test_outcome_mapping(code: int, expected: str) -> None:
    assert outcome_for(code) == expected


def test_an_unexpected_code_is_treated_as_our_failure() -> None:
    assert outcome_for(99) == "internal-error"


# --------------------------------------------------------------------------
# GitHub environment files
# --------------------------------------------------------------------------


def test_outputs_are_written_in_the_expected_format(tmp_path: Path) -> None:
    target = tmp_path / "github_output"

    write_outputs(1, path=str(target))

    assert target.read_text(encoding="utf-8") == "exit-code=1\noutcome=lint-failed\n"


def test_outputs_are_skipped_when_github_gave_us_no_file() -> None:
    write_outputs(0, path=None)


def test_the_summary_names_the_outcome(tmp_path: Path) -> None:
    target = tmp_path / "summary.md"

    write_summary(_inputs(), 1, path=str(target), version="0.1.0")
    rendered = target.read_text(encoding="utf-8")

    assert "lint-failed" in rendered
    assert "exit code 1" in rendered


def test_the_summary_cannot_have_its_fence_closed_by_an_input(tmp_path: Path) -> None:
    """A backtick in an input would let it write the rest of the page."""
    target = tmp_path / "summary.md"

    write_summary(_inputs(files="```\n# pwned"), 0, path=str(target), version="0.1.0")
    rendered = target.read_text(encoding="utf-8")

    assert "```\n# pwned" not in rendered
    assert rendered.count("```") == 2


def test_the_summary_truncates_a_huge_input(tmp_path: Path) -> None:
    target = tmp_path / "summary.md"

    write_summary(_inputs(files="a" * 5000), 0, path=str(target), version="0.1.0")

    assert len(target.read_text(encoding="utf-8")) < 2000


def test_the_summary_carries_no_document_content(tmp_path: Path, workspace: Path) -> None:
    target = tmp_path / "summary.md"

    write_summary(_inputs(files="claims/clean.json"), 0, path=str(target), version="0.1.0")
    rendered = target.read_text(encoding="utf-8")

    assert "vegetation" not in rendered.lower()
    assert "Example Area" not in rendered


# --------------------------------------------------------------------------
# End to end through the CLI
# --------------------------------------------------------------------------


def _environ(workspace: Path, tmp_path: Path, **inputs: str) -> dict[str, str]:
    env = {
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(tmp_path / "github_output"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        "INPUT_FILES": "claims/clean.json",
        "INPUT_FAIL_ON": "error",
        "INPUT_ENABLE": "",
        "INPUT_DISABLE": "",
        "INPUT_SEVERITY": "",
        "INPUT_WORKING_DIRECTORY": ".",
    }
    env.update({f"INPUT_{key.upper().replace('-', '_')}": value for key, value in inputs.items()})
    return env


def _outputs(tmp_path: Path) -> dict[str, str]:
    text = (tmp_path / "github_output").read_text(encoding="utf-8")
    return dict(line.split("=", 1) for line in text.splitlines() if line)


def test_a_clean_document_exits_zero(workspace: Path, tmp_path: Path) -> None:
    code = main(_environ(workspace, tmp_path))

    assert code == 0
    assert _outputs(tmp_path) == {"exit-code": "0", "outcome": "passed"}


def test_a_failing_document_exits_one(workspace: Path, tmp_path: Path) -> None:
    code = main(_environ(workspace, tmp_path, files="claims/bad.json"))

    assert code == 1
    assert _outputs(tmp_path) == {"exit-code": "1", "outcome": "lint-failed"}


def test_a_missing_file_exits_two(workspace: Path, tmp_path: Path) -> None:
    code = main(_environ(workspace, tmp_path, files="claims/missing.json"))

    assert code == 2
    assert _outputs(tmp_path) == {"exit-code": "2", "outcome": "usage-error"}


def test_an_escaping_working_directory_exits_two(workspace: Path, tmp_path: Path) -> None:
    code = main(_environ(workspace, tmp_path, working_directory=".."))

    assert code == 2
    assert _outputs(tmp_path)["outcome"] == "usage-error"


def test_a_crashing_rule_exits_three(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("deliberate failure")

    monkeypatch.setattr("eo_claim_lint.cli.commands.lint_document", _boom)

    code = main(_environ(workspace, tmp_path))

    assert code == 3
    assert _outputs(tmp_path) == {"exit-code": "3", "outcome": "internal-error"}


def test_fail_on_warning_turns_a_warning_into_a_failure(workspace: Path, tmp_path: Path) -> None:
    (workspace / "claims" / "warn.json").write_text(
        WARNING_DOC.read_text(encoding="utf-8"), encoding="utf-8"
    )

    passed = main(_environ(workspace, tmp_path, files="claims/warn.json"))
    assert passed == 0

    (tmp_path / "github_output").unlink()
    failed = main(_environ(workspace, tmp_path, files="claims/warn.json", fail_on="warning"))

    assert failed == 1


def test_disabling_a_rule_changes_the_outcome(workspace: Path, tmp_path: Path) -> None:
    code = main(_environ(workspace, tmp_path, files="claims/bad.json", disable="EOC301"))

    assert code == 0


def test_a_severity_override_changes_the_outcome(workspace: Path, tmp_path: Path) -> None:
    code = main(_environ(workspace, tmp_path, files="claims/bad.json", severity="EOC301=warning"))

    assert code == 0


def test_an_unknown_rule_id_exits_two(workspace: Path, tmp_path: Path) -> None:
    code = main(_environ(workspace, tmp_path, files="claims/clean.json", disable="EOC997"))

    assert code == 2


def test_the_working_directory_is_restored(workspace: Path, tmp_path: Path) -> None:
    import os

    before = os.getcwd()

    main(_environ(workspace, tmp_path))

    assert os.getcwd() == before


def test_annotations_go_to_stdout(
    workspace: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(_environ(workspace, tmp_path, files="claims/bad.json"))

    assert capsys.readouterr().out.startswith("::error ")


def test_the_wrapper_writes_no_json_report(
    workspace: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The action reports through annotations, not through a parsed document."""
    main(_environ(workspace, tmp_path, files="claims/bad.json"))
    captured = capsys.readouterr().out

    with pytest.raises(json.JSONDecodeError):
        json.loads(captured)
