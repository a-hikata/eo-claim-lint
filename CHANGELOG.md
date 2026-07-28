# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While the version is `0.x`, the public API may change in any minor release.

## [Unreleased]

Nothing yet.

## [0.1.1] - 2026-07-28

A documentation and maintenance patch. **Nothing a user can observe changes.**
The rules, their default severities, the exit codes, the JSON output, and the
Action's inputs and outputs are exactly what `0.1.0` published. A workflow
pinned to `@v0` gets the same findings from the same documents.

### Changed

- Updated the pinned `actions/setup-python` inside the Action to v7.0.0, and
  the pinned `actions/checkout` used by this repository's own workflows to
  v7.0.1. Both target Node.js 24, which removes the Node.js 20 deprecation
  warning that every run of the Action produced. Both are still pinned to a
  commit, and the self-test on GitHub-hosted runners reports the same findings
  as before with that warning gone.

### Fixed

- The README's "Purpose and non-goals" section credited the linter with three
  checks it does not perform: that declared layers exist, that a manifest
  agrees with its items, and that an asserted class discloses where its
  thresholds came from. No rule has ever implemented any of them. The section
  now describes the ten rules that do exist, and says what is not read.
- The package docstring said the command-line interface and the GitHub Action
  did not exist. Both shipped in `0.1.0`.

### Documentation

- Stated where the fail threshold comes from: the `--fail-on` option when it is
  given, and `error` when it is not, on the command line and in the Action
  alike. No file is consulted anywhere in `0.1.x`, and the "No configuration
  file" limitation now says so explicitly.
- Stated that a finding names a file rather than a line, and that the position
  inside the document is the JSON Pointer that opens the message.
- Pinned `actions/checkout` to a commit in the Quick start and in
  `examples/github-action.yml`, so the examples follow the pinning this project
  applies to itself.
- Noted that `init` writes its example without printing anything.

### Notes

- Tests now hold the documentation to the rule registry: every rule named in a
  document exists, every rule that exists appears in the README table with its
  real default severity, and the withdrawn capabilities cannot return unnoticed.
- The `0.1.x` threshold resolution — the option, then the built-in default,
  with nothing in between — is fixed by test on both surfaces. Adding a
  configuration file later has to change a test rather than change behaviour
  quietly.

## [0.1.0] - 2026-07-27

First release. Rule ids are stable from this release onward and are never
reused, including after a rule is withdrawn.

### Added

- Added initial claim document data model.
- Added claim document JSON Schema.
- Added lint output data model and JSON Schema.
- Added synthetic schema fixtures.
- Added packaged schema loading helpers.
- Added deterministic lint rule engine.
- Added initial EO claim rules (`EOC101`–`EOC103`, `EOC201`–`EOC203`, `EOC301`,
  `EOC302`, `EOC401`, `EOC402`).
- Added rule registry and rule configuration.
- Added synthetic lint-valid and lint-invalid fixtures.
- Added lint engine contract tests.
- Added CLI with `check`, `rules`, `schema`, and `init` commands.
- Added text, JSON, and GitHub annotation output.
- Added exit code handling for lint failures, input errors, and internal errors.
- Added stdin and multiple-file support.
- Added packaged CLI output JSON Schema (`cli-output-0.1`) and a loader for it.
- Added CLI integration tests that run the module as a process.
- Added a composite GitHub Action.
- Added Action inputs for files, fail threshold, rule selection, and severity
  overrides.
- Added Action outputs for the linter's exit code and a named outcome.
- Added a self-test workflow that exercises the local Action.
- Added Action metadata contract tests and wrapper unit tests.
- Added least-privilege workflow examples.
- Added the project skeleton: `src/` layout, PEP 621 packaging, Apache-2.0
  license, typed-package marker, and continuous integration for Python 3.11,
  3.12, and 3.13.

### Fixed

- Action annotations now name paths relative to the workspace root rather than
  to `working-directory`. GitHub resolves an annotation's `file=` against the
  workspace, so a non-default `working-directory` previously attached findings
  to a path that did not exist. Output with the default `working-directory` is
  unchanged.

### Notes

- The Action requires `contents: read` and no secrets.
- The Action's file patterns are newline-separated and do not recurse, and
  every path is required to resolve inside the workspace.
- Reading configuration from a file is not implemented; rules are selected with
  `--enable`, `--disable`, and `--severity`, or with `RuleConfig` in Python.
- `check` does not validate against the JSON Schema at runtime, because that
  would require a schema library and the package has no runtime dependencies.
  The data model performs the equivalent structural checks.
- Exit code `3` is reserved for a failure inside the linter, so that a defect
  here is never reported as a finding about a document.
- `EOC301` is the only rule that defaults to error severity.
- A rule that raises produces `RuleExecutionError` rather than an issue, so a
  defect in this package is never reported as a finding about a document.
- `jsonschema` is a development dependency only; the package still has no
  runtime dependencies.
- One constraint is enforced by the data model rather than by the schema:
  `lower <= upper` on an interval compares two sibling values, which JSON
  Schema Draft 2020-12 cannot express.
