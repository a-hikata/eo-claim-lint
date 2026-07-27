# Test fixtures

**Every file in this directory is entirely fictional.**

No fixture contains a real place, a real coordinate, a real parcel or field
identifier, a real organisation, a real person, a real observation, or a value
taken from any production system. Place names are invented (`Example Area`,
`Example Region`), identifiers are sequential (`claim-001`, `evidence-001`),
URIs use the reserved `urn:example:` namespace, bounding boxes use the obvious
sample range `[10.0, 10.0, 11.0, 11.0]`, and dates are chosen for legibility.

## `data_origin: "measured"` does not mean real data

A fixture that declares `"data_origin": "measured"` is **a synthetic example of
a document that claims measured origin**. It is not measured data. The field
records what a document asserts about itself, which is exactly what this linter
inspects — so the fixtures must be able to assert every value the field allows,
including `measured`.

The same applies to `data_processing`, checksums, and evidence references. A
checksum in a fixture is a placeholder string; it digests nothing.

## Directories

### `schema_valid/`

Documents that are structurally correct. Every one must validate against the
claim document schema **and** load through `ClaimDocument.from_dict()`.

### `schema_invalid/`

Documents that must be rejected.

Most are rejected by the JSON Schema. One is not: **`reversed-interval.json`**
violates `lower <= upper`, which JSON Schema cannot express — a comparison
between two sibling values has no vocabulary in Draft 2020-12. That constraint
lives in the Python model instead. The contract tests record which layer
rejects which fixture, so that the boundary between the two is visible rather
than assumed.

### `lint_invalid/`

Documents that are **structurally valid but questionable in substance** — an
estimate with no declared uncertainty, an interpretation with no evidence, an
estimated value presented under a label that reads as measured.

These files must pass the schema. They exist to be caught by linting rules that
do not exist yet. Keeping them separate is deliberate: whether a document
*should* declare uncertainty is a policy question, and policy belongs in rules
that a project can configure, not in the schema that defines what a document
*is*.

## Adding a fixture

Use invented names, synthetic coordinates, and `urn:example:` URIs. Never copy
a document out of a real system to reproduce a bug — rewrite it as a synthetic
minimal case. `tests/test_fixture_safety.py` enforces the parts of this that
can be checked mechanically.
