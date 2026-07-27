# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While the version is `0.x`, the public API may change in any minor release.

## [Unreleased]

**Not released.** These changes exist in the repository only.

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

### Notes

- No CLI or GitHub Action is implemented yet. Linting is a Python API.
- Reading configuration from a file is not implemented; `RuleConfig` is
  constructed in Python.
- `EOC301` is the only rule that defaults to error severity.
- A rule that raises produces `RuleExecutionError` rather than an issue, so a
  defect in this package is never reported as a finding about a document.
- `jsonschema` is a development dependency only; the package still has no
  runtime dependencies.
- One constraint is enforced by the data model rather than by the schema:
  `lower <= upper` on an interval compares two sibling values, which JSON
  Schema Draft 2020-12 cannot express.

## [0.1.0] - 2026-07-27

**Not released.** This version exists in the repository only; it has not been
published to any package index.

### Added

- Initial project structure: `src/` layout, PEP 621 packaging, Apache-2.0
  license, typed-package marker.
- Continuous integration for Python 3.11, 3.12, and 3.13.
- Documentation of the `data_origin` / `data_processing` axes that replace a
  single `real` / `mock` flag.

### Notes

- No linting rules, CLI, or schema are implemented in this version.
