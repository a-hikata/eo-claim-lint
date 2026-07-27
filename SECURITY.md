# Security policy

## Project status

This project is in **early development**. There is no released version and no
linting functionality yet. Treat it accordingly: it should not be relied on in
a security-sensitive pipeline at this stage.

## Supported versions

| Version | Supported |
|---|---|
| `0.1.x` | Yes — current development line |
| older | None exist |

While the version is `0.x`, only the latest release receives fixes. There are
no backports.

## Reporting a vulnerability

**The contact channel is not established yet.** This repository does not have a
public remote at the time of writing, so no reporting address can be given.

Once the repository is published, the intended channel is **GitHub Security
Advisories** — the "Report a vulnerability" button under the repository's
Security tab — which keeps the report private until a fix is available.

Until then, report privately through whatever channel you already use to reach
the maintainer.

## Please do not

- **Do not open a public issue for a vulnerability.** Use the private channel
  above.
- **Do not put secrets, credentials, tokens, personal data, or real-world
  coordinates in an issue, a pull request, or a test fixture** — including as a
  reproduction case. Reproduce with synthetic data instead. This applies to
  ordinary bug reports as well as security reports.

## Scope notes

`eo-claim-lint` is designed to run offline:

- no network access at lint time,
- no credentials or API keys,
- no runtime dependencies.

Anything that would change one of those properties is a security-relevant
change and should be raised before it is implemented.
