# eo-claim-lint

A linter for checking whether Earth observation claims distinguish measurements,
estimates, uncertainty, and supporting evidence.

## Project status

**Early development.**

- The API is **not yet stable**. Anything may change without notice while the
  version is `0.x`.
- **No linting rules are implemented yet.** This release contains the package
  skeleton only: packaging, license, CI, and a typed-package marker.
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

## Data semantics

A claim document describes its data along **two independent axes**. A single
`real` / `mock` flag conflates them and is not used.

### `data_origin` — where the data came from

| Value | Meaning |
|---|---|
| `measured` | Recorded by an instrument or sensor. |
| `synthetic` | Generated, for example for a demo, a test fixture, or a placeholder. |
| `unknown` | Not established. |

### `data_processing` — how far it has been transformed

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

## Installation

Not on PyPI yet. From a checkout:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows, activate with `.venv\Scripts\activate` instead.

## Current usage

There is no CLI and no linting functionality yet. What works today is importing
the package and reading its version:

```python
import eo_claim_lint

print(eo_claim_lint.__version__)
```

Commands such as `eo-claim-lint check` are planned but **do not exist yet**.

## Roadmap

In order:

1. **Schema** — a JSON Schema for the claim document, and one for the linter's
   own output.
2. **Models** — the result and issue types the rules produce.
3. **Rule engine** — the rules themselves, with stable rule IDs.
4. **CLI** — `check`, `rules`, `schema`, `init`, with documented exit codes.
5. **GitHub Action** — a composite action that needs no secrets.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Two rules matter more than the rest:
never add real-world locations or personal data to this repository, and every
new rule needs an ID, a test, and documentation.

## License

Apache License 2.0. See [LICENSE](LICENSE).
