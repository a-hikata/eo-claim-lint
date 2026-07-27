"""Integration tests that run the CLI as a real process.

The in-process tests exercise the code; these check that the packaging works —
that the module is executable, that streams and exit statuses cross the process
boundary intact. ``python -m eo_claim_lint`` is used rather than the installed
console script, because the script's location depends on how the environment
was set up while the module path does not.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Final

FIXTURES: Final = Path(__file__).resolve().parent / "fixtures"
CLEAN: Final = FIXTURES / "lint_valid" / "observation-fully-qualified.json"
ERROR_DOC: Final = FIXTURES / "lint_invalid" / "interpretation-without-evidence.json"


def _run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "eo_claim_lint", *args],
        capture_output=True,
        text=True,
        input=stdin,
        check=False,
    )


def test_version() -> None:
    completed = _run("--version")

    assert completed.returncode == 0
    assert completed.stdout.startswith("eo-claim-lint ")


def test_no_arguments_prints_help_and_exits_two() -> None:
    completed = _run()

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "usage:" in completed.stderr


def test_check_a_clean_document() -> None:
    completed = _run("check", str(CLEAN))

    assert completed.returncode == 0
    assert "0 errors" in completed.stdout


def test_check_a_failing_document() -> None:
    completed = _run("check", str(ERROR_DOC))

    assert completed.returncode == 1
    assert "EOC301" in completed.stdout


def test_check_json_output_is_pure_json() -> None:
    completed = _run("check", "--format", "json", str(ERROR_DOC))

    payload = json.loads(completed.stdout)

    assert payload["valid"] is False
    assert completed.stderr == ""


def test_check_github_output() -> None:
    completed = _run("check", "--format", "github", str(ERROR_DOC))

    assert completed.stdout.startswith("::error ")


def test_check_reads_stdin() -> None:
    completed = _run("check", "-", stdin=ERROR_DOC.read_text(encoding="utf-8"))

    assert completed.returncode == 1
    assert "<stdin>" in completed.stdout


def test_missing_file_writes_to_stderr_only() -> None:
    completed = _run("check", "definitely-missing.json")

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "no such file" in completed.stderr


def test_rules() -> None:
    completed = _run("rules")

    assert completed.returncode == 0
    assert "EOC101" in completed.stdout


def test_schema_claim() -> None:
    completed = _run("schema", "claim")

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["$id"].endswith("claim-document-0.1.schema.json")


def test_init_stdout() -> None:
    completed = _run("init", "--stdout")

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["claim_id"] == "claim-001"


def test_the_generated_example_passes_its_own_check(tmp_path: Path) -> None:
    """End to end: what `init` writes is what `check` accepts."""
    example = tmp_path / "claim-document.json"
    example.write_text(_run("init", "--stdout").stdout, encoding="utf-8")

    completed = _run("check", str(example))

    assert completed.returncode == 0
