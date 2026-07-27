"""Wrapper that turns GitHub Action inputs into an ``eo-claim-lint check`` run.

This file is repository infrastructure, not library code. It lives outside
``src/`` on purpose: it only makes sense inside a GitHub runner, and shipping it
in the wheel would put a module in library users' import space that they can
never use.

It contains no linting logic. Its whole job is to read inputs, turn them into a
safe argument list, hand them to the CLI, and report what came back.

**Inputs arrive as environment variables, never as shell interpolation.** A
composite action that writes ``${{ inputs.files }}`` into a ``run:`` block hands
the caller a shell prompt; reading ``INPUT_FILES`` from the environment does
not. Nothing here builds a command string, and nothing is evaluated by a shell.
"""

from __future__ import annotations

import glob
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# The wrapper runs after `pip install`, so the package is importable.
from eo_claim_lint.cli import main as cli_main

__all__ = ["ActionInputError", "build_argv", "main", "outcome_for"]

#: CLI exit status to a name a human can read in the workflow log.
OUTCOMES: Final = {
    0: "passed",
    1: "lint-failed",
    2: "usage-error",
    3: "internal-error",
}

FAIL_ON_VALUES: Final = ("error", "warning", "info")

#: How much of an input is echoed into the step summary. Long enough to be
#: useful, short enough that a pathological input cannot flood the page.
SUMMARY_VALUE_LIMIT: Final = 500


class ActionInputError(Exception):
    """An input is missing, malformed, or points outside the workspace.

    Reported as CLI exit status 2, the same code the CLI uses for a bad
    invocation, because that is exactly what it is.
    """


@dataclass(frozen=True)
class Inputs:
    """The action's inputs, as read from the environment."""

    files: str
    fail_on: str
    enable: str
    disable: str
    severity: str
    working_directory: str

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> Inputs:
        env = os.environ if environ is None else environ
        return cls(
            files=env.get("INPUT_FILES", ""),
            fail_on=env.get("INPUT_FAIL_ON", "error").strip() or "error",
            enable=env.get("INPUT_ENABLE", ""),
            disable=env.get("INPUT_DISABLE", ""),
            severity=env.get("INPUT_SEVERITY", ""),
            working_directory=env.get("INPUT_WORKING_DIRECTORY", ".").strip() or ".",
        )


# --------------------------------------------------------------------------
# Parsing inputs
# --------------------------------------------------------------------------


def split_lines(raw: str) -> tuple[str, ...]:
    """Split a multi-line input into entries.

    Newlines are the only separator. Splitting on whitespace as well would make
    a path containing a space impossible to express, and a linter that cannot
    be pointed at ``my claims/a.json`` is a linter with a silent blind spot.
    """
    return tuple(line.strip() for line in raw.splitlines() if line.strip())


def _resolve_workspace(env: Mapping[str, str]) -> Path:
    """The checkout root. Everything the action touches must stay inside it."""
    workspace = env.get("GITHUB_WORKSPACE")
    return Path(workspace if workspace else os.getcwd()).resolve()


def _is_inside(candidate: Path, root: Path) -> bool:
    return candidate == root or root in candidate.parents


def resolve_working_directory(value: str, workspace: Path) -> Path:
    """Resolve the working directory, refusing anything outside the workspace.

    ``Path.resolve`` follows symlinks, so a link pointing out of the checkout is
    rejected by the same containment check as ``../..``. There is no legitimate
    reason for a workflow to lint files it did not check out, and every reason
    not to let an input decide which ones.
    """
    resolved = (
        (workspace / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    )

    if not _is_inside(resolved, workspace):
        raise ActionInputError(f"working-directory resolves outside the workspace: {value!r}")
    if not resolved.is_dir():
        raise ActionInputError(f"working-directory is not a directory: {value!r}")
    return resolved


def expand_files(patterns: Sequence[str], base: Path, workspace: Path) -> tuple[str, ...]:
    """Expand each pattern against ``base``, returning workspace-relative paths.

    Patterns are matched against ``base`` (the ``working-directory`` input) but
    the paths that come back are relative to ``workspace``. When the two are the
    same — the default — the result is identical either way.

    Globbing happens here rather than in the shell, so that a pattern is never
    re-evaluated as a command. Expansion is not recursive: the CLI has no
    recursive mode, and an action that quietly checked more than the CLI would
    make the two disagree about what "checked" means.
    """
    if not patterns:
        raise ActionInputError("files: at least one path or glob is required")

    matched: list[str] = []
    seen: set[str] = set()

    for pattern in patterns:
        hits = sorted(glob.glob(pattern, root_dir=base, recursive=False))
        real_hits = [name for name in hits if (base / name).is_file()]
        if not real_hits:
            raise ActionInputError(f"files: no file matched {pattern!r}")

        for name in real_hits:
            resolved = (base / name).resolve()
            if not _is_inside(resolved, workspace):
                raise ActionInputError(f"files: {name!r} resolves outside the workspace")

            # Paths are returned relative to the **workspace**, not to
            # `working-directory`. GitHub resolves the `file=` property of an
            # annotation against the workspace root, so a path relative to
            # anywhere else silently attaches the annotation to nothing.
            # Patterns are still matched against `working-directory` — that is
            # what the input means — but what leaves this function is anchored
            # where GitHub will read it.
            relative = resolved.relative_to(workspace).as_posix()
            if relative in seen:
                continue
            seen.add(relative)
            # A leading dash would be read as an option however the argument
            # list is built. `./` is the portable way to say "this is a path".
            matched.append(f"./{relative}" if relative.startswith("-") else relative)

    return tuple(matched)


def _validate_fail_on(value: str) -> str:
    if value not in FAIL_ON_VALUES:
        allowed = ", ".join(FAIL_ON_VALUES)
        raise ActionInputError(f"fail-on: {value!r} is not one of {allowed}")
    return value


def build_argv(inputs: Inputs, *, base: Path, workspace: Path) -> list[str]:
    """Build the CLI argument list.

    Everything the caller supplied ends up as a separate element of a list. No
    string is ever concatenated into a command, and ``--`` separates the options
    from the paths so that a file called ``-x`` cannot be read as a flag.
    """
    argv: list[str] = [
        "check",
        "--format",
        "github",
        "--fail-on",
        _validate_fail_on(inputs.fail_on),
    ]

    for rule_id in split_lines(inputs.enable):
        argv += ["--enable", rule_id]
    for rule_id in split_lines(inputs.disable):
        argv += ["--disable", rule_id]
    for override in split_lines(inputs.severity):
        argv += ["--severity", override]

    argv.append("--")
    argv.extend(expand_files(split_lines(inputs.files), base, workspace))
    return argv


def outcome_for(code: int) -> str:
    """Name the exit status. Anything unexpected is treated as our failure."""
    return OUTCOMES.get(code, "internal-error")


# --------------------------------------------------------------------------
# Reporting back to GitHub
# --------------------------------------------------------------------------


def _sanitise(value: str) -> str:
    """Make an input safe to place inside a fenced block in the step summary.

    Backticks are removed so the fence cannot be closed early, control
    characters are dropped, and the result is truncated. The step summary is
    Markdown that GitHub renders; an input that can close its own container can
    write the rest of the page.
    """
    cleaned = "".join(
        character
        for character in value.replace("`", "")
        if character == "\n" or character.isprintable()
    )
    if len(cleaned) > SUMMARY_VALUE_LIMIT:
        cleaned = f"{cleaned[:SUMMARY_VALUE_LIMIT]}…"
    return cleaned.strip() or "(none)"


def write_outputs(code: int, *, path: str | None) -> None:
    """Write the action's outputs to the file GitHub gave us."""
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"exit-code={code}\n")
        handle.write(f"outcome={outcome_for(code)}\n")


def write_summary(inputs: Inputs, code: int, *, path: str | None, version: str) -> None:
    """Append a short summary. Never the documents, never the findings in full.

    The annotations are the report; this is a header so that a reader scanning
    a workflow run knows what was checked and how it was configured.
    """
    if not path:
        return

    lines = [
        "## eo-claim-lint",
        "",
        f"- version: `{version}`",
        f"- outcome: **{outcome_for(code)}** (exit code {code})",
        f"- fail-on: `{_sanitise(inputs.fail_on)}`",
        "",
        "<details><summary>Configuration</summary>",
        "",
        "```",
        f"files:\n{_sanitise(inputs.files)}",
        f"enable: {_sanitise(inputs.enable)}",
        f"disable: {_sanitise(inputs.disable)}",
        f"severity: {_sanitise(inputs.severity)}",
        f"working-directory: {_sanitise(inputs.working_directory)}",
        "```",
        "",
        "</details>",
        "",
    ]
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main(environ: Mapping[str, str] | None = None) -> int:
    """Run the check and return the CLI's exit status, unchanged."""
    from eo_claim_lint import __version__

    env = os.environ if environ is None else environ
    inputs = Inputs.from_environ(env)
    workspace = _resolve_workspace(env)

    try:
        base = resolve_working_directory(inputs.working_directory, workspace)
        argv = build_argv(inputs, base=base, workspace=workspace)
    except ActionInputError as exc:
        sys.stderr.write(f"error: {exc}\n")
        code = 2
        write_outputs(code, path=env.get("GITHUB_OUTPUT"))
        write_summary(inputs, code, path=env.get("GITHUB_STEP_SUMMARY"), version=__version__)
        return code

    # The linter runs from the workspace root, because `expand_files` hands it
    # workspace-relative paths. `working-directory` decides which files are
    # selected, not which directory the reported paths are anchored to.
    previous = os.getcwd()
    try:
        os.chdir(workspace)
        code = cli_main(argv)
    finally:
        os.chdir(previous)

    write_outputs(code, path=env.get("GITHUB_OUTPUT"))
    write_summary(inputs, code, path=env.get("GITHUB_STEP_SUMMARY"), version=__version__)
    return code


if __name__ == "__main__":
    sys.exit(main())
