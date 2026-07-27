# Security policy

## Reporting a vulnerability

**Use [private vulnerability reporting](https://github.com/a-hikata/eo-claim-lint/security/advisories/new).**
Open the repository's **Security** tab and choose **Report a vulnerability**.
The report is visible only to you and the maintainer until a fix is published.

Please do **not** open a public issue for a vulnerability.

You can expect an acknowledgement within a week. If a report is accepted, the
fix and the advisory are published together.

## Supported versions

| Version | Supported |
|---|---|
| `0.1.x` | Yes — current release line |
| older | None exist |

While the version is `0.x`, only the latest release receives fixes. There are no
backports.

## What to include, and what to leave out

A good report says what an attacker can do, and how you made it happen.

**Do not put secrets, credentials, tokens, personal data, or real-world
coordinates in a report** — including as a reproduction case. Reproduce with
synthetic data instead. This applies to ordinary bug reports as well as security
reports. If a reproduction genuinely cannot be built from synthetic data, say so
in the report and we will work out how to handle it privately.

## Scope

`eo-claim-lint` is designed to run offline:

- **no network access** while linting,
- **no credentials** and no API keys,
- **no runtime dependencies**.

Anything that would change one of those properties is a security-relevant change
and should be raised before it is implemented.

The GitHub Action inherits the same properties, with one exception worth
stating plainly: `pip` builds this package in an isolated environment, which
downloads the build backend (`hatchling`) and its dependencies from PyPI at run
time. Those are resolved by version range, not pinned. If your threat model
requires a fully pinned install, vendor the wheel and install it yourself rather
than using the Action.

### Reports we are particularly interested in

- A way to make a rule report a document as clean when it is not, or the reverse.
- A way to make the linter read or write a path outside the workspace.
- A way to inject a GitHub Actions workflow command through a document, a file
  name, or an Action input.
- A way to make the linter reach the network.
- Anything that causes an internal failure to be reported as a lint finding
  rather than as exit code 3.

### Out of scope

- **The correctness of any number in a claim document.** This tool never
  recomputes a value; it checks how a value is described. A wrong measurement
  that is honestly labelled is not a vulnerability here.
- **Any claim about legal validity.** Passing this linter establishes nothing
  legally, and no report should assume otherwise.
- Findings that require an attacker to already control the repository or the
  workflow file.
