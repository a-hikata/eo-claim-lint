# eo-claim-lint

A linter for checking whether Earth observation claims distinguish measurements,
estimates, uncertainty, and supporting evidence.

## Project status

**Early development.**

- The API is **not yet stable**. Anything may change without notice while the
  version is `0.x`.
- **Implemented so far:** the claim document data model, the report data model,
  and the two JSON Schemas, with synthetic fixtures and contract tests.
- **Not implemented:** the linting rules, the CLI, and the GitHub Action. No
  rule exists yet, so nothing is currently checked.
- Not published to PyPI. Install from a source checkout (see below).

## Purpose

When a result derived from satellite or weather data is published to a general
audience, two very different things end up on the same page: what an instrument
actually recorded, and what a model concluded from it. Once they are rendered
with the same styling, a reader cannot tell them apart — and neither can a
reviewer, six months later, reading the artifact instead of the code.

`eo-claim-lint` checks the artifact.

- **Structural integrity of a claim document** — the declared layers exist, the
  manifest and the items agree, nothing is declared that is not there.
- **Measured observations are distinguishable from estimates** — an estimate
  carries the method and confidence that make it recognisable as an estimate,
  and a measured artifact does not quietly reference an estimated value.
- **Uncertainty and evidence are not missing** — an estimate that asserts a
  class or category has to say where its thresholds came from. If the
  provenance of a threshold cannot be disclosed, the class should not be
  asserted.

The tool works on structured data and the labels rendered from it. It reads
what a document claims about itself.

## Non-goals

`eo-claim-lint` does **not** do any of the following, and is not intended to
grow into them:

- satellite image processing
- scientific validation of numeric values (it never recomputes a number)
- legal evidence certification
- notarization
- agricultural risk prediction
- yield prediction
- general prose linting (use [Vale](https://vale.sh/) or
  [textlint](https://textlint.github.io/) for that)
- GIS processing
- an MCP server

Passing this linter means a document is internally consistent about what it
claims. **It does not mean the underlying data is correct, and it does not make
any statement legally valid.**

## The claim document

A **claim document** is one claim, expressed as a single JSON object, with
enough context to tell what kind of claim it is. It is the unit this linter
reads.

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

Notes on reading these values:

- **`synthetic` does not mean false.** Synthetic data is legitimate and useful;
  it means the values were not recorded by an instrument. The point of labelling
  it is that a reader should never have to guess.
- **`modeled` does not imply `synthetic`.** A model can be driven entirely by
  measured inputs. Origin and processing are orthogonal, which is exactly why
  they are separate fields.
- A measured, derived value (for example a spectral index computed from measured
  bands) is `data_origin: measured`, `data_processing: derived`.

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

Two JSON Schemas ([Draft 2020-12](https://json-schema.org/draft/2020-12/schema))
ship inside the package:

| Schema | `$id` |
|---|---|
| Claim document | `https://schemas.orbseekr.jp/eo-claim-lint/claim-document-0.1.schema.json` |
| Linter report | `https://schemas.orbseekr.jp/eo-claim-lint/lint-output-1.0.schema.json` |

**Those `$id` values are canonical identifiers, not download locations.** They
name the schemas so that two documents can agree on which version they mean.
Retrieval from those URLs is **not guaranteed**, and nothing in this package
ever fetches them. The schema files are bundled in the wheel and read through
`importlib.resources`, so **no network access is required at any point** and
neither schema contains an external `$ref`.

Load them from Python:

```python
from eo_claim_lint import load_claim_document_schema, load_lint_output_schema

schema = load_claim_document_schema()
```

Each call returns a fresh object, so a caller that modifies a schema before
handing it to a validator cannot affect the next caller.

## Report format

A report records what a run found. `valid` is **derived from the issues, never
supplied**: it is false when any issue has `error` severity, and warnings or
info alone leave a report valid. There is no way to express a report that
claims to be valid while carrying an error.

Rule identifiers match `^EOC[0-9]{3}$` and are grouped by concern: `EOC0xx`
document contract, `EOC1xx` observation and estimate separation, `EOC2xx` claim
safety, `EOC3xx` provenance and evidence, `EOC4xx` data origin and processing.
Identifiers are never reused, including after a rule is withdrawn.

`doc_url` is nullable and is currently always null: the rule documentation pages
do not exist yet, and a URL that resolves to nothing is worse than none.

## Installation

Not on PyPI yet. From a checkout:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows, activate with `.venv\Scripts\activate` instead.

The package has **no runtime dependencies**. `jsonschema` is a development
dependency only — it is used to test the bundled schemas, never to validate
anything at runtime.

## Current usage

There is no CLI and no linting functionality yet. What works today is building
and serialising documents, and reading the schemas:

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

Commands such as `eo-claim-lint check` are planned but **do not exist yet**.

## Test fixtures

Every fixture under `tests/fixtures/` is **entirely fictional** — invented place
names, synthetic coordinates, `urn:example:` URIs, and placeholder checksums
that digest nothing. A fixture declaring `"data_origin": "measured"` is a
synthetic example of a document that *claims* measured origin; it is not
measured data. See [`tests/fixtures/README.md`](tests/fixtures/README.md).

## Roadmap

In order:

1. ~~**Schema** — a JSON Schema for the claim document, and one for the
   linter's own output.~~ Done.
2. ~~**Models** — the result and issue types the rules produce.~~ Done.
3. **Rule engine** — the rules themselves, with stable rule IDs.
4. **CLI** — `check`, `rules`, `schema`, `init`, with documented exit codes.
5. **GitHub Action** — a composite action that needs no secrets.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Two rules matter more than the rest:
never add real-world locations or personal data to this repository, and every
new rule needs an ID, a test, and documentation.

## License

Apache License 2.0. See [LICENSE](LICENSE).
