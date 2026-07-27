# eo-claim-lint

[![CI](https://github.com/a-hikata/eo-claim-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/a-hikata/eo-claim-lint/actions/workflows/ci.yml)
[![Action self-test](https://github.com/a-hikata/eo-claim-lint/actions/workflows/action-test.yml/badge.svg)](https://github.com/a-hikata/eo-claim-lint/actions/workflows/action-test.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

**Check that a published Earth observation claim keeps measurements, estimates,
uncertainty, and evidence distinguishable — before anyone reads it.**

A number derived from satellite data reaches a page as either something an
instrument recorded or something a model concluded. Rendered the same way, a
reader cannot tell which. Neither can a reviewer, six months later, reading the
artifact instead of the code. This linter reads the artifact.

---

## Quick start

Add one step to a workflow. Nothing else is required.

```yaml
name: Claim documents

on: pull_request

permissions:
  contents: read # nothing else is needed

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: a-hikata/eo-claim-lint@v0
        with:
          files: claims/*.json
```

A finding appears as an annotation on the offending file in the pull request:

```
::error file=claims/harvest-index.json,title=EOC301::$.evidence: This claim references no evidence. Add at least one reference so that a reader can trace where the value came from.
```

The step fails, so the check goes red and the pull request cannot be merged
until it is fixed or the rule is deliberately switched off.

**No secrets. No write permissions. No network access beyond `pip` and
`setup-python`.**

### Try it locally first

```bash
python -m pip install "git+https://github.com/a-hikata/eo-claim-lint@v0"

eo-claim-lint init                          # writes a working example
eo-claim-lint check claim-document.json     # passes
eo-claim-lint rules                         # what gets checked
```

Then delete the `evidence` array from the example and run `check` again to see
what a finding looks like. The Action runs exactly this code.

---

## Inputs

| Input | Required | Default | Meaning |
|---|:-:|---|---|
| `files` | **Yes** | — | Documents to check. **One path or glob per line.** Not recursive. |
| `fail-on` | No | `error` | Lowest severity that fails the step: `error`, `warning`, or `info`. |
| `enable` | No | — | Run only these rules. One id per line. |
| `disable` | No | — | Skip these rules. One id per line. |
| `severity` | No | — | Overrides, one `RULE_ID=SEVERITY` per line. |
| `python-version` | No | `3.11` | Python used to run the linter. |
| `working-directory` | No | `.` | Directory the patterns are resolved against. Must stay inside the workspace. |

**Newlines are the only separator.** Splitting on spaces as well would make a
path containing a space impossible to express, so `my claims/a.json` on its own
line is one path, not two.

```yaml
- uses: a-hikata/eo-claim-lint@v0
  with:
    files: |
      claims/*.json
      archive/2026/*.json
    fail-on: warning
    disable: EOC202
    severity: |
      EOC101=error
      EOC401=info
```

## Outputs

| Output | Meaning | Values |
|---|---|---|
| `exit-code` | The linter's own exit status. | `0` `1` `2` `3` |
| `outcome` | The same, named. | `passed` `lint-failed` `usage-error` `internal-error` |

```yaml
- id: lint
  uses: a-hikata/eo-claim-lint@v0
  with:
    files: claims/*.json
- run: echo "${{ steps.lint.outputs.outcome }}"
```

There is deliberately no `valid` output. Producing one would mean running the
linter a second time in JSON format, and a report that can disagree with the
annotations beside it is worse than no report.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Nothing at or above the `--fail-on` threshold. |
| `1` | The threshold was reached. |
| `2` | The invocation or the input was wrong: missing file, malformed JSON, unknown rule. |
| `3` | **The linter itself failed.** Not a statement about your document. |

Code `3` exists so that a bug here cannot masquerade as a finding about your
data. The Action passes the code through unchanged rather than collapsing
everything into "failed", so `outputs.exit-code` still distinguishes *your*
mistake from *ours*.

## Permissions and secrets

`contents: read`, and nothing else. Annotations travel as workflow commands
printed to stdout, so no write permission is involved. The Action needs **no
secrets**, no `GITHUB_TOKEN`, and contacts no schema URL or Earth observation
service.

`actions/setup-python` is pinned to a commit inside the Action, and this package
is installed from the Action's own checkout rather than from a package index —
the code that runs is the code at the ref you referenced.

> **One dependency does come from PyPI at run time.** `pip` builds this package
> in an isolated environment, which downloads the build backend (`hatchling`)
> and its dependencies. Those are resolved by version range, not pinned. If your
> threat model requires a fully pinned install, vendor the wheel and install it
> yourself instead of using this Action.

## Versioning

| Reference | Behaviour | Use when |
|---|---|---|
| `@v0` | **Moves.** Always the newest `v0.x.y`. | You want fixes automatically. Recommended. |
| `@v0.1.0` | **Fixed forever.** | You need a reproducible build. |
| `@<commit sha>` | Fixed, and immune to a tag being re-pointed. | Your policy requires SHA pinning. |

While the version is `0.x` the Python API may change in any minor release.
**Rule ids are stable from the first release and are never reused**, including
after a rule is withdrawn — a workflow that disables `EOC202` keeps working.

## What gets checked

| ID | Default | What it looks for |
|---|---|---|
| `EOC101` | warning | An estimate that declares no uncertainty. |
| `EOC102` | warning | An observation whose data is marked as `modeled`. |
| `EOC103` | warning | An interpretation with neither uncertainty nor disclaimer. |
| `EOC201` | warning | A display label that contradicts the claim type. |
| `EOC202` | warning | A displayed unit that differs from the recorded unit. |
| `EOC203` | warning | Definitive wording while the uncertainty is `unknown`. |
| `EOC301` | **error** | A claim that references no evidence at all. |
| `EOC302` | warning | Modeled data that names no software or version. |
| `EOC401` | warning | Synthetic origin the display does not disclose. |
| `EOC402` | warning | Unknown origin the display does not disclose. |

`EOC301` is the only error by default. A claim published with nothing behind it
cannot be checked by anyone, which is the failure this tool exists to prevent.
Everything else asks for a second look rather than asserting a defect.

Two false-positive conditions are worth knowing before you start:

- **`EOC202` compares units as plain strings.** A dimensionless value recorded
  as `"1"` and displayed as `"index"` is correct in both places and will still
  be reported. Add `disable: EOC202` if you render units for humans.
- **`EOC201` recognises a handful of English words only.** A label that
  overstates without using one of them is not caught, and a label in another
  language is not examined at all.

`eo-claim-lint rules --rule EOC301` prints the details of any one rule.

## Limitations

- **`files` does not recurse**, and a pattern matching nothing is an error
  rather than an empty pass. Reporting success for a repository nobody looked
  at is the failure this tool exists to prevent.
- **Everything must stay inside the workspace.** `working-directory` and every
  matched file are resolved and checked for containment, so `../..` and a
  symlink leading out of the checkout are both refused. Symlinks *within* the
  workspace are followed normally.
- **No file size limit.** Documents are read whole.
- **No configuration file.** Rules are selected through the `enable`,
  `disable`, and `severity` inputs.
- **It never checks a number.** A value of `0.42` that should have been `4.2`
  passes every rule.
- **It establishes nothing legally.** Passing this linter is not evidence of
  anything.

---

# Beyond the Action

Everything below documents the command line, the Python API, and the document
format. **If you only want the pull-request check, you are already done.**

## Project status

**Early development.**

- The API is **not yet stable**. Anything may change without notice while the
  version is `0.x`.
- **Implemented:** the claim document data model, the report data model, three
  JSON Schemas, a deterministic rule engine with ten rules, a command-line
  interface, and a composite GitHub Action.
- **Not implemented:** reading configuration from a file.
- Not published to PyPI. Install from the repository, as shown above.

## Command line

The Action is a thin wrapper around this. Same rules, same findings.

| Command | What it does |
|---|---|
| `check [FILE...]` | Check documents. `-` reads one from stdin. |
| `rules [--rule ID]` | List the rules, or describe one. |
| `schema NAME` | Print a bundled schema: `claim`, `lint-output`, `cli-output`. |
| `init [PATH]` | Write a synthetic example document. |

### `check` options

| Option | Default | Meaning |
|---|---|---|
| `--format {text,json,github}` | `text` | Output format. |
| `--output PATH` | stdout | Write the report to a file. |
| `--force` | off | Allow `--output` to overwrite. |
| `--quiet` | off | Drop the summary line; print nothing when clean. |
| `--fail-on {error,warning,info}` | `error` | Lowest severity that exits 1. |
| `--enable RULE_ID` | — | Run only these rules. Repeatable. |
| `--disable RULE_ID` | — | Skip these rules. Repeatable. |
| `--severity RULE_ID=SEVERITY` | — | Report a rule at another severity. Repeatable. |
| `--stdin-name NAME` | `<stdin>` | Label to report stdin under. |
| `--no-color` | off | Accepted for compatibility; output is never coloured. |

### Output examples

**text** — one line per finding, then a summary:

```console
$ eo-claim-lint check bad.json
bad.json: EOC301 error $.evidence This claim references no evidence. Add at least one reference so that a reader can trace where the value came from.
1 file checked: 1 error, 0 warnings, 0 info
```

**json** — nothing but JSON on stdout, matching `cli-output-0.1`:

```json
{
  "schema_version": "0.1",
  "tool": { "name": "eo-claim-lint", "version": "0.1.0" },
  "valid": false,
  "files": [
    {
      "source": "bad.json",
      "valid": false,
      "issues": [
        {
          "rule_id": "EOC301",
          "severity": "error",
          "message": "This claim references no evidence. …",
          "path": "$",
          "field": "evidence",
          "doc_url": null,
          "context": { "claim_type": "interpretation" }
        }
      ]
    }
  ],
  "summary": { "files": 1, "errors": 1, "warnings": 0, "info": 0 }
}
```

**github** — workflow commands that GitHub turns into annotations. Severities
map to `error`, `warning`, and `notice`, because GitHub has no "info"
annotation. Messages and property values are escaped, so a finding can never
inject a workflow command of its own.

### `--fail-on` is not the same as `valid`

`valid` in the JSON report answers *does this document carry an error?* The
exit code answers *should this build stop?* They can disagree, and both answers
are correct:

```console
$ eo-claim-lint check --format json --fail-on warning estimate.json
{ ... "valid": true, "summary": {"errors": 0, "warnings": 1, "info": 0} }
$ echo $?
1
```

The document carries no error, so the report is valid. You asked to stop on
warnings, so the process failed.

### Multiple files, and stdin

`check` accepts several paths and reports them in the order given. `-` reads a
single document from stdin and cannot be combined with file arguments.

**If any input cannot be read, the whole run fails with code 2 and prints no
report.** A partial report would look exactly like a complete one to whatever
consumes it, and an unchecked file would quietly pass as checked.

### Schema validation at run time

`check` does not validate against the JSON Schema. Validation needs a schema
library, and this package has no runtime dependencies. What it does instead is
build a `ClaimDocument`, which rejects missing required fields, unknown
enumerated values, wrong types, and self-inconsistent values such as an
interval whose lower bound exceeds its upper bound.

The schemas are still shipped, and `eo-claim-lint schema` prints them, so you
can validate in your own pipeline with the tool of your choice.

## The claim document

A **claim document** is one claim, expressed as a single JSON object, with
enough context to tell what kind of claim it is.

```json
{
  "schema_version": "0.1",
  "claim_id": "claim-001",
  "claim": {
    "type": "observation",
    "statement": "A vegetation index was computed for the specified area.",
    "value": 0.42,
    "unit": "1"
  },
  "data_origin": "measured",
  "data_processing": "derived",
  "spatial_scope": { "type": "named_area", "name": "Example Area" },
  "temporal_scope": { "observed_at": "2026-01-15T01:30:00Z" },
  "evidence": [
    {
      "id": "evidence-001",
      "type": "dataset",
      "title": "Example synthetic source record",
      "uri": "urn:example:evidence:001"
    }
  ],
  "display": { "label": "Measured vegetation index" },
  "processing": { "method": "Example index calculation" }
}
```

All ten top-level fields are required. `evidence` may be an empty array:
whether a particular kind of claim needs evidence is a policy question, and
policy belongs in a configurable rule rather than in the definition of what a
document *is*.

### Claim types

| Value | Meaning |
|---|---|
| `observation` | Recorded by an instrument or supplied by a data source. |
| `estimate` | Produced by a model, an interpolation, or a statistical procedure. |
| `interpretation` | A meaning assigned to an observation or an estimate. |

`prediction` is deliberately absent. A statement about the future raises
questions this version does not attempt to answer — how the forecast horizon is
declared, and how a claim is reconciled against what later happened.

### Data semantics

A claim document describes its data along **two independent axes**. A single
`real` / `mock` flag conflates them and is not used.

#### `data_origin` — where the data came from

| Value | Meaning |
|---|---|
| `measured` | Recorded by an instrument or sensor. |
| `synthetic` | Generated, for example for a demo, a test fixture, or a placeholder. |
| `unknown` | Not established. |

#### `data_processing` — how far it has been transformed

| Value | Meaning |
|---|---|
| `raw` | As delivered by the source, without derivation. |
| `derived` | Computed from measurements by a defined, deterministic procedure. |
| `modeled` | Produced by a model that adds assumptions beyond the input data. |
| `unknown` | Not established. |

- **`synthetic` does not mean false.** Synthetic data is legitimate and useful;
  it means the values were not recorded by an instrument. The point of labelling
  it is that a reader should never have to guess.
- **`modeled` does not imply `synthetic`.** A model can be driven entirely by
  measured inputs. Origin and processing are orthogonal, which is exactly why
  they are separate fields.
- A measured, derived value — a spectral index computed from measured bands —
  is `data_origin: measured`, `data_processing: derived`.

### Uncertainty

Uncertainty is optional and attaches to the claim. Four kinds are recognised:

| `kind` | Requires | Optional |
|---|---|---|
| `interval` | `lower`, `upper` | `unit`, `confidence`, `description` |
| `standard_deviation` | `value` (non-negative) | `unit`, `confidence`, `description` |
| `qualitative` | `description` | `confidence` |
| `unknown` | — | `description` |

`confidence` is a fraction between 0 and 1, not a percentage.

An estimate that declares no uncertainty is still a **valid document**. Whether
it should be allowed is a rule, and rules are configurable; the schema stays out
of that argument.

### Scope

`spatial_scope` is either a `named_area` or a `bbox`; nothing more expressive is
supported, and no GIS or coordinate transformation is performed.
`temporal_scope` is either a single `observed_at` instant or a `start`/`end`
period — never both. All timestamps are RFC 3339 and must carry a timezone
offset.

## Schemas

Three JSON Schemas ([Draft 2020-12](https://json-schema.org/draft/2020-12/schema))
ship inside the package:

| Schema | `$id` |
|---|---|
| Claim document | `https://schemas.orbseekr.jp/eo-claim-lint/claim-document-0.1.schema.json` |
| Linter report (one document) | `https://schemas.orbseekr.jp/eo-claim-lint/lint-output-1.0.schema.json` |
| Command-line report (one run) | `https://schemas.orbseekr.jp/eo-claim-lint/cli-output-0.1.schema.json` |

**Those `$id` values are canonical identifiers, not download locations.** They
name the schemas so that two documents can agree on which version they mean.
Retrieval from those URLs is **not guaranteed**, and nothing in this package
ever fetches them. The schema files are bundled in the wheel and read through
`importlib.resources`, so **no network access is required at any point** and
neither schema contains an external `$ref`.

```python
from eo_claim_lint import load_claim_document_schema

schema = load_claim_document_schema()
```

Each call returns a fresh object, so a caller that modifies a schema before
handing it to a validator cannot affect the next caller.

## Report format

`valid` is **derived from the issues, never supplied**: it is false when any
issue has `error` severity, and warnings or info alone leave a report valid.
There is no way to express a report that claims to be valid while carrying an
error.

Rule identifiers match `^EOC[0-9]{3}$` and are grouped by concern: `EOC0xx`
document contract, `EOC1xx` observation and estimate separation, `EOC2xx` claim
safety, `EOC3xx` provenance and evidence, `EOC4xx` data origin and processing.

`doc_url` is nullable and is currently always null: the rule documentation pages
do not exist yet, and a URL that resolves to nothing is worse than none.

## Python API

### What the rules add that the schema does not

The schema answers *is this a document?* — required fields, types, enumerated
values, basic formats. It is a structural question with a structural answer.

The rules answer *does this document contradict itself?* That question is not
structural, and it has no single right answer: whether an estimate must declare
uncertainty depends on the project. So the schema stays permissive and the
rules carry the judgement, which is why they can be switched off individually
while the schema cannot.

### Running the rules

```python
from eo_claim_lint import ClaimDocument, lint_document

document = ClaimDocument.from_dict(payload)
result = lint_document(document)

print(result.valid)
for issue in result.issues:
    print(issue.rule_id, issue.severity, issue.path, issue.message)
```

Issues come back sorted by rule id, then path, then field, then message, so two
runs over the same document produce identical output.

### Selecting and adjusting rules

```python
from eo_claim_lint import RuleConfig, Severity, lint_document

config = RuleConfig(
    disabled=frozenset({"EOC202"}),
    severity_overrides={"EOC301": Severity.WARNING},
)
result = lint_document(document, config=config)
```

Configuration selects rules and adjusts severities. It never changes *what* a
rule considers wrong — a rule whose meaning varies with configuration produces
findings that cannot be compared between projects. Naming a rule that does not
exist is an error rather than a silent no-op.

### When a rule itself fails

A rule that raises produces a `RuleExecutionError`, not an issue. A broken rule
is a defect in this package, not a finding about your document, and reporting
one as the other would hide the difference. The CLI maps it to exit code 3.

### Building documents

```python
from datetime import UTC, datetime

from eo_claim_lint import (
    ClaimDocument,
    ClaimType,
    ClaimValue,
    DataOrigin,
    DataProcessing,
    DisplayInfo,
    NamedAreaScope,
    ProcessingInfo,
    TemporalScope,
)

document = ClaimDocument(
    claim_id="claim-001",
    claim=ClaimValue(
        type=ClaimType.OBSERVATION,
        statement="A vegetation index was computed for the specified area.",
        value=0.42,
        unit="1",
    ),
    data_origin=DataOrigin.MEASURED,
    data_processing=DataProcessing.DERIVED,
    spatial_scope=NamedAreaScope(name="Example Area"),
    temporal_scope=TemporalScope(observed_at=datetime(2026, 1, 15, 1, 30, tzinfo=UTC)),
    display=DisplayInfo(label="Measured vegetation index"),
    processing=ProcessingInfo(method="Example index calculation"),
)

print(document.to_dict())
```

### Public API

Everything below is importable from `eo_claim_lint` directly:

- **Linting** — `lint_document`, `RuleConfig`, `Rule`, `RuleExecutionError`,
  `get_default_rules`, `get_rule`
- **Document model** — `ClaimDocument`, `ClaimValue`, `Uncertainty`,
  `NamedAreaScope`, `BoundingBoxScope`, `SpatialScope`, `TemporalScope`,
  `EvidenceReference`, `Checksum`, `DisplayInfo`, `ProcessingInfo`
- **Report model** — `LintResult`, `LintIssue`, `Severity`
- **Enumerations** — `ClaimType`, `DataOrigin`, `DataProcessing`,
  `EvidenceType`, `UncertaintyKind`
- **Schemas** — `load_claim_document_schema`, `load_lint_output_schema`,
  `load_cli_output_schema`, `CLAIM_DOCUMENT_SCHEMA_ID`, `LINT_OUTPUT_SCHEMA_ID`,
  `CLI_OUTPUT_SCHEMA_ID`
- **Errors** — `EoClaimLintError`

Concrete rule classes live in `eo_claim_lint.rules.*` and are reached through
`get_rule`; they are not exported at the top level.

## Purpose and non-goals

`eo-claim-lint` checks three things about a published artifact:

- **Structural integrity of a claim document** — the declared layers exist, the
  manifest and the items agree, nothing is declared that is not there.
- **Measured observations are distinguishable from estimates** — an estimate
  carries the method and confidence that make it recognisable as an estimate.
- **Uncertainty and evidence are not missing** — an estimate that asserts a
  class has to say where its thresholds came from. If the provenance of a
  threshold cannot be disclosed, the class should not be asserted.

It does **not** do any of the following, and is not intended to grow into them:

- satellite image processing
- scientific validation of numeric values (it never recomputes a number)
- legal evidence certification
- notarization
- agricultural risk prediction
- yield prediction
- general prose linting (use [Vale](https://vale.sh/) or
  [textlint](https://textlint.github.io/) for that)
- GIS processing
- automatic fixing of anything it reports
- an MCP server

Passing this linter means a document is internally consistent about what it
claims. **It does not mean the underlying data is correct, and it does not make
any statement legally valid.**

## Development

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"

ruff check . && ruff format --check . && mypy && pytest
```

The package has **no runtime dependencies**. `jsonschema` and `PyYAML` are
development dependencies only — used to test the bundled schemas and the action
metadata, never to validate anything at run time.

### Test fixtures

Every fixture under `tests/fixtures/` is **entirely fictional** — invented place
names, synthetic coordinates, `urn:example:` URIs, and placeholder checksums
that digest nothing. A fixture declaring `"data_origin": "measured"` is a
synthetic example of a document that *claims* measured origin; it is not
measured data. See [`tests/fixtures/README.md`](tests/fixtures/README.md).

## Roadmap

1. ~~Schema, models, rule engine, CLI, GitHub Action.~~ Done.
2. **Configuration files** — reading `RuleConfig` from TOML.
3. **Rule documentation pages** — so that `doc_url` stops being null.
4. **More rules**, added as `experimental` first.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Two rules matter more than the rest:
never add real-world locations or personal data to this repository, and every
new rule needs an ID, a test, and documentation.

Security reports: see [SECURITY.md](SECURITY.md). Please do not open a public
issue for a vulnerability.

## License

Apache License 2.0. See [LICENSE](LICENSE).
