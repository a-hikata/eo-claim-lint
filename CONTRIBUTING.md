# Contributing to eo-claim-lint

Thanks for your interest. This project is in early development and the API is
not stable yet, so please open an issue before starting anything substantial.

## Development environment

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

The package has **no runtime dependencies**. Please keep it that way unless
there is a concrete feature that cannot be built without one, and raise it in an
issue first.

## Checks

Run all of these before opening a pull request. CI runs the same commands on
Python 3.11, 3.12, and 3.13.

```bash
ruff check .                  # lint
ruff format --check .         # formatting
mypy                          # type check
pytest                        # tests
python -m build               # build sdist and wheel
twine check dist/*            # package metadata
```

To apply formatting rather than just checking it:

```bash
ruff format .
```

These are the only commands the project currently has. If you find a command in
the documentation that does not exist, that is a bug — please report it.

## What must never enter this repository

These are not style preferences. A pull request containing any of the following
will be rejected regardless of its other merits.

- **Real-world locations.** No real place names, no real coordinates, no real
  bounding boxes, no parcel or field identifiers from any land registry. Test
  data uses invented names and synthetic coordinates.
- **Personal data.** No names of individuals, no email addresses, no contact
  details, no photographs of people, no producer or landowner information.
- **Data extracted from a specific organisation's internal systems**, including
  thresholds, risk classifications, customer logic, or domain rules that belong
  to a particular business rather than to the general problem this linter
  addresses.
- **Credentials of any kind** — API keys, tokens, passwords, private keys — even
  expired or example ones that look real.
- **Absolute paths from a developer's machine**, internal URLs, or internal
  hostnames.

If you need data to demonstrate a rule, write a synthetic fixture. Synthetic
data is not a compromise here; it is the requirement.

## Adding a rule

Every new rule needs three things, in the same pull request:

1. **A rule ID.** IDs are stable and are never reused, including after a rule is
   removed. Use the next free ID in the appropriate range.
2. **Tests.** At minimum: a document that passes, a document that fails, and a
   boundary case. Include a test that the rule *actually reports* the violation
   it claims to detect — a check that silently never fires reads as a pass.
3. **Documentation.** What the rule checks, why it exists, and what a fix looks
   like.

A rule that cannot be explained without reference to one organisation's business
logic does not belong in this project.

## Commits

- Keep each commit to one logical change.
- Write the subject in the imperative mood: `add rule for missing provenance`,
  not `added` or `adds`.
- Explain *why* in the body when the reason is not obvious from the diff.
- Do not commit generated artifacts (`dist/`, caches, virtual environments).

## Issues and pull requests

- **Issues**: say what you did, what you expected, and what happened. For a
  suspected false positive or false negative, include a **synthetic** document
  that reproduces it.
- **Pull requests**: describe the change and its motivation, link the issue it
  addresses, and confirm that all checks above pass locally.
- Security problems do not go in public issues. See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the
Apache License 2.0, in accordance with section 5 of that license. There is no
separate contributor licence agreement.
