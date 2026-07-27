# Privacy notice

This notice describes what `eo-claim-lint` — the Python package and the GitHub
Action — does with data. It covers version `0.1.0`.

## The short version

**`eo-claim-lint` does not collect, store, sell, transmit, or share personal
data.** There is no telemetry, no analytics, no usage reporting, and no
maintainer-operated service of any kind.

## Where your documents are processed

**Claim documents are read and checked entirely inside your own environment** —
your machine when you run the command line, or the GitHub-hosted runner
executing your workflow when you use the Action.

**The contents of your claim documents are never transmitted to the
maintainer.** The linter has no code that sends a document anywhere. Findings
are written to standard output, and in a workflow they become GitHub
annotations that belong to your repository.

The package declares **no runtime dependencies**, and the linter makes **no
network requests while checking a document**. It contacts no schema URL — the
JSON Schemas ship inside the package and are read from disk — and no Earth
observation service.

## What the Action requires, and what it does not

The Action needs **`contents: read`** and nothing else. It does **not** require
`GITHUB_TOKEN`, repository secrets, API keys, or credentials for any external
service.

**The Action is not network-isolated during installation.** Two steps reach the
network before any linting happens:

1. `actions/setup-python` provisions the Python version you asked for.
2. `pip` installs this package from the Action's own checkout. Because the build
   runs in an isolated environment, `pip` downloads the build backend
   (`hatchling`) and its dependencies from PyPI. These are resolved by version
   range rather than pinned.

Neither step transmits your claim documents. They are ordinary package
installation traffic, directed at GitHub and PyPI, not at the maintainer. If
your threat model requires a fully pinned or fully offline install, vendor the
wheel and install it yourself rather than using the Action.

## What GitHub retains

**GitHub independently retains workflow logs, annotations, job metadata, and
related records under its own terms.** That retention is GitHub's, governed by
the [GitHub Privacy Statement](https://docs.github.com/site-policy/privacy-policies/github-privacy-statement)
and your agreement with GitHub.

**The maintainer of this project does not control, administer, or have access to
those records**, beyond what any person can see in a public repository. Deletion
or export requests concerning workflow logs go to GitHub, not here.

Note that a finding printed by the linter appears in your workflow log, and the
message can quote a field name and a location from your document. The linter is
written not to echo document values into its messages, but the log is still
yours to govern.

## What you should keep out of your documents

**Do not place secrets, credentials, tokens, personal data, customer data, or
sensitive real-world coordinates in a claim document, an issue, or a
reproduction case.**

A claim document is intended to be published — that is the entire point of
checking it — and a workflow log is retained by GitHub. Neither is a suitable
container for anything confidential. Use synthetic data in reports; see
[SUPPORT.md](SUPPORT.md).

## If this ever changes

**If a future version introduces telemetry, a hosted service, calls to an
external API, or any processing under the maintainer's control, this notice must
be updated before that version is released** — not afterwards, and not in a
changelog entry alone. A privacy notice that lags the software it describes is
worse than none.

Any such change would also be a security-relevant change under
[SECURITY.md](SECURITY.md).

## Related documents

- [GitHub Privacy Statement](https://docs.github.com/site-policy/privacy-policies/github-privacy-statement)
- [SECURITY.md](SECURITY.md) — vulnerability reporting and scope
- [SUPPORT.md](SUPPORT.md) — where to ask, and what not to include
- [LICENSE](LICENSE) — Apache License 2.0
